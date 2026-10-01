import copy
import unittest
from legal_bench.core import digest
from legal_bench.scoped_engine import projection_view, execute
from legal_bench.reconcile import alignment


class ScopedEngineTests(unittest.TestCase):
    def setUp(self):
        def assertion(aid, typ, obj, time=None, unresolved=None):
            return {'id': aid, 'kind': 'FACT', 'predicate': typ, 'polarity': 'POSITIVE',
                    'roles': {'property': obj}, 'attributes': {'amount': 60},
                    'scope': {'portion': 'specified premises only', 'period': 'historical'},
                    'time': {'date': time} if time else None,
                    'origin': {'stage_id': 'historical_trial'}, 'deciding_court_treatment': {'value': 'ADOPTED', 'evidence': []},
                    'unresolved': unresolved or [], 'evidence': [{'segment_id': 's1', 'quote': 'Synthetic evidence'}]}
        self.a = {'case_id': 'synthetic', 'assertions': [
            assertion('a1', 'NOTICE', 'd1', '1964-09-15'),
            assertion('a2', 'PAY', 'd2', unresolved=[{'field': 'time', 'reason': 'date absent'}]),
            assertion('a3', 'PAY', None, unresolved=[{'field': 'roles.property', 'reason': 'debt unknown'}])],
            'relations': []}
        self.r = {'annotation_hash': digest(self.a), 'mode': 'SCOPED_EXISTENTIAL', 'unit_id': 'u',
                  'provenance': {'origin': 'synthetic test'}, 'decisions': []}
        self.refresh()
    def refresh(self):
        self.r['annotation_hash'] = digest(self.a)
        self.r['decisions'] = [{'assertion_id': a['id'], 'assertion_hash': digest(a), 'decision': 'ACCEPT',
                               'approved_fields': ['id', 'type', 'status', 'polarity', 'roles.property', 'attributes.amount', 'time'],
                               'basis': 'Synthetic projected identity remains within original scope', 'evidence': a['evidence']}
                              for a in self.a['assertions']]
    def query(self, constraints=None, specified=False):
        atoms = [{'var': 'n', 'type': 'NOTICE'}, {'var': 'p', 'type': 'PAY'}]
        if specified: atoms[0]['event_id'] = 'a1'; atoms[1]['event_id'] = 'a2'
        return {'mode': 'SCOPED_EXISTENTIAL', 'atoms': atoms,
                'constraints': constraints or [{'op': 'same', 'left': 'n.roles.property', 'right': 'p.roles.property'}]}
    def run_query(self, q): return execute(projection_view(self.a, self.r), q)
    def test_pair_mismatch_does_not_make_case_negative(self):
        self.assertEqual(self.run_query(self.query(specified=True))['status'], 'MISMATCH')
        result = self.run_query(self.query())
        self.assertEqual(result['status'], 'UNKNOWN')
        self.assertEqual(result['uncertain_bindings'][0]['uncertainty'][0]['field'], 'roles.property')
    def test_known_role_survives_unknown_date_and_retains_scope(self):
        q = self.query([{'op': 'different', 'left': 'n.roles.property', 'right': 'p.roles.property'}], True)
        result = self.run_query(q)
        self.assertEqual(result['status'], 'MATCH')
        self.assertEqual(result['witnesses'][0]['scopes']['p']['period'], 'historical')
    def test_unknown_date_blocks_date_use(self):
        q = self.query([{'op': 'before', 'left': 'n.time', 'right': 'p.time'}], True)
        self.assertEqual(self.run_query(q)['status'], 'UNKNOWN')
    def test_alternative_witness_can_satisfy_case(self):
        self.a['assertions'][2]['roles']['property'] = 'd1'
        self.a['assertions'][2]['unresolved'] = []
        self.refresh()
        r = self.run_query(self.query())
        self.assertEqual(r['status'], 'MATCH')
        self.assertEqual(r['witnesses'][0]['binding']['p'], 'a3')
    def test_unreviewed_field_is_not_executable(self):
        self.r['decisions'][1]['approved_fields'].remove('roles.property')
        self.assertEqual(self.run_query(self.query(specified=True))['status'], 'UNKNOWN')
    def test_uncertain_review_retains_potential_witness(self):
        self.r['decisions'][1].update(decision='UNCERTAIN', approved_fields=[], basis='Court adoption unclear')
        q = {'mode': 'SCOPED_EXISTENTIAL', 'atoms': [{'var': 'p', 'type': 'PAY', 'event_id': 'a2'}]}
        r = self.run_query(q)
        self.assertEqual(r['status'], 'UNKNOWN')
        self.assertTrue(r['uncertain_bindings'])
    def test_unrecognized_uncertainty_blocks_proposition(self):
        self.a['assertions'][1]['unresolved'] = [{'field': 'amount_allocation', 'reason': 'unparsed restriction'}]
        self.refresh()
        q = self.query([{'op': 'different', 'left': 'n.roles.property', 'right': 'p.roles.property'}], True)
        self.assertEqual(self.run_query(q)['status'], 'UNKNOWN')
    def test_approximate_amount_cannot_answer_exact_query(self):
        self.a['assertions'][1]['unresolved'] = [{'field': 'attributes.amount', 'reason': 'approximate only'}]
        self.refresh()
        q = {'mode': 'SCOPED_EXISTENTIAL', 'atoms': [{'var': 'p', 'type': 'PAY', 'event_id': 'a2'}],
             'constraints': [{'op': 'equals', 'left': 'p.attributes.amount', 'value': 60}]}
        self.assertEqual(self.run_query(q)['status'], 'UNKNOWN')
    def test_rejected_allegation_cannot_enter_adopted_view(self):
        self.a['assertions'][1]['deciding_court_treatment']['value'] = 'NOT_ESTABLISHED'
        self.refresh()
        with self.assertRaises(ValueError): projection_view(self.a, self.r)
    def test_version_binding_and_no_mutation(self):
        original = copy.deepcopy(self.a)
        self.run_query(self.query())
        self.assertEqual(self.a, original)
        self.a['assertions'][0]['roles']['property'] = 'other'
        with self.assertRaises(ValueError): projection_view(self.a, self.r)
    def test_empty_result_never_proves_absence(self):
        q = {'mode': 'SCOPED_EXISTENTIAL', 'atoms': [{'var': 'x', 'type': 'MISSING'}]}
        r = self.run_query(q)
        self.assertEqual(r['status'], 'NOT_FOUND'); self.assertFalse(r['closed_world'])
    def test_unsupported_language_and_current_snapshot(self):
        q = self.query(); q['mode'] = 'CURRENT_TRUTH'
        self.assertEqual(self.run_query(q)['status'], 'UNSUPPORTED')
        self.assertEqual(self.run_query({'mode': 'SCOPED_EXISTENTIAL', 'atoms': [None]})['status'], 'UNSUPPORTED')
        self.assertEqual(self.run_query([])['status'], 'UNSUPPORTED')
        q = self.query([{'op': 'sum', 'left': 'p.attributes.amount', 'value': 100}])
        self.assertEqual(self.run_query(q)['status'], 'UNSUPPORTED')
    def test_alignment_overlap_does_not_promote_equivalence(self):
        a = dict(self.a, predicate_definitions=[{'id': p} for p in ['NOTICE', 'PAY']])
        r = alignment(a, a)
        self.assertTrue(r['candidates'])
        self.assertTrue(all(c['state'] == 'SEMANTIC_REVIEW_PENDING' for c in r['candidates']))


if __name__ == '__main__': unittest.main()
