import copy,json,tempfile,unittest
from pathlib import Path
from legal_bench.proof_carrying import local_pipeline_v18 as p
from legal_bench.proof_carrying.local_checker_v18 import check
from legal_bench.proof_carrying.local_schedule_v18 import run
import scripts.proof_local_comparison_v18 as entry

def fixture():
 c={'case_id':'SYN','dispute_id':'SYN','targets':[{'id':'Q1','question':'reconstruct trial control'}],
    'segments':[{'id':'SYN:L1','source_document':'SYN','original_line':1,'text':'Mira claimed she returned the key.'},
                {'id':'SYN:L2','source_document':'SYN','original_line':2,'text':'The trial court found Mira retained the key on Saturday.'},
                {'id':'SYN:L3','source_document':'SYN','original_line':3,'text':'The person with the key was Mira, not Nia.'}]}
 r=[{'id':'R1','operator':'ALL','stage':'trial','premises':[{'id':'R1.P1','text':'Trial retained control','variables':{'tenant':'person'},'allowed_statuses':['COURT_FINDING']}],'conclusion':'Trial control','exceptions':[]}]
 raw={'records':[{'text':'Trial retained control','status':'COURT_FINDING','stage':'trial','refs':['SYN:L2']}],
      'objects':[{'label':'Mira','type':'person','refs':['SYN:L3'],'identity_basis':'Source explicitly names Mira.'}],
      'uses':[{'premise':'R1.P1','records':[1],'bindings':[{'address':'R1.P1::tenant','object':1}],'direction':'SUPPORT',
               'claim':'Report the attributed trial finding','stage':'trial','witnesses':[{'refs':['SYN:L2'],'quote':'The trial court found Mira retained the key on Saturday.','necessity':'REQUIRED'}],
               'self_assessment':'SUPPORTED','limits':[]}],
      'premises':[{'premise':'R1.P1','bindings':[{'address':'R1.P1::tenant','object':1}],'uses':[1],'state':'TRUE','complete':True,'stage':'trial','basis':'Report trial finding only',
                   'opposition_uses':[],'gaps':[],'necessary_limits':[]}],'coverage_limits':[]}
 return c,r,raw
