"""Direct sourced object edges, separate from identity and legal inference.

The executor keeps the earlier assertion/field contracts. A missing edge is
unknown; neither property containment nor party membership implies identity,
inheritance of an event, contemporaneity, or a legal conclusion.
"""
import copy
import itertools
import json
from collections import Counter, defaultdict
from .core import canonical, digest
from .engine import canonical_query, query_error
from .conditional_engine import execute as base_execute, field_value
from .fast_development import candidates as identity_candidates, seed_event

EDGE_OPS = {'member_of', 'part_of'}
DECISIONS = {'SUPPORTED', 'DENIED', 'UNRESOLVED'}
PROCEDURAL_TYPES = {'FILE_EVICTION', 'FILE_OTHER_PROCEEDING', 'GRANT_EVICTION',
                    'REJECT_EVICTION', 'SERVE_NOTICE'}


def import_edges(view, source, reply, target):
    """Reject invalid cells without granting semantic approvals locally."""
    objects = {o['id']: o for o in view['objects']}
    segments = {s['id']: s for s in source['segments']}
    groups = set(target['group_ids'])
    parents = {(x['left'], x['right']) for x in target['parent_pairs']}
    edges, rejected = [], []
    for original in reply.get('edges', []):
        why = None
        if not isinstance(original, dict):
            rejected.append({'record': original, 'reason': 'MALFORMED_EDGE'}); continue
        op, left, right, decision = (original.get(k) for k in ('op', 'left', 'right', 'decision'))
        if op not in EDGE_OPS or decision not in DECISIONS: why = 'INVALID_OPERATOR_OR_STATE'
        elif not isinstance(left, str) or not isinstance(right, str) or left not in objects or right not in objects: why = 'INVALID_OBJECT_REFERENCE'
        elif left == right: why = 'PROPER_EDGE_CANNOT_BE_SELF'
        elif op == 'part_of' and (objects[left].get('kind') != 'PROPERTY' or objects[right].get('kind') != 'PROPERTY'): why = 'INVALID_PART_KINDS'
        elif op == 'part_of' and (left, right) not in parents: why = 'OUTSIDE_PROPOSED_PARENT_PAIRS'
        elif op == 'member_of' and (objects[left].get('kind') not in {'PERSON', 'ORGANIZATION'} or objects[right].get('kind') != 'GROUP' or right not in groups): why = 'INVALID_MEMBERSHIP_KINDS_OR_TARGET'
        evs = original.get('evidence', [])
        anchored = (isinstance(evs, list) and bool(evs) and all(isinstance(e, dict) and
                    e.get('segment_id') in segments and isinstance(e.get('quote'), str) and bool(e['quote']) and
                    e['quote'] in segments[e['segment_id']]['text'] for e in evs))
        if why is None and decision in {'SUPPORTED','DENIED'} and not anchored: why = 'UNLOCATED_EDGE_EVIDENCE'
        if why:
            rejected.append({'record': copy.deepcopy(original), 'reason': why}); continue
        edge = copy.deepcopy(original)
        edge['id'] = digest({'case': view['case_id'], 'op': op, 'left': left, 'right': right, 'decision': decision})[:20]
        edge['origin'] = 'TARGETED_WEB_MODEL_RELATION_NOT_HUMAN_GOLD'
        edge['computational_evidence'] = [dict(e, page=segments[e['segment_id']].get('page'), source_url=source['url']) for e in evs if isinstance(e, dict) and e.get('segment_id') in segments]
        edges.append(edge)
    # Absence of a decision is a coverage gap, never an implicit negative edge.
    covered = {(e['left'],e['right']) for e in edges if e['op']=='part_of'}
    group_reviews = reply.get('group_reviews', [])
    reviewed = {g.get('group_id') for g in group_reviews if isinstance(g,dict)}
    return {'case_id':view['case_id'], 'edges':edges, 'rejected':rejected,
            'missing_parent_decisions':[list(p) for p in sorted(parents-covered)],
            'missing_group_reviews':sorted(groups-reviewed),
            'group_reviews':copy.deepcopy(group_reviews), 'raw_hash':digest(reply),
            'view_hash':digest(view), 'source_hash':digest(source),
            'closed_world':False, 'semantic_accuracy':'NOT_ESTABLISHED'}


