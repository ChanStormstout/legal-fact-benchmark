"""Scoped evidence, DAG derivation, targeted exceptions, and report control.

Legal content and acceptance are always model-proposed/source-reviewed. Program
logic alone never certifies premise truth, completeness or legal correctness.
"""
import datetime
from common import digest, refs_valid, review_ok, actionable_omissions, coverage_consistent, task_review_ok, witness_quotes_valid, execution_authorities, unsupported_time_years, substantive_report_text, SCOPE_FIELDS, SPEAKER_KINDS
from legal_bench.proof_carrying.use_contract_v14 import inspect_use
from legal_bench.proof_carrying.semantic_checker_v16 import inspect_alignment, review_status
from legal_bench.research_diagnostic_e2e_v1.contracts import join as old_join
from legal_bench.proof_carrying.final_statement_pack_v20_9 import check_pack

VALUES={'TRUE','FALSE','UNKNOWN','CONFLICTED'}

def join(values):
    return old_join([v.replace('CONFLICTED','CONFLICT') for v in values]).replace('CONFLICT','CONFLICTED')

def logical(op, values):
    if op=='AND':
        if 'FALSE' in values:return 'FALSE'
        if 'CONFLICTED' in values:return 'CONFLICTED'
        return 'TRUE' if values and all(x=='TRUE' for x in values) else 'UNKNOWN'
    if op=='OR':
        if 'TRUE' in values:return 'TRUE'
        if 'CONFLICTED' in values:return 'CONFLICTED'
        return 'FALSE' if values and all(x=='FALSE' for x in values) else 'UNKNOWN'
    raise ValueError('UNSUPPORTED_OPERATOR:'+op)

def evaluate(expr, states):
    op=expr.get('op')
    if op=='REF':return states.get(expr['id'],'UNKNOWN')
    if op=='NOT':
        if len(expr.get('args',[]))!=1:raise ValueError('NOT_ARITY')
        return {'TRUE':'FALSE','FALSE':'TRUE','UNKNOWN':'UNKNOWN','CONFLICTED':'CONFLICTED'}[evaluate(expr['args'][0],states)]
    if op in ('AND','OR'):return logical(op,[evaluate(x,states) for x in expr.get('args',[])])
    raise ValueError('UNSUPPORTED_OPERATOR:'+str(op))

def witnesses(refs,sources):
    return [{'refs':[r],'quote':sources[r]['text']} for r in refs if r in sources]

def envelope(snapshot,proposal,values):
    return {'snapshot_id':snapshot['snapshot_id'],'proposal_hash':digest(proposal),'values':values,'legal_approval':False}

def require_review(snapshot,proposal,reviews):
    if reviews['snapshot_id']!=snapshot['snapshot_id'] or reviews['proposal_hash']!=digest(proposal):
        raise ValueError('REVIEW_VERSION_OR_SOURCE_VIEW_CONFLICT')
    return reviews['values']

def validate_dependencies(p):
    """Reject stale graph references before any inference; not a semantic check."""
    errors=[];tasks=p['tasks'];scopes=p['scopes'];objects=p['objects'];records=p.get('source_records',{})
    for sid,s in scopes.items():
        ids=s['actors']+s['properties']+([] if s['court']=='UNKNOWN' else [s['court']])+[r['object_id'] for r in s['participant_roles']]
        errors.extend('scope:'+sid+':object:'+i for i in ids if i not in objects)
    errors.extend('task:'+tid+':scope:'+t['scope_id'] for tid,t in tasks.items() if t['scope_id'] not in scopes)
    for uid,u in p['uses'].items():
        if u['task_id'] not in tasks:errors.append('use:'+uid+':task:'+u['task_id'])
        errors.extend('use:'+uid+':record:'+rid for rid in u.get('source_record_ids',[]) if rid not in records)
    for bid,b in p['bundles'].items():
        if b['task_id'] not in tasks:errors.append('bundle:'+bid+':task:'+b['task_id'])
        errors.extend('bundle:'+bid+':use:'+uid for uid in b['use_ids']+b['counter_use_ids']
            if uid not in p['uses'] or p['uses'][uid]['task_id']!=b['task_id'])
    if errors:raise ValueError('STALE_DEPENDENCY_REFERENCES:'+','.join(errors))


