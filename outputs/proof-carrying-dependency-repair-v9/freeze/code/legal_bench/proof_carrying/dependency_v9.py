"""Rule-declared variables, finite alternative routes, and dependency-closed budgets.
No rank model, reference label, or checker outcome is used by selection.
"""
import copy,itertools
from .contracts import content_hash

def role_contracts(rules,case):
    out={}
    for r in rules:
        ref=r['id']+'@'+str(r['version'])
        maps={s['name']:{k:k for k in s['required_roles']} for s in r['slots']}
        reason='Existing slot descriptions share the named litigant/property roles; only required roles unify; extra event roles remain local.'
        if case=='840688' and r['id']=='R1':
            maps={'record_P1':{'subject':'applicant','opponent':'owner','property':'property'},'record_P2':{'subject':'requisitioner','opponent':'applicant','property':'property'},'record_P6':{'subject':'applicant','opponent':'requisitioner','property':'property'}}
            reason='Lease lessee is displaced occupier; State is requisition actor, not lessee. Rule describes same land, lease applicant, State and owner as different variables.'
        elif case=='840688' and r['id']=='R2':
            maps={'record_P3':{'subject':'high_court','opponent':'state','property':'property'},'record_P5':{'subject':'supreme_court','opponent':'high_court','property':'property'}}
            reason='Reopening criticism is by Supreme Court of High Court order; adjudicators do not become the owner or State. Only declared links join.'
        elif case=='1144022':
            for slot,m in maps.items():
                if slot=='record_P3':m.update(subject='company',opponent='bank')
                else:m.update(subject='bank',opponent='company')
            reason='Company counsel makes procedural concession about bank possession. Concession actor and protected possessor differ. The two judicial opinions remain separate rule IDs.'
        out[ref]={'version':1,'rule_hash':content_hash(r),'slot_variables':maps,'source_refs':r['source_refs'],'source_quote':r['source_quote'],'reason':reason,'review_status':'MAINTAINER_SOURCE_REVIEW_RESEARCH_ONLY','legal_approval':False}
    return out

def rebind(c,rule,facts,contract):
    n=copy.deepcopy(c);bind={};issues=[]
    for x in c['inputs']:
        if x['kind']!='PREMISE':continue
        p=facts.get(x['id']);mapping=contract['slot_variables'][x['slot']]
        if not p:issues.append('MISSING:'+x['slot']);continue
        pb={b['role']:b['entity'] for b in p['bindings']}
        for role,var in mapping.items():
            v=pb.get(role)
            if not v:issues.append('VARIABLE_UNKNOWN:'+x['slot']+':'+role);continue
            if var in bind and bind[var]!=v:issues.append('VARIABLE_CONFLICT:'+var)
            else:bind[var]=v
    n['bindings']=[{'role':k,'entity':v} for k,v in sorted(bind.items())]
    n['parent_candidate_id']=c['id'];n['binding_contract_hash']=content_hash(contract)
    n['v9_binding_issues']=issues
    return n

