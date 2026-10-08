"""V5 interface checks. These compute declared uses, never certify legal truth.

V4 code and frozen results stay unchanged. Address conversion is exact; there is
no semantic repair, object merging, or keyword interpretation of limitations.
"""
import copy
import hashlib
import json
import re
from collections import Counter

from .hybrid_v3 import analyze as declared_checks, source_errors
from .pipeline_v4 import compact, expand_compact, display as old_display

USES = ('CONDITION_INFERENCE', 'RECORD_EXISTENCE', 'PROVEN_FACT', 'TARGET_ACCEPTANCE')
EFFECTS = ('USE_BLOCK', 'PROPOSITION_BLOCK', 'NOTE', 'SCOPE_UNMAPPED')
STATES = ('SUPPORTED', 'REFUTED', 'UNRESOLVED', 'UNSUPPORTED')
STATEMENTS = ('PARTY_CLAIM', 'DENIAL', 'ADMISSION', 'TESTIMONY',
              'PRIOR_COURT_FINDING', 'RECORDED_DOCUMENT', 'UNKNOWN')


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def address_directory(template):
    """Single versioned directory; each enum value maps to one legal leaf."""
    rows = {}
    for test in template['tests']:
        for branch in test.get('branches', []) or [{'id': '', 'text': ''}]:
            key = 'ADDR-%03d' % (len(rows) + 1)
            rows[key] = {'test_id': test['id'], 'branch_id': branch['id'],
                         'test_text': test.get('text', test.get('proposition', '')),
                         'branch_text': branch.get('text', '')}
    pairs = [(r['test_id'], r['branch_id']) for r in rows.values()]
    if len(set(pairs)) != len(pairs):
        raise ValueError('DUPLICATE_LEGAL_ADDRESS')
    reserved = {x['id'] for key in ('tests', 'elements') for x in template.get(key, [])}
    if set(rows) & reserved:
        raise ValueError('ADDRESS_NAMESPACE_COLLISION')
    return rows


def decode_address(record, directory, allow_legacy=True):
    if not isinstance(record, dict):
        return None
    if 'condition_address' in record:
        key = record['condition_address']
        if not isinstance(key, str) or key not in directory:
            return None
        row = directory[key]
        # Never let a second, contradictory representation override the enum.
        if any(k in record and record[k] != row[k] for k in ('test_id', 'branch_id')):
            return None
        return {'test_id': row['test_id'], 'branch_id': row['branch_id']}
    if allow_legacy:
        pair = (record.get('test_id'), record.get('branch_id'))
        for row in directory.values():
            if pair == (row['test_id'], row['branch_id']):
                return {'test_id': row['test_id'], 'branch_id': row['branch_id']}
    return None


def encode_address(test_id, branch_id, directory):
    for key, row in directory.items():
        if (test_id, branch_id) == (row['test_id'], row['branch_id']):
            return key
    raise ValueError('ILLEGAL_TEST_BRANCH_PAIR')


def string_list(value):
    return isinstance(value, list) and all(isinstance(x, str) for x in value)


