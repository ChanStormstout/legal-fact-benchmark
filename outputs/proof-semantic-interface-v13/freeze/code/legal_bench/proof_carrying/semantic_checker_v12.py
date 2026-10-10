"""Independent recomputation of proposed routes, with unverified model semantics explicit.
Does not import search, reference, label or ranker code. Not a legal certifier.
"""
from .grounding_v9 import source_match
from .contracts import content_hash

def check(snapshot,search):
    facts=snapshot['premises'];rules=snapshot['rules'];sources=snapshot['sources'];uses=snapshot.get('model_uses',{})
    steps={s['id']:s for s in search['steps']};cache={}
    def visit(sid,active):
        if sid in active:return {'state':None,'errors':['CYCLE'],'assumptions':[]}
        if sid in cache:return cache[sid]
        st=steps.get(sid)
        if st is None:return {'state':None,'errors':['DANGLING_STEP'],'assumptions':[]}
        r=rules.get(st['rule_ref']);errs=[];pending=[];assumptions=[];states={}
        if r is None:return {'state':None,'errors':['RULE_VERSION_MISSING'],'assumptions':[]}
        rc=snapshot['contracts'].get(st['rule_ref'],{});mapping=rc.get('slot_variables',{})
        if st['rule_ref'] != r['id']+'@'+str(r['version']):errs.append('RULE_VERSION_MISMATCH')
        if rc.get('rule_hash') != content_hash(r):errs.append('RULE_CONTRACT_HASH_MISMATCH')
        bp={x['role']:x['entity'] for x in st['bindings']};inputs={x['slot']:x for x in st['inputs']}
        if len(inputs)!=len(st['inputs']):errs.append('DUPLICATE_SLOT')
        ruleloc=source_match(r,sources)
        if ruleloc['error']:errs.append('RULE_SOURCE:'+ruleloc['error'])
        required={s['name']:s for s in r['slots']}
        if set(inputs)-set(required):errs.append('EXTRA_SLOT')
        for name,s in required.items():
            x=inputs.get(name);v='UNKNOWN'
            if not x or x['kind']=='MISSING':pending.append('MISSING:'+name)
            elif x['kind']=='STEP':
                child=steps.get(x['id']);dep=visit(x['id'],active|{sid});assumptions+=dep['assumptions']
                if dep['errors']:pending.append('INVALID_ALTERNATIVE:'+name)
                elif child and rules[child['rule_ref']]['conclusion_predicate']!=s['predicate']:errs.append('DEPENDENCY_TYPE:'+name)
                else:v=dep['state'] or 'UNKNOWN'
                b={z['role']:z['entity'] for z in child['bindings']} if child else {}
                for role,var in mapping.get(name,{}).items():
                    if not b.get(role) or not bp.get(var):pending.append('DEPENDENCY_OBJECT_UNKNOWN:'+name);v='UNKNOWN'
                    elif b[role]!=bp[var]:errs.append('DEPENDENCY_OBJECT_MISMATCH:'+name)
            elif x['kind'] in ('PREMISE','BUNDLE'):
                u=uses.get(st['candidate_id']+'::'+name);bad=[]
                evidence_ids=x.get('evidence_ids',[x['id']]);bundle_records=[]
                if not evidence_ids:bad.append('EMPTY_EVIDENCE_BUNDLE')
                for evidence_id in evidence_ids:
                    p=facts.get(evidence_id)
                    if not p:bad.append('MISSING_RECORD:'+evidence_id);continue
                    bundle_records.append(p)
                    loc=source_match(p,sources)
                    if loc['error']:bad.append('SOURCE:'+loc['error'])
                    if p.get('statement_status') not in s['allowed_statuses']:bad.append('STATEMENT_STATUS')
                    if p.get('statement_status') in ['LEGAL_RULE','TARGET_DISPOSITION']:bad.append('NONFACT')
                    if not p.get('refs'):bad.append('SOURCE_MISSING')
                    if p.get('refs') and all(sources.get(k,{}).get('document_role')!='TARGET' for k in p['refs']):bad.append('FOREIGN_FACT')
                    if p.get('refs') and all(sources.get(k,{}).get('role')=='DISPOSITION_ONLY' for k in p['refs']):bad.append('CIRCULAR_DISPOSITION_PREMISE')
                    pb={z['role']:z['entity'] for z in p.get('bindings',[])}
                    for role,var in mapping.get(name,{}).items():
                        if not pb.get(role) or not bp.get(var):pending.append('OBJECT_UNKNOWN:'+name);bad.append('UNESTABLISHED_BINDING')
                        elif pb[role]!=bp[var]:bad.append('OBJECT_MISMATCH')
                    if s.get('time_required'):
                        if not p.get('time_scope') or not st.get('time_scope'):bad.append('TIME_UNKNOWN')
                        elif p['time_scope']!=st['time_scope']:bad.append('TIME_MISMATCH')
                    for field in ('court_level','stage','jurisdiction'):
                        if s.get(field) and p.get(field)!=s[field]:bad.append('SCOPE_MISMATCH:'+field)
                coverage=snapshot.get('coverage_contracts',{}).get(st['rule_ref'],{}).get(name,{})
                if coverage.get('mode')=='UNRESOLVED':bad.append('PREMISE_COVERAGE_UNRESOLVED')
                if coverage.get('required_components'):
                    # A named predicate is not a certificate of full compound coverage.
                    required_components=coverage['required_components']
                    supplied=(u or {}).get('component_coverage',[])
                    covered={content_hash(z['component']) for z in supplied if z.get('basis') and 'component' in z}
                    if any(content_hash(z) not in covered for z in required_components):bad.append('COMPOUND_COVERAGE_UNESTABLISHED')
                if bad:pending.extend(name+':'+z for z in bad)
                elif not u or u.get('label')!='USABLE':pending.append('MODEL_USE_UNRESOLVED_OR_REJECTED:'+name)
                else:
                    # Even an accepted use score cannot supply a missing whole-premise judgment.
                    v=u.get('premise_state','UNKNOWN')
                    if v not in ['TRUE','FALSE','UNKNOWN','CONFLICTED']:v='UNKNOWN'
                    if not u.get('premise_judgment_basis'):v='UNKNOWN';pending.append('NO_WHOLE_PREMISE_JUDGMENT:'+name)
                    assumptions.append({'use':st['candidate_id']+'::'+name,'facts':evidence_ids,'status':'MODEL_SEMANTICS_UNVERIFIED','premise_state':v,'basis':u.get('premise_judgment_basis')})
            else:errs.append('INPUT_KIND:'+name)
            if s.get('expected','TRUE')=='FALSE':v={'TRUE':'FALSE','FALSE':'TRUE'}.get(v,v)
            states[name]=v
        exc=set(r.get('exception_slots',[]));normal=[v for k,v in states.items() if k not in exc];exceptions=[states.get(k,'UNKNOWN') for k in exc]
        if errs:state=None
        elif r['operator']=='OPEN_TEXT':state='UNKNOWN';pending.append('OPEN_LEGAL_INTERPRETATION_NOT_EXECUTED')
        elif not normal:state='UNKNOWN';pending.append('NO_ANTECEDENTS')
        elif r['operator']=='ALL':state='FALSE' if 'FALSE' in normal else 'CONFLICTED' if 'CONFLICTED' in normal else 'UNKNOWN' if 'UNKNOWN' in normal else 'TRUE'
        elif r['operator']=='ANY':state='TRUE' if 'TRUE' in normal else 'CONFLICTED' if 'CONFLICTED' in normal else 'UNKNOWN' if 'UNKNOWN' in normal else 'FALSE'
        else:state=None;errs.append('UNSUPPORTED_OPERATOR')
        if state is not None:
            if 'TRUE' in exceptions:state='FALSE'
            elif any(v in ['UNKNOWN','CONFLICTED'] for v in exceptions):state='UNKNOWN';pending.append('EXCEPTION_UNRESOLVED')
        cache[sid]={'state':state,'errors':errs,'pending':pending,'assumptions':assumptions,'legal_approval':False};return cache[sid]
    requests=[]
    for item in search['requests']:
        rows=[{'step':sid,**visit(sid,set())} for sid in item['root_steps']];vs={z['state'] for z in rows if not z['errors']}
        state='CONFLICTED' if 'CONFLICTED' in vs or {'TRUE','FALSE'}<=vs else 'TRUE' if 'TRUE' in vs else 'UNKNOWN'
        requests.append({'id':item['request']['id'],'answer':state,'scope':'CONDITIONAL_ON_UNVERIFIED_MODEL_SEMANTICS','search_status':item['search_status'],'alternatives':rows,'formal_status':'NOT_LEGALLY_APPROVED'})
    return {'run_status':'OK','requests':requests,'steps':cache,'all_opposition':snapshot.get('relations',[]),'all_limitations':snapshot.get('coverage_limits',[]),'reference_read':False,'semantic_verified':False}