class Interface(unittest.TestCase):
 def test_actual_entry_and_independent_checker(self):
  c,r,x=fixture();self.assertIs(entry.pipe,p);p.validate(x,p.schema(r));a=p.apply_connection_decisions(c,r,x);self.assertEqual(a['conditional_rules'][0]['conditional_result'],'TRUE');self.assertFalse(check(r,a)['traces'][0]['errors']);self.assertEqual(a['approval'],'NOT_GRANTED')
 def test_object_only_refs_recovered_and_common_input(self):
  c,r,x=fixture();data=p.learner_inputs(c,r,x);self.assertIn('SYN:L3',data['materials']['K001']['actual_restored_source']['requested_refs'])
  self.assertIn('not Nia',data['ce_pairs'][0]['right']);self.assertIn('not Nia',next(n['text'] for n in data['graph']['nodes'] if n['id']=='C:K001'));self.assertIn('not Nia',data['ce_pairs'][0]['shared_case_context']['packets']['K001']['actual_restored_source']['segments'][-1]['text'])
 def test_address_not_type_and_wrong_object_local(self):
  c,r,x=fixture();x['uses'][0]['bindings'][0]['address']='person';a=p.apply_connection_decisions(c,r,x);self.assertIn('INVALID_ROLE_ADDRESS',a['checks'][0]['errors']);self.assertEqual(a['raw_records_retained'],1)
 def test_use_label_never_whole_truth(self):
  c,r,x=fixture();x['premises'][0]['complete']=False;a=p.apply_connection_decisions(c,r,x);self.assertEqual(a['checks'][0]['applied_label'],'SUPPORTED');self.assertEqual(a['conditional_rules'][0]['conditional_result'],'UNKNOWN')
 def test_predictor_actually_changes_processing(self):
  c,r,x=fixture();a=p.apply_connection_decisions(c,r,x,{'K001':'UNSUPPORTED'});self.assertEqual(a['checks'][0]['disposition'],'MODEL_REJECTED_USE');self.assertEqual(a['conditional_rules'][0]['conditional_result'],'UNKNOWN');self.assertEqual(a['raw_records_retained'],1)
 def test_unknown_not_rejection(self):
  c,r,x=fixture();a=p.apply_connection_decisions(c,r,x,{'K001':'UNRESOLVED'});self.assertEqual(a['checks'][0]['disposition'],'MODEL_PENDING_USE');self.assertEqual(a['premise_judgments'][0]['pending_uses'],['K001'])
 def test_independent_use_survives_invalid(self):
  c,r,x=fixture();x['uses'].append(copy.deepcopy(x['uses'][0]));x['uses'][0]['witnesses'][0]['refs']=['WRONG:L2'];x['premises'][0]['uses']=[1,2];a=p.apply_connection_decisions(c,r,x);self.assertEqual(a['conditional_rules'][0]['conditional_result'],'TRUE');self.assertEqual(a['premise_judgments'][0]['blocked_uses'],['K001'])
 def test_whole_limit_not_bypassed(self):
  c,r,x=fixture();x['premises'][0]['necessary_limits']=['Identity unresolved'];a=p.apply_connection_decisions(c,r,x);self.assertEqual(a['conditional_rules'][0]['conditional_result'],'UNKNOWN');self.assertFalse(check(r,a)['traces'][0]['errors'])
 def test_true_unknown_not_conflict(self):
  self.assertEqual(p.combine_states(['TRUE','UNKNOWN']),'TRUE');self.assertEqual(p.combine_states(['TRUE','FALSE']),'CONFLICTED')
 def test_opposition_preserved_and_background_insufficient(self):
  c,r,x=fixture();x['uses'][0]['direction']='CONTEXT';a=p.apply_connection_decisions(c,r,x);self.assertEqual(a['conditional_rules'][0]['conditional_result'],'UNKNOWN');x['uses'][0]['direction']='OPPOSE';a=p.apply_connection_decisions(c,r,x);self.assertEqual(len(a['raw_opposition_retained']),1)
 def test_open_text_not_and_and_exception_retained(self):
  c,r,x=fixture();r[0]['operator']='OPEN_TEXT';a=p.apply_connection_decisions(c,r,x);self.assertEqual(a['conditional_rules'][0]['conditional_result'],'UNKNOWN');self.assertTrue(a['conditional_rules'][0]['not_executed']);r[0]['operator']='ALL';r[0]['exceptions']=['unresolved exception'];self.assertEqual(p.apply_connection_decisions(c,r,x)['conditional_rules'][0]['conditional_result'],'UNKNOWN')
 def test_different_role_dictionaries_compatible_only_shared(self):
  rows=[{'binding':{'claimant':1,'land':2}},{'binding':{'state':3,'land':2}}];self.assertEqual(p.compatible(rows),{'claimant':1,'land':2,'state':3});rows[1]['binding']['land']=4;self.assertIsNone(p.compatible(rows))
 def test_no_name_merging_across_parts(self):
  c,r,x=fixture();z,ledger=p.merge_parts([('part1',x),('part2',x),('failed',None)]);self.assertEqual(len(z['objects']),2);self.assertEqual(len(z['records']),1);self.assertIn('FAILED_PART:failed',z['coverage_limits'])
 def test_reviewer_not_self_approval(self):
  c,r,x=fixture();y=p.annotation_material(x);self.assertNotIn('self_assessment',y['uses'][0]);self.assertNotIn('premises',y);self.assertIn('self_assessment',x['uses'][0])
 def test_independent_checker_rejects_tampered_result(self):
  c,r,x=fixture();a=p.apply_connection_decisions(c,r,x);a['conditional_rules'][0]['conditional_result']='FALSE';self.assertIn('RESULT_MISMATCH',check(r,a)['traces'][0]['errors'])
 def test_pause_after_single_result_saved(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);called=[]
   def perform(s,dest):
    dest.mkdir();(dest/'run.json').write_text('{"run_status":"OK"}');called.append(s['id']);(root/'PAUSE_REQUESTED.json').write_text('{}');return {'run_status':'OK'}
   self.assertEqual(entry.schedule(root,[{'id':1,'dest':'one'},{'id':2,'dest':'two'}],perform),'PAUSED');self.assertEqual(called,[1]);self.assertFalse((root/'two').exists())
 def test_final_answer_nonempty(self):
  with self.assertRaises(ValueError):p.validate({'request_id':'Q1','conclusion':'','grounds':[],'counterarguments':[],'gaps':[],'assumptions':[],'connection_handling':[]},p.FINAL_SCHEMA)
if __name__=='__main__':unittest.main()
