import copy,json,tempfile,unittest
from tests.test_pipeline_contract_v19_7 import fixture
from legal_bench.proof_carrying import source_verification_v20 as m
from legal_bench.proof_carrying.source_verification_check_v20 import check
from legal_bench.proof_carrying.schema_contract_v19_6 import validate

def setup():
 c,r,p=fixture();q={'supplement':copy.deepcopy(p),'verdicts':[],'coverage_limits':[]}
 for origin,raw in [('P',p),('Q',q['supplement'])]:
  for d in m.declarations(raw,origin,r):q['verdicts'].append({'declaration':d['id'],'label':'SUPPORTED','refs':['SRC:1'],'counter_refs':[],'reason':'Synthetic only.'})
 return c,r,p,q
class SourceVerification(unittest.TestCase):
 def test_full_entry_immutability_and_independent_check(self):
  c,r,p,q=setup();before=copy.deepcopy([p,q]);x=m.apply(c,r,p,q)
  self.assertEqual(before,[p,q]);self.assertEqual(check(p,q,x,r)['status'],'OK');self.assertFalse(x['semantic_approval'])
  x['applied_proposals']['P']['analyses']['R1.P1']['records']=[]
  self.assertEqual(check(p,q,x,r)['status'],'REJECTED')
 def test_label_does_not_become_truth_and_local_alternative_preserved(self):
  c,r,p,q=setup();labels={d['id']:'SUPPORTED' for d in m.candidates(c,r,p,q)['candidates']}
  labels['P/R1.P1/J:1']='UNSUPPORTED';x=m.apply(c,r,p,q,labels)
  self.assertEqual(x['applied_proposals']['P']['analyses']['R1.P1']['judgments'][0]['state'],'UNKNOWN')
  self.assertEqual(x['applied_proposals']['Q']['analyses']['R1.P1']['judgments'][0]['state'],'TRUE')
  self.assertEqual(check(p,q,x,r)['status'],'OK')
 def test_bad_attribution_does_not_delete_original_or_opposition(self):
  c,r,p,q=setup();labels={d['id']:'SUPPORTED' for d in m.candidates(c,r,p,q)['candidates']};labels['P/R1.P1/EV:1']='UNSUPPORTED'
  x=m.apply(c,r,p,q,labels);self.assertEqual(len(x['applied_proposals']['P']['analyses']['R1.P1']['records']),1)
  self.assertEqual(x['applied_proposals']['P']['analyses']['R1.P1']['uses'][0]['self_assessment'],'UNRESOLVED')
 def test_missing_unknown_duplicate_verdicts_are_local(self):
  c,r,p,q=setup();q['verdicts']+=[q['verdicts'][0],{'declaration':'P/FAKE','label':'SUPPORTED','refs':['SRC:1'],'counter_refs':[],'reason':'bad'}]
  pool=m.candidates(c,r,p,q);self.assertEqual(pool['candidates'][0]['proposed_label'],'UNRESOLVED');self.assertEqual(len(pool['quarantined']),2)
 def test_features_no_labels_and_full_source_blocks(self):
  c,r,p,q=setup();data=m.common_inputs(c,r,m.candidates(c,r,p,q));blob=json.dumps(data['graph'])
  for k in ('self_assessment','verification_label','verifier_reason','proposed_label'):self.assertNotIn(k,blob)
  self.assertTrue(data['source_mapping']);self.assertTrue(data['graph']['edges'])
  self.assertEqual(data['ce_pairs'][0]['shared_material_blocks'][0]['text'],data['graph']['nodes'][0]['text'])
 def test_q_schema_and_bad_reference(self):
  c,r,p,q=setup();validate(q,m.q_schema(r,c));bad=copy.deepcopy(q);bad['verdicts'][0]['refs']=['SRC:999']
  with self.assertRaises(ValueError):validate(bad,m.q_schema(r,c))
 def test_all_final_methods_and_missing_predictions(self):
  c,r,p,q=setup();labels={d['id']:'SUPPORTED' for d in m.candidates(c,r,p,q)['candidates']}
  for method in 'ACDEFG':
   task=m.final_task(c,r,method,p,q,labels if method in 'EFG' else None)
   self.assertTrue(task['presentation_audit']['exact_roundtrip'])
  with self.assertRaises(ValueError):m.final_task(c,r,'G',p,q)
 def test_generic_adapter_never_infers_shared_roles(self):
  c,r,p,q=setup();r[0].pop('slot_variables');pr=r[0]['premises'][0];pr.pop('input_contract');pr['variables']={'widow':'person'}
  r[0]['premises'].append({**copy.deepcopy(pr),'id':'R1.P2'});z=m.adapt_rules(r)
  self.assertNotEqual(z[0]['slot_variables']['R1.P1']['widow'],z[0]['slot_variables']['R1.P2']['widow']);self.assertTrue(z[0]['unmapped_shared_variable_contract'])
if __name__=='__main__':unittest.main()

class ActualEntry(unittest.TestCase):
 def test_merge_does_not_offset_invalid_refs_into_other_parts(self):
  from scripts.proof_source_verification_v20 import merge_raw
  c,r,p,q=setup();c['case_id']='SYN';f={'case':c,'rules':r}
  slots=[({'part':{'source_ids':[s['id'] for s in c['segments']]}},p),({'part':{'source_ids':[s['id'] for s in c['segments']]}},copy.deepcopy(p))]
  slots[1][1]['analyses']['R1.P1']['uses'][0]['records']=['EV:999']
  z=merge_raw(f,slots,'P');self.assertEqual(len(z['analyses']['R1.P1']['records']),2)
  self.assertEqual(z['analyses']['R1.P1']['uses'][1]['records'],['INVALID_LOCAL:EV:999'])
 def test_actual_final_dispatch_and_pause_saving(self):
  from scripts import proof_source_verification_v20 as entry
  from unittest.mock import patch
  from pathlib import Path
  c,r,p,q=setup();c.update(case_id='SYN',split='DEV');f={'case':c,'rules':r}
  class FakeRunner:
   def __init__(self,*args):pass
   def run(self,prompt,schema,dest,*args):
    entry.save(dest/'run.json',{'run_status':'OUTPUT_TRUNCATED','elapsed_seconds':1})
    entry.text(dest/'raw-response.txt','{"partial":');return {'run_status':'OUTPUT_TRUNCATED'}
  from legal_bench.proof_carrying.local_runtime_v19_6 import SETTINGS
  cfg={'slots':[{'case_id':'SYN','role':'A','dest':'local/SYN/A','output_tokens':8192}], 'runtime':SETTINGS,'stage_seconds':{'final':50}}
  with tempfile.TemporaryDirectory() as d,patch.object(entry,'OUT',Path(d)),patch.object(entry,'frozen',return_value=cfg),patch.object(entry,'fixture',return_value=f),patch.object(entry,'tokenizer',return_value=None),patch.object(entry,'measured',return_value={'fits':True}),patch('legal_bench.proof_carrying.local_runtime_v19_6.Runner',FakeRunner):
   self.assertEqual(entry.run_generation('final'),'FINISHED');v=entry.read(Path(d)/'local/SYN/A/formal-answer.json');self.assertIsNone(v['answer'])
   entry.save(Path(d)/'PAUSE_REQUESTED.json',{'requested':True});self.assertEqual(entry.run_generation('final'),'PAUSED')
