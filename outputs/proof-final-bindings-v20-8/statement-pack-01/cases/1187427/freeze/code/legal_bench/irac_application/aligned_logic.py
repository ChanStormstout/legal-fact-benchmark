"""Conservative explicit combinations, evaluated only within one witnessed binding."""
STATES={'SUPPORTED','REFUTED','UNRESOLVED','UNSUPPORTED'}
def evaluate(expr,tests,definitions=None,seen=()):
    definitions=definitions or {};op=expr['op']
    if not expr.get('source_refs'):return {'status':'UNSUPPORTED','reason':'COMBINATION_WITHOUT_SOURCE','trace':[]}
    if op=='REF':
        key=expr['id']
        if key in seen:raise ValueError('cyclic legal expression')
        if key in definitions:return evaluate(definitions[key],tests,definitions,seen+(key,))
        item=tests.get(key,{'status':'UNRESOLVED','reason':'TEST_NOT_EVALUATED'})
        if item['status'] not in STATES:raise ValueError('invalid state')
        return dict(item,trace=[key])
    if op=='UNSUPPORTED':return {'status':'UNSUPPORTED','reason':expr['reason'],'trace':[]}
    if op=='NOT':
        r=evaluate(expr['arg'],tests,definitions,seen)
        return dict(r,status={'SUPPORTED':'REFUTED','REFUTED':'SUPPORTED'}.get(r['status'],r['status']))
    if op=='EXCEPT':
        return evaluate(dict(op='AND',args=[expr['base'],dict(op='NOT',arg=expr['exception'],source_refs=expr['source_refs'])],source_refs=expr['source_refs']),tests,definitions,seen)
    if op not in ('AND','OR') or not expr.get('args'):return {'status':'UNSUPPORTED','reason':'UNIMPLEMENTED_EXPRESSION','trace':[]}
    results=[evaluate(e,tests,definitions,seen) for e in expr['args']];s=[r['status'] for r in results]
    if op=='AND':status='REFUTED' if 'REFUTED' in s else 'SUPPORTED' if all(v=='SUPPORTED' for v in s) else 'UNSUPPORTED' if 'UNSUPPORTED' in s else 'UNRESOLVED'
    else:status='SUPPORTED' if 'SUPPORTED' in s else 'REFUTED' if all(v=='REFUTED' for v in s) else 'UNSUPPORTED' if 'UNSUPPORTED' in s else 'UNRESOLVED'
    return {'status':status,'trace':results,'interpretation':'CONDITIONAL_ON_MODEL_TEST_STATES_AND_BINDING'}

def combine_bound(expr,bindings,definitions=None,bindings_complete=False):
    rows=[]
    for b in bindings:
        if not b.get('binding_source_refs') or not b.get('identity_checks_complete'):
            rows.append({'binding_id':b.get('binding_id'),'status':'UNRESOLVED','reason':'BINDING_NOT_ESTABLISHED'});continue
        rows.append(dict(evaluate(expr,b['tests'],definitions),binding_id=b['binding_id']))
    if any(r['status']=='SUPPORTED' for r in rows):status='SUPPORTED'
    elif any(r['status']=='UNRESOLVED' for r in rows) or not rows:status='UNRESOLVED'
    elif any(r['status']=='UNSUPPORTED' for r in rows):status='UNSUPPORTED'
    else:status='REFUTED' if bindings_complete else 'UNRESOLVED'
    return {'status':status,'combinations':rows,'scope':'ONLY_ENUMERATED_BINDINGS; DOES_NOT_PROVE_GLOBAL_ABSENCE','burden_failure_inferred':False}
