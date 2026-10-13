"""Versioned final binding bridge and reviewed-frame rendering.

Does not modify the historical retrieval pipeline or any old proposal. Business
addresses retain their analysis scope; tensor/global positions are never identities.
Frame facts require a separately saved exact-payload source review. The writer
cannot generate or replace them. Its prose still requires whole-answer source review.
"""
import copy
import json
import re

from . import final_source_guard_v20_7 as prior
from .artifact_state_v20_2 import digest
from .schema_contract_v19_6 import loads, validate

VERSION = 'V20_8_FINAL_BINDINGS_1'
FRAME_VERSION = 'V20_8_FRAME_SOURCE_REVIEW_1'
KINDS = ('PARTY_APPLICATION', 'PARTY_ASSERTION', 'PARTY_PAYMENT',
         'PARTY_KNOWLEDGE', 'COURT_ORDER', 'COURT_REMAND', 'AUTHORITY_NOTICE',
         'RETIREMENT', 'SUBLETTING', 'OTHER')


def clone(value):
    return copy.deepcopy(value)


def scoped(case, part, premise, address):
    return '/'.join((str(case['case_id']), digest(case['segments'])[:16], part,
                     'P', premise, address))


def build_bridge(case, parts, merged):
    """Keep every local declaration and map actual global positions explicitly."""
    units = merged['canonical']['analysis_units']
    global_objects = merged['canonical']['objects']
    source = prior.source_map(case)
    addresses, global_map, rows = {}, {}, []
    seen_parts = set()
    for part, applied in parts:
        if part in seen_parts:
            raise ValueError('DUPLICATE_PART')
        seen_parts.add(part)
        if applied['pool']['source_sha256'] != digest(case['segments']):
            raise ValueError('BRIDGE_STALE_SOURCE')
        analyses = applied['applied_proposals']['P']['analyses']
        scopes = {u['premise']: u['scope'] for u in units
                  if u['scope'].startswith(part + ':')}
        if len(scopes) != len(analyses):
            raise ValueError('BRIDGE_ANALYSIS_COVERAGE')
        for pid, unit in analyses.items():
            for kind, field in [('OBJ', 'objects'), ('EV', 'records'),
                                ('USE', 'uses'), ('J', 'judgments')]:
                for i, original in enumerate(unit[field], 1):
                    local = kind + ':' + str(i)
                    full = scoped(case, part, pid, local)
                    addresses[(part, pid, local)] = full
                    rows.append({'id': full, 'part': part, 'premise': pid,
                                 'local_address': local, 'kind': kind,
                                 'original': clone(original),
                                 'original_sha256': digest(original)})
            globals_ = [(i, o) for i, o in enumerate(global_objects, 1)
                        if o.get('part_scope') == scopes[pid]]
            if len(globals_) != len(unit['objects']):
                raise ValueError('BRIDGE_OBJECT_CARDINALITY')
            for local_index, (position, obj) in enumerate(globals_, 1):
                expected = clone(unit['objects'][local_index - 1])
                expected['refs'] = [source[r] for r in expected['refs']]
                actual = {k: v for k, v in obj.items() if k != 'part_scope'}
                if actual != expected:
                    raise ValueError('BRIDGE_OBJECT_CONTENT_OR_ORDER_CHANGED')
                global_map[position] = addresses[(part, pid, 'OBJ:' + str(local_index))]
    if len(global_map) != len(global_objects):
        raise ValueError('BRIDGE_GLOBAL_OBJECT_COVERAGE')
    def resolve(part, pid, value, expected_kind):
        if value == 'UNMAPPED':
            return value
        if not isinstance(value, str) or not re.fullmatch(expected_kind + r':[1-9][0-9]*', value):
            raise ValueError('BRIDGE_WRONG_LOCAL_KIND:' + str(value))
        if (part, pid, value) not in addresses:
            raise ValueError('BRIDGE_UNDECLARED_LOCAL_REFERENCE:' + str(value))
        return addresses[(part, pid, value)]
    def normalize(value, part, pid, field=None):
        if isinstance(value, dict):
            result = {}
            for k, v in value.items():
                if k == 'role_objects':
                    result[k] = {role: resolve(part, pid, ref, 'OBJ') for role, ref in v.items()}
                elif k == 'proposed_local_address':
                    result['proposed_scoped_address'] = resolve(part, pid, v, 'OBJ')
                elif k == 'court_level':
                    # Record attribution is provenance, not the actor's institution.
                    result['reporting_court_level'] = v
                else:
                    result[k] = normalize(v, part, pid, k)
            return result
        if isinstance(value, list):
            return [normalize(x, part, pid, field) for x in value]
        if isinstance(value, str):
            if field in ('records',):
                return resolve(part, pid, value, 'EV')
            if field in ('uses', 'opposition_uses', 'alternatives'):
                return resolve(part, pid, value, 'USE')
            if field == 'refs' and value in source:
                return source[value]
        return value
    book = prior.registry(case, parts)
    normalized = {}
    for key, row in book['accepted'].items():
        origin = row['origin_declaration_id']
        part, rest = origin.split('::', 1)
        fields = rest.split('/')
        # Identity LINK entries carry explicitly scoped endpoints, not local rows.
        if fields[0] == 'P' and len(fields) > 2:
            cl = normalize(row['claim'], part, fields[1])
        else:
            cl = clone(row['claim'])
        normalized[key] = {**clone(row), 'claim': cl}
    routes = clone(merged['audit']['conditional_rules'])
    def global_id(number):
        if number == 0:
            return 'UNMAPPED'
        if type(number) is not int or number not in global_map:
            raise ValueError('BRIDGE_UNDECLARED_GLOBAL_REFERENCE')
        return global_map[number]
    for route in routes:
        route['binding'] = {k: global_id(v) for k, v in route['binding'].items()}
        route['binding_candidates'] = {k: [global_id(v) for v in vs]
                                      for k, vs in route.get('binding_candidates', {}).items()}
        route['branch_bindings'] = [{k: global_id(v) for k, v in b.items()}
                                    for b in route.get('branch_bindings', [])]
    result = {'version': VERSION, 'source_sha256': digest(case['segments']),
              'declarations': rows, 'global_positions': {str(k): v for k, v in global_map.items()},
              'normalized_claims': normalized, 'conditional_rules': routes,
              'original_registry_sha256': digest(book), 'identity_merges': 0,
              'original_material_preserved': True}
    result['sha256'] = digest(result)
    return result


