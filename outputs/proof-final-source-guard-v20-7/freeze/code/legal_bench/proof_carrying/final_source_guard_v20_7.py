"""Versioned source-reconstruction final entry. No model calls or legal approval.

The producer may propose prose; only this exact, source-reviewed candidate can
become an accepted answer. Historical schemas, source reviews and outputs are
never edited. Semantic review remains a fallible model/human input.
"""
import copy
import json
from collections import defaultdict
from . import local_pipeline_v19_8 as legacy
from .rule_contracts_v19_7 import digest
from .schema_contract_v19_6 import loads, validate

VERSION = 'V20_7_FINAL_SOURCE_GUARD'
LABELS = ('SUPPORTED', 'UNSUPPORTED', 'UNRESOLVED')
COVERAGE = ('ACTORS_IDENTIFIED', 'PROPERTY_IDENTIFIED', 'EVENT_ATTRIBUTION',
            'COURT_STAGES', 'ADOPTED_REASONING', 'DECISIVE_COUNTERARGUMENTS',
            'UNCERTAINTY_PRESERVED', 'CONCLUSION_SCOPE',
            'NO_REJECTED_FACT_REENTRY', 'CLAIM_SUPPORT_ALIGNMENT',
            'NARRATIVE_COMPLETENESS')
AUXILIARY = {'coverage_limits', 'gaps', 'limits', 'assumptions'}


def detached(value):
    """Clone each occurrence; deepcopy alone preserves schema aliasing."""
    if isinstance(value, dict):
        return {k: detached(v) for k, v in value.items()}
    if isinstance(value, list):
        return [detached(v) for v in value]
    return copy.deepcopy(value)


def metadata_schema(schema):
    result = detached(schema)
    def walk(node, name=None):
        if not isinstance(node, dict):
            return
        if name in AUXILIARY and node.get('type') == 'array':
            node['uniqueItems'] = True
            node['maxItems'] = min(node.get('maxItems', 256), 8)
            if node.get('items', {}).get('type') == 'string':
                node['items']['maxLength'] = 480
        for k, v in node.get('properties', {}).items():
            walk(v, k)
        if 'items' in node:
            walk(node['items'])
        for v in node.get('$defs', {}).values():
            walk(v)
    walk(result)
    return result


def text():
    return {'type': 'string', 'minLength': 1}


def enum(values):
    return {'type': 'string', 'enum': list(values)}


def array(items, minimum=0, maximum=256):
    return {'type': 'array', 'items': detached(items), 'minItems': minimum,
            'maxItems': maximum, 'uniqueItems': True}


def obj(fields):
    return {'type': 'object', 'properties': detached(fields),
            'required': list(fields), 'additionalProperties': False}


def source_map(case):
    result = {}
    ids = [s['id'] for s in case['segments']]
    if len(ids) != len(set(ids)):
        raise ValueError('DUPLICATE_SOURCE_ID')
    for i, s in enumerate(case['segments'], 1):
        if s['text'].strip():
            result[s['id']] = s['id']
            result['SRC:' + str(i)] = s['id']
    return result