def validate_query(query):
    if not isinstance(query,dict): return 'Malformed query'
    try:
        base = copy.deepcopy(query)
        for c in base.get('constraints', []):
            if c.get('op') in EDGE_OPS:
                if any(not isinstance(c.get(s),str) or '.roles.' not in c[s] for s in ('left','right')):
                    return 'Typed relations require two role/object references'
                c['op']='same'
        return query_error(base)
    except (TypeError, AttributeError, KeyError): return 'Malformed query'


def relation_value(registry, objects, op, left, right):
    """A directed decision on one recorded pair; no closure or co-membership."""
    if left is None or right is None: return 'UNKNOWN', [], 'UNKNOWN_ENDPOINT'
    if left not in objects or right not in objects: return 'UNKNOWN', [], 'MISSING_OBJECT'
    if left == right: return 'MISMATCH', [], 'PROPER_EDGE_NOT_IDENTITY'
    a,b = objects[left],objects[right]
    if op == 'part_of' and (a.get('kind')!='PROPERTY' or b.get('kind')!='PROPERTY'):
        return 'MISMATCH', [], 'WRONG_OBJECT_KINDS'
    if op == 'member_of' and (a.get('kind') not in {'PERSON','ORGANIZATION'} or b.get('kind')!='GROUP'):
        return 'MISMATCH', [], 'WRONG_OBJECT_KINDS'
    edges = [e for e in registry['edges'] if (e['op'],e['left'],e['right'])==(op,left,right)]
    states = {e['decision'] for e in edges}
    refs = sorted({e['id'] for e in edges})
    if {'SUPPORTED','DENIED'} <= states: return 'UNKNOWN', refs, 'CONFLICTING_EDGE_EVIDENCE'
    if 'SUPPORTED' in states: return 'MATCH', refs, 'SOURCED_DIRECT_EDGE'
    if 'DENIED' in states: return 'MISMATCH', refs, 'EXPLICIT_DENIAL'
    return 'UNKNOWN', refs, 'EDGE_NOT_ESTABLISHED'


def compact(witness, case_id):
    """Evidence remains resolvable by case/event IDs rather than duplicated."""
    result = {k:copy.deepcopy(witness[k]) for k in ['binding','failed_conditions','uncertainty'] if k in witness}
    result['evidence_refs'] = [{'case_id':case_id,'event_id':eid} for eid in witness['binding'].values()]
    return result


def base_rows(view, query):
    result = base_execute(view,query)
    return {'status': result['status'], 'unit_id':result.get('unit_id'),
            'witnesses':[compact(w,view['case_id']) for w in result['witnesses']],
            'uncertain_bindings':[compact(w,view['case_id']) for w in result['uncertain_bindings']],
            'rejected_bindings':[compact(w,view['case_id']) for w in result['rejected_bindings']],
            'conflict_event_ids':sorted({c['event_id'] for c in result.get('conflicts',[])}),
            'closed_world':False}


