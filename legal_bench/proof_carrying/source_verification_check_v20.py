"""Independent application invariants; no semantic or legal approval."""
import copy

def check(p,q,result,rules):
    failures=[];labels=result['predictions']
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
                        value=labels[key]
                        for ev in a['records']:
                            if labels.get(f'{name}/{pid}/{ev}')!='SUPPORTED':value='UNRESOLVED'
                        expected['self_assessment']=value
                    elif labels[key]!='SUPPORTED':expected.update(state='UNKNOWN',complete=False)
                    if expected!=b:failures.append('UNAUTHORIZED_OR_MISSING_LOCAL_TRANSFORMATION:'+key)
        expected_links=[link for i,link in enumerate(source['object_links'],1) if labels.get(f'{name}/LINK:{i}')=='SUPPORTED']
        if target['object_links']!=expected_links:failures.append('IDENTITY_APPLICATION')
        if target['coverage_limits']!=source['coverage_limits']:failures.append('COVERAGE_LIMITS_CHANGED')
    for route in result['audit']['conditional_rules']:
        rule=next((r for r in rules if r['id']==route.get('rule_id')),None)
        if rule and rule.get('unmapped_shared_variable_contract') and route.get('conditional_result')!='UNKNOWN':failures.append('UNDECLARED_JOIN_EXECUTED')
    if result.get('semantic_approval') or result.get('legal_approval'):failures.append('SELF_APPROVAL')
    return {'status':'REJECTED' if failures else 'OK','errors':failures,'scope':'APPLICATION_FIDELITY_NOT_NATURAL_LANGUAGE_PROOF'}
