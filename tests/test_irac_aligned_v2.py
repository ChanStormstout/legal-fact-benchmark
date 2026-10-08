import unittest,tempfile,json
from pathlib import Path
from legal_bench.irac_application.aligned_v2_runtime import run_schedule
from legal_bench.irac_application.aligned_v2 import effective_state,unit_id,render,template_version
from legal_bench.irac_application.aligned_v2_split import split
class Repair(unittest.TestCase):
 def test_actual_orchestration_failure(self):
  with tempfile.TemporaryDirectory() as d:
   calls=[]
   def cb(s):
    def fit():calls.append(s['id']);return object(),{'history':[{'epoch':0,'loss':1.0}]}
    def fail(m,p):raise OSError('injected weight failure')
    return dict(fit_call=fit,predict_call=lambda m:[{'status':'SUPPORTED'}],export_call=fail,verify_call=lambda *a:{})
   specs=[{'id':'first'},{'id':'second'}];r=run_schedule(d,specs,cb)
   self.assertEqual(calls,['first']);self.assertEqual(r['status'],'PAUSED')
   self.assertTrue((Path(d)/'predictions/first.json').exists());self.assertTrue((Path(d)/'training/first-fit.json').exists())
   self.assertEqual(json.loads((Path(d)/'training/first.json').read_text())['failed_stage'],'weight_export')
   run_schedule(d,specs,cb);self.assertEqual(calls,['first'])
 def test_date_only_and_note(self):
  b={'restrictions':[{'kind':'FIELD','affected_tests':['DATE'],'fields':['date'],'reason':'unknown','source_refs':[],'original_ids':['COMBO:1:0']},{'kind':'NOTE','reason':'prior court','affected_tests':[]}]}
  self.assertEqual(effective_state(b,'TENANCY',{'status':'SUPPORTED'}, {})['status'],'SUPPORTED')
  self.assertEqual(effective_state(b,'DATE',{'status':'SUPPORTED'}, {})['status'],'UNRESOLVED')
 def test_local_witness_not_other_witness(self):
  b={'restrictions':[{'kind':'FIELD','affected_tests':['OWN'],'reason':'lessor title unknown','original_ids':['LINK:L1:0']} ]}
  self.assertEqual(effective_state(b,'OWN',{'status':'SUPPORTED'}, {})['status'],'SUPPORTED')
  self.assertEqual(effective_state(b,'OWN',{'status':'SUPPORTED'}, {})['notes'][0]['application'],'LOCAL_LINK_LIMIT_NOT_WHOLE_TEST')
 def test_units_and_split(self):
  self.assertNotEqual(unit_id('x','c','v','t','father'),unit_id('x','c','v','t','brother'))
  folds=split([{'group_id':str(i),'family':'A' if i<2 else 'B'} for i in range(6)])
  self.assertEqual(len(folds),2)
  for f in folds:
   self.assertFalse(set(f['fit_groups'])&set(f['test_groups']));self.assertFalse(f['validation_groups']);self.assertEqual(len(set(['0','1'])&set(f['fit_groups'])),1)
 def test_distinct_bindings_no_broadcast(self):
  ref={'source_refs':[{'source_id':'law','quote':'rule'}],'op':'REF','id':'T'}
  g={'case_id':'x','source_manifest':{},'bindings':[],'legal_structure':{'template_id':'v','tests':[{'id':'T'}],'claims':[{'id':'C','expression':ref}],'elements':[],'burdens':[],'scope':{},'coverage_limits':[]}}
  for bid in ['father','brother']:g['bindings'].append({'binding_id':bid,'claim_ids':['C'],'identity_status':'ESTABLISHED','identity_refs':[{'source_id':'x','quote':'explicit'}],'scope_status':'COMPATIBLE','restrictions':[],'objects':[],'test_links':{'T':[]}})
  pred={unit_id('x','C','v','T','b'):{} } if False else {unit_id('x','C',template_version(g['legal_structure']),'T','father'):{'status':'REFUTED'},unit_id('x','C',template_version(g['legal_structure']),'T','brother'):{'status':'SUPPORTED'}}
  result=render(g,pred);self.assertEqual([b['result']['status'] for b in result['bindings']],['REFUTED','SUPPORTED']);self.assertEqual(result['claims'][0]['status'],'SUPPORTED')
if __name__=='__main__':unittest.main()
