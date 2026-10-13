"""Nonempty citations and source-reviewed role bindings; no payload repair."""
import copy
import json
from collections import Counter
from . import shared_sources_v20_3 as shared, declared_references_v20_4 as local
from .object_types_v19 import normalize, compare
from .rule_contracts_v19_7 import digest
from .schema_contract_v19_6 import validate

VERSION = 'V20_5_EVIDENCE_BINDING_GATE'
ROLE_DESCRIPTION = 'V20_5_EXPECTED_TYPE:'
# Exact generic descriptions, never role-name substrings or proper names.
TYPE_ALIASES = {
    'identified leased property': 'PROPERTY', 'identified property': 'PROPERTY',
    'leased property': 'PROPERTY', 'rented premises': 'PROPERTY',
    'person or association': 'PARTY',
}


def source_directory(case):
    return {'SRC:'+str(i): s for i, s in enumerate(case['segments'], 1)}


def citation_choices(case):
    return [k for k, s in source_directory(case).items()
            if isinstance(s['text'], str) and s['text'].strip()]


def role_types(rules):
    result = {}
    for r in rules:
        for p in r['premises']:
            types = {}
            for role, value in p.get('variables', {}).items():
                explicit = normalize(value)['canonical']
                if explicit is None:
                    original = p.get('original_variable_descriptions', {}).get(role, value)
                    key = ' '.join(original.split()).casefold() if isinstance(original, str) else ''
                    explicit = normalize(original)['canonical'] or TYPE_ALIASES.get(key)
                types[role] = explicit or 'UNMAPPED'
            result[p['id']] = types
    return result


def generation_schema(original, case, rules):
    """Keep source positions; only generation choices exclude blank anchors."""
    sc = shared.schema(original)
    choices = citation_choices(case)
    sc['$defs']['source_choice']['enum'] = choices
    member = sc['properties']['source_sets']['items']
    member['items']['enum'] = choices
    member['maxItems'] = len(choices)
    for pid, unit in sc['properties']['analyses']['properties'].items():
        for coll in ('uses', 'judgments'):
            props = unit['properties'][coll]['items']['properties']['role_objects']['properties']
            for role, spec in props.items():
                spec['description'] = ROLE_DESCRIPTION + role_types(rules).get(pid, {}).get(role, 'UNMAPPED')
    return sc


def binding_claim(raw, path):
    pid, coll, i, role = path[1], path[2], path[3], path[5]
    unit = raw['analyses'][pid]
    ref = unit[coll][i]['role_objects'][role]
    entity = unit['objects'][int(ref.split(':')[1])-1]
    return {'premise': pid, 'collection': coll, 'index': i, 'role': role,
            'reference': ref, 'object': entity}


def reviews_from_q(raw, case, rules, q, frozen_context):
    """Reuse existing source-verifier verdicts only for their frozen P/source/rules."""
    envelope = {'payload_sha256': digest(raw), 'source_sha256': digest(case['segments']),
                'rule_sha256': digest(rules), 'verdicts': []}
    if (frozen_context.get('original_P_sha256') != envelope['payload_sha256']
            or frozen_context.get('source_sha256') != envelope['source_sha256']
            or frozen_context.get('rule_sha256') != envelope['rule_sha256']
            or frozen_context.get('run_status') != 'OK'):
        envelope['adapter_status'] = 'STALE_OR_FAILED_VERIFIER_CONTEXT'
        return envelope
    from .source_verification_v20_2 import candidates
    pool = candidates(case, rules, raw, q)
    for d in pool['candidates']:
        if d['origin'] != 'P' or d['kind'] != 'OBJECT_BINDING' or d['verification_state'] != 'REVIEWED':
            continue
        _, pid, address, role_address = d['id'].split('/', 3)
        prefix, ordinal = address.split(':')
        coll = 'uses' if prefix == 'USE' else 'judgments'
        path = ['analyses', pid, coll, int(ordinal)-1, 'role_objects', role_address[5:]]
        envelope['verdicts'].append({'path': path, 'claim_sha256': digest(binding_claim(raw, path)),
                                    'label': d['proposed_label'], 'refs': d['verification_refs'],
                                    'reason': d['verifier_reason']})
    envelope['adapter_status'] = 'EXISTING_SOURCE_VERIFIER_MODEL_VERDICTS'
    return envelope


