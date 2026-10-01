import copy
import unittest
from legal_bench.core import digest
from legal_bench.conditional_engine import execute, field_value
from legal_bench.type_projection import apply_type_projections, REVIEW_KIND, SCOPE


class TypeProjectionTests(unittest.TestCase):
    def fixture(self):
        source = {'case_id': 'control', 'segments': [{'id': 's1', 'text': 'Tenant allegedly did not pay rent during an unclear interval.'}]}
        event = {'id': 'a1', 'unit_id': 'u1', 'type': 'PAY_RENT',
                 'status': 'ALLEGED', 'polarity': 'NEGATIVE', 'time': None,
                 'roles': {}, 'attributes': {}, 'scope': {'period': 'unclear'},
                 'origin': {}, 'evidence': [], 'source_assertion': {},
                 'field_contract': {'type_unresolved': True, 'blocked': [
                     {'affected_fields': ['*'], 'reason': 'Unparsed interval'}]}}
        view = {'case_id': 'control', 'units': [{'id': 'u1'}], 'events': [event]}
        review = {'case_id': 'control', 'event_id': 'a1', 'view_hash': digest(view),
                  'source_hash': digest(source), 'review_kind': REVIEW_KIND,
                  'scope': SCOPE, 'field': 'type', 'value': 'PAY_RENT',
                  'source_support': True, 'rationale': 'Signed allegation is about rent payment, not an affirmative payment event.',
                  'evidence': [{'segment_id': 's1', 'quote': 'did not pay rent'}]}
        return view, source, review

    def test_unrelated_candidate_removed_only_after_explicit_review(self):
        view, source, review = self.fixture()
        q = {'atoms': [{'var': 'x', 'type': 'SUBLET_PROPERTY'}], 'constraints': []}
        self.assertEqual(execute(view, q)['status'], 'UNKNOWN')
        revised = apply_type_projections(view, source, [review])
        self.assertEqual(execute(revised, q)['status'], 'NOT_FOUND')
        q['atoms'][0]['type'] = 'PAY_RENT'
        # Type support cannot establish positive occurrence or court adoption.
        self.assertEqual(execute(revised, q)['status'], 'UNKNOWN')

    def test_other_blocks_and_original_view_are_unchanged(self):
        view, source, review = self.fixture()
        before = copy.deepcopy(view)
        revised = apply_type_projections(view, source, [review])
        e = revised['events'][0]
        self.assertEqual(view, before)
        self.assertEqual(field_value(e, 'type'), ('PAY_RENT', []))
        for field in ['time', 'polarity', 'status', 'roles.payer']:
            self.assertIsNone(field_value(e, field)[0])
        self.assertEqual(e['field_contract']['blocked'], before['events'][0]['field_contract']['blocked'])

    def test_quote_location_or_label_alone_does_not_grant_support(self):
        view, source, review = self.fixture()
        review['source_support'] = False
        with self.assertRaises(ValueError): apply_type_projections(view, source, [review])
        self.assertTrue(view['events'][0]['field_contract']['type_unresolved'])

    def test_explicit_predicate_doubt_is_retained(self):
        view, source, review = self.fixture()
        view['events'][0]['field_contract']['blocked'].append({'affected_fields': ['type'], 'reason': 'Sublease versus possession transfer unresolved'})
        review['view_hash'] = digest(view)
        with self.assertRaises(ValueError): apply_type_projections(view, source, [review])
        # Even a forged field contract cannot bypass the explicit type block.
        view['events'][0]['field_contract']['source_reviewed_type_projection'] = review
        self.assertIsNone(field_value(view['events'][0], 'type')[0])

    def test_stale_or_unlocated_source_review_is_rejected(self):
        view, source, review = self.fixture()
        bad = copy.deepcopy(review); bad['view_hash'] = 'stale'
        with self.assertRaises(ValueError): apply_type_projections(view, source, [bad])
        bad = copy.deepcopy(review); bad['evidence'][0]['quote'] = 'invented'
        with self.assertRaises(ValueError): apply_type_projections(view, source, [bad])

    def test_known_type_with_only_time_uncertainty_remains_usable(self):
        view, source, review = self.fixture()
        e = view['events'][0]; e['field_contract']['blocked'] = [{'affected_fields': ['time'], 'reason': 'Missing date'}]
        e['field_contract']['type_unresolved'] = False
        q = {'atoms': [{'var': 'x', 'type': 'PAY_RENT', 'status': 'ALLEGED', 'polarity': 'NEGATIVE'}], 'constraints': []}
        self.assertEqual(execute(view, q)['status'], 'MATCH')
        self.assertIsNone(field_value(e, 'time')[0])


if __name__ == '__main__':
    unittest.main()
