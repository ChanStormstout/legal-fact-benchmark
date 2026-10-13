"""Injected reviews exercise code; they are not semantic accuracy evidence."""
import copy,json,unittest
from scripts.proof_final_bindings_v20_8 import OUT,inputs,read
from legal_bench.proof_carrying import final_statement_pack_v20_9 as core


class PackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case,cls.old,_,_=inputs('1187427');d=OUT/'cases/1187427'
        cls.frame=read(d/'frame-proposal.json');cls.bridge=read(d/'bridge.json');cls.frame_review=read(d/'frame-review/parsed.json')
        cls.pack=read(OUT/'statement-pack-01/cases/1187427/proposal.json')
        rt=core.pack_review_task(cls.case,cls.frame,cls.pack,cls.bridge['conditional_rules'])
        cls.review={**rt['bindings'],'verdicts':{r['id']:{'label':'SUPPORTED','refs':r['refs'],'reason':'Injected engineering fixture, not semantic gold.'} for r in cls.pack['records']}}
        cls.task=core.final_task(cls.case,cls.old,cls.bridge,cls.frame,cls.frame_review,cls.pack,cls.review)
        cls.plan={'record_order':[r['id'] for r in cls.pack['records']]}

    def test_pack_reporting_court_is_not_performing_actor(self):
        rows=[r for r in self.pack['records'] if any(b['role']=='REPORTING_COURT' and b['actor_id'] not in r['actor_ids'] for b in r['role_bindings'])]
        self.assertTrue(rows);self.assertTrue(core.check_pack(self.case,self.frame,self.pack))

    def test_court_cannot_be_bound_to_landlord(self):
        p=copy.deepcopy(self.pack);r=p['records'][0];r['role_bindings']=[{'role':'ISSUING_COURT','actor_id':self.frame['actors'][0]['id']}];r['actor_ids']=[self.frame['actors'][0]['id']]
        with self.assertRaisesRegex(ValueError,'COURT_ROLE'):core.check_pack(self.case,self.frame,p)

    def test_cross_case_ids_and_empty_source_rejected(self):
        p=copy.deepcopy(self.pack);p['records'][0]['actor_ids']=['1954254/A01']
        with self.assertRaises(ValueError):core.check_pack(self.case,self.frame,p)
        p=copy.deepcopy(self.pack);p['records'][0]['refs']=[]
        with self.assertRaises(ValueError):core.check_pack(self.case,self.frame,p)

    def test_changed_statement_and_computation_invalidate_review(self):
        p=copy.deepcopy(self.pack);p['records'][0]['text']+=' Changed.'
        with self.assertRaises(ValueError):core.final_task(self.case,self.old,self.bridge,self.frame,self.frame_review,p,self.review)
        b=copy.deepcopy(self.bridge);b['conditional_rules'][0]['conditional_result']='TRUE'
        with self.assertRaises(ValueError):core.final_task(self.case,self.old,b,self.frame,self.frame_review,self.pack,self.review)

    def test_unresolved_record_cannot_dispatch(self):
        review=copy.deepcopy(self.review);review['verdicts'][next(iter(review['verdicts']))]['label']='UNRESOLVED'
        with self.assertRaisesRegex(ValueError,'NOT_SOURCE_REVIEW_ACCEPTED'):core.final_task(self.case,self.old,self.bridge,self.frame,self.frame_review,self.pack,review)

    def test_model_cannot_drop_duplicate_or_add_prose(self):
        for plan in [dict(record_order=self.plan['record_order'][:-1]),dict(record_order=self.plan['record_order'][:-1]+self.plan['record_order'][:1]),dict(self.plan,conclusion='New unreviewed prose')]:
            with self.assertRaises(ValueError):core.render(self.task,plan,self.case)

    def test_all_text_and_bindings_preserved(self):
        a=core.render(self.task,self.plan,self.case)
        for r in self.pack['records']:
            if r['section']=='SUMMARY':self.assertIn(r['text'],a['conclusion'])
            elif r['section']=='LIMITATION':self.assertIn(r['text'],a['gaps'])
            else:
                rows=a['grounds'] if r['section']=='GROUND' else a['counterarguments'];row=next(x for x in rows if x['claim_ids']==[r['id']])
                self.assertEqual(row.get('explanation',row.get('treatment')),r['text']);self.assertEqual(row['actor_ids'],r['actor_ids']);self.assertEqual(row['property_ids'],r['property_ids'])
        self.assertEqual(a['case_frame'],self.frame);self.assertEqual(a['assumptions'],[])

    def test_every_binding_is_in_dependency_closure(self):
        book=self.task['review_proxy']['verification_task']['claim_registry']['accepted']
        for r in self.pack['records']:
            self.assertTrue(book[r['id']]['dependencies'])
            self.assertTrue(all(k in book for k in book[r['id']]['dependencies']))

    def test_source_checked_pack_does_not_skip_final_review(self):
        result=core.accept_final(self.task,json.dumps(self.plan),'OK',case=self.case)
        self.assertEqual(result['contract_status'],'PENDING_WHOLE_ANSWER_SOURCE_REVIEW');self.assertIsNone(result['answer'])

    def test_technical_failure_remains_null(self):
        result=core.accept_final(self.task,'{','OUTPUT_TRUNCATED',case=self.case)
        self.assertIsNone(result['answer']);self.assertEqual(result['contract_status'],'GENERATION_FAILED')


if __name__=='__main__':unittest.main()
