import copy
import unittest
from legal_bench.core import make_source, validate
from legal_bench.engine import execute, mine, canonical_query, cooccurrence_query


def event(eid, typ, obj, time=None, status='COURT_FOUND'):
    return {'id': eid, 'unit_id': 'u1', 'type': typ, 'roles': {'property': obj},
            'time': time, 'status': status, 'polarity': 'POSITIVE', 'speaker': 'court',
            'attributes': {}, 'unresolved': [], 'evidence': [{'paragraph_id': 'p0001', 'quote': 'A fact.'}]}


def ann(events, case='c1'):
    return {'case_id': case, 'units': [{'id': 'u1', 'primary': True}],
            'entities': [{'id': 'o1', 'label': 'A'}, {'id': 'o2', 'label': 'B'}], 'events': events,
            'coverage': [{'paragraph_id': 'p0001', 'category': 'fact'}], 'unresolved': []}


def query():
    return {'atoms': [{'var': 'n', 'type': 'NOTICE'}, {'var': 'p', 'type': 'PAYMENT'}],
            'constraints': [{'op': 'same', 'left': 'n.roles.property', 'right': 'p.roles.property'}]}


class EngineTests(unittest.TestCase):
    def test_shared_identity(self):
        a = ann([event('e1', 'NOTICE', 'o1'), event('e2', 'PAYMENT', 'o1')])
        self.assertEqual(execute(a, query())['status'], 'MATCH')
        a['events'][1]['roles']['property'] = 'o2'
        self.assertEqual(execute(a, query())['status'], 'NOT_FOUND')
        self.assertEqual(execute(a, cooccurrence_query(query()))['status'], 'MATCH')

    def test_pair_vs_case_unknown(self):
        a = ann([event('e1', 'NOTICE', 'o1'), event('e2', 'PAYMENT', 'o2'), event('e3', 'PAYMENT', None)])
        q = query(); q['atoms'][0]['event_id'] = 'e1'; q['atoms'][1]['event_id'] = 'e2'
        self.assertEqual(execute(a, q)['status'], 'MISMATCH')
        self.assertEqual(execute(a, query())['status'], 'UNKNOWN')

    def test_missing_not_false(self):
        self.assertEqual(execute(ann([]), query())['status'], 'NOT_FOUND')

    def test_status_negation(self):
        for status in ['ALLEGED', 'REJECTED', 'DISPUTED']:
            a = ann([event('e1', 'NOTICE', 'o1'), event('e2', 'PAYMENT', 'o1', status=status)])
            self.assertNotEqual(execute(a, query())['status'], 'MATCH')
        a['events'][1]['status'] = 'COURT_FOUND'; a['events'][1]['polarity'] = 'NEGATIVE'
        self.assertNotEqual(execute(a, query())['status'], 'MATCH')

    def test_unknown_date(self):
        a = ann([event('e1', 'NOTICE', 'o1', '2020-01-01'), event('e2', 'PAYMENT', 'o1')])
        q = query(); q['constraints'].append({'op': 'before', 'left': 'n.time', 'right': 'p.time'})
        self.assertEqual(execute(a, q)['status'], 'UNKNOWN')

    def test_local_unknown_does_not_block_other_witness(self):
        a = ann([event('e1', 'NOTICE', 'o1'), event('e2', 'PAYMENT', 'o1'), event('e3', 'PAYMENT', 'o1')])
        a['events'][1]['unresolved'] = ['qualifier scope uncertain']
        r = execute(a, query())
        self.assertEqual(r['status'], 'MATCH'); self.assertEqual(len(r['witnesses']), 1)

    def test_conflict_preserved(self):
        a = ann([event('e1', 'NOTICE', 'o1'), event('e2', 'PAYMENT', 'o1'), event('e3', 'PAYMENT', 'o1', status='DISPUTED')])
        r = execute(a, query()); self.assertEqual(r['status'], 'MATCH'); self.assertTrue(r['conflicts'])

    def test_unsupported_aggregation(self):
        for op in ['sum', 'allocation', 'reversal', 'python']:
            q = query(); q['constraints'].append({'op': op})
            self.assertEqual(execute(ann([]), q)['status'], 'UNSUPPORTED')

    def test_support_counts_units(self):
        a = ann([event('e1', 'NOTICE', 'o1'), event('e2', 'PAYMENT', 'o1'), event('e3', 'PAYMENT', 'o1')])
        b = copy.deepcopy(a); b['case_id'] = 'c2'
        result = mine([a, b])
        self.assertTrue(result['patterns'])
        self.assertTrue(all(x['support'] <= 2 for x in result['patterns']))
        self.assertEqual(result, mine([b, a]))

    def test_budget_records_frontier(self):
        a = ann([event('e1', 'NOTICE', 'o1', '2020-01-01'), event('e2', 'PAYMENT', 'o1', '2020-02-01')])
        r = mine([a], 1); self.assertFalse(r['search_complete']); self.assertTrue(r['frontier'])

    def test_canonical_variable_names(self):
        q = query(); z = {'atoms': [{'var': 'y', 'type': 'PAYMENT'}, {'var': 'x', 'type': 'NOTICE'}],
            'constraints': [{'op': 'same', 'left': 'y.roles.property', 'right': 'x.roles.property'}]}
        self.assertEqual(canonical_query(q), canonical_query(z))

    def test_quote_validation(self):
        source = make_source('c1', 'A fact.', 'https://example.org', 'hash')
        a = ann([event('e1', 'NOTICE', 'o1')]); self.assertTrue(validate(a, source)['valid'])
        a['events'][0]['evidence'][0]['quote'] = 'Invented fact'
        self.assertFalse(validate(a, source)['valid'])

    def test_unknown_ids_and_coverage(self):
        source = make_source('c1', 'A fact.\n\nSecond paragraph.', 'https://example.org', 'hash')
        a = ann([event('e1', 'NOTICE', 'unresolved-id')])
        codes = {x['code'] for x in validate(a, source)['errors']}
        self.assertIn('dangling_entity', codes); self.assertIn('unreviewed_paragraphs', codes)


if __name__ == '__main__':
    unittest.main()
