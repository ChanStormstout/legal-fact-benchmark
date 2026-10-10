"""Independent V15 checker. No proposer/task, reference, learner or search import.

Semantic claims stay assumptions even after model-assisted source review.
"""
import copy
from .contracts import content_hash
from .semantic_checker_v13 import check as legacy_check, source_match

PROMOTING = {'ESTABLISH_OCCURRENCE', 'RECONSTRUCT_COURT_PREMISE'}
CLAIMS = {'PARTY_CLAIM', 'PARTY_CONTENTION', 'PARTY_ALLEGATION', 'HYPOTHETICAL', 'FUTURE_CONDITIONAL'}
STATES = {'TRUE', 'FALSE', 'UNKNOWN', 'CONFLICTED'}


def locate(w, sources):
    result = source_match(w, sources)
    if not result.get('error') and any(sources[r].get('document_role') != 'TARGET' or sources[r].get('role') == 'DISPOSITION_ONLY' for r in w['refs']):
        result = {**result, 'error': 'FOREIGN_OR_FINAL_DISPOSITION_PREMISE'}
    return result


def witnesses(rows, sources):
    return [{'witness': w, 'source_check': locate(w, sources)} for w in rows]


def inspect_alignment(row, d, sources):
    errors, pending = [], []
    whole = row.get('whole_premise', {})
    state = whole.get('state', 'UNKNOWN')
    if state not in STATES:
        errors.append('INVALID_PREMISE_STATE')
    if not whole.get('basis'):
        pending.append('WHOLE_PREMISE_BASIS_MISSING')
    if not whole.get('complete') or whole.get('missing_components'):
        pending.append('WHOLE_PREMISE_COVERAGE_NOT_CLAIMED_COMPLETE')
    components = []
    for c in whole.get('components', []):
        ws = witnesses(c.get('witnesses', []), sources)
        ok = c.get('covered') is True and bool(c.get('component')) and bool(c.get('basis')) and bool(ws) and all(not w['source_check'].get('error') for w in ws)
        components.append({'component': c, 'structurally_witnessed': ok, 'witnesses': ws})
    if not components or not all(c['structurally_witnessed'] for c in components):
        pending.append('COMPONENT_COVERAGE_WITNESS_INCOMPLETE')
    if row.get('statement_status') not in d['allowed_statuses']:
        pending.append('STATEMENT_STATUS_NOT_ALLOWED_FOR_SLOT')
    if row.get('rule_stage') != d['rule_stage']:
        errors.append('RULE_STAGE_MISMATCH')
    if not row.get('source_stage') or not row.get('court_level'):
        pending.append('ATTRIBUTION_INCOMPLETE')
    roles = set(d['role_descriptions'])
    variables = set(d['candidate_bindings']) | set(d['original_use'].get('bindings', {}))
    bs = {}
    binding_checks = []
    for b in row.get('bindings', []):
        role, var, value = b.get('role'), b.get('variable'), b.get('value')
        ws = witnesses(b.get('witnesses', []), sources)
        bad = []
        if role not in roles or var not in variables:
            bad.append('UNKNOWN_ROLE_OR_VARIABLE_ADDRESS')
        if role in bs:
            bad.append('DUPLICATE_ROLE_BINDING')
        bs[role] = b
        expected = d['candidate_bindings'].get(var, d['original_use'].get('bindings', {}).get(var))
        if b.get('status') == 'UNKNOWN':
            bad.append('OBJECT_CONNECTION_UNKNOWN')
        elif b.get('status') == 'NOT_APPLICABLE':
            if state != 'FALSE' or value is not None:
                bad.append('ABSENT_EVENT_ROLE_NOT_JUSTIFIED')
        elif b.get('status') != 'BOUND' or value is None or value == '' or value == []:
            bad.append('NO_EXPLICIT_BOUND_OBJECT')
        elif expected is not None and expected != '' and expected != value:
            bad.append('EXPLICIT_OBJECT_VALUE_CONFLICT')
        if not ws or any(w['source_check'].get('error') for w in ws) or not b.get('basis'):
            bad.append('OBJECT_WITNESS_NOT_VERIFIED')
        binding_checks.append({'binding': b, 'witnesses': ws, 'pending': bad})
        pending.extend('BINDING:' + str(role) + ':' + x for x in bad)
    for role in roles - set(bs):
        pending.append('MISSING_RULE_ROLE:' + role)
    use_checks, promoters = [], []
    for u in row.get('uses', []):
        ws = witnesses(u.get('witnesses', []), sources)
        eligible = bool(ws) and all(not w['source_check'].get('error') for w in ws) and bool(u.get('explanation'))
        promoting = eligible and u.get('purpose') in PROMOTING and row.get('statement_status') not in CLAIMS
        use_checks.append({'use': u, 'witnesses': ws, 'structurally_eligible': eligible,
                           'whole_premise_function': promoting, 'semantic_verified': False})
        if promoting:
            promoters.append(u)
    if not promoters:
        pending.append('NO_WITNESSED_WHOLE_PREMISE_FUNCTION')
    # A background or supporting edge never creates a truth state. Only the
    # separate, complete, witnessed whole-premise claim can be assumed here.
    conditional = state if not errors and not pending else 'UNKNOWN'
    return {'structural_status': 'FAIL' if errors else 'PARTIAL' if pending else 'PASS',
            'errors': errors, 'pending': pending, 'binding_checks': binding_checks,
            'use_checks': use_checks, 'component_checks': components,
            'counterevidence_checks': witnesses(row.get('counterevidence', []), sources),
            'raw_model_state': state, 'conditional_state': conditional,
            'limitations': row.get('limitations', []), 'origin': 'MODEL_PROPOSED',
            'semantic_verified': False, 'review_acceptance': 'NOT_REVIEWED',
            'formal_legal_approval': False}


