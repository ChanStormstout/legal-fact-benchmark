import unittest
from legal_bench.rules_verdict_v1 import authority_use_v10 as cats,legal_material_v10 as pack,rgcn_development_v4 as graph,coarse_label_v10 as lab
class ContractTests(unittest.TestCase):
 def test_category_explicit_unknown(self):
  self.assertEqual(cats.normalize('CORE'),'CORE');self.assertEqual(cats.normalize('DIRECT'),'CORE');self.assertEqual(cats.normalize('NO_USE'),'UNKNOWN');self.assertEqual(cats.normalize('NO_USE',no_use_review='IRRELEVANT'),'IRRELEVANT')
  with self.assertRaises(ValueError):cats.normalize('NEW_CATEGORY')
 def test_material_preserves_legal_status_and_text(self):
  u={'id':'x','text':'legal text\nno omission','legal_status':'RESERVED','source':{'url':'https://example.org','document_id':'1','court':'HC','raw_provenance':[{'raw_path':'secret','raw_sha256':'hash'}]},'dependencies':[],'coverage_limit':'limited'}
  v=pack.payload(u);self.assertEqual(v['text'],u['text']);self.assertEqual(v['legal_status'],'RESERVED');self.assertEqual(v['source'],{'url':'https://example.org','document_id':'1','court':'HC'});self.assertIn('raw_provenance',u['source'])
 def test_unprocessed_not_certain_zero(self):
  self.assertEqual(graph.alignment_unknown_fraction({'scope':'UNKNOWN','state':'UNKNOWN'},[]),1)
  self.assertEqual(graph.alignment_unknown_fraction({'scope':'INCOMPATIBLE','state':'INCOMPATIBLE'},[]),0)
  self.assertEqual(graph.alignment_unknown_fraction({'scope':'DIRECT','state':'CANDIDATE'},[{'uncertain':False}]),0)
 def test_whitespace_only_does_not_reconstruct_quote(self):
  c={'case_id':'1','segments':[{'id':'L1'}]};u=[{'id':'law','text':'No  written\nconsent.'}];row={'unit_id':'law','category':'CORE','reason':'r','case_refs':['L1'],'law_quote':'No written consent.'}
  a=lab.inspect({'case_id':'1','uses':[row]},c,u);self.assertEqual(a['slots']['law']['state'],'KNOWN');self.assertEqual(a['slots']['law']['record'],row);self.assertEqual(a['locations']['law']['status'],'WHITESPACE_ONLY')
  row=dict(row,law_quote='No ... consent.');b=lab.inspect({'case_id':'1','uses':[row]},c,u);self.assertEqual(b['slots']['law']['state'],'ISOLATED')
class EvaluationTests(unittest.TestCase):
 def test_core_and_unknown_not_silently_negatives(self):
  from legal_bench.rules_verdict_v1.authority_evaluation_v10 import evaluate
  units=[{'id':'a','text':'Primary rule','source':{'document_id':'doc'},'dependencies':[]},{'id':'b','text':'Another rule','source':{'document_id':'doc'},'dependencies':[]},{'id':'c','text':'Unreviewed','source':{'document_id':'other'},'dependencies':[]}]
  ranking=[{'id':u['id']} for u in units];sel=pack.select(ranking,units,pack.PRIMARY_CONFIG)
  slots={'a':{'state':'KNOWN','canonical_category':'CORE'},'b':{'state':'KNOWN','canonical_category':'CORE'},'c':{'state':'UNKNOWN'}}
  result=evaluate('example','S',1,ranking,slots,units,sel)
  self.assertEqual(result['core_delivered'],[2,2]);self.assertEqual(result['core_document_delivered'],[1,1]);self.assertEqual(result['known_irrelevant_selected'],[]);self.assertEqual(result['unknown_selected'],['c']);self.assertEqual(result['classification_known'],2)
 def test_undeliverable_core_kept_in_full_denominator(self):
  from legal_bench.rules_verdict_v1.authority_evaluation_v10 import evaluate
  units=[{'id':'large','text':'x'*21000,'source':{'document_id':'d'},'dependencies':[]}]
  sel=pack.select([{'id':'large'}],units,pack.PRIMARY_CONFIG)
  out=evaluate('x','S',0,[{'id':'large'}],{'large':{'state':'KNOWN','canonical_category':'CORE'}},units,sel)
  self.assertEqual(out['core_delivered'],[0,1]);self.assertEqual(out['feasible_core_delivered'],[0,0]);self.assertEqual(out['core_missing_reasons']['large'],'INDIVIDUAL_DEPENDENCY_BUNDLE_TOO_LONG')
if __name__=='__main__':unittest.main()
