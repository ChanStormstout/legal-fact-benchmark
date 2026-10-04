import json
import tempfile
import unittest
from pathlib import Path

from legal_bench.rules_verdict_v1 import rule_retrieval_v21 as v


class V21Tests(unittest.TestCase):
    def answer(self):
        return {'outcome': 'UNDETERMINED', 'grounds': [
            {'point': 'Consent exists.', 'case_refs': ['C1'], 'law_refs': ['L1'],
             'assessment': 'UNRESOLVED', 'explanation': 'The party alleges consent; adoption is not established.'}],
                'reason': 'The decisive condition remains unsettled.'}

    def unit(self, key, text='amalgamation rent consent', deps=None):
        return {'id': key, 'text': text, 'source': {'url': 'https://example.invalid/fictional'},
                'version_status': 'FICTIONAL_TEST_ONLY', 'scope': 'fictional', 'dependencies': deps or []}

    def test_soft_limits_and_source_addresses_preserve_values(self):
        answer = self.answer()
        answer['grounds'][0]['case_refs'] = ['C1', 'C2', 'C3', 'C4', 'C5', 'unprovided']
        parsed, trace = v.parse_answer('```json\n'+json.dumps(answer)+'\n```\nEND', ['C1'], ['L1'])
        self.assertEqual(parsed, answer)
        self.assertEqual(trace['run_status'], 'OK')
        self.assertTrue(trace['warnings'])
        self.assertEqual(len(trace['source_issues']), 5)
        self.assertFalse(trace['semantic_correctness_certified'])
        for malformed in [json.dumps(answer)[:-1], json.dumps(answer)+' extra']:
            with self.assertRaises(ValueError): v.parse_answer(malformed, [], [])
        del answer['grounds'][0]['assessment']
        with self.assertRaises(ValueError): v.parse_answer(json.dumps(answer), [], [])

    def test_cross_line_markup_mapping_requires_contiguous_provenance(self):
        originals = [
            {'id': 'C1', 'text': 'A cite9†written', 'original_line': 3, 'source_document': 'D'},
            {'id': 'C2', 'text': 'consent B', 'original_line': 4, 'source_document': 'D'}]
        view = v.reading_view(originals)
        self.assertEqual([s['text'] for s in view['segments']], ['A written', 'consent B'])
        for raw, shown, mapping in zip(originals, view['segments'], view['mapping']):
            self.assertEqual(shown['text'], ''.join(raw['text'][i] for i in mapping['view_character_to_original_character']))
        originals[1]['original_line'] = 6
        self.assertEqual(v.reading_view(originals)['segments'], originals)
        originals[1]['original_line'] = 4
        originals[1]['source_document'] = 'OTHER'
        self.assertEqual(v.reading_view(originals)['segments'], originals)

    def test_atomic_dependencies_budget_and_missing_source(self):
        units = [self.unit('A', deps=['B']), self.unit('B', 'opposing exception')]
        ranks = [{'id': 'A', 'rank': 1}]
        self.assertEqual(v.select_units(ranks, units)['selected_ids'], ['A', 'B'])
        self.assertEqual(v.select_units(ranks, units, max_units=1)['selected_ids'], [])
        self.assertEqual(v.select_units(ranks, units, max_characters=1)['selected_ids'], [])
        result = v.select_units(ranks, units[:1])
        self.assertEqual(result['decisions'][0]['decision'], 'MISSING_REQUIRED_DEPENDENCY')
        result = v.select_units(ranks, units, excluded_ids={'B': 'definite statute incompatibility'})
        self.assertEqual(result['selected_ids'], [])

    def test_rule_dedupe_before_fusion_and_identical_original_inputs(self):
        cards = [{'id': 'R1', 'legal_unit_id': 'A'}, {'id': 'R2', 'legal_unit_id': 'A'},
                 {'id': 'R3', 'legal_unit_id': 'B'}]
        result, trace = v.dedupe_rules([{'id': k, 'rank': n+1} for n, k in enumerate(['R1','R2','R3'])], cards)
        self.assertEqual([(r['id'], r['rank']) for r in result], [('A',1),('B',2)])
        self.assertTrue(trace[1]['duplicate_legal_unit'])
        with tempfile.TemporaryDirectory() as temp:
            units = [self.unit('A')]
            pair = v.retrieve_pair(units, [], 'rent', Path(temp))
            self.assertTrue(pair['legal_blocks_identical'])
            source = {'case_id': 'fictional', 'segments': [{'id':'C1', 'text':'Allowed record.'}],
                      'reference_answer': 'FORBIDDEN_REFERENCE'}
            prompt = v.prompt(source, pair['selected']['A']['units'], 'Evaluate the fictional ground.')
            self.assertNotIn('FORBIDDEN_REFERENCE', prompt)
            self.assertIn('Allowed record.', prompt)
            self.assertNotIn('first_card', prompt)


if __name__ == '__main__': unittest.main()
