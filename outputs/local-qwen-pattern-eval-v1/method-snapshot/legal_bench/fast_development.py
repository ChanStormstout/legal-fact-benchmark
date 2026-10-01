"""Single-pass, source-anchored development discovery; never a held-out score."""
import copy
import itertools
import json
import random
import re
from collections import Counter
from pathlib import Path
from .core import canonical, digest, read, write_new
from .engine import canonical_query
from .conditional_engine import execute as conditional_execute, field_value, iso_date

VERSION = 'single-pass-development-20-v1'
VOCABULARY = {
    'LEASE_PROPERTY': ['landlord', 'tenant', 'property', 'agreement'],
    'OCCUPY_PROPERTY': ['occupant', 'property'],
    'OWN_PROPERTY': ['owner', 'property'],
    'PAY_RENT': ['payer', 'payee', 'property'],
    'SET_RENT': ['landlord', 'tenant', 'property'],
    'SERVE_NOTICE': ['sender', 'recipient', 'property'],
    'SUBLET_PROPERTY': ['tenant', 'subtenant', 'property'],
    'SURRENDER_PROPERTY': ['surrenderer', 'recipient', 'property'],
    'TRANSFER_TITLE': ['transferor', 'transferee', 'property'],
    'BUILD_ON_PROPERTY': ['actor', 'property'],
    'DISPOSSESS': ['actor', 'dispossessed', 'property'],
    'FILE_EVICTION': ['filer', 'respondent', 'property'],
    'FILE_OTHER_PROCEEDING': ['filer', 'respondent', 'property'],
    'GRANT_EVICTION': ['beneficiary', 'affected_party', 'property'],
    'REJECT_EVICTION': ['claimant', 'opponent', 'property'],
    'DELIVER_POSSESSION': ['deliverer', 'recipient', 'property'],
    'CHANGE_USE': ['actor', 'property'],
    'DAMAGE_PROPERTY': ['actor', 'property'],
    'ENTER_AGREEMENT': ['party', 'counterparty', 'property', 'agreement'],
    'DEATH': ['person'],
}
STATUSES = {'NARRATED', 'COURT_FOUND', 'ALLEGED', 'REJECTED', 'DISPUTED', 'UNKNOWN'}
CONFIG = {'version': VERSION, 'sample_role': 'DEVELOPMENT_ALLOW_METHOD_CHANGES',
          'min_support': 2, 'budget': 1000, 'seed': 20260930,
          'seed_statuses': ['COURT_FOUND', 'NARRATED'], 'polarity': 'POSITIVE',
          'max_joins': 1, 'extra_conditions': 0,
          'candidate_order': 'Canonical query string, before support is observed',
          'audit_rule': 'First 3 repeated relation patterns by fixed candidate order plus 3 seeded random other executed patterns; if no repeats first 3 executed plus random 3. Per pattern first relation witness and first extra cooccurrence binding in sample order, else first cooccurrence witness. Maximum 12 binding items.',
          'held_out': False, 'labels': 'SINGLE_WEB_EXTRACTION_NOT_HUMAN_GOLD',
          'meaning': 'Two source assertions with positive polarity and retained narrative/finding status; not legal sufficiency, simultaneous truth or a prediction.',
          'limitations': ['One extraction per case; no full semantic annotation audit',
                         'Support counts documents; confirmed duplicate disputes excluded but unresolved relations remain',
                         'Fixed task vocabulary is predefined, not discovered fact clusters',
                         'No temporal, amount aggregation or arbitrary qualifier formalization in this first run']}