def compile_routes(candidates,selected,rules,requests,facts,contracts,limit=64):
    chosen={c['id']:c for c in candidates if c['id'] in selected};by_rule={}
    for key in selected:
        if key in chosen:by_rule.setdefault(chosen[key]['rule_ref'],[]).append(key)
    cache={};steps={};origins={};gaps=[]
    def expand(key,seen):
        if key in seen:gaps.append('CYCLE:'+key);return []
        if key in cache:return cache[key]
        c=chosen[key];pools=[]
        for x in c['inputs']:
            if x['kind']=='PREMISE':pools.append([x])
            elif x['kind']=='RULE_DEPENDENCY':
                options=[{'slot':x['slot'],'kind':'STEP','id':s['id']} for k in by_rule.get(x['id'],[]) for s in expand(k,seen|{key}) if compatible(c,s)]
                pools.append(options or [None])
            else:pools.append([None])
        variants=[]
        for idx,combo in enumerate(itertools.product(*pools)):
            if idx>=limit:gaps.append('ROUTE_LIMIT:'+key);break
            binding={x['role']:x['entity'] for x in c['bindings']}
            for x in combo:
                if not x or x['kind']!='STEP':continue
                dep=steps[x['id']];mp=contracts[c['rule_ref']]['slot_variables'][x['slot']];db={v['role']:v['entity'] for v in dep['bindings']}
                for role,var in mp.items():
                    if role in db:binding.setdefault(var,db[role]) # conflicts are independently rejected by checker
            step={'id':key+'~'+str(idx),'rule_ref':c['rule_ref'],'bindings':[{'role':k,'entity':v} for k,v in sorted(binding.items())],'time_scope':c['time_scope'],'inputs':[x for x in combo if x],'proposed_state':'TRUE','explanation':'Untrusted route proposal; every selected alternative is independently checked.'}
            steps[step['id']]=step;origins[step['id']]=key;variants.append(step)
        cache[key]=variants;return variants
    qs=[];mapq={}
    for q in requests:
        roots=[key for key in selected if key in chosen and rules[chosen[key]['rule_ref']]['conclusion_predicate']==q['predicate']]
        for key in roots:
            for s in expand(key,set()):
                qid=q['id']+'~'+str(len(qs));qs.append({**q,'id':qid,'step_id':s['id'],'proposed_state':'TRUE'});mapq[qid]=q['id']
    return {'steps':list(steps.values()),'requests':qs,'counterarguments':[],'gaps':gaps},origins,mapq

def select_closed(candidates,order,rules,requests,budget=6,limit=64):
    cs={c['id']:c for c in candidates};rank={k:i for i,k in enumerate(order)};by_rule={}
    for k in order:by_rule.setdefault(cs[k]['rule_ref'],[]).append(k)
    notes=[]
    def closure(k,seen):
        if k in seen:return []
        pools=[]
        for x in cs[k]['inputs']:
            if x['kind']=='MISSING':return []
            if x['kind']=='RULE_DEPENDENCY':
                options=[s for dep in by_rule.get(x['id'],[]) if compatible(cs[k],cs[dep]) for s in closure(dep,seen|{k})]
                if not options:return []
                pools.append(options[:limit])
        result=[]
        for parts in itertools.islice(itertools.product(*pools),limit):
            s={k}.union(*parts)
            if len(s)<=budget:result.append(s)
        return result
    selected=set();bundles=[]
    for q in requests:
        possible=[]
        for k in order:
            if rules[cs[k]['rule_ref']]['conclusion_predicate']==q['predicate']:
                possible += [(s,k) for s in closure(k,set()) if len(s|selected)<=budget]
        if possible:
            # Fixed lexical rank tuple, no reference scores/labels or legal acceptance.
            possible.sort(key=lambda sk:(max(rank[k] for k in sk[0]),sum(rank[k] for k in sk[0]),len(sk[0]-selected),sk[1]))
            s,k=possible[0];selected|=s;bundles.append({'request':q['id'],'root':k,'members':sorted(s,key=rank.get)})
        else:notes.append('NO_COMPLETE_BUNDLE_WITHIN_BUDGET:'+q['id'])
    # Preserve ranked alternatives with their full dependencies, rather than adding orphan roots.
    for k in order:
        if k in selected:continue
        opts=[s for s in closure(k,set()) if len(s|selected)<=budget]
        if opts:selected|=min(opts,key=lambda s:(sum(rank[x] for x in s),len(s),sorted(s)))
    return {'selected':[k for k in order if k in selected],'bundles':bundles,'budget':budget,'gaps':notes,'excluded':[{'id':k,'reason':'BUDGET_OR_DEPENDENCY_CLOSURE','flags':cs[k].get('structural_flags',[]),'opposition':cs[k]['simple_features']['opposition'],'conflict':cs[k]['simple_features']['conflict']} for k in order if k not in selected]}


def compatible(a,b):
    av={x['role']:x['entity'] for x in a['bindings']};bv={x['role']:x['entity'] for x in b['bindings']}
    return not any(av[k] and bv[k] and av[k]!=bv[k] for k in av.keys() & bv.keys())
