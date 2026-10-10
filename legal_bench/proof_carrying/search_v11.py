"""Label-blind balanced candidates and request-conditioned sequential selection."""
import itertools,math,copy
from .contracts import content_hash

def covered_product(pools,base=12,cap=64):
    if not pools:return [()],{'total':1,'covered_all_marginals':True,'omitted':0}
    sizes=[len(p) for p in pools];total=math.prod(sizes);limit=min(total,cap,max(base,max(sizes)))
    indexes=[]
    # A diagonal first pass covers each option of every slot, unlike a product prefix.
    for j in range(max(sizes)):
        x=tuple(j % n for n in sizes)
        if x not in indexes and len(indexes)<limit:indexes.append(x)
    for x in itertools.product(*(range(n) for n in sizes)):
        if len(indexes)>=limit:break
        if x not in indexes:indexes.append(x)
    unseen={str(i):[j for j in range(n) if all(x[i]!=j for x in indexes)] for i,n in enumerate(sizes)}
    return [tuple(pools[i][j] for i,j in enumerate(x)) for x in indexes],{'total':total,'enumerated':len(indexes),'omitted':total-len(indexes),'pool_sizes':sizes,'unseen_options':unseen,'covered_all_marginals':not any(unseen.values()),'not_complete_cartesian_coverage':len(indexes)<total}

def signature(c):return content_hash([c['rule_ref'],c['inputs']])

def generate(facts,rules,similarity):
    outputs={}
    for r in rules:outputs.setdefault(r['conclusion_predicate'],[]).append(r['id']+'@'+str(r['version']))
    out=[];audit=[];fi={p['id']:p for p in facts['premises']}
    for r in rules:
        rid=r['id']+'@'+str(r['version']);pools=[]
        for s in r['slots']:
            exact=[p for p in fi.values() if p['predicate']==s['predicate']]
            near=sorted(fi.values(),key=lambda p:(-similarity(p['text'],s['description']),p['id']))[:2]
            pool=[{'slot':s['name'],'kind':'RULE_DEPENDENCY','id':q} for q in outputs.get(s['predicate'],[]) if q!=rid]
            for p in exact+near:
                x={'slot':s['name'],'kind':'PREMISE','id':p['id']}
                if x not in pool:pool.append(x)
            pools.append(pool or [{'slot':s['name'],'kind':'MISSING','id':None}])
        choices,diag=covered_product(pools);audit.append({'rule_ref':rid,'pools':pools,**diag})
        for choice in choices:
            refs=set();sim=[];states=[];flags=[];times=set()
            for s,x in zip(r['slots'],choice):
                if x['kind']=='MISSING':flags.append('MISSING:'+s['name'])
                if x['kind']!='PREMISE':continue
                p=fi[x['id']];refs.update(p['refs']);sim.append(similarity(p['text'],s['description']));states.append(p['state'])
                if p['predicate']!=s['predicate']:flags.append('UNREVIEWED_PREDICATE_MAPPING:'+s['name'])
                if p['time_scope']:times.add(p['time_scope'])
            c={'rule_ref':rid,'inputs':list(choice),'bindings':[],'time_scope':next(iter(times)) if len(times)==1 else None,'proposed_use':'INPUTS_FOR_RULE_APPLICATION','refs':sorted(refs),'structural_flags':flags,'simple_features':{'mean_similarity':sum(sim)/max(1,len(sim)),'missing':sum(x['kind']=='MISSING' for x in choice),'flags':len(flags),'opposition':states.count('FALSE'),'conflict':states.count('CONFLICTED')},'origin':'BALANCED_MARGINAL_COVERAGE_NOT_LEGAL_FINDING'}
            c['id']='ACT-'+signature(c)[:16];out.append(c)
    return out,audit

def rule_goals(request,rules):
    needed={k for k,r in rules.items() if r['conclusion_predicate']==request['predicate']};changed=True
    while changed:
        before=set(needed)
        for rid in list(needed):
            for s in rules[rid]['slots']:
                needed.update(k for k,r in rules.items() if r['conclusion_predicate']==s['predicate'] and k!=rid)
        changed=before!=needed
    return needed

def structural_ready(candidates,selected):
    cs={c['id']:c for c in candidates};ready=set();changed=True
    while changed:
        before=set(ready)
        for k in selected:
            c=cs[k]
            if any(x['kind']=='MISSING' for x in c['inputs']):continue
            deps=[x['id'] for x in c['inputs'] if x['kind']=='RULE_DEPENDENCY']
            if all(any(cs[z]['rule_ref']==rid for z in ready) for rid in deps):ready.add(k)
        changed=ready!=before
    return ready

def state_features(candidates,rules,request,selected,budget):
    """No reference, acceptance result, known route or label enters this function."""
    chosen=set(selected);cs={c['id']:c for c in candidates};ready=structural_ready(candidates,chosen);rr={cs[k]['rule_ref'] for k in ready}
    roots={r for r,v in rules.items() if v['conclusion_predicate']==request['predicate']};goals=rule_goals(request,rules)
    missing=set(roots)-rr
    for k in chosen:
        if cs[k]['rule_ref'] in goals:
            missing.update(x['id'] for x in cs[k]['inputs'] if x['kind']=='RULE_DEPENDENCY' and x['id'] not in rr)
    used_facts={x['id'] for k in chosen for x in cs[k]['inputs'] if x['kind']=='PREMISE'}
    rows={}
    for c in candidates:
        rid=c['rule_ref'];deps=[x['id'] for x in c['inputs'] if x['kind']=='RULE_DEPENDENCY'];facts=[x['id'] for x in c['inputs'] if x['kind']=='PREMISE'];f=c['simple_features']
        rows[c['id']]=[float(rid in roots),float(rid in goals),float(rid in missing),float(rid in rr),float(c['id'] in chosen),(budget-len(chosen))/max(1,budget),len(deps)/8,sum(x in rr for x in deps)/max(1,len(deps)),sum(x in used_facts for x in facts)/max(1,len(facts)),float(f['mean_similarity']),f['missing']/8,f['flags']/8,float(f['opposition']>0),float(f['conflict']>0)]
    return rows

def simple_scores(features):
    # Same state information available to Flat/RGCN; no candidate correctness oracle.
    return {k:4*x[2]+2*x[1]+x[0]+1.5*x[7]+.5*x[8]+x[9]-2*x[3]-2*x[10]-.5*x[11] for k,x in features.items()}

def search(candidates,rules,requests,budget,scorer):
    selected=[];trace=[]
    for t in range(min(budget,len(candidates))):
        q=requests[t%len(requests)];features=state_features(candidates,rules,q,selected,budget);scores=scorer(q,selected,budget,features)
        available=[c['id'] for c in candidates if c['id'] not in selected]
        chosen=min(available,key=lambda k:(-scores[k],k));trace.append({'request':q['id'],'selected_before':list(selected),'remaining':budget-len(selected),'chosen':chosen,'scores':scores,'state_features':features});selected.append(chosen)
    return {'selected':selected,'budget':budget,'gaps':[],'trace':trace,'structural_ready_not_legal_truth':sorted(structural_ready(candidates,selected))}