def registry(case, applied_parts):
    """Only reviewed, dependency-supported declarations are selectable.

    Pending/rejected content stays in the old audit; its IDs/statuses are kept
    here without injecting its prose into the producer's accepted material.
    """
    aliases = source_map(case)
    accepted, blocked = {}, {}
    part_names = [name for name, _ in applied_parts]
    if len(part_names) != len(set(part_names)):
        raise ValueError('DUPLICATE_PART_NAME')
    for part, result in applied_parts:
        pool = result['pool']
        if pool['source_sha256'] != digest(case['segments']):
            raise ValueError('STALE_PART_SOURCE')
        if not result.get('structure_checked') or result['independent']['status'] != 'OK':
            raise ValueError('PART_NOT_STRUCTURALLY_CHECKED')
        rows = pool['candidates']
        by_id = {d['id']: d for d in rows}
        if len(by_id) != len(rows):
            raise ValueError('DUPLICATE_DECLARATION_ID')
        cache = {}
        def eligible(key, active=()):
            if key in cache:
                return cache[key]
            if key in active:
                raise ValueError('DECLARATION_DEPENDENCY_CYCLE')
            row = by_id.get(key)
            ok = bool(row and row.get('proposed_label') == 'SUPPORTED'
                      and row.get('verification_state') == 'REVIEWED'
                      and row.get('verification_refs')
                      and all(r in aliases for r in row['verification_refs']))
            if ok:
                ok = all(eligible(dep, active + (key,)) for dep in row['dependencies'])
            cache[key] = ok
            return ok
        # Bind each J:n to its own audit row, not the first row for a premise.
        audits = defaultdict(list)
        for a in result['audit']['premise_judgments']:
            audits[a['premise']].append(a)
        judgment_audit = {}
        for pid, u in result['applied_proposals']['P']['analyses'].items():
            if len(audits[pid]) != len(u['judgments']):
                raise ValueError('JUDGMENT_AUDIT_CARDINALITY')
            for i, a in enumerate(audits[pid], 1):
                judgment_audit['P/' + pid + '/J:' + str(i)] = a
        for d in rows:
            key = part + '::' + d['id']
            if not eligible(d['id']):
                blocked[key] = {'label': d.get('proposed_label'),
                                'dependency_supported': False}
                continue
            value = {'id': key, 'kind': d['kind'], 'claim': detached(d['claim']),
                     'source_refs': sorted({aliases[r] for r in d['verification_refs']}),
                     'dependencies': [part + '::' + x for x in d['dependencies']],
                     'acceptance': 'MODEL_SOURCE_REVIEW_NOT_LEGAL_APPROVAL'}
            if d['kind'] == 'PREMISE_BASIS':
                a = judgment_audit.get(d['id'])
                if a is None:
                    raise ValueError('JUDGMENT_AUDIT_NOT_FOUND')
                value['conditional_state'] = a['conditional_state']
                value['computation_errors'] = detached(a['errors'])
            accepted[key] = value
    return {'accepted': accepted, 'blocked': blocked}


def final_schema(case, book):
    schema = metadata_schema(legacy.FINAL_SCHEMA)
    p = schema['properties']
    refs = array(enum(sorted(set(source_map(case).values()))), 1)
    claims = array(enum(sorted(book['accepted'])), 1)
    p['conclusion_claim_ids'] = array(enum(sorted(book['accepted'])), 0)
    p['result_status'] = enum(('SOURCE_RECONSTRUCTION', 'CONDITIONAL', 'UNRESOLVED'))
    actor = obj({'id': text(), 'name': text(), 'kind': enum(('PARTY', 'COURT', 'OTHER')),
                 'capacities': array(text(), 1), 'court_level': text(), 'refs': refs})
    property_ = obj({'id': text(), 'description': text(), 'refs': refs})
    event = obj({'id': text(), 'actor_id': text(), 'property_id': text(),
                 'court_context_id': text(), 'stage': text(),
                 'kind': enum(('PARTY_APPLICATION', 'PARTY_ASSERTION', 'PARTY_PAYMENT',
                               'PARTY_KNOWLEDGE', 'COURT_ORDER', 'COURT_REMAND', 'OTHER')),
                 'statement_status': text(), 'description': text(),
                 'claim_ids': claims, 'refs': refs})
    p['case_frame'] = obj({'actors': array(actor, 2, 32),
                          'properties': array(property_, 1, 16),
                          'events': array(event, 0, 64)})
    for name in ('grounds', 'counterarguments'):
        fields = p[name]['items']['properties']
        fields['claim_ids'] = detached(claims)
        fields['actor_ids'] = array(text())
        fields['property_ids'] = array(text())
        fields['event_ids'] = array(text())
        p[name]['items']['required'] = list(fields)
    # Hypothetical evidence belongs in a separate scenario task. It cannot repair
    # a historical answer by becoming an unchecked assumption.
    p['assumptions'] = array(text(), 0, 0)
    p['connection_handling']['items']['properties']['connection_id'] = enum(sorted(book['accepted']))
    for name in ('grounds', 'counterarguments', 'connection_handling'):
        fields = p[name]['items']['properties']
        for field in ('case_refs', 'refs'):
            if field in fields:
                fields[field]['items'] = enum(sorted(set(source_map(case).values())))
    schema['required'] = list(p)
    return schema


