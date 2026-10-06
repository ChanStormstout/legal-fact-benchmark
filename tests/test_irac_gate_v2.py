import copy
import unittest
from legal_bench.rules_verdict_v1.irac_gate_v2 import (
    admit_record, digest, inference_payload, validate_blind_binding, validate_condition)


class StageAndBlindGateTests(unittest.TestCase):
    def setUp(self):
        self.fact = {'id': 'f1', 'status': 'FOUND', 'court': 'TRIAL',
                     'stage': 'ARC trial 1990', 'refs': ['p1'], 'text': 'A disputed prior finding'}
        self.grant = {'semantic_stage': 'PRIOR_COURT_FINDING', 'input_allowed': True,
                      'source_refs': ['p1'], 'prospective_availability': 'RETROSPECTIVELY_RECONSTRUCTED_PRE_TARGET'}
        self.sg = {'p1': copy.deepcopy(self.grant)}
        self.binding = {'fact_id': 'f1', 'condition_id': 'c1', 'relation': 'RELEVANT_TO',
                        'source_refs': ['p1'], 'statement_status': 'FOUND',
                        'court_stage': {'court': 'TRIAL', 'stage': 'ARC trial 1990'}}

    def test_target_findings_and_reasoning_edges_blocked_for_all_types(self):
        for kind in ['Fact', 'Relation', 'Claim', 'Evidence', 'GraphEdge', 'Sidecar']:
            for stage in ['TARGET_COURT_REASONING', 'TARGET_DISPOSITION', 'AMBIGUOUS']:
                with self.subTest(kind=kind, stage=stage):
                    grant = dict(self.grant, semantic_stage=stage, input_allowed=False)
                    value, errors = admit_record(dict(self.fact, type=kind, court='TARGET'), grant, self.sg)
                    self.assertIsNone(value); self.assertTrue(errors)
        value, errors = admit_record(dict(self.fact, court='TARGET'), self.grant, self.sg)
        self.assertIsNone(value); self.assertIn('TARGET_FOUND_NOT_INPUT', errors)

    def test_prior_findings_retained_without_promotion_and_mixed_source_blocked(self):
        value, errors = admit_record(self.fact, self.grant, self.sg)
        self.assertEqual(value, self.fact); self.assertFalse(errors)
        source = {'p1': dict(self.grant, semantic_stage='TARGET_COURT_REASONING', input_allowed=False)}
        self.assertIsNone(admit_record(self.fact, self.grant, source)[0])

    def test_blind_binding_unknown_fact_target_source_and_status_change(self):
        facts = {'f1': self.fact}; conditions = {'c1': {}}; grants = {'f1': self.grant}
        self.assertEqual(validate_blind_binding(self.binding, facts, conditions, self.sg, grants), [])
        for change, expected in [({'fact_id': 'new'}, 'UNKNOWN_OR_NEW_FACT_FORBIDDEN'),
                                 ({'source_refs': ['post']}, 'BINDING_REF_NOT_IN_FACT_PROVENANCE'),
                                 ({'statement_status': 'CLAIMED'}, 'FACT_STATUS_CHANGED')]:
            errors = validate_blind_binding(dict(self.binding, **change), facts, conditions, self.sg, grants)
            self.assertIn(expected, errors)
        self.assertTrue(validate_blind_binding(self.binding, facts, conditions,
            {'p1': dict(self.grant, input_allowed=False)}, grants))

    def test_independent_rule_condition_required(self):
        condition = {'rule_id': 'R1', 'exact_rule_quote': 'legal possession', 'source_refs': ['law:p1'], 'dependencies': []}
        good = {'R1': {'independent_source_verified': True, 'exact_quote': 'Retains legal possession'}}
        self.assertFalse(validate_condition(condition, good))
        self.assertIn('NO_INDEPENDENT_RULE_SOURCE', validate_condition(condition, {}))
        self.assertIn('RULE_QUOTE_NOT_LOCATED', validate_condition(dict(condition, exact_rule_quote='invented'), good))

    def test_targets_and_oracle_selection_never_change_input_or_binding_hash(self):
        rule = {'rule_id': 'R1', 'exact_quote': 'independent law', 'oracle_selection_basis': 'target says yes'}
        args = ('fixed issue', [rule], [], [self.fact], [], [], [])
        before = digest(inference_payload(*args)); bh = digest(self.binding)
        target = {'status': 'SATISFIED'}; target['status'] = 'DEFEATED'
        rule['oracle_selection_basis'] = 'changed target label'
        payload = inference_payload(*args)
        self.assertEqual(before, digest(payload)); self.assertEqual(bh, digest(self.binding))
        self.assertNotIn('targets', payload); self.assertNotIn('oracle_selection_basis', payload['rules'][0])


if __name__ == '__main__':
    unittest.main()
