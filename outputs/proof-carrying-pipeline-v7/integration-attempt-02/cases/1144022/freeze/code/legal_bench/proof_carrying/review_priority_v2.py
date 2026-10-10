"""Frozen review order features; never modify premises or checker results."""
import math
from .spectral import solve

def percentile(values):
    if len(values)<2:return [0.0]*len(values)
    return [(sum(x<v for x in values)+(sum(x==v for x in values)-1)/2)/(len(values)-1) for v in values]

def order(proposal):
    ids=[p['id'] for p in proposal['premises']]; index={x:i for i,x in enumerate(ids)}; n=len(ids)
    P=[[0]*n for _ in ids];N=[[0]*n for _ in ids];ignored=[]
    for e in proposal['relations']:
        if e['from'] not in index or e['to'] not in index or e['from']==e['to'] or e['sign']=='UNRESOLVED':
            ignored.append(e);continue
        i,j=index[e['from']],index[e['to']];M=P if e['sign']=='SUPPORT' else N
        M[i][j]=M[j][i]=1  # unit channel; parallel opposite channel retained
    numeric=solve(P,N);simple=[];features={}
    for i,p in enumerate(proposal['premises']):
        # Uses proposal uncertainty, never subsequent reference/error labels.
        unresolved=int(p['state'] in ('UNKNOWN','CONFLICTED'))+sum(1 for e in proposal['relations']
            if e['sign']=='UNRESOLVED' and p['id'] in (e['from'],e['to']))
        opposed=sum(1 for j in range(n) if N[i][j])
        features[p['id']]={'unresolved_proposition_or_connections':unresolved,'opposing_pairs':opposed}
        simple.append(unresolved+opposed)
    components=[];positions={p['id']:k for k,p in enumerate(proposal['premises'])}
    for comp in numeric['components']:
        ix=comp['nodes'];x=comp['scores'];energies=[]
        for a,i in enumerate(ix):
            energies.append(sum(P[i][j]*(x[a]-x[b])**2+N[i][j]*(x[a]+x[b])**2 for b,j in enumerate(ix)))
        ps=percentile([simple[i] for i in ix]);pe=percentile(energies)
        score=[ps[k] if comp['nonunique_axis'] else (ps[k]+pe[k])/2 for k in range(len(ix))]
        components.append({'nodes':[ids[i] for i in ix], 'scores':dict(zip([ids[i] for i in ix],score)),
            'energy':dict(zip([ids[i] for i in ix],energies)), 'fallback':comp['nonunique_axis']})
    for i in numeric['isolates']:
        components.append({'nodes':[ids[i]],'scores':{ids[i]:simple[i]},'energy':None,'fallback':True})
    def allocate(k):
        total=min(k,n); alloc=[int(total*len(c['nodes'])/n) for c in components] if n else []
        rem=sorted(range(len(components)),key=lambda i:(-(total*len(components[i]['nodes'])/n-alloc[i]),min(components[i]['nodes'])))
        for i in rem[:total-sum(alloc)]:alloc[i]+=1
        picked=[]
        for c,num in zip(components,alloc):picked+=sorted(c['nodes'],key=lambda q:(-c['scores'][q],q))[:num]
        return picked
    # Source order rather than proposal order; preserve stable ID tie-breaks.
    import re
    def key(p):
        locs=[(r.split(':L')[0],int(m.group(1))) for r in p['refs'] if (m:=re.search(r':L(\d+)',r))]
        return min(locs) if locs else ('ZZZ',positions[p['id']])
    return {'scope':'TEACHING_INTERFACE_ONLY_NO_GRAPH_BENEFIT_ESTIMATE','signed_graph':numeric,
        'proposal_relations':proposal['relations'],'ignored_in_projection':ignored,'components':components,
        'source_order':[p['id'] for p in sorted(proposal['premises'],key=lambda p:(key(p),p['id']))],
        'simple_order':sorted(ids,key=lambda q:(-simple[index[q]],q)),
        'simple_features':features, 'simple_scores':dict(zip(ids,simple)), 'graph_budget_5':allocate(5),'graph_budget_10':allocate(10),
        'evaluation_labels_seen':False,'truth_or_approval_changed':False,
        'feature_limit':'Unresolved propositions/connections and opposing pairs are proposal-declared review work, not verified errors. Logical dependencies are not signed votes.'}
