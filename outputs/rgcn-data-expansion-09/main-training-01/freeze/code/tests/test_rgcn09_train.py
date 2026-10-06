import unittest
import numpy as np
from legal_bench.rules_verdict_v1 import rgcn_use_v2 as use, rgcn_train_v2 as tr
from scripts.rgcn09_train import augment_dev
class Train09Tests(unittest.TestCase):
 def test_core_alias_and_missing_mask(self):
  x={'uses':[{'unit_id':'a','category':'CORE'},{'unit_id':'b','category':'DIRECT'},{'unit_id':'c','category':'UNKNOWN'}],'isolated':[{'unit_id':'d','category':'CORE'}]}
  self.assertEqual(use.supervision(x,['a','b','c','d','e']),[(0,0),(1,0)])
 def test_shared_pool30(self):
  self.assertEqual(use.UseModel('S',units=30)({}).shape,(30,3))
 def test_dev_alignment_not_invented(self):
  g={'case_id':'dev','nodes':[],'edges':[],'validlinks':{},'alignments':[],'quarantine':[],'pending':[]}
  z=augment_dev(g,[{'id':'law','text':'x'}],[])
  self.assertEqual(z['alignments'][0]['state'],'UNKNOWN');self.assertEqual(z['alignments'][0]['scope'],'UNKNOWN');self.assertEqual(z['validlinks']['law'],[]);self.assertEqual(g['nodes'],[])
 def test_scaler_training_only(self):
  raw={'train':{'z':np.ones((30,18),np.float32)},'dev':{'z':np.full((30,18),999,np.float32)}}
  _,s=tr.fold_data(raw,['train']);self.assertEqual(s['mean'],[1.]*18);self.assertEqual(s['fit_case_ids'],['train'])
if __name__=='__main__':unittest.main()
