"""Independent, deterministic checker for a bounded teaching rule registry.

Trust root is the caller-selected manifest plus its review process, not a field
supplied by the certificate. Hashes detect changes, not fraudulent approvals.
No LLM, proposal engine, old condition evaluator or spectral score is called.
"""
from datetime import date
from pathlib import Path

from .contracts import STATES, byte_hash, content_hash, read_json, subject_hash, validate_certificate


class CheckFailure(ValueError):
    def __init__(self, code, status='INVALID', detail=None):
        super().__init__(code)
        self.code, self.status, self.detail = code, status, detail


def require(test, code, status='INVALID', detail=None):
    if not test:
        raise CheckFailure(code, status, detail)


def _load(root, entry):
    path = (root / entry['path']).resolve()
    require(path.is_relative_to(root.resolve()), 'PATH_OUTSIDE_TRUST_ROOT')
    require(path.is_file(), 'TRUSTED_FILE_MISSING', 'INCOMPLETE', entry['path'])
    require(byte_hash(path) == entry['sha256'], 'TRUSTED_FILE_CHANGED', detail=entry['path'])
    return read_json(path)


def _source(ref, snapshot, root):
    require(ref in snapshot['sources'], 'SOURCE_MISSING', 'INCOMPLETE', ref)
    loc = snapshot['sources'][ref]
    require(loc['document_id'] in snapshot['documents'], 'DOCUMENT_ID_UNRESOLVED', 'INCOMPLETE')
    doc = snapshot['documents'][loc['document_id']]
    require(doc['case_id'] == snapshot['case_id'] and loc['case_id'] == snapshot['case_id'], 'SOURCE_CASE_MISMATCH')
    path = (root / doc['path']).resolve()
    require(path.is_relative_to(root.resolve()), 'SOURCE_PATH_OUTSIDE_TRUST_ROOT')
    require(path.is_file(), 'SOURCE_DOCUMENT_MISSING', 'INCOMPLETE')
    require(byte_hash(path) == doc['sha256'], 'SOURCE_DOCUMENT_CHANGED')
    text = path.read_bytes().decode('utf-8')
    start, end = loc['start'], loc['end']
    require(type(start) is int and type(end) is int and 0 <= start < end <= len(text), 'SOURCE_RANGE_INVALID')
    require(text[start:end] == loc['exact_text'], 'SOURCE_LOCATOR_MISMATCH')
    require(loc['line'] == text[:start].count('\n') + 1, 'SOURCE_LINE_MISMATCH')
    return {'source_ref': ref, 'document_id': loc['document_id'], 'start': start, 'end': end,
            'exact_text': text[start:end], 'availability': loc['availability'],
            'semantic_support_inferred_from_locator': False}


def _review(record, reviews, policy, role):
    rid = record.get('review_id')
    require(rid in reviews, 'REVIEW_MISSING', 'INCOMPLETE', rid)
    rv = reviews[rid]
    require(rv['subject_sha256'] == subject_hash(record), 'REVIEW_SUBJECT_CHANGED')
    require(rv['decision'] == 'EXERCISE_SUPPLIED', 'REVIEW_NOT_ACCEPTED', 'INCOMPLETE', rid)
    require(rv['reviewer_role'] in policy['accepted_review_roles'][role], 'REVIEWER_ROLE_NOT_ELIGIBLE')
    require(rv['human_legal_approval'] is False, 'TEACHING_APPROVAL_MISREPRESENTED')
    require(rv['basis'] == 'SYNTHETIC_EXERCISE', 'NON_SYNTHETIC_TEACHING_APPROVAL')


def _proposition(pid, spec, binding, snapshot, policy, root):
    require(pid in snapshot['propositions'], 'PREMISE_MISSING', 'INCOMPLETE', pid)
    p = snapshot['propositions'][pid]
    require(p['id'] == pid and p['case_id'] == snapshot['case_id'], 'PREMISE_ID_OR_CASE_MISMATCH')
    require(p['stage_id'] == snapshot['stage_id'], 'PREMISE_STAGE_MISMATCH')
    require(p['predicate'] == spec['predicate'], 'PREDICATE_MISMATCH')
    require(p['statement_status'] in policy['accepted_statement_statuses'], 'PREMISE_ATTRIBUTION_NOT_ACCEPTED')
    require(p['assessment'] in STATES, 'ASSESSMENT_INVALID')
    _review(p, snapshot['reviews'], policy, 'premise')
    require(bool(p['source_refs']), 'PREMISE_SOURCE_MISSING', 'INCOMPLETE')
    sources = [_source(r, snapshot, root) for r in p['source_refs']]
    for field, typ in (('person', 'PERSON'), ('property', 'PROPERTY')):
        v = p['bindings'].get(field)
        require(bool(v) and v in snapshot['entities'], 'TYPED_BINDING_MISSING', 'INCOMPLETE', field)
        require(snapshot['entities'][v]['type'] == typ, 'ENTITY_TYPE_MISMATCH')
        require(v == binding[field], 'BINDING_MISMATCH', detail={'premise': pid, 'field': field})
    return p, sources


