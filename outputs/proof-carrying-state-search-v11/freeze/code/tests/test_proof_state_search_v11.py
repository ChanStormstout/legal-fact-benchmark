import unittest,json,copy,tempfile,shutil
from pathlib import Path
from legal_bench.proof_carrying.search_v11 import covered_product,search,state_features,simple_scores
from scripts import proof_search_delivery_v11 as app
class StateSearch(unittest.TestCase):
 def test_balanced_not_prefix(self):
  p=[list(range(3)),list(range(5)),list(range(4))];cs,a=covered_product(p);self.assertEqual(len(cs),12);self.assertTrue(a['covered_all_marginals']);self.assertTrue(a['not_complete_cartesian_coverage'])
  for i,x in enumerate(p):self.assertEqual({c[i] for c in cs},set(x))
 def test_empty_and_capped_pools(self):
  self.assertEqual(covered_product([])[0],[()]);cs,a=covered_product([list(range(80)),[1]],cap=64);self.assertFalse(a['covered_all_marginals']);self.assertEqual(len(a['unseen_options']['0']),16)
 def test_query_and_state_are_real_inputs(self):
  def c(k,r,inputs):return {'id':k,'rule_ref':r,'inputs':inputs,'simple_features':{'mean_similarity':1.,'missing':0,'flags':0,'opposition':0,'conflict':0}}
  cs=[c('a','r1',[]),c('b','r2',[{'kind':'RULE_DEPENDENCY','id':'r1'}])];rr={'r1':{'conclusion_predicate':'p','slots':[]},'r2':{'conclusion_predicate':'q','slots':[{'predicate':'p'}]}};q={'id':'Q','predicate':'q'}
  empty=state_features(cs,rr,q,[],2);partial=state_features(cs,rr,q,['a'],2);self.assertNotEqual(empty['b'],partial['b']);self.assertEqual(partial['b'][7],1);self.assertEqual(partial['a'][4],1)
  other=state_features(cs,rr,{'id':'P','predicate':'p'},[],2);self.assertNotEqual(empty['b'],other['b'])
  result=search(cs,rr,[q],2,lambda q,s,b,f:simple_scores(f));self.assertEqual(len(set(result['selected'])),2)
 def test_role_fix_actual_entry_not_truth_upgrade(self):
  root=app.OUT
  with tempfile.TemporaryDirectory() as td:
   dest=Path(td);shutil.copytree(root/'contracts',dest/'contracts');shutil.copytree(root/'prepared',dest/'prepared');app.OUT=dest
   try:
    result=app.run_case('1841885','test',app.prepare_case('1841885'),{'selected':['APP-eebe2d556feaa3f7'],'budget':6,'gaps':[]});a=json.loads((dest/'results/test/1841885/analysis.json').read_text());q=next(q for q in a['requests'] if q['id']=='Q4');self.assertEqual(q['answer'],'TRUE');self.assertIn('neither',q['text']);self.assertEqual(result['true'],1)
   finally:app.OUT=root
 def test_input_graph_and_actual_pair_loss(self):
  import numpy as np,mlx.core as mx,mlx.nn as nn
  from legal_bench.proof_carrying.state_ranker_v11 import base_data,state_tensor,StateRanker
  from scripts.proof_state_search_v11 import eligible,BASE
  cid='161859415';prep=app.prepare_case(cid);cs=eligible(cid);qs=json.loads((BASE/'inputs'/cid/'requests.json').read_text());vec=np.load(BASE/'encoding/candidate/vectors.npz');d=base_data(prep[1],prep[0],cs,qs,vec,prep[4]);features=state_features(cs,prep[0],qs[0],[],6);dyn=state_tensor(d,features,qs[0]['id'])
  for kind in ['Flat','RGCN']:
   m=StateRanker(kind,d['x'].shape[1]);m.eval();y=m(d,dyn,qs[0]['id']);mx.eval(y);self.assertEqual(y.shape,(len(cs),));self.assertTrue(np.isfinite(np.array(y)).all())
   def loss(model):
    s=model(d,dyn,qs[0]['id']);return mx.logaddexp(mx.array(0.),s[1]-s[0])
   l,g=nn.value_and_grad(m,loss)(m);mx.eval(l,g);self.assertTrue(np.isfinite(float(l)))
if __name__=='__main__':unittest.main()