def import_proposal(value, template, sources, case_id, allow_legacy=True):
    directory = address_directory(template)
    out = {k: [] for k in ('bindings', 'evidence', 'limitations', 'conditions', 'coverage_limits')}
    quarantined, coverage, safeguards = [], [], []

    def reject(kind, position, record, reason):
        quarantined.append({'kind': kind, 'position': position,
                            'record': copy.deepcopy(record), 'reason': reason})

    def refs_valid(refs):
        return string_list(refs) and bool(refs) and not source_errors(refs, sources, case_id)

    def address(row):
        return decode_address(row, directory, allow_legacy)

    if not isinstance(value, dict) or not all(isinstance(value.get(k), list) for k in ('bindings', 'evidence')):
        return {'status': 'STRUCTURE_ERROR', 'usable': False, 'raw_proposal': value,
                'projection': out, 'quarantine': [], 'restriction_coverage': [], 'safeguards': []}

    claims = {x['id'] for x in template['claims'] if x.get('expression', {}).get('op') != 'UNSUPPORTED'}
    counts = Counter(x.get('id') for x in value['bindings'] if isinstance(x, dict) and isinstance(x.get('id'), str))
    for i, b in enumerate(value['bindings']):
        valid = (isinstance(b, dict) and all(isinstance(b.get(k), str) and bool(b[k].strip())
                 for k in ('id', 'objects', 'event', 'stage')) and counts[b['id']] == 1
                 and refs_valid(b.get('refs')) and string_list(b.get('claim_ids'))
                 and bool(b['claim_ids']) and set(b['claim_ids']) <= claims)
        if valid:
            out['bindings'].append(copy.deepcopy(b))
        else:
            reject('binding', i, b, 'INVALID_BINDING_STRUCTURE_SOURCE_OR_CLAIM')
    bids = {x['id'] for x in out['bindings']}
    counts = Counter(x.get('id') for x in value['evidence'] if isinstance(x, dict) and isinstance(x.get('id'), str))
    for i, e in enumerate(value['evidence']):
        valid = (isinstance(e, dict) and all(isinstance(e.get(k), str) for k in ('id', 'binding_id', 'record', 'statement_status'))
                 and counts[e['id']] == 1 and e['binding_id'] in bids and refs_valid(e.get('refs'))
                 and e['statement_status'] in STATEMENTS and isinstance(e.get('uses'), list))
        if not valid:
            reject('evidence', i, e, 'INVALID_RECORD_STRUCTURE_SOURCE_OR_BINDING')
            continue
        retained = copy.deepcopy(e)
        retained['uses'] = []
        for j, u in enumerate(e['uses']):
            a = address(u)
            if a is None or u.get('direction') not in ('SUPPORT', 'OPPOSE', 'UNKNOWN') or u.get('use') not in USES:
                reject('use', '%s/%s' % (i, j), u, 'INVALID_ADDRESS_OR_USE; parent record retained')
                continue
            retained['uses'].append(dict(a, direction=u['direction'], use=u['use']))
        out['evidence'].append(retained)
    by_e = {x['id']: x for x in out['evidence']}

    for kind in ('conditions', 'limitations'):
        values = value.get(kind, [])
        if not isinstance(values, list):
            reject(kind, None, values, 'INVALID_ARRAY')
            if kind == 'limitations':
                coverage.append({'position': None, 'status': 'UNMAPPED_RESTRICTION',
                                 'reason': 'Restriction array unreadable; no global block inferred.', 'raw_record': copy.deepcopy(values)})
            continue
        id_counts = Counter(x.get('id') for x in values if isinstance(x, dict) and isinstance(x.get('id'), str))
        for i, x in enumerate(values):
            a = address(x)
            row = x if isinstance(x, dict) else {}
            ids = row.get('evidence_ids')
            bid = row.get('binding_id')
            binding_ok = isinstance(bid, str) and bid in bids
            ids_ok = (string_list(ids) and all(e in by_e and by_e[e]['binding_id'] == bid for e in ids))
            valid = a is not None and binding_ok and ids_ok
            if kind == 'conditions':
                valid = valid and row.get('assessment') in STATES and isinstance(row.get('gap'), str)
            else:
                valid = (valid and isinstance(row.get('id'), str) and bool(row['id']) and id_counts[row['id']] == 1
                         and refs_valid(row.get('refs')) and row.get('effect') in EFFECTS
                         and row.get('use') in USES and isinstance(row.get('reason'), str))
                # USE_BLOCK without a specific witness does not mean the whole proposition.
                valid = valid and not (row.get('effect') == 'USE_BLOCK' and not ids)
            if valid:
                fields = ('assessment', 'gap') if kind == 'conditions' else ('id', 'use', 'effect', 'reason', 'refs')
                out[kind].append(dict(a, binding_id=bid, evidence_ids=copy.deepcopy(ids),
                                     **{k: copy.deepcopy(row[k]) for k in fields}))
                continue
            reject(kind, i, x, 'INVALID_LOCAL_STRUCTURE_ADDRESS_OR_REFERENCE')
            if kind != 'limitations':
                continue

            # Range and source validity are independent. Preserve a known range
            # as pending even when the alleged restriction cannot be validated.
            range_known = binding_ok and a is not None and row.get('use') in USES
            whole = row.get('effect') == 'PROPOSITION_BLOCK' and ids == []
            specific = string_list(ids) and bool(ids)
            mapped_ids = [e for e in ids if e in by_e and by_e[e]['binding_id'] == bid] if specific else []
            can_guard = range_known and row.get('effect') != 'NOTE' and (whole or bool(mapped_ids))
            c = {'position': i, 'binding_id': bid, 'address': a, 'use': row.get('use'),
                 'status': 'PENDING_RESTRICTION_IN_KNOWN_SCOPE' if can_guard else 'UNMAPPED_RESTRICTION',
                 'scope': 'WHOLE_PROPOSITION' if whole else 'SPECIFIC_EVIDENCE' if specific else 'UNDETERMINED',
                 'reason': 'Restriction could not be validated; this is not legal opposition or absence of source evidence.',
                 'raw_record': copy.deepcopy(x), 'safeguard_ids': []}
            if can_guard:
                guard_id = 'IMPORT-PENDING-%d' % i
                while guard_id in id_counts:
                    guard_id += '-INTERNAL'
                guard = dict(a, id=guard_id, evidence_ids=[] if whole else mapped_ids,
                             binding_id=bid, use=row['use'], effect='SCOPE_UNMAPPED', refs=[],
                             reason='Declared restriction pending validation in this exact scope; no semantic repair.')
                out['limitations'].append(guard)
                safeguards.append(dict(guard, raw_position=i, scope=c['scope']))
                c['safeguard_ids'].append(guard['id'])
            coverage.append(c)

    raw_coverage = value.get('coverage_limits', [])
    if string_list(raw_coverage):
        out['coverage_limits'] = copy.deepcopy(raw_coverage)
    else:
        reject('coverage_limits', None, raw_coverage, 'INVALID_ARRAY')
    usable = bool(out['bindings'] and (out['evidence'] or out['conditions']))
    return {'status': 'PARTIAL' if usable and quarantined else 'OK' if usable else 'NO_USABLE_PROPOSAL',
            'usable': usable, 'raw_proposal': copy.deepcopy(value), 'projection': out,
            'quarantine': quarantined, 'restriction_coverage': coverage, 'safeguards': safeguards,
            'address_directory': directory, 'condition_summary_required': False,
            'semantic_certification': False}


