import unittest,copy,numpy as np
from legal_bench.rules_verdict_v1 import rgcn_development_v2 as g
class GraphChecks(unittest.TestCase):
 def test_status_features(self):
  base={'type':'fact','text':'tenant occupies','status':'CLAIMED','court':'NONE','polarity':'POSITIVE','stage':'pleading','unknown':[]}
  for key,value in [('status','FOUND'),('court','TRIAL'),('polarity','NEGATIVE'),('stage','appeal'),('unknown',['identity'])]:
   b=dict(base);b[key]=value;self.assertFalse(np.array_equal(g.feature(base),g.feature(b)))
 def test_id_not_feature(self):self.assertEqual(g.feature({'id':'a','type':'fact','text':'x'}),g.feature({'id':'b','type':'fact','text':'x'}))
 def test_shapes_and_training(self):
  from legal_bench.rules_verdict_v1.rgcn_train_v2 import Ranker,fit
  import mlx.core as mx
  x=np.random.default_rng(7).normal(size=(4,g.WIDTH)).astype(np.float32)
  adj=np.zeros((len(g.EDGE_TYPES),4,4),np.float32);adj[0,1,0]=1;adj[1,2,1]=1
  pools=np.zeros((2,7,4),np.float32);pools[0,:,1]=1;pools[1,:,2]=1
  d={k:mx.array(v) for k,v in dict(x=x,adj=adj,pools=pools,z=np.zeros((2,len(g.Z_NAMES)),np.float32)).items()}
  mx.random.seed(4);c=Ranker('C');mx.eval(c.parameters());s=np.array(c(d));changed=dict(d,adj=mx.zeros_like(d['adj']));self.assertGreater(float(np.linalg.norm(s-np.array(c(changed)))),1e-7)
  c0=Ranker('C0');self.assertTrue(np.array_equal(np.array(c0(d)),np.array(c0(changed))))
  fitted,log=fit('C',{'synthetic':d},{'synthetic':[(0,1)]},4,steps=2);self.assertGreater(log['parameter_delta_norm'],0);self.assertGreater(log['gradient_norm_first'],0)
 def test_assertion_relation_and_unknown(self):
  source={'segments':[{'id':'P1','text':'Alpha says Beta is a member of Team.'}]}
  fact={'id':'f1','text':'membership alleged','speaker':'THIRD_PARTY','status':'CLAIMED','court':'NONE','stage':'pleading','polarity':'POSITIVE','unknown':[],'roles':[{'role':'SUBJECT','object_id':'o1'}],'refs':['P1'],'quote':'Beta is a member of Team.'}
  rel=dict(fact,id='r1',left='o1',right='o2',relation='member_of')
  p={'case_id':'SYNTHETIC','needs':[{'id':'n1','text':'membership','refs':['P1']}],'objects':[{'id':'o1','text':'Beta','kind':'PERSON','refs':['P1']},{'id':'o2','text':'Team','kind':'GROUP','refs':['P1']}],'facts':[fact],'relations':[rel],'alignments':[]}
  a=g.make_graph(p,[],source,[])
  self.assertFalse(any(x['type'] in ['status','stage'] for x in a['nodes']))
  self.assertFalse(any(e[0]=='o1' and e[2]=='o2' for e in a['edges']))
  self.assertIn(['r1','relation_left','o1'],a['edges']);self.assertIn(['r1','relation_right','o2'],a['edges'])
  p['relations'][0]['unknown']=['identity'];b=g.make_graph(p,[],source,[])
  self.assertFalse(any(e[0]=='r1' for e in b['edges']));self.assertTrue(b['pending'])
  p['gold_correct_authority']='DO_NOT_USE';c=g.make_graph(p,[],source,[]);self.assertEqual(b,c)
 def test_review_masks_scope_without_rewriting(self):
  p={'case_id':'S','needs':[],'objects':[],'facts':[],'relations':[],'alignments':[{'unit_id':'U','scope':'INCOMPATIBLE','state':'CANDIDATE','links':[]}]}
  a=g.make_graph(p,[],{'segments':[]},[{'id':'U','text':'rule'}],['U::alignment0'])
  self.assertEqual(a['alignments'][0]['scope'],'UNKNOWN')
  self.assertEqual(a['alignments'][0]['original_scope'],'INCOMPATIBLE')
  self.assertEqual(p['alignments'][0]['scope'],'INCOMPATIBLE')
 def test_training_only_scaler(self):
  from legal_bench.rules_verdict_v1.rgcn_train_v2 import fold_data
  a={'x':np.ones((1,g.WIDTH),np.float32),'adj':np.zeros((len(g.EDGE_TYPES),1,1),np.float32),'pools':np.ones((1,7,1),np.float32),'z':np.ones((1,len(g.Z_NAMES)),np.float32)}
  b=dict(a,z=np.full_like(a['z'],1000));data,scaler=fold_data({'train':a,'held':b},['train'])
  self.assertEqual(scaler['mean'],[1.]*len(g.Z_NAMES));self.assertEqual(scaler['fit_case_ids'],['train'])
 def test_linear_preferences_required(self):
  from legal_bench.rules_verdict_v1.rgcn_train_v2 import fit
  with self.assertRaises(ValueError):fit('B',{}, {},1)
if __name__=='__main__':unittest.main()
