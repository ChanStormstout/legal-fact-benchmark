"""Literal rendering controls. Injected source reviews are only program fixtures."""
import copy
import json
import unittest
from legal_bench.proof_carrying import final_render_v20_8_2 as core
from scripts.proof_final_bindings_v20_8 import OUT, inputs, read
from test_final_bindings_v20_8 import injected


class LiteralRenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case, old, _, _ = inputs('569555')
        d=OUT/'cases/569555'
        bridge, frame=read(d/'bridge.json'),read(d/'frame-proposal.json')
        cls.task=core.final_task(cls.case,old,bridge,frame,injected(cls.case,frame,bridge))
        cls.key=next(k for k,c in cls.task['clauses'].items() if c['kind']=='ATTRIBUTION')
        cls.plan={'request_id':'Q1','disposition_claim_ids':cls.task['dispositions'],
                  'reasoning_claim_ids':[cls.key],'ground_claim_ids':[cls.key],
                  'counterargument_claim_ids':[]}

    def test_no_new_prose_channel(self):
        plan=copy.deepcopy(self.plan);plan['conclusion']='The landlord is the High Court.'
        with self.assertRaises(ValueError):core.render(self.task,plan,self.case)

    def test_no_unreviewed_clause(self):
        plan=copy.deepcopy(self.plan);plan['ground_claim_ids']=['C999']
        with self.assertRaises(ValueError):core.render(self.task,plan,self.case)

    def test_disposition_cannot_be_omitted(self):
        plan=copy.deepcopy(self.plan);plan['disposition_claim_ids']=[]
        with self.assertRaises(ValueError):core.render(self.task,plan,self.case)

    def test_duplicate_and_contradictory_assignment_rejected(self):
        plan=copy.deepcopy(self.plan);plan['ground_claim_ids']=[self.key,self.key]
        with self.assertRaises(ValueError):core.render(self.task,plan,self.case)
        plan=copy.deepcopy(self.plan);plan['counterargument_claim_ids']=[self.key]
        with self.assertRaisesRegex(ValueError,'CONTRADICTORY'):core.render(self.task,plan,self.case)

    def test_render_uses_exact_reviewed_clauses(self):
        answer=core.render(self.task,self.plan,self.case)
        self.assertEqual(answer['grounds'][0]['explanation'],self.task['clauses'][self.key]['text'])
        self.assertEqual(answer['case_frame'],self.task['frame'])
        expected=' '.join(core.sentence(self.task['clauses'][k]['text']) for k in self.task['dispositions']+[self.key])
        self.assertEqual(answer['conclusion'],expected)

    def test_all_reviewed_attributions_remain_visible(self):
        answer=core.render(self.task,self.plan,self.case)
        visible={r['claim_ids'][0] for group in ['grounds','counterarguments','source_attribution_appendix'] for r in answer[group]}
        expected={k for k,c in self.task['clauses'].items() if c['kind']=='ATTRIBUTION'}
        self.assertTrue(expected<=visible)

    def test_appendix_is_not_relabelled_counterargument(self):
        answer=core.render(self.task,self.plan,self.case)
        self.assertEqual(answer['counterarguments'],[])
        self.assertTrue(answer['source_attribution_appendix'])
        for r in answer['source_attribution_appendix']:
            c=self.task['clauses'][r['claim_ids'][0]]
            self.assertEqual(r['statement_status_and_stage'],c['status']+'; '+c['stage'])

    def test_whole_review_includes_appendix_claims(self):
        rt=core.review_task(self.task,self.plan,self.case)
        start=rt['prompt'].index('{"bindings":');end=rt['prompt'].index('\nOUTPUT SCHEMA:\n',start)
        payload=json.loads(rt['prompt'][start:end])
        self.assertEqual(payload['source'],[{'id':s['id'],'text':s['text']} for s in self.case['segments']])
        answer=payload['candidate']
        for r in answer['source_attribution_appendix']:
            self.assertIn(r['claim_ids'][0],payload['reviewed_claims']['accepted'])

    def test_whole_review_still_required(self):
        result=core.accept_final(self.task,json.dumps(self.plan),'OK',case=self.case)
        self.assertEqual(result['contract_status'],'PENDING_WHOLE_ANSWER_SOURCE_REVIEW')
        self.assertIsNone(result['answer'])

    def test_failed_transport_is_not_unknown(self):
        result=core.accept_final(self.task,'{','OUTPUT_TRUNCATED',case=self.case)
        self.assertEqual(result['contract_status'],'GENERATION_FAILED');self.assertIsNone(result['answer'])

    def test_reviewed_clause_mutation_is_rejected(self):
        task=copy.deepcopy(self.task);task['clauses'][self.key]['text']='A substituted court and actor.'
        with self.assertRaisesRegex(ValueError,'TASK_CHANGED'):core.render(task,self.plan,self.case)


if __name__=='__main__':unittest.main()