def _expr(expr, states, trace):
    op = expr['op']
    if op == 'REF':
        require(expr['role'] in states, 'EXPRESSION_ROLE_MISSING', 'INCOMPLETE', expr['role'])
        value = states[expr['role']]
    elif op == 'NOT':
        value = {'TRUE': 'FALSE', 'FALSE': 'TRUE', 'UNKNOWN': 'UNKNOWN', 'CONFLICTED': 'CONFLICTED'}[_expr(expr['arg'], states, trace)]
    else:
        require(op in ('AND', 'OR') and bool(expr.get('args')), 'EXPRESSION_UNSUPPORTED')
        values = [_expr(e, states, trace) for e in expr['args']]
        if op == 'AND':
            value = 'FALSE' if 'FALSE' in values else 'TRUE' if all(s == 'TRUE' for s in values) else 'CONFLICTED' if 'CONFLICTED' in values else 'UNKNOWN'
        else:
            value = 'TRUE' if 'TRUE' in values else 'FALSE' if all(s == 'FALSE' for s in values) else 'CONFLICTED' if 'CONFLICTED' in values else 'UNKNOWN'
    trace.append({'expression': expr, 'result': value})
    return value


def _step(step, snapshot, registry, policy, root):
    require(step['rule_ref'] in registry['rules'], 'RULE_VERSION_MISSING', 'INCOMPLETE')
    rule = registry['rules'][step['rule_ref']]
    require(rule['id'] == step['rule_ref'], 'RULE_VERSION_ID_MISMATCH')
    require(rule['status'] == 'DEMO_ONLY', 'RULE_NOT_ELIGIBLE')
    _review(rule, registry['reviews'], policy, 'rule')
    for key in ('jurisdiction', 'issue_id', 'stage_id'):
        require(rule['scope'][key] == snapshot[key], 'RULE_SCOPE_MISMATCH', detail=key)
    require(rule['burden_policy'] == 'NOT_APPLICABLE_NARROW_TEACHING_TEST', 'UNIMPLEMENTED_BURDEN_POLICY')
    require(rule['exception_policy'] in ('NOT_APPLICABLE_NARROW_TEACHING_TEST', 'EXPLICIT_INPUT'), 'UNRESOLVED_EXCEPTION_POLICY')
    require(rule['scope']['valid_from'] <= snapshot['as_of'] <= rule['scope']['valid_to'], 'RULE_TEMPORAL_SCOPE_MISMATCH')
    require(len(step['premise_ids']) == len(rule['inputs']), 'MISSING_OR_EXTRA_PREMISE', 'INCOMPLETE')
    require(not step['depends_on'], 'STEP_DEPENDENCY_NOT_CONSUMED_BY_BOUNDED_RULE')
    vals, source_trace = {}, []
    for pid, spec in zip(step['premise_ids'], rule['inputs']):
        p, refs = _proposition(pid, spec, step['bindings'], snapshot, policy, root)
        vals[spec['role']] = p
        source_trace.extend(refs)
    trace = []
    if rule['kind'] == 'PERMISSION_COVERAGE':
        require(set(vals) == {'authorization', 'entry'}, 'COVERAGE_ROLE_CONTRACT')
        a, b = vals['authorization'], vals['entry']
        require(a['assessment'] == b['assessment'] == 'TRUE', 'REQUIRES_ACCEPTED_TRUE_PREMISES', 'INCOMPLETE')
        require(len(a['interval']) == 2, 'INVALID_INTERVAL')
        lo, hi, event = date.fromisoformat(a['interval'][0]), date.fromisoformat(a['interval'][1]), date.fromisoformat(b['event_time'])
        require(lo <= hi, 'INVALID_INTERVAL')
        require(isinstance(a['activity_scope'], list) and bool(a['activity_scope']) and
                all(isinstance(x, str) and bool(x) for x in a['activity_scope']) and bool(b['activity']), 'INVALID_ACTIVITY_SCOPE')
        checks = {'person': 'TRUE', 'parcel': 'TRUE', 'time': 'TRUE' if lo <= event <= hi else 'FALSE',
                  'activity': 'TRUE' if b['activity'] in a['activity_scope'] else 'FALSE'}
        result = 'TRUE' if all(v == 'TRUE' for v in checks.values()) else 'FALSE'
        trace = [{'check': k, 'result': v} for k, v in checks.items()]
    else:
        require(rule['kind'] == 'EXPRESSION', 'RULE_KIND_UNSUPPORTED')
        result = _expr(rule['expression'], {k: p['assessment'] for k, p in vals.items()}, trace)
    require(result == step['proposed_result'], 'PROPOSED_RESULT_MISMATCH', detail={'computed': result, 'proposed': step['proposed_result']})
    exception_pending = rule['exception_policy'] == 'EXPLICIT_INPUT' and vals['exception']['assessment'] in ('UNKNOWN', 'CONFLICTED')
    return {'step_id': step['id'], 'status': 'CHECKED' if result in ('TRUE', 'FALSE') and not exception_pending else 'CONDITIONAL',
            'result': result, 'claim': rule['conclusion'], 'rule_ref': step['rule_ref'],
            'premise_ids': step['premise_ids'], 'bindings': step['bindings'], 'trace': trace,
            'unresolved_inputs': [p['id'] for p in vals.values() if p['assessment'] in ('UNKNOWN', 'CONFLICTED')],
            'exception_gate_pending': exception_pending,
            'source_trace': source_trace, 'verification_scope': 'SYNTHETIC_TEACHING_POLICY_ONLY'}


