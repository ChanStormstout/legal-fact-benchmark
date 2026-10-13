"""Multiple uses retain identical facts; real cached plans are not new generations."""
import copy
import json
import unittest
from scripts.proof_final_bindings_v20_8 import OUT,inputs,read
from legal_bench.proof_carrying import final_render_v20_8_3 as core


class MultipleUseTests(unittest.TestCase):
    def test_three_unchanged_real_plans_pass_repaired_consumer(self):
        for cid in ['1954254','569555','1187427']:
            case,old,_,_=inputs(cid);p=OUT/'cases'/cid
            task=core.final_task(case,old,read(p/'bridge.json'),read(p/'frame-proposal.json'),read(p/'frame-review/parsed.json'))
            generated=OUT/'clause-render-03/cases'/cid
            original=read(generated/'task.json');plan=read(generated/'generation/parsed.json')
            self.assertEqual(task['clauses'],original['clauses']);self.assertEqual(task['schema'],original['schema'])
            answer=core.render(task,plan,case)
            shared=set(plan['ground_claim_ids'])&set(plan['counterargument_claim_ids'])
            self.assertTrue(shared)
            for key in shared:
                ground=next(r for r in answer['grounds'] if r['claim_ids']==[key])
                counter=next(r for r in answer['counterarguments'] if r['claim_ids']==[key])
                self.assertEqual(ground['explanation'],counter['treatment'])
                self.assertEqual(ground['explanation'],task['clauses'][key]['text'])
            result=core.accept_final(task,json.dumps(plan),'OK',case=case)
            self.assertEqual(result['contract_status'],'PENDING_WHOLE_ANSWER_SOURCE_REVIEW')
            self.assertIsNone(result['answer'])
            self.assertEqual(answer['assumptions'],[])
            self.assertEqual(answer['case_frame'],task['frame'])

    def test_unknown_and_new_free_text_still_rejected(self):
        cid='1187427';case,old,_,_=inputs(cid);p=OUT/'cases'/cid
        task=core.final_task(case,old,read(p/'bridge.json'),read(p/'frame-proposal.json'),read(p/'frame-review/parsed.json'))
        plan=read(OUT/'clause-render-03/cases'/cid/'generation/parsed.json')
        for bad in [dict(plan,conclusion='Fabricated'),dict(plan,reasoning_claim_ids=['C999'])]:
            self.assertIsNone(core.accept_final(task,json.dumps(bad),'OK',case=case)['answer'])


if __name__=='__main__':unittest.main()
