"""Label-blind rule application enumeration and typed graph construction."""
import itertools
import re
from .contracts import content_hash
from .workflow_v8 import fact_source_check

RELATIONS=('USES_FACT','USES_RULE','HAS_SLOT','OPPOSES','SUPPORTS','UNRESOLVED','HAS_SOURCE','HAS_OBJECT','DERIVED_DEPENDENCY','REQUESTS_CONCLUSION')
TYPES=('CANDIDATE','FACT','RULE','SOURCE','OBJECT','REQUEST')

def catalogue(rules):
    result={}
    for rule in rules:
        for slot in rule['slots']:
            p=slot['predicate']
            result.setdefault(p,{'id':p,'meaning':slot['description'],'parameters':slot['required_roles'],
                'allowed_statuses':slot['allowed_statuses'],'time_required':slot['time_required'],
                'scope':[],'negation':'Explicit FALSE is not lack of a witness','origin':'EXISTING_VERSIONED_RULE_SLOT'})
            result[p]['scope'].append({'rule_ref':rule['id']+'@'+str(rule['version']), 'stage':rule['stage'],'jurisdiction':rule['jurisdiction']})
        result.setdefault(rule['conclusion_predicate'],{'id':rule['conclusion_predicate'],'meaning':rule['conclusion_text'],
            'parameters':[],'scope':[{'rule_ref':rule['id']+'@'+str(rule['version']),'stage':rule['stage']}],
            'origin':'EXISTING_RULE_CONCLUSION','negation':'Explicit FALSE is not lack of a witness'})
    return list(result.values())

def layout(rules):
    """Explicit roles rather than declaring every case assessment a reusable standard."""
    return [{'rule_ref':r['id']+'@'+str(r['version']),
        'role':'TEST' if r['operator']=='OPEN_TEXT' else 'ELEMENT_COMBINATION',
        'reusability':'CASE_ATTRIBUTED_EVALUATION' if r['operator']=='OPEN_TEXT' else 'RESEARCH_TRANSLATION_SCOPE_BOUND',
        'operator':r['operator'],'exceptions':r['exception_slots'],'burden_policy':r['burden_policy'],
        'unimplemented':r['unimplemented'],'source_refs':r['source_refs'],
        'generic_rule_approval':False} for r in rules]

def mapping_candidates(facts,cat,similarity):
    rows=[]
    for p in facts['premises']:
        ranked=sorted(cat,key=lambda c:(-similarity(p['text'],c['meaning']),c['id']))[:5]
        rows.append({'premise':p['id'],'declared_predicate':p['predicate'],
            'candidates':[{'predicate':c['id'],'similarity':similarity(p['text'],c['meaning'])} for c in ranked],
            'mapping_status':'UNREVIEWED_MODEL_DECLARATION','identity_merge':False})
    return rows

def generate(facts,rules,sources,similarity,max_per_rule=12):
    """Enumerate from slots, including alternate fact choices, independent of labels.

    Two E5 candidates per slot and explicit predicate matches; all missing slots
    retained. Bounded combinations use deterministic product order, not labels.
    Derived slots remain explicit dependencies; never treated as witnessed facts.
    """
    premises=facts['premises'];outputs={r['conclusion_predicate']:r['id']+'@'+str(r['version']) for r in rules}
    out=[]
    for rule in rules:
        rid=rule['id']+'@'+str(rule['version']);pools=[]
        for slot in rule['slots']:
            exact=[p for p in premises if p['predicate']==slot['predicate']]
            ranked=sorted(premises,key=lambda p:(-similarity(p['text'],slot['description']),p['id']))
            pool=[]
            for p in exact+ranked[:2]:
                v={'slot':slot['name'],'kind':'PREMISE','id':p['id']}
                if v not in pool:pool.append(v)
            if slot['predicate'] in outputs and outputs[slot['predicate']]!=rid:
                pool.insert(0,{'slot':slot['name'],'kind':'RULE_DEPENDENCY','id':outputs[slot['predicate']]})
            pools.append(pool or [{'slot':slot['name'],'kind':'MISSING','id':None}])
        # Round-robin depth coverage avoids treating a supplied derivation as sole candidate.
        choices=list(itertools.islice(itertools.product(*pools),max_per_rule)) if pools else [()]
        for choice in choices:
            errors=[];bindings={};times=set();states=[];refs=set();similarities=[]
            for inp,slot in zip(choice,rule['slots']):
                if inp['kind']!='PREMISE':
                    if inp['kind']=='MISSING':errors.append('MISSING:'+slot['name'])
                    continue
                p=next(p for p in premises if p['id']==inp['id'])
                refs.update(p['refs']);states.append(p['state']);similarities.append(similarity(p['text'],slot['description']))
                if p['predicate']!=slot['predicate']:errors.append('UNREVIEWED_PREDICATE_MAPPING:'+slot['name'])
                if p['statement_status'] not in slot['allowed_statuses']:errors.append('STATUS_MISMATCH:'+slot['name'])
                if slot['time_required'] and not p['time_scope']:errors.append('TIME_UNKNOWN:'+slot['name'])
                if p['time_scope']:times.add(p['time_scope'])
                pb={b['role']:b['entity'] for b in p['bindings']}
                for role in slot['required_roles']:
                    if not pb.get(role):errors.append('OBJECT_UNKNOWN:'+slot['name']+':'+role)
                for role,value in pb.items():
                    if role in bindings and bindings[role]!=value:errors.append('OBJECT_CONFLICT:'+role)
                    else:bindings[role]=value
                origin=fact_source_check(p,sources)
                if not origin.startswith('ADDRESS_AND_ROLE_VALID'):errors.append(origin+':'+p['id'])
            if len(times)>1:errors.append('TIME_SCOPE_JOIN_UNREVIEWED')
            record={'rule_ref':rid,'inputs':list(choice),'bindings':[{'role':r,'entity':v} for r,v in sorted(bindings.items())],
                'time_scope':next(iter(times)) if len(times)==1 else None,'proposed_use':'INPUTS_FOR_RULE_APPLICATION',
                'refs':sorted(refs),'structural_flags':sorted(set(errors)),
                'simple_features':{'mean_similarity':sum(similarities)/max(len(similarities),1),
                    'missing':sum(x['kind']=='MISSING' for x in choice),'flags':len(set(errors)),
                    'opposition':sum(s=='FALSE' for s in states),'conflict':sum(s=='CONFLICTED' for s in states)},
                'origin':'DETERMINISTIC_SLOT_ENUMERATION_NOT_LEGAL_FINDING'}
            record['id']='APP-'+content_hash(record)[:16];out.append(record)
    return out

