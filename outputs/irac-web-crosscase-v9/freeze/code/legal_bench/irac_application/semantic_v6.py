"""V6: independent records, scoped uses and explicit model premises.

No edge sign is a legal truth value. This audit is not supplied to the final LLM.
Source roles come from the frozen input containers, never model-assigned IDs.
"""
import copy
from collections import Counter

from .aligned_logic import evaluate
from .contract_v5 import display, STATEMENTS, STATES, decode_address, address_directory


def catalogue(template):
    result = {}
    for test in template['tests']:
        for b in test.get('branches', []) or [{'id': '', 'text': test['text']}]:
            key = b['id'] or test['id']
            if key in result:
                raise ValueError('DUPLICATE_CONDITION_SELECTOR')
            result[key] = {'test_id': test['id'], 'branch_id': b['id'],
                           'proposition': b['text'], 'parent_proposition': test['text']}
    return result


def source_catalogue(material, law):
    result = {}
    for sid, row in material['sources'].items():
        if str(row['document_id']) != str(material['case_id']):
            raise ValueError('TARGET_SOURCE_DOCUMENT_ID_CONFLICT:' + sid)
        result[sid] = dict(copy.deepcopy(row), role='CASE_RECORD')
    for row in law:
        sid = row['source_id']
        if sid in result:
            raise ValueError('CASE_LAW_ADDRESS_COLLISION:' + sid)
        result[sid] = dict(copy.deepcopy(row), role='LEGAL_AUTHORITY')
    return result


def refs_ok(refs, sources, role=None):
    return (isinstance(refs, list) and bool(refs)
            and all(isinstance(r, str) and r in sources for r in refs)
            and (role is None or all(sources[r]['role'] == role for r in refs)))


def index_ok(index, values):
    return type(index) is int and 1 <= index <= len(values)


