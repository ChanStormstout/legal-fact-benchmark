import unittest
from legal_bench.rules_verdict_v1.scope_rerank_diagnostic_v1 import scope_match,rerank
class ScopeRerankTests(unittest.TestCase):
 def test_normalized_name_and_boundary(self):
  self.assertTrue(scope_match('Example Rent Act section 3',['Example Rent Act, 1958']))
  self.assertFalse(scope_match('Example Rent Action section 3',['Example Rent Act, 1958']))
 def test_citation_and_negation_not_prefix(self):
  self.assertFalse(scope_match('Not Example Rent Act; different law',['Example Rent Act']))
  self.assertFalse(scope_match('Other law; cites Example Rent Act',['Example Rent Act']))
 def test_only_permutation_and_stable_ties(self):
  units=[{'id':'x','scope':'Other Act'}, {'id':'y','scope':'Example Act section 7'}, {'id':'z','scope':'Example Act section 2'}]
  ranked=rerank([{'id':'x'},{'id':'z'},{'id':'y'}],units,['Example Act'])
  self.assertEqual([x['id'] for x in ranked],['z','y','x'])
  self.assertEqual(set(x['id'] for x in ranked),{'x','y','z'})
 def test_unknown_scope_stays_not_excluded(self):
  self.assertEqual(rerank([{'id':'x'}],[{'id':'x'}],['Example Act'])[0]['id'],'x')
if __name__=='__main__': unittest.main()
