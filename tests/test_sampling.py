import unittest
from legal_bench.sampling import candidate_queue, select_screened, reviewed_dispute_groups
from legal_bench.experiment import check_manifest


class SamplingTests(unittest.TestCase):
    def records(self):
        return [dict(doc_id=str(i), title='Case ' + str(i), url='url', facts='Tenant faces eviction', issues='') for i in range(125)]

    def decisions(self, queue):
        return [dict(case_id=r['case_id'], state='ELIGIBLE', evidence='p1: tenancy eviction request',
                     source_review_sha256='source hash', source_completeness='VERIFIED_FULL',
                     dispute_group='g' + r['case_id'], group_review_state='REVIEWED') for r in queue['cases']]

    def test_order_is_outcome_blind_and_resumable(self):
        records = self.records()
        q = candidate_queue(records, ['0','1','2','3','4'])
        for r in records:
            r['conclusion'] = 'different outcome'
            r['courts_reasoning'] = 'new explanation'
        updated = candidate_queue(list(reversed(records)), ['0','1','2','3','4'])
        self.assertEqual([r['case_id'] for r in q['cases']], [r['case_id'] for r in updated['cases']])
        self.assertEqual(len(q['cases']), 120)
        self.assertTrue(all(r['state'] == 'CANDIDATE_NOT_ELIGIBLE' for r in q['cases']))

    def test_replacement_preserves_order_and_dispute_independence(self):
        q = candidate_queue(self.records(), ['0','1','2','3','4'])
        q['development_dispute_groups'] = ['d0','d1','d2','d3','d4']
        ds = self.decisions(q)
        ds[0]['state'] = 'INELIGIBLE'
        ds[1]['dispute_group'] = 'd0'
        ds[3]['dispute_group'] = ds[2]['dispute_group']
        m = select_screened(q, ds)
        self.assertEqual(len(m['cases']), 100)
        self.assertEqual(len(m['excluded']), 3)
        self.assertEqual(m['cases'][0]['case_id'], q['cases'][2]['case_id'])
        self.assertEqual(m['next_rank'], 104)

    def test_pending_rank_cannot_be_skipped_and_summaries_cannot_be_full_source(self):
        q = candidate_queue(self.records(), ['0','1','2','3','4'])
        q['development_dispute_groups'] = ['d0','d1','d2','d3','d4']
        ds = self.decisions(q)
        with self.assertRaises(ValueError): select_screened(q, ds[1:])
        ds[0]['source_completeness'] = 'EXTRACTED_FIELDS_ONLY'
        with self.assertRaises(ValueError): select_screened(q, ds)

    def test_companion_dispute_leakage_cannot_hide_behind_different_primary_groups(self):
        q = candidate_queue(self.records(), ['0','1','2','3','4'])
        q['development_dispute_groups'] = ['d0','d1','d2','d3','d4']
        ds = self.decisions(q)
        ds[0].update(multi_dispute_document=True, associated_dispute_groups=[ds[0]['dispute_group'], 'companion'])
        ds[1]['associated_dispute_groups'] = [ds[1]['dispute_group'], 'companion']
        ds[2]['associated_dispute_groups'] = [ds[2]['dispute_group'], 'd0']
        selected = select_screened(q, ds)
        self.assertEqual(len(selected['excluded']), 2)
        self.assertEqual(len(selected['cases']), 100)
        for r in ds[:2]:
            r.update(split='check', eligibility_evidence='source', group_review='reviewed')
        with self.assertRaises(ValueError): check_manifest({'cases':ds[:2]})

    def test_common_judgment_requires_companion_group_registration(self):
        with self.assertRaises(ValueError):
            reviewed_dispute_groups({'dispute_group':'primary','multi_dispute_document':True})
        self.assertEqual(reviewed_dispute_groups({'dispute_group':'primary','associated_dispute_groups':['primary','other']}), {'primary','other'})