def process(value, template, material, law):
    cat = catalogue(template)
    sources = source_catalogue(material, law)
    if not isinstance(value, dict):
        return {'usable': False, 'status': 'STRUCTURE_ERROR', 'raw_proposal': value}, None
    original = copy.deepcopy(value)
    value = copy.deepcopy(value)
    records, arrangements, uses, rows, quarantine, coverage = [], [], [], [], [], []

    def isolate(kind, index, raw, reason):
        quarantine.append({'kind': kind, 'position': index, 'raw': copy.deepcopy(raw), 'reason': reason})

    for key in ('records', 'arrangements', 'conditions'):
        if not isinstance(value.get(key), list):
            isolate(key, None, value.get(key), 'MISSING_OR_UNREADABLE_LOCAL_ARRAY; other arrays retained')
            value[key] = []

    for i, raw in enumerate(value['records'], 1):
        r = raw if isinstance(raw, dict) else {}
        valid = (isinstance(r.get('text'), str) and bool(r['text'].strip())
                 and r.get('statement_status') in STATEMENTS and refs_ok(r.get('refs'), sources))
        case_refs = [s for s in r.get('refs', []) if isinstance(s, str) and s in sources
                     and sources[s]['role'] == 'CASE_RECORD'] if isinstance(r.get('refs'), list) else []
        records.append({'record_id': 'R%d' % i, 'position': i, 'raw': copy.deepcopy(raw),
                        'interface_valid': valid, 'case_refs': case_refs,
                        'source_roles': {s: sources[s]['role'] for s in r.get('refs', []) if s in sources}
                        if isinstance(r.get('refs'), list) and all(isinstance(s, str) for s in r['refs']) else {},
                        'case_use_available': valid and bool(case_refs), 'semantic_verified': False})
        if not valid:
            isolate('record_projection', i, raw, 'INVALID_RECORD_INTERFACE_OR_SOURCE; raw retained')
    for i, raw in enumerate(value['arrangements'], 1):
        r = raw if isinstance(raw, dict) else {}
        valid = (isinstance(r.get('description'), str) and bool(r['description'].strip())
                 and refs_ok(r.get('refs'), sources, 'CASE_RECORD'))
        arrangements.append({'arrangement_id': 'A%d' % i, 'position': i, 'raw': copy.deepcopy(raw),
                             'interface_valid': valid, 'identity_semantics_verified': False})
        if not valid:
            isolate('arrangement_projection', i, raw, 'NO_VALID_CASE_GROUNDED_ARRANGEMENT')

    limits = []
    raw_limits = value.get('limitations', [])
    if not isinstance(raw_limits, list):
        coverage.append({'reason': 'UNREADABLE_RESTRICTIONS; no global block inferred', 'raw': raw_limits})
        raw_limits = []
    for i, raw in enumerate(raw_limits, 1):
        r = raw if isinstance(raw, dict) else {}
        scope = (index_ok(r.get('arrangement'), arrangements) and
                 arrangements[r['arrangement'] - 1]['interface_valid'] and r.get('condition') in cat)
        ids = r.get('records')
        whole = r.get('effect') == 'CONDITION_PENDING' and ids == []
        specific = isinstance(ids, list) and bool(ids) and all(index_ok(n, records) for n in ids)
        effect = r.get('effect')
        valid = (scope and (whole or specific or effect == 'NOTE')
                 and effect in ('EVIDENCE_USE_BLOCK', 'CONDITION_PENDING', 'NOTE', 'UNMAPPED')
                 and refs_ok(r.get('refs'), sources) and isinstance(r.get('reason'), str))
        guarded = scope and (whole or specific) and effect != 'NOTE'
        l = {'limitation_id': 'L%d' % i, 'raw': copy.deepcopy(raw), 'valid': valid,
             'scope_known': scope, 'guarded': guarded, 'whole_proposition': whole,
             'source_valid': refs_ok(r.get('refs'), sources)}
        limits.append(l)
        if not valid:
            isolate('restriction', i, raw, 'RESTRICTION_NOT_VALIDATED')
            coverage.append({'limitation_id': l['limitation_id'], 'reason':
                             'PENDING_IN_DECLARED_LOCAL_SCOPE' if guarded else 'UNMAPPED_RESTRICTION_NO_GLOBAL_BLOCK'})

    for i, raw in enumerate(value['conditions'], 1):
        r = raw if isinstance(raw, dict) else {}
        ai, key = r.get('arrangement'), r.get('condition')
        scope = (index_ok(ai, arrangements) and arrangements[ai - 1]['interface_valid'] and key in cat)
        valid = (scope and r.get('assessment') in STATES and isinstance(r.get('explanation'), str)
                 and bool(r['explanation'].strip()) and isinstance(r.get('evidence'), list)
                 and isinstance(r.get('gaps'), list) and all(isinstance(g, str) for g in r['gaps'])
                 and isinstance(r.get('law_refs'), list)
                 and (not r['law_refs'] or refs_ok(r['law_refs'], sources, 'LEGAL_AUTHORITY')))
        if not valid:
            isolate('condition', i, raw, 'INVALID_LOCAL_CONDITION_INTERFACE; raw and independent records retained')
        applicable = [l for l in limits if l['scope_known'] and l['raw']['arrangement'] == ai
                      and l['raw']['condition'] == key]
        whole = [l['limitation_id'] for l in applicable if l['whole_proposition'] and l['guarded']]
        local_uses = []
        for j, u in enumerate(r.get('evidence', []) if isinstance(r.get('evidence'), list) else [], 1):
            u = copy.deepcopy(u)
            d = u if isinstance(u, dict) else {}
            n = d.get('record')
            reasons, pending, notes = [], [], []
            e = records[n - 1] if index_ok(n, records) else None
            if not scope:
                reasons.append('UNESTABLISHED_LOCAL_ARRANGEMENT_OR_CONDITION')
            if not e or not e['interface_valid']:
                reasons.append('INVALID_RECORD_REFERENCE_OR_INTERFACE')
            elif not e['case_refs']:
                reasons.append('LEGAL_SOURCE_CANNOT_PROVE_TARGET_CASE_FACT')
            if d.get('role') not in ('SUPPORT', 'OPPOSE', 'CONTEXT', 'UNRESOLVED', 'IRRELEVANT') or not isinstance(d.get('connection'), str) or not d['connection'].strip():
                reasons.append('UNSPECIFIED_USE_CONNECTION')
            for l in applicable:
                lr = l['raw']
                if lr.get('records') and n not in lr['records']:
                    continue
                if l['valid'] and lr['effect'] == 'NOTE':
                    notes.append(l['limitation_id'])
                elif l['whole_proposition'] or l['guarded']:
                    pending.append(l['limitation_id'])
            status = 'ISOLATED' if reasons else 'PENDING_LOCAL_RESTRICTION' if pending else 'PROPOSED_CONNECTION'
            row = {'use_id': 'U%d.%d' % (i, j), 'condition_row': i, 'arrangement': ai, 'condition': key,
                   'record': n, 'raw': u, 'role': d.get('role'), 'status': status, 'reasons': reasons, 'restrictions': pending,
                   'notes': notes, 'statement_status': e['raw'].get('statement_status') if e else None,
                   'semantic_verified': False}
            local_uses.append(row)
            uses.append(row)
            if reasons:
                isolate('use', row['use_id'], u, '; '.join(reasons))
        available = [u for u in local_uses if u['status'] == 'PROPOSED_CONNECTION']
        pertinent = [u for u in available if u['role'] in ('SUPPORT', 'OPPOSE')]
        summary = {k: [u['use_id'] for u in available if u['role'] == role]
                   for k, role in [('support', 'SUPPORT'), ('opposition', 'OPPOSE'), ('context', 'CONTEXT'), ('irrelevant', 'IRRELEVANT')]}
        summary['pending'] = [u['use_id'] for u in local_uses if u not in available or u['role'] == 'UNRESOLVED']
        summary['conflicting_directions'] = bool(summary['support'] and summary['opposition'])
        summary['interpretation'] = 'RELEVANCE_ONLY_NOT_SUFFICIENCY; not independent votes'
        assessment = r.get('assessment') if valid else None
        reason = 'EXPLICIT_MODEL_JUDGMENT_NOT_VERIFIED'
        state = assessment or 'UNRESOLVED'
        if whole:
            state, reason = 'UNRESOLVED', 'DECLARED_WHOLE_PROPOSITION_PENDING'
        elif valid and assessment in ('SUPPORTED', 'REFUTED') and not pertinent:
            state, reason = 'UNRESOLVED', 'NO_USABLE_PERTINENT_CONNECTION_IN_CURRENT_PROPOSAL'
        elif not valid:
            reason = 'NO_VALID_MODEL_JUDGMENT'
        rows.append({'condition_row': i, 'arrangement': ai, 'condition': key,
                     'model_judgment': copy.deepcopy(raw), 'model_assessment': assessment,
                     'evidence_use_summary': summary, 'program_input_state': {'status': state, 'reason': reason},
                     'whole_proposition_restrictions': whole, 'semantic_verified': False})

    combined = []
    for a in arrangements:
        ai = a['position']
        states, leaf_states = {}, {}
        for key, address in cat.items():
            matching = [r for r in rows if r['arrangement'] == ai and r['condition'] == key]
            ss = {r['program_input_state']['status'] for r in matching}
            leaf_states[key] = {'status': next(iter(ss)) if len(ss) == 1 else 'UNRESOLVED',
                               'reason': 'MODEL_PREMISE' if len(ss) == 1 else 'CONFLICTING_MODEL_JUDGMENTS' if ss else 'NOT_PRODUCED_OPTIONAL',
                               'model_premise_rows': [r['condition_row'] for r in matching]}
        for test in template['tests']:
            states[test['id']] = evaluate(test['branch_expression'], leaf_states) if test.get('branch_expression') else leaf_states[test['id']]
        definitions = {x['id']: x['expression'] for x in template['elements']}
        claims = [{'claim_id': c['id'], 'result': evaluate(c['expression'], states, definitions)}
                  for c in template['claims'] if c['expression']['op'] != 'UNSUPPORTED']
        if not a['interface_valid']:
            claims = [{'claim_id': c['claim_id'], 'result': {'status': 'UNRESOLVED', 'reason': 'ARRANGEMENT_NOT_ESTABLISHED'}} for c in claims]
        combined.append({'arrangement': ai, 'tests': states, 'leaves': leaf_states, 'claims': claims,
                         'basis': 'CONDITIONAL_ON_EXPLICIT_MODEL_JUDGMENTS_AND_UNVERIFIED_BINDING',
                         'does_not_prove_other_arrangements_absent': True})
    imported = {'status': 'PARTIAL' if quarantine else 'OK', 'usable': True, 'raw_proposal': original,
                'records': records, 'arrangements': arrangements, 'quarantine': quarantine,
                'restriction_coverage': coverage, 'semantic_verified': False}
    checks = {'case_id': str(material['case_id']), 'catalogue': cat, 'records': records, 'arrangements': arrangements,
              'evidence_use_checks': uses, 'conditions': rows, 'combinations': combined, 'limitations': limits,
              'restriction_coverage': coverage, 'source_recovery': sources, 'import_quarantine': quarantine,
              'model_coverage_limits': value.get('coverage_limits', []), 'legal_coverage_limits': template.get('coverage_limits', []),
              'scope': 'Offline structural audit. No evidence vote or automatic sufficiency, target acceptance or burden inference. No case-level absence conclusion.',
              'legal_truth_verified': False}
    return imported, checks


