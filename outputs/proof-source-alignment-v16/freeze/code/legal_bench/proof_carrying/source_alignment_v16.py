"""V16 input-only task and supplement assembly. Never reads reference labels.

No semantic acceptance is manufactured here. The checker lives in a separate
module/process and independently validates addresses, witnesses and rule use.
"""
import copy
from .contracts import content_hash
from .semantic_interface_v13 import adapt, position
from .semantic_search_v12 import complete_search
from .quote_locator_v16 import source_match
from .realcase_grounding_v3 import canonical_chars

VERSION = 'V16.1'
PURPOSES = ['REPORT_ASSERTION', 'PARTIAL_SUPPORT', 'PARTIAL_OPPOSITION',
            'BACKGROUND', 'ESTABLISH_OCCURRENCE', 'RECONSTRUCT_COURT_PREMISE']
CONTRACT = {
    'version': VERSION,
    'use_eligibility_not_truth': True,
    'truth_states': ['TRUE', 'FALSE', 'UNKNOWN', 'CONFLICTED'],
    'purposes': PURPOSES,
    'directions': ['SUPPORT', 'OPPOSE', 'CONTEXT', 'UNRESOLVED'],
    'acceptance_policy': 'Separate actual independent review from hypothetical model semantics',
    'formal_legal_approval': False,
    'binding_policy': 'Exact declared variable/value plus source witness; type/name/null never identity',
    'not_applicable_policy': 'Only an explicitly source-supported absent-event role in a FALSE whole-premise proposal; still unverified semantics',
    'coverage_policy': 'Model must separately assert complete proposition coverage; components do not create a new AND rule',
    'source_policy': 'Exact reversible quotation locator; complete allowed source retained in source order',
    'rule_policy': 'No operator, exception, proposition or expected-polarity edits',
    'technical_failure_answer': None,
}


def prepare(case, proposal, request_id):
    if case.get('split') != 'DEV':
        raise ValueError('ONLY_EXPLICIT_DEV_INPUT_ALLOWED')
    s, candidates, requests = adapt(case, proposal)
    if any(x['source_document'] != case['case_id'] for x in case['segments']):
        raise ValueError('SOURCE_DOCUMENT_IDENTITY_CONFLICT')
    repairs = []
    # Presentation-only correction: recover unique case differences with exact
    # character offsets. Never fill null quotes or repair omitted words/negation.
    for rr, rule in s['rules'].items():
        quote = rule.get('quote')
        if not isinstance(quote, str) or not quote or not source_match(rule, s['sources']).get('error'):
            continue
        q, _ = canonical_chars(quote)
        matches = []
        for ref in dict.fromkeys(rule['refs']):
            text = s['sources'].get(ref, {}).get('text', '')
            canon, offsets = canonical_chars(text)
            lo = canon.lower().find(q.lower())
            while q and lo >= 0:
                if len(canon.lower()) != len(canon) or len(q.lower()) != len(q):
                    break
                a, b = offsets[lo], offsets[lo + len(q) - 1] + 1
                matches.append({'ref': ref, 'start': a, 'end': b, 'original': text[a:b]})
                lo = canon.lower().find(q.lower(), lo + 1)
        if len(matches) == 1:
            rule['quote'] = matches[0]['original']
            s['contracts'][rr]['rule_hash'] = content_hash(rule)
            repairs.append({'rule_ref': rr, 'old_quote': quote, 'restored_quote': rule['quote'],
                            'location': matches[0], 'kind': 'UNIQUE_CASE_ONLY_PRESENTATION_RECOVERY_NOT_SEMANTIC_APPROVAL'})
    # Restore presentation only in the new snapshot, retaining old rule bytes.
    for rr, rule in s['rules'].items():
        located = source_match(rule, s['sources'])
        if located.get('mode') == 'REVERSIBLE_DOCUMENT_ATTESTED_LAYOUT_JOIN':
            old = rule['quote']
            rule['quote'] = ' '.join(x['original'] for x in located['original_spans'])
            s['contracts'][rr]['rule_hash'] = content_hash(rule)
            repairs.append({'rule_ref': rr, 'old_quote': old, 'restored_quote': rule['quote'],
                            'location': located, 'kind': 'VERSIONED_TYPOGRAPHY_ONLY_NO_SEMANTIC_APPROVAL'})
    request = next(q for q in requests if q['id'] == request_id)
    # Do not expose an old target-level answer as task instructions.
    request = {k: v for k, v in request.items() if k != 'model_limited_conclusion'}
    search = complete_search(candidates, s['rules'], [request], s['contracts'])
    used = {st['candidate_id'] for st in search['steps']}
    chosen = [c for c in candidates if c['id'] in used]
    directory = []
    raw_slots = {p['id']: p for r in proposal['rules'] for p in r['premises']}
    raw_uses = {u['id']: u for u in proposal['uses']}
    for c in chosen:
        r = s['rules'][c['rule_ref']]
        for sl in r['slots']:
            u = s['model_uses'].get(c['id'] + '::' + sl['name'], {})
            original = raw_uses.get(u.get('raw_use_id'), {})
            directory.append({
                'address': 'A%02d' % (len(directory) + 1),
                'candidate_id': c['id'], 'rule_ref': c['rule_ref'],
                'premise_id': sl['name'], 'proposition': sl['predicate'],
                'expected': sl.get('expected', 'TRUE'), 'allowed_statuses': sl['allowed_statuses'],
                'rule_stage': r.get('stage'),
                'role_descriptions': raw_slots[sl['name']].get('variables', {}),
                'candidate_bindings': {b['role']: b['entity'] for b in c['bindings']},
                'original_use': original,
                'original_input': next(x for x in c['inputs'] if x['slot'] == sl['name']),
                'fixed_mapping': s['contracts'][c['rule_ref']]['slot_variables'].get(sl['name'], {}),
                'unmapped_roles': s['contracts'][c['rule_ref']]['unmapped_roles'].get(sl['name'], {}),
                'execution_binding_dependencies': sorted(raw_slots[sl['name']].get('variables', {})),
            })
    return {'case': copy.deepcopy(case), 'original_P': copy.deepcopy(proposal),
            'snapshot': s, 'candidates': chosen, 'requests': [request],
            'directory': directory, 'source_order': [x['id'] for x in sorted(case['segments'], key=lambda x: (x['source_document'], position(x), x['id']))],
            'search_scope': search['requests'], 'version': VERSION, 'deterministic_repairs': repairs}


