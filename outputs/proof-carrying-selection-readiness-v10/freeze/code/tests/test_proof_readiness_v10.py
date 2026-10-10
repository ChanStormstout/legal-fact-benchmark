import copy,json,shutil,tempfile,unittest
from pathlib import Path
from scripts import proof_readiness_v10 as app
from legal_bench.proof_carrying.selection_v10 import eligibility,load_contracts,revise_addresses,oracle_frontier
from legal_bench.proof_carrying.contracts import content_hash
class Readiness(unittest.TestCase):
 def test_common_filter(self):
  rr,ff,ss,vc,mm,cc,cs,tt=app.prepare_case('789051');ct=load_contracts(app.OUT/'contracts/registry.json',rr);fi={p['id']:p for p in ff['premises']}
  rows=eligibility(cs,rr,fi,ss,ct);self.assertTrue(any(any('NONFACT_AS_FACT' in e for e in r['errors']) for r in rows))
  c=copy.deepcopy(cs[0]);x=next(x for x in c['inputs'] if x['kind']=='PREMISE');p=copy.deepcopy(fi[x['id']]);p['statement_status']='UNKNOWN';fi[x['id']]=p
  row=eligibility([c],rr,fi,ss,ct)[0];self.assertIn('STATUS_UNKNOWN:'+p['id'],row['pending'])
 def test_address_not_semantics(self):
  ss={'a':{'document':'d','document_role':'TARGET','original_line':1,'text':'He did not transfer possession.'},'b':{'document':'d','document_role':'TARGET','original_line':2,'text':'Other record.'}}
  ref={'premise_reviews':[{'id':'p','quote':'He did not transfer possession.','refs':['b'],'decision':'DEFER'}]}
  out,log=revise_addresses(ref,ss);self.assertEqual(out['premise_reviews'][0]['decision'],'DEFER');self.assertIn('a',out['premise_reviews'][0]['refs']);self.assertEqual(ref['premise_reviews'][0]['refs'],['b'])
  ref['premise_reviews'][0]['quote']='He did transfer possession.';out,log=revise_addresses(ref,ss);self.assertEqual(out,ref)
 def test_oracle_shared_budget(self):
  ck={'steps':{'s1':{'dependencies':[]},'s2':{'dependencies':[{'kind':'STEP','id':'s1'}]},'s3':{'dependencies':[{'kind':'STEP','id':'s1'}]}},'requests':[{'id':'q2','step_id':'s2','answer':'TRUE','errors':[]},{'id':'q3','step_id':'s3','answer':'TRUE','errors':[]}]};args=(ck,{'q2':'Q2','q3':'Q3'},{'s1':'c1','s2':'c2','s3':'c3'})
  self.assertEqual(len(oracle_frontier(*args,budget=2)['covered_requests']),1);self.assertEqual(len(oracle_frontier(*args,budget=3)['covered_requests']),2)
 def test_real_entry_and_macro(self):
  root=app.OUT
  with tempfile.TemporaryDirectory() as td:
   dest=Path(td);shutil.copytree(root/'contracts',dest/'contracts');shutil.copytree(root/'prepared',dest/'prepared');app.OUT=dest
   try:
    result=app.run_case('840688','simple',app.prepare_case('840688'));self.assertEqual(result['requests'],2)
    ck=json.loads((dest/'results/simple/840688/checked.json').read_text());self.assertEqual(ck['status'],'COMPLETED')
    from legal_bench.proof_carrying.checker_v10 import check_payload
    from legal_bench.proof_carrying.contracts_v10 import propose
    snap=json.loads((dest/'results/simple/840688/snapshot.json').read_text());der=json.loads((dest/'results/simple/840688/derivation.json').read_text())
    for slots in snap['coverage_contracts'].values():
     for cov in slots.values():cov['mode']='UNRESOLVED'
    changed=check_payload(propose(snap,der),snap);self.assertFalse(any(q.get('answer')=='TRUE' for q in changed['requests']))
   finally:app.OUT=root
if __name__=='__main__':unittest.main()