def process(value, template, sources, case_id, allow_legacy=True):
    imp = import_proposal(value, template, sources, case_id, allow_legacy)
    if not imp['usable']:
        return imp, None
    checks = declared_checks(imp['projection'], template, sources, case_id)
    directory = address_directory(template)
    checks['address_directory'] = directory
    checks['import_quarantine'] = imp['quarantine']
    checks['restriction_coverage'] = imp['restriction_coverage']
    checks['restriction_safeguards'] = imp['safeguards']
    checks['check_coverage'] = 'INCOMPLETE_RESTRICTION_VALIDATION' if imp['restriction_coverage'] else 'DECLARED_SCOPE_CHECKED'
    for u in checks['evidence_use_checks']:
        u['condition_address'] = encode_address(u['test_id'], u['branch_id'], directory)
    for c in checks['conditions']:
        c['model_assessments'] = c.pop('model_predictions')
        c['assessment_not_overwritten'] = c.pop('prediction_not_overwritten')
        c['model_output_status'] = 'PRODUCED' if c['model_assessments'] else 'NOT_PRODUCED_OPTIONAL'
        c['model_summary_required'] = False
        structural = [u for u in checks['evidence_use_checks']
                      if u['binding_id'] == c['binding_id'] and u['test_id'] == c['test_id']]
        uses = [u for u in structural if u['use'] in ('CONDITION_INFERENCE', 'PROVEN_FACT')]
        available = [u for u in uses if u['use_status'] == 'USABLE_AS_MODEL_PROPOSED']
        c['evidence_use_summary'] = {
            'structurally_valid_uses': len(structural), 'condition_connections': len(uses),
            'usable_condition_connections': len(available),
            'support': [u['evidence_id'] for u in available if u['direction'] == 'SUPPORT'],
            'opposition': [u['evidence_id'] for u in available if u['direction'] == 'OPPOSE'],
            'pending': [dict(evidence_id=u['evidence_id'], condition_address=u['condition_address'],
                             direction=u['direction'], use_status=u['use_status'],
                             blocked_by=u['blocked_by'], mapping_questions=u['mapping_questions'])
                        for u in uses if u not in available or u['direction'] == 'UNKNOWN'],
            'basis': 'Declared uses in the current proposal, not source truth or independent votes.'}
        c['program_assessment_origin'] = ('DECLARED_EVIDENCE_USE_AGGREGATION' if available else
                                         'DECLARED_USES_RESTRICTED' if uses else 'NO_USABLE_CONNECTION_IN_CURRENT_PROPOSAL')
        c['connection_coverage_note'] = ('' if available else
                                        'The current proposal provides no usable condition connection; no claim that the original source has no evidence.')
    return imp, checks


