import unittest
from legal_bench.core import digest
from legal_bench.source_screening import import_screen_source, screening_task, validate_screening_reply
from legal_bench.annotation_v2 import segment_source
from legal_bench.reviewed_pipeline import registry


class SourceScreeningTests(unittest.TestCase):
    def export(self, text):
        return {'case_id':'123', 'drive_metadata':{'url':'source-url'},
                'response':{'structuredContent':{'content':text}}}

    def test_sequence_does_not_promote_semantic_completeness(self):
        parent, source = import_screen_source(self.export('Beginning\nIndian Kanoon - http://indiankanoon.org/doc/123/ 1Terminal decision\nIndian Kanoon - http://indiankanoon.org/doc/123/ 2'), b'original export')
        self.assertEqual(source['completeness_basis']['page_count'], 2)
        self.assertEqual(source['source_completeness'], 'REQUIRES_TERMINAL_REVIEW')
        self.assertEqual(source['source_sha256'], digest(b'original export'))
        with self.assertRaises(ValueError): segment_source(parent)
        task = screening_task([source], {}, 'b')
        self.assertIn('Beginning', task['prompt'])
        self.assertIn('Terminal decision', task['prompt'])
        self.assertTrue(task['prompt'].endswith('END_COMPLETE_SCREEN_INPUT b'))
        self.assertEqual(task['state'], 'PREPARED_NOT_SUBMITTED')

    def test_wrong_source_gaps_and_trailing_material_block_import(self):
        for text in ['Indian Kanoon - http://indiankanoon.org/doc/999/ 1',
                     'Indian Kanoon - http://indiankanoon.org/doc/123/ 2',
                     'Indian Kanoon - http://indiankanoon.org/doc/123/ 1unassigned appendix']:
            with self.assertRaises(ValueError): import_screen_source(self.export(text), text.encode())

    def test_no_foreign_case_inherits_development_assertion_ids(self):
        definition = {'id':'FILE_PROCEEDING','meaning':'A civil suit was filed', 'roles':{'filer':'Party'}}
        annotation = {'case_id':'new-case','predicate_definitions':[definition]}
        rules = registry(annotation, {'FILE_PROCEEDING':{'type':'SUIT_FILING_RECORD','roles':{'claimant':'filer'}}}, 'B')
        self.assertNotIn('assertion_ids', rules['rules']['FILE_PROCEEDING'])

    def test_model_screening_requires_every_case_and_anchored_evidence(self):
        _, source = import_screen_source(self.export('Tenant sought possession.\nIndian Kanoon - http://indiankanoon.org/doc/123/ 1'), b'export')
        task = screening_task([source], {}, 'b')
        ev = [{'segment_id':source['segments'][0]['id'],'quote':'Tenant sought possession.'}]
        row = {'case_id':'123','eligibility':'ELIGIBLE','reason':'Stated request', 'source_completeness':'VERIFIED_FULL',
               'completeness_reason':'Terminal inspected', 'court_evidence':ev, 'request_evidence':ev,
               'tenancy_evidence':ev,'terminal_evidence':ev,'parties':[], 'properties':[], 'proceedings':[],
               'related_judgments':[], 'grouping_limitations':[], 'uncertainties':[]}
        reply = {'batch_id':'b','end_marker':'END_COMPLETE_SCREEN_BATCH b','cases':[row]}
        self.assertTrue(validate_screening_reply(reply, task, [source])['valid'])
        row['tenancy_evidence'] = [{'segment_id':ev[0]['segment_id'],'quote':'Invented payment'}]
        self.assertFalse(validate_screening_reply(reply, task, [source])['valid'])
        reply['cases'] = []
        self.assertFalse(validate_screening_reply(reply, task, [source])['valid'])

    def test_malformed_model_reply_is_rejected_without_crashing(self):
        task = {'batch_id':'b', 'case_ids':['123']}
        for reply in [[], None, {'cases':[{'case_id': []}]}]:
            self.assertFalse(validate_screening_reply(reply, task, [])['valid'])