def validate_final(value, schema, template):
    from legal_bench.rules_verdict_v1.contracts import validate
    validate(value, schema)
    required = [c['id'] for c in template['claims'] if c['expression']['op'] != 'UNSUPPORTED']
    actual = [a['claim_id'] for a in value['answers']]
    if Counter(actual) != Counter(required):
        raise ValueError('ANSWER_REQUEST_SET_NOT_EXACT_ONCE')
    for answer in value['answers']:
        if not answer['reason'].strip() or not answer['conditions']:
            raise ValueError('EMPTY_REASON_OR_DECISIVE_ANALYSIS')
        if any(not x['explanation'].strip() or not x['binding'].strip() for x in answer['conditions']):
            raise ValueError('EMPTY_CONDITION_EXPLANATION_OR_BINDING')


def legacy_projection(old, template):
    """Read-only V5 structural migration for replay, never reused as a new P.

    Relevance-only old uses receive no invented model judgment. Independent
    record rows survive; condition summaries retain only their original states.
    """
    directory = address_directory(template)
    bindings = old.get('bindings', [])
    bids = {b['id']: i for i, b in enumerate(bindings, 1)}
    records = old.get('evidence', [])
    eids = {e['id']: i for i, e in enumerate(records, 1)}
    out = {'records': [{'text': e['record'], 'statement_status': e['statement_status'], 'refs': e['refs']} for e in records],
           'arrangements': [{'description': b['objects'] + '; ' + b['event'], 'refs': b['refs']} for b in bindings],
           'conditions': [], 'limitations': [], 'coverage_limits': copy.deepcopy(old.get('coverage_limits', []))}
    for e in records:
        for u in e.get('uses', []):
            a = decode_address(u, directory)
            key = (a['branch_id'] or a['test_id']) if a else 'INVALID_OLD_ADDRESS'
            matching = [c for c in old.get('conditions', []) if c.get('binding_id') == e['binding_id'] and decode_address(c, directory) == a]
            out['conditions'].append({'arrangement': bids.get(e['binding_id'], 0), 'condition': key,
                 'assessment': matching[0]['assessment'] if len(matching) == 1 else 'UNRESOLVED',
                 'evidence': [{'record': eids[e['id']], 'role': {'UNKNOWN': 'UNRESOLVED'}.get(u['direction'], u['direction']),
                              'connection': 'Legacy declared use: ' + u['use']}], 'law_refs': [],
                 'explanation': 'Legacy explicit summary.' if len(matching) == 1 else 'No unique explicit model judgment; old relevance is not sufficiency.',
                 'gaps': [c.get('gap', '') for c in matching]})
    for l in old.get('limitations', []):
        a = decode_address(l, directory)
        out['limitations'].append({'arrangement': bids.get(l['binding_id'], 0), 'condition': (a['branch_id'] or a['test_id']) if a else '',
             'records': [eids.get(e, 0) for e in l.get('evidence_ids', [])],
             'effect': {'PROPOSITION_BLOCK': 'CONDITION_PENDING', 'USE_BLOCK': 'EVIDENCE_USE_BLOCK', 'SCOPE_UNMAPPED': 'UNMAPPED'}.get(l['effect'], l['effect']),
             'reason': l['reason'], 'refs': l['refs']})
    return out