def frame_units(frame):
    units = {}
    for field in ('actors', 'properties', 'events'):
        for i, row in enumerate(frame[field]):
            key = ('A' if field == 'actors' else 'P' if field == 'properties' else 'E') + '%02d' % (i + 1)
            units[key] = {'path': [field, i], 'row': clone(row)}
    return units


def frame_errors(frame, source_ids):
    errors = []
    groups = {k: {r['id']: r for r in frame[k]} for k in ('actors', 'properties', 'events')}
    all_ids = [r['id'] for k in groups for r in frame[k]]
    if len(all_ids) != len(set(all_ids)):
        errors.append('FRAME_DUPLICATE_OR_CROSS_KIND_ID')
    for group in groups:
        for row in frame[group]:
            if not row.get('refs') or any(r not in source_ids for r in row['refs']):
                errors.append('FRAME_SOURCE_OUTSIDE_SNAPSHOT')
    actors = groups['actors']
    for a in actors.values():
        if a['kind'] not in ('PARTY', 'COURT', 'OTHER'):
            errors.append('FRAME_ACTOR_KIND')
        if (a['kind'] != 'COURT' and a['court_level'] != 'NONE') or (a['kind'] == 'COURT' and a['court_level'] in ('NONE', 'UNKNOWN')):
            errors.append('FRAME_INSTITUTION_LEVEL')
    for e in groups['events'].values():
        a = actors.get(e['actor_id'])
        if a is None:
            errors.append('FRAME_ACTOR_MISSING')
        if e['kind'] not in KINDS:
            errors.append('FRAME_EVENT_KIND')
        elif e['kind'].startswith('COURT_') and (a is None or a['kind'] != 'COURT' or e['court_context_id'] != e['actor_id']):
            errors.append('FRAME_ISSUING_COURT_MISMATCH')
        elif e['kind'].startswith('PARTY_') and (a is None or a['kind'] != 'PARTY'):
            errors.append('FRAME_PARTY_EVENT_MISMATCH')
        elif e['kind'] == 'AUTHORITY_NOTICE' and (a is None or a['kind'] != 'OTHER'):
            errors.append('FRAME_AUTHORITY_EVENT_MISMATCH')
        for field in ('court_context_id', 'reporting_court_id'):
            context = actors.get(e[field])
            if e[field] != 'NONE' and (context is None or context['kind'] != 'COURT'):
                errors.append('FRAME_COURT_CONTEXT_MISMATCH')
        if e['property_id'] != 'NONE' and e['property_id'] not in groups['properties']:
            errors.append('FRAME_PROPERTY_MISSING')
        if any(x not in actors for x in e['affected_actor_ids']):
            errors.append('FRAME_AFFECTED_ACTOR_MISSING')
    return sorted(set(errors))


