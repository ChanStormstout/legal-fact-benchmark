import copy,json,tempfile,unittest
from pathlib import Path
from legal_bench.proof_carrying import local_pipeline_v19 as pipe
from legal_bench.proof_carrying.local_checker_v19 import check
from legal_bench.proof_carrying.local_schedule_v19 import run,state,checkpoint
from legal_bench.proof_carrying.repetition_v19 import RecordGuard
from legal_bench.rules_verdict_v1.repetition_v9 import RepetitionAbort

def fixture():
 from tests.test_local_comparison_v18 import fixture as legacy
 c,r,p=legacy();p['records'][0]['court_level']='Trial Court'
 unit={'premise':'R1.P1','analysis_status':'ANALYZED','records':p['records'],'objects':p['objects'],'uses':p['uses'],'judgments':p['premises'],'limits':[]}
 for u in unit['uses']:u.pop('premise')
 for j in unit['judgments']:j.pop('premise');j['components']=[{'description':'Attributed trial finding','alternatives':[[1]]}]
 raw={'analyses':[unit],'object_links':[],'coverage_limits':[]}
 return c,r,raw

def process(raw=None,decisions=None):
 c,r,x=fixture();x=x if raw is None else raw;p,_=pipe.merge_parts([('P01',x)]);a=pipe.apply_connection_decisions(c,r,p,decisions)
 assert check(c,r,p,decisions,a)['status']=='OK'
 return a

