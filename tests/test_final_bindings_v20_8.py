"""Binding/transport controls; injected reviews are NOT semantic accuracy labels."""
import copy
import json
import unittest
from pathlib import Path

from legal_bench.proof_carrying import final_bindings_v20_8 as core
from legal_bench.proof_carrying.artifact_state_v20_2 import digest
from legal_bench.proof_carrying.schema_contract_v19_6 import validate
from scripts.proof_final_bindings_v20_8 import inputs, OUT


def injected(case, frame, bridge):
    rt = core.frame_review_task(case, frame, bridge)
    return {**rt['bindings'], 'verdicts': {k: {'label': 'SUPPORTED',
            'refs': v['row']['refs'], 'reason': 'Injected engineering control only.'}
            for k, v in rt['units'].items()}}


class FinalBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case, cls.old, cls.merged, cls.parts = inputs('1187427')
        cls.bridge = core.build_bridge(cls.case, cls.parts, cls.merged)
        cls.frame = json.loads((OUT / 'cases/1187427/frame-proposal.json').read_text())
        cls.review = injected(cls.case, cls.frame, cls.bridge)
        cls.task = core.final_task(cls.case, cls.old, cls.bridge, cls.frame, cls.review)
        source = cls.case['segments'][0]['id']
        claim = 'FE07'
        cls.writer = {'request_id': 'Q1', 'conclusion': 'The Supreme Court allowed the appeal. ' * 25,
                      'conclusion_claim_ids': [claim], 'result_status': 'SOURCE_RECONSTRUCTION',
                      'grounds': [{'point': 'The Supreme Court allowed the appeal.',
                                   'statement_status_and_stage': 'SUPREME_COURT_DISPOSITION',
                                   'case_refs': [source], 'rule_refs': [], 'explanation': 'Retirement did not exclude section 14A benefits.',
                                   'claim_ids': [claim], 'actor_ids': [cls.frame['actors'][-1]['id']],
                                   'property_ids': [cls.frame['properties'][0]['id']],
                                   'event_ids': [cls.frame['events'][-1]['id']]}],
                      'counterarguments': [], 'gaps': [], 'assumptions': [], 'connection_handling': []}

    def test_every_cache_preserves_all_local_rows(self):
        for cid in ('1954254', '569555', '1187427'):
            case, old, merged, parts = inputs(cid)
            bridge = core.build_bridge(case, parts, merged)
            expected = {core.scoped(case, part, pid, kind + ':' + str(i)): row
                        for part, result in parts
                        for pid, unit in result['applied_proposals']['P']['analyses'].items()
                        for kind, field in [('OBJ','objects'),('EV','records'),('USE','uses'),('J','judgments')]
                        for i, row in enumerate(unit[field], 1)}
            self.assertEqual(expected, {d['id']: d['original'] for d in bridge['declarations']})
            self.assertEqual(old['registry_sha256'], bridge['original_registry_sha256'])
            self.assertEqual(len(merged['canonical']['objects']), len(bridge['global_positions']))
            self.assertEqual(bridge['identity_merges'], 0)

    def test_local_obj_one_has_distinct_scoped_identities(self):
        rows = [d for d in self.bridge['declarations'] if d['local_address'] == 'OBJ:1']
        self.assertGreater(len({d['id'] for d in rows}), 5)
        self.assertGreater(len({d['original']['label'] for d in rows}), 5)

    def test_normalized_role_references_keep_scope(self):
        for claim in self.bridge['normalized_claims'].values():
            body = claim['claim']
            row = body.get('judgment', body.get('use', {}))
            for ref in row.get('role_objects', {}).values():
                self.assertTrue(ref == 'UNMAPPED' or ref.startswith('1187427/'))

    def test_reporting_court_does_not_become_actor_type(self):
        claim = self.bridge['normalized_claims']['C036']['claim']
        self.assertEqual(claim['reporting_court_level'], 'Supreme Court')
        self.assertNotIn('court_level', claim)
        self.assertEqual(self.frame['actors'][2]['court_level'], 'NONE')

    def test_object_order_mismatch_is_rejected(self):
        merged = copy.deepcopy(self.merged)
        merged['canonical']['objects'][0], merged['canonical']['objects'][1] = merged['canonical']['objects'][1], merged['canonical']['objects'][0]
        with self.assertRaisesRegex(ValueError, 'CONTENT_OR_ORDER'):
            core.build_bridge(self.case, self.parts, merged)

    def test_undeclared_global_reference_is_rejected(self):
        merged = copy.deepcopy(self.merged)
        key = next(iter(merged['audit']['conditional_rules'][0]['binding']))
        merged['audit']['conditional_rules'][0]['binding'][key] = 99999
        with self.assertRaisesRegex(ValueError, 'UNDECLARED_GLOBAL'):
            core.build_bridge(self.case, self.parts, merged)

    def test_no_claim_or_dependency_dropped(self):
        self.assertEqual(set(self.old['claim_registry']['accepted']), set(self.bridge['normalized_claims']))
        for key, row in self.bridge['normalized_claims'].items():
            self.assertEqual(row['dependencies'], self.old['claim_registry']['accepted'][key]['dependencies'])

    def test_frame_requires_exact_source_review(self):
        review = copy.deepcopy(self.review)
        review['frame_sha256'] = 'stale'
        with self.assertRaises(ValueError):
            core.final_task(self.case, self.old, self.bridge, self.frame, review)

    def test_frame_unresolved_cannot_dispatch(self):
        review = copy.deepcopy(self.review)
        review['verdicts']['E07']['label'] = 'UNRESOLVED'
        with self.assertRaisesRegex(ValueError, 'NOT_SOURCE_REVIEW_ACCEPTED'):
            core.final_task(self.case, self.old, self.bridge, self.frame, review)

    def test_frame_source_blank_cannot_dispatch(self):
        review = copy.deepcopy(self.review)
        review['verdicts']['E07']['refs'] = []
        with self.assertRaises(ValueError):
            core.final_task(self.case, self.old, self.bridge, self.frame, review)

    def test_duplicate_identity_link_is_rejected(self):
        frame = copy.deepcopy(self.frame)
        frame['actors'][1]['origin_object_ids'] = frame['actors'][0]['origin_object_ids']
        with self.assertRaisesRegex(ValueError, 'MULTIPLE_IDENTITY'):
            core.frame_review_task(self.case, frame, self.bridge)

    def test_writer_cannot_replace_frame(self):
        writer = copy.deepcopy(self.writer)
        writer['case_frame'] = self.frame
        self.assertEqual(core.accept_final(self.task, json.dumps(writer), 'OK', case=self.case)['contract_status'],
                         'FINAL_BINDING_CONTRACT_REJECTED')

    def test_writer_cannot_choose_undeclared_actor(self):
        writer = copy.deepcopy(self.writer)
        writer['grounds'][0]['actor_ids'] = ['OBJ:1']
        self.assertIsNone(core.accept_final(self.task, json.dumps(writer), 'OK', case=self.case)['answer'])

    def test_writer_cannot_choose_undeclared_event(self):
        writer = copy.deepcopy(self.writer)
        writer['grounds'][0]['event_ids'] = ['EV:99']
        with self.assertRaises(ValueError):
            core.render(self.task, writer, self.case)

    def test_frame_rendered_exactly_and_summary_not_cut(self):
        rendered = core.render(self.task, self.writer, self.case)
        self.assertEqual(rendered['case_frame'], self.frame)
        self.assertEqual(rendered['conclusion'], self.writer['conclusion'])
        self.assertGreater(len(rendered['conclusion']), 480)
        self.assertEqual(rendered['case_frame']['events'][0]['kind'], 'RETIREMENT')
        self.assertEqual(rendered['case_frame']['events'][1]['kind'], 'AUTHORITY_NOTICE')
        self.assertEqual(rendered['case_frame']['events'][-1]['actor_id'], self.frame['actors'][-1]['id'])

    def test_structural_success_requires_whole_answer_review(self):
        result = core.accept_final(self.task, json.dumps(self.writer), 'OK', case=self.case)
        self.assertEqual(result['contract_status'], 'PENDING_WHOLE_ANSWER_SOURCE_REVIEW')
        self.assertIsNone(result['answer'])

    def test_transport_failure_retains_null_answer(self):
        result = core.accept_final(self.task, '{', 'FORMAT_OR_TRANSPORT_FAILURE', case=self.case)
        self.assertEqual(result['contract_status'], 'GENERATION_FAILED')
        self.assertIsNone(result['answer'])

    def test_tampered_task_is_rejected(self):
        task = copy.deepcopy(self.task)
        task['frame']['events'][-1]['actor_id'] = self.frame['actors'][0]['id']
        with self.assertRaisesRegex(ValueError, 'TASK_CHANGED'):
            core.render(task, self.writer, self.case)

    def test_source_review_displays_all_original_text_and_dependencies(self):
        rt = core.review_task(self.task, self.writer, self.case)
        start = rt['prompt'].index('{"bindings":')
        end = rt['prompt'].index('\nOUTPUT SCHEMA:\n', start)
        payload = json.loads(rt['prompt'][start:end])
        self.assertEqual(payload['source'], [{'id': s['id'], 'text': s['text']} for s in self.case['segments']])
        used = rt['review_display']['selected_claims_and_all_dependencies']
        for key in used:
            self.assertTrue(set(payload['reviewed_claims']['accepted'][key]['dependencies']) <= set(used))
        self.assertIn('FE07', used)


if __name__ == '__main__':
    unittest.main()