def graph(facts,rules,sources,candidates,requests=()):
    nodes=[];edges=[]
    def add(kind,key,text,meta):nodes.append({'id':kind+':'+key,'type':kind,'text':text,'metadata':meta})
    for p in facts['premises']:
        add('FACT',p['id'],p['text'],{k:p[k] for k in ('statement_status','bindings','time_scope','state','limitations','stage')})
        for r in p['refs']:
            if r in sources:edges.append(['SOURCE:'+r,'FACT:'+p['id'],'HAS_SOURCE'])
        for b in p['bindings']:edges.append(['OBJECT:'+b['entity'],'FACT:'+p['id'],'HAS_OBJECT'])
    for e in facts['entities']:add('OBJECT',e['id'],e['label'],{'kind':e['kind']})
    for ref,s in sources.items():add('SOURCE',ref,s['text'],{'document_role':s['document_role'],'role':s.get('role'),'stage':'SOURCE'})
    for r in rules:add('RULE',r['id']+'@'+str(r['version']),r['description']+' '+r['conclusion_text'],
        {k:r[k] for k in ('operator','scope_limits','burden_policy','unimplemented','stage','jurisdiction')})
    for c in candidates:
        add('CANDIDATE',c['id'],c['proposed_use']+' '+c['rule_ref'],{k:c[k] for k in ('bindings','time_scope','structural_flags','simple_features')})
        edges.append(['RULE:'+c['rule_ref'],'CANDIDATE:'+c['id'],'USES_RULE'])
        for x in c['inputs']:
            if x['kind']=='PREMISE':edges.append(['FACT:'+x['id'],'CANDIDATE:'+c['id'],'USES_FACT'])
            elif x['kind']=='RULE_DEPENDENCY':edges.append(['RULE:'+x['id'],'CANDIDATE:'+c['id'],'DERIVED_DEPENDENCY'])
    for e in facts['relations']:
        relation={'SUPPORT':'SUPPORTS','OPPOSE':'OPPOSES','UNRESOLVED':'UNRESOLVED'}[e['sign']]
        edges.append(['FACT:'+e['from'],'FACT:'+e['to'],relation])
    for q in requests:
        add('REQUEST',q['id'],q['predicate'],{'role':'REQUEST_OR_DEFENSE'})
        for c in candidates:
            rule=next(r for r in rules if r['id']+'@'+str(r['version'])==c['rule_ref'])
            if rule['conclusion_predicate']==q['predicate']:edges.append(['CANDIDATE:'+c['id'],'REQUEST:'+q['id'],'REQUESTS_CONCLUSION'])
    ids={n['id'] for n in nodes};valid=[e for e in edges if e[0] in ids and e[1] in ids]
    return {'nodes':nodes,'edges':valid,'isolated_edges':[e for e in edges if e not in valid],
        'labels_in_input':False,'relation_origins':{'HAS_SOURCE':'MODEL_CITATION_ADDRESS','HAS_OBJECT':'MODEL_BINDING',
        'USES_RULE':'DETERMINISTIC_CANDIDATE','USES_FACT':'DETERMINISTIC_CANDIDATE','DERIVED_DEPENDENCY':'RULE_SLOT',
        'SUPPORTS':'MODEL_PROPOSAL','OPPOSES':'MODEL_PROPOSAL','UNRESOLVED':'MODEL_PROPOSAL'}}

def simple_score(c):
    f=c['simple_features'];return f['mean_similarity']-0.1*f['flags']-0.2*f['missing']

def select(candidates,scores,budget=6):
    ranked=sorted(candidates,key=lambda c:(-scores[c['id']],c['id']))
    return {'ranking':[c['id'] for c in ranked],'selected':[c['id'] for c in ranked[:budget]],'budget':budget,
        'dependency_policy':'Selected applications only; missing dependency explicitly unresolved, never fetched using labels'}
