import unittest,tempfile,json,subprocess,sys,copy
from pathlib import Path
from legal_bench.proof_carrying.semantic_search_v12 import complete_search
from legal_bench.proof_carrying.semantic_checker_v12 import check
from legal_bench.proof_carrying.semantic_data_v12 import training_gate,hierarchical_weights
from scripts.proof_semantic_run_v12 import run
from legal_bench.proof_carrying.contracts import content_hash

def fixture():
 source={'s':{'text':'A witness asserted entry. Rule permits the limited result.','document':'x','document_role':'TARGET','role':'BODY','original_line':1}}
 slot=lambda name:{'name':name,'predicate':'assertion','expected':'TRUE','allowed_statuses':['PARTY_CLAIM'],'required_roles':['subject'],'time_required':False}
 rule={'id':'R','version':1,'operator':'ALL','slots':[slot('a'),slot('b')],'exception_slots':[],'conclusion_predicate':'limited','source_refs':['s'],'source_quote':'Rule permits the limited result.'}
 fact={'id':'f','predicate':'assertion','statement_status':'PARTY_CLAIM','bindings':[{'role':'subject','entity':'person'}],'refs':['s'],'quote':'A witness asserted entry.','state':'TRUE','time_scope':None}
 c={'id':'c','rule_ref':'R@1','bindings':fact['bindings'],'time_scope':None,'inputs':[{'slot':k,'kind':'PREMISE','id':'f'} for k in ['a','b']]}
 s={'case_id':'x','sources':source,'premises':{'f':fact},'rules':{'R@1':rule},'contracts':{'R@1':{'slot_variables':{'a':{'subject':'subject'},'b':{'subject':'subject'}}}},'model_uses':{}}
 s['contracts']['R@1']['rule_hash']=content_hash(rule)
 q=[{'id':'Q','predicate':'limited'}];return s,[c],q

