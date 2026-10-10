import copy
import json
import tempfile
import unittest
from pathlib import Path

from tests.test_proof_semantic_v12 import fixture
from legal_bench.proof_carrying.contracts import content_hash
from legal_bench.proof_carrying.semantic_calibration_v14 import apply_overlay
from legal_bench.proof_carrying.use_contract_v14 import inspect_use
from scripts.proof_semantic_run_v14 import run


def calibrated_fixture():
    s, cs, qs = fixture()
    s['sources']['s']['text'] = 'The court found that Ada entered Lot A. Rule permits the limited result.'
    s['premises']['f'].update(statement_status='COURT_FINDING', quote='The court found that Ada entered Lot A.', bindings=[{'role': 'subject', 'entity': 'Ada'}])
    cs[0]['bindings'] = [{'role': 'subject', 'entity': 'Ada'}]
    r = s['rules']['R@1']; r['stage'] = 'Appeal'
    for slot in r['slots']: slot['allowed_statuses'] = ['COURT_FINDING']
    s['contracts']['R@1']['rule_hash'] = content_hash(r)
    s['raw_proposal'] = {'uses': [{'id': 'u'+name, 'rule_premise': name, 'evidence_ids': ['f'], 'bindings': {'subject':'Ada'}, 'use_judgment':'USABLE', 'premise_state':'UNKNOWN'} for name in ['a','b']]}
    s['model_uses'] = {'c::'+name: {'raw_use_id':'u'+name, 'label':'USABLE', 'premise_state':'UNKNOWN', 'premise_judgment_basis':'Original P uncertainty'} for name in ['a','b']}
    s['relations'] = [{'from':'f','to':'a','type':'OPPOSES','text':'Preserved distinct opposing record'}]
    witness = {'refs':['s'], 'quote':'The court found that Ada entered Lot A.', 'reason':'Synthetic recorded court finding, not independent proof of entry.'}
    receipts = {}; declarations = {}
    for name in ['a','b']:
        witness = copy.deepcopy(witness)
        receipts[name] = {'id':'e'+name, 'case_id':'x', 'rule_ref':'R@1', 'premise_id':name, 'predicate_hash':content_hash('assertion'), 'state':'TRUE', 'statement_status':'COURT_FINDING', 'court_level':'Synthetic appellate court', 'stage':'Appeal', 'reason':'Recorded finding accepted for synthetic reconstruction', 'refs':['s'], 'quote':witness['quote'], 'source_witnesses':[witness], 'binding_witnesses':[{**witness,'role':'subject','variable':'subject','value':'Ada'}], 'raw_use_id':'u'+name,'original_evidence_ids':['f'], 'review_decision':'ACCEPT_FOR_RECONSTRUCTION', 'component_coverage':[{**witness, 'id':'whole'}]}
        declarations['u'+name] = {'premise_id':name, 'purpose':'RECONSTRUCT_COURT_PREMISE', 'direction':'SUPPORT', 'bindings':{'subject':'Ada'}, 'stage':'Appeal', 'source_status':'COURT_FINDING','source_witnesses':[witness], 'required_components':['whole']}
    policy = {'research_acceptance':True, 'formal_legal_approval':False, 'accepted_receipt_hashes':{r['id']:content_hash(r) for r in receipts.values()}}
    overlay = {'case_id':'x', 'original_snapshot_hash':content_hash(s), 'candidate_id':'c','premises':receipts,'use_declarations':declarations,'policy':policy}
    s, cs, _ = apply_overlay(s, cs, overlay)
    return s, cs, qs, policy


def renew_policy(s, policy):
    policy['accepted_receipt_hashes'] = {r['id']:content_hash(r) for r in s['external_premise_receipts'].values()}
    s['calibration_policy_hash'] = content_hash(policy)


