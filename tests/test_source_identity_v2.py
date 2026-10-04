import tempfile
import unittest
from pathlib import Path
from legal_bench.rules_verdict_v1.source_identity_v2 import parse_responses, merge_windows, validate_view, validate_submission


def block(cid, lines, total=2):
    return 'Case %s (https://indiankanoon.org/doc/%s/)\nref Content type: text/html; Source: open({}); Total lines: %d\n%s\n' % (cid,cid,total,'\n'.join('L%d: %s'%x for x in lines))

class IdentityTest(unittest.TestCase):
    def test_actual_contamination_reproduced(self):
        p=Path('outputs/rules-verdict-v22-scope-preparation/search/v22_moreviews.txt')
        docs=merge_windows(parse_responses(p.read_text(),p))
        a=docs['34625760']; b=docs['157278563']
        self.assertFalse(any(s['original_line']==192 for s in a['segments']))
        self.assertTrue(any('appeal is accordingly dismissed' in s['text'] for s in b['segments']))
        import json
        old=json.loads(Path('outputs/rules-verdict-v23-uniform-retrieval/sources/34625760-allowed.json').read_text())
        with self.assertRaisesRegex(ValueError,'SOURCE_TEXT_MISMATCH|SOURCE_ADDRESS_MISSING'):
            validate_view(old,a,require_complete=False)
    def test_citation_is_not_boundary(self):
        raw=block('1',[(0,'Cites Case 2 (https://indiankanoon.org/doc/2/)'),(1,'The court discusses Case 2.')])
        self.assertEqual(list(merge_windows(parse_responses(raw,'unused'))),['1'])
    def test_overlap_and_submission(self):
        raw=block('1',[(0,'first')])+block('1',[(0,'first'),(1,'second')])
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'raw.txt';p.write_text(raw);d=merge_windows(parse_responses(raw,p))['1']
            self.assertEqual(d['status'],'COMPLETE_RENDERING'); self.assertEqual(len(d['segments'][0]['provenance']),2)
            v={'case_id':'1','segments':d['segments']}
            validate_submission('IK-1:L0 first IK-1:L1 second',v,d)
            with self.assertRaisesRegex(ValueError,'OMISSION'):validate_submission('first',v,d)
    def test_inline_renderer_address(self):
        raw=block('1',[(0,'a  L1: '),(2,'b')],total=3)
        d=merge_windows(parse_responses(raw,'unused'))['1']
        self.assertEqual(d['status'],'COMPLETE_RENDERING')
        self.assertEqual(d['segments'][0]['text'],'a ')
        self.assertEqual(d['segments'][1]['text'],'')
    def test_conflict_missing_identity(self):
        d=merge_windows(parse_responses(block('1',[(0,'a')])+block('1',[(0,'b')]),'unused'))['1']
        self.assertEqual(d['status'],'CONFLICT')
        d=merge_windows(parse_responses(block('1',[(0,'a')]),'unused'))['1']
        with self.assertRaisesRegex(ValueError,'INCOMPLETE'):validate_view({'case_id':'1','segments':d['segments']},d)
        with self.assertRaisesRegex(ValueError,'IDENTITY'):parse_responses('unknown body','unused')

if __name__=='__main__':unittest.main()
