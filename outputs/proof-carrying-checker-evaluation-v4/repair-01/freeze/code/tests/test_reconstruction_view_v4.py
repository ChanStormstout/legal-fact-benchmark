import copy, unittest
from pathlib import Path
from legal_bench.proof_carrying.contracts import read_json
from legal_bench.proof_carrying.reconstruction_view_v4 import view

ROOT=Path(__file__).resolve().parents[1]/'outputs/proof-carrying-local-repair-v3/cases/789051/reviewed-reconstruction'

class DisplayTests(unittest.TestCase):
    def test_submitted_prose_never_becomes_checked_statement(self):
        s=read_json(ROOT/'snapshot.json');c=read_json(ROOT/'certificate.json');r=read_json(ROOT/'check.json')
        c['proposal']['requests'][0]['text']='The plaintiff owns the land.'
        r['requests'][0]['text']='The plaintiff owns the land.'
        q=view(s,c,r)['requests'][0]
        self.assertFalse(q['submitted_prose_semantically_checked'])
        self.assertEqual(q['submitted_prose'],'The plaintiff owns the land.')
        self.assertNotEqual(q['published_conditional_statement'],q['submitted_prose'])
        self.assertTrue(q['semantic_assumptions']);self.assertFalse(q['legal_approval'])

    def test_withheld_claim_is_not_published_as_success(self):
        s=read_json(ROOT/'snapshot.json');c=read_json(ROOT/'certificate.json');r=read_json(ROOT/'check.json')
        r['requests'][0].update(draft_status='INCOMPLETE_EXECUTION',answer=None)
        q=view(s,c,r)['requests'][0];self.assertIsNone(q['published_conditional_statement']);self.assertIsNone(q['state'])

    def test_display_rejects_mismatched_snapshot_and_predicate(self):
        s=read_json(ROOT/'snapshot.json');c=read_json(ROOT/'certificate.json');r=read_json(ROOT/'check.json')
        wrong=copy.deepcopy(s);wrong['case_id']='different'
        with self.assertRaises(ValueError):view(wrong,c,r)
        r['requests'][0]['predicate']='OWNERSHIP'
        with self.assertRaises(ValueError):view(s,c,r)

if __name__=='__main__':unittest.main()