def supplement(bundle, proposal):
    """Attach new records losslessly; validation/approval is not performed here."""
    return {'case_id': bundle['case']['case_id'], 'version': VERSION,
            'input_sha256': content_hash(bundle), 'proposal_sha256': content_hash(proposal),
            'origin': 'MODEL_PROPOSED', 'formal_legal_approval': False,
            'raw': copy.deepcopy(proposal)}


def schemas(addresses):
    def obj(props):
        return {'type': 'object', 'additionalProperties': False, 'required': list(props), 'properties': props}
    string = {'type': 'string'}
    strs = {'type': 'array', 'items': string}
    witness = obj({'refs': strs, 'quote': string, 'reason': string})
    value = {'type': ['string', 'number', 'array', 'null'], 'items': {'type': ['string', 'number']}}
    binding = obj({'role': string, 'variable': string, 'value': value,
                   'status': {'enum': ['BOUND', 'UNKNOWN', 'NOT_APPLICABLE']},
                   'witnesses': {'type': 'array', 'items': witness}, 'basis': string})
    use = obj({'purpose': {'enum': PURPOSES}, 'direction': {'enum': CONTRACT['directions']},
               'witnesses': {'type': 'array', 'items': witness}, 'explanation': string})
    component = obj({'component': string, 'covered': {'type': 'boolean'},
                     'witnesses': {'type': 'array', 'items': witness}, 'basis': string})
    whole = obj({'state': {'enum': CONTRACT['truth_states']}, 'complete': {'type': 'boolean'},
                 'basis': string, 'components': {'type': 'array', 'items': component},
                 'missing_components': strs, 'use_indices': {'type': 'array', 'items': {'type': 'integer', 'minimum': 1}}})
    alignment = obj({'address': {'enum': addresses},
        'bindings': {'type': 'array', 'items': binding}, 'uses': {'type': 'array', 'items': use},
        'whole_premise': whole, 'statement_status': string, 'court_level': string,
        'source_stage': string, 'rule_stage': string,
        'counterevidence': {'type': 'array', 'items': witness}, 'limitations': strs})
    proposal = obj({'alignments': {'type': 'array', 'items': alignment}, 'coverage_limits': strs})
    decision = obj({'address': {'enum': addresses}, 'decision': {'enum': ['ACCEPT', 'REJECT', 'UNRESOLVED']},
                    'scope': {'enum': ['ALIGNMENT', 'BINDING', 'USE', 'WHOLE_PREMISE']}, 'role': string, 'use_index': {'type': ['integer', 'null'], 'minimum': 1},
                    'reason': string, 'witnesses': {'type': 'array', 'items': witness},
                    'counterevidence': {'type': 'array', 'items': witness}, 'limitations': strs})
    review = obj({'reviews': {'type': 'array', 'items': decision}, 'coverage_limits': strs})
    return proposal, review


