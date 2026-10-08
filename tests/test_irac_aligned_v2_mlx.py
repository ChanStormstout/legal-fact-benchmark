import unittest,numpy as np
from legal_bench.irac_application.aligned_v2_models import metadata,masked_group_loss
from legal_bench.irac_application.graph_builder import reject_supervision
class Inputs(unittest.TestCase):
 def test_cli_main_keeps_logs_when_export_fails(self):
  import tempfile,json
  from pathlib import Path
  from unittest.mock import patch
  import scripts.irac_aligned_v2_train as entry
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'freeze').mkdir();(root/'freeze/run-order.json').write_text(json.dumps([{'id':'a'},{'id':'b'}]));(root/'freeze/splits.json').write_text('[]');called=[]
   def cb(spec):
    def fit():called.append(spec['id']);return object(),{'history':[{'epoch':0}]}
    def fail(*args):raise OSError('injected actual entry export failure')
    return dict(fit_call=fit,predict_call=lambda m:{'rows':[]},export_call=fail,verify_call=lambda *a:{})
   with patch.object(entry,'R',root),patch.object(entry,'verify_frozen'),patch.object(entry,'load',return_value=[]),patch.object(entry,'callbacks',side_effect=cb):entry.main()
   self.assertEqual(called,['a']);self.assertTrue((root/'training/a-fit.json').is_file());self.assertTrue((root/'predictions/a.json').is_file());self.assertEqual(json.loads((root/'training-status.json').read_text())['status'],'PAUSED')
 def test_coverage_changes_actual_features(self):
  n={'type':'Burden','features':{'coverage_status':'NOT_COVERED'},'source_grounded':False}
  a=metadata(n);n['features']['coverage_status']='COVERED';self.assertNotEqual(a,metadata(n))
 def test_reference_rejected(self):
  with self.assertRaises(ValueError):reject_supervision({'bindings':[{'label':'SUPPORTED'}]})
 def test_group_weight_not_binding_count(self):
  import mlx.core as mx
  def model(t):return mx.array(t)
  p={'group_id':'a','mask':[True],'labels':[0],'issue_ids':['c'],'tensors':[[2.,0.,0.]]}
  q={'group_id':'b','mask':[True],'labels':[1],'issue_ids':['c'],'tensors':[[2.,0.,0.]]}
  a=float(masked_group_loss(model,[p,q]).item())
  p=dict(p,mask=[True]*5,labels=[0]*5,issue_ids=['c']*5,tensors=p['tensors']*5)
  b=float(masked_group_loss(model,[p,q]).item());self.assertAlmostEqual(a,b,places=6)
if __name__=='__main__':unittest.main()
