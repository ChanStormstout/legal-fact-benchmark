"""2013 Alternatingly Normalized CO-HITS; scores are not truth probabilities."""
import math

def project(test_ids, instance_ids, links):
    ti={v:i for i,v in enumerate(test_ids)};fi={v:i for i,v in enumerate(instance_ids)}
    matrix=[[0.0]*len(fi) for _ in ti]; pairs={}; omitted=[]
    for link in links:
        if link['test_id'] not in ti or link['instance_id'] not in fi:raise ValueError('invalid ANCO endpoint')
        key=(link['test_id'],link['instance_id']); sign=link['direction']
        if sign not in ('SUPPORT','OPPOSE'):
            omitted.append(dict(link,reason='UNKNOWN_OR_IRRELEVANT_NOT_NEGATIVE'));continue
        pairs.setdefault(key,set()).add(sign)
    conflicts=[]
    for (test,fact),signs in pairs.items():
        matrix[ti[test]][fi[fact]]=float(('SUPPORT' in signs)-('OPPOSE' in signs))
        if len(signs)==2:conflicts.append({'test_id':test,'instance_id':fact,'reason':'NUMERIC_CANCELLATION_NOT_NO_EVIDENCE'})
    return {'matrix':matrix,'test_ids':test_ids,'instance_ids':instance_ids,'conflicts':conflicts,'non_numeric_links':omitted}

def anco(matrix, n_columns=None, max_iterations=1000, tolerance=1e-8):
    a=[[float(v) for v in row] for row in matrix];n=len(a);m=len(a[0]) if a else (n_columns or 0)
    if any(len(r)!=m for r in a):raise ValueError('ragged matrix')
    if any(not math.isfinite(v) for r in a for v in r):return {'status':'NON_FINITE_INPUT','x':None,'y':None}
    dr=[sum(abs(v) for v in r) for r in a];dc=[sum(abs(a[i][j]) for i in range(n)) for j in range(m)]
    x=[1.0]*n;y=[1.0]*m;trace=[];converged=False
    for step in range(1,max_iterations+1):
        nx=[sum(a[i][j]*y[j] for j in range(m))/dr[i] if dr[i] else 0.0 for i in range(n)]
        ny=[sum(a[i][j]*nx[i] for i in range(n))/dc[j] if dc[j] else 0.0 for j in range(m)]
        if not all(math.isfinite(v) for v in nx+ny):return {'status':'NON_FINITE_ITERATE','iteration':step,'x':None,'y':None,'trace':trace}
        delta=max([abs(v-w) for v,w in zip(nx+ny,x+y)]+[0.0]);x,y=nx,ny
        trace.append({'iteration':step,'delta':delta})
        if delta<=tolerance:converged=True;break
    return {'status':'CONVERGED' if converged else 'NON_CONVERGED','x':x,'y':y,'trace':trace,
            'isolated_tests':[i for i,v in enumerate(dr) if not v],'isolated_instances':[j for j,v in enumerate(dc) if not v],
            'degenerate_test_scores':len(set(round(v,8) for v in x))<=1,'all_zero':all(abs(v)<=tolerance for v in x+y),
            'interpretation':'DETERMINISTIC_PROPOSAL_FEATURE_NOT_LEGAL_PROBABILITY'}
