import json, tempfile, unittest
from pathlib import Path
from legal_bench.rules_verdict_v1.rule_transfer_v16 import inspect_reply, schema, EXAMPLE, retrieve

class RuleTransferTests(unittest.TestCase):
    def setUp(self):
        self.source = {'case_id':'FICTIONAL','metadata':{'year':2000},'segments':[{'id':'EX-S1','text':'Original unchanged source'}]}
        self.bundle = json.loads(json.dumps(EXAMPLE['answer']))
    def test_source_status_preserved_and_full_text_restored(self):
        self.bundle['rule_cards'][0]['source_kind']='PRIMA_FACIE_RESERVED'
        result,check=inspect_reply('```json\n'+json.dumps(self.bundle)+'\n```',self.source)
        self.assertEqual(result,self.bundle)
        self.assertEqual(check['restored_sources'][0]['sources'],self.source['segments'])
        self.assertFalse(check['semantic_certification'])
    def test_invalid_or_missing_evidence_not_repaired(self):
        for evidence in [[],['not-a-source']]:
            self.bundle['rule_cards'][0]['evidence']=evidence
            with self.assertRaises(ValueError):inspect_reply(json.dumps(self.bundle),self.source)
    def test_retrieval_keeps_provenance_without_applicability_claim(self):
        with tempfile.TemporaryDirectory() as d:
            result=retrieve([self.bundle],{'FICTIONAL':self.source},Path(d)/'index.sqlite','waiver storage')
            self.assertEqual(len(result['candidates']),1)
            self.assertFalse(result['legal_applicability_confirmed'])
            self.assertEqual(result['units'][0]['source']['evidence'],['EX-S1'])
    def test_output_with_extra_explanation_is_not_silently_repaired(self):
        with self.assertRaises(ValueError):inspect_reply(json.dumps(self.bundle)+' More advice.',self.source)

if __name__=='__main__':unittest.main()