def inspect(snapshot,proposal,reviews,revoked=()):
    validate_dependencies(proposal)
    rv=require_review(snapshot,proposal,reviews);revoked=set(revoked)
    objects=proposal['objects'];scopes=proposal['scopes'];tasks=proposal['tasks']
    sources={i:{'text':x['text'],'document_role':'TARGET' if x['domain']=='CASE' else 'AUTHORITY',
        'role':'VISIBLE_RECONSTRUCTION','document':x['origin_group']} for i,x in snapshot['directory'].items()}
    def accepted(group,ident,part=None,domain=None):
        if ident in revoked or f'{group}:{ident}' in revoked or (part and f'{group}:{ident}:{part}' in revoked):return False
        rec=rv.get(group,{}).get(ident,{})
        if group=='tasks' and part is None:
            if any(f'tasks:{ident}:{k}' in revoked for k in ('question','law')):return False
            return task_review_ok(rec,snapshot,tasks[ident])
        return review_ok(rec.get(part,{}) if part else rec,snapshot,domain)
    object_ok={i:refs_valid(o['refs'],snapshot,'CASE') and accepted('objects',i,domain='CASE')
        and rv.get('objects',{}).get(i,{}).get('observed_kind')==o['kind']
        and witness_quotes_valid(rv.get('objects',{}).get(i,{}).get('identity_witnesses',[]),snapshot,'CASE',rv.get('objects',{}).get(i,{}).get('refs',[]))
        for i,o in objects.items()}
    scope_ok={};scope_checks={};execution_scope_ok={}
    for sid,s in scopes.items():
        ids=s['actors']+s['properties']+([] if s['court']=='UNKNOWN' else [s['court']])+[r['object_id'] for r in s['participant_roles']]
        typed=all(objects.get(i,{}).get('kind')=='PROPERTY' for i in s['properties']) and all(objects.get(i,{}).get('kind') in ('PARTY','PERSON','ORGANIZATION') for i in s['actors'])
        court=s['court']=='UNKNOWN' or objects.get(s['court'],{}).get('kind')=='COURT'
        checks={}
        for part,fields in SCOPE_FIELDS.items():
            rec=rv.get('scopes',{}).get(sid,{}).get(part,{})
            checks[part]={'decision':rec.get('decision','UNRESOLVED'),
                'assessed_exact_declared_values':rec.get('assessed')=={k:s[k] for k in fields},
                'has_source_witness':witness_quotes_valid(rec.get('witnesses',[]),snapshot,'CASE',rec.get('refs',[])),
                'unsupported_years':unsupported_time_years(s['time'],rec.get('witnesses',[]),snapshot) if part=='time' else [],
                'event_relation_valid':(rec.get('event_relation')=='MATCH' and rec.get('time_role')=='EVENT_DATE') if part=='time' else True}
        scope_checks[sid]=checks
        scope_ok[sid]=typed and court and all(witness_quotes_valid(r['witnesses'],snapshot,'CASE') for r in s['participant_roles']) and all(object_ok.get(i,False) for i in ids) and all(
            accepted('scopes',sid,k,'CASE') and x['assessed_exact_declared_values'] and x['has_source_witness'] and not x['unsupported_years'] and x['event_relation_valid'] for k,x in checks.items())
        # A heterogeneous collection can be described as a collection. It cannot
        # silently stand for each differently governed unit in rule computation.
        execution_scope_ok[sid]=scope_ok[sid] and all(objects[i].get('extent') not in ('HETEROGENEOUS_COLLECTION','UNRESOLVED') for i in s['properties'])
    import source_records as SR
    record_acceptance=SR.qualify(snapshot,proposal.get('source_records',{}),rv.get('source_records',{}),revoked)
    uses={}
    for uid,u in proposal['uses'].items():
        t=tasks[u['task_id']];scope=scopes[t['scope_id']]
        bindings={k:scope[k] for k in ('actors','properties','time','stage','court','request')}
        raw={'rule_premise':u['task_id'],'bindings':bindings,'premise_state':u['state'],'use_judgment':'UNRESOLVED'}
        declared={'purpose':u['purpose'],'direction':'OPPOSE' if u['purpose']=='PARTIAL_OPPOSITION' else 'SUPPORT',
            'premise_id':u['task_id'],'bindings':bindings,'stage':scope['stage'],'source_status':u['status'],
            'source_witnesses':witnesses(u['refs'],sources)}
        uc=inspect_use(raw,declared,sources)
        # Displaying an attributed statement never requires whole-predicate approval.
        owner=u.get('source_owner','UNRESOLVED')
        needs_owner=u.get('content_role')=='ATTRIBUTION' or u['status'] in ('PARTY_CLAIM','COURT_RECORDED')
        record_ids=u.get('source_record_ids',[])
        local_owner=(owner=='SOURCE_LOCAL_UNNAMED' and bool(record_ids) and all(
            record_acceptance.get(i,{}).get('report_eligible') and proposal['source_records'][i]['source_owner']==owner
            and proposal['source_records'][i]['owner_label'].strip() for i in record_ids))
        owner_ok=not needs_owner or local_owner or (objects.get(owner,{}).get('kind') in SPEAKER_KINDS and object_ok.get(owner,False))
        if t.get('source_owner') not in (None,'NONE','UNRESOLVED'):
            owner_ok=owner_ok and owner==t['source_owner']
        record_ids=u.get('source_record_ids',[])
        reasons=[]
        if not record_ids or any(not record_acceptance.get(i,{}).get('report_eligible') for i in record_ids):reasons.append('SOURCE_RECORD_DEPENDENCY_UNACCEPTED')
        if not set(u['refs'])<=set(r for i in record_ids for r in proposal.get('source_records',{}).get(i,{}).get('refs',[])):reasons.append('USE_REFS_OUTSIDE_SOURCE_RECORDS')
        if not owner_ok:reasons.append('SOURCE_OWNER_UNQUALIFIED_OR_MISMATCH')
        reasons.extend(uc.get('errors',[]));reasons.extend(uc.get('pending',[]))
        source_review=rv.get('uses',{}).get(uid,{})
        attribution=source_review.get('attribution',{});binding=source_review.get('binding',{})
        observed_owner_ok=(attribution.get('owner_relation')=='MATCH' and
            attribution.get('observed_owner')==owner and attribution.get('observed_status')==u['status'])
        if not observed_owner_ok:reasons.append('SOURCE_OWNER_OR_STATUS_NOT_INDEPENDENTLY_MATCHED')
        observed_binding_ok=(binding.get('scope_relation')=='MATCH' and
            set(binding.get('observed_actors',[]))=={a for rid in record_ids for a in proposal['source_records'][rid]['actors']} and
            set(binding.get('observed_properties',[]))=={a for rid in record_ids for a in proposal['source_records'][rid]['properties']} and bool(binding.get('record_event','').strip()))
        if not observed_binding_ok:reasons.append('SOURCE_EVENT_OR_BINDING_NOT_INDEPENDENTLY_MATCHED')
        for part in ('attribution','binding','report'):
            record=rv.get('uses',{}).get(uid,{}).get(part,{})
            if not accepted('uses',uid,part,'CASE'):reasons.append('SOURCE_USE_REVIEW_NOT_ACCEPTED:'+part)
            if not witness_quotes_valid(record.get('witnesses',[]),snapshot,'CASE',record.get('refs',[])):reasons.append('SOURCE_USE_WITNESS_MISSING:'+part)
        # Reporting the EXACT source statement has its own model-reviewed binding.
        # Execution still requires every applicable scope, task and legal gate.
        report_ok=not reasons and uc.get('eligible_under_declared_review',False)
        # Uncertain legal/premise use does not invalidate an accurately attributed
        # source description. The same uncertainty still blocks every derivation.
        premise_reasons=[]
        bridges=[SR.bridge_check(snapshot,proposal['source_records'][rid],scope,source_review.get('scope_bridge',{})) for rid in record_ids if rid in proposal['source_records']]
        if not bridges or any(not b['accepted'] for b in bridges):premise_reasons.append('SOURCE_TO_TARGET_SCOPE_NOT_VERIFIED')
        premise=source_review.get('use',{})
        if not accepted('uses',uid,'use','CASE'):premise_reasons.append('PREMISE_USE_REVIEW_NOT_ACCEPTED')
        if not witness_quotes_valid(premise.get('witnesses',[]),snapshot,'CASE',premise.get('refs',[])):premise_reasons.append('PREMISE_USE_WITNESS_MISSING')
        uses[uid]={'report_eligible':report_ok,'report_reasons':reasons,
            'bundle_eligible':report_ok and not premise_reasons and scope_ok.get(t['scope_id'],False) and accepted('tasks',u['task_id']),
            'premise_reasons':premise_reasons,'scope_bridges':bridges,'report_requires_task_execution_acceptance':False,'use_contract_v14':uc,'task_id':u['task_id'],
            'source_owner':owner,'content_role':u.get('content_role'),'owner_qualified':owner_ok,
            'origin_groups':sorted({snapshot['directory'][r]['origin_group'] for r in u['refs']}),
            'review':rv.get('uses',{}).get(uid,{}),'legal_approval':False}
    bundles={}
    for bid,b in proposal['bundles'].items():
        tid=b['task_id'];t=tasks[tid];s=scopes[t['scope_id']];ids=b['use_ids']
        all_ids=ids+b['counter_use_ids']; reasons=[]
        if not ids or any(i not in uses or proposal['uses'][i]['task_id']!=tid for i in all_ids):reasons.append('INVALID_TASK_USE_BINDING')
        if any(not uses.get(i,{}).get('bundle_eligible') for i in all_ids):reasons.append('UNACCEPTED_USE_OR_COUNTEREVIDENCE')
        # An omitted adverse use cannot silently become an accepted complete premise.
        adverse={i for i,u in proposal['uses'].items() if u['task_id']==tid and u['purpose']=='PARTIAL_OPPOSITION' and uses[i]['bundle_eligible']}
        if adverse-set(all_ids):reasons.append('OMITTED_DECLARED_COUNTEREVIDENCE')
        if not execution_scope_ok.get(t['scope_id']):reasons.append('UNACCEPTED_OR_UNPARTITIONED_EXECUTION_SCOPE')
        if t['effect'] in ('CONTROLLING_GATE','CONTROLLING_BAR') and not refs_valid(t['authority_refs'],snapshot,'LAW'):reasons.append('CONTROLLING_TASK_WITHOUT_AUTHORITY')
        if not accepted('tasks',tid):reasons.append('TASK_SCOPE_OR_STANDARD_UNACCEPTED')
        if t['kind']=='DERIVED':reasons.append('DERIVED_TASK_REQUIRES_RULE_NOT_BUNDLE')
        # Hypotheses are applied after checking the immutable ACTUAL parent; never assessed as evidence.
        selected=[proposal['uses'][i] for i in ids if i in proposal['uses']]
        if any(u['status'] in ('PARTY_CLAIM','HYPOTHETICAL','LIMITATION') for u in selected):reasons.append('ASSERTION_CANNOT_ESTABLISH_CONTENT')
        if t['kind'] in ('FACT','PROCEDURE') and any(u.get('content_role')!='OBSERVATION' for u in selected):
            reasons.append('ATTRIBUTED_OR_ASSESSED_CONTENT_NOT_FACT_PREMISE')
        if t['kind']=='ATTRIBUTION':reasons.append('ATTRIBUTED_RECORD_REPORT_ONLY')
        needs_standard=t['kind'] in ('LEGAL','PROCEDURE') or b['proof_status']=='NOT_SATISFIED'
        if needs_standard and (not execution_authorities(b['sufficiency_authority_refs'],snapshot) or not accepted('bundles',bid,'standard','LAW')):reasons.append('BURDEN_OR_LEGAL_STANDARD_UNSUPPORTED')
        # Proof burden and semantic truth are independent axes. Failure to prove P
        # never becomes FALSE(P); CONTESTED does not erase an explicit CONFLICTED.
        # The separately reviewed whole-premise state alone feeds four-valued logic.
        refs=list(dict.fromkeys(r for u in selected for r in u['refs']))
        binding_values={k:s[k] for k in ('actors','properties','time','stage','court','request') if s[k] not in ([], 'UNKNOWN')}
        ws=witnesses(refs,sources);bv=rv.get('bundles',{}).get(bid,{})
        source_stages=sorted({proposal['source_records'][rid]['procedure'] for u in selected for rid in u.get('source_record_ids',[])})
        row={'statement_status':'REPORTED_EVIDENCE','source_stage':' | '.join(source_stages),'rule_stage':s['stage'],'court_level':'SCOPED_MODEL_ASSESSMENT',
            'bindings':[{'role':k,'variable':k,'value':v,'status':'BOUND','basis':b['reason'],'witnesses':ws} for k,v in binding_values.items()],
            # This promotes the separately assessed complete BUNDLE, not each partial source.
            'uses':[{'purpose':'ESTABLISH_OCCURRENCE','explanation':b['reason'],'witnesses':ws}],
            'whole_premise':{'state':b['state'],'basis':b['reason'],'complete':b['complete'],'missing_components':b['missing'],'use_indices':[1],
                'components':[{'component':c['condition'],'covered':c['covered'],'basis':b['reason'],
                    'witnesses':witnesses(list(dict.fromkeys(r for u in c['use_ids'] if u in proposal['uses'] for r in proposal['uses'][u]['refs'])),sources)} for c in b['components']]},
            'counterevidence':witnesses(list(dict.fromkeys(r for u in b['counter_use_ids'] if u in proposal['uses'] for r in proposal['uses'][u]['refs'])),sources), 'limitations':b['missing']}
        directory={'allowed_statuses':['REPORTED_EVIDENCE'],'rule_stage':s['stage'],'role_descriptions':{k:k for k in binding_values},
            'candidate_bindings':binding_values,'original_use':{'bindings':binding_values},'execution_binding_dependencies':list(binding_values)}
        records=[]
        for part,scope in [('alignment','ALIGNMENT'),('whole','WHOLE_PREMISE'),('alignment','USE')]:
            rec=bv.get(part,{});records.append({'scope':scope,'decision':rec.get('decision','UNRESOLVED') if accepted('bundles',bid,part) else 'UNRESOLVED','reason':rec.get('reason','No model review'),'witnesses':witnesses([r for r in rec.get('refs',[]) if sources.get(r,{}).get('document_role')=='TARGET'],sources),**({'use_index':1} if scope=='USE' else {})})
        br=bv.get('binding',{})
        records += [{'scope':'BINDING','role':k,'decision':br.get('decision','UNRESOLVED') if accepted('bundles',bid,'binding') else 'UNRESOLVED','reason':br.get('reason','No model review'),'witnesses':witnesses([r for r in br.get('refs',[]) if sources.get(r,{}).get('document_role')=='TARGET'],sources)} for k in binding_values]
        alignment=inspect_alignment(row,directory,sources);checked=review_status(row,records,sources,directory,alignment)
        if alignment['structural_status']!='PASS' or checked['decision']!='ACCEPT':reasons.append('V16_WHOLE_OR_BINDING_NOT_ACCEPTED')
        if not accepted('bundles',bid,'counterevidence'):reasons.append('COUNTEREVIDENCE_REVIEW_NOT_ACCEPTED')
        # All component references must belong to this exact bundle.
        if any(not set(c['use_ids'])<=set(ids) for c in b['components']):reasons.append('COMPONENT_OUTSIDE_BUNDLE')
        groups=sorted({g for uid in all_ids if uid in uses for g in uses[uid]['origin_groups']})
        bundles[bid]={'task_id':tid,'state':b['state'] if not reasons else 'UNKNOWN','eligible':not reasons,'reasons':reasons,
            'proof_status':b['proof_status'],'proof_eligible':not [x for x in reasons if x!='V16_WHOLE_OR_BINDING_NOT_ACCEPTED'] and all(accepted('bundles',bid,k) for k in ('alignment','binding','whole','counterevidence','standard')),'origin_groups':groups,'independent_source_count':len(groups),
            'independence_is_not_sufficiency':True,'alignment_v16':alignment,'scoped_review_v16':checked,
            'use_dependencies':all_ids,'review':bv}
    from history_comparison import qualify
    analogies={}
    for hid,h in proposal.get('analogies',{}).items():
        rec=rv.get('analogies',{}).get(hid,{})
        if 'current_assertions' not in h:
            analogies[hid]={'report_eligible':False,'reasons':['LEGACY_COMPARISON_REQUIRES_NEW_SOURCE_REVIEW'],
                'task_id':h['task_id'],'history_refs':h['history_refs'],'case_refs':h['case_refs'],'never_current_case_premise':True}
            continue
        row=qualify(snapshot,h,rec,hid in revoked or 'analogies:'+hid in revoked)
        if any(tid not in tasks or not task_review_ok(rv.get('tasks',{}).get(tid,{}),snapshot,tasks[tid],execution=False) for tid in h.get('report_task_ids',[])):
            row['reasons'].append('TASK_QUESTION_UNACCEPTED');row['report_eligible']=False;row['permitted_use']=None
        analogies[hid]=row
    return {'source_records':record_acceptance,'analogies':analogies,'objects':object_ok,'scopes':scope_ok,'execution_scopes':execution_scope_ok,'scope_checks':scope_checks,'uses':uses,'bundles':bundles,'revoked':sorted(revoked)}

