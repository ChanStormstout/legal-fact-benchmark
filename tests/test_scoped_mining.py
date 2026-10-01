import copy
import unittest
from legal_bench.scoped_mining import mine, seed_annotation


class ScopedMiningTests(unittest.TestCase):
    def view(self, case_id, shared=True):
        events = []
        for aid, typ, obj in [('n', 'NOTICE', 'd1'), ('p', 'PAY', 'd1' if shared else 'd2')]:
            events.append({'id': aid, 'type': typ, 'status': 'COURT_FOUND', 'polarity': 'POSITIVE',
                           'roles': {'debt': obj}, 'attributes': {}, 'time': None,
                           'scope': {'period': 'historical only'}, 'origin': {},
                           'evidence': [{'segment_id': 's', 'quote': 'Synthetic fixture'}],
                           'review_evidence': [], 'unresolved': [{'field': 'time', 'reason': 'date missing'}],
                           'approved_fields': ['id', 'type', 'status', 'polarity', 'roles.debt']})
        return {'case_id': case_id, 'unit_id': 'u', 'material_scope': 'SYNTHETIC_TEST_ONLY',
                'input_hash': 'x', 'review_hash': 'y', 'conflicts': [], 'events': events}

    def test_shared_object_separates_relation_from_cooccurrence(self):
        r = mine([self.view('c1'), self.view('c2', False)])
        self.assertEqual(r['generated'], 1)
        p = r['patterns'][0]
        self.assertEqual(p['support'], 1)
        self.assertEqual(p['cooccurrence_support'], 2)
        self.assertFalse(p['repeated'])
        self.assertEqual(p['results'][0]['relation']['witnesses'][0]['scopes']['e0']['period'], 'historical only')

    def test_duplicate_ab_case_cannot_inflate_support(self):
        with self.assertRaises(ValueError): mine([self.view('c1'), self.view('c1')])

    def test_unknown_time_does_not_seed_temporal_candidate(self):
        r = mine([self.view('c1'), self.view('c2')])
        self.assertTrue(r['patterns'][0]['repeated'])
        self.assertFalse(any(c['op'] == 'before' for p in r['patterns'] for c in p['query']['constraints']))

    def test_unknown_join_field_not_treated_as_different(self):
        v = self.view('c2')
        v['events'][1]['unresolved'].append({'field': 'roles.debt', 'reason': 'allocation unclear'})
        r = mine([self.view('c1'), v])
        self.assertEqual(r['patterns'][0]['unknown'], 1)
        self.assertEqual(r['patterns'][0]['support'], 1)

    def test_candidate_order_budget_and_frontier_reproducible(self):
        v = self.view('c1')
        v['events'][1]['attributes'] = {'amount': 25}
        v['events'][1]['approved_fields'].append('attributes.amount')
        r = mine([v], budget=1)
        self.assertFalse(r['search_complete'])
        self.assertEqual(r['executed'], 1)
        self.assertEqual(len(r['frontier']), 1)
        self.assertEqual(r, mine([copy.deepcopy(v)], budget=1))

    def test_unreviewed_amount_cannot_seed_condition(self):
        v = self.view('c1')
        v['events'][1]['attributes']['amount'] = 25
        r = mine([v])
        self.assertEqual(r['generated'], 1)
