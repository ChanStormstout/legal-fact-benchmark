import copy,json,tempfile,unittest
from pathlib import Path
from tests.test_proof_semantic_v12 import fixture
from scripts.proof_semantic_run_v13 import run
from legal_bench.proof_carrying.semantic_interface_v13 import adapt,inputs,recover
from legal_bench.proof_carrying.semantic_tasks_v12 import CONTRACT
from legal_bench.proof_carrying.contracts import content_hash
class V13Tests(unittest.TestCase):
 def entry(self,s,c,q):
  with tempfile.TemporaryDirectory() as t:
   run(s,c,q,Path(t)/'run');return json.loads((Path(t)/'run/checked.json').read_text())
 def bundle(self):
  s,c,q=fixture();c[0]['inputs'][0].update(kind='BUNDLE',id='bundle',evidence_ids=['f','g']);s['premises']['f']['bindings']=[{'role':'actor','entity':'A'}];s['premises']['g']=copy.deepcopy(s['premises']['f']);s['premises']['g']['bindings']=[{'role':'property','entity':'Land'}];c[0]['bindings']=[{'role':'actor','entity':'A'},{'role':'property','entity':'Land'}];s['contracts']['R@1']['slot_variables']={'a':{'actor':'actor','property':'property'},'b':{'actor':'actor'}};s['model_uses']={f'c::{x}':{'label':'USABLE','premise_state':'TRUE','premise_judgment_basis':'unverified explicit judgment'} for x in ['a','b']};return s,c,q
 def test_bundle_roles_and_exact_identity(self):
  s,c,q=self.bundle();self.assertEqual(self.entry(s,c,q)['requests'][0]['answer'],'TRUE')
  s['premises']['g']['bindings'].append({'role':'actor','entity':'Other A'});self.assertEqual(self.entry(s,c,q)['requests'][0]['answer'],'UNKNOWN')
  s,c,q=self.bundle();s['premises']['f']['bindings'][0]['entity']='';c[0]['bindings'][0]['entity']='';self.assertEqual(self.entry(s,c,q)['requests'][0]['answer'],'UNKNOWN')
 def test_types_are_not_variables_and_local_pending(self):
  case,p=self.example();s,c,q=adapt(case,p);self.assertEqual(self.entry(s,c,q)['requests'][0]['answer'],'TRUE')
  p['rules'][0]['premises'][0]['variables']={'speaker':'person','property':'property'};p['uses'][0]['bindings']={'speaker':'Ada','property':'Lot A'}
  s,c,q=adapt(case,p);rc=s['contracts']['R1@1'];self.assertEqual(rc['slot_variables']['R1.P1'],{'speaker':'speaker','property':'property'});self.assertEqual(rc['role_types']['R1.P1']['speaker'],'person');self.assertEqual(self.entry(s,c,q)['requests'][0]['answer'],'TRUE')
  # An unmapped second alternative must not block the independent valid branch.
  s,c,q=self.bundle();s['rules']['R@1']['operator']='ANY';s['contracts']['R@1']['unmapped_roles']={'b':{'unknown':'type'}};s['contracts']['R@1']['rule_hash']=content_hash(s['rules']['R@1']);self.assertEqual(self.entry(s,c,q)['requests'][0]['answer'],'TRUE')
 def example(self):
  case={'case_id':'demo','targets':[{'id':'Q1','text':'Attribution'}],'segments':[{'id':'DEMO:L1','source_document':'demo','original_line':1,'text':'Ada testified that she entered Lot A on Monday.'},{'id':'DEMO:L2','source_document':'demo','original_line':2,'text':'A testimony record supports the attribution of the assertion, not automatic proof of entry.'}]};return case,copy.deepcopy(CONTRACT)
 def test_source_and_relations_shared_not_discarded(self):
  case,p=self.example();p['facts'].append({**copy.deepcopy(p['facts'][0]),'id':'F2'});p['uses'][0]['opposition']=['F2','a prose limitation'];p['relations']=[{'from':'F1','to':'F2','type':'OPPOSES'},{'from':'F2','to':'F1','type':'CONTRARY_ACCOUNT_RESOLVED','text':'full raw relationship'}]
  data=inputs(case,p);self.assertEqual(sum(x['encoded'] for x in data['graph']['relation_audit']),2);self.assertTrue(any(e[2]==6 for e in data['graph']['edges']));pair=data['ce_pairs'][0];node=next(n for n in data['graph']['nodes'] if n['id']=='C:U1');self.assertIn('full raw relationship',pair['right']);self.assertIn('full raw relationship',node['text']);self.assertIn('A testimony record supports',pair['right']);self.assertIn('A testimony record supports',node['text']);self.assertFalse(data['reference_used'])
  mentions=[n for n in data['graph']['nodes'] if n['kind']==4];self.assertEqual(len(mentions),sum(sum(v is not None and v!='' for v in f['bindings'].values()) for f in p['facts']));self.assertEqual(len({n['id'] for n in mentions}),len(mentions))
 def test_usable_not_truth_open_and_failure(self):
  s,c,q=self.bundle();s['premises'][next(iter(s['premises']))]['quote']=None;out=self.entry(s,c,q);self.assertEqual(out['run_status'],'OK');self.assertIn('QUOTE_NOT_A_STRING',json.dumps(out))
  s,c,q=self.bundle();s['model_uses']['c::a']['premise_state']='UNKNOWN';self.assertEqual(self.entry(s,c,q)['requests'][0]['answer'],'UNKNOWN')
  s,c,q=self.bundle();s['rules']['R@1']['operator']='OPEN_TEXT';s['contracts']['R@1']['rule_hash']=content_hash(s['rules']['R@1']);out=self.entry(s,c,q);self.assertEqual(out['requests'][0]['answer'],'UNKNOWN');self.assertIn('OPEN_LEGAL_INTERPRETATION_NOT_EXECUTED',json.dumps(out))
  with tempfile.TemporaryDirectory() as t:
   s.pop('rules');d=Path(t)/'run'
   with self.assertRaises(KeyError):run(s,c,q,d)
   self.assertIsNone(json.loads((d/'failure.json').read_text())['answer'])
 def test_prediction_delivery_keeps_unscored_pool_and_state(self):
  from scripts.proof_semantic_apply_v13 import apply
  s,c,q=self.bundle();s['model_uses']['c::a']['raw_use_id']='u1';s['model_uses']['c::b']['raw_use_id']='u2'
  original=s['model_uses']['c::a']['premise_state'];p=apply(s,[{'key':'x::u1','probabilities':[.01,.98,.01]}]);self.assertEqual(p['model_uses']['c::a']['premise_state'],original);self.assertEqual(p['model_uses']['c::b']['label'],s['model_uses']['c::b']['label']);self.assertEqual(len(p['model_uses']),2)
  self.assertEqual(self.entry(p,c,q)['requests'][0]['answer'],'UNKNOWN')
 def test_reversible_source_chunks_and_sort(self):
  case,p=self.example();case['segments'][0]['text']='x'*6010;case['segments'].reverse();r=recover(case,['DEMO:L1']);self.assertEqual([s['id'] for s in r['segments']],['DEMO:L1','DEMO:L2']);self.assertEqual(''.join(c['text'] for c in r['segments'][0]['chunks']),'x'*6010)
 def test_exact_attachment_hash_address_keeps_unknown_and_values(self):
  from legal_bench.proof_carrying.semantic_sources_v13 import resolve_record
  case={'case_id':'1','source_sha256':'saved','segments':[{'id':'IK-1:L2','source_document':'1','text':'The court recorded a denial.'}]}
  original={'refs':['turn0file0#IK-1:L2','turn0file0#IK-2:L2','turn0file0#IK-1:L3'],'label':'USABLE','quote':'recorded a denial','bindings':{'widow':'A'}}
  with tempfile.TemporaryDirectory() as t:
   task=Path(t)/'task.txt';task.write_text('[IK-1:L2]\nThe court recorded a denial.');mapped,ledger=resolve_record(original,case,task)
  self.assertEqual(mapped['refs'],['IK-1:L2','turn0file0#IK-2:L2','turn0file0#IK-1:L3']);self.assertEqual(mapped['quote'],original['quote']);self.assertEqual(mapped['bindings'],original['bindings']);self.assertEqual(mapped['label'],original['label']);self.assertEqual(len(ledger['mappings']),1);self.assertFalse(ledger['semantic_verified'])
if __name__=='__main__':unittest.main()
