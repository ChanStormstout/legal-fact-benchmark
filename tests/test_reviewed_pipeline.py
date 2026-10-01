import copy
import json
import unittest
from legal_bench.core import digest
from legal_bench.reviewed_pipeline import normalize_view, oracle_view, registry, CARDS
from legal_bench.scoped_engine import execute, field_value
from legal_bench.scoped_mining import seed_annotation, mine
from legal_bench.conditional_engine import generate_from_seeds
from legal_bench import exhaustive_oracle as oracle


class ReviewedIntegrationTests(unittest.TestCase):
    def fixture(self, cid='c'):
        assertions = []
        for aid, predicate in [('a1', 'LEASE'), ('a2', 'PAY')]:
            assertions.append({'id': aid, 'kind': 'FACT', 'predicate': predicate, 'polarity': 'POSITIVE',
                'roles': {'person': 'p1', 'property': 'd1'}, 'attributes': {'amount': 1},
                'scope': {'period': 'Historical record'}, 'time': {'date': '2000-01-01' if aid == 'a1' else '2000-02-01'},
                'origin': {}, 'evidence': [{'segment_id': 's1', 'quote': 'Synthetic source'}],
                'deciding_court_treatment': {'value': 'ADOPTED', 'evidence': []}, 'unresolved': []})
        raw = {'case_id': cid, 'assertions': assertions, 'relations': [],
               'predicate_definitions': [{'id': p, 'meaning': p, 'roles': {'person': 'Individual actor', 'property': 'Object'}} for p in ['LEASE', 'PAY']]}
        review = {'annotation_hash': digest(raw), 'mode': 'SCOPED_EXISTENTIAL', 'unit_id': 'u',
                  'provenance': {'origin': 'SYNTHETIC'}, 'decisions': [
                  {'assertion_id': a['id'], 'assertion_hash': digest(a), 'decision': 'ACCEPT', 'basis': 'Synthetic approval',
                   'evidence': a['evidence'], 'approved_fields': ['id', 'type', 'status', 'polarity', 'roles.person', 'roles.property']}
                  for a in assertions]}
        rules = {'LEASE': {'type': 'LEASE_RECORD', 'roles': {'tenant': 'person', 'property': 'property'}},
                 'PAY': {'type': 'RENT_PAYMENT_RECORD', 'roles': {'payer': 'person', 'property': 'property'}}}
        return raw, review, registry(raw, rules, 'A')

    def query(self):
        return {'mode': 'SCOPED_EXISTENTIAL', 'atoms': [{'var': 'l', 'type': 'LEASE_RECORD'}, {'var': 'p', 'type': 'RENT_PAYMENT_RECORD'}],
                'constraints': [{'op': 'different', 'left': 'l.id', 'right': 'p.id'},
                                {'op': 'same', 'left': 'l.roles.tenant', 'right': 'p.roles.payer'},
                                {'op': 'same', 'left': 'l.roles.property', 'right': 'p.roles.property'}]}

    def test_renames_keep_permissions_source_and_hashes(self):
        raw, review, cards = self.fixture()
        hashes = [digest(x) for x in [raw, review, cards]]
        v = normalize_view(raw, review, cards)
        self.assertEqual(execute(v, self.query())['status'], 'MATCH')
        self.assertEqual([digest(x) for x in [raw, review, cards]], hashes)
        self.assertEqual(v['events'][1]['source_assertion'], raw['assertions'][1])
        self.assertIn('roles.payer', v['events'][1]['approved_fields'])
        self.assertEqual(v['review_hash'], digest(review))

    def test_withheld_object_cannot_be_reapproved_by_rename_or_search(self):
        raw, review, cards = self.fixture()
        review['decisions'][1]['approved_fields'].remove('roles.person')
        v = normalize_view(raw, review, cards)
        self.assertEqual(execute(v, self.query())['status'], 'UNKNOWN')
        self.assertEqual(v['events'][1]['roles']['payer'], 'p1')  # Saved, not executable.
        self.assertNotIn('roles.payer', v['events'][1]['approved_fields'])
        self.assertNotIn('payer', seed_annotation(v)['events'][1]['roles'])
        result = mine([v])
        self.assertFalse(any('payer' in json.dumps(p['query']) for p in result['patterns']))

    def test_known_date_not_executable_without_source_approval(self):
        raw, review, cards = self.fixture()
        v = normalize_view(raw, review, cards)
        q = self.query()
        q['constraints'].append({'op': 'before', 'left': 'l.time', 'right': 'p.time'})
        self.assertEqual(execute(v, q)['status'], 'UNKNOWN')
        self.assertIsNone(seed_annotation(v)['events'][1]['time'])
        self.assertFalse(any(c['op'] == 'before' for p in mine([v])['patterns'] for c in p['query']['constraints']))

    def test_unresolved_source_role_renames_its_blocker(self):
        raw, review, cards = self.fixture()
        raw['assertions'][1]['unresolved'] = [{'field': 'roles.person', 'reason': 'Identity unresolved'}]
        review['annotation_hash'] = cards['annotation_hash'] = digest(raw)
        review['decisions'][1]['assertion_hash'] = digest(raw['assertions'][1])
        v = normalize_view(raw, review, cards)
        self.assertEqual(v['events'][1]['unresolved'][0]['field'], 'roles.payer')
        self.assertEqual(execute(v, self.query())['status'], 'UNKNOWN')

    def test_uncertain_and_excluded_never_seed_or_promote(self):
        raw, review, cards = self.fixture()
        review['decisions'][1].update(decision='UNCERTAIN', approved_fields=[])
        v = normalize_view(raw, review, cards)
        self.assertEqual(execute(v, self.query())['status'], 'UNKNOWN')
        self.assertEqual(mine([v])['generated'], 0)
        review['decisions'][1]['decision'] = 'EXCLUDE'
        v = normalize_view(raw, review, cards)
        self.assertEqual(execute(v, self.query())['status'], 'NOT_FOUND')
        self.assertFalse(execute(v, self.query())['closed_world'])

    def test_double_join_generation_and_independent_oracle(self):
        views = [normalize_view(*self.fixture(cid)) for cid in ['c1', 'c2']]
        candidates = generate_from_seeds([seed_annotation(v) for v in views])
        translated = [oracle_view(v) for v in views]
        checked = oracle.check(translated, candidates)
        self.assertTrue(checked['exact'])
        q = self.query()
        q.pop('mode')
        self.assertIn(oracle.normalized(q), candidates)
        for serialized in candidates:
            for v, independent in zip(views, translated):
                q = json.loads(serialized)
                actual = execute(v, dict(q, mode='SCOPED_EXISTENTIAL'))
                expected = oracle.answer(independent, q)
                self.assertEqual(actual['status'], expected['status'])
        self.assertTrue(all(p['support'] == 2 for p in mine(views)['patterns']))

    def test_incorrect_case_registry_and_role_are_rejected(self):
        raw, review, cards = self.fixture()
        cards['annotation_hash'] = 'stale'
        with self.assertRaises(ValueError):
            normalize_view(raw, review, cards)
        cards['annotation_hash'] = digest(raw)
        cards['rules']['PAY']['roles']['payer'] = 'nonexistent'
        with self.assertRaises(ValueError):
            normalize_view(raw, review, cards)

    def test_boolean_amount_and_invalid_time_field_not_accepted(self):
        raw, review, cards = self.fixture()
        review['decisions'][1]['approved_fields'].append('attributes.amount')
        v = normalize_view(raw, review, cards)
        q = self.query()
        q['constraints'].append({'op': 'equals', 'left': 'p.attributes.amount', 'value': True})
        self.assertEqual(execute(v, q)['status'], 'NOT_FOUND')
        q['constraints'][-1] = {'op': 'before', 'left': 'l.roles.property', 'right': 'p.roles.property'}
        self.assertEqual(execute(v, q)['status'], 'UNSUPPORTED')

    def test_native_does_not_claim_semantic_equivalence(self):
        raw, review, cards = self.fixture()
        v = normalize_view(raw, review, cards, 'NATIVE')
        self.assertTrue(v['events'][0]['type'].startswith('NATIVE::'))
        self.assertIn('Syntactic', v['events'][0]['abstraction']['card'][2])


if __name__ == '__main__':
    unittest.main()
