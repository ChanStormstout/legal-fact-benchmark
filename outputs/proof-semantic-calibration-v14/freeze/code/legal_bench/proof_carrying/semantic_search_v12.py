"""Budgeted backward hypergraph expansion. No labels, policies or truth checks.
Every route is an untrusted proposal. All evidence and opposition stay in the snapshot.
"""
from collections import defaultdict
from itertools import product
import hashlib,json,time

class SearchLimit(Exception): pass

def complete_search(candidates,rules,requests,contracts,max_expansions=10000,max_seconds=10):
    byrule=defaultdict(list)
    for c in candidates: byrule[c['rule_ref']].append(c)
    all_steps={};out=[]
    for q in requests:
        start=time.monotonic();expanded=0;memo={};issues=[];roots=[]
        def tick():
            nonlocal expanded
            if expanded>=max_expansions or time.monotonic()-start>=max_seconds: raise SearchLimit()
            expanded+=1
        def expand(c,active):
            tick()
            if c['id'] in active:
                issues.append({'kind':'CYCLE','candidate':c['id']});return []
            # Path-sensitive cache prevents a cyclic branch poisoning an independent route.
            key=(c['id'],tuple(sorted(active)))
            if key in memo:return memo[key]
            r=rules[c['rule_ref']];slots={s['name']:s for s in r['slots']}
            pools=[]
            xs={x['slot']:x for x in c['inputs']}
            for name,s in slots.items():
                x=xs.get(name,{'slot':name,'kind':'MISSING','id':''})
                if x['kind']=='RULE_DEPENDENCY':
                    options=[]
                    for dep in byrule.get(x['id'],[]):
                        for sid in expand(dep,active|{c['id']}):
                            # Only rule-declared role mapping, not global role-name equality.
                            child=all_steps[sid]; vals={b['role']:b['entity'] for b in child['bindings']}
                            parent={b['role']:b['entity'] for b in c['bindings']}
                            mapping=contracts[c['rule_ref']]['slot_variables'].get(name,{})
                            if any(parent.get(var) and vals.get(role) and parent[var]!=vals[role] for role,var in mapping.items()):continue
                            options.append({'slot':name,'kind':'STEP','id':sid})
                    if not options:options=[{'slot':name,'kind':'MISSING','id':x['id']}]
                else:options=[x]
                pools.append(options)
            variants=[]
            # Missing slots remain explicit. ANY is decided by checker; one missing alternative never blocks another.
            for combo in product(*pools):
                tick();binding={b['role']:b['entity'] for b in c['bindings']};conflict=False
                for x in combo:
                    if x['kind']!='STEP':continue
                    db={b['role']:b['entity'] for b in all_steps[x['id']]['bindings']}
                    for role,var in contracts[c['rule_ref']]['slot_variables'].get(x['slot'],{}).items():
                        v=db.get(role)
                        if v and binding.get(var) and binding[var]!=v: conflict=True
                        elif v:binding[var]=v
                if conflict:
                    issues.append({'kind':'DEPENDENCY_BINDING_CONFLICT','candidate':c['id']});continue
                step={'candidate_id':c['id'],'rule_ref':c['rule_ref'],'bindings':[{'role':k,'entity':v} for k,v in sorted(binding.items())], 'time_scope':c.get('time_scope'),'inputs':list(combo), 'proposed_state':'UNKNOWN','explanation':'Enumerated dependency route; neither semantic approval nor legal truth.'}
                sid='S-'+hashlib.sha256(json.dumps(step,sort_keys=True).encode()).hexdigest()[:24]
                step['id']=sid;all_steps[sid]=step;variants.append(sid)
            memo[key]=variants;return variants
        limited=False
        try:
            for rid,r in rules.items():
                if r['conclusion_predicate']!=q['predicate']:continue
                for c in byrule[rid]:roots.extend(expand(c,set()))
        except SearchLimit:limited=True
        out.append({'request':q,'root_steps':list(dict.fromkeys(roots)),'search_status':'SEARCH_INCOMPLETE' if limited else 'EXHAUSTED_GIVEN_CANDIDATES','state_expansions':expanded,'routes':len(set(roots)),'seconds':time.monotonic()-start,'issues':issues,'exhaustive_over_source_meaning':False})
    return {'steps':list(all_steps.values()),'requests':out,'budget':{'expansions':max_expansions,'seconds':max_seconds},'reference_used':False,'candidate_count':len(candidates)}
