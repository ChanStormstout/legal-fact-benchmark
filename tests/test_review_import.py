import unittest
from legal_bench.core import digest
from legal_bench.review_import import check_reply


class ReviewImportTests(unittest.TestCase):
    def setUp(self):
        self.ann = {'A': {'assertions': []}, 'B': {'assertions': []}}
        self.source = {'case_id': 'c', 'text_sha256': 'source-v1',
                       'segments': [{'id': 's1', 'text': 'Rent was fixed at 25.'}]}
        self.source['text_sha256'] = digest(self.source['segments'])
        ev = [{'segment_id': 's1', 'quote': 'Rent was fixed at 25.'}]
        self.task = {'case_id': 'c', 'source_hash': self.source['text_sha256'],
                     'annotation_hashes': {k: digest(v) for k, v in self.ann.items()},
                     'selected': {'A': [], 'B': []}}
        self.reply = {'case_id': 'c', 'unit_resolution': {'unit_id': 'current_appeal', 'evidence': ev},
                      'decisions': {'A': [], 'B': []},
                      'query_reference': [{'id': 'Q%d' % i, 'status': 'UNKNOWN', 'evidence': ev}
                                          for i in range(1, 11)]}

    def check(self):
        return check_reply(self.reply, self.task, self.ann, self.source)

    def test_valid_evidence_does_not_claim_semantic_accuracy(self):
        result = self.check()
        self.assertTrue(result['valid'])
        self.assertEqual(result['semantic_correctness'], 'MODEL_REVIEW_NOT_ESTABLISHED_BY_VALIDATOR')

    def test_quote_changed_from_rate_to_payment_rejected(self):
        self.reply['query_reference'][0]['evidence'][0]['quote'] = 'Rent was paid at 25.'
        self.assertFalse(self.check()['valid'])

    def test_stale_source_rejected(self):
        self.source['text_sha256'] = 'source-v2'
        self.assertFalse(self.check()['valid'])

    def test_changed_source_with_old_claimed_hash_rejected(self):
        self.source['segments'][0]['text'] += ' Unreviewed added text.'
        self.assertFalse(self.check()['valid'])

    def test_duplicate_query_rejected(self):
        self.reply['query_reference'][1]['id'] = 'Q1'
        self.assertFalse(self.check()['valid'])

    def test_missing_selected_assertion_rejected(self):
        self.task['selected']['A'] = ['a1']
        self.assertFalse(self.check()['valid'])

    def test_changed_annotation_rejected(self):
        self.ann['A']['assertions'].append({'id': 'new'})
        self.assertFalse(self.check()['valid'])
