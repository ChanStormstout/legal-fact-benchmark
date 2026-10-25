"""Proof responsibility and request consequences; no legal defaults.

Semantic truth, proof status and procedural/legal consequence remain separate.
This interpreter executes sourced, provider-reviewed mappings, not new legal rules.
"""
from common import refs_valid,review_ok,execution_authorities

def approved(snapshot,rows,ident,mapping,revoked):
    reasons=[]
    if ident in revoked or any(x.endswith(':'+ident) for x in revoked):reasons.append('REVOKED_MAPPING')
    for part in ('scope','law','coverage'):
        r=rows.get(ident,{}).get(part,{})
        if not review_ok(r,snapshot,'LAW') or not any(snapshot['directory'].get(i,{}).get('domain')=='CASE' for i in r.get('refs',[])):
            reasons.append('UNACCEPTED_'+part.upper())
        if not set(mapping['authority_refs'])<=set(r.get('refs',[])):reasons.append('AUTHORITY_REVIEW_MISMATCH')
    if not refs_valid(mapping['authority_refs'],snapshot,'LAW'):reasons.append('MISSING_AUTHORITY')
    elif not execution_authorities(mapping['authority_refs'],snapshot):reasons.append('READING_ONLY_AUTHORITY_NOT_EXECUTABLE')
    return reasons

