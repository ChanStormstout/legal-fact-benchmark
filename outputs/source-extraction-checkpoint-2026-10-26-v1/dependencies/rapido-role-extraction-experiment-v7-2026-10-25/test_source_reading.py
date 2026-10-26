"""Offline contract/orchestration tests. Fixtures are NOT Qwen or legal gold."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from source_reading import (catalog, reading_request, initial_packet, review_request,
                           apply_review, run, record_errors, digest, CHECKS, NULLABLE)
from schema_contract import validate, decoder_schema

SOURCES = {
    'P1': 'A filed a defense. A denied that B',
    'P2': 'paid C. The panel held recovery available only if notice was served.',
    'P3': 'Counsel appeared. A proposed payment of Rs. 100.00; no judgment is stated.'}


def record(anchor='P2', qualified=True):
    c = catalog(SOURCES)
    cue = next(iter(c['qualification_cues']))
    return {'anchor': anchor, 'kind': 'COURT_FINDING',
        'attribution': {'speaker': 'The panel', 'forum': None, 'stage': None, 'time': None},
        'proposition': {'subject': 'Recovery', 'relation': 'is available', 'object': 'to the claimant', 'event_time': None},
        'qualification_state': 'PRESENT' if qualified else 'NONE',
        'qualifications': [{'type': 'ONLY_IF', 'text': 'notice was served', 'cue_ids': [cue], 'evidence': ['P2']}] if qualified else [],
        'evidence': [anchor], 'unknowns': [{'field': k, 'reason': 'SOURCE_ABSENT', 'detail': 'Not specified.'}
            for k in NULLABLE if k != 'attribution.speaker']}


def reading(focus, qualified=True):
    records = [record(qualified=qualified)] if 'P2' in focus else []
    # Deliberately incomplete source interpretation; tests linkage, not coverage quality.
    return {'records': records, 'coverage': {sid: {
        'state': 'RECORDS' if sid == 'P2' else 'UNRESOLVED',
        'indices': [0] if sid == 'P2' else [], 'reason': 'Synthetic fixture; other content unresolved.'} for sid in focus},
        'conflicts': []}


def review(c, packet):
    rows = [{'target': ident, 'decision': 'KEEP', 'checks': {key: 'SUPPORTED' for key in CHECKS},
        'source_basis': 'The panel conditions recovery on service of notice.',
        'evidence': row['record']['evidence'], 'replacements': []} for ident, row in packet['records'].items()]
    return {'reviews': rows, 'additions': [],
        'coverage': {sid: {'state': 'RECORDS' if sid == 'P2' else 'UNRESOLVED',
            'targets': list(packet['records']) if sid == 'P2' else [], 'addition_indices': [],
            'source_basis': 'Fixture coverage is not a semantic label.'} for sid in packet['focus']},
        'cue_decisions': {key: {'decision': 'LINKED', 'targets': list(packet['records']), 'addition_indices': [],
            'source_basis': 'Notice condition limits the recovery proposition.'} for key, cue in c['qualification_cues'].items()
            if cue['source_id'] in packet['focus']}, 'conflicts': []}


class SourceTests(unittest.TestCase):
    def setUp(self):
        self.c = catalog(SOURCES)
        self.focus = list(SOURCES)
        self.packet = initial_packet(self.c, self.focus, reading(self.focus))

    def test_full_paragraphs_and_no_abbreviation_split(self):
        req = reading_request(self.c, ['P2'])
        self.assertEqual(req['sources'], SOURCES)
        self.assertIn('Rs. 100.00', req['sources']['P3'])
        self.assertNotIn('span_catalog', req)
        self.assertEqual(req['schema']['properties']['records']['items']['properties']['evidence']['items']['enum'], list(SOURCES))

    def test_condition_attachment_and_status_survive_roundtrip(self):
        r = review(self.c, self.packet)
        out = apply_review(self.c, self.packet, r, self.packet['snapshot_hash'])
        self.assertEqual(out['records']['R0000']['record']['qualifications'], record()['qualifications'])
        self.assertEqual(out['records']['R0000']['state'], 'MODEL_REVIEW_SUPPORTED')
        self.assertFalse(out['program_semantic_acceptance'])
        self.assertIsNone(out['semantic_quality'])

    def test_missing_condition_cannot_claim_linked_without_edit(self):
        packet = initial_packet(self.c, self.focus, reading(self.focus, False))
        out = apply_review(self.c, packet, review(self.c, packet), packet['snapshot_hash'])
        self.assertEqual(out['records']['R0000']['state'], 'UNRESOLVED')
        self.assertTrue(any(x['reason'] == 'LINKED_CUE_NOT_ATTACHED_TO_PROPOSITION' for x in out['pending']))

    def test_actual_replacement_not_auto_accepted(self):
        packet = initial_packet(self.c, self.focus, reading(self.focus, False))
        r = review(self.c, packet)
        r['reviews'][0].update(decision='REPLACE', replacements=[record()])
        r['reviews'][0]['checks']['qualifications'] = 'ERROR'
        out = apply_review(self.c, packet, r, packet['snapshot_hash'])
        self.assertEqual(out['records']['R0000.r0']['state'], 'REVISION_NOT_INDEPENDENTLY_REVIEWED')
        self.assertEqual(out['retired_records']['R0000']['record']['qualification_state'], 'NONE')
        self.assertEqual(out['revision_events'][0]['before_hash'], packet['records']['R0000']['hash'])

    def test_stale_review_and_duplicate_target_fail(self):
        r = review(self.c, self.packet)
        with self.assertRaisesRegex(ValueError, 'STALE_REVIEW'):
            apply_review(self.c, self.packet, r, 'old')
        two = reading(self.focus); two['records'].append(copy.deepcopy(two['records'][0])); two['coverage']['P2']['indices'].append(1)
        packet = initial_packet(self.c, self.focus, two); r = review(self.c, packet)
        r['reviews'][1] = copy.deepcopy(r['reviews'][0])
        with self.assertRaisesRegex(ValueError, 'DUPLICATE_OR_MISSING'):
            apply_review(self.c, packet, r, packet['snapshot_hash'])

    def test_contradictory_keep_and_missing_antecedent_flag_boundary(self):
        r = review(self.c, self.packet); r['reviews'][0]['checks']['evidence'] = 'ERROR'
        out = apply_review(self.c, self.packet, r, self.packet['snapshot_hash'])
        self.assertEqual(out['records']['R0000']['state'], 'UNRESOLVED')
        # The program cannot prove a quotation entails a proposition: no fabricated ACCEPT.
        self.assertFalse(out['program_semantic_acceptance'])

    def test_null_notes_and_focus_addresses_are_not_silently_filled(self):
        candidate = record(); candidate['attribution']['stage'] = 'Execution'
        self.assertIn('UNKNOWN_NOTES_MUST_MATCH_NULL_FIELDS', record_errors(candidate, self.c, self.focus))
        candidate['unknowns'] = [x for x in candidate['unknowns'] if x['field'] != 'attribution.stage']
        self.assertEqual(record_errors(candidate, self.c, self.focus), [])
        candidate['anchor'] = 'P1'
        self.assertIn('ANCHOR_OUTSIDE_FOCUS_OR_EVIDENCE', record_errors(candidate, self.c, ['P2']))

    def test_dismissed_cue_cannot_remain_attached_as_supported(self):
        r = review(self.c, self.packet)
        cue = next(iter(r['cue_decisions']))
        r['cue_decisions'][cue].update(decision='NOT_A_QUALIFICATION', targets=[])
        out = apply_review(self.c, self.packet, r, self.packet['snapshot_hash'])
        self.assertEqual(out['records']['R0000']['state'], 'UNRESOLVED')

    def test_generic_none_and_all_supported_do_not_certify_records(self):
        r = review(self.c, self.packet)
        r['reviews'][0]['source_basis'] = 'All components are supported.'
        next(iter(r['cue_decisions'].values()))['source_basis'] = 'None.'
        out = apply_review(self.c, self.packet, r, self.packet['snapshot_hash'])
        self.assertEqual(out['records']['R0000']['state'], 'UNRESOLVED')
        reasons = {x['reason'] for x in out['pending']}
        self.assertIn('REVIEW_HAS_NO_SPECIFIC_SOURCE_COMPARISON', reasons)
        self.assertIn('CUE_REVIEW_HAS_NO_SPECIFIC_SOURCE_COMPARISON', reasons)

    def test_modified_packet_cannot_reuse_original_snapshot_hash(self):
        packet = copy.deepcopy(self.packet)
        packet['records']['R0000']['record']['proposition']['object'] = 'a changed target'
        with self.assertRaisesRegex(ValueError, 'STALE_REVIEW_SNAPSHOT'):
            apply_review(self.c, packet, review(self.c, packet), packet['snapshot_hash'])

    def test_cross_batch_condition_remains_visible_and_requires_audit(self):
        # The condition is in P2; a hypothetical completed proposition is anchored
        # in P3. This fixture tests addressing only, not that P3 actually says it.
        r = record(anchor='P3'); r['evidence'] = ['P2', 'P3']
        value = {'records': [r], 'coverage': {'P3': {'state': 'RECORDS', 'indices': [0], 'reason': 'Fixture'}}, 'conflicts': []}
        packet = initial_packet(self.c, ['P3'], value)
        req = review_request(self.c, packet)
        cue = next(iter(self.c['qualification_cues']))
        self.assertIn(cue, req['schema']['properties']['cue_decisions']['properties'])
        self.assertEqual(req['sources'], SOURCES)

    def test_schema_decoder_and_wire_use_same_sources(self):
        for req, val in [(reading_request(self.c, self.focus), reading(self.focus)),
                         (review_request(self.c, self.packet), review(self.c, self.packet))]:
            validate(val, req['schema']); validate(val, decoder_schema(req['schema']))
            self.assertEqual(req['sources'], SOURCES)
        self.assertNotIn('hash', next(iter(review_request(self.c, self.packet)['candidates'].values())))

    def test_fixed_batches_use_full_context_and_finish_once(self):
        seen = []
        def ask(tag, req):
            self.assertEqual(req['sources'], SOURCES); seen.append(tag)
            if tag.startswith('reading'):
                return reading(req['focus_source_ids'])
            packet = initial_packet(self.c, req['focus_source_ids'], reading(req['focus_source_ids']))
            return review(self.c, packet)
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)/'attempt'
            out = run(SOURCES, ask, dest, 1)
            self.assertEqual(len(seen), 6); self.assertTrue(out['technical_complete'])
            with self.assertRaisesRegex(ValueError, 'EXISTING_ATTEMPT'):
                run(SOURCES, ask, dest, 1)

    def test_failed_stream_keeps_finished_batch_but_has_no_final_packet(self):
        def ask(tag, req):
            if tag == 'reading-001':
                raise RuntimeError('STREAM_INCOMPLETE')
            if tag.startswith('reading'):
                return reading(req['focus_source_ids'])
            packet = initial_packet(self.c, req['focus_source_ids'], reading(req['focus_source_ids']))
            return review(self.c, packet)
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)/'attempt'
            with self.assertRaisesRegex(RuntimeError, 'STREAM_INCOMPLETE'):
                run(SOURCES, ask, dest, 1)
            outcome = json.loads((dest/'outcome.json').read_text())
            self.assertFalse(outcome['technical_complete']); self.assertIsNone(outcome['answer'])
            self.assertEqual(outcome['completed_batches'], 1)
            self.assertFalse((dest/'source-records.json').exists())
            self.assertTrue((dest/'batch-000/reviewed.json').exists())


if __name__ == '__main__':
    unittest.main()