def frame_review_task(case, frame, bridge=None):
    source_ids = sorted(s['id'] for s in case['segments'] if s['text'].strip())
    errors = frame_errors(frame, source_ids)
    if errors:
        raise ValueError(str(errors))
    originals = {d['id']: d['original'] for d in bridge['declarations'] if d['kind'] == 'OBJ'} if bridge else {}
    links = {}
    for row in frame['actors'] + frame['properties']:
        for origin in row.get('origin_object_ids', []):
            if origin not in originals or origin in links:
                raise ValueError('FRAME_UNDECLARED_OR_MULTIPLE_IDENTITY_LINK')
            links[origin] = row['id']
    bindings = {'version': FRAME_VERSION, 'source_sha256': digest(case['segments']),
                'frame_sha256': digest(frame), 'bridge_sha256': bridge['sha256'] if bridge else 'NONE'}
    units = frame_units(frame)
    verdict = prior.obj({'label': prior.enum(prior.LABELS),
                         'refs': prior.array({'$ref': '#/$defs/source_id'}), 'reason': prior.text()})
    schema = prior.obj({**{k: prior.enum([v]) for k, v in bindings.items()},
                        'verdicts': prior.obj({k: verdict for k in units})})
    schema['$defs'] = {'source_id': prior.enum(source_ids)}
    payload = {'bindings': bindings, 'frame': frame, 'units': units,
               'linked_original_objects': {k: originals[k] for k in links},
               'source_aliases': {k: v for k, v in prior.source_map(case).items() if k.startswith('SRC:')},
               # Metadata is retained in source.json; every source text and its
               # exact address/order are displayed without repeated provenance.
               'source': [{'id': s['id'], 'text': s['text']} for s in case['segments']]}
    prompt = '''Verify every proposed actor, property and event in this EXACT frame
against the complete source. The structured actor ID, affected actor IDs, issuing
court, reporting court, court context, event kind, statement status, stage and
description must agree with each other and with the source. Verify every proposed
origin_object_ids identity link against its linked original object and source;
an old object's erroneous type may be corrected only in this NEW reviewed frame,
not by accepting its old blocked declaration. A court is not a
litigant. A government notice is not a party allegation; retirement is not an
application. Distinguish appellate majority, dissent, quoted allegation, finding,
legal prerequisite and actual conduct. Never convert conditional payment into
payment or disputed knowledge into a fixed date. Mark any material error or
unsupported precision UNSUPPORTED, ambiguity UNRESOLVED. Do not repair the frame
or assume a familiar case. SUPPORTED/UNSUPPORTED require relevant nonempty source
refs. Return ONE strict JSON matching the supplied schema, preserving bindings.
This is a model source review, not human gold or legal approval.\n'''
    prompt += json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    prompt += '\nOUTPUT SCHEMA:\n' + json.dumps(schema, separators=(',', ':'))
    return {'bindings': bindings, 'schema': schema, 'prompt': prompt, 'units': units}


def reviewed_frame_book(case, frame, review, bridge=None):
    rt = frame_review_task(case, frame, bridge)
    validate(review, rt['schema'])
    source_ids = {s['id'] for s in case['segments'] if s['text'].strip()}
    for v in review['verdicts'].values():
        if v['label'] != 'SUPPORTED' or not v['refs'] or any(r not in source_ids for r in v['refs']):
            raise ValueError('FRAME_NOT_SOURCE_REVIEW_ACCEPTED')
    book = {}
    for key, unit in rt['units'].items():
        row = unit['row']
        book['F' + key] = {'id': 'F' + key, 'kind': 'FRAME_FACT',
                           'claim': clone(unit), 'source_refs': review['verdicts'][key]['refs'],
                           'dependencies': [], 'acceptance': 'MODEL_SOURCE_REVIEW_NOT_LEGAL_APPROVAL',
                           'origin_declaration_id': 'V20_8_FRAME/' + key}
    for key, unit in rt['units'].items():
        if unit['path'][0] == 'events' and unit['row']['claim_ids'] != ['F' + key]:
            raise ValueError('FRAME_EVENT_SUPPORT_NOT_OWN_REVIEWED_DECLARATION')
    return book


