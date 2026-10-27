"""Arithmetic/provenance acceptance only; no semantic or model experiment."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    'rapido_score_v2', Path(__file__).resolve().parents[1] / 'scripts/score_rapido_reports_v2.py')
S = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(S)


class ScoreContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.view = {'case_id': 'fixture', 'sources': {'s': {'text': 'The trial court rejected the claim.'}}}
        self.sp = self.put('sources.json', self.view)
        self.ref = {'case_id': 'fixture', 'reading_complete': True,
                    'source_view_sha256': S.sha(self.sp.read_bytes()), 'items': [
                        {'id': 'r1', 'criterion': 'Prior outcome with attribution',
                         'importance_reason': 'Defines prior posture',
                         'evidence': [{'source_id': 's', 'quote': 'rejected the claim'}]},
                        {'id': 'r2', 'criterion': 'Current outcome remains unavailable',
                         'importance_reason': 'Respects view boundary',
                         'evidence': [{'source_id': 's', 'quote': 'The trial court'}]}]}
        self.rp = self.put('reference.json', self.ref)
        self.report = {'blind_id': 'X1', 'text': 'The trial court rejected the claim.',
                       'report_sha256': S.sha(b'The trial court rejected the claim.'),
                       'delivery_status': 'SUBSTANTIVE_REPORT'}
        self.row = {'blind_id': 'X1', 'case_id': 'fixture', 'reading_complete': True,
                    'report_sha256': self.report['report_sha256'],
                    'reference_sha256': S.sha(self.rp.read_bytes()),
                    'source_view_sha256': S.sha(self.sp.read_bytes()),
                    'coverage': [
                        {'item_id': 'r1', 'status': 'CORRECT',
                         'report_quotes': ['trial court rejected'], 'reason': 'Matches prior stage'},
                        {'item_id': 'r2', 'status': 'NOT_SATISFIED', 'reason': 'Not addressed'}],
                    'assertion_inventory_complete': True,
                    'assertions': [{'id': 'a1', 'proposition': 'Prior court rejection',
                                    'report_quote': self.report['text'], 'label': 'SUPPORTED',
                                    'evidence': [{'source_id': 's', 'quote': 'rejected the claim'}],
                                    'reason': 'Attributed prior outcome'}],
                    'serious_error_inventory_complete': True, 'serious_errors': [],
                    'main_answer': 'PARTIAL'}

    def put(self, name, data):
        p = self.root / name
        p.write_text(json.dumps(data), encoding='utf-8')
        return p

    def run_score(self, rows=None, report=None):
        pp = self.put('packet.json', {'case_id': 'fixture',
                                    'source_view_sha256': S.sha(self.sp.read_bytes()),
                                    'reference_sha256': S.sha(self.rp.read_bytes()),
                                    'reports': [report or self.report]})
        lp = self.put('labels.json', {'case_id': 'fixture',
                                    'source_view_sha256': S.sha(self.sp.read_bytes()),
                                    'reference_sha256': S.sha(self.rp.read_bytes()),
                                    'reports': rows if rows is not None else [self.row]})
        return S.score(self.sp, self.rp, pp, lp)['reports'][0]

    def test_components_and_auxiliary_harmonic(self):
        r = self.run_score()
        self.assertEqual(r['R'], [.5, .5])
        self.assertEqual(r['P'], [1, 1])
        self.assertAlmostEqual(r['H'][0], 200 / 3)
        self.assertEqual(r['strict_success'], [0, 0])

    def test_unresolved_does_not_leave_denominator(self):
        self.row['coverage'][1]['status'] = 'ANNOTATION_UNRESOLVED'
        self.row['assertions'][0]['label'] = 'ANNOTATION_UNRESOLVED'
        r = self.run_score()
        self.assertEqual(r['R'], [.5, 1])
        self.assertEqual(r['P'], [0, 1])

    def test_missing_annotation_is_not_zero(self):
        r = self.run_score(rows=[])
        self.assertEqual(r['annotation_status'], 'NOT_ANNOTATED')
        self.assertEqual(r['R'], [0, 1])

    def test_empty_failure_cannot_obtain_precision_credit(self):
        r = self.run_score(rows=[], report=dict(self.report, text='',
                          report_sha256=S.sha(b''), delivery_status='TECHNICAL_FAILURE'))
        self.assertEqual(r['R'], [0, 0])
        self.assertIsNone(r['P'])
        self.assertEqual(r['H'], [0, 0])

    def test_incomplete_inventory_has_no_precision(self):
        self.row['assertion_inventory_complete'] = False
        r = self.run_score()
        self.assertIsNone(r['P'])
        self.assertEqual(r['strict_success'][0], 0)

    def test_wrong_hash_missing_item_and_bad_evidence_rejected(self):
        self.row['report_sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            self.run_score()
        self.row['report_sha256'] = self.report['report_sha256']
        removed = self.row['coverage'].pop()
        with self.assertRaisesRegex(ValueError, 'Missing/extra'):
            self.run_score()
        self.row['coverage'].append(removed)
        self.row['assertions'][0]['evidence'][0]['quote'] = 'allowed the claim'
        with self.assertRaisesRegex(ValueError, 'Non-verbatim'):
            self.run_score()

    def test_packet_cannot_silently_use_another_reference(self):
        pp = self.put('wrong-packet.json', {'case_id': 'fixture',
                      'source_view_sha256': S.sha(self.sp.read_bytes()),
                      'reference_sha256': '0' * 64, 'reports': [self.report]})
        lp = self.put('labels.json', {'case_id': 'fixture',
                      'source_view_sha256': S.sha(self.sp.read_bytes()),
                      'reference_sha256': S.sha(self.rp.read_bytes()), 'reports': [self.row]})
        with self.assertRaisesRegex(ValueError, 'Packet reference'):
            S.score(self.sp, self.rp, pp, lp)


if __name__ == '__main__':
    unittest.main()
