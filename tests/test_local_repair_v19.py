import copy,json,unittest,tempfile
from pathlib import Path
from tests.test_local_pipeline_v19 import fixture
from legal_bench.proof_carrying import source_contract_v19 as source
from legal_bench.proof_carrying import local_pipeline_v19_repair as pipe
from legal_bench.proof_carrying.local_checker_v19_repair import check
class Repair(unittest.TestCase):
 def execute(self,raw=None,decisions=None):
  c,r,x=fixture();x=x if raw is None else raw;p,_=pipe.merge_parts([('P01',x)]);a=pipe.apply_connection_decisions(c,r,p,decisions);self.assertEqual(check(c,r,p,decisions,a)['status'],'OK');return a
 def test_unique_address_and_ambiguity(self):
  c={'segments':[{'id':'IK-1:L2','source_document':'IK-1','text':'one','original_line':2}]};self.assertEqual(source.resolve('L2',c)['resolved'],'IK-1:L2');self.assertIsNone(source.resolve('IK-9:L2',c)['resolved']);c['segments'].append({'id':'IK-2:L2','source_document':'IK-2','text':'two','original_line':2});self.assertEqual(source.resolve('L2',c)['status'],'AMBIGUOUS_ADDRESS')
 def test_source_schema_and_anchor(self):
  c,r,x=fixture()
  for u in x['analyses'][0]['uses']:
   for w in u['witnesses']:w.pop('quote')
  def refs(v):
   if isinstance(v,dict):
    for key,z in v.items():
     if key=='refs':v[key]=[next(i for i,seg in enumerate(c['segments'],1) if seg['id']==ref) for ref in z]
     else:refs(z)
   elif isinstance(v,list):
    for z in v:refs(z)
  refs(x)
  pipe.validate(x,pipe.schema(r,c));z,m=source.convert(x,c,True);self.assertEqual(self.execute(z)['conditional_rules'][0]['conditional_result'],'TRUE');x['analyses'][0]['records'][0]['refs']=['BAD']
  with self.assertRaises(Exception):pipe.validate(x,pipe.schema(r,c))
 def test_bad_quote_and_disjoint_fragments(self):
  src={'IK-1:L2':{'document':'IK-1','original_line':2,'text':'Monday permission does not cover Tuesday entry.'}}
  self.assertTrue(source.witness_location({'refs':['IK-1:L2'],'quote':'permission covers Tuesday entry'},src).get('error'))
  d=source.witness_location({'refs':['IK-1:L2'],'quote':'Monday permission … Tuesday entry.'},src);self.assertFalse(d['complete_quote_verified']);self.assertFalse(d['omitted_text_restored']);self.assertTrue(source.witness_location({'refs':['IK-1:L2'],'quote':'Tuesday entry. … Monday permission'},src).get('error'))
 def test_limits_are_scoped_no_keywords(self):
  c,r,x=fixture();j=x['analyses'][0]['judgments'][0];j['necessary_limits']=[{'kind':'STAGE_SCOPE','component':0,'reason':'Trial finding only','refs':[]}];self.assertEqual(self.execute(x)['premise_judgments'][0]['conditional_state'],'TRUE');j['necessary_limits']=[{'kind':'BLOCK_SCOPE','component':0,'reason':'Missing prerequisite','refs':[c['segments'][0]['id']]}];self.assertEqual(self.execute(x)['premise_judgments'][0]['conditional_state'],'UNKNOWN');j['necessary_limits']=['Trial finding only'];a=self.execute(x);self.assertTrue(a['premise_judgments'][0]['limit_scope_audit']['scope_pending']);self.assertEqual(a['premise_judgments'][0]['conditional_state'],'UNKNOWN')
 def test_local_error_and_alternative_survival(self):
  c,r,x=fixture();u=x['analyses'][0];u['uses'].append(copy.deepcopy(u['uses'][0]));u['uses'][0]['bindings'][0]['object']=999;u['judgments'][0]['uses']=[1,2];u['judgments'][0]['components'][0]['alternatives']=[[1],[2]];a=self.execute(x);self.assertTrue(a['checks'][0]['errors']);self.assertEqual(a['conditional_rules'][0]['conditional_result'],'TRUE');self.assertEqual(len(a['checks']),2)
 def test_nonpositive_local_reference_is_local_invalid(self):
  c,r,x=fixture();unit=x['analyses'][0];unit['uses'].append(copy.deepcopy(unit['uses'][0]));unit['uses'][0]['bindings'][0]['object']=-1;unit['judgments'][0]['uses']=[1,2];unit['judgments'][0]['components'][0]['alternatives']=[[1],[2]];a=self.execute(x);self.assertTrue(a['checks'][0]['errors']);self.assertEqual(a['checks'][1]['disposition'],'CONDITIONALLY_AVAILABLE_USE');self.assertEqual(a['conditional_rules'][0]['conditional_result'],'TRUE')
 def test_prediction_changes_legal_coverage_not_truth_vote(self):
  a=self.execute();b=self.execute(decisions={'K001':'UNSUPPORTED'});self.assertEqual(a['conditional_rules'][0]['conditional_result'],'TRUE');self.assertEqual(b['conditional_rules'][0]['conditional_result'],'UNKNOWN');self.assertEqual(b['premise_judgments'][0]['model_state'],'TRUE')
 def test_type_and_wrong_document_rejected(self):
  c,r,x=fixture();x['analyses'][0]['objects'][0]['type']='land';self.assertIn('OBJECT_TYPE_MISMATCH',self.execute(x)['checks'][0]['errors']);x['analyses'][0]['objects'][0]['type']='person';x['analyses'][0]['objects'][0]['refs']=['IK-99:L1'];self.assertIn('OBJECT_SOURCE_INVALID',self.execute(x)['checks'][0]['errors'])
 def test_restored_source_shared_all_methods(self):
  c,r,x=fixture();p,_=pipe.merge_parts([('P01',x)]);data=pipe.learner_inputs(c,r,p);self.assertTrue(data['common_material_manifest']['saved_source_ids']);self.assertEqual(len(data['materials']),1);pool=[b for b in data['ce_pairs'][0]['shared_material_blocks'] if b['id'].startswith('source:')];self.assertTrue(pool);self.assertTrue(all(b['text'] in data['graph']['nodes'][0]['text'] for b in pool))
 def test_actual_entry_pause_resume_and_restoration(self):
  from scripts import proof_local_repair_v19 as entry
  from unittest.mock import patch
  from legal_bench.proof_carrying.local_runtime_v19 import SETTINGS
  c,r,x=fixture()
  for u in x['analyses'][0]['uses']:
   for w in u['witnesses']:w.pop('quote')
  def refs(v):
   if isinstance(v,dict):
    for key,z in v.items():
     if key=='refs':v[key]=[next(i for i,seg in enumerate(c['segments'],1) if seg['id']==ref) for ref in z]
     else:refs(z)
   elif isinstance(v,list):
    for z in v:refs(z)
  refs(x)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);prep=root/'preparation';slots=[{'role':'P','case_id':'SYN','dest':'local/SYN/P01','part':{'id':'P01','rule_ids':['R1'],'source_ids':[s['id'] for s in c['segments']]},'max_tokens':16384},{'role':'P','case_id':'SYN','dest':'local/SYN/P02','part':{'id':'P02','rule_ids':['R1'],'source_ids':[s['id'] for s in c['segments']]},'max_tokens':16384}]
   cfg={'code_hashes':{},'runtime_settings':SETTINGS,'local_generation_slots':slots,'first_DEV':'SYN','P_seconds_cap':86400,'final_seconds_cap':43200,'per_call_seconds_cap':3600}
   for slot in slots:
    entry.text(prep/'inputs/SYN'/(slot['part']['id']+'-prompt.txt'),'Engineering only');entry.save(prep/'inputs/SYN'/(slot['part']['id']+'-schema.json'),pipe.schema(r,c))
   calls=[]
   class MockRunner:
    def run(self,prompt,schema,dest,max_tokens,timeout,mode):
     pipe.validate(x,schema);dest.mkdir(parents=True,exist_ok=True)
     for name,value in [('start',{}),('run',{'run_status':'OK','elapsed_seconds':0}),('parsed',x),('token-ids',[])]:entry.save(dest/(name+'.json'),value)
     entry.text(dest/'raw-response.txt',json.dumps(x));calls.append(str(dest))
     if len(calls)==1:entry.save(root/'PAUSE_REQUESTED.json',{})
     return {'run_status':'OK'}
   with patch.object(entry,'OUT',root),patch.object(entry,'PREP',prep),patch.object(entry,'protocol',lambda:cfg),patch.object(entry,'fixture',lambda cid:{'case':c,'rules':r}),patch.object(entry,'annotation_task',lambda cid:None):
    self.assertEqual(entry.run_local('P',MockRunner()),'PAUSED');self.assertFalse((root/'local/SYN/P02/run.json').exists());(root/'PAUSE_REQUESTED.json').unlink();self.assertEqual(entry.run_local('P',MockRunner()),'FINISHED');data=entry.read(root/'inputs/SYN/learner-inputs.json');self.assertTrue(data['common_material_manifest']['saved_source_ids']);self.assertEqual(entry.read(root/'local/SYN/P/independent-check.json')['status'],'OK')
   self.assertEqual(len(calls),2)
if __name__=='__main__':unittest.main()