def compute(snapshot,p,reviews,accepted,cfg,assumptions=None):
    rv=require_review(snapshot,p,reviews);rules={r['id']:r for r in snapshot['rule_library']['rules']};tasks=p['tasks']
    base={i:join([b['state'] for b in accepted['bundles'].values() if b['task_id']==i and b['eligible']]) for i in tasks}
    states=dict(base);traces={};pending=dict(p['applications']);evaluations=0
    for tid,value in (assumptions or {}).items():
        if tid not in tasks or tasks[tid]['kind'] in ('DERIVED','ATTRIBUTION') or base[tid]!='UNKNOWN' or value not in ('TRUE','FALSE'):
            raise ValueError('HYPOTHESIS_MAY_ONLY_FILL_UNRESOLVED_TASK_NOT_CHANGE_KNOWN_FACT')
        states[tid]=value
    alias={}
    for i,src in snapshot['directory'].items():alias.setdefault(src['original_id'],[]).append(i)
    revoked=set(accepted['revoked'])
    while pending and evaluations<cfg['max_rule_evaluations']:
        progressed=False
        for aid,a in list(pending.items()):
            deps={v for v in a['premises'].values() if v!='UNKNOWN'}
            waiting={x for x in deps if x in pending}
            if waiting:continue
            evaluations+=1;progressed=True;del pending[aid]
            task=tasks[aid];r=rules[task['rule_id']];v=rv.get('applications',{}).get(aid,{})
            reasons=[]
            screening=p.get('rule_screen',{}).get(task['rule_id'],{})
            if screening.get('assessment')!='ASSESS_CONDITIONS' or task['scope_id'] not in screening.get('scope_ids',[]):reasons.append('RULE_CANDIDATE_NOT_SELECTED_FOR_THIS_SCOPE')
            if not refs_valid(screening.get('case_refs',[]),snapshot,'CASE') or not execution_authorities(screening.get('law_refs',[]),snapshot):reasons.append('RULE_SCREEN_WITHOUT_CASE_AND_LAW_BASIS')
            if not a['selected'] or a['applicability']!='APPLICABLE':reasons.append('RULE_SCOPE_UNSUPPORTED')
            if not r.get('execution_enabled') or not r.get('original_text_verified'):reasons.append('FROZEN_RULE_NOT_EXECUTABLE')
            if not execution_authorities([j for i in r['refs'] for j in alias.get(i,[])],snapshot):reasons.append('READING_ONLY_OR_MISSING_RULE_AUTHORITY')
            if r.get('effect') in ('PROCEDURAL_GATE','EVIDENCE_GATE') and task['effect']!='CONTROLLING_GATE':reasons.append('RULE_GATE_EFFECT_MISMATCH')
            if r.get('effect') in ('PROCEDURAL_BAR','SUBSTANTIVE_BAR','GUARD') and task['effect']!='CONTROLLING_BAR':reasons.append('RULE_BAR_EFFECT_MISMATCH')
            if not task_review_ok(rv.get('tasks',{}).get(aid,{}),snapshot,task):reasons.append('DERIVED_TASK_NOT_ACCEPTED')
            if not accepted['execution_scopes'].get(task['scope_id']):reasons.append('SCOPE_UNACCEPTED_OR_UNPARTITIONED')
            if aid in revoked or 'applications:'+aid in revoked or 'tasks:'+aid in revoked or any(f'tasks:{aid}:{k}' in revoked for k in ('question','law')):reasons.append('REVIEW_REVOKED')
            for part in ('scope','mapping','time'):
                record=v.get(part,{})
                if not review_ok(record,snapshot,'LAW') or not any(snapshot['directory'][i]['domain']=='CASE' for i in record.get('refs',[]) if i in snapshot['directory']):reasons.append('UNACCEPTED_APPLICATION_'+part)
                if any(not set(alias.get(i,[])) & set(record.get('refs',[])) for i in r['refs']):reasons.append('WRONG_RULE_AUTHORITY_'+part)
            if any(x not in tasks or tasks[x]['scope_id']!=task['scope_id'] or tasks[x]['kind']=='ATTRIBUTION' for x in deps):reasons.append('CROSS_SCOPE_OR_ATTRIBUTION_PREMISE')
            try:
                lo=datetime.date.fromisoformat(a['event_interval']['from']);hi=datetime.date.fromisoformat(a['event_interval']['to']);effective=datetime.date.fromisoformat(r['effective_from'])
                if lo>hi:reasons.append('REVERSED_EVENT_INTERVAL')
                if not refs_valid(a['event_interval']['refs'],snapshot,'CASE'):reasons.append('EVENT_WITHOUT_SOURCE')
                if lo<effective and r.get('temporal_mode')!='SAVINGS_PRECOMMENCEMENT':reasons.append('LAW_TIME_UNSUPPORTED')
            except (ValueError,KeyError):reasons.append('UNRESOLVED_EVENT_TIME')
            # Frozen arithmetic predicates require event-specific sourced intervals.
            values={pred:states.get(tid,'UNKNOWN') for pred,tid in a['premises'].items()}
            for pred,dc in r.get('date_constraints',{}).items():
                interval=a['predicate_intervals'].get(pred,{})
                try:
                    start=datetime.date.fromisoformat(interval['from']);end=datetime.date.fromisoformat(interval['to'])
                    threshold=datetime.date.fromisoformat(dc['before'])
                    verified=review_ok(v.get('date:'+pred,{}),snapshot,'CASE') and refs_valid(interval['refs'],snapshot,'CASE') and start<=end
                    calculated=('TRUE' if end<threshold else 'FALSE' if start>=threshold else 'UNKNOWN') if verified else 'UNKNOWN'
                    if values[pred] in ('TRUE','FALSE') and values[pred]!=calculated:reasons.append('DATE_PREDICATE_MISMATCH:'+pred)
                    values[pred]=calculated
                except (ValueError,KeyError):values[pred]='UNKNOWN'
            try:raw=evaluate(r['expression'],values)
            except ValueError as exc:raw='UNKNOWN';reasons.append(str(exc))
            state=raw if not reasons else 'UNKNOWN'
            states[aid]=state
            traces[aid]={'rule_id':r['id'],'scope_id':task['scope_id'],'state':state,'raw_conditional_state':raw,
                'status':'SCOPE_UNSUPPORTED' if reasons else 'COMPUTED_IN_DECLARED_SCOPE','reasons':reasons,
                'failure_categories':sorted(set('LEGAL_AUTHORITY' if any(w in reason for w in ('AUTHORITY','FROZEN_RULE')) else 'SCOPE_BINDING' if 'SCOPE_UNACCEPTED' in reason or 'CROSS_SCOPE' in reason else 'TEMPORAL' if any(w in reason for w in ('TIME','INTERVAL','DATE')) else 'SEMANTIC_APPLICABILITY_OR_MAPPING' for reason in reasons)),
                'premises':a['premises'],'premise_states':values,'authority_refs':[j for i in r['refs'] for j in alias.get(i,[])],
                'legal_approval':False}
            if evaluations>=cfg['max_rule_evaluations']:break
        if not progressed:break
    for aid in pending:
        states[aid]='UNKNOWN';traces[aid]={'state':'UNKNOWN','status':'UNRESOLVED_CYCLE_OR_COMPUTATION_LIMIT','premises':pending[aid]['premises'],'legal_approval':False}
    paths={}
    for pid,path in p['paths'].items():
        reasons=[];v=rv.get('paths',{}).get(pid,{})
        if not accepted['execution_scopes'].get(path['scope_id']):reasons.append('SCOPE_UNACCEPTED_OR_UNPARTITIONED')
        if not execution_authorities(path['authority_refs'],snapshot):reasons.append('PATH_AUTHORITY_NOT_EXECUTABLE')
        controlling_gates={i for i,t in tasks.items() if t['scope_id']==path['scope_id'] and t['effect']=='CONTROLLING_GATE'}
        controlling_bars={i for i,t in tasks.items() if t['scope_id']==path['scope_id'] and t['effect']=='CONTROLLING_BAR'}
        if controlling_gates-set(path['gates']):reasons.append('OMITTED_CONTROLLING_GATE')
        if controlling_bars-set(path['blockers']):reasons.append('OMITTED_CONTROLLING_BAR')
        dependencies=set(path['supports']+path['alternatives']+path['gates']+path['blockers']+[x['exception_task'] for x in path['exceptions']])
        if not dependencies or any(i not in tasks or tasks[i]['scope_id']!=path['scope_id'] for i in dependencies|{path['conclusion_task']}):reasons.append('PATH_SCOPE_OR_DEPENDENCY_ERROR')
        if not path['supports'] and not path['alternatives']:reasons.append('NO_POSITIVE_PATH')
        if not review_ok(v,snapshot,'LAW') or not refs_valid(path['authority_refs'],snapshot,'LAW'):reasons.append('PATH_LEGAL_RELATION_UNREVIEWED')
        if not set(path['authority_refs'])<=set(v.get('refs',[])):reasons.append('PATH_AUTHORITY_MISMATCH')
        if pid in revoked or 'paths:'+pid in revoked:reasons.append('PATH_REVIEW_REVOKED')
        if any(e['blocker_task'] not in path['blockers'] or not refs_valid(e['authority_refs'],snapshot,'LAW') or not set(e['authority_refs'])<=set(v.get('refs',[])) for e in path['exceptions']):reasons.append('UNSUPPORTED_EXCEPTION_TARGET')
        support=logical('AND',[states.get(i,'UNKNOWN') for i in path['supports']]) if path['supports'] else 'TRUE'
        alternative=logical('OR',[states.get(i,'UNKNOWN') for i in path['alternatives']]) if path['alternatives'] else 'TRUE'
        gates=logical('AND',[states.get(i,'UNKNOWN') for i in path['gates']]) if path['gates'] else 'TRUE'
        effects=[]
        for blocker in path['blockers']:
            b=states.get(blocker,'UNKNOWN');exc=[states.get(e['exception_task'],'UNKNOWN') for e in path['exceptions'] if e['blocker_task']==blocker]
            ex=logical('OR',exc) if exc else 'FALSE'
            effects.append('FALSE' if b=='FALSE' or ex=='TRUE' else b if ex=='FALSE' else 'UNKNOWN')
        blocker=logical('OR',effects) if effects else 'FALSE'
        value='UNRESOLVED'
        if not reasons:
            if blocker=='TRUE':value='BLOCKED'
            elif gates=='FALSE':value='PROCEDURALLY_UNAVAILABLE'
            elif support=='FALSE' or alternative=='FALSE':value='REQUIRED_SUPPORT_REFUTED'
            elif support==alternative==gates=='TRUE' and blocker=='FALSE':value='CONDITIONS_MET_IN_DECLARED_SCOPE'
        paths[pid]={'state':value,'hypothetical':bool(assumptions),'reasons':reasons,'task_id':path['conclusion_task'],'dependencies':sorted(dependencies),
            'gate_state':gates,'blocker_state':blocker,'scope_id':path['scope_id'],'legal_approval':False}
    # Comparisons annotate existing paths; they cannot change any truth value,
    # rule trace, procedural gate or request certificate.
    for pid,row in paths.items():
        linked=[hid for hid,h in p.get('analogies',{}).items() if accepted['analogies'][hid]['report_eligible']
                and set(h.get('report_task_ids',[])) & set(row['dependencies']+[row['task_id']])]
        row['historical_context']=[{'comparison_id':hid,'purpose':accepted['analogies'][hid]['permitted_use'],
            'law_status':p['analogies'][hid]['law_status'],'affects':'ARGUMENT_AND_REPORT_ONLY'} for hid in linked]
        row['historical_response_required']=[hid for hid in linked if accepted['analogies'][hid]['permitted_use'] in
            ('COUNTERARGUMENT','MATERIAL_DISTINCTION','PROCEDURAL_LIMIT')]
    result={'task_states':states,'rules':traces,'paths':paths,'evaluations':evaluations,
        'search_complete':p['search_complete'] and not pending and not p['unrepresented_paths'],
        'scope_supported':any(x.get('status')=='COMPUTED_IN_DECLARED_SCOPE' for x in traces.values()),
        'not_global_relief_certificate':True,'namespace':'HYPOTHETICAL' if assumptions else snapshot['namespace'],
        'assumptions':assumptions or {},'conditional_not_actual':bool(assumptions) or snapshot['namespace']=='HYPOTHETICAL','legal_approval':False}
    result['rule_coverage']={'proposed_applications':len(p['applications']),
        'frozen_rule_dispositions':p.get('rule_screen',{}),
        'unassessed_frozen_rules':sorted(set(rules)-set(p.get('rule_screen',{}))),
        'condition_assessment_without_scope':[i for i,row in p.get('rule_screen',{}).items() if row['assessment']=='ASSESS_CONDITIONS' and not row['scope_ids']],
        'computed_in_declared_scope':sum(x.get('status')=='COMPUTED_IN_DECLARED_SCOPE' for x in traces.values()),
        'unmapped_rule_tasks':[i for i,t in tasks.items() if t['kind']=='DERIVED' and t['rule_id']!='NONE' and i not in p['applications']],
        'open_legal_tasks':[i for i,t in tasks.items() if t['kind'] in ('LEGAL','PROCEDURE','DERIVED') and t['rule_id']=='NONE'],
        'proof_task_count':sum(t.get('role')=='PROOF' for t in tasks.values()),
        'no_application_does_not_prove_no_applicable_law':True}
    from consequences import compute as consequences
    result.update(consequences(snapshot,p,reviews,accepted,result))
    return result

