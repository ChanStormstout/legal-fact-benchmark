"""Failure injections and actual saved-entry checks; no real model calls."""
import copy
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from tests.test_pipeline_diagnostic_v19_8 import pair, part
from legal_bench.proof_carrying import evidence_binding_gate_v20_5 as gate
from legal_bench.proof_carrying import local_pipeline_v19_8 as core
from legal_bench.proof_carrying import shared_sources_v20_3 as shared
from legal_bench.proof_carrying.declared_references_v20_4 import wire_order
from legal_bench.mlx_json_constraint_v20_5 import EvidenceBindingParser
from legal_bench.proof_carrying.rule_contracts_v19_7 import digest


def setup():
    c, r, raw = pair()
    original = core.schema(r, c)
    compact = wire_order(shared.pack(raw), shared.schema(original))
    return c, r, raw, original, compact


def reviews(raw, case, rules):
    rows = []
    for pid, u in raw['analyses'].items():
        for coll in ('uses', 'judgments'):
            for i, row in enumerate(u[coll]):
                for role, ref in row['role_objects'].items():
                    if ref == 'UNMAPPED': continue
                    path = ['analyses', pid, coll, i, 'role_objects', role]
                    rows.append({'path': path, 'claim_sha256': digest(gate.binding_claim(raw, path)),
                                 'label': 'SUPPORTED', 'refs': ['SRC:1'],
                                 'reason': 'Synthetic fixture review only; not a real legal annotation.'})
    return {'payload_sha256': digest(raw), 'source_sha256': digest(case['segments']),
            'rule_sha256': digest(rules), 'verdicts': rows}


def parse(value, schema):
    parser = EvidenceBindingParser(schema)
    for char in json.dumps(value, separators=(',', ':')):
        parser = parser.add_character(char)
    return parser