def compute(snapshot,p,reviews,accepted,computed):
    from engine import logical
    states=computed['task_states']; tasks=p['tasks'];rv=reviews['values'];revoked=accepted['revoked'];burdens={};requests={}
    for ident,b in p.get('burdens',{}).items():
        reasons=approved(snapshot,rv.get('burdens',{}),ident,b,revoked)
        deps=set(b['trigger_tasks']+b['shift_trigger_tasks']+[b['task_id'],b['record_complete_task']]+([] if b['shifted_task_id']=='NONE' else [b['shifted_task_id']]))
        if any(t not in tasks or tasks[t]['scope_id']!=b['scope_id'] for t in deps):reasons.append('BURDEN_SCOPE_MISMATCH')
        if not accepted['execution_scopes'].get(b['scope_id']):reasons.append('SCOPE_UNACCEPTED_OR_UNPARTITIONED')
        scope=p['scopes'].get(b['scope_id'],{})
        for who in (b['holder'],b['shifted_holder']):
            if who!='NONE' and (who not in scope.get('actors',[]) or not accepted['objects'].get(who)):reasons.append('HOLDER_NOT_BOUND')
        activation=logical('AND',[states.get(t,'UNKNOWN') for t in b['trigger_tasks']]) if b['trigger_tasks'] else 'TRUE'
        shift=logical('AND',[states.get(t,'UNKNOWN') for t in b['shift_trigger_tasks']]) if b['shift_trigger_tasks'] else 'FALSE'
        holder=b['holder'];effective_task=b['task_id'];effect='UNRESOLVED'
        if b['shifted_holder']!='NONE':
            if shift=='TRUE':
                holder=b['shifted_holder'];effective_task=b['shifted_task_id']
                if effective_task=='NONE':reasons.append('SHIFT_WITHOUT_PROOF_TASK')
            elif shift not in ('FALSE',):reasons.append('BURDEN_SHIFT_UNRESOLVED')
        elif b['shift_trigger_tasks']:reasons.append('SHIFT_WITHOUT_HOLDER')
        proof={x['proof_status'] for x in accepted['bundles'].values() if x['task_id']==effective_task and x.get('proof_eligible',x['eligible'])}
        # Bundles are alternative evidence combinations: an incomplete alternative
        # does not defeat a separately sufficient reviewed combination.
        if 'CONTESTED' in proof or states.get(effective_task)=='CONFLICTED':status='CONTESTED'
        elif 'SATISFIED' in proof:status='SATISFIED'
        elif proof=={'NOT_SATISFIED'} and all(x.get('proof_eligible',x['eligible']) for x in accepted['bundles'].values() if x['task_id']==effective_task):status='NOT_SATISFIED'
        else:status='UNRESOLVED'
        complete=states.get(b['record_complete_task'],'UNKNOWN')=='TRUE'
        if not reasons:
            if activation=='FALSE':effect='NOT_APPLICABLE'
            elif activation=='TRUE' and status=='SATISFIED':effect='SATISFIED'
            elif activation=='TRUE' and status=='NOT_SATISFIED' and complete:effect=b['failure_effect']
        burdens[ident]={'effect':effect,'holder':holder,'proof_status':status,'record_complete':complete,
            'activation':activation,'shift':shift,'effective_proof_task':effective_task,'task_id':b['task_id'],'scope_id':b['scope_id'],
            'dependencies':sorted(deps),'reasons':reasons,'authority_refs':b['authority_refs'],
            'semantic_state_unchanged':states.get(b['task_id'],'UNKNOWN'),'conditional':computed['conditional_not_actual']}
    for ident,r in p.get('requests',{}).items():
        reasons=approved(snapshot,rv.get('requests',{}),ident,r,revoked);sid=r['scope_id']
        deps=set(r['gates']+r['blockers']+[x['exception_task'] for x in r['exceptions']]+[r['conclusion_task']])
        if any(t not in tasks or tasks[t]['scope_id']!=sid for t in deps):reasons.append('REQUEST_SCOPE_MISMATCH')
        if not accepted['execution_scopes'].get(sid):reasons.append('SCOPE_UNACCEPTED_OR_UNPARTITIONED')
        if not r['coverage_complete'] or r['missing_grounds']:reasons.append('LEGAL_COVERAGE_INCOMPLETE')
        if not computed['search_complete'] or p.get('coverage_limitations'):reasons.append('PATH_SEARCH_INCOMPLETE')
        gates={t for t,x in tasks.items() if x['scope_id']==sid and x['effect']=='CONTROLLING_GATE'}
        bars={t for t,x in tasks.items() if x['scope_id']==sid and x['effect']=='CONTROLLING_BAR'}
        if gates-set(r['gates']) or bars-set(r['blockers']):reasons.append('OMITTED_CONTROL')
        needed={i for i,b in p.get('burdens',{}).items() if b['scope_id']==sid}
        if needed-set(r['burden_ids']):reasons.append('OMITTED_BURDEN')
        if any(i not in burdens or burdens[i]['scope_id']!=sid for i in r['burden_ids']):reasons.append('WRONG_BURDEN')
        effects=[]
        for blocker in r['blockers']:
            ex=[]
            for e in r['exceptions']:
                if e['blocker_task']==blocker:ex.append(states.get(e['exception_task'],'UNKNOWN'))
            ev=logical('OR',ex) if ex else 'FALSE';bv=states.get(blocker,'UNKNOWN')
            effects.append('FALSE' if bv=='FALSE' or ev=='TRUE' else bv if ev=='FALSE' else 'UNKNOWN')
        if any(e['blocker_task'] not in r['blockers'] or not execution_authorities(e['authority_refs'],snapshot) or not set(e['authority_refs'])<=set(rv.get('requests',{}).get(ident,{}).get('law',{}).get('refs',[])) for e in r['exceptions']):reasons.append('UNSUPPORTED_TARGETED_EXCEPTION')
        gate=logical('AND',[states.get(t,'UNKNOWN') for t in r['gates']]) if r['gates'] else 'TRUE'
        blocker=logical('OR',effects) if effects else 'FALSE';grounds=[]
        for group in r['grounds']:
            ps=[]
            for pid in group['all_paths']:
                path=computed['paths'].get(pid)
                if not path or path['scope_id']!=sid:reasons.append('WRONG_GROUND_SCOPE');ps.append('UNKNOWN');continue
                value=path['state']
                failed_burden=any(b['effect']=='PATH_UNAVAILABLE' and b['task_id'] in path['dependencies'] for b in burdens.values() if b['scope_id']==sid)
                ps.append('FALSE' if failed_burden else 'TRUE' if value=='CONDITIONS_MET_IN_DECLARED_SCOPE' else 'FALSE' if value in ('BLOCKED','PROCEDURALLY_UNAVAILABLE','REQUIRED_SUPPORT_REFUTED') else 'UNKNOWN')
            grounds.append(logical('AND',ps))
        support=logical('OR',grounds);be=[burdens[i]['effect'] for i in r['burden_ids'] if i in burdens]
        outcome='UNRESOLVED'
        if not reasons:
            if gate=='FALSE':outcome='PROCEDURALLY_UNAVAILABLE'
            elif blocker=='TRUE':outcome='BLOCKED'
            elif gate=='TRUE' and blocker=='FALSE':
                if 'REQUEST_NOT_ESTABLISHED' in be:outcome='NOT_ESTABLISHED'
                elif support=='FALSE':outcome='NOT_ESTABLISHED'
                elif support=='TRUE' and 'UNRESOLVED' not in be:outcome='SUPPORTED_IN_DECLARED_SCOPE'
        requests[ident]={'outcome':outcome,'scope_id':sid,'task_id':r['conclusion_task'],'level':r['level'],
            'ground_states':grounds,'gate_state':gate,'blocker_state':blocker,'burden_ids':r['burden_ids'],
            'path_ids':[i for g in r['grounds'] for i in g['all_paths']], 'authority_refs':r['authority_refs'],
            'reasons':sorted(set(reasons)),'conditional':computed['conditional_not_actual'],
            'legal_approval':False,'not_whole_case_outcome':True}
    return {'burdens':burdens,'requests':requests}
