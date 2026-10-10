import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from legal_bench.proof_carrying.checker import check
from legal_bench.proof_carrying.contracts import content_hash, read_json, validate_certificate
from legal_bench.proof_carrying.engine import propose
from legal_bench.proof_carrying.teaching import build, patch_record, validate_revision
from scripts.proof_teaching_v1 import run_demo


class TeachingCertificateTest(unittest.TestCase):
    def test_actual_entry_and_all_mutations(self):
        with tempfile.TemporaryDirectory() as d:
            rows=run_demo(Path(d))
            self.assertGreaterEqual(len(rows), 25)
            self.assertTrue(all(r['matches_expected'] for r in rows), rows)
            first=read_json(Path(d)/'runs/S1-specific-mismatch/checker_result.json')
            second=read_json(Path(d)/'runs/S2-corrected-coverage/checker_result.json')
            self.assertEqual(first['requests'][0]['result'],'FALSE')
            self.assertEqual(second['requests'][0]['result'],'TRUE')
            self.assertFalse(second['legal_approved'])
            self.assertTrue(read_json(Path(d)/'dependency-index.json')['old_premises_unchanged'])

    def test_production_cannot_adopt_demo_approval(self):
        with tempfile.TemporaryDirectory() as d:
            s,_,r,p=build(d); c=propose(s,r,p,['P1','P2'])
            c['mode']='LEGAL'
            result=check(c,d,mode='LEGAL')
            self.assertEqual(result['reason'],'NO_APPROVED_PRODUCTION_LEGAL_RULES')
            self.assertFalse(result['legal_approved'])

    def test_additive_patch_and_exact_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            s,t,r,p=build(d)
            self.assertEqual(validate_revision(s,t,patch_record(s,t))['added_premises'],['P4'])
            changed=copy.deepcopy(t);changed['propositions']['P1']['interval'][1]='2026-10-13'
            with self.assertRaisesRegex(ValueError,'REWRITES_EXISTING'):
                validate_revision(s,changed,patch_record(s,changed))
            doc=Path(d)/'documents/E1.txt'
            doc.write_bytes(doc.read_bytes().replace(b'\n',b'\r\n'))
            self.assertEqual(check(propose(s,r,p,['P1','P2']),d)['steps'][0]['reason'],'SOURCE_DOCUMENT_CHANGED')

    def test_checker_does_not_call_engine_or_spectral(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/'legal_bench/proof_carrying/checker.py').read_text()
        for forbidden in ('from .engine','import numpy','aligned_logic','import spectral'):
            self.assertNotIn(forbidden,text)
        # The same serialized proposal is accepted/rejected without recomputation
        # by the generator, so corrupted generator truth claims cannot pass.
        with tempfile.TemporaryDirectory() as d:
            s,_,r,p=build(d); c=propose(s,r,p,['P1','P2'])
            original=content_hash(c)
            self.assertEqual(check(c,d)['status'],'CHECKED')
            self.assertEqual(content_hash(c),original)
            c['steps'][0]['proposed_result']='TRUE'
            self.assertEqual(check(c,d)['status'],'INVALID')

    def test_multiple_requests_do_not_convert_blocker_to_global_absence(self):
        with tempfile.TemporaryDirectory() as d:
            s,_,r,p=build(d); c=propose(s,r,p,['P1','P2'])
            c['requests'].append({'id':'Q2','step_id':'T1','claim':'NO_AUTHORIZATION_EXISTS','proposed_result':'TRUE'})
            result=check(c,d)
            self.assertEqual([x['status'] for x in result['requests']],['CHECKED','INCOMPLETE'])
            self.assertEqual(result['status'],'MIXED')

    def test_content_pins_and_missing_review(self):
        with tempfile.TemporaryDirectory() as d:
            s,_,r,p=build(d); c=propose(s,r,p,['P1','P2'])
            c['policy_sha256']='fake'
            self.assertEqual(check(c,d)['reason'],'CERTIFICATE_CONTENT_HASH_MISMATCH')
            c=propose(s,r,p,['P1','P2']); c['snapshot_id']='MISSING'
            self.assertEqual(check(c,d)['status'],'INCOMPLETE')


class SpectralExerciseTest(unittest.TestCase):
    def test_reference_numbers_and_conflict(self):
        try:
            import numpy as np
        except ImportError:
            self.skipTest('Run this numeric test with the existing bundled NumPy runtime.')
        from legal_bench.proof_carrying.spectral import examples, solve
        x=examples()
        self.assertAlmostEqual(x['bipartite']['components'][0]['eigenvalues'][0],0.0726006,places=6)
        self.assertAlmostEqual(x['internal']['components'][0]['eigenvalues'][0],0.106424,places=5)
        self.assertTrue(np.allclose(x['bipartite']['components'][0]['scores'],[1,.7096,-1,1,.7096,-1],atol=1e-4))
        conflict=x['parallel_conflict']
        self.assertEqual(conflict['components'][0]['degree'],[6.,6.])
        self.assertEqual(conflict['conflicting_pairs'],[[0,1]])
        self.assertEqual(conflict['isolates'],[2])
        self.assertTrue(conflict['components'][0]['nonunique_axis'])
        self.assertEqual(len(conflict['parallel_edges']) if 'parallel_edges' in conflict else len(conflict['edge_records']),2)
        with self.assertRaises(ValueError):solve([[0,-1],[-1,0]],[[0,0],[0,0]])


if __name__=='__main__':
    unittest.main()