def final_task(case, rules, merged, applied_parts):
    book = registry(case, applied_parts)
    if not book['accepted']:
        raise ValueError('NO_SOURCE_REVIEWED_DECLARATIONS')
    schema = final_schema(case, book)
    source_ids = sorted(set(source_map(case).values()))
    rule_ids = sorted({x for r in rules for x in [r['id'], *r.get('source_refs', []),
                                               *[p['id'] for p in r['premises']]]})
    schema['properties']['grounds']['items']['properties']['rule_refs']['items'] = enum(rule_ids)
    prompt = '''Produce a complete historical source reconstruction, not a legal certificate.
Use the complete allowed source and only the selectable source-reviewed declaration
IDs to justify material grounds and the conclusion. A SUPPORTED use is not a TRUE
premise. A conditional_state or OPEN_TEXT limitation remains binding.
Identify concrete parties, their capacities, the specific property and distinct
court/procedural events in case_frame. PARTY_APPLICATION has the applying party as
actor; the hearing court is court_context_id, not the applicant. A court remand
has the issuing court as actor; preserve its level and stage. Use NONE for an
inapplicable event property/court context; never invent entities.
A legal prerequisite or 'if paid' does not establish payment. A contested knowledge
date remains contested unless actually found. Allegations, court findings and
adopted appellate reasoning remain distinct. Rejected/pending IDs cannot justify
facts, counterarguments or the conclusion. Unsupported facts belong in gaps, not
assumptions. This actual-reconstruction task requires assumptions=[]. New claims
must first receive a separately recorded source review and a new task version;
they cannot bypass that requirement by appearing in prose or the conclusion.
Preserve decisive opposition, actual uncertainty and the exact conclusion scope.
Do not compress the answer to fit 480 characters: substantive prose has no such
cap. No source text is removed. The candidate remains unaccepted until the exact
whole-answer source and coverage review passes. Output the supplied JSON schema.
'''
    material = {'selectable_claims': book['accepted'], 'blocked_ids': book['blocked'],
                'conditional_rules': merged['audit']['conditional_rules']}
    neutral_rules = copy.deepcopy(rules)
    for rule in neutral_rules:
        rule.pop('slot_variables', None)
        for premise in rule['premises']:
            premise.pop('expected', None)
    request = next(q for q in case['targets'] if q['id'] == 'Q1')
    aliases = {k: v for k, v in source_map(case).items() if k.startswith('SRC:')}
    prompt += '\nFIXED REQUEST:\n' + json.dumps(request, ensure_ascii=False)
    prompt += '\nLEGAL RULES (conditions are not observed facts):\n' + json.dumps(neutral_rules, ensure_ascii=False)
    prompt += '\nSOURCE ALIASES:\n' + json.dumps(aliases, ensure_ascii=False)
    prompt += '\nREVIEWED MATERIAL:\n' + json.dumps(material, ensure_ascii=False)
    prompt += '\nCOMPLETE ALLOWED SOURCE:\n' + '\n'.join(s['id'] + '\n' + s['text'] for s in case['segments'])
    prompt += '\nOUTPUT SCHEMA:\n' + json.dumps(schema, ensure_ascii=False)
    review_context = {'request': detached(request), 'rules': neutral_rules,
                      'conditional_rules': detached(material['conditional_rules'])}
    return {'version': VERSION, 'method': 'D', 'prompt': prompt, 'schema': schema,
            'input_sha256': digest({'prompt': prompt, 'schema': schema,
                                    'review_context': review_context}),
            'review_context': review_context,
            'source_sha256': digest(case['segments']), 'rule_sha256': digest(rules),
            'registry_sha256': digest(book), 'claim_registry': book,
            'source_ids': source_ids, 'rule_addresses': rule_ids,
            'source_input_truncated': False, 'semantic_success': False,
            'full_audit_saved_separately': True}


def verify_task(task, case):
    if task.get('version') != VERSION:
        raise ValueError('FINAL_TASK_VERSION')
    if task['input_sha256'] != digest({'prompt': task['prompt'], 'schema': task['schema'],
                                      'review_context': task['review_context']}):
        raise ValueError('FINAL_TASK_CHANGED')
    if task['registry_sha256'] != digest(task['claim_registry']):
        raise ValueError('FINAL_REGISTRY_CHANGED')
    if task['source_sha256'] != digest(case['segments']):
        raise ValueError('STALE_FINAL_SOURCE')
    request = next(q for q in case['targets'] if q['id'] == 'Q1')
    if task['review_context']['request'] != request:
        raise ValueError('STALE_FINAL_REQUEST')


