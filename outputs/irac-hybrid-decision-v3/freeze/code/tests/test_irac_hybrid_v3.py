import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from legal_bench.irac_application.hybrid_v3 import analyze,branches,legacy_replay
from legal_bench.irac_application.aligned_logic import evaluate
from scripts import irac_hybrid_v3 as entry

V=Path('outputs/gnn-irac-aligned-v2')
def load(p):return json.loads(Path(p).read_text())

def fixture():
 refs=[{'source_id':'law','quote':'A'}]
 t={'tests':[{'id':'T'}],'elements':[],'claims':[{'id':'C','expression':{'op':'REF','id':'T','source_refs':refs}}],'coverage_limits':[],'burdens':[],'scope':'synthetic'}
 s={k:{'text':k,'document_id':'c'} for k in ['s1','s2','law']}
 p={'bindings':[{'id':'b','claim_ids':['C'],'event':'one event','objects':'one person','stage':'review','refs':['s1']}],
 'evidence':[{'id':'e1','binding_id':'b','record':'reported operational conduct','statement_status':'TESTIMONY','refs':['s1'],'uses':[{'test_id':'T','branch_id':'','direction':'SUPPORT','use':'CONDITION_INFERENCE'}]},{'id':'e2','binding_id':'b','record':'prior court refuted disposition','statement_status':'PRIOR_COURT_FINDING','refs':['s2'],'uses':[{'test_id':'T','branch_id':'','direction':'OPPOSE','use':'CONDITION_INFERENCE'}]}],
 'limitations':[{'id':'LINK:note','evidence_ids':['e1'],'binding_id':'b','test_id':'T','branch_id':'','use':'CONDITION_INFERENCE','effect':'USE_BLOCK','reason':'does not establish legal transfer','refs':['s1']}],'conditions':[],'coverage_limits':[]}
 return p,t,s