def final_task(case, previous_task, bridge, frame, frame_review):
    prior.verify_task(previous_task, case)
    if bridge['source_sha256'] != digest(case['segments']) or bridge['original_registry_sha256'] != previous_task['registry_sha256']:
        raise ValueError('BRIDGE_TASK_MISMATCH')
    if digest({k: v for k, v in bridge.items() if k != 'sha256'}) != bridge['sha256']:
        raise ValueError('BRIDGE_CHANGED')
    book = clone(previous_task['claim_registry'])
    for key, value in reviewed_frame_book(case, frame, frame_review, bridge).items():
        if key in book['accepted']:
            raise ValueError('FRAME_CLAIM_ID_COLLISION')
        book['accepted'][key] = value
    full_schema = prior.final_schema(case, book)
    full_schema['$defs']['source_id'] = prior.enum(sorted(s['id'] for s in case['segments'] if s['text'].strip()))
    for field in ('actors', 'properties'):
        spec = full_schema['properties']['case_frame']['properties'][field]['items']
        spec['properties']['origin_object_ids'] = prior.array(prior.text())
        spec['required'] = list(spec['properties'])
    full_schema['properties']['case_frame']['properties']['events']['items']['properties']['kind'] = prior.enum(KINDS)
    e = full_schema['properties']['case_frame']['properties']['events']['items']
    e['properties']['reporting_court_id'] = prior.text()
    e['properties']['affected_actor_ids'] = prior.array(prior.text())
    e['required'] = list(e['properties'])
    full_schema['$defs']['rule_address'] = prior.enum(previous_task['rule_addresses'])
    full_schema['properties']['grounds']['items']['properties']['rule_refs']['items'] = {'$ref': '#/$defs/rule_address'}
    for collection in ('grounds', 'counterarguments'):
        props = full_schema['properties'][collection]['items']['properties']
        for field, rows in [('actor_ids', frame['actors']), ('property_ids', frame['properties']), ('event_ids', frame['events'])]:
            props[field] = prior.array(prior.enum([x['id'] for x in rows]))
    writer_schema = clone(full_schema)
    del writer_schema['properties']['case_frame']
    writer_schema['required'] = list(writer_schema['properties'])
    verification_task = clone(previous_task)
    verification_task.update(schema=full_schema, claim_registry=book,
                             registry_sha256=digest(book))
    verification_task['review_context']['conditional_rules'] = clone(bridge['conditional_rules'])
    identity_links = {origin: row['id'] for row in frame['actors'] + frame['properties']
                      for origin in row['origin_object_ids']}
    material = {'case_frame': frame, 'reviewed_entity_identity_links': identity_links,
                'global_position_to_scoped_address': bridge['global_positions'],
                'object_definitions': {d['id']: d['original'] for d in bridge['declarations'] if d['kind'] == 'OBJ'},
                'selectable_claims': {**bridge['normalized_claims'],
                **{k: v for k, v in book['accepted'].items() if k.startswith('F')}},
                'blocked_ids': book['blocked'], 'conditional_rules': bridge['conditional_rules']}
    prompt = '''Write a complete historical source reconstruction for the fixed request.
The reviewed case_frame is supplied INPUT and rendered by code; do not output,
rename, infer or rebind its actors, properties or events. Its actor court_level
describes the institution itself (NONE for parties/government). A declaration's
reporting_court_level is the court recording/adopting that proposition, not the
actor who performed it. Its legal beneficiary is not the issuing actor. All
addresses include scope; a local OBJ:1 is not a global identity.
Use ONLY selectable declaration IDs with the SAME assertion, actor, event,
modality, stage and scope. Adding valid but unrelated claim IDs does not provide
support. FRAME_FACT declarations support the exact reviewed actor/property/event.
SUPPORTED evidence use is not a TRUE premise; preserve conditional_rules UNKNOWN,
OPEN_TEXT and computation limitations. Distinguish reconstruction of what a court
held from an independently executable legal certificate. State concrete actors
and premises. Cover decisive opposition, majority/dissent, limitations and the
actual disposition. Do not turn a prerequisite into performed conduct, alleged
knowledge into a fact or procedural relief into finally decided entitlement.
New material claims require a new reviewed declaration and task version. Record
unresolved matters honestly; assumptions=[] in this historical task. The 480
character limit is ONLY for auxiliary notes, not conclusion or explanation.
Return exactly the writer JSON schema. The whole rendered answer still requires
an exact-payload independent source and coverage review.\n'''
    prompt += '\nFIXED REQUEST:\n' + json.dumps(previous_task['review_context']['request'])
    prompt += '\nRULES:\n' + json.dumps(previous_task['review_context']['rules'])
    prompt += '\nREVIEWED MATERIAL:\n' + json.dumps(material, ensure_ascii=False, separators=(',', ':'))
    prompt += '\nCOMPLETE ALLOWED SOURCE:\n' + '\n'.join(s['id'] + '\n' + s['text'] for s in case['segments'])
    prompt += '\nOUTPUT SCHEMA:\n' + json.dumps(writer_schema, separators=(',', ':'))
    verification_task['prompt'] = prompt
    verification_task['input_sha256'] = digest({k: verification_task[k] for k in ('prompt', 'schema', 'review_context')})
    task = {'version': VERSION, 'prompt': prompt, 'schema': writer_schema,
            'frame': clone(frame), 'frame_review_sha256': digest(frame_review),
            'bridge_sha256': bridge['sha256'], 'verification_task': verification_task,
            'source_sha256': digest(case['segments']), 'source_input_truncated': False}
    task['input_sha256'] = digest(task)
    return task