class V14Tests(unittest.TestCase):
    def entry(self, s, cs, qs, policy):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)/'run'
            result = run(s, cs, qs, policy, dest)
            self.assertTrue((dest/'manifest.json').exists())
            self.assertTrue((dest/'checker.stdout.txt').exists())
            self.assertEqual(json.loads((dest/'checked.json').read_text()), result)
            return result

    def test_valid_entry_and_preserves_originals(self):
        s, cs, qs, p = calibrated_fixture(); old = copy.deepcopy(s)
        out = self.entry(s, cs, qs, p)
        self.assertEqual(out['requests'][0]['answer'], 'TRUE')
        self.assertEqual(s, old)
        self.assertFalse(out['formal_legal_approval'])
        self.assertEqual(out['all_original_opposition'], s['relations'])
        self.assertEqual(out['all_original_records'], ['f'])

    def test_eligibility_never_supplies_truth_and_opposition_is_usable(self):
        for purpose in ['REPORT_ASSERTION','PARTIAL_SUPPORT','PARTIAL_OPPOSITION','BACKGROUND']:
            s, cs, qs, p = calibrated_fixture()
            s['use_declarations']['ua'].update(purpose=purpose, direction='OPPOSE' if purpose=='PARTIAL_OPPOSITION' else 'CONTEXT')
            out = self.entry(s, cs, qs, p)
            audit = next(v for k,v in out['external_receipt_checks'].items() if k.endswith('::a'))['use_audit']
            self.assertTrue(audit['eligible_under_declared_review'])
            self.assertFalse(audit['can_supply_whole_premise'])
            self.assertEqual(out['requests'][0]['answer'], 'UNKNOWN')
        s, cs, qs, p = calibrated_fixture()
        s['external_premise_receipts']['a']['state'] = 'FALSE'
        s['use_declarations']['ua']['direction'] = 'OPPOSE'
        s['rules']['R@1']['slots'][0]['expected'] = 'FALSE'
        s['contracts']['R@1']['rule_hash'] = content_hash(s['rules']['R@1']); renew_policy(s,p)
        out = self.entry(s,cs,qs,p)
        self.assertEqual(out['requests'][0]['answer'],'TRUE')
        self.assertEqual(next(v for k,v in out['external_receipt_checks'].items() if k.endswith('::a'))['state'],'FALSE')

    def test_invalid_local_receipt_not_global_rejection(self):
        for mutation, code in [('object','EXTERNAL_OBJECT_MISMATCH'),('quote','EXTERNAL_SOURCE:'),('stage','EXTERNAL_PROCEDURAL_STAGE_MISMATCH'),('lineage','EXTERNAL_EVIDENCE_LINEAGE_MISMATCH'),('coverage','WHOLE_PREMISE_COMPONENT_COVERAGE_UNESTABLISHED')]:
            s,cs,qs,p = calibrated_fixture(); a=s['external_premise_receipts']['a']
            if mutation=='object': a['binding_witnesses'][0]['value']='Another Ada'
            if mutation=='quote': a['source_witnesses'][0]['quote']='The court did not find entry.'
            if mutation=='stage': a['stage']='Different trial'
            if mutation=='lineage': a['original_evidence_ids']=[]
            if mutation=='coverage': a['component_coverage']=[]
            renew_policy(s,p)
            out=self.entry(s,cs,qs,p); self.assertEqual(out['requests'][0]['answer'],'UNKNOWN');self.assertIn(code,json.dumps(out))
            s['rules']['R@1']['operator']='ANY';s['contracts']['R@1']['rule_hash']=content_hash(s['rules']['R@1'])
            self.assertEqual(self.entry(s,cs,qs,p)['requests'][0]['answer'],'TRUE')

    def test_no_assertion_hypothesis_or_final_conclusion_upgrade(self):
        for status in ['PARTY_CLAIM','FUTURE_CONDITIONAL','HYPOTHETICAL']:
            s,cs,qs,p=calibrated_fixture();s['use_declarations']['ua']['source_status']=status
            self.assertEqual(self.entry(s,cs,qs,p)['requests'][0]['answer'],'UNKNOWN')
        s,cs,qs,p=calibrated_fixture();s['sources']['s']['role']='DISPOSITION_ONLY'
        self.assertIn('EXTERNAL_FOREIGN_OR_DISPOSITION_SOURCE',json.dumps(self.entry(s,cs,qs,p)))
        s,cs,qs,p=calibrated_fixture();s['rules']['R@1']['conclusion_predicate']='assertion';qs[0]['predicate']='assertion';s['contracts']['R@1']['rule_hash']=content_hash(s['rules']['R@1'])
        self.assertIn('CIRCULAR_CONCLUSION_AS_PREMISE',json.dumps(self.entry(s,cs,qs,p)))

    def test_version_policy_missing_quotes_open_and_failure(self):
        s,cs,qs,p=calibrated_fixture();s['external_premise_receipts']['a']['rule_ref']='R@2';renew_policy(s,p)
        self.assertIn('RECEIPT_CASE_OR_VERSION_MISMATCH',json.dumps(self.entry(s,cs,qs,p)))
        s,cs,qs,p=calibrated_fixture();s['external_premise_receipts']['a']['state']='FALSE'
        self.assertIn('EXTERNAL_RECEIPT_NOT_IN_REVIEWED_POLICY_VERSION',json.dumps(self.entry(s,cs,qs,p)))
        s,cs,qs,p=calibrated_fixture();self.assertEqual(self.entry(s,cs,qs,{})['requests'][0]['answer'],'UNKNOWN')
        s,cs,qs,p=calibrated_fixture();s['premises']['f']['quote']=None
        out=self.entry(s,cs,qs,p);self.assertIsNone(s['premises']['f']['quote']);self.assertEqual(out['requests'][0]['answer'],'TRUE')
        # This accepted external court premise does not repair the raw null quote.
        s['rules']['R@1']['operator']='OPEN_TEXT';s['contracts']['R@1']['rule_hash']=content_hash(s['rules']['R@1'])
        self.assertIn('OPEN_LEGAL_INTERPRETATION_NOT_EXECUTED',json.dumps(self.entry(s,cs,qs,p)))
        del s['rules']
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)/'run'
            with self.assertRaises(KeyError): run(s,cs,qs,p,dest)
            self.assertIsNone(json.loads((dest/'failure.json').read_text())['answer'])

if __name__ == '__main__': unittest.main()
