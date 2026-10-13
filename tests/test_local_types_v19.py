import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_local_pipeline_v19 import fixture
from legal_bench.proof_carrying import object_types_v19 as types
from legal_bench.proof_carrying import local_pipeline_v19_types as pipe
from legal_bench.proof_carrying.local_checker_v19_types import check
from scripts import proof_local_types_v19 as entry
class Types(unittest.TestCase):
 def execute(self,actual='person',expected='person',change=None,decision=None):
  c,r,x=fixture();x['analyses'][0]['objects'][0]['type']=actual;r[0]['premises'][0]['variables']['tenant']=expected
  if change:change(x)
  p,_=pipe.merge_parts([('P01',x)]);a=pipe.apply_connection_decisions(c,r,p,decision);ind=check(c,r,p,decision,a);self.assertEqual(ind['status'],'OK',ind);return c,r,p,a
 def test_known_alias_not_identity(self):
  c,r,p,a=self.execute(' tenant ','person');self.assertEqual(a['checks'][0]['disposition'],'CONDITIONALLY_AVAILABLE_USE');self.assertEqual(a['premise_judgments'][0]['conditional_state'],'TRUE');self.assertFalse(a['checks'][0]['type_compatibility'][0]['identity_established'])
 def test_unknown_equal_different_and_null_not_conflict(self):
  for actual,expected in [('appealing tenant','person'),('person','tenant seeking relief'),('specific person A','specific person A'),(None,'person'),('persno','person')]:
   c,r,p,a=self.execute(actual,expected);self.assertNotIn('OBJECT_TYPE_CONFLICT',a['checks'][0]['errors']);self.assertEqual(a['checks'][0]['type_coverage'],'PENDING');self.assertTrue(a['checks'][0]['full_basis_eligible']);self.assertEqual(a['premise_judgments'][0]['conditional_state'],'TRUE');self.assertTrue(a['premise_judgments'][0]['unverified_type_assumptions'])
 def test_clear_disjoint_types_still_rejected(self):
  c,r,p,a=self.execute('leased_premises','person');self.assertIn('OBJECT_TYPE_CONFLICT',a['checks'][0]['errors']);self.assertEqual(a['checks'][0]['disposition'],'STRUCTURAL_INVALID')
 def test_wrong_id_and_document_rejected_locally(self):
  for change in [lambda x:x['analyses'][0]['uses'][0]['bindings'][0].update(object=99),lambda x:x['analyses'][0]['objects'][0].update(refs=['WRONG:L3'])]:
   c,r,p,a=self.execute(change=change);self.assertEqual(a['checks'][0]['disposition'],'STRUCTURAL_INVALID');self.assertEqual(a['raw_records_retained'],1)
 def test_alternative_with_unmapped_type_retained(self):
  def change(x):
   u=x['analyses'][0];u['objects'].append({**u['objects'][0],'type':'unmapped human description'});u['uses'].append(copy.deepcopy(u['uses'][0]));u['uses'][1]['bindings'][0]['object']=2;u['judgments'][0]['uses']=[1,2];u['judgments'][0]['components'][0]['alternatives']=[[1],[2]]
  c,r,p,a=self.execute(change=change);self.assertEqual(a['premise_judgments'][0]['conditional_state'],'TRUE');self.assertEqual(len(a['checks']),2)
 def test_same_type_different_id_not_merged(self):
  c,r,x=fixture();p,_=pipe.merge_parts([('P01',x),('P02',x)]);alias,checks=pipe.object_aliases(p,pipe.sources(c));self.assertEqual(alias,{1:1,2:2});self.assertEqual(checks,[])
 def test_conflicting_rule_variable_rejected(self):
  def change(x):
   u=x['analyses'][0];u['objects'].append({**u['objects'][0],'label':'Nia'});u['uses'][0]['bindings'].append({**u['uses'][0]['bindings'][0],'object':2})
  c,r,p,a=self.execute(change=change);self.assertIn('OBJECT_CONFLICT',a['checks'][0]['errors'])
 def test_explicit_link_pending_vs_conflict(self):
  for t,status in [('free descriptor','OBJECT_LINK_TYPE_UNMAPPED'),('property','OBJECT_LINK_TYPE_CONFLICT')]:
   c,r,x=fixture();second=copy.deepcopy(x['analyses'][0]);second['premise']='R2.P1';second['objects'][0]['type']=t;x['analyses'].append(second);x['object_links']=[{'left_premise':'R1.P1','left_object':1,'right_premise':'R2.P1','right_object':1,'refs':['SYN:L3'],'identity_basis':'Source explicitly links objects.'}];p,_=pipe.merge_parts([('P01',x)]);alias,checks=pipe.object_aliases(p,pipe.sources(c));self.assertNotEqual(alias[1],alias[2]);self.assertIn(status,checks[0]['pending']+checks[0]['errors'])
 def test_checker_recomputes_not_trust_upstream(self):
  c,r,p,a=self.execute();p['objects'][0]['type']='property';self.assertEqual(check(c,r,p,None,a)['status'],'REJECTED')
 def test_use_prediction_not_premise_truth(self):
  c,r,p,a=self.execute(decision={'K001':'UNSUPPORTED'});self.assertEqual(a['premise_judgments'][0]['conditional_state'],'UNKNOWN');self.assertEqual(p['premises'][0]['state'],'TRUE')
 def test_all_methods_see_same_type_policy_and_sources(self):
  c,r,p,a=self.execute('tenant');data=pipe.learner_inputs(c,r,p);pair=data['ce_pairs'][0];q=next(x['text'] for x in data['graph']['nodes'] if x['id']=='Q:Q1');block=next(x for x in pair['shared_material_blocks'] if x['id']=='object-type-contract');self.assertIn(block['text'],q);self.assertIn('not Nia',q);self.assertIn('source:SYN:L3',[x['id'] for x in pair['shared_material_blocks']])
 def test_actual_entry_consolidation(self):
  c,r,x=fixture()
  with tempfile.TemporaryDirectory() as d:
   out=Path(d);part=out/'local/SYN/P01';part.mkdir(parents=True);entry.save(part/'run.json',{'run_status':'OK'});entry.save(part/'parsed.json',x);entry.save(part/'production-version.json',{'version':'V19_1'})
   cfg={'local_generation_slots':[{'role':'P','case_id':'SYN','dest':'local/SYN/P01','part':{'id':'P01','source_ids':[s['id'] for s in c['segments']]}}]}
   with patch.object(entry,'OUT',out),patch.object(entry,'fixture',lambda cid:{'case':c,'rules':r}),patch.object(entry,'protocol',lambda:cfg),patch.object(entry,'annotation_task',lambda cid:None):m=entry.consolidate('SYN')
   self.assertEqual(entry.read(out/'local/SYN/P/independent-check.json')['status'],'OK');self.assertEqual(entry.read(out/'local/SYN/P/offline-audit.json')['interface'],'V19_3');self.assertTrue((out/'inputs/SYN/learner-inputs.json').exists())
 def test_final_real_entry_uses_repaired_checker_and_display(self):
  from legal_bench.proof_carrying.local_runtime_v19_repair import SETTINGS
  c,r,x=fixture();p,_=pipe.merge_parts([('P01',x)])
  with tempfile.TemporaryDirectory() as d:
   out=Path(d);entry.save(out/'local/SYN/P/merged.json',{'answer':p,'status':'COMPLETE'});entry.save(out/'local/SYN/P01/parsed.json',x);entry.save(out/'local/SYN/P01/production-version.json',{'version':'V19_1'})
   slots=[{'role':'P','case_id':'SYN','dest':'local/SYN/P01','part':{'id':'P01','source_ids':[s['id'] for s in c['segments']]}},{'role':'D','case_id':'SYN','dest':'local/SYN/D','max_tokens':8192}]
   cfg={'runtime_settings':SETTINGS,'first_DEV':'SYN','local_generation_slots':slots,'P_seconds_cap':86400,'final_seconds_cap':43200,'per_call_seconds_cap':3600}
   class SavedSyntheticRunner:
    def run(self,prompt,schema,dest,*args):
     entry.text(dest/'prompt.txt',prompt);entry.save(dest/'parsed.json',{'synthetic_transport_only':True});entry.save(dest/'run.json',{'run_status':'OK','elapsed_seconds':0,'model_called':False});return {'run_status':'OK'}
   with patch.object(entry,'OUT',out),patch.object(entry,'assert_frozen',lambda:cfg),patch.object(entry,'protocol',lambda:cfg),patch.object(entry,'fixture',lambda cid:{'case':c,'rules':r}):self.assertEqual(entry.run_local('final',SavedSyntheticRunner()),'FINISHED')
   self.assertEqual(entry.read(out/'local/SYN/D/offline-audit.json')['interface'],'V19_3');self.assertEqual(entry.read(out/'local/SYN/D/independent-check.json')['status'],'OK');self.assertIn('COMPATIBLE_TYPE_DOMAIN',(out/'local/SYN/D/prompt.txt').read_text())
if __name__=='__main__':unittest.main()