class SemanticTests(unittest.TestCase):
 def test_entry_no_reference_and_support_not_truth(self):
  s,c,q=fixture();s['model_uses']={'c::a':{'label':'USABLE'},'c::b':{'label':'USABLE'}}
  with tempfile.TemporaryDirectory() as t:
   run(s,c,q,Path(t)/'run');d=json.loads((Path(t)/'run/checked.json').read_text());self.assertFalse(d['reference_read']);self.assertEqual(d['requests'][0]['answer'],'UNKNOWN')
 def test_status_and_local_use(self):
  s,c,q=fixture();s['rules']['R@1']['operator']='ANY';s['rules']['R@1']['slots'][0]['allowed_statuses']=['TARGET_COURT_FINDING']
  s['model_uses']={f'c::{x}':{'label':'USABLE','premise_state':'TRUE','premise_judgment_basis':'Explicit unverified model judgment of recorded assertion, not occurrence.'} for x in ['a','b']}
  s['contracts']['R@1']['rule_hash']=content_hash(s['rules']['R@1'])
  d=check(s,complete_search(c,s['rules'],q,s['contracts']));self.assertEqual(d['requests'][0]['answer'],'TRUE');self.assertTrue(any('STATEMENT_STATUS' in z for z in next(iter(d['steps'].values()))['pending']))
 def test_unknown_object_and_exception(self):
  s,c,q=fixture();s['model_uses']={f'c::{x}':{'label':'USABLE','premise_state':'TRUE','premise_judgment_basis':'assumption'} for x in ['a','b']}
  s['premises']['f']['bindings'][0]['entity']=''
  self.assertEqual(check(s,complete_search(c,s['rules'],q,s['contracts']))['requests'][0]['answer'],'UNKNOWN')
  s,c,q=fixture();s['rules']['R@1']['operator']='ANY';s['rules']['R@1']['exception_slots']=['b'];s['model_uses']={'c::a':{'label':'USABLE','premise_state':'TRUE','premise_judgment_basis':'assumption'}}
  s['contracts']['R@1']['rule_hash']=content_hash(s['rules']['R@1'])
  self.assertEqual(check(s,complete_search(c,s['rules'],q,s['contracts']))['requests'][0]['answer'],'UNKNOWN')
 def test_alternatives_dependencies_and_budget(self):
  s,c,q=fixture();r=copy.deepcopy(s['rules']['R@1']);r['id']='D';r['conclusion_predicate']='assertion';s['rules']['D@1']=r;s['contracts']['D@1']=s['contracts']['R@1'];dep=copy.deepcopy(c[0]);dep.update(id='dep',rule_ref='D@1');c.append(dep);c[0]['inputs'][0]={'slot':'a','kind':'RULE_DEPENDENCY','id':'D@1'}
  out=complete_search(c,s['rules'],q,s['contracts']);self.assertEqual(len(out['steps']),2);self.assertEqual(out['steps'][-1]['inputs'][0]['kind'],'STEP')
  stop=complete_search(c,s['rules'],q,s['contracts'],max_expansions=1);self.assertEqual(stop['requests'][0]['search_status'],'SEARCH_INCOMPLETE')
  dep['inputs'][0]={'slot':'a','kind':'RULE_DEPENDENCY','id':'R@1'};out=complete_search(c,s['rules'],q,s['contracts']);self.assertTrue(any(x['kind']=='CYCLE' for x in out['requests'][0]['issues']))
 def test_actual_entry_foreign_time_and_bundle(self):
  for mutation,reason in [('foreign','FOREIGN_FACT'),('time','TIME_MISMATCH'),('quote','SOURCE:')]:
   s,c,q=fixture();s['model_uses']={f'c::{x}':{'label':'USABLE','premise_state':'TRUE','premise_judgment_basis':'model assumption'} for x in ['a','b']}
   if mutation=='foreign':s['sources']['s']['document_role']='PRECEDENT'
   if mutation=='time':
    s['rules']['R@1']['slots'][0]['time_required']=True;s['premises']['f']['time_scope']='Monday';c[0]['time_scope']='Tuesday';s['contracts']['R@1']['rule_hash']=content_hash(s['rules']['R@1'])
   if mutation=='quote':s['premises']['f']['quote']='An altered quotation.'
   with tempfile.TemporaryDirectory() as t:
    run(s,c,q,Path(t)/'run');d=json.loads((Path(t)/'run/checked.json').read_text());self.assertEqual(d['requests'][0]['answer'],'UNKNOWN');self.assertIn(reason,json.dumps(d))
  s,c,q=fixture();s['premises']['g']=copy.deepcopy(s['premises']['f']);s['premises']['g']['id']='g';c[0]['inputs'][0].update(kind='BUNDLE',id='bundle',evidence_ids=['f','g'])
  s['model_uses']={f'c::{x}':{'label':'USABLE','premise_state':'TRUE','premise_judgment_basis':'explicit bundle coverage proposed by model'} for x in ['a','b']}
  with tempfile.TemporaryDirectory() as t:
   run(s,c,q,Path(t)/'run');d=json.loads((Path(t)/'run/checked.json').read_text());self.assertEqual(d['requests'][0]['answer'],'TRUE');self.assertFalse(d['semantic_verified'])
 def test_failure_preserves_null(self):
  s,c,q=fixture();del s['rules']
  with tempfile.TemporaryDirectory() as t:
   with self.assertRaises(KeyError):run(s,c,q,Path(t)/'run')
   failure=json.loads((Path(t)/'run/failure.json').read_text());self.assertIsNone(failure['answer']);self.assertIn('traceback',failure)
 def test_prediction_does_not_supply_truth_or_approval(self):
  from scripts.proof_semantic_apply_v12 import apply
  s,c,q=fixture();s['model_uses']={'c::a':{'raw_use_id':'u','label':'UNRESOLVED','premise_state':'UNKNOWN'}}
  changed=apply(s,[{'key':'x::u','probabilities':[.9,.05,.05]}],'x')
  self.assertEqual(changed['model_uses']['c::a']['label'],'USABLE');self.assertEqual(changed['model_uses']['c::a']['premise_state'],'UNKNOWN');self.assertEqual(s['model_uses']['c::a']['label'],'UNRESOLVED')
  with tempfile.TemporaryDirectory() as t:
   run(changed,c,q,Path(t)/'run');d=json.loads((Path(t)/'run/checked.json').read_text());self.assertEqual(d['requests'][0]['answer'],'UNKNOWN')
 def test_frozen_proposal_adapter_actual_entry(self):
  from legal_bench.proof_carrying.semantic_import_v12 import adapt
  from legal_bench.proof_carrying.semantic_tasks_v12 import CONTRACT
  p=copy.deepcopy(CONTRACT)
  case={'case_id':'demo','targets':[{'id':'Q1','text':'Recorded assertion only'}],'segments':[{'id':'DEMO:L1','source_document':'demo','original_line':1,'text':'Ada testified that she entered Lot A on Monday.'},{'id':'DEMO:L2','source_document':'demo','original_line':2,'text':'A testimony record supports the attribution of the assertion, not automatic proof of entry.'}]}
  s,c,q=adapt(case,p)
  with tempfile.TemporaryDirectory() as t:
   run(s,c,q,Path(t)/'run');d=json.loads((Path(t)/'run/checked.json').read_text());self.assertEqual(d['requests'][0]['answer'],'TRUE');self.assertFalse(d['semantic_verified'])
  self.assertEqual(s['raw_proposal'],p)
 def test_gate_and_weights(self):
  self.assertFalse(training_gate([], {})['open']);rows=[{'dispute_id':'a','request_id':'1'}]*5+[{'dispute_id':'b','request_id':'2'}];w=hierarchical_weights(rows);self.assertAlmostEqual(sum(w[:5]),.5);self.assertAlmostEqual(w[-1],.5)
if __name__=='__main__':unittest.main()