def audit(value, original_schema, case, rules, reviews=None):
    """Independent completed-JSON gate. Old bad citations/indices stay bad."""
    errors = []
    try:
        validate(value, shared.schema(original_schema))
        shared.check_expansion(value, shared.expand(value), original_schema)
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        return {'status': 'REJECTED_FORMAT', 'errors': [str(exc)], 'bindings': [],
                'information_rewritten': False, 'semantic_approval': False}
    refs = local.audit(value, shared.schema(original_schema))
    errors += [{'kind': 'INVALID_LOCAL_REFERENCE', **x} for x in refs['violations']]
    raw = shared.expand(value)
    directory = source_directory(case)
    for i, group in enumerate(value['source_sets']):
        for choice in group:
            if choice not in directory or not directory[choice]['text'].strip():
                errors.append({'kind': 'EMPTY_OR_MISSING_SOURCE', 'source': choice,
                               'path': ['source_sets', i]})
    if not errors:
        # Check exactly what the code will restore, independently of parser claims.
        from .source_contract_v19 import witness_location
        src = {s['id']: {'document': s['source_document'], 'original_line': s.get('original_line'),
                        'text': s['text']} for s in case['segments']}
        required = {w['source'] for u in raw['analyses'].values() for use in u['uses']
                    for w in use['witnesses'] if w['necessity'] == 'REQUIRED'}
        for choice in sorted(required):
            s = directory[choice]
            located = witness_location({'refs': [s['id']], 'quote': s['text']}, src)
            if located.get('error'):
                errors.append({'kind': 'REQUIRED_WITNESS_NOT_LOCATED', 'source': choice,
                               'reason': located['error']})
    rows = []
    expected = role_types(rules)
    review_index = {}
    review_errors = []
    if reviews is not None:
        if (not isinstance(reviews, dict) or reviews.get('payload_sha256') != digest(raw)
                or reviews.get('source_sha256') != digest(case['segments'])
                or reviews.get('rule_sha256') != digest(rules)):
            review_errors.append('STALE_BINDING_REVIEW')
        else:
            candidates = reviews.get('verdicts', [])
            if not isinstance(candidates, list):
                candidates = []; review_errors.append('MALFORMED_BINDING_REVIEW')
            safe = []
            for x in candidates:
                p = x.get('path') if isinstance(x, dict) else None
                if (not isinstance(p, list) or len(p) != 6 or p[0] != 'analyses'
                        or not isinstance(p[1], str) or p[2] not in ('uses', 'judgments')
                        or type(p[3]) is not int or p[3] < 0 or p[4] != 'role_objects'
                        or not isinstance(p[5], str)):
                    review_errors.append('MALFORMED_BINDING_REVIEW'); continue
                safe.append(x)
            counts = Counter(tuple(x['path']) for x in safe)
            for x in safe:
                path = tuple(x.get('path', []))
                if counts[path] != 1:
                    review_errors.append('DUPLICATE_BINDING_REVIEW')
                    continue
                review_index[path] = x
    for pid, unit in raw['analyses'].items():
        for coll in ('uses', 'judgments'):
            for i, row in enumerate(unit[coll]):
                for role, ref in row['role_objects'].items():
                    path = ['analyses', pid, coll, i, 'role_objects', role]
                    state = 'NOT_REVIEWED'
                    actual = 'UNMAPPED'
                    target = expected.get(pid, {}).get(role, 'UNMAPPED')
                    if ref == 'UNMAPPED':
                        state = 'UNMAPPED_BINDING'
                    else:
                        try:
                            entity = binding_claim(raw, path)['object']
                            actual = entity['type']
                        except (KeyError, ValueError, IndexError):
                            state = 'INVALID_REFERENCE'
                            entity = None
                        if entity is not None and compare(actual, target)['status'] == 'EXPLICIT_TYPE_CONFLICT':
                            state = 'EXPLICIT_TYPE_CONFLICT'
                            errors.append({'kind': state, 'path': path, 'actual': actual, 'expected': target})
                        elif entity is not None:
                            verdict = review_index.get(tuple(path))
                            if verdict:
                                rrefs = verdict.get('refs', [])
                                label = verdict.get('label')
                                valid = (verdict.get('claim_sha256') == digest(binding_claim(raw, path))
                                         and label in ('SUPPORTED', 'UNSUPPORTED', 'UNRESOLVED')
                                         and isinstance(verdict.get('reason'), str) and bool(verdict['reason'].strip())
                                         and isinstance(rrefs, list) and all(isinstance(x, str) for x in rrefs)
                                         and len(set(rrefs)) == len(rrefs)
                                         and all(x in citation_choices(case) for x in rrefs)
                                         and (bool(rrefs) or label == 'UNRESOLVED'))
                                state = 'REVIEW_'+label if valid else 'QUARANTINED_REVIEW'
                    rows.append({'path': path, 'reference': ref, 'actual_type': actual,
                                 'expected_type': target, 'state': state,
                                 'identity_established_by_code': False})
    rejected = sum(x['state'] == 'REVIEW_UNSUPPORTED' for x in rows)
    pending = sum(x['state'] not in ('REVIEW_SUPPORTED', 'REVIEW_UNSUPPORTED', 'EXPLICIT_TYPE_CONFLICT')
                  for x in rows)
    analyzed = sum(u['analysis_status'] == 'ANALYZED' for u in raw['analyses'].values())
    return {'version': VERSION,
            'status': ('REJECTED_EVIDENCE_OR_BINDING' if errors else
                       'NO_ANALYZED_UNITS' if not analyzed else
                       'BINDING_REVIEW_REJECTED' if rejected else
                       'BINDING_REVIEW_PENDING' if pending else 'READY_FOR_CONDITIONAL_PROCESSING'),
            'errors': errors, 'review_errors': review_errors, 'bindings': rows,
            'pending_bindings': pending, 'rejected_bindings': rejected,
            'binding_state_counts': dict(Counter(x['state'] for x in rows)), 'local_reference_audit': refs,
            'payload_sha256': digest(raw), 'source_sha256': digest(case['segments']),
            'rule_sha256': digest(rules),
            'information_rewritten': False, 'semantic_approval': False, 'legal_approval': False}