class HybridTests(unittest.TestCase):
 def test_actual_analyze_independent_opposition_and_prior_stage(self):
  p,t,s=fixture();r=analyze(p,t,s,'c');self.assertEqual(r['conditions'][0]['program_assessment']['status'],'REFUTED');self.assertEqual(r['evidence_use_checks'][1]['statement_status'],'PRIOR_COURT_FINDING');self.assertFalse(r['legal_truth_verified']);self.assertEqual(r['evidence_use_checks'][0]['record_retained'],p['evidence'][0]['record'])
 def test_sole_limited_witness_not_proof(self):
  p,t,s=fixture();p['evidence']=p['evidence'][:1];r=analyze(p,t,s,'c');self.assertEqual(r['conditions'][0]['program_assessment']['status'],'UNRESOLVED')
 def test_opposition_not_deleted_no_vote(self):
  p,t,s=fixture();p['limitations']=[];p['evidence'].append(dict(p['evidence'][0],id='duplicate'));r=analyze(p,t,s,'c');self.assertTrue(r['conditions'][0]['program_assessment']['conflict']);self.assertEqual(r['conditions'][0]['program_assessment']['status'],'UNRESOLVED')
 def test_id_prefix_irrelevant(self):
  p,t,s=fixture();a=analyze(p,t,s,'c');p['limitations'][0]['id']='COMBO:note';b=analyze(p,t,s,'c');self.assertEqual(a['conditions'],b['conditions']);self.assertEqual(a['bindings'],b['bindings'])
 def test_or_not_blocked_by_other_branch_and_and_gap(self):
  t=branches(load(V/'templates/DRC_BONA_FIDE.json'));m=load(V/'sources/112400.json');s=m['sources'];p,_,_=fixture();tid='DRC_BONA_FIDE-C03';sid='IK-112400:L124:restored-v2';p['bindings'][0].update(claim_ids=['DRC_BONA_FIDE-CLAIM-01'],refs=[sid]);p['evidence']=p['evidence'][:1];p['evidence'][0].update(refs=[sid],statement_status='PARTY_CLAIM');p['evidence'][0]['uses'][0].update(test_id=tid,branch_id=tid+'/SELF');p['limitations'][0].update(test_id=tid,branch_id=tid+'/DEPENDENT',refs=[sid]);r=analyze(p,t,s,'112400');self.assertEqual(r['bindings'][0]['tests'][tid]['status'],'SUPPORTED');self.assertEqual(r['bindings'][0]['claims'][0]['result']['status'],'UNRESOLVED')
 def test_other_binding_never_combined(self):
  p,t,s=fixture();p['bindings'].append(dict(p['bindings'][0],id='b2',event='different event'));p['evidence'][1]['binding_id']='b2';r=analyze(p,t,s,'c');self.assertEqual(r['bindings'][0]['tests']['T']['status'],'UNRESOLVED');self.assertEqual(r['bindings'][1]['tests']['T']['status'],'REFUTED')
 def test_prior_not_accepted_target(self):
  p,t,s=fixture();p['evidence'][1]['uses'][0]['use']='TARGET_ACCEPTANCE';r=analyze(p,t,s,'c');self.assertIn('PRIOR_FINDING_NOT_TARGET_ACCEPTANCE',r['evidence_use_checks'][1]['blocked_by'])
 def test_address_failure_local(self):
  p,t,s=fixture();p['evidence'][0]['refs']=['missing'];r=analyze(p,t,s,'c');self.assertEqual(r['conditions'][0]['program_assessment']['status'],'REFUTED');self.assertFalse(r['evidence_use_checks'][0]['record_address_valid'])
 def test_real_188721101_operational_limit_does_not_erase_prior_record(self):
  g=load(V/'graphs/188721101.json');m=load(V/'sources/188721101.json');s=dict(m['sources']);s.update({x['source_id']:x for x in load(V/'sources/DRC_SUBLETTING-law.json')});p,t,_=fixture();tid='DRC_SUBLETTING_C04';p['bindings'][0].update(claim_ids=['DRC_SUBLETTING_CLAIM_01'],refs=['IK-188721101:L72:restored-v2'],objects='Ramesh Kumar / Bhagwan Dass / Shop15',event='brother arrangement');p['evidence'][0]['refs']=['IK-188721101:L81:restored-v2'];p['evidence'][1]['refs']=['IK-188721101:L83:restored-v2'];p['limitations'][0].update(test_id=tid,refs=p['evidence'][0]['refs']);
  for e in p['evidence']:e['uses'][0]['test_id']=tid
  r=analyze(p,branches(g['legal_structure']),s,'188721101');u=next(x for x in r['conditions'] if x['test_id']==tid);self.assertEqual(u['program_assessment']['opposes'],['e2']);self.assertEqual(u['program_assessment']['status'],'REFUTED');self.assertIn('Trial Court',s['IK-188721101:L83:restored-v2']['text'])
 def test_old_aggregate_cannot_supply_branch_labels(self):
  g=load(V/'graphs/112400.json');r=legacy_replay(g,{});u=next(x for x in r['units'] if x['test_id']=='DRC_BONA_FIDE-C03');self.assertEqual(u['replay_status'],'BRANCH_DETAIL_UNAVAILABLE');self.assertIsNone(u['branch_predictions'])
 def test_actual_run_entry_failure_null(self):
  class Fake:
   def run(self,*args,**kwargs):return {'run_status':'OUTPUT_TRUNCATED'}
  with tempfile.TemporaryDirectory() as d,patch.object(entry,'inputs',return_value=({'sources':{}}, {'tests':[]}, [])):
   r,_=entry.complete_slot(Fake(),'c','A','x',{},1,Path(d));self.assertIsNone(r['prediction']);self.assertEqual(r['run_status'],'OUTPUT_TRUNCATED');self.assertTrue((Path(d)/'result.json').is_file())
 def test_actual_proposal_entry_runs_checks(self):
  p,t,s=fixture();p['conditions']=[{'binding_id':'b','test_id':'T','evidence_ids':['e1'],'prediction':'PREDICT_REFUTED'}]
  class Fake:
   def run(self,*args,**kwargs):return {'run_status':'OK','schema_mask_calls':3}
  with tempfile.TemporaryDirectory() as d,patch.object(entry,'R',Path(d)),patch.object(entry,'inputs',return_value=({'sources':s},t,[])):
   out=Path(d)/'run';out.mkdir();(out/'parsed.json').write_text(json.dumps(p));r,_=entry.complete_slot(Fake(),'c','proposal','x',{},1,out);self.assertEqual(r['run_status'],'OK');self.assertEqual(load(Path(d)/'checks/c.json')['conditions'][0]['program_assessment']['status'],'REFUTED')
if __name__=='__main__':unittest.main()
