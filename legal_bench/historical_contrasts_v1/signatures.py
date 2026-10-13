"""Signed proposal-structure hints. No coordinate is a truth/outcome probability."""
import math
from .contracts import ContractError, validate


def profile(graph,route_ids,max_nodes=512):
    from legal_bench.proof_carrying.spectral import solve
    import numpy as np
    g=validate(graph,'GraphRelease');routes=set(route_ids);nodes={n['uid']:n for n in g['nodes']}
    if any(uid not in nodes or nodes[uid]['node_type']!='ROUTE' for uid in routes):
        raise ContractError('SIGNATURE_ROUTE_SET')
    members=sorted({e['src'] for e in g['edges'] if e['relation']=='ROUTE_MEMBER' and e['dst'] in routes})
    if not members:return {'available':False,'reason':'NO_VALID_PROPOSAL_RECORDS','vector':None}
    if len(members)>max_nodes:return {'available':False,'reason':'SPECTRAL_MATRIX_BUDGET','vector':None,'node_count':len(members)}
    ix={uid:i for i,uid in enumerate(members)};p=np.zeros((len(ix),len(ix)));n=np.zeros_like(p)
    for e in g['edges']:
        if e['src'] not in ix or e['dst'] not in ix or e['src']==e['dst']:continue
        if e['relation'] not in ('PROPOSED_SUPPORT','PROPOSED_OPPOSE'):continue
        a,b=ix[e['src']],ix[e['dst']];channel=n if e['relation']=='PROPOSED_OPPOSE' else p
        channel[a,b]+=1;channel[b,a]+=1
    value=solve(p,n);plus=float(p.sum()/2);minus=float(n.sum()/2);edges=plus+minus
    components=value['components'];ev=[c['eigenvalues'] for c in components]
    kinds=['EVIDENCE','ENTITY','USE','JUDGMENT','BINDING','LINK']
    counts=[sum(nodes[uid]['node_type']==kind for uid in members)/len(members) for kind in kinds]
    vector=[math.log1p(len(members)),plus/max(edges,1),minus/max(edges,1),
        len(value['isolates'])/len(members),len(components)/len(members),
        sum(e[0] for e in ev)/max(len(ev),1),sum(e[1] for e in ev)/max(len(ev),1),*counts]
    return {'available':True,'vector':vector,'node_count':len(members),'positive_edges':plus,'negative_edges':minus,
        'components':len(components),'isolates':len(value['isolates']),
        'interpretation':'PROPOSED_STRUCTURE_ONLY_NOT_LEGAL_TRUTH','truncated':False}


def cosine(a,b):
    if len(a)!=len(b):raise ContractError('COSINE_DIMENSION')
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in [*a,*b]):raise ContractError('COSINE_NONFINITE')
    norm=math.sqrt(sum(x*x for x in a)*sum(x*x for x in b))
    return sum(x*y for x,y in zip(a,b))/norm if norm else 0.0