def display(material, source_map):
    """Reversible containment display sorted by original document position only.

    source_map is the existing V4 exact-source audit, not inferred event dates.
    Unknown positions are kept with an explicit limitation, never dropped.
    """
    view, aliases = old_display(material)
    maps = {x['source_id']: x for x in source_map}
    docs = list(dict.fromkeys(str(s['document_id']) for s in material['sources'].values()))
    ordering = []
    for row in view['records']:
        sid = row['source_id']
        m = maps.get(sid, {})
        raw_range = m.get('raw_char_range')
        valid = (str(m.get('document_id')) == str(row['document_id']) and m.get('text_exact_in_raw') is True
                 and m.get('allowed_text_sha256') == digest(row['text'])
                 and isinstance(raw_range, list) and len(raw_range) == 2
                 and all(isinstance(n, int) for n in raw_range) and 0 <= raw_range[0] <= raw_range[1]
                 and raw_range[1] - raw_range[0] == len(row['text']))
        match = re.match(r'^IK-' + re.escape(str(row['document_id'])) + r':L(\d+)(?::|$)', sid)
        ordering.append({'source_id': sid, 'document_id': row['document_id'],
                         'raw_path': m.get('raw_path'), 'raw_sha256': m.get('raw_sha256'),
                         'raw_char_range': raw_range if valid else None,
                         'line': int(match.group(1)) if match else None,
                         'position_status': 'AUDITED_ORIGINAL_CHAR_RANGE' if valid else 'SOURCE_ADDRESS_LINE_ONLY' if match else 'POSITION_UNKNOWN'})
    # Ranges from different raw windows cannot be compared as if one document.
    order_by = {x['source_id']: x for x in ordering}
    modes = {}
    for doc in docs:
        local = [x for x in ordering if str(x['document_id']) == doc]
        origins = {(x['raw_path'], x['raw_sha256']) for x in local}
        modes[doc] = 'RAW_CHARS' if local and len(origins) == 1 and all(x['raw_char_range'] is not None for x in local) else 'LINES'

    def key(row):
        x = order_by[row['source_id']]
        doc = str(row['document_id'])
        if modes[doc] == 'RAW_CHARS':
            position = (0, x['raw_char_range'][0], x['raw_char_range'][1])
        else:
            position = (0, x['line'], 0) if x['line'] is not None else (1, 0, 0)
        return (docs.index(doc), *position, row['source_id'])

    view['records'].sort(key=key)
    audit = {'rows': ordering, 'document_order_mode': modes,
             'ordering': 'Original source position; not inferred event time or legal importance.',
             'coverage_limits': [x for x in ordering if x['position_status'] != 'AUDITED_ORIGINAL_CHAR_RANGE']}
    return view, aliases, audit
