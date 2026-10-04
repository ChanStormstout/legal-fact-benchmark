import copy
import json
import unittest

from legal_bench.rules_verdict_v1.final_v9 import final_schema
from legal_bench.rules_verdict_v1.rule_application_v17 import (
    build_pair, material_parts, parse_final, restore_evidence, source_map)


class RuleApplicationTests(unittest.TestCase):
    def setUp(self):
        self.case = {'segments': [{'id': 'C1', 'text': 'Claimed custody; court did not decide it.'}],
                     'excluded_segment_ids': ['C2']}
        self.law = {'law_segments': [{'id': 'L1', 'text': 'Fictional fee rule.'}], 'cards': [{'old': True}]}
        self.authorities = [{'case_id': 'EXAMPLE', 'source_coverage': 'Excerpt only',
                             'segments': [{'id': 'L2', 'text': 'Original "waiver"\ntext and opposing view.'}]}]
        self.collection = {'role': 'UNVERIFIED', 'bundles': [{'case_id': 'EXAMPLE', 'limitations': ['Incomplete'],
            'rule_cards': [{'id': 'R1', 'proposition': 'Provisional view.', 'source_kind': 'PRIMA_FACIE_RESERVED',
                            'scope': 'Fictional law', 'evidence': ['L2'], 'conditions': [],
                            'exceptions': ['Opposing exception'], 'formalization_limits': ['Unknown effect']}]}]}
        self.schema = final_schema(['C1'], ['L1'])
        self.prompt = 'Law and fictional examples\nTARGET INTERMEDIATE MATERIAL (UNVERIFIED)\n{}\nTARGET COMPLETE ALLOWED CASE SOURCE\n[C1] case\nFinal task'
        self.answer = {'outcome': 'UNDETERMINED', 'grounds': [{'point': 'Custody was claimed.',
            'case_refs': ['C1'], 'law_refs': ['L2'], 'assessment': 'SUPPORTED',
            'explanation': 'An allegation remains distinct from a finding.'}], 'reason': 'The fictional material leaves an issue open.'}

    def pair(self):
        return build_pair(self.prompt, self.schema, self.case, self.law, self.authorities, self.collection)

    def test_only_proposal_changes_and_original_recovers(self):
        old = copy.deepcopy(self.collection)
        pair = self.pair()
        a, b = [material_parts(pair['prompts'][k]) for k in ['A_COMMON', 'B_PLUS_V16']]
        self.assertEqual((a[0], a[2]), (b[0], b[2]))
        self.assertEqual(a[1], {})
        self.assertEqual(b[1], {'proposal': old})
        self.assertEqual(pair['prompts']['A_COMMON'].replace(pair['authority_block'], '', 1), self.prompt)
        self.assertEqual(self.collection, old)
        self.assertEqual(pair['schema']['properties']['grounds']['items']['properties']['law_refs']['items']['enum'], ['L1', 'L2'])

    def test_unknown_limits_and_original_quotation_restored(self):
        pair = self.pair()
        proposal = material_parts(pair['prompts']['B_PLUS_V16'])[1]['proposal']
        self.assertEqual(proposal, self.collection)
        result = restore_evidence(self.answer, self.case['segments'], list(pair['law_source_map'].values()))
        self.assertEqual(result[0]['law_sources'][0]['text'], 'Original "waiver"\ntext and opposing view.')
        self.assertFalse(result[0]['semantic_correctness_certified'])

    def test_duplicate_excluded_or_invalid_ids_fail(self):
        with self.assertRaises(ValueError): source_map([{'id': 'L1', 'text': 'a'}, {'id': 'L1', 'text': 'b'}])
        self.case['excluded_segment_ids'] = ['C1']
        with self.assertRaises(ValueError): self.pair()
        self.case['excluded_segment_ids'] = ['C2']
        self.collection['bundles'][0]['rule_cards'][0]['evidence'] = ['not-real']
        with self.assertRaises(ValueError): self.pair()

    def test_unambiguous_wrappers_only_and_card_ids_rejected(self):
        pair = self.pair()
        raw = json.dumps(self.answer)
        for wrapped in [raw, raw + '\nEND', '```json\n' + raw + '\n```\nEND']:
            answer, text, check = parse_final(wrapped, pair['schema'])
            self.assertEqual(answer, self.answer)
            self.assertEqual(json.loads(text), self.answer)
            self.assertTrue(check['json_values_unchanged'])
        for bad in [raw[:-4], raw + ' More advice', '```json\n' + raw, '{"outcome":"UNDETERMINED"}']:
            with self.assertRaises(ValueError): parse_final(bad, pair['schema'])
        self.answer['grounds'][0]['law_refs'] = ['R1']
        with self.assertRaises(ValueError): parse_final(json.dumps(self.answer), pair['schema'])


if __name__ == '__main__':
    unittest.main()
