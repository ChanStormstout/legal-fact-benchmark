"""Entry-level scope metadata fix; original v2 freeze and output preserved."""
import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from tests.test_proof_realcase_v2 import fixture,ROOT
from legal_bench.proof_carrying.contracts import content_hash,byte_hash,write_once
from legal_bench.proof_carrying.realcase_engine import propose

class ScopeTest(unittest.TestCase):
    def run_scope(self,compatible=True,stale=False,missing=False):
        s,d=fixture()
        for r in s['rules'].values():r['jurisdiction']='Synthetic jurisdiction; descriptive scope, not a canonical code.'
        for k,r in s['rules'].items():s['reviews']['rules'][k]['subject_hash']=content_hash(r)
        s['scope_reviews']={k:{'subject_hash':content_hash(r),'jurisdiction_compatible':compatible,'stage_compatible':True,'basis':'Synthetic scope fixture'} for k,r in s['rules'].items()}
        if stale:s['scope_reviews']['R1@1']['subject_hash']='stale'
        if missing:s['scope_reviews']={}
        if stale or missing:
            for t in d['steps']:t['proposed_state']='UNKNOWN'
            d['requests'][0]['proposed_state']='UNKNOWN'
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);write_once(p/'s.json',s);write_once(p/'c.json',propose(s,d))
            write_once(p/'m.json',{'snapshots':{'S1':{'path':'s.json','sha256':byte_hash(p/'s.json')}}})
            x=subprocess.run([sys.executable,str(ROOT/'scripts/check_realcase_certificate_v2_1.py'),str(p/'c.json'),'--manifest',str(p/'m.json')],text=True,capture_output=True)
            self.assertEqual(x.returncode,0,x.stderr);return json.loads(x.stdout)
    def test_descriptive_jurisdiction_needs_separate_scope_review(self):
        self.assertEqual(self.run_scope()['requests'][0]['answer'],'TRUE')
        self.assertEqual(self.run_scope(missing=True)['requests'][0]['answer'],'UNKNOWN')
    def test_rejected_or_stale_scope_never_silent_accept(self):
        r=self.run_scope(compatible=False);self.assertIn('RULE_SCOPE_MISMATCH',r['steps']['T1']['errors'])
        self.assertEqual(self.run_scope(stale=True)['requests'][0]['answer'],'UNKNOWN')

if __name__=='__main__':unittest.main()
