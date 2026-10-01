"""Small exact reference checks, not a production legal-AI pipeline.
Standard library only. Run: python3 机制样例.py
Exhaustive enumeration supplies a ground-truth oracle for tiny MILP instances.
No LLM extraction, real legal rules, corpus evaluation or production encoder.
"""
from itertools import combinations, product
from pathlib import Path
import json


def subsets(xs):
    xs=list(xs)
    for mask in range(1<<len(xs)):
        yield {xs[i] for i in range(len(xs)) if mask>>i & 1}


def partitions(xs):
    if not xs:
        yield []
        return
    first,*rest=xs
    for p in partitions(rest):
        yield [{first}]+p
        for i in range(len(p)):
            yield p[:i]+[p[i]|{first}]+p[i+1:]


def internal_pairs(p):
    return {tuple(sorted(e)) for c in p for e in combinations(c,2)}


def greedy_partition(n, edges):
    p=[{i} for i in range(n)]
    for i,j in sorted(edges):
        a=next(c for c in p if i in c);b=next(c for c in p if j in c)
        if a is b: continue
        if internal_pairs([a|b])<=edges:
            p.remove(a);p.remove(b);p.append(a|b)
    return p


def check_a():
    all_pairs=list(combinations(range(4),2)); checked=0
    for e in subsets(all_pairs):
        feasible=[p for p in partitions(list(range(4))) if internal_pairs(p)<=e]
        best=max(feasible,key=lambda p:len(internal_pairs(p)))
        greedy=greedy_partition(4,e)
        assert len(internal_pairs(best))>=len(internal_pairs(greedy))
        assert internal_pairs(best)<=e
        checked+=1
    e={(0,1),(0,2),(1,3)}
    p=max((p for p in partitions(list(range(4))) if internal_pairs(p)<=e),key=lambda p:len(internal_pairs(p)))
    assert len(internal_pairs(p))==2 and len(internal_pairs(greedy_partition(4,e)))==1
    return {'exhaustive_4_node_graphs':checked,'competition_optimum_pairs':2,'competition_greedy_pairs':1,'limitation':'Tests only the graph objective and hard constraints, not EQ judgments.'}


def bound_match(atoms):
    # Tuple schema: predicate, buyer, seller, contract, status.
    paid={(b,s,k) for pred,b,s,k,state in atoms if pred=='paid' and state=='FOUND'}
    nd={(b,s,k) for pred,b,s,k,state in atoms if pred=='not_delivered' and state=='FOUND'}
    return paid & nd


def check_b():
    a={('paid','b','s','K1','FOUND'),('not_delivered','b','s','K2','FOUND'),('not_delivered','b','s','K1','ALLEGED')}
    assert not bound_match(a)
    a.add(('not_delivered','b','s','K1','FOUND'))
    assert bound_match(a)=={('b','s','K1')}
    # Fixed synthetic costs, not bytes from a production encoder.
    # Three independent units each contain atoms a,b,c.
    facts={(u,f) for u in range(3) for f in 'abc'}
    patterns={'P':set('ab'),'Q':set('bc'),'R':set('abc')}
    definitions={'P':5,'Q':5,'R':11};macro_cost={'P':3,'Q':3,'R':5}; literal_cost=6
    occ=[(p,u) for p in patterns for u in range(3)]
    best=(len(facts)*literal_cost,set(),set(),facts)
    valid=0
    for chosen in subsets(occ):
        selected={p for p,u in chosen}
        if any(len({u for q,u in chosen if q==p})<3 for p in selected):continue
        covered={(u,f) for p,u in chosen for f in patterns[p]}
        residual=facts-covered
        cost=sum(definitions[p] for p in selected)+sum(macro_cost[p] for p,u in chosen)+literal_cost*len(residual)
        # This is symbolic macro expansion, not a binary-code roundtrip.
        assert covered|residual==facts
        assert covered<=facts
        valid+=1
        if cost<best[0]:best=(cost,selected,chosen,residual)
    assert best[0]==26 and best[1]=={'R'}
    return {'binding_status_checks':2,'feasible_cover_selections':valid,'toy_all_literal_cost':54,'toy_optimum_cost':26,'selected':['R'],'limitation':'Synthetic fixed costs; checks objective/coverage and symbolic expansion. Does not implement binary encoding or query enumeration.'}


def defended(nodes,edges,s):
    return {a for a in nodes if all(any((c,b) in edges for c in s) for b in nodes if (b,a) in edges)}


def grounded(nodes,edges):
    s=set()
    while True:
        nxt=defended(nodes,edges,s)
        assert s<=nxt
        if nxt==s:return s
        s=nxt


def check_c():
    nodes=set(range(3));possible=list(product(range(3),repeat=2));checked=0
    for edges in subsets(possible):
        g=grounded(nodes,edges)
        complete=[]
        for s in subsets(nodes):
            conflict_free=not any(a in s and b in s for a,b in edges)
            if conflict_free and defended(nodes,edges,s)==s:complete.append(s)
        assert complete
        assert g==set.intersection(*complete)
        assert not any(a in g and b in g for a,b in edges)
        checked+=1
    assert grounded({0,1},{(0,1),(1,0)})==set()
    assert grounded({0,1,2},{(0,1),(1,2)})=={0,2}
    return {'all_directed_3_argument_graphs_including_self_attacks':checked,'oracle':'Intersection of complete extensions enumerated independently','limitation':'Tests abstract grounded semantics only, not ASPIC+ grounding, preference lifting, or legal rule translation.'}


if __name__=='__main__':
    result={'status':'PASS','A':check_a(),'B':check_b(),'C':check_c(),'scope':'Small deterministic mechanisms only; no project accuracy or legal validity claims.'}
    dest=Path(__file__).with_name('机制样例结果.json');dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
