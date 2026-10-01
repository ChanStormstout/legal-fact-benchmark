import copy
import unittest
from legal_bench.grouping_review import validate_grouping_reply


class GroupingReviewTests(unittest.TestCase):
    def setUp(self):
        self.task = {'batch_id': 'g1', 'case_ids': ['1']}
        self.sources = [{'case_id': '1', 'segments': [{'id': 's1', 'text': 'A leased Shop 12 to B.'}]}]
        self.reply = {'batch_id': 'g1', 'end_marker': 'END_COMPLETE_GROUP_REVIEW g1', 'cases': [
            {'case_id': '1', 'review_state': 'IDENTIFIER_REVIEW_COMPLETE', 'primary_dispute_key': 'd1',
             'associated_disputes': [{'key': 'd1', 'evidence': [{'segment_id': 's1', 'quote': 'A leased Shop 12 to B.'}]}],
             'links': []}]}

    def test_valid_is_only_anchored_proposal(self):
        result = validate_grouping_reply(self.reply, self.task, self.sources)
        self.assertTrue(result['valid'])
        self.assertIn('not a proof', result['interpretation'])

    def test_unlocated_quote(self):
        self.reply['cases'][0]['associated_disputes'][0]['evidence'][0]['quote'] = 'Shop 99'
        self.assertFalse(validate_grouping_reply(self.reply, self.task, self.sources)['valid'])

    def test_companion_primary_must_be_registered(self):
        self.reply['cases'][0]['primary_dispute_key'] = 'unregistered-companion'
        self.assertFalse(validate_grouping_reply(self.reply, self.task, self.sources)['valid'])

    def test_coverage_not_silently_partial(self):
        self.task['case_ids'].append('2')
        self.assertFalse(validate_grouping_reply(self.reply, self.task, self.sources)['valid'])

    def test_duplicate_case_id(self):
        self.reply['cases'].append(copy.deepcopy(self.reply['cases'][0]))
        self.assertFalse(validate_grouping_reply(self.reply, self.task, self.sources)['valid'])
