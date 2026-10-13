"""Replay audit controls; source judgments are not mocked as accuracy evidence."""
import copy
import unittest
from scripts.proof_final_statement_completion_v20_9_2 import extend_order


class CompletionReplayTests(unittest.TestCase):
    def setUp(self):
        self.old = {'records': [{'id': 'S01', 'section': 'SUMMARY', 'text': 'Original.'}]}
        self.new = {'records': self.old['records'] + [{'id': 'S02', 'section': 'LIMITATION', 'text': 'Reserved.'}]}
        self.plan = {'record_order': ['S01']}

    def test_only_additions_follow_original_model_order(self):
        result = extend_order(self.old, self.new, self.plan)
        self.assertEqual(result, {'record_order': ['S01', 'S02']})
        self.assertEqual(self.plan, {'record_order': ['S01']})

    def test_changed_old_fact_or_nonlimitation_addition_cannot_replay(self):
        changed = copy.deepcopy(self.new); changed['records'][0]['text'] = 'Changed.'
        with self.assertRaisesRegex(ValueError, 'OLD_STATEMENTS_CHANGED'):
            extend_order(self.old, changed, self.plan)
        changed = copy.deepcopy(self.new); changed['records'][1]['section'] = 'GROUND'
        with self.assertRaisesRegex(ValueError, 'ADDITIONS_MUST'):
            extend_order(self.old, changed, self.plan)

    def test_missing_order_or_new_id_collision_cannot_replay(self):
        with self.assertRaisesRegex(ValueError, 'OLD_PLAN'):
            extend_order(self.old, self.new, {'record_order': []})
        changed = copy.deepcopy(self.new); changed['records'][1]['id'] = 'S01'
        with self.assertRaisesRegex(ValueError, 'ID_COLLISION'):
            extend_order(self.old, changed, self.plan)


if __name__ == '__main__': unittest.main()
