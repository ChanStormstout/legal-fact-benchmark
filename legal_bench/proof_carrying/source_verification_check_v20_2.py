"""Independent application invariants; no semantic or legal approval."""
import copy
import re

def check(p,q,result,rules,execution=None):
    failures=[];labels=result['predictions']
    expected_ids=set()
    for origin,raw in [('P',p),('Q',q['supplement'])]:
        for pid,unit in raw['analyses'].items():
            expected_ids.update(f'{origin}/{pid}/EV:{i}' for i in range(1,len(unit['records'])+1))
            for coll,prefix in [('uses','USE'),('judgments','J')]:
                for i,row in enumerate(unit[coll],1):
                    base=f'{origin}/{pid}/{prefix}:{i}';expected_ids.add(base)
                    expected_ids.update(base+'/ROLE:'+role for role,ref in row['role_objects'].items() if ref!='UNMAPPED')
        expected_ids.update(f'{origin}/LINK:{i}' for i in range(1,len(raw['object_links'])+1))
    if set(labels)!=expected_ids:failures.append('PREDICTION_COVERAGE')
    origin=result.get('decision_origin')
    allowed=('SUPPORTED','UNSUPPORTED','UNRESOLVED',None) if origin=='Q' else ('SUPPORTED','UNSUPPORTED','UNRESOLVED')
    if origin not in ('Q','LEARNER') or any(v not in allowed for v in labels.values()):failures.append('PREDICTION_STATE_CONTRACT')
    candidates=result.get('pool',{}).get('candidates',[])
    if len(candidates)!=len(expected_ids) or {d['id'] for d in candidates}!=expected_ids:failures.append('DECLARATION_DIRECTORY_FIDELITY')
    states=[d.get('verification_state') for d in candidates]
    expected_coverage={'expected':len(candidates),'reviewed':states.count('REVIEWED'),'not_reviewed':states.count('NOT_REVIEWED'),
                      'quarantined':states.count('QUARANTINED'),
                      'status':'NO_DECLARATIONS' if not candidates else 'COMPLETE' if states.count('REVIEWED')==len(candidates) else 'PARTIAL',
                      'explicit_unresolved':sum(d.get('proposed_label')=='UNRESOLVED' for d in candidates),'not_a_semantic_accuracy_metric':True}
    if result.get('pool',{}).get('verification_coverage')!=expected_coverage:failures.append('VERIFICATION_COVERAGE_FIDELITY')
    for name,source in [('P',p),('Q',q['supplement'])]:
        target=result['applied_proposals'][name]
        if set(source['analyses'])!=set(target['analyses']):failures.append('ANALYSIS_COVERAGE')
        for pid,u in source['analyses'].items():
            v=target['analyses'].get(pid,{})
            for field in ('records','objects','limits','analysis_status'):
                if u[field]!=v.get(field):failures.append('RAW_CONTENT_CHANGED:'+field)
            for coll,prefix in [('uses','USE'),('judgments','J')]:
                if len(u[coll])!=len(v.get(coll,[])):failures.append('ROW_COUNT');continue
                for i,(a,b) in enumerate(zip(u[coll],v[coll]),1):
                    key=f'{name}/{pid}/{prefix}:{i}';expected=copy.deepcopy(a)
                    for role,ref in a['role_objects'].items():
                        if ref!='UNMAPPED' and labels.get(key+'/ROLE:'+role)!='SUPPORTED':expected['role_objects'][role]='UNMAPPED'
                    if prefix=='USE':
                        value=labels.get(key) or 'UNRESOLVED'
                        for ev in a['records']:
                            match=re.fullmatch(r'EV:([1-9][0-9]*)',ev)
                            if not match or int(match[1])>len(u['records']) or labels.get(f'{name}/{pid}/{ev}')!='SUPPORTED':value='UNRESOLVED'
                        expected['self_assessment']=value
                    elif labels.get(key)!='SUPPORTED':expected.update(state='UNKNOWN',complete=False)
                    if expected!=b:failures.append('UNAUTHORIZED_OR_MISSING_LOCAL_TRANSFORMATION:'+key)
        expected_links=[link for i,link in enumerate(source['object_links'],1) if labels.get(f'{name}/LINK:{i}')=='SUPPORTED']
        if target['object_links']!=expected_links:failures.append('IDENTITY_APPLICATION')
        if target['coverage_limits']!=source['coverage_limits']:failures.append('COVERAGE_LIMITS_CHANGED')
    for route in result['audit']['conditional_rules']:
        rule=next((r for r in rules if r['id']==route.get('rule_id')),None)
        if rule and rule.get('unmapped_shared_variable_contract') and route.get('conditional_result')!='UNKNOWN':failures.append('UNDECLARED_JOIN_EXECUTED')
    if result.get('semantic_approval') or result.get('legal_approval'):failures.append('SELF_APPROVAL')
    if result.get('execution',{})!=(execution or {}):failures.append('EXECUTION_CONTEXT_FIDELITY')
    return {'status':'REJECTED' if failures else 'OK','errors':failures,'scope':'APPLICATION_FIDELITY_NOT_NATURAL_LANGUAGE_PROOF'}