def process_saved(case, rules, part, compact, original_schema, technical_status='OK', reviews=None):
    """The new entry cannot promote a rejected/unreviewed binding into computation."""
    gate = audit(compact, original_schema, case, rules, reviews)
    result = {'version': VERSION, 'technical_status': technical_status,
              'contract_status': gate['status'], 'gate': gate, 'formal_answer': None,
              'conditional_audit': None, 'automatic_computation_status': 'NOT_RUN_GATE_NOT_READY',
              'usability': {'checked_use_count': 0, 'status': 'NOT_COMPUTED_GATE_NOT_READY'},
              'semantic_approval': False, 'legal_approval': False}
    if technical_status != 'OK' or gate['status'] != 'READY_FOR_CONDITIONAL_PROCESSING':
        return result
    from scripts.proof_pipeline_contract_v19_8 import process_saved as original_entry
    raw = shared.expand(compact)
    entry = original_entry(case, rules, part, json.dumps(raw, ensure_ascii=False, separators=(',', ':')),
                           original_schema, 'V19_8', technical_status)
    result.update(original_entry=entry, formal_answer=entry['formal_answer'],
                  conditional_audit=entry.get('conditional_audit'),
                  contract_status=entry['contract_status'],
                  automatic_computation_status='PROCESSED_SOURCE_REVIEWED_MODEL_BINDINGS')
    checks = (entry.get('conditional_audit') or {}).get('checks', [])
    result['usability'] = {'checked_use_count': len(checks),
                           'use_dispositions': dict(Counter(x['disposition'] for x in checks)),
                           'analysis_coverage': entry.get('coverage'),
                           'status': 'REPORTED_SEPARATELY_FROM_TRANSPORT'}
    return result


def accept_saved(input_dir, output_dir, case, rules, part, original_schema, reviews=None):
    """Read a generation; save acceptance separately, never edit its raw answer."""
    from pathlib import Path
    from .artifact_state_v20_2 import immutable
    source, destination = Path(input_dir).resolve(), Path(output_dir).resolve()
    if source == destination or source in destination.parents:
        raise ValueError('ACCEPTANCE_MUST_NOT_WRITE_INTO_GENERATION')
    run = json.loads((source/'run.json').read_text())
    if run.get('run_status') != 'OK':
        result = {'version': VERSION, 'technical_status': run.get('run_status'),
                  'formal_answer': None, 'contract_status': 'GENERATION_FAILED',
                  'conditional_audit': None, 'automatic_computation_status': 'NOT_RUN_GENERATION_FAILED'}
    else:
        value = json.loads((source/'parsed.json').read_text())
        result = process_saved(case, rules, part, value, original_schema, 'OK', reviews)
    immutable(destination/'acceptance.json', result)
    immutable(destination/'formal-answer.json', {'answer': result['formal_answer'],
              'status': result['contract_status'], 'semantic_approval': False, 'legal_approval': False})
    return result