def inspect_candidate(task, answer):
    validate(answer, task['schema'])
    errors = []
    frame = answer['case_frame']
    def keyed(rows, kind):
        ids = [r['id'] for r in rows]
        if len(ids) != len(set(ids)):
            errors.append('DUPLICATE_' + kind + '_ID')
        return {r['id']: r for r in rows}
    actors = keyed(frame['actors'], 'ACTOR')
    props = keyed(frame['properties'], 'PROPERTY')
    events = keyed(frame['events'], 'EVENT')
    if set(actors) & set(props) or set(actors) & set(events) or set(props) & set(events):
        errors.append('CROSS_KIND_ID_COLLISION')
    if sum(a['kind'] == 'PARTY' for a in actors.values()) < 2:
        errors.append('PARTIES_NOT_IDENTIFIED')
    accepted = task['claim_registry']['accepted']
    def claim_refs(row, field='claim_ids'):
        if any(c not in accepted for c in row[field]):
            errors.append('NONSELECTABLE_CLAIM')
    for a in actors.values():
        if a['kind'] != 'COURT' and a['court_level'] != 'NONE':
            errors.append('NONCOURT_HAS_COURT_LEVEL')
        if a['kind'] == 'COURT' and a['court_level'] in ('NONE', 'UNKNOWN'):
            errors.append('COURT_LEVEL_NOT_IDENTIFIED')
    for event in events.values():
        claim_refs(event)
        a = actors.get(event['actor_id'])
        context = actors.get(event['court_context_id'])
        if not a:
            errors.append('EVENT_ACTOR_NOT_FOUND')
        elif event['kind'].startswith('PARTY_') and a['kind'] != 'PARTY':
            errors.append('PARTY_EVENT_MISATTRIBUTED_TO_NONPARTY')
        elif event['kind'].startswith('COURT_') and a['kind'] != 'COURT':
            errors.append('COURT_EVENT_MISATTRIBUTED_TO_NONCOURT')
        if event['court_context_id'] != 'NONE' and (not context or context['kind'] != 'COURT'):
            errors.append('EVENT_COURT_CONTEXT_INVALID')
        if event['kind'].startswith('COURT_') and event['court_context_id'] != event['actor_id']:
            errors.append('ISSUING_COURT_CONTEXT_MISMATCH')
        if event['property_id'] != 'NONE' and event['property_id'] not in props:
            errors.append('EVENT_PROPERTY_NOT_FOUND')
    claim_refs(answer, 'conclusion_claim_ids')
    if answer['result_status'] != 'UNRESOLVED' and not answer['conclusion_claim_ids']:
        errors.append('CONCLUSION_WITHOUT_REVIEWED_SUPPORT')
    if answer['assumptions']:
        errors.append('UNCHECKED_ASSUMPTION_IN_ACTUAL_RECONSTRUCTION')
    for row in answer['grounds'] + answer['counterarguments']:
        claim_refs(row)
        for field, ids in [('actor_ids', actors), ('property_ids', props), ('event_ids', events)]:
            if any(i not in ids for i in row[field]):
                errors.append('NARRATIVE_' + field.upper() + '_INVALID')
        if any(r not in task['rule_addresses'] for r in row.get('rule_refs', [])):
            errors.append('FINAL_RULE_OUTSIDE_ALLOWLIST')
    return {'status': 'OK' if not errors else 'REJECTED', 'errors': sorted(set(errors)),
            'actor_count': len(actors), 'property_count': len(props), 'event_count': len(events)}


def narrative_units(answer):
    """Include every prose-bearing field, including gaps and handling reasons."""
    units = {}
    def walk(value, path):
        if isinstance(value, dict):
            for k, v in value.items():
                walk(v, path + [k])
        elif isinstance(value, list):
            for i, v in enumerate(value):
                walk(v, path + [i])
        elif isinstance(value, str):
            # IDs and references are checked mechanically; all other text and
            # classification strings receive the exact-payload semantic review.
            if path[-1] in ('id', 'request_id', 'actor_id', 'property_id', 'court_context_id', 'connection_id'):
                return
            if len(path) > 1 and path[-2] in ('refs', 'case_refs', 'rule_refs', 'claim_ids',
                                             'actor_ids', 'property_ids', 'event_ids', 'conclusion_claim_ids'):
                return
            key = 'U' + str(len(units) + 1)
            units[key] = {'path': path, 'value': value, 'sha256': digest({'path': path, 'value': value})}
    walk(answer, [])
    return units