INSTRUCTIONS = """Historical judgment reasoning reconstruction, not verdict prediction.
Read only the supplied permitted sources, original untrusted P, selected request,
and unchanged rules. Do not search externally, use other conversations, or consult
old answers/reviews. Output English JSON once using the supplied schema. An address
identifies an existing candidate/premise, not a correct answer. Retain alternative
routes, counterevidence, missing information and procedural attribution.

Propose a source alignment for each address you can assess; omission is allowed
but must be disclosed. Bind each rule role to an explicitly named candidate/use
variable, preserving exact existing values; a null or a type is not identity.
If the existing value is missing, a new binding needs an exact source witness.
UNKNOWN is permitted. NOT_APPLICABLE is only for a role of an explicitly absent
event when the whole premise is FALSE, with an exact witness and explanation.
Do not infer that event absence follows from no evidence. Multiple records can
cover different parts if their objects and scope are explicitly connected.

Every use has a specific function. REPORT_ASSERTION proves that a party asserted
something, not its occurrence. PARTIAL_SUPPORT/PARTIAL_OPPOSITION/BACKGROUND
cannot themselves fill a whole premise. Effective opposition can be usable.
Identify in whole_premise.use_indices the one-based uses your whole judgment depends on. Fixed execution_binding_dependencies come from the unchanged rule roles and cannot be deleted by the model. Separately state the whole-premise judgment, its component coverage and remaining
gaps; complete=true is your unverified semantic claim, not program approval.
For a whole judicial premise use RECONSTRUCT_COURT_PREMISE, preserving the court
level, actual source stage and fixed rule stage; never upgrade a lower finding.
Hypothetical/future statements do not establish an actual event. Do not use final
disposition to prove itself. Legal material explains rules, not case occurrences.

Use exact quotations from supplied IDs. An old null quote stays null: propose a
new witness rather than guessing its intended quote. Explicit separate excerpts
may be different witnesses, never a fabricated continuous sentence. Statement
status must use the fixed slot's allowed vocabulary when applicable. You cannot
rewrite rules, exceptions, polarity, operator, or manufacture review approval.
UNKNOWN and CONFLICTED are valid semantic states. Technical failure is separate.
Write brief basis statements, retain decisive qualifications; do not reproduce
the full source in each field. No hashes, internal IDs or approval fields.
"""