INSTRUCTION = '''EVIDENCE AND BINDING CONTRACT V20.5:
Keep the complete supplied source and original SRC addresses. Only nonblank source
anchors in the decoder's citation vocabulary can serve as cited evidence. Select
relevant anchors; a shared source set is not permission to cite the whole case.
Declare records and objects before uses, then judgments. Restart EV, OBJ and USE
at 1 in EACH analysis. Match each role to the declared object's actual identity,
not just an available ordinal. Declare a separately grounded missing object or
write UNMAPPED; never reuse a person as property or one date as a different date.
Explicitly incompatible declared types are blocked. Unknown types and identities
remain unverified. Source-grounded binding reviews are separate from generation;
unreviewed bindings cannot be promoted into automated conditional computation.
Return all work keys and preserve counterevidence, UNKNOWN and NOT_ANALYZED.
'''


def reset_example():
    """Two nonempty synthetic analyses demonstrate local ordinal restart."""
    from .local_pipeline_v19_6 import synthetic_example
    example = synthetic_example()
    first = example['analyses']['SYN.P1']
    first['objects'][0]['type'] = 'PERSON'
    first['judgments'][0]['basis_mode'] = 'REPORT_STATEMENT_ONLY'
    comp = first['judgments'][0]['components'][0]
    comp.pop('description'); comp['component_id'] = 'SYN.P1.K1'
    second = copy.deepcopy(first)
    second['records'] = second['records'][:1]
    second['records'][0]['proposition'] = 'The trial found Mira entered Field Y.'
    second['records'][0]['refs'] = ['SRC:4']
    second['objects'][0]['label'] = 'Mira'
    second['objects'][0]['refs'] = ['SRC:4']
    second['objects'][0]['identity_basis'] = 'SRC:4 explicitly identifies Mira in the separate trial finding.'
    second['uses'] = second['uses'][:1]
    second['uses'][0]['claim'] = 'Report the separate trial finding about Mira.'
    second['uses'][0]['witnesses'] = [{'source': 'SRC:4', 'necessity': 'REQUIRED'}]
    j = second['judgments'][0]
    j['uses'] = ['USE:1']; j['basis'] = 'Only the local finding is reported.'
    j['components'][0]['component_id'] = 'SYN.P2.K1'
    j['necessary_limits'][0]['refs'] = ['SRC:4']
    example['analyses']['SYN.P2'] = second
    example['coverage_limits'] = ['Entire example is fictional; not target facts or legal rules.']
    return shared.pack(example)


def prompt(previous):
    """Replace instruction/example blocks only; original source bytes stay intact."""
    head, separator, source = previous.partition('\nALLOWED SOURCE (copy the adjacent SRC address):\n')
    if not separator:
        raise ValueError('SOURCE_SECTION_BOUNDARY_MISSING')
    head = head.replace(local.INSTRUCTION, '')
    head = head.replace('Reference only declared local items; dynamic existence is checked on import, not guaranteed by the decoder.',
                        'Reference only declared local items; the decoder enforces their actual local bounds.')
    head = head.replace('records and objects cite only relevant unique refs; a witness selects ONE source address in its source field.',
                        'records and objects cite relevant ref_set identifiers; witnesses select source_set and necessity.')
    start = head.index('\nFICTIONAL EXAMPLE ONLY:')
    stop = head.index('\nFIXED REQUEST:', start)
    teaching = ('\nFICTIONAL TWO-ANALYSIS RESET EXAMPLE ONLY:\n'
                'SRC:1: Rowan denied Monday entry. SRC:2: The trial found Rowan entered Garden Z on Monday. '
                'SRC:3: A witness saw Rowan depart on Tuesday. SRC:4: The trial found Mira entered Field Y.\n'
                'SYN.P1 reports the trial finding about Rowan; SYN.P2 reports the trial finding about Mira. '
                'Each analysis has a separately declared actor:PERSON.\n')
    head = head[:start] + teaching + json.dumps(reset_example(), separators=(',', ':')) + head[stop:]
    return INSTRUCTION + local.INSTRUCTION + head + separator + source
