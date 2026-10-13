"""Reviewers receive original definitions, not only opaque addresses."""
import copy,json,unittest
from scripts.proof_final_bindings_v20_8 import OUT,inputs,read
from legal_bench.proof_carrying import final_statement_review_v20_9_1 as core


class ReviewMaterialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case,old,_,_=inputs('569555');p=OUT/'cases/569555';q=OUT/'statement-pack-01/cases/569555'
        cls.frame=read(p/'frame-proposal.json');cls.bridge=read(p/'bridge.json')
        cls.task=core.final_task(cls.case,old,cls.bridge,cls.frame,read(p/'frame-review/parsed.json'),read(q/'proposal.json'),read(q/'source-review/parsed.json'))
        cls.plan=read(q/'generation/parsed.json')

    def test_every_origin_has_exact_original_definition(self):
        evidence=self.task['review_proxy']['verification_task']['review_context']['identity_review_evidence']
        old={r['id']:r['original'] for r in self.bridge['declarations'] if r['kind']=='OBJ'}
        for row in self.frame['actors']+self.frame['properties']:
            for key in row['origin_object_ids']:self.assertEqual(evidence['original_object_definitions'][key],old[key])
        self.assertIn('SRC:1',evidence['source_aliases'])

    def test_review_prompt_displays_definitions_and_complete_source(self):
        rt=core.review_task(self.task,self.plan,self.case)
        start=rt['prompt'].index('{"bindings":');end=rt['prompt'].index('\nOUTPUT SCHEMA:\n',start)
        p=json.loads(rt['prompt'][start:end]);self.assertTrue(p['request_and_rules']['identity_review_evidence']['original_object_definitions'])
        self.assertEqual(p['source'],[{'id':s['id'],'text':s['text']} for s in self.case['segments']])

    def test_identity_evidence_tampering_invalidates_task(self):
        task=copy.deepcopy(self.task);task['review_proxy']['verification_task']['review_context']['identity_review_evidence']['original_object_definitions']={}
        with self.assertRaises(ValueError):core.render(task,self.plan,self.case)

    def test_conservative_token_preflight_covers_every_observed_request(self):
        c=read(OUT/'engineering/token-budget-calibration-v2.json')
        self.assertEqual(len(c['calibration']),6)
        for row in c['calibration']:
            self.assertGreater(row['client_tokens'],1000)
            self.assertLessEqual(row['server_tokens'],(3*(row['client_tokens']+row['schema_tokens'])+1)//2+4096)


if __name__=='__main__':unittest.main()
