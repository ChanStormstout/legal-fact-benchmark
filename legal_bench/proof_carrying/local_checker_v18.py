"""Independent recomputation of V18 declared conditional rule traces.
Does not import proposer composition, labels, model or reference data.
Not legal approval and not a semantic source verifier.
"""
def check(rules,analysis):
    directory={r['id']:r for r in rules};judgments={j['id']:j for j in analysis['premise_judgments']};out=[]
    for trace in analysis['conditional_rules']:
        r=directory.get(trace['rule_id']);errors=[];values=[];objects={}
        if r is None:errors.append('RULE_NOT_FOUND')
        elif len(trace['inputs'])!=len(r['premises']):errors.append('INPUT_ARITY')
        else:
            for p,key in zip(r['premises'],trace['inputs']):
                j=judgments.get(key);v='UNKNOWN'
                if key is not None and (j is None or j['premise']!=p['id']):errors.append('DEPENDENCY_TYPE')
                if j:
                    v=j['conditional_state']
                    for role,obj in j['binding'].items():
                        if role in objects and objects[role]!=obj:errors.append('OBJECT_MISMATCH')
                        objects[role]=obj
                    if j['errors'] and v!='UNKNOWN':errors.append('INVALID_PREMISE_ACCEPTED')
                    if j['necessary_limits'] and v!='UNKNOWN':errors.append('NECESSARY_LIMIT_BYPASSED')
                if p.get('expected')=='FALSE':v='FALSE' if v=='TRUE' else 'TRUE' if v=='FALSE' else v
                values.append(v)
            op=r['operator']
            if op=='ALL':state='FALSE' if any(v=='FALSE' for v in values) else 'CONFLICTED' if any(v=='CONFLICTED' for v in values) else 'TRUE' if values and all(v=='TRUE' for v in values) else 'UNKNOWN'
            elif op=='ANY':state='TRUE' if any(v=='TRUE' for v in values) else 'CONFLICTED' if any(v=='CONFLICTED' for v in values) else 'FALSE' if values and all(v=='FALSE' for v in values) else 'UNKNOWN'
            else:state='UNKNOWN'
            if r.get('exceptions') and state=='TRUE':state='UNKNOWN'
            if trace['conditional_result']!=state:errors.append('RESULT_MISMATCH')
            if trace['slot_states']!=values:errors.append('SLOT_STATE_MISMATCH')
            if trace['binding']!=objects:errors.append('BINDING_MISMATCH')
        out.append({'rule_id':trace['rule_id'],'inputs':trace['inputs'],'status':'REJECTED_TRACE' if errors else 'CONDITIONAL_TRACE_RECOMPUTED',
                    'errors':errors,'semantic_approval':False,'legal_approval':False})
    return {'status':'OK','traces':out,'scope':'DECLARED_CONDITIONAL_COMBINATION_ONLY; NO_SOURCE_SEMANTIC_PROOF'}
