import copy
import unittest

from scripts.rgcn09_labels import validate, reviewed_supervision, training_gate, model_material
from scripts.rgcn09_data import resolve_renderer_markers


class CoarseUseTests(unittest.TestCase):
    def setUp(self):
        self.case = {'case_id': '1', 'split': 'TRAIN', 'segments': [
            {'id': 'IK-1:L1', 'text': 'Tenant disputes exclusive possession.',
             'source_document': '1', 'provenance': {'raw': 'kept offline'}}]}
        self.units = [{'id': 'LAW:A', 'text': 'Assess retained control.',
                       'scope': 'Delhi; conditional', 'coverage_limit': 'Not every presence is subletting',
                       'source': {'document_id': '99', 'raw_provenance': ['offline address']}},
                      {'id': 'LAW:B', 'text': 'Other scope.', 'source': {'document_id': '98'}}]
        self.item = {'unit_id': 'LAW:A', 'category': 'CORE', 'reason': 'Disputed control is live.',
                     'case_refs': ['IK-1:L1'], 'law_quote': 'retained control'}
        self.payload = {'case_id': '1', 'uses': [self.item], 'unresolved': []}

    def test_unknown_and_unlabelled_not_negative(self):
        v = validate(self.payload, self.case, self.units)
        self.assertEqual(v['unlabelled'], ['LAW:B'])
        self.assertEqual(reviewed_supervision(v, []), [])
        self.assertEqual(reviewed_supervision(v, ['LAW:A']), [('LAW:A', 0)])
        p = copy.deepcopy(self.payload); p['uses'][0]['category'] = 'UNKNOWN'
        v = validate(p, self.case, self.units)
        self.assertEqual(v['known'], [])
        with self.assertRaisesRegex(ValueError, 'REVIEW_ID'):
            reviewed_supervision(v, ['LAW:A'])

    def test_forged_addresses_quotes_and_micro_fields_rejected(self):
        for key, value, error in [('case_refs', ['IK-2:L1'], 'CASE_ADDRESS'),
                                 ('law_quote', 'Invented rule', 'QUOTE_NOT_EXACT')]:
            p = copy.deepcopy(self.payload); p['uses'][0][key] = value
            with self.assertRaisesRegex(ValueError, error): validate(p, self.case, self.units)
        p = copy.deepcopy(self.payload); p['uses'][0]['preferred_over'] = 'LAW:B'
        with self.assertRaisesRegex(ValueError, 'COARSE_FIELDS_ONLY'): validate(p, self.case, self.units)

    def test_sealed_block_and_group_leakage(self):
        self.case['split'] = 'SEALED_TEST'
        with self.assertRaisesRegex(ValueError, 'SEALED_TEST'): validate(self.payload, self.case, self.units)
        m = {'cases': [{'case_id': '1', 'group_id': 'g', 'split': 'TRAIN'},
                       {'case_id': '2', 'group_id': 'g', 'split': 'SEALED_TEST'}]}
        with self.assertRaisesRegex(ValueError, 'CROSSES_SPLIT'):
            training_gate(m, [], {'reserved_authority_case_ids': []})

    def test_training_gate_not_open_at_ten_and_no_dev_labels(self):
        m = {'cases': [{'case_id': str(i), 'group_id': str(i), 'split': 'TRAIN'} for i in range(10)]}
        pool = {'reserved_authority_case_ids': []}
        self.assertFalse(training_gate(m, [str(i) for i in range(10)], pool)['open'])
        with self.assertRaisesRegex(ValueError, 'NONTRAIN_SUPERVISION'):
            training_gate(m, ['99'], pool)
        with self.assertRaisesRegex(ValueError, 'AUTHORITY_SOURCE'):
            training_gate(m, [], {'reserved_authority_case_ids': ['1']})

    def test_display_preserves_all_text_and_scope(self):
        view, laws = model_material(self.case, self.units)
        self.assertEqual(view['segments'][0]['text'], self.case['segments'][0]['text'])
        self.assertEqual(laws[0]['text'], self.units[0]['text'])
        self.assertEqual(laws[0]['scope'], self.units[0]['scope'])
        self.assertEqual(laws[0]['coverage_limit'], self.units[0]['coverage_limit'])
        self.assertNotIn('raw_provenance', laws[0]['source'])
        self.assertIn('raw_provenance', self.units[0]['source'])

    def test_renderer_only_resolution_never_changes_words(self):
        d = {'conflicts': [{'existing': 'Act \ue200cite\ue20213†s.', 'alternative': 'Act 【13†s.'}],
             'unparsed': [], 'totals': [2], 'missing_lines': [], 'status': 'CONFLICT'}
        fixed = resolve_renderer_markers(d)
        self.assertEqual(fixed['status'], 'COMPLETE_RENDERING')
        self.assertEqual(len(fixed['equivalent_renderer_variants']), 1)
        self.assertEqual(d['status'], 'CONFLICT')
        d['conflicts'][0]['alternative'] = 'Not Act 【13†s.'
        self.assertEqual(resolve_renderer_markers(d)['status'], 'CONFLICT')


if __name__ == '__main__':
    unittest.main()