def check(certificate, trust_root, manifest_name='trust-manifest.json', mode='TEACHING', current_snapshot=None):
    """Load trusted material independently; return per-conclusion, not global truth."""
    root = Path(trust_root)
    result = {'certificate_id': certificate.get('certificate_id') if isinstance(certificate, dict) else None,
              'status': 'INVALID', 'legal_approved': False, 'steps': [], 'requests': [],
              'trust_boundary': 'Caller-controlled manifest and review process; no cryptographic reviewer identity attestation.'}
    try:
        validate_certificate(certificate)
        manifest = read_json(root / manifest_name)
        require(certificate['mode'] == mode, 'CALLER_MODE_MISMATCH')
        require(mode == 'TEACHING', 'NO_APPROVED_PRODUCTION_LEGAL_RULES')
        sid = certificate['snapshot_id']
        require(current_snapshot is None or current_snapshot == sid, 'STALE_CERTIFICATE_FOR_CURRENT_SNAPSHOT')
        require(sid in manifest['snapshots'], 'SNAPSHOT_MISSING', 'INCOMPLETE')
        snapshot = _load(root, manifest['snapshots'][sid])
        registry = _load(root, manifest['registry'])
        policy = _load(root, manifest['policy'])
        require(snapshot['snapshot_id'] == sid, 'SNAPSHOT_ID_MISMATCH')
        for key, value in (('snapshot_sha256', snapshot), ('registry_sha256', registry), ('policy_sha256', policy)):
            require(certificate[key] == content_hash(value), 'CERTIFICATE_CONTENT_HASH_MISMATCH', detail=key)
        require(snapshot['case_id'] == 'DEMO_PERMISSION' and policy['mode'] == 'TEACHING', 'TEACHING_DOMAIN_MISMATCH')
        steps = {s['id']: s for s in certificate['steps']}
        ordered, visiting, visited = [], set(), set()
        def visit(key):
            require(key in steps, 'STEP_DEPENDENCY_MISSING', 'INCOMPLETE', key)
            require(key not in visiting, 'CYCLIC_DEPENDENCY')
            if key in visited:
                return
            visiting.add(key)
            for dep in steps[key]['depends_on']:
                visit(dep)
            visiting.remove(key); visited.add(key); ordered.append(key)
        for key in steps:
            visit(key)
        by_id = {}
        for key in ordered:
            try:
                row = _step(steps[key], snapshot, registry, policy, root)
            except CheckFailure as e:
                row = {'step_id': key, 'status': e.status, 'reason': e.code, 'detail': e.detail, 'result': None}
            by_id[key] = row; result['steps'].append(row)
        for req in certificate['requests']:
            row = by_id.get(req['step_id'])
            if row is None:
                answer = {'status': 'INCOMPLETE', 'reason': 'NO_ELIGIBLE_DERIVATION', 'result': None}
            elif row['status'] not in ('CHECKED', 'CONDITIONAL'):
                answer = {k: row[k] for k in ('status', 'reason', 'result')}
            elif req['claim'] != row['claim']:
                answer = {'status': 'INCOMPLETE', 'reason': 'NO_RULE_FOR_REQUESTED_BROADER_CONCLUSION', 'result': None}
            elif req['proposed_result'] != row['result']:
                answer = {'status': 'INVALID', 'reason': 'REQUEST_STEP_RESULT_MISMATCH', 'result': None}
            else:
                answer = {'status': row['status'], 'result': row['result'], 'step_id': row['step_id']}
            result['requests'].append(dict(answer, request_id=req['id'], claim=req['claim']))
        statuses = {r['status'] for r in result['requests']}
        result['status'] = statuses.pop() if len(statuses) == 1 else 'MIXED'
        result['historical_snapshot_validated'] = sid
    except CheckFailure as e:
        result.update(status=e.status, reason=e.code, detail=e.detail)
    except (ValueError, TypeError, KeyError, OSError, IndexError, RecursionError) as e:
        result.update(status='INVALID', reason='MALFORMED_CONTRACT', detail=str(e))
    return result