class Contracts(unittest.TestCase):
 def test_schema_and_adapter(self):
  c,r,x=fixture();pipe.validate(x,pipe.schema(r));a=process(x);self.assertEqual(a['conditional_rules'][0]['conditional_result'],'TRUE');self.assertEqual(a['approval'],'NOT_GRANTED')
 def test_supplementary_wrong_witness_local(self):
  c,r,x=fixture();x['analyses'][0]['uses'][0]['witnesses'].append({'refs':['WRONG'],'quote':'wrong','necessity':'SUPPLEMENTARY'})
  a=process(x);self.assertTrue(a['checks'][0]['warnings']);self.assertEqual(a['premise_judgments'][0]['conditional_state'],'TRUE')
 def test_required_failure_unknown(self):
  c,r,x=fixture();x['analyses'][0]['uses'][0]['witnesses'][0]['quote']='made up';a=process(x);self.assertEqual(a['premise_judgments'][0]['conditional_state'],'UNKNOWN')
 def test_necessary_prediction_rejection(self):
  a=process(decisions={'K001':'UNSUPPORTED'});self.assertEqual(a['premise_judgments'][0]['conditional_state'],'UNKNOWN');self.assertEqual(a['premise_judgments'][0]['model_state'],'TRUE')
 def test_alternative_survives(self):
  c,r,x=fixture();u=x['analyses'][0];u['uses'].append(copy.deepcopy(u['uses'][0]));u['judgments'][0]['uses']=[1,2];u['judgments'][0]['components'][0]['alternatives']=[[1],[2]]
  self.assertEqual(process(x,{'K001':'UNSUPPORTED','K002':'SUPPORTED'})['conditional_rules'][0]['conditional_result'],'TRUE')
 def test_context_not_full_basis(self):
  c,r,x=fixture();x['analyses'][0]['uses'][0]['direction']='CONTEXT';self.assertEqual(process(x)['conditional_rules'][0]['conditional_result'],'UNKNOWN')
 def test_opposition_actually_retained(self):
  c,r,x=fixture();u=x['analyses'][0];u['uses'].append(copy.deepcopy(u['uses'][0]));u['uses'][1]['direction']='OPPOSE';u['judgments'][0]['opposition_uses']=[2]
  a=process(x,{'K001':'UNRESOLVED','K002':'UNSUPPORTED'});self.assertEqual(a['premise_judgments'][0]['conditional_state'],'UNKNOWN');self.assertEqual(len(a['premise_judgments'][0]['opposition_uses']),1)
 def test_stage_check_at_premise_and_rule_scope(self):
  c,r,x=fixture();r[0]['premises'][0]['stage']='appeal';p,_=pipe.merge_parts([('P01',x)]);a=pipe.apply_connection_decisions(c,r,p);self.assertIn('EXPLICIT_SCOPE_MISMATCH:stage',a['checks'][0]['errors']);self.assertEqual(check(c,r,p,None,a)['status'],'OK');self.assertEqual(a['checks'][0]['scope_checks'][0]['rule_stage'],'trial')
 def test_role_type_is_not_variable(self):
  c,r,x=fixture();self.assertEqual(pipe.role_directory(r)[0]['variable'],'R1.P1::tenant');x['analyses'][0]['uses'][0]['bindings'][0]['address']='person';self.assertTrue(process(x)['checks'][0]['errors'])
 def test_no_type_name_merging(self):
  c,r,x=fixture();p,_=pipe.merge_parts([('P01',x),('P02',x)]);self.assertEqual(len(p['objects']),2);self.assertNotEqual(p['objects'][0]['part_scope'],p['objects'][1]['part_scope'])
 def test_prediction_contract_no_fallback(self):
  with self.assertRaises(ValueError):process(decisions={})
  m={'version':'V19_1','class_order':list(pipe.LABELS),'input_sha256':'h'}
  self.assertTrue(pipe.validate_predictions([{'key':'D::K001','probabilities':[1,0,0]}],['D::K001'],m,'h'))
  with self.assertRaises(ValueError):pipe.validate_predictions([],['D::K001'],m,'h')
  with self.assertRaises(ValueError):pipe.validate_predictions([{'key':'D::K001','probabilities':[1,0,0]}],['D::K001'],{**m,'class_order':list(reversed(pipe.LABELS))},'h')
 def test_independent_checker_does_not_trust_errors(self):
  c,r,x=fixture();p,_=pipe.merge_parts([('P01',x)]);a=pipe.apply_connection_decisions(c,r,p);p['uses'][0]['witnesses'][0]['quote']='fabrication';self.assertEqual(check(c,r,p,None,a)['status'],'REJECTED')
 def test_NOT_ANALYZED_not_unknown(self):
  c,r,x=fixture();x['analyses'][0]['analysis_status']='NOT_ANALYZED';a=process(x);self.assertEqual(a['analysis_units'][0]['status'],'NOT_ANALYZED');self.assertEqual(a['premise_judgments'][0]['conditional_state'],'UNKNOWN')
 def test_full_common_input_and_source(self):
  c,r,x=fixture();p,_=pipe.merge_parts([('P01',x)]);d=pipe.learner_inputs(c,r,p);common=d['ce_pairs'][0]['shared_material_blocks'];self.assertIn('not Nia',json.dumps(common));self.assertNotIn('shared_case_context',d['ce_pairs'][0]);self.assertTrue(d['relation_counts']['SUPPORT']);self.assertIn('not Nia',next(n['text'] for n in d['graph']['nodes'] if n['id']=='Q:Q1'))
 def test_repetition_scope_and_chunk_boundaries(self):
  c,r,x=fixture();u=x['analyses'][0];u['records']*=3;raw=json.dumps(x);g=RecordGuard()
  with self.assertRaises(RepetitionAbort):
   for i in range(0,len(raw),7):g.feed(raw[i:i+7])
  c,r,x=fixture();x['analyses']*=3;RecordGuard().feed(json.dumps(x))
 def test_pause_save_resume_checkpoint(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);slots=[{'dest':'one'},{'dest':'two'}];called=[]
   def perform(s,dest):
    dest.mkdir();(dest/'start.json').write_text('{}');(dest/'run.json').write_text('{"run_status":"OK"}');(dest/'formal-answer.json').write_text('{"answer":{}}');(dest/'raw-response.txt').write_text('{}');(dest/'token-ids.json').write_text('[]');called.append(s['dest']);(root/'PAUSE_REQUESTED.json').write_text('{}');return {'run_status':'OK'}
   self.assertEqual(run(root,slots,perform),'PAUSED');self.assertEqual(state(root/'two'),'NOT_STARTED');a=checkpoint(root,'merge',{'first':'OK','second':'NOT_STARTED'});(root/'PAUSE_REQUESTED.json').unlink();self.assertEqual(run(root,slots,perform),'PAUSED');b=checkpoint(root,'merge',{'first':'OK','second':'OK'});self.assertNotEqual(a,b);self.assertEqual(called,['one','two'])
 def test_open_text_and_true_unknown(self):
  c,r,x=fixture();r[0]['operator']='OPEN_TEXT';p,_=pipe.merge_parts([('P01',x)]);self.assertEqual(pipe.apply_connection_decisions(c,r,p)['conditional_rules'][0]['conditional_result'],'UNKNOWN')
if __name__=='__main__':unittest.main()