def review_status(row, review, sources):
    if review is None:
        return {'decision': 'NOT_REVIEWED', 'reason': 'No actual independent review record', 'formal_legal_approval': False}
    ws = witnesses(review.get('witnesses', []), sources)
    valid = bool(ws) and all(not w['source_check'].get('error') for w in ws) and bool(review.get('reason'))
    decision = review.get('decision', 'UNRESOLVED')
    if decision not in {'ACCEPT', 'REJECT', 'UNRESOLVED'} or not valid:
        decision = 'UNRESOLVED'
    return {'decision': decision, 'submitted_decision': review.get('decision'),
            'reason': review.get('reason'), 'witnesses': ws,
            'counterevidence_checks': witnesses(review.get('counterevidence', []), sources),
            'limits': review.get('limitations', []), 'structurally_located_review': valid,
            'identity': 'INDEPENDENT_MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
            'formal_legal_approval': False}


def check(bundle, route, supplement=None, review=None, view='D'):
    s = bundle['snapshot']
    base = legacy_check(s, route)  # raw model judgments, not V14 approval masking
    directory = {(d['candidate_id'], d['premise_id']): d for d in bundle['directory']}
    addresses = {d['address']: d for d in bundle['directory']}
    rows, duplicate = {}, set()
    if supplement is not None:
        if supplement.get('input_sha256') != content_hash(bundle) or supplement.get('proposal_sha256') != content_hash(supplement.get('raw')):
            raise ValueError('SUPPLEMENT_HASH_MISMATCH')
        for row in supplement.get('raw', {}).get('alignments', []):
            addr = row.get('address')
            if addr in rows:
                duplicate.add(addr)
            rows[addr] = row
    reviews = {}
    if review is not None:
        if not supplement or review.get('proposal_sha256') != supplement['proposal_sha256']:
            raise ValueError('INDEPENDENT_REVIEW_PROPOSAL_MISMATCH')
        for r in review.get('raw', {}).get('reviews', []):
            if r['address'] in reviews:
                reviews[r['address']] = {'decision': 'UNRESOLVED', 'reason': 'Duplicate review address', 'witnesses': []}
            else:
                reviews[r['address']] = r
    audits = {}
    for addr, row in rows.items():
        if addr not in addresses:
            audits[addr] = {'structural_status': 'FAIL', 'errors': ['UNKNOWN_ADDRESS'], 'conditional_state': 'UNKNOWN'}
            continue
        audit = inspect_alignment(row, addresses[addr], s['sources'])
        if addr in duplicate:
            audit['errors'].append('DUPLICATE_ALIGNMENT_ADDRESS');audit['conditional_state'] = 'UNKNOWN';audit['structural_status'] = 'FAIL'
        audit['review'] = review_status(row, reviews.get(addr), s['sources'])
        audit['accepted_state'] = audit['conditional_state'] if audit['review']['decision'] == 'ACCEPT' else 'UNKNOWN'
        audits[addr] = audit
    steps = {st['id']: st for st in route['steps']}
    cache = {}

    def visit(sid, active):
        if sid in active:
            return {'state': None, 'errors': ['CYCLE'], 'pending': [], 'assumptions': []}
        if sid in cache:
            return cache[sid]
        st = steps.get(sid)
        if not st:
            return {'state': None, 'errors': ['DANGLING_STEP'], 'pending': [], 'assumptions': []}
        rr = st['rule_ref'];r = s['rules'].get(rr);errs = [];pending = [];assumptions = [];states = {}
        if not r:
            return {'state': None, 'errors': ['RULE_MISSING'], 'pending': [], 'assumptions': []}
        if rr != r['id'] + '@' + str(r['version']) or s['contracts'][rr]['rule_hash'] != content_hash(r):
            errs.append('RULE_VERSION_OR_HASH_MISMATCH')
        loc = source_match(r, s['sources'])
        if loc.get('error'):
            errs.append('RULE_SOURCE:' + loc['error'])
        ins = {x['slot']: x for x in st['inputs']}
        if len(ins) != len(st['inputs']) or set(ins) - {sl['name'] for sl in r['slots']}:
            errs.append('DUPLICATE_OR_EXTRA_SLOT')
        for sl in r['slots']:
            x = ins.get(sl['name']);d = directory.get((st['candidate_id'], sl['name']));v = 'UNKNOWN'
            addr = d['address'] if d else None
            if addr in audits:
                a = audits[addr];v = a.get('accepted_state', 'UNKNOWN') if view == 'R' else a['conditional_state']
                pending.extend(sl['name'] + ':' + p for p in a.get('pending', []))
                assumptions.append({'address': addr, 'state': v, 'raw_model_state': a.get('raw_model_state'),
                    'basis': rows[addr].get('whole_premise', {}).get('basis'),
                    'source_stage': rows[addr].get('source_stage'), 'court_level': rows[addr].get('court_level'),
                    'origin': 'MODEL_PROPOSED_SEMANTICS_NOT_LEGAL_PROOF', 'review': a.get('review')})
                if view == 'R' and a.get('review', {}).get('decision') != 'ACCEPT':
                    pending.append(sl['name'] + ':RESEARCH_ACCEPTANCE_PENDING_OR_REJECTED')
            elif x and x['kind'] == 'STEP':
                child = visit(x['id'], active | {sid});ch = steps.get(x['id'])
                if child['errors'] or not ch or s['rules'][ch['rule_ref']]['conclusion_predicate'] != sl['predicate']:
                    pending.append(sl['name'] + ':INVALID_DEPENDENCY')
                else:
                    v = child['state'] or 'UNKNOWN'
                    child_bindings = {b['role']: b['entity'] for b in ch['bindings']}
                    parent = {b['role']: b['entity'] for b in st['bindings']}
                    maps = s['contracts'][rr]['slot_variables'].get(sl['name'], {})
                    if s['contracts'][rr].get('unmapped_roles', {}).get(sl['name']):
                        pending.append(sl['name'] + ':DEPENDENCY_ROLE_UNMAPPED');v = 'UNKNOWN'
                    for role, variable in maps.items():
                        if child_bindings.get(role) is None or parent.get(variable) is None or child_bindings[role] != parent[variable]:
                            pending.append(sl['name'] + ':DEPENDENCY_OBJECT_UNESTABLISHED');v = 'UNKNOWN'
                    assumptions.extend(child['assumptions'])
            elif x and x['kind'] in {'PREMISE', 'BUNDLE'}:
                # Evaluate this raw slot alone without inheriting other slot failures.
                ss = copy.deepcopy(s);rt = copy.deepcopy(route)
                localrule = ss['rules'][rr]
                localrule['slots'] = [copy.deepcopy(sl)];localrule['exception_slots'] = [];localrule['operator'] = 'ALL'
                # Keep expectation outside the local checker to apply it exactly once.
                localrule['slots'][0]['expected'] = 'TRUE'
                ss['contracts'][rr]['rule_hash'] = content_hash(localrule)
                local = copy.deepcopy(st);local['inputs'] = [copy.deepcopy(x)]
                rt = {'steps': [local], 'requests': [{'request': {'id': addr or sl['name']}, 'root_steps': [sid], 'search_status': 'RAW_SLOT_CHECK'}]}
                b = legacy_check(ss, rt)['steps'][sid]
                v = b['state'] or 'UNKNOWN';pending += [sl['name'] + ':' + p for p in b.get('pending', [])]
                assumptions += b.get('assumptions', [])
                if view == 'R':
                    v = 'UNKNOWN';pending.append(sl['name'] + ':RAW_P_NOT_INDEPENDENTLY_REVIEWED')
            else:
                pending.append(sl['name'] + ':MISSING_INPUT')
            if sl.get('expected', 'TRUE') == 'FALSE':
                v = {'TRUE': 'FALSE', 'FALSE': 'TRUE'}.get(v, v)
            states[sl['name']] = v
        exc = set(r.get('exception_slots', []));normal = [v for k, v in states.items() if k not in exc]
        if errs:
            state = None
        elif r['operator'] == 'OPEN_TEXT':
            state = 'UNKNOWN';pending.append('OPEN_LEGAL_INTERPRETATION_NOT_EXECUTED')
        elif not normal:
            state = 'UNKNOWN';pending.append('NO_ANTECEDENTS')
        elif r['operator'] == 'ALL':
            state = 'FALSE' if 'FALSE' in normal else 'CONFLICTED' if 'CONFLICTED' in normal else 'UNKNOWN' if 'UNKNOWN' in normal else 'TRUE'
        elif r['operator'] == 'ANY':
            state = 'TRUE' if 'TRUE' in normal else 'CONFLICTED' if 'CONFLICTED' in normal else 'UNKNOWN' if 'UNKNOWN' in normal else 'FALSE'
        else:
            state = None;errs.append('UNSUPPORTED_OPERATOR')
        ev = [states.get(k, 'UNKNOWN') for k in exc]
        if state is not None and 'TRUE' in ev:
            state = 'FALSE'
        elif state is not None and any(v in {'UNKNOWN', 'CONFLICTED'} for v in ev):
            state = 'UNKNOWN';pending.append('EXCEPTION_PENDING')
        cache[sid] = {'state': state, 'premise_states': states, 'errors': errs, 'pending': pending,
                      'assumptions': assumptions, 'rule_ref': rr, 'candidate_id': st['candidate_id'], 'formal_legal_approval': False}
        return cache[sid]

    requests = []
    for req in route['requests']:
        alts = [{'step': sid, **visit(sid, set())} for sid in req['root_steps']]
        vals = {a['state'] for a in alts if not a['errors']}
        state = 'CONFLICTED' if 'CONFLICTED' in vals or {'TRUE', 'FALSE'} <= vals else 'TRUE' if 'TRUE' in vals else 'FALSE' if vals == {'FALSE'} else 'UNKNOWN'
        requests.append({'id': req['request']['id'], 'answer': state, 'alternatives': alts,
            'meaning': 'Applicability/result of the unchanged selected rule under declared premises, not an entire case verdict',
            'scope': 'MODEL_ASSISTED_REVIEW_ACCEPTANCE' if view == 'R' else 'CONDITIONAL_ON_UNVERIFIED_MODEL_SEMANTICS',
            'formal_legal_approval': False})
    return {'run_status': 'OK', 'view': view, 'requests': requests, 'steps': cache,
        'structure_checks': audits, 'raw_P_diagnostic': base,
        'proposal_coverage_limits': (supplement or {}).get('raw', {}).get('coverage_limits', []),
        'review_coverage_limits': (review or {}).get('raw', {}).get('coverage_limits', []),
        'all_original_opposition': s.get('relations', []), 'all_original_uses': s.get('raw_proposal', {}).get('uses', []),
        'all_original_limits': s.get('coverage_limits', []), 'semantic_verified': False,
        'formal_legal_approval': False, 'technical_answer': requests,
        'original_null_quotes_retained': [p['id'] for p in s['premises'].values() if p.get('quote') is None]}
