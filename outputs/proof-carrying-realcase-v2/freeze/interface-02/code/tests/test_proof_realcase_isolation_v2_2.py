import unittest
from legal_bench.proof_carrying.realcase_tasks_v2_2 import prompt
from legal_bench.proof_carrying.realcase_tasks import prompt as old_prompt
class IsolationTest(unittest.TestCase):
    def test_no_candidate_rules_or_facts_enter_reference(self):
        for attachments in ({'rules':{}},{'facts':{}},{'rules':{},'facts':{}}):
            with self.assertRaisesRegex(ValueError,'ISOLATION'):
                prompt('789051','reference',{'segments':[]},attachments)
        text=prompt('789051','reference',{'segments':[]},{})
        self.assertIn('TASK ATTACHMENTS:\n{}',text)
    def test_all_submitted_nonreference_prompts_unchanged(self):
        for k,a in [('rules',{}),('rule_review',{'rules':{}}),('facts',{'rules':{}}),('derivation',{'rules':{},'facts':{}})]:
            self.assertEqual(prompt('789051',k,{'segments':[]},a),old_prompt('789051',k,{'segments':[]},a))
if __name__=='__main__':unittest.main()