def execute(view, registry, query, cached_base=None):
    error=validate_query(query)
    if error: return {'status':'UNSUPPORTED','reason':error,'witnesses':[],'uncertain_bindings':[],'rejected_bindings':[]}
    typed = [c for c in query.get('constraints',[]) if c['op'] in EDGE_OPS]
    if not typed: return base_rows(view,query)
    base = {'atoms':query['atoms'],'constraints':[c for c in query.get('constraints',[]) if c['op'] not in EDGE_OPS]}
    result = copy.deepcopy(cached_base if cached_base is not None else base_rows(view,base))
    good, unknown, rejected = [], [], list(result['rejected_bindings'])
    objects={o['id']:o for o in view['objects']};events={e['id']:e for e in view['events']}
    for original in result['witnesses']+result['uncertain_bindings']:
        w=copy.deepcopy(original);missing=list(w.get('uncertainty',[]));failed=list(w.get('failed_conditions',[]));edge_refs=[]
        for c in typed:
            vals=[]
            for side in ('left','right'):
                var,field=c[side].split('.',1);event=events[w['binding'][var]]
                val,why=field_value(event,field);vals.append(val)
                if why:missing.append({'event_id':event['id'],'field':field,'dependencies':why})
            state,refs,reason=relation_value(registry,objects,c['op'],*vals)
            edge_refs.extend(refs)
            decision={'constraint':c,'left':vals[0],'right':vals[1],'reason':reason,'edge_ids':refs}
            if state=='MISMATCH':failed.append(decision)
            elif state=='UNKNOWN':missing.append(decision)
        w['relation_edge_refs']=sorted(set(edge_refs))
        if failed:w['failed_conditions']=failed;w['uncertainty']=missing;rejected.append(w)
        elif missing:w['uncertainty']=missing;unknown.append(w)
        else:good.append(w)
    specified=all('event_id' in a for a in query['atoms'])
    return dict(result,status='MATCH' if good else 'UNKNOWN' if unknown else 'MISMATCH' if specified and rejected else 'NOT_FOUND',
                witnesses=good,uncertain_bindings=unknown,rejected_bindings=rejected,
                answer_scope='Scoped assertion records plus direct recorded object-edge evidence; not simultaneous truth or legal applicability')


def generate(views, registries):
    common,strict=identity_candidates(views)
    typed=set()
    for view in views:
        registry=registries[view['case_id']]; objects={o['id']:o for o in view['objects']}
        seeds=[s for e in view['events'] for s in [seed_event(e)] if s]
        edge_set={(e['op'],e['left'],e['right']) for e in registry['edges'] if e['decision']=='SUPPORTED'}
        for a,b in itertools.combinations(seeds,2):
            atoms=[{'var':'a','type':a['type'],'status':a['status']},{'var':'b','type':b['type'],'status':b['status']}]
            distinct={'op':'different','left':'a.id','right':'b.id'}
            for ra,va in sorted(a['roles'].items()):
                for rb,vb in sorted(b['roles'].items()):
                    for op in sorted(EDGE_OPS):
                        for lv,rv,lf,rf in [(va,vb,'a.roles.'+ra,'b.roles.'+rb),(vb,va,'b.roles.'+rb,'a.roles.'+ra)]:
                            if (op,lv,rv) in edge_set and relation_value(registry,objects,op,lv,rv)[0]=='MATCH':
                                typed.add(canonical_query({'atoms':atoms,'constraints':[distinct,{'op':op,'left':lf,'right':rf}]}))
    return {'cooccurrence':common,'identity':strict,'typed':sorted(typed)}


def pattern_family(query):
    """A display skeleton, NOT a learned cluster or semantic equivalence."""
    op=next((c['op'] for c in query['constraints'] if c['op']!='different'),'cooccurrence')
    key={'atoms':sorted([{k:a[k] for k in ('type','status')} for a in query['atoms']],key=canonical),'operator':op}
    types={a['type'] for a in query['atoms']}
    n=len(types & PROCEDURAL_TYPES)
    category='PROCEDURE_ONLY' if n==len(types) else 'MIXED' if n else 'FACT_ONLY'
    return digest(key)[:16],key,category


def summarize_patterns(patterns):
    families=defaultdict(list)
    for p in patterns:
        fid,skeleton,category=pattern_family(p['query'])
        families[fid].append(p)
        p['family_id']=fid;p['category']=category
    result=[]
    for fid,ps in sorted(families.items()):
        _,sk,category=pattern_family(ps[0]['query'])
        result.append({'id':fid,'skeleton':sk,'category':category,'query_ids':[p['id'] for p in ps],
                       'repeated_variants':sum(p['repeated'] for p in ps),
                       'meaning':'Display family only; role variants are retained and not equated'})
    return result
