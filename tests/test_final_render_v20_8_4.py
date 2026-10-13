"""A source-supported report of rejected reasoning is not an adopted premise."""
import json
import unittest
from scripts.proof_final_bindings_v20_8 import OUT,inputs,read
from legal_bench.proof_carrying import final_render_v20_8_4 as core


class SummaryAttributionTests(unittest.TestCase):
    def test_every_summary_clause_keeps_original_status_and_stage(self):
        for cid in ['1954254','569555','1187427']:
            case,old,_,_=inputs(cid);p=OUT/'cases'/cid
            task=core.final_task(case,old,read(p/'bridge.json'),read(p/'frame-proposal.json'),read(p/'frame-review/parsed.json'))
            plan=read(OUT/'clause-render-03/cases'/cid/'generation/parsed.json')
            answer=core.render(task,plan,case)
            for key in dict.fromkeys(plan['disposition_claim_ids']+plan['reasoning_claim_ids']):
                c=task['clauses'][key]
                self.assertIn(c['status'].replace('_',' ').capitalize()+' ('+c['stage']+'): '+core.sentence(c['text']),answer['conclusion'])
            self.assertEqual(answer['case_frame'],task['frame'])
            self.assertGreater(len(answer['conclusion']),480)
            self.assertEqual(core.accept_final(task,json.dumps(plan),'OK',case=case)['contract_status'],'PENDING_WHOLE_ANSWER_SOURCE_REVIEW')

    def test_rejected_lower_court_view_cannot_become_unqualified_law(self):
        cid='1954254';case,old,_,_=inputs(cid);p=OUT/'cases'/cid
        task=core.final_task(case,old,read(p/'bridge.json'),read(p/'frame-proposal.json'),read(p/'frame-review/parsed.json'))
        plan=read(OUT/'clause-render-03/cases'/cid/'generation/parsed.json');answer=core.render(task,plan,case)
        self.assertIn('Reported lower court reasoning (',answer['conclusion'])
        self.assertIn('Landlord claim reported (',answer['conclusion'])
        self.assertIn(task['clauses']['C085']['text'],answer['conclusion'])


if __name__=='__main__':unittest.main()