def compact(p,a,c):
    return {'rule_coverage':c['rule_coverage'],'historical_comparisons':{i:{k:v for k,v in h.items() if k!='review'} for i,h in a.get('analogies',{}).items()},'tasks':{i:{'proposition':t['proposition'],'kind':t['kind'],'scope_id':t['scope_id'],
        'state':c['task_states'][i],'usable_report_sources':sorted({r for u,x in a['uses'].items() if x['task_id']==i and x['report_eligible'] for r in p['uses'][u]['refs']})} for i,t in p['tasks'].items()},
        'paths':c['paths'],'requests':c.get('requests',{}),'burdens':c.get('burdens',{}),'assumptions':c['assumptions'],'conditional_not_actual':c['conditional_not_actual'],'rules':{i:{k:v for k,v in row.items() if k not in ('raw_conditional_state',)} for i,row in c['rules'].items()},
        'scope_checks':a.get('scope_checks',{}),
        'limits':{'path_search_complete':c['search_complete'],'rule_coverage':c.get('rule_coverage',{}),'legal_approval':False}}

def mechanical_repair_questions(snapshot,p,accepted,check=None,review=None):
    """Route failed contracts to their dependencies without supplying answers."""
    import source_records as SR
    result=[{'repair_target':'SOURCE_RECORDS','question':g['question'],'refs':g['refs'],
        'basis':{'source_coverage_gap':g['source_id'],'failed_contracts':g['reasons']}}
        for g in p.get('source_record_coverage',{}).get('gaps',[])]
    for rid,row in accepted.get('source_records',{}).items():
        if row['report_eligible']:continue
        result.append({'repair_target':'SOURCE_RECORDS',
            'question':'Re-read this unqualified source record and its field-level findings. Resolve the source disagreement or retain it as unresolved; do not assume rejection proves the opposite fact.',
            'refs':p['source_records'][rid]['refs'],'basis':{'source_record_id':rid,'failed_contracts':row['reasons']}})
    report_scopes={t['scope_id'] for t in p['tasks'].values() if t.get('role','REPORT')=='REPORT'}
    for sid in report_scopes:
        checks=accepted.get('scope_checks',{}).get(sid,{})
        bad={part:row for part,row in checks.items() if row.get('decision')=='ACCEPT' and
             (not row['assessed_exact_declared_values'] or not row['has_source_witness'] or row.get('unsupported_years') or not row.get('event_relation_valid',True))}
        if bad:result.append({'repair_target':'SCOPES','question':'Reassess the declared scope from original passages; its purported acceptance lacks exact value/source support.',
            'refs':p['scopes'][sid]['refs'],'basis':{'scope_id':sid,'failed_contracts':bad}})
        mixed=[i for i in p['scopes'][sid]['properties'] if p['objects'][i].get('extent') in ('HETEROGENEOUS_COLLECTION','UNRESOLVED')]
        if mixed:result.append({'repair_target':'SCOPES','question':'Represent separately governed property members in separate scopes, or retain the unresolved collection as description only. Do not invent missing distinctions.',
            'refs':p['scopes'][sid]['refs'],'basis':{'scope_id':sid,'unpartitioned_objects':mixed}})
    for uid,row in accepted.get('uses',{}).items():
        a=row.get('review',{}).get('attribution',{})
        u=p['uses'][uid];task=p['tasks'][u['task_id']]
        if a.get('observed_owner')=='UNDECLARED':
            result.append({'repair_target':'OBJECTS','question':'Identify the source-mentioned speaker or deciding court missing from the object catalog. Preserve separate trial, appellate and reporting courts; do not substitute a nearby declared court.',
                'refs':p['uses'][uid]['refs'],'basis':{'use_id':uid,'observed_owner':'UNDECLARED'}})
        elif 'SOURCE_OWNER_UNQUALIFIED_OR_MISMATCH' in row.get('report_reasons',[]):
            target='TASKS' if task.get('source_owner') not in (None,'NONE','UNRESOLVED',u['source_owner']) else 'USES' if accepted['objects'].get(a.get('observed_owner'),False) else 'OBJECTS'
            result.append({'repair_target':target,'question':'Reassess the original source owner and the question addressing it. Use an already qualified source-mentioned owner by repairing USES; only a genuinely absent/unqualified identity requires OBJECTS. No correct owner is supplied by this routing.',
                'refs':u['refs'],'basis':{'use_id':uid,'failed_contracts':row['report_reasons']}})
        elif 'SOURCE_OWNER_OR_STATUS_NOT_INDEPENDENTLY_MATCHED' in row.get('report_reasons',[]) or 'SOURCE_EVENT_OR_BINDING_NOT_INDEPENDENTLY_MATCHED' in row.get('report_reasons',[]):
            result.append({'repair_target':'USES','question':'Reassess this source interpretation and its actor, property, event and source status from the cited passages; an ACCEPT token is insufficient when the observed values disagree.',
                'refs':p['uses'][uid]['refs'],'basis':{'use_id':uid,'failed_contracts':row['report_reasons']}})
    for uid,rec in (review or {}).get('source_records',{}).items():
        if uid in p.get('source_records',{}) and rec.get('observed_owner')=='UNDECLARED':
            result.append({'repair_target':'OBJECTS','question':'The independent final source review found a missing source-mentioned speaker/court. Reassess the object catalog from these original passages before rebuilding uses; do not substitute an existing court.',
                'refs':p['source_records'][uid]['refs'],'basis':{'source_record_id':uid,'final_observed_owner':'UNDECLARED'}})
    coverage=(review or {}).get('whole_source_coverage',{})
    for oid,row in coverage.get('inventory_check',{}).get('obligations',{}).items():
        if row['complete']:continue
        obligation=p['source_inventory']['obligations'][oid]
        target=coverage.get('obligations',{}).get(oid,{}).get('repair_target','USES')
        # Describing a known record is a different obligation from deciding its
        # ultimate legal effect. Missing descriptions return to source recovery.
        if obligation.get('answerability')=='KNOWN_RECORD':
            refs=set(obligation['refs'])
            source_gaps={g['source_id'] for g in p.get('source_record_coverage',{}).get('gaps',[])}
            represented=any(refs&set(r['refs']) and accepted.get('source_records',{}).get(rid,{}).get('report_eligible')
                for rid,r in p.get('source_records',{}).items())
            if not represented or refs&source_gaps:target='SOURCE_RECORDS'
            elif target=='NO_ALLOWED_REPAIR':target='USES'
        if target=='NO_ALLOWED_REPAIR':continue
        result.append({'repair_target':target,'question':obligation['question'],
            'refs':obligation['refs'],'basis':{'inventory_obligation':oid,'model_coverage':row['model_status']}})
    missing=coverage.get('inventory_check',{}).get('important_sources_without_obligation',[])
    if missing:result.append({'repair_target':'TASKS','question':'Reassess whether these allowed passages contain distinct important obligations omitted from the inventory.', 'refs':missing,'basis':'Important sources have no report obligation'})
    for failure in (check or {}).get('problems',[]):
        tid=failure.get('task_id')
        if tid not in p['tasks']:continue
        t=p['tasks'][tid];reasons=set(failure['reasons']);target=None
        if reasons & {'DERIVED_CONCLUSION_WITHOUT_QUALIFIED_PATH','REQUEST_CERTIFICATE_MISMATCH'}:
            target='TASKS' if t['rule_id']=='NONE' or t['kind']!='DERIVED' else 'RULE_MAPPING'
        if reasons & {'REPORT_USE_NOT_ACCEPTED','REPORT_CITATION_OUTSIDE_ACCEPTED_USES'} or any(x.startswith('FINAL_SOURCE_RECORD_BINDING_NOT_CONFIRMED:') for x in reasons):
            target='USES'
        if reasons & {'ATTRIBUTION_OWNER_DISAGREEMENT','REPORT_ATTRIBUTION_DIFFERS_FROM_ACCEPTED_SOURCE_USE','ATTRIBUTED_ASSESSED_OR_HYPOTHETICAL_CONTENT_PROMOTED_TO_FACT'}:
            target='TASKS'
        if target:
            refs=t['question_basis_refs'] or p['scopes'][t['scope_id']]['refs']
            if refs_valid(refs,snapshot,'CASE'):
                result.append({'repair_target':target,'question':'Reassess the upstream representation for this reported item using the original allowed record. Separate speakers and scopes; a prior ruling is not a new conclusion. If law or evidence is unavailable, retain that limitation.',
                    'refs':refs,'basis':{'task_id':tid,'failed_contracts':sorted(reasons)}})
    return result