def review_task(task, answer, case):
    verify_task(task, case)
    check = inspect_candidate(task, answer)
    if check['status'] != 'OK':
        raise ValueError('FINAL_CANDIDATE_REJECTED:' + str(check['errors']))
    units = narrative_units(answer)
    verdict = obj({'label': enum(LABELS), 'refs': array(enum(task['source_ids'])), 'reason': text()})
    bindings = {'version': VERSION, 'task_sha256': task['input_sha256'],
                'candidate_sha256': digest(answer), 'source_sha256': task['source_sha256'],
                'registry_sha256': task['registry_sha256'], 'rule_sha256': task['rule_sha256']}
    schema = obj({**{k: enum([v]) for k, v in bindings.items()},
                  'verdicts': obj({k: verdict for k in units}),
                  'coverage': obj({k: verdict for k in COVERAGE})})
    payload = {'bindings': bindings, 'units': units, 'candidate': answer,
               'reviewed_claims': task['claim_registry'],
               'request_and_rules': task['review_context'],
               'source': case['segments'], 'coverage_required': list(COVERAGE)}
    prompt = '''Independently verify this EXACT whole answer against the complete source.
Audit every U item in its candidate context. Confirm the actual actor/property,
event, date, modality, court level, attribution, adoption status and complete scope.
An if-clause or payment deadline is not actual payment. Contested knowledge is not
an established date. Landlords apply for withdrawal; courts decide applications.
Verify the issuing court of every remand directly. A supported intermediary label
does not override original text. Rejected facts may not reappear through a ground,
counterargument, explanation, conclusion, gap or handling reason. Do not invent a
replacement or guess missing evidence. Mark any definite mismatch UNSUPPORTED;
insufficient evidence or ambiguous meaning is UNRESOLVED. COVERAGE must inspect the
entire answer: report decisive omissions, missing concrete actors/property, lost
opposition/uncertainty and unfinished sentences. Never approve solely because a
string fits a schema. For CLAIM_SUPPORT_ALIGNMENT, require every material factual
assertion in grounds/counterarguments/conclusion/events to be justified by its
selected declaration IDs with the same actor, event, stage, modality and scope.
Direct source support cannot bypass a missing intermediate declaration. Require
a new declaration review/task instead. A source-supported use does not establish
a TRUE premise; respect each judgment's own conditional_state and computation
errors. Compare conclusion scope with the fixed request and supplied rules.
SUPPORTED/UNSUPPORTED require nonblank relevant source refs.
Classification strings can be SUPPORTED when contextually correct. Preserve all
hash bindings exactly. This is source review, not human gold or legal approval.
Return the strict review JSON; no corrected answer or majority vote.
'''
    prompt += json.dumps(payload, ensure_ascii=False)
    return {'version': VERSION, 'prompt': prompt, 'schema': schema,
            'bindings': bindings, 'units': units, 'candidate_check': check}


def accept_final(task, raw, technical_status, *, case, review=None):
    result = {'version': VERSION, 'answer': None, 'technical_status': technical_status,
              'legal_approval': False, 'semantic_evaluation': 'NOT_DONE',
              'input_sha256': task['input_sha256']}
    if technical_status != 'OK':
        result['contract_status'] = 'GENERATION_FAILED'
        return result
    try:
        verify_task(task, case)
        answer = loads(raw)
        check = inspect_candidate(task, answer)
        result['candidate_check'] = check
        if check['status'] != 'OK':
            result['contract_status'] = 'FINAL_CONTENT_CONTRACT_REJECTED'
            return result
        expected = review_task(task, answer, case)
        result['candidate_sha256'] = digest(answer)
        if review is None:
            result['contract_status'] = 'PENDING_WHOLE_ANSWER_SOURCE_REVIEW'
            return result
        validate(review, expected['schema'])
        issues = []
        for group in ('verdicts', 'coverage'):
            for key, v in review[group].items():
                if v['label'] in ('SUPPORTED', 'UNSUPPORTED') and not v['refs']:
                    issues.append({'group': group, 'id': key, 'reason': 'REVIEW_WITHOUT_SOURCE'})
                elif v['label'] != 'SUPPORTED':
                    issues.append({'group': group, 'id': key, 'reason': v['label']})
        result['source_review_issues'] = issues
        result['review_sha256'] = digest(review)
        if issues:
            result['contract_status'] = 'WHOLE_ANSWER_SOURCE_REVIEW_REJECTED_OR_UNRESOLVED'
            return result
        result.update(answer=answer, contract_status='MODEL_SOURCE_REVIEW_ACCEPTED_NOT_LEGAL_SUCCESS',
                      semantic_evaluation='MODEL_SOURCE_REVIEW_NOT_HUMAN_GOLD')
    except (ValueError, TypeError, KeyError) as exc:
        result.update(contract_status='FINAL_CONTRACT_OR_REVIEW_REJECTED', error=str(exc))
    return result