def verify_task(task, case):
    if task['version'] != VERSION or digest({k: v for k, v in task.items() if k != 'input_sha256'}) != task['input_sha256']:
        raise ValueError('FINAL_BINDING_TASK_CHANGED')
    if task['source_sha256'] != digest(case['segments']):
        raise ValueError('FINAL_BINDING_SOURCE_CHANGED')
    prior.verify_task(task['verification_task'], case)


def render(task, writer, case):
    verify_task(task, case)
    validate(writer, task['schema'])
    answer = {**clone(writer), 'case_frame': clone(task['frame'])}
    validate(answer, task['verification_task']['schema'])
    if frame_errors(answer['case_frame'], task['verification_task']['source_ids']):
        raise ValueError('RENDERED_FRAME_INVALID')
    return answer


def review_task(task, writer, case):
    result = prior.review_task(task['verification_task'], render(task, writer, case), case)
    start = result['prompt'].index('{"bindings":')
    payload = json.loads(result['prompt'][start:])
    all_claims = payload['reviewed_claims']['accepted']
    answer = payload['candidate']
    used = set(answer['conclusion_claim_ids'])
    for collection in ('grounds', 'counterarguments'):
        for row in answer[collection]:
            used.update(row['claim_ids'])
    for row in answer['case_frame']['events']:
        used.update(row['claim_ids'])
    used.update(r['connection_id'] for r in answer['connection_handling'])
    used.update(k for k in all_claims if k.startswith('F'))
    pending = list(used)
    while pending:
        for dep in all_claims[pending.pop()]['dependencies']:
            if dep not in used:
                used.add(dep)
                pending.append(dep)
    payload['reviewed_claims']['accepted'] = {k: all_claims[k] for k in sorted(used)}
    payload['source'] = [{'id': s['id'], 'text': s['text']} for s in case['segments']]
    payload['review_display'] = {'selected_claims_and_all_dependencies': sorted(used),
                                'full_registry_saved_sha256': task['verification_task']['registry_sha256'],
                                'all_original_source_text_displayed': True,
                                'provenance_metadata_saved_in_source_json': True}
    result['prompt'] = result['prompt'][:start] + json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    result['prompt'] += '\nOUTPUT SCHEMA:\n' + json.dumps(result['schema'], separators=(',', ':'))
    result['review_display'] = payload['review_display']
    return result


def accept_final(task, raw, technical_status, *, case, review=None):
    if technical_status != 'OK':
        return {'version': VERSION, 'answer': None, 'technical_status': technical_status,
                'contract_status': 'GENERATION_FAILED', 'legal_approval': False}
    try:
        answer = render(task, loads(raw), case)
        if review is not None:
            parsed = loads(review) if isinstance(review, str) else review
            valid_refs = {s['id'] for s in case['segments'] if s['text'].strip()}
            if any(r not in valid_refs for group in ('verdicts', 'coverage')
                   for v in parsed.get(group, {}).values() for r in v.get('refs', [])):
                raise ValueError('BLANK_OR_UNDECLARED_REVIEW_SOURCE_REFERENCE')
        result = prior.accept_final(task['verification_task'], json.dumps(answer),
                                   technical_status, case=case, review=review)
        result.update(version=VERSION, writer_sha256=digest(loads(raw)),
                      frame_sha256=digest(task['frame']), frame_rendered_from_reviewed_input=True)
        return result
    except (ValueError, KeyError, TypeError) as exc:
        return {'version': VERSION, 'answer': None, 'technical_status': technical_status,
                'contract_status': 'FINAL_BINDING_CONTRACT_REJECTED', 'error': str(exc),
                'legal_approval': False}