def parse_local(raw):
    """Remove a presentation wrapper; never change a semantic field or quote."""
    text = raw.decode('utf-8-sig').strip()
    repairs = []
    if text.startswith('```'):
        m = re.fullmatch(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if m:
            text = m.group(1); repairs.append('REMOVED_CODE_FENCE')
    try:
        return json.loads(text), repairs
    except ValueError:
        # One unambiguous complete JSON value surrounded by prose is a format repair.
        decoder = json.JSONDecoder()
        matches = []
        for m in re.finditer(r'\{', text):
            try:
                obj, end = decoder.raw_decode(text[m.start():])
                if isinstance(obj, dict) and isinstance(obj.get('cases'), list):
                    matches.append(obj)
            except ValueError:
                pass
        if len(matches) != 1: raise ValueError('No unique complete cases JSON; retain raw file')
        return matches[0], repairs + ['EXTRACTED_UNIQUE_JSON_FROM_PROSE']


def import_case(annotation, source):
    """Quarantine a bad record or field, not the entire otherwise usable batch."""
    if annotation.get('case_id') != source['case_id']: raise ValueError('Case mismatch')
    pmap = {s['id']: s for s in source['segments']}
    changes, excluded, errors = [], [], []
    def anchored(seq):
        return (isinstance(seq, list) and bool(seq) and all(isinstance(e, dict) and
                e.get('segment_id') in pmap and isinstance(e.get('quote'), str) and bool(e['quote']) and
                e['quote'] in pmap[e['segment_id']]['text'] for e in seq))
    objects, seen = {}, Counter(o.get('id') for o in annotation.get('objects', []) if isinstance(o, dict))
    for obj in annotation.get('objects', []):
        if not isinstance(obj, dict) or not isinstance(obj.get('id'), str):
            excluded.append({'collection': 'objects', 'record': obj, 'reason': 'INVALID_OBJECT_ID'}); continue
        if seen[obj['id']] != 1 or not anchored(obj.get('evidence')):
            excluded.append({'collection': 'objects', 'record': obj, 'reason': 'DUPLICATE_ID_OR_UNLOCATED_QUOTE'}); continue
        objects[obj['id']] = copy.deepcopy(obj)
    units = annotation.get('units', [])
    valid_units = [u for u in units if isinstance(u, dict) and isinstance(u.get('id'), str) and anchored(u.get('evidence'))]
    ids = [u['id'] for u in valid_units]
    if len(ids) != len(set(ids)): raise ValueError('Duplicate unit ID')
    primary = [u for u in valid_units if u.get('primary') is True]
    if len(primary) != 1: raise ValueError('Exactly one source-anchored primary unit needed')
    pid = primary[0]['id']; events = []
    counts = Counter(e.get('id') for e in annotation.get('events', []) if isinstance(e, dict))
    for original in annotation.get('events', []):
        event = copy.deepcopy(original)
        if not isinstance(event, dict) or not isinstance(event.get('id'), str) or counts[event['id']] != 1:
            excluded.append({'collection': 'events', 'record': original, 'reason': 'INVALID_OR_DUPLICATE_EVENT_ID'}); continue
        eid = event['id']
        reason = None
        if event.get('type') not in VOCABULARY: reason = 'OUTSIDE_VOCABULARY'
        elif event.get('unit_id') != pid: reason = 'NOT_PRIMARY_REQUEST_UNIT'
        elif not anchored(event.get('evidence')): reason = 'UNLOCATED_EVENT_QUOTE'
        elif event.get('known_error') is True: reason = 'MODEL_FLAGGED_ERROR'
        elif event.get('status') not in STATUSES or event.get('polarity') not in ['POSITIVE','NEGATIVE','UNKNOWN']: reason = 'INVALID_STATE'
        elif not isinstance(event.get('roles'), dict): reason = 'INVALID_ROLES'
        elif event.get('kind') not in ['FACT','PROCEDURAL_ACT']: reason = 'NOT_FACT_OR_PROCEDURAL_ACT'
        if reason:
            excluded.append({'collection': 'events', 'record': original, 'reason': reason}); continue
        blocked = []
        def block(field, why): blocked.append({'affected_fields': [field], 'reason': why, 'kind': 'LOCAL_ISOLATION'})
        role_evidence = event.get('role_evidence', {})
        for role, value in list(event['roles'].items()):
            if role not in VOCABULARY[event['type']]:
                block('roles.'+role,'ROLE_OUTSIDE_FIXED_TYPE'); continue
            if value is None: block('roles.'+role, 'UNKNOWN_OBJECT'); continue
            if value not in objects:
                block('roles.'+role,'DANGLING_OR_QUARANTINED_OBJECT')
            elif objects[value].get('identity_resolved') is not True:
                block('roles.'+role,'UNRESOLVED_OBJECT_IDENTITY')
            elif not anchored(role_evidence.get(role)):
                block('roles.'+role,'OBJECT_BINDING_QUOTE_UNLOCATED')
        for role in VOCABULARY[event['type']]:
            if role not in event['roles']: event['roles'][role] = None
        unresolved = event.get('unresolved', [])
        if not isinstance(unresolved, list): block('*', 'MALFORMED_UNRESOLVED')
        else:
            for u in unresolved:
                field = u.get('field') if isinstance(u,dict) else None
                recognized = field in ['type','polarity','status','time','roles','attributes','*'] or isinstance(field,str) and field.startswith(('roles.','attributes.'))
                block(field if recognized else '*', str(u.get('reason','UNKNOWN')) if isinstance(u,dict) else 'INVALID_UNRESOLVED')
        for field in ['time', 'attributes', 'scope', 'origin']:
            if field not in event:
                event[field] = None if field == 'time' else {}
                changes.append({'event_id':eid,'action':'MISSING_OPTIONAL_FIELD_SET_UNKNOWN','field':field})
        if event['time'] is not None and (not iso_date(event['time']) or not anchored(event.get('time_evidence'))):
            block('time','UNKNOWN_OR_UNLOCATED_DATE')
        # Unparsed limitations must not silently disappear from computation.
        if event['scope'] and not event.get('scope_parsed', False): block('*','UNPARSED_SCOPE')
        if event['status'] == 'UNKNOWN': block('status','UNKNOWN_STATEMENT_STATUS')
        if event['status'] == 'COURT_FOUND' and not anchored(event.get('status_evidence')): block('status','FINDING_EVIDENCE_UNLOCATED')
        if event['polarity'] == 'UNKNOWN': block('polarity','UNKNOWN_POLARITY')
        event['source_assertion'] = copy.deepcopy(original)
        event['field_contract'] = {'type_unresolved': any('type' in b['affected_fields'] or '*' in b['affected_fields'] for b in blocked), 'blocked': blocked}
        event['evidence'] = [dict(e, page=pmap[e['segment_id']].get('page'), source_url=source['url']) for e in event['evidence']]
        events.append(event)
    # Exact duplicated source propositions are excluded from mining, without claiming event identity.
    dedup, unique = {}, []
    for event in events:
        key = canonical({k:event.get(k) for k in ['type','roles','unit_id','status','polarity','time','scope','evidence']})
        if key in dedup:
            excluded.append({'collection':'events','record':event,'reason':'EXACT_DUPLICATE_ASSERTION','duplicate_of':dedup[key]})
        else: dedup[key]=event['id'];unique.append(event)
    return {'case_id':source['case_id'],'units':[primary[0]],'objects':list(objects.values()),'events':unique,
            'excluded':excluded,'local_repairs':changes,'errors':errors,'input_hash':digest(annotation),
            'source_hash':source['text_sha256'],'semantic_review':'NOT_DONE_SINGLE_PASS','held_out':False}


def seed_event(event):
    if event['status'] not in CONFIG['seed_statuses'] or event['polarity'] != 'POSITIVE': return None
    if any(field_value(event, f)[1] for f in ['type','status','polarity','id']): return None
    roles = {}
    for role in sorted(event['roles']):
        v, why = field_value(event,'roles.'+role)
        if not why: roles[role]=v
    return dict(event, roles=roles)


def candidates(views):
    relation, common = set(), set()
    for view in views:
        es = [seed_event(e) for e in view['events']]; es = [e for e in es if e]
        for a,b in itertools.combinations(es,2):
            atoms=[{'var':'a','type':a['type'],'status':a['status']},{'var':'b','type':b['type'],'status':b['status']}]
            distinct={'op':'different','left':'a.id','right':'b.id'}
            base={'atoms':atoms,'constraints':[distinct]};common.add(canonical_query(base))
            for ra,va in sorted(a['roles'].items()):
                for rb,vb in sorted(b['roles'].items()):
                    if va == vb and va is not None:
                        relation.add(canonical_query({'atoms':atoms,'constraints':[distinct,{'op':'same','left':'a.roles.'+ra,'right':'b.roles.'+rb}]}))
    return sorted(common),sorted(relation)


def execute(view,q):
    r=conditional_execute(view,q)
    r['assumption']='PROVISIONAL_MODEL_ASSERTIONS_WITH_FIELD_ISOLATION_NOT_REFERENCE'
    for key in ['witnesses','uncertain_bindings','rejected_bindings']:
        for w in r[key]:
            em={e['id']:e for e in view['events']}
            w['objects']={var:copy.deepcopy(em[eid]['roles']) for var,eid in w['binding'].items()}
            w['role_evidence']={var:copy.deepcopy(em[eid].get('role_evidence',{})) for var,eid in w['binding'].items()}
    return r


def run(views,config=CONFIG):
    if len({v['case_id'] for v in views}) != len(views):raise ValueError('Duplicate case IDs')
    common,relation=candidates(views);allsets={'cooccurrence':common,'relation':relation};result={}
    for kind,qs in allsets.items():
        entries=[]
        for key in qs[:config['budget']]:
            q=json.loads(key);rows=[{'case_id':v['case_id'],'result':execute(v,q)} for v in views]
            support=sum(r['result']['status']=='MATCH' for r in rows)
            entries.append({'id':digest(q)[:16],'query':q,'support':support,'repeated':support>=config['min_support'],'results':rows})
        result[kind]={'generated':len(qs),'executed':len(entries),'frontier':qs[config['budget']:],
                      'all_candidates':qs,'search_complete':len(qs)<=config['budget'],'patterns':entries}
    # Paired comparison keeps both states and types identical, removing only the ID join.
    for p in result['relation']['patterns']:
        baseline={'atoms':p['query']['atoms'],'constraints':[c for c in p['query']['constraints'] if c['op']!='same']}
        p['cooccurrence_results']=[{'case_id':v['case_id'],'result':execute(v,baseline)} for v in views]
        p['cooccurrence_support']=sum(r['result']['status']=='MATCH' for r in p['cooccurrence_results'])
        p['cooccurrence_extra_bindings']=sum(len({canonical(w['binding']) for w in b['result']['witnesses']}-{canonical(w['binding']) for w in a['result']['witnesses']}) for a,b in zip(p['results'],p['cooccurrence_results']))
    return {'config':config,'views_hash':digest(views),'methods':result,'held_out':False,'accuracy':None}


def audit_items(results):
    ps=results['methods']['relation']['patterns'];repeated=[p for p in ps if p['repeated']]
    first=(repeated if repeated else ps)[:3];rest=[p for p in ps if p not in first]
    picked=first+random.Random(CONFIG['seed']).sample(rest,min(3,len(rest)))
    items=[]
    for p in picked:
        positive=next((r for r in p['results'] if r['result']['witnesses']),None)
        if positive:
            items.append({'id':p['id']+'-R','pattern_id':p['id'],'query':p['query'],'case_id':positive['case_id'],'method':'relation','witness':positive['result']['witnesses'][0]})
        extra=None
        for a,b in zip(p['results'],p['cooccurrence_results']):
            good={canonical(w['binding']) for w in a['result']['witnesses']}
            for w in b['result']['witnesses']:
                if canonical(w['binding']) not in good:
                    extra={'case_id':b['case_id'],'witness':w};break
            if extra:break
        if extra:
            items.append(dict(extra,id=p['id']+'-C',pattern_id=p['id'],query=p['query'],method='cooccurrence_extra'))
    return {'selection_rule':CONFIG['audit_rule'],'pattern_ids':[p['id'] for p in picked],'items':items,'no_accuracy_denominator':True}