def synthetic_example():
    w = lambda ref, quote, reason: {'refs': [ref], 'quote': quote, 'reason': reason}
    a = w('SYN:L1', 'Trial court found Room A remained under Mira’s control.', 'Attributed trial finding, not the reviewing court’s endorsement.')
    b = w('SYN:L2', 'Owner alleged that Len alone controlled Room A.', 'Owner’s contrary allegation, not an adjudicated fact.')
    return {
        'input': {'sources': [{'id': 'SYN:L1', 'text': 'Trial court found Room A remained under Mira’s control.'},
                              {'id': 'SYN:L2', 'text': 'Owner alleged that Len alone controlled Room A.'}],
                  'teaching_rule_only': 'Fictional rule: a trial finding of retained control supplies a trial-stage control premise; it does not settle an appeal.',
                  'address': {'address': 'EX01', 'proposition': 'At trial, Mira was found to retain control of Room A.',
                              'roles': {'holder': 'person', 'room': 'property'}, 'variables': {'tenant': 'Mira', 'premises': 'Room A'}, 'rule_stage': 'trial finding reconstruction'}},
        'output': {'alignments': [{'address': 'EX01', 'bindings': [
            {'role': 'holder', 'variable': 'tenant', 'value': 'Mira', 'status': 'BOUND', 'witnesses': [a], 'basis': 'The trial finding names Mira.'},
            {'role': 'room', 'variable': 'premises', 'value': 'Room A', 'status': 'BOUND', 'witnesses': [a], 'basis': 'Both passages name the same room; no event is merged merely by role.'}],
            'uses': [{'purpose': 'RECONSTRUCT_COURT_PREMISE', 'direction': 'SUPPORT', 'witnesses': [a], 'explanation': 'Reports the trial finding only.'},
                     {'purpose': 'PARTIAL_OPPOSITION', 'direction': 'OPPOSE', 'witnesses': [b], 'explanation': 'Retains the disputed party allegation; not proof of Len’s control.'}],
            'whole_premise': {'state': 'TRUE', 'complete': True, 'basis': 'The proposition is only that this finding was made at trial.',
                'components': [{'component': 'Mira and Room A in the attributed trial finding', 'covered': True, 'witnesses': [a], 'basis': 'All elements of this narrow reporting premise are explicit.'}], 'missing_components': [], 'use_indices': [1]},
            'statement_status': 'LOWER_COURT_FINDING', 'court_level': 'trial court', 'source_stage': 'trial judgment', 'rule_stage': 'trial finding reconstruction',
            'counterevidence': [b], 'limitations': ['No material supplies the reviewing court’s acceptance of the finding.']}],
            'coverage_limits': ['The synthetic rule proves no ultimate legal entitlement.']},
        'independent_review_example': {'reviews': [{'address': 'EX01', 'decision': 'ACCEPT', 'scope': 'ALIGNMENT', 'role': '', 'use_index': None, 'reason': 'Accept the attributed trial finding only; the allegation remains distinct.',
            'witnesses': [a], 'counterevidence': [b], 'limitations': ['Appeal effect is not established.']}], 'coverage_limits': ['No legal approval supplied.']}}


def task(bundle, role='proposal', proposed=None):
    import json
    ps, rs = schemas([d['address'] for d in bundle['directory']])
    instructions = INSTRUCTIONS
    if role == 'review':
        instructions = """Independently source-review the actual proposed alignments below. Read the
complete permitted source and important opposing passages, not only quotations
chosen by the proposer. For each address return ACCEPT, REJECT or UNRESOLVED of
a specified scope: BINDING (role), USE (one-based use_index), WHOLE_PREMISE
(the exact stated proposition/attribution/completeness), or ALIGNMENT (all of it).
Provide separate decisions for each submitted binding, use and whole premise.
For nonbinding scopes role is an empty string; for nonuse scopes use_index is null.
A rejected binding must remain rejected; it need not negate an independently
witnessed narrow court finding. Execution still requires all fixed rule binding
dependencies. Do not broaden an absent special event into absence of all events.
Accept limited FALSE/UNKNOWN conclusions when justified. Do not rewrite a rejected
proposal or supply replacement bindings/answers. Report exact source witnesses,
decisive opposition and limits. A plausible self-explanation is not approval.
This is model-assisted research review, not formal legal approval. Do not search,
use other conversations or old reference labels. Output English JSON once.
""" + INSTRUCTIONS
    material = {'task_role': role, 'contract': CONTRACT, 'request': bundle['requests'][0],
                'address_directory': bundle['directory'], 'unchanged_rules': bundle['snapshot']['rules'],
                'original_untrusted_P': bundle['original_P'],
                'allowed_sources': [bundle['snapshot']['sources'][i] for i in bundle['source_order']]}
    if role == 'review':
        material['actual_unreviewed_proposal'] = proposed
    return instructions + '\nCOMPLETE SYNTHETIC TEACHING EXAMPLE (not target law):\n' + json.dumps(synthetic_example(), ensure_ascii=False, indent=2) + '\nOUTPUT SCHEMA:\n' + json.dumps(rs if role == 'review' else ps, indent=2) + '\nCOMPLETE TASK MATERIAL:\n' + json.dumps(material, ensure_ascii=False, indent=2)