class EvidenceBindings(unittest.TestCase):
    def test_noncontiguous_source_addresses_do_not_renumber_or_drop_source(self):
        c, r, raw, original, compact = setup()
        c['segments'][1]['text'] = ' \n\t'
        before = copy.deepcopy(c)
        sc = gate.generation_schema(core.schema(r, c), c, r)
        self.assertIn('SRC:1', sc['$defs']['source_choice']['enum'])
        self.assertNotIn('SRC:2', sc['$defs']['source_choice']['enum'])
        if len(c['segments']) > 2: self.assertIn('SRC:3', sc['$defs']['source_choice']['enum'])
        self.assertEqual(c, before)

    def test_blank_choice_is_blocked_before_generation_of_source_set(self):
        c, r, raw, original, compact = setup()
        c['segments'][0]['text'] = ''
        compact['source_sets'][0] = ['SRC:1']
        with self.assertRaises(ValueError): parse(compact, gate.generation_schema(original, c, r))

    def test_required_witness_locator_failure_is_not_promoted(self):
        c, r, raw, original, compact = setup()
        with patch('legal_bench.proof_carrying.source_contract_v19.witness_location',
                   return_value={'error': 'QUOTE_NOT_LOCATED'}):
            result = gate.process_saved(c, r, part(c, r), compact, original, reviews=reviews(raw, c, r))
        self.assertIsNone(result['formal_answer'])
        self.assertTrue(any(x['kind'] == 'REQUIRED_WITNESS_NOT_LOCATED' for x in result['gate']['errors']))

    def test_acceptance_writes_separate_null_answer_and_preserves_raw(self):
        c, r, raw, original, compact = setup()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); src = root/'generation'; src.mkdir()
            (src/'run.json').write_text(json.dumps({'run_status':'OK'}))
            (src/'parsed.json').write_text(json.dumps(compact))
            (src/'raw-response.txt').write_text('saved raw bytes')
            gate.accept_saved(src, root/'acceptance', c, r, part(c, r), original)
            self.assertIsNone(json.loads((root/'acceptance/formal-answer.json').read_text())['answer'])
            self.assertEqual((src/'raw-response.txt').read_text(), 'saved raw bytes')
            with self.assertRaises(ValueError):
                gate.accept_saved(src, src/'nested', c, r, part(c, r), original)

    def test_prompt_replaces_conflict_and_preserves_every_source_byte(self):
        c, r, raw, original, compact = setup()
        old = core.proposal_prompt(c, r, part(c, r))
        p = gate.prompt(shared.INSTRUCTION+old)
        marker = '\nALLOWED SOURCE (copy the adjacent SRC address):\n'
        self.assertEqual(p.split(marker, 1)[1], old.split(marker, 1)[1])
        self.assertNotIn('dynamic existence is checked on import, not guaranteed by the decoder', p)
        self.assertIn('FICTIONAL TWO-ANALYSIS RESET EXAMPLE', p)

    def test_blank_selected_witness_rejected_without_rewriting_old_payload(self):
        c, r, raw, original, compact = setup()
        selected = raw['analyses']['R1.P1']['uses'][0]['witnesses'][0]['source']
        c['segments'][int(selected.split(':')[1])-1]['text'] = ''
        before = copy.deepcopy(compact)
        a = gate.audit(compact, original, c, r)
        self.assertEqual(a['status'], 'REJECTED_EVIDENCE_OR_BINDING')
        self.assertTrue(any(x['kind'] == 'EMPTY_OR_MISSING_SOURCE' for x in a['errors']))
        entry = gate.process_saved(c, r, part(c, r), compact, original)
        self.assertIsNone(entry['formal_answer']); self.assertIsNone(entry['conditional_audit'])
        self.assertEqual(compact, before)

    def test_explicit_property_person_conflict_blocked_during_generation(self):
        c, r, raw, original, compact = setup()
        for rule in r:
            for premise in rule['premises']:
                premise['variables']['tenant'] = 'PROPERTY'
        sc = gate.generation_schema(original, c, r)
        with self.assertRaises(ValueError): parse(compact, sc)
        a = gate.audit(compact, original, c, r)
        self.assertTrue(any(x['kind'] == 'EXPLICIT_TYPE_CONFLICT' for x in a['errors']))

    def test_exact_generic_type_alias_only(self):
        c, r, raw, original, compact = setup()
        p = r[0]['premises'][0]
        p['variables']['tenant'] = 'UNMAPPED'
        p['original_variable_descriptions'] = {'tenant': 'identified leased property'}
        self.assertEqual(gate.role_types(r)[p['id']]['tenant'], 'PROPERTY')
        p['original_variable_descriptions']['tenant'] = 'disputed property-related entitlement'
        self.assertEqual(gate.role_types(r)[p['id']]['tenant'], 'UNMAPPED')

    def test_unmapped_is_available_when_no_type_compatible_object(self):
        c, r, raw, original, compact = setup()
        for rule in r:
            for premise in rule['premises']: premise['variables']['tenant'] = 'PROPERTY'
        for u in compact['analyses'].values():
            for row in u['uses']+u['judgments']: row['role_objects']['tenant'] = 'UNMAPPED'
        self.assertTrue(parse(compact, gate.generation_schema(original, c, r)).can_end())
        self.assertEqual(gate.audit(compact, original, c, r)['status'], 'BINDING_REVIEW_PENDING')

    def test_unknown_type_not_claimed_as_verified(self):
        c, r, raw, original, compact = setup()
        for u in compact['analyses'].values():
            for o in u['objects']: o['type'] = 'UNMAPPED'
        self.assertTrue(parse(compact, gate.generation_schema(original, c, r)).can_end())
        a = gate.audit(compact, original, c, r)
        self.assertEqual(a['status'], 'BINDING_REVIEW_PENDING')
        self.assertTrue(all(not x['identity_established_by_code'] for x in a['bindings']))

    def test_same_type_identity_cannot_be_accepted_from_ordinal_alone(self):
        c, r, raw, original, compact = setup()
        a = gate.process_saved(c, r, part(c, r), compact, original)
        self.assertEqual(a['contract_status'], 'BINDING_REVIEW_PENDING')
        self.assertIsNone(a['formal_answer']); self.assertIsNone(a['conditional_audit'])

    def test_reviewed_rejection_and_unresolved_are_not_unreviewed(self):
        c, r, raw, original, compact = setup()
        v = reviews(raw, c, r); v['verdicts'][0]['label'] = 'UNSUPPORTED'
        a = gate.audit(compact, original, c, r, v)
        self.assertEqual(a['status'], 'BINDING_REVIEW_REJECTED')
        self.assertEqual(a['rejected_bindings'], 1); self.assertEqual(a['pending_bindings'], 0)
        v['verdicts'][0].update(label='UNRESOLVED', refs=[])
        a = gate.audit(compact, original, c, r, v)
        self.assertEqual(a['status'], 'BINDING_REVIEW_PENDING')
        self.assertEqual(a['binding_state_counts']['REVIEW_UNRESOLVED'], 1)

    def test_sourced_review_runs_actual_conversion_merge_and_checker(self):
        c, r, raw, original, compact = setup()
        before = copy.deepcopy(compact)
        a = gate.process_saved(c, r, part(c, r), compact, original, reviews=reviews(raw, c, r))
        self.assertEqual(a['contract_status'], 'CONTRACT_VALID')
        self.assertEqual(a['formal_answer'], raw)
        for k in ('independent_import', 'independent_merge', 'independent_check'):
            self.assertEqual(a['original_entry'][k]['status'], 'OK')
        self.assertEqual(compact, before); self.assertFalse(a['semantic_approval'])

    def test_stale_duplicate_or_unanchored_reviews_never_unlock(self):
        c, r, raw, original, compact = setup()
        for mode in ('stale', 'duplicate', 'missing_source', 'wrong_claim', 'wrong_rules'):
            v = reviews(raw, c, r)
            if mode == 'stale': v['payload_sha256'] = 'old'
            if mode == 'duplicate': v['verdicts'].append(copy.deepcopy(v['verdicts'][0]))
            if mode == 'missing_source': v['verdicts'][0]['refs'] = []
            if mode == 'wrong_claim': v['verdicts'][0]['claim_sha256'] = 'wrong'
            if mode == 'wrong_rules': v['rule_sha256'] = 'old'
            self.assertEqual(gate.audit(compact, original, c, r, v)['status'], 'BINDING_REVIEW_PENDING', mode)

    def test_existing_q_verdicts_require_matching_frozen_input_context(self):
        c, r, raw, original, compact = setup()
        q = {'supplement': {'analyses': {}}, 'verdicts': []}
        for row in reviews(raw, c, r)['verdicts']:
            path = row['path']; prefix = 'USE' if path[2] == 'uses' else 'J'
            q['verdicts'].append({'declaration': 'P/'+path[1]+'/'+prefix+':'+str(path[3]+1)+'/ROLE:'+path[5],
                                 'label':'SUPPORTED','refs':['SRC:1'],'counter_refs':[],
                                 'reason':'Synthetic existing verifier verdict only.'})
        context = {'original_P_sha256':digest(raw),'source_sha256':digest(c['segments']),
                   'rule_sha256':digest(r),'run_status':'OK'}
        v = gate.reviews_from_q(raw, c, r, q, context)
        self.assertEqual(gate.audit(compact, original, c, r, v)['status'], 'READY_FOR_CONDITIONAL_PROCESSING')
        context['original_P_sha256'] = 'old'
        v = gate.reviews_from_q(raw, c, r, q, context)
        self.assertEqual(gate.audit(compact, original, c, r, v)['status'], 'BINDING_REVIEW_PENDING')

    def test_malformed_reviews_and_type_conflict_cannot_be_overridden(self):
        c, r, raw, original, compact = setup()
        v = reviews(raw, c, r); v['verdicts'][0]['refs'] = [{}]
        self.assertEqual(gate.audit(compact, original, c, r, v)['status'], 'BINDING_REVIEW_PENDING')
        v = reviews(raw, c, r); v['verdicts'][0]['path'] = [{}]
        self.assertEqual(gate.audit(compact, original, c, r, v)['status'], 'BINDING_REVIEW_PENDING')
        for z in r:
            for p in z['premises']: p['variables']['tenant'] = 'PROPERTY'
        v = reviews(raw, c, r)
        self.assertEqual(gate.audit(compact, original, c, r, v)['status'], 'REJECTED_EVIDENCE_OR_BINDING')

    def test_cross_unit_global_index_still_rejected(self):
        c, r, raw, original, compact = setup()
        compact['analyses']['R1.P2']['uses'][0]['records'] = ['EV:999']
        with self.assertRaises(ValueError): parse(compact, gate.generation_schema(original, c, r))
        self.assertEqual(gate.audit(compact, original, c, r)['status'], 'REJECTED_EVIDENCE_OR_BINDING')

    def test_all_blank_sources_allow_empty_complete_output(self):
        c, r, raw, original, compact = setup()
        for s in c['segments']: s['text'] = ''
        empty = {'source_sets': [], 'analyses': {}, 'object_links': [], 'coverage_limits': []}
        for pid in raw['analyses']:
            empty['analyses'][pid] = {'analysis_status': 'NOT_ANALYZED', 'records': [], 'objects': [],
                                     'uses': [], 'judgments': [], 'limits': []}
        self.assertTrue(parse(empty, gate.generation_schema(original, c, r)).can_end())

    def test_only_not_analyzed_entries_do_not_claim_readiness(self):
        c, r, raw, original, compact = setup()
        empty = {'analyses': {}, 'object_links': [], 'coverage_limits': []}
        for pid in raw['analyses']:
            empty['analyses'][pid] = {'analysis_status':'NOT_ANALYZED','records':[],
                                     'objects':[],'uses':[],'judgments':[],'limits':[]}
        value = wire_order(shared.pack(empty), shared.schema(original))
        result = gate.process_saved(c, r, part(c, r), value, original)
        self.assertEqual(result['contract_status'], 'NO_ANALYZED_UNITS')
        self.assertIsNone(result['formal_answer']); self.assertIsNone(result['conditional_audit'])

    def test_reset_example_has_two_nonempty_locally_numbered_analyses(self):
        x = shared.expand(gate.reset_example())
        for u in x['analyses'].values():
            self.assertTrue(u['records']); self.assertEqual(u['uses'][0]['records'], ['EV:1'])
        self.assertEqual(x['analyses']['SYN.P2']['judgments'][0]['uses'], ['USE:1'])
        self.assertIn('Mira', x['analyses']['SYN.P2']['objects'][0]['identity_basis'])
        self.assertNotIn('Rowan', x['analyses']['SYN.P2']['objects'][0]['identity_basis'])


if __name__ == '__main__': unittest.main()
