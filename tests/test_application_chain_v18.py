import copy
import json
import unittest

from legal_bench.rules_verdict_v1.application_chain_v18 import (
    APPLICATION_REQUIREMENTS, audit_prompt, audit_view, refine_prompt)
from legal_bench.rules_verdict_v1.final_v9 import final_schema
from legal_bench.rules_verdict_v1.source_views import build_view


class ApplicationChainTests(unittest.TestCase):
    def setUp(self):
        self.full = {'case_id': 'SYNTHETIC', 'segments': [
            {'id': 'C1', 'text': 'Custody was claimed. Its proof was not decided.'},
            {'id': 'C2', 'text': 'Withheld fictional conclusion.'}]}
        self.view = build_view(self.full, [{'segment_id': 'C1', 'end': 20}], 'SYNTHETIC')
        self.law = {'cards': [{'source_case': 'OTHER'}], 'law_segments': [
            {'id': 'L1', 'source_case': 'OTHER', 'text': 'Fictional custody rule; an exception is unresolved.'}]}
        self.schema = final_schema([s['id'] for s in self.view['segments']], ['L1'])
        self.prompt = ('Examples\nTARGET SHARED LAW PACKAGE\n'+json.dumps(self.law)+
            '\nTARGET INTERMEDIATE MATERIAL (UNVERIFIED)\n{}\nTARGET COMPLETE ALLOWED CASE SOURCE\n'+
            '\n'.join('['+s['id']+'] '+s['text'] for s in self.view['segments'])+
            '\nFINAL TASK REMINDER\nReturn a complete answer.')

    def test_exact_source_slices_and_ambiguous_changes_rejected(self):
        out = audit_view(self.view, self.full)
        self.assertTrue(out['selected_slices'][0]['partial_parent'])
        self.assertFalse(out['semantic_correctness_certified'])
        changed = copy.deepcopy(self.view); changed['segments'][0]['text'] += ' invented'
        with self.assertRaises(ValueError): audit_view(changed, self.full)

    def test_only_additive_generic_requirements_and_no_double_insertion(self):
        refined = refine_prompt(self.prompt)
        self.assertEqual(refined[:-len(APPLICATION_REQUIREMENTS)], self.prompt)
        self.assertNotIn('1134266', APPLICATION_REQUIREMENTS)
        self.assertNotIn('661475', APPLICATION_REQUIREMENTS)
        with self.assertRaises(ValueError): refine_prompt(refined)

    def test_material_contract_no_own_cards_or_prior_answer(self):
        checks = audit_prompt(self.prompt, self.schema, self.view, self.law, [])
        self.assertFalse(checks['program_executes_legal_rules'])
        bad = copy.deepcopy(self.law); bad['cards'][0]['source_case'] = self.view['case_id']
        with self.assertRaises(ValueError): audit_prompt(self.prompt, self.schema, self.view, bad, [])
        with self.assertRaises(ValueError): audit_prompt(self.prompt.replace('\n{}\n', '\n{"old_answer":"YES"}\n'), self.schema, self.view, self.law, [])


if __name__ == '__main__':
    unittest.main()
