"""Common input eligibility; never reads references, model scores or checker output."""
import copy,json
from pathlib import Path
from .contracts import content_hash
from .grounding_v9 import source_match

def load_contracts(path,rules):
    data=json.loads(Path(path).read_text());out={}
    for rid,rule in rules.items():
        c=data.get(content_hash(rule))
        if not c or c['variables']['rule_hash']!=content_hash(rule):raise ValueError('RULE_CONTRACT_MISSING:'+rid)
        out[rid]=c
    return out

def eligibility(candidates,rules,facts,sources,contracts):
    rows=[]
    for c in candidates:
        bad=[];pending=[];r=rules.get(c['rule_ref'])
        if r is None:bad.append('RULE_VERSION_MISSING')
        else:
            sc={s['name']:s for s in r['slots']}
            for x in c['inputs']:
                s=sc.get(x['slot'])
                if not s:bad.append('UNKNOWN_SLOT:'+x['slot']);continue
                if x['kind']=='MISSING':pending.append('MISSING_SLOT:'+x['slot']);continue
                if x['kind']=='RULE_DEPENDENCY':
                    if x['id'] not in rules or rules[x['id']]['conclusion_predicate']!=s['predicate']:bad.append('DEPENDENCY_TYPE:'+x['slot'])
                    continue
                p=facts.get(x['id'])
                if not p:pending.append('MISSING_RECORD:'+x['slot']);continue
                if p['statement_status'] in ['LEGAL_RULE','TARGET_DISPOSITION']:bad.append('NONFACT_AS_FACT:'+p['id'])
                elif p['statement_status']=='UNKNOWN':pending.append('STATUS_UNKNOWN:'+p['id'])
                elif p['statement_status'] not in s['allowed_statuses']:bad.append('KNOWN_STATUS_MISMATCH:'+p['id'])
                refs=[sources.get(z) for z in p['refs']]
                if not refs or any(z is None for z in refs):pending.append('SOURCE_UNKNOWN:'+p['id'])
                elif all(z.get('document_role')!='TARGET' for z in refs):bad.append('FOREIGN_ONLY_FACT:'+p['id'])
                elif all(z.get('role')=='DISPOSITION_ONLY' for z in refs):bad.append('DISPOSITION_SOURCE:'+p['id'])
                if p['predicate']!=s['predicate']:pending.append('PREDICATE_MAPPING_UNREVIEWED:'+x['slot'])
                if s['time_required']:
                    if not p['time_scope'] or not c['time_scope']:pending.append('TIME_UNKNOWN:'+x['slot'])
                    elif p['time_scope']!=c['time_scope']:bad.append('KNOWN_TIME_MISMATCH:'+x['slot'])
                coverage=contracts[c['rule_ref']]['coverage'][x['slot']]
                if coverage['mode']=='UNRESOLVED':pending.append('COVERAGE_UNRESOLVED:'+x['slot'])
            for issue in c.get('v9_binding_issues',[]):
                (bad if issue.startswith('VARIABLE_CONFLICT:') else pending).append(issue)
        rows.append({'id':c['id'],'status':'EXCLUDE_EXPLICIT_CONTRACT_ERROR' if bad else 'KEEP_PENDING' if pending else 'KEEP','errors':bad,'pending':pending})
    return rows

def revise_addresses(reference,sources):
    result=copy.deepcopy(reference);ledger=[]
    for group,refskey,qkey in [('premise_reviews','refs','quote'),('candidate_reviews','conclusion_refs','conclusion_quote')]:
        for x in result.get(group,[]):
            if not x.get(qkey) or not x.get(refskey):continue
            before={'quote':x[qkey],'refs':x[refskey]}
            if source_match(before,sources)['error'] is None:continue
            docs={sources[k]['document'] for k in x[refskey] if k in sources}
            if len(docs)!=1:continue
            full={k:s for k,s in sources.items() if s['document'] in docs and s.get('document_role')=='TARGET'}
            found=source_match({'quote':x[qkey],'refs':list(full)},full)
            if found['error']:ledger.append({'group':group,'id':x['id'],'status':'NOT_REPAIRED','reason':found['error']});continue
            refs=list(dict.fromkeys(s['ref'] for s in found['original_spans']))
            after=list(dict.fromkeys(x[refskey]+refs))
            if source_match({'quote':x[qkey],'refs':after},sources)['error']:continue
            ledger.append({'group':group,'id':x['id'],'status':'ADDRESS_ONLY_REVISION','old_refs':x[refskey],'new_refs':after,'quote_unchanged':x[qkey],'locator':found,'semantic_decision_unchanged':True})
            x[refskey]=after
    return result,ledger

def oracle_frontier(checked,qmap,origins,budget=6,cap=50000):
    """Evaluation-only upper envelope of explicitly checked routes. Never a ranker."""
    steps=checked.get('steps',{});memo={}
    def footprint(sid,seen=frozenset()):
        if sid in seen:raise ValueError('CYCLE')
        if sid in memo:return memo[sid]
        row=steps[sid];s={origins[sid]}
        for d in row.get('dependencies',[]):
            if d['kind']=='STEP':s|=footprint(d['id'],seen|{sid})
        memo[sid]=s;return s
    paths=[]
    for q in checked.get('requests',[]):
        if q.get('answer')!='TRUE' or q.get('errors'):continue
        members=footprint(q['step_id'])
        if len(members)<=budget:paths.append({'request':qmap[q['id']],'step_id':q['step_id'],'members':sorted(members),'assumptions':q.get('semantic_assumptions',[])})
    states={frozenset()};capped=False
    for p in paths:
        new={s|frozenset(p['members']) for s in states if len(s|frozenset(p['members']))<=budget}
        if len(states|new)>cap:capped=True;break
        states|=new
    def covered(s):return {p['request'] for p in paths if set(p['members'])<=s}
    best=min(states,key=lambda s:(-len(covered(s)),len(s),sorted(s)))
    return {'label':'EVALUATION_ONLY_NOT_DEPLOYABLE','selected':sorted(best),'covered_requests':sorted(covered(best)),'valid_paths':paths,'states_examined':len(states),'frontier_capped':capped,'budget':budget,'exact_over_enumerated_paths':not capped,'not_full_legal_oracle':True}