def check_report(snapshot,p,report,review,accepted=None,computed=None,source_reviews=None):
    problems=[]
    if accepted is not None:
        from report_control import check_exact
        errors=check_exact(snapshot,p,source_reviews,accepted,computed,report) if source_reviews else ['MISSING_SOURCE_REVIEW_ENVELOPE']
        if errors:problems.append({'task_id':None,'reasons':errors})
    items=report['items'];seen={};included={i:x for i,x in items.items() if x['include']};obligations={}
    for tid,item in items.items():
        t=p['tasks'][tid];v=review['items'][tid];why=[]
        if item['include']:
            for segment in item.get('segments',[]):
                uid=segment.get('source_use_id')
                if not uid:continue
                rec=review.get('source_records',{}).get(uid,{})
                from source_records import review_conflicts
                if (review_conflicts(rec,snapshot) or not review_ok(rec,snapshot,'CASE') or rec.get('observed_owner')!=segment['source_owner'] or
                    rec.get('observed_status')!=segment['status'] or rec.get('observed_content_role')!=segment['content_role'] or
                    not set(segment['refs'])<=set(rec.get('refs',[])) or
                    not witness_quotes_valid(rec.get('witnesses',[]),snapshot,'CASE',rec.get('refs',[]))):
                    why.append('FINAL_SOURCE_RECORD_BINDING_NOT_CONFIRMED:'+uid)
            if not item['text'].strip() or not refs_valid(item['refs'],snapshot):why.append('EMPTY_OR_UNSOURCED_STATEMENT')
            if not substantive_report_text(item['text']):why.append('NON_SUBSTANTIVE_REPORT_TEXT')
            if not v.get('substantive_text'):why.append('REVIEW_FOUND_NO_SUBSTANTIVE_TEXT')
            key=digest({'scope':t['scope_id'],'owner':item.get('attributed_to'),'text':' '.join(item['text'].split()).casefold()})
            if key in seen:why.append('DUPLICATE_REPORT_STATEMENT:'+seen[key])
            seen[key]=tid
            if not review_ok(v,snapshot) or v['serious_error']:why.append('FINAL_SOURCE_REVIEW_NOT_ACCEPTED')
            if not set(item['refs'])<=set(v.get('refs',[])):why.append('FINAL_REVIEW_DID_NOT_COVER_ALL_CITATIONS')
            if v.get('error_types'):why.append('FINAL_REVIEW_IDENTIFIES_CONTENT_ERROR')
            if (v.get('error_types') or v.get('decision')=='REJECT') and v.get('revision_class')=='NO_CORRECTION_REQUIRED':why.append('REVIEW_REPAIR_CONFLICT')
            if not witness_quotes_valid(v.get('witnesses',[]),snapshot,refs=v.get('refs',[])):why.append('FINAL_REVIEW_WITHOUT_VERBATIM_WITNESS')
            if item.get('kind')=='ATTRIBUTED':
                if item.get('attributed_to') not in p['objects']:why.append('ATTRIBUTION_OWNER_MISSING_OR_UNRESOLVED')
                if item.get('attributed_to')!=v.get('source_owner'):why.append('ATTRIBUTION_OWNER_DISAGREEMENT')
                if t.get('source_owner') not in (None,'NONE','UNRESOLVED') and item.get('attributed_to')!=t['source_owner']:why.append('REPORT_OWNER_DIFFERS_FROM_ATOMIC_TASK')
            if v.get('content_role')=='LEGAL_CONCLUSION' and item['kind'] not in ('DERIVED','ATTRIBUTED','CONDITIONAL','CONTROLLED_RECORDS'):why.append('LEGAL_EFFECT_MISCLASSIFIED_AS_RECORD_FACT')
            history_refs={r for r in item['refs'] if snapshot['directory'].get(r,{}).get('domain')=='HISTORY'}
            if history_refs and (item['kind']!='ANALOGY' or item['consequence_scope']!='DESCRIPTION'):
                why.append('HISTORY_PROMOTED_BEYOND_COMPARATIVE_DESCRIPTION')
            if item['kind']=='ANALOGY' and (not history_refs or not any(snapshot['directory'].get(r,{}).get('domain')=='CASE' for r in item['refs'])):
                why.append('COMPARISON_REQUIRES_BOTH_HISTORY_AND_CURRENT_SOURCES')
            if accepted is not None:
                available={i for i,x in accepted['uses'].items() if x['task_id']==tid and x['report_eligible']}
                if item['kind']=='ANALOGY':
                    if item['consequence_scope']!='DESCRIPTION' or not any(accepted.get('analogies',{}).get(i,{}).get('report_eligible') and accepted['analogies'][i]['task_id']==tid for i in item['support_ids']):why.append('ANALOGY_NOT_SOURCE_REVIEWED_OR_PROMOTED')
                    qualified=[accepted['analogies'][i] for i in item['support_ids'] if i in accepted.get('analogies',{}) and accepted['analogies'][i]['report_eligible'] and accepted['analogies'][i]['task_id']==tid]
                    if history_refs-set(r for x in qualified for r in x['history_refs']):why.append('HISTORY_CITATION_OUTSIDE_ACCEPTED_COMPARISON')
                    if qualified and not any(set(x['case_refs'])&set(item['refs']) for x in qualified):why.append('COMPARISON_CURRENT_BINDING_NOT_CITED')
                if item['kind'] in ('FACTUAL','ATTRIBUTED') and not set(item['support_ids'])&available:why.append('REPORT_USE_NOT_ACCEPTED')
                if item['kind'] in ('FACTUAL','ATTRIBUTED'):
                    selected=set(item['support_ids'])&available
                    reviewed_case_refs={r for uid in selected for r in p['uses'][uid]['refs']}
                    case_refs={r for r in item['refs'] if snapshot['directory'].get(r,{}).get('domain')=='CASE'}
                    if case_refs-reviewed_case_refs:why.append('REPORT_CITATION_OUTSIDE_ACCEPTED_USES')
                    if item['kind']=='ATTRIBUTED' and (not accepted['objects'].get(item.get('attributed_to')) or
                        any(p['uses'][uid].get('source_owner')!=item.get('attributed_to') for uid in selected)):
                        why.append('REPORT_ATTRIBUTION_DIFFERS_FROM_ACCEPTED_SOURCE_USE')
                    if item['kind']=='FACTUAL' and any(p['uses'][uid].get('content_role')!='OBSERVATION' or
                        p['uses'][uid]['status'] in ('PARTY_CLAIM','HYPOTHETICAL','LIMITATION') for uid in selected):
                        why.append('ATTRIBUTED_ASSESSED_OR_HYPOTHETICAL_CONTENT_PROMOTED_TO_FACT')
                if item['kind']=='FACTUAL' and t['kind']=='ATTRIBUTION':why.append('ATTRIBUTED_CONTENT_PROMOTION')
                if item['kind']=='DERIVED':
                    if item['consequence_scope']=='WHOLE_CASE':why.append('NO_WHOLE_CASE_OUTCOME_FROM_LOCAL_REQUEST')
                    paths=[computed['paths'][i] for i in item['support_ids'] if i in computed['paths'] and computed['paths'][i]['task_id']==tid]
                    if item['consequence_scope'] not in ('REQUEST','REMEDY') and (not paths or any(x['state']!='CONDITIONS_MET_IN_DECLARED_SCOPE' for x in paths)):why.append('DERIVED_CONCLUSION_WITHOUT_QUALIFIED_PATH')
                if item['consequence_scope'] in ('REQUEST','REMEDY') and item['kind'] not in ('ATTRIBUTED',):
                    certs=[computed.get('requests',{}).get(i) for i in item['support_ids'] if i in computed.get('requests',{})]
                    certs=[x for x in certs if x['task_id']==tid and x['scope_id']==t['scope_id'] and x['level']==item['consequence_scope']]
                    if not certs or any(x['outcome']!=item['outcome'] for x in certs):why.append('REQUEST_CERTIFICATE_MISMATCH')
                    if item['kind']=='DERIVED' and (item['outcome']=='UNRESOLVED' or any(x['conditional'] for x in certs)):why.append('UNRESOLVED_OR_HYPOTHETICAL_NOT_ACTUAL_RELIEF')
                if computed.get('conditional_not_actual') and (tid in computed.get('assumptions',{}) or item['kind']=='DERIVED'):
                    if item['kind']!='CONDITIONAL':why.append('HYPOTHESIS_PROMOTED_TO_FACT')
        if t['importance']=='IMPORTANT':
            links=item.get('also_covered_by',[])
            linked=bool(links) and all(k in items and items[k]['include'] and bool(items[k].get('segments')) for k in links)
            obligations[tid]=(item['include'] or linked) and not why and v['important_content_complete'] and review_ok(v,snapshot) and not v.get('serious_error') and not v.get('error_types')
        if why:problems.append({'task_id':tid,'reasons':why})
    # Historical comparisons have their own optional report addresses. They cannot
    # replace a required current-case finding, and omission needs an explicit reason.
    comparison_decisions={}
    for hid,h in p.get('analogies',{}).items():
        item=report.get('comparisons',{}).get(hid);v=review.get('comparisons',{}).get(hid,{})
        why=[]
        if item is None:
            why.append('COMPARISON_DISPOSITION_MISSING')
        elif item['include']:
            if item['report_item_id'] not in __import__('report_control').comparison_routes(p,h):why.append('COMPARISON_REPORT_DESTINATION_ERROR')
            if item['disposition']!='USED' or not substantive_report_text(item['text']):why.append('COMPARISON_DISPOSITION_CONFLICT')
            if not v.get('substantive_text'):why.append('REVIEW_FOUND_NO_SUBSTANTIVE_TEXT')
            if not review_ok(v,snapshot) or v.get('serious_error') or v.get('error_types'):why.append('COMPARISON_FINAL_REVIEW_NOT_ACCEPTED')
            if not set(item['refs'])<=set(v.get('refs',[])):why.append('COMPARISON_FINAL_REVIEW_DID_NOT_COVER_ALL_CITATIONS')
            if not witness_quotes_valid(v.get('witnesses',[]),snapshot,refs=v.get('refs',[])):why.append('COMPARISON_REVIEW_WITHOUT_VERBATIM_WITNESS')
            if not witness_quotes_valid(v.get('history_witnesses',[]),snapshot,'HISTORY',h['history_refs']):why.append('COMPARISON_REVIEW_WITHOUT_HISTORY_WITNESS')
            if not witness_quotes_valid(v.get('case_witnesses',[]),snapshot,'CASE',h['case_refs']):why.append('COMPARISON_REVIEW_WITHOUT_CASE_WITNESS')
            refs=set(item['refs']);allowed=set(h['history_refs']+h['case_refs']+h['authority_refs'])
            if not refs_valid(item['refs'],snapshot) or refs-allowed:why.append('COMPARISON_CITATION_OUTSIDE_PROPOSAL')
            if not refs&set(h['history_refs']) or not refs&set(h['case_refs']):why.append('COMPARISON_REQUIRES_BOTH_RECORDS')
            if v.get('content_role')!='COMPARISON':why.append('COMPARISON_PROMOTED_TO_CURRENT_FACT_OR_LAW')
            if accepted is not None and not accepted.get('analogies',{}).get(hid,{}).get('report_eligible'):why.append('COMPARISON_NOT_SOURCE_REVIEWED')
        elif item['disposition']=='USED' or not item['reason'].strip():
            why.append('OMITTED_COMPARISON_HAS_TEXT_OR_NO_REASON')
        elif v.get('decision')=='REJECT' or v.get('serious_error') or v.get('error_types') or v.get('important_content_complete') is False:
            why.append('COMPARISON_OMISSION_REJECTED_BY_SOURCE_REVIEW')
        comparison_decisions[hid]={'included':bool(item and item['include']),
            'disposition':item['disposition'] if item else 'MISSING',
            'reason':item['reason'] if item else None,'problems':why,
            'omission_is_not_automatically_an_error':True}
        if why:problems.append({'task_id':h['task_id'],'comparison_id':hid,'reasons':why})
    # V20 checks the actual final report, never an incomplete intermediate pack.
    frame={'actors':[{'id':i,'kind':o['kind'] if o['kind'] in ('PARTY','COURT') else 'OTHER'} for i,o in p['objects'].items() if o['kind']!='PROPERTY'],
        'properties':[{'id':i} for i,o in p['objects'].items() if o['kind']=='PROPERTY'],'events':[]}
    records=[]
    pack_items=dict(included)
    # Expand navigation links for the legacy four-section checker only. The
    # delivered report remains deduplicated; no new assertion is manufactured.
    for tid,item in items.items():
        linked=[items[k] for k in item.get('also_covered_by',[]) if k in included]
        if tid not in pack_items and linked:
            pack_items[tid]={**item,'text':'\n'.join(r['text'] for r in linked),'refs':list(dict.fromkeys(ref for r in linked for ref in r['refs']))}
    for tid,item in pack_items.items():
        scope=p['scopes'][p['tasks'][tid]['scope_id']]
        records.append({'id':f'S{len(records)+1:02d}','section':item['section'],'text':item['text'],'status':'ATTRIBUTED' if item['kind']=='CONTROLLED_RECORDS' else item['kind'],'stage':scope['stage'],
            'actor_ids':scope['actors'],'property_ids':scope['properties'],'event_ids':[],'role_bindings':[],
            'refs':[i for i in item['refs'] if snapshot['directory'].get(i,{}).get('domain')=='CASE']})
    case={'segments':[{'id':i,'text':s['text']} for i,s in snapshot['directory'].items() if s['domain']=='CASE']}
    try:check_pack(case,frame,{'records':records});pack={'status':'STRUCTURAL_PASS_NOT_SEMANTIC_APPROVAL'}
    except ValueError as exc:pack={'status':'STRUCTURAL_REJECTION','reason':str(exc)}
    coverage=review['whole_source_coverage'];important_omissions=actionable_omissions(coverage,snapshot)
    for oid,result in coverage.get('inventory_check',{}).get('obligations',{}).items():
        if not result['complete']:
            tids=[i for i,t in p['tasks'].items() if oid in t.get('obligation_ids',[])]
            problems.append({'task_id':tids[0] if tids else None,'obligation_id':oid,'reasons':['SOURCE_INVENTORY_COVERAGE_INCOMPLETE']})
    if coverage.get('inventory_check',{}).get('important_sources_without_obligation'):
        problems.append({'task_id':None,'reasons':['IMPORTANT_SOURCE_WITHOUT_REPORT_OBLIGATION']})
    if not coverage_consistent(coverage,snapshot):problems.append({'task_id':None,'reasons':['COVERAGE_CLASSIFICATION_INCONSISTENT']})
    import source_records as SR
    if 'source_record_coverage' in p:
        sr_reviews=(source_reviews or {}).get('values',{}).get('source_records',{})
        gaps=SR.coverage_gaps(snapshot,p['source_records'],sr_reviews,p['source_original_reading'],p['source_record_coverage'])
        if gaps:problems.append({'task_id':None,'reasons':['SOURCE_RECORD_COVERAGE_UNRESOLVED'],'source_ids':[g['source_id'] for g in gaps]})
    passed=bool(included) and bool(obligations) and all(obligations.values()) and not problems and coverage['complete'] and not important_omissions and pack['status']=='STRUCTURAL_PASS_NOT_SEMANTIC_APPROVAL'
    return {'report_hash':digest(report),'internal_pass':passed,'problems':problems,'important_obligations':obligations,
        'whole_source_coverage':coverage,'v20_final_pack':pack,'candidate_preserved':True,
        'comparison_decisions':comparison_decisions,
        'quality_score':None,'independent_evaluation':'PENDING','legal_approval':False}
