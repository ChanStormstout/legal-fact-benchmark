"""V5 legal addresses and sparse evidence; no source or legal semantic changes."""
import copy
import json

from .contract_v5 import address_directory, display
from .pipeline_v4_tasks import GUIDE, FINAL_GUIDE, EXAMPLES, schema as old_schema
from .hybrid_v3_tasks import obj, arr, S, enum, A, USE, STAT

PROPOSAL_GUIDE = '''Generate sparse attributed records for the specified request.
bindings identifies an actual arrangement: persons, premises, conduct or transaction and procedural stage, supported by refs. A date question, consent question or retained-possession question is not by itself a different arrangement. Keep genuinely different arrangements distinct; shared names or premises alone do not establish identity. Do not fill missing facts or merge uncertain identities. No complete five-role tuple is required.
evidence preserves the compact attributed record, source IDs and statement_status independently of its uses. Use binding_id="" and uses=[] when its arrangement is unresolved; never invent an arrangement to save a record. Each use selects exactly one condition_address from ADDRESS_DIRECTORY, direction (SUPPORT, OPPOSE or UNKNOWN) and purpose. The address deterministically determines its test_id and branch_id: do not output those two fields. An element ID is never a condition address. CONDITION_INFERENCE is a proposed argument, RECORD_EXISTENCE only records existence, PROVEN_FACT needs established status, and TARGET_ACCEPTANCE is not implied by a prior finding. A record survives even with an empty uses array.
limitations states binding_id, condition_address, use, effect, evidence_ids, reason and refs. USE_BLOCK limits only the listed witnesses' use. PROPOSITION_BLOCK with empty evidence_ids explicitly concerns the entire named proposition within that binding and purpose; it needs a sourced whole-proposition justification. NOTE preserves a non-blocking caveat. SCOPE_UNMAPPED records uncertainty. Limitations never automatically become opposition. Keep independent evidence and independent OR branches.
conditions is optional in coverage: provide a summary only if useful, using condition_address, binding_id, assessment, evidence_ids and gap. Its absence is not a defect or absence of evidence. A summary alone supplies no evidence use. Keep an empty array when no summary is needed. All top-level arrays exist but may be empty. Preserve decisive opposing evidence, unresolved identity and scope in coverage_limits. Prefer 3-6 decisive evidence items; maxima inherited from V4 are ceilings, not targets. Do not emit rows merely to cover every condition. Return complete JSON; never repair a missing fact to meet an interface.'''

EXAMPLE_PROPOSAL = {
    'bindings': [{'id': 'b1', 'claim_ids': ['CERTIFY'], 'objects': 'Mira; beacon Z',
                  'event': 'Beacon installation', 'stage': 'Appeal from district panel', 'refs': ['S1']}],
    'evidence': [{'id': 'e1', 'binding_id': 'b1', 'record': 'The district panel found personal installation by Mira; the appeal challenges that finding.',
                  'statement_status': 'PRIOR_COURT_FINDING', 'refs': ['S1'],
                  'uses': [{'condition_address': 'ADDR-001', 'direction': 'SUPPORT', 'use': 'CONDITION_INFERENCE'}]}],
    'limitations': [{'id': 'l1', 'evidence_ids': ['e1'], 'binding_id': 'b1', 'condition_address': 'ADDR-001',
                     'use': 'TARGET_ACCEPTANCE', 'effect': 'USE_BLOCK', 'reason': 'The prior finding does not establish appellate acceptance.', 'refs': ['S1']}],
    'conditions': [], 'coverage_limits': ['The appeal challenge remains open; no summary row is needed to preserve the evidence.']}


def schema(stage, material, template, law):
    if stage != 'proposal':
        return old_schema(stage, material, template, law)
    refs = arr(enum(list(material['sources']) + [s['source_id'] for s in law]), 6)
    addr = enum(list(address_directory(template)))
    claims = enum([c['id'] for c in template['claims'] if c['expression']['op'] != 'UNSUPPORTED'])
    return obj({
        'bindings': arr(obj({'id': S, 'claim_ids': arr(claims, 2), 'objects': S, 'event': S, 'stage': S, 'refs': refs}), 4),
        'evidence': arr(obj({'id': S, 'binding_id': S, 'record': S, 'statement_status': STAT, 'refs': refs,
                             'uses': arr(obj({'condition_address': addr, 'direction': enum(['SUPPORT', 'OPPOSE', 'UNKNOWN']), 'use': USE}), 8)}), 10),
        'limitations': arr(obj({'id': S, 'evidence_ids': arr(S, 6), 'binding_id': S, 'condition_address': addr,
                                'use': USE, 'effect': enum(['USE_BLOCK', 'PROPOSITION_BLOCK', 'NOTE', 'SCOPE_UNMAPPED']), 'reason': S, 'refs': refs}), 8),
        'conditions': arr(obj({'binding_id': S, 'condition_address': addr, 'assessment': A, 'evidence_ids': arr(S, 6), 'gap': S}), 24),
        'coverage_limits': arr(S, 4)})


def prompt(stage, material, template, law, source_map, intermediate=None):
    view, _, _ = display(material, source_map)
    parts = [GUIDE, 'TWO COMPLETE FICTIONAL EXAMPLES:', json.dumps(EXAMPLES, ensure_ascii=False)]
    if stage == 'proposal':
        parts += [PROPOSAL_GUIDE, 'FICTIONAL EXAMPLE ADDRESS DIRECTORY (not target law):',
                  json.dumps({'ADDR-001': {'test_id': 'INSTALL', 'branch_id': 'INSTALL/SELF', 'text': 'Operator personally installed this beacon.'}}),
                  'Complete fictional sparse proposal example:', json.dumps(EXAMPLE_PROPOSAL, ensure_ascii=False)]
    else:
        parts.append(FINAL_GUIDE)
    parts += ['ADDRESS_DIRECTORY:', json.dumps(address_directory(template), ensure_ascii=False),
              'COMMON GIVEN LAW:', json.dumps(law, ensure_ascii=False),
              'COMMON LEGAL STRUCTURE:', json.dumps(template, ensure_ascii=False),
              'INTERMEDIATE MATERIAL:', json.dumps(intermediate or {}, ensure_ascii=False),
              'COMPLETE ALLOWED CASE MATERIAL:', json.dumps(view, ensure_ascii=False),
              'TASK: ' + ('Propose sparse attributed evidence and its uses.' if stage == 'proposal' else
                          'Under the supplied facts, law and procedural stage, should each specified substantive request be supported? State a request prediction while retaining evidence uncertainty.')]
    return '\n\n'.join(parts)
