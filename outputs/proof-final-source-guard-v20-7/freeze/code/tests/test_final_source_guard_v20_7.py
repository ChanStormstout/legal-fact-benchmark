"""Final-source regressions. Injected reviews test code, never legal accuracy."""
import copy
import json
import unittest
from pathlib import Path
from legal_bench.proof_carrying import final_source_guard_v20_7 as guard
from legal_bench.proof_carrying import local_pipeline_v19_8 as legacy
from legal_bench.proof_carrying.schema_contract_v19_6 import validate
from legal_bench.proof_carrying.rule_contracts_v19_7 import digest

ROOT = Path(__file__).resolve().parents[1]


def material():
    case = {'case_id': 'toy', 'targets': [{'id': 'Q1', 'text': 'Reconstruct the dispute.'}],
            'segments': [
                {'id': 'S1', 'text': 'Alice, landlord of Room 17, applied for withdrawal. Bob is the tenant.'},
                {'id': 'S2', 'text': 'The Supreme Court remanded the dispute. Payment was a condition, not a found event.'}]}
    def row(key, kind, claim, deps=(), label='SUPPORTED'):
        return {'id': key, 'kind': kind, 'claim': claim, 'refs': ['SRC:1'],
                'dependencies': list(deps), 'proposed_label': label,
                'verification_state': 'REVIEWED', 'verification_refs': ['SRC:1']}
    rows = [row('P/R1.P1/EV:1', 'ATTRIBUTION', {'proposition': 'Alice applied for withdrawal.'}),
            row('P/R1.P1/USE:1/ROLE:landlord', 'OBJECT_BINDING', {'role': 'landlord', 'object': {'label': 'Alice'}}),
            row('P/R1.P1/J:1', 'PREMISE_BASIS', {'judgment': {'state': 'TRUE'}},
                ['P/R1.P1/EV:1', 'P/R1.P1/USE:1/ROLE:landlord']),
            row('P/R1.P1/EV:2', 'ATTRIBUTION', {'proposition': 'Bob already paid.'}, label='UNSUPPORTED')]
    result = {'structure_checked': True, 'independent': {'status': 'OK'},
              'pool': {'source_sha256': digest(case['segments']), 'candidates': rows},
              'applied_proposals': {'P': {'analyses': {'R1.P1': {'judgments': [{'state': 'TRUE'}]}}}},
              'audit': {'premise_judgments': [{'premise': 'R1.P1', 'conditional_state': 'TRUE', 'errors': []}]}}
    return case, [{'id': 'R1', 'source_refs': [], 'premises': [{'id': 'R1.P1', 'expected': 'TRUE'}]}], result


def candidate(task):
    key = 'P01::P/R1.P1/EV:1'
    return {'request_id': 'Q1', 'conclusion': 'Alice applied concerning Room 17; ownership is not decided.',
            'conclusion_claim_ids': [key], 'result_status': 'SOURCE_RECONSTRUCTION',
            'case_frame': {'actors': [
                {'id': 'A', 'name': 'Alice', 'kind': 'PARTY', 'capacities': ['LANDLORD'], 'court_level': 'NONE', 'refs': ['S1']},
                {'id': 'B', 'name': 'Bob', 'kind': 'PARTY', 'capacities': ['TENANT'], 'court_level': 'NONE', 'refs': ['S1']},
                {'id': 'C', 'name': 'Supreme Court', 'kind': 'COURT', 'capacities': ['COURT'], 'court_level': 'SUPREME_COURT', 'refs': ['S2']}],
                'properties': [{'id': 'X', 'description': 'Room 17', 'refs': ['S1']}],
                'events': [{'id': 'E', 'actor_id': 'A', 'property_id': 'X', 'court_context_id': 'C',
                            'stage': 'TRIAL', 'kind': 'PARTY_APPLICATION', 'statement_status': 'REPORTED_EVENT',
                            'description': 'Alice applied for withdrawal.', 'claim_ids': [key], 'refs': ['S1']}]},
            'grounds': [{'point': 'Alice applied for withdrawal.', 'statement_status_and_stage': 'REPORTED_EVENT; trial',
                         'case_refs': ['S1'], 'rule_refs': ['R1'], 'explanation': 'This is a party application, not a court application.',
                         'claim_ids': [key], 'actor_ids': ['A'], 'property_ids': ['X'], 'event_ids': ['E']}],
            'counterarguments': [], 'gaps': ['No title determination is made.'], 'assumptions': [], 'connection_handling': []}


def injected_review(task, answer, case):
    rt = guard.review_task(task, answer, case)
    verdict = lambda: {'label': 'SUPPORTED', 'refs': ['S1'], 'reason': 'Injected program control; not a legal review.'}
    return {**rt['bindings'], 'verdicts': {k: verdict() for k in rt['units']},
            'coverage': {k: verdict() for k in guard.COVERAGE}}


class FinalGuardTests(unittest.TestCase):
    def setUp(self):
        self.case, self.rules, self.result = material()
        self.task = guard.final_task(self.case, self.rules, {'audit': {'conditional_rules': []}}, [('P01', self.result)])
        self.answer = candidate(self.task)

    def accept(self, answer=None, review=True, task=None, case=None):
        a = self.answer if answer is None else answer
        t = self.task if task is None else task
        c = self.case if case is None else case
        r = injected_review(t, a, c) if review is True else review
        return guard.accept_final(t, json.dumps(a), 'OK', case=c, review=r)

    def test_text_rules_are_independent(self):
        before = copy.deepcopy(legacy.FINAL_SCHEMA)
        schema = guard.metadata_schema(legacy.FINAL_SCHEMA)
        self.assertEqual(legacy.FINAL_SCHEMA, before)
        for field in ['conclusion']:
            self.assertNotIn('maxLength', schema['properties'][field])
        for field in ['point', 'explanation']:
            self.assertNotIn('maxLength', schema['properties']['grounds']['items']['properties'][field])
        self.assertEqual(schema['properties']['gaps']['items']['maxLength'], 480)
        schema['properties']['gaps']['items']['maxLength'] = 10
        self.assertNotIn('maxLength', schema['properties']['conclusion'])

    def test_long_substantive_answer_survives_whole_entry(self):
        self.answer['conclusion'] = 'A complete source reconstruction with explicit limitations. ' * 30
        self.answer['grounds'][0]['explanation'] = 'Substantive explanation is retained in full. ' * 30
        result = self.accept()
        self.assertEqual(result['answer'], self.answer)
        self.assertGreater(len(result['answer']['conclusion']), 480)
        self.assertFalse(result['legal_approval'])

    def test_auxiliary_text_still_has_a_bound(self):
        self.answer['gaps'] = ['g' * 481]
        result = self.accept(review=None)
        self.assertIsNone(result['answer'])

    def test_no_automatic_acceptance_without_exact_source_review(self):
        self.assertEqual(self.accept(review=None)['contract_status'], 'PENDING_WHOLE_ANSWER_SOURCE_REVIEW')

    def test_rejected_fact_cannot_be_selected(self):
        self.answer['grounds'][0]['claim_ids'] = ['P01::P/R1.P1/EV:2']
        self.assertIsNone(self.accept(review=None)['answer'])

    def test_source_supported_use_with_rejected_dependency_is_not_selectable(self):
        result = copy.deepcopy(self.result)
        result['pool']['candidates'][0]['proposed_label'] = 'UNSUPPORTED'
        book = guard.registry(self.case, [('P01', result)])
        self.assertNotIn('P01::P/R1.P1/J:1', book['accepted'])
        self.assertIn('P01::P/R1.P1/J:1', book['blocked'])

    def test_pending_fact_cannot_be_selected(self):
        result = copy.deepcopy(self.result)
        result['pool']['candidates'][0]['proposed_label'] = 'UNRESOLVED'
        book = guard.registry(self.case, [('P01', result)])
        self.assertNotIn('P01::P/R1.P1/EV:1', book['accepted'])

    def test_unsupported_fact_cannot_return_as_an_assumption(self):
        self.answer['assumptions'] = ['Assume the tenant already paid.']
        self.assertIsNone(self.accept(review=None)['answer'])

    def test_new_prose_fact_requires_source_review_even_with_legal_refs(self):
        self.answer['grounds'][0]['point'] = 'Bob had paid on time.'
        r = injected_review(self.task, self.answer, self.case)
        rt = guard.review_task(self.task, self.answer, self.case)
        key = next(k for k, v in rt['units'].items() if v['path'] == ['grounds', 0, 'point'])
        r['verdicts'][key] = {'label': 'UNSUPPORTED', 'refs': ['S2'], 'reason': 'Condition is not an observed payment.'}
        self.assertIsNone(self.accept(review=r)['answer'])

    def test_disputed_date_is_not_forced_to_a_fact(self):
        self.answer['conclusion'] = 'Knowledge was definitively on Friday.'
        r = injected_review(self.task, self.answer, self.case)
        r['coverage']['UNCERTAINTY_PRESERVED']['label'] = 'UNRESOLVED'
        self.assertIsNone(self.accept(review=r)['answer'])

    def test_court_cannot_be_the_applying_party(self):
        self.answer['case_frame']['events'][0]['actor_id'] = 'C'
        result = self.accept(review=None)
        self.assertIn('PARTY_EVENT_MISATTRIBUTED_TO_NONPARTY', result['candidate_check']['errors'])

    def test_party_cannot_issue_a_court_remand(self):
        self.answer['case_frame']['events'][0]['kind'] = 'COURT_REMAND'
        result = self.accept(review=None)
        self.assertIn('COURT_EVENT_MISATTRIBUTED_TO_NONCOURT', result['candidate_check']['errors'])

    def test_wrong_issuing_court_context_is_rejected(self):
        e = self.answer['case_frame']['events'][0]
        e.update(kind='COURT_REMAND', actor_id='C', court_context_id='NONE')
        result = self.accept(review=None)
        self.assertIn('ISSUING_COURT_CONTEXT_MISMATCH', result['candidate_check']['errors'])

    def test_valid_but_wrong_court_is_rejected_by_semantic_review(self):
        self.answer['case_frame']['actors'][2]['name'] = 'District Court'
        self.answer['case_frame']['actors'][2]['court_level'] = 'DISTRICT_COURT'
        r = injected_review(self.task, self.answer, self.case)
        r['coverage']['COURT_STAGES'] = {'label': 'UNSUPPORTED', 'refs': ['S2'], 'reason': 'Source identifies Supreme Court.'}
        self.assertIsNone(self.accept(review=r)['answer'])

    def test_missing_property_is_rejected(self):
        self.answer['case_frame']['properties'] = []
        self.assertIsNone(self.accept(review=None)['answer'])

    def test_missing_parties_is_rejected(self):
        self.answer['case_frame']['actors'] = self.answer['case_frame']['actors'][2:]
        self.assertIsNone(self.accept(review=None)['answer'])

    def test_duplicate_actor_ids_are_rejected(self):
        self.answer['case_frame']['actors'][1]['id'] = 'A'
        result = self.accept(review=None)
        self.assertIn('DUPLICATE_ACTOR_ID', result['candidate_check']['errors'])

    def test_unknown_event_references_are_rejected(self):
        self.answer['grounds'][0]['event_ids'] = ['MISSING']
        self.assertIsNone(self.accept(review=None)['answer'])

    def test_missing_decisive_counterargument_blocks_acceptance(self):
        r = injected_review(self.task, self.answer, self.case)
        r['coverage']['DECISIVE_COUNTERARGUMENTS']['label'] = 'UNSUPPORTED'
        self.assertIsNone(self.accept(review=r)['answer'])

    def test_incomplete_sentence_blocks_acceptance(self):
        self.answer['conclusion'] = 'The order directing the'
        r = injected_review(self.task, self.answer, self.case)
        r['coverage']['NARRATIVE_COMPLETENESS']['label'] = 'UNSUPPORTED'
        self.assertIsNone(self.accept(review=r)['answer'])

    def test_stale_candidate_review_is_rejected(self):
        r = injected_review(self.task, self.answer, self.case)
        self.answer['conclusion'] += ' Changed.'
        self.assertIsNone(self.accept(review=r)['answer'])

    def test_stale_registry_review_is_rejected(self):
        r = injected_review(self.task, self.answer, self.case)
        r['registry_sha256'] = 'stale'
        self.assertIsNone(self.accept(review=r)['answer'])

    def test_changed_task_or_registry_is_rejected(self):
        for field in ['prompt', 'claim_registry', 'review_context']:
            t = copy.deepcopy(self.task)
            if field == 'prompt': t[field] += ' Changed.'
            elif field == 'claim_registry': t[field]['accepted'].clear()
            else: t[field]['request']['text'] += ' Changed.'
            self.assertIsNone(self.accept(task=t, review=None)['answer'])

    def test_changed_request_cannot_reuse_an_old_task(self):
        case = copy.deepcopy(self.case)
        case['targets'][0]['text'] += ' Changed.'
        self.assertIsNone(self.accept(case=case, review=None)['answer'])

    def test_reviewer_has_fixed_request_rules_and_computed_states(self):
        rt = guard.review_task(self.task, self.answer, self.case)
        self.assertIn(json.dumps(self.case['targets'][0], ensure_ascii=False), rt['prompt'])
        self.assertIn('request_and_rules', rt['prompt'])
        self.assertIn('CLAIM_SUPPORT_ALIGNMENT', rt['schema']['properties']['coverage']['properties'])

    def test_source_supported_new_fact_cannot_bypass_declared_support(self):
        self.answer['conclusion'] = 'The Supreme Court remanded the case.'
        r = injected_review(self.task, self.answer, self.case)
        r['coverage']['CLAIM_SUPPORT_ALIGNMENT'] = {
            'label': 'UNSUPPORTED', 'refs': ['S2'],
            'reason': 'Selected declaration is about the application; no reviewed remand declaration is selected.'}
        self.assertIsNone(self.accept(review=r)['answer'])

    def test_changed_source_is_rejected(self):
        c = copy.deepcopy(self.case)
        c['segments'][0]['text'] += ' Changed.'
        self.assertIsNone(self.accept(case=c, review=None)['answer'])

    def test_review_without_sources_or_with_missing_units_is_rejected(self):
        r = injected_review(self.task, self.answer, self.case)
        r['verdicts']['U1']['refs'] = []
        self.assertIsNone(self.accept(review=r)['answer'])
        r = injected_review(self.task, self.answer, self.case)
        r['verdicts'].pop('U1')
        self.assertIsNone(self.accept(review=r)['answer'])

    def test_all_prose_including_gaps_and_handling_is_reviewed(self):
        self.answer['connection_handling'] = [{'connection_id': 'P01::P/R1.P1/EV:1',
            'decision': 'NOT_USED', 'refs': ['S1'], 'reason': 'A precise scope limitation.'}]
        paths = [u['path'] for u in guard.narrative_units(self.answer).values()]
        for path in [['conclusion'], ['grounds', 0, 'explanation'], ['gaps', 0],
                     ['case_frame', 'actors', 0, 'name'], ['case_frame', 'events', 0, 'description'],
                     ['connection_handling', 0, 'reason']]:
            self.assertIn(path, paths)

    def test_each_judgment_uses_its_own_state(self):
        r = copy.deepcopy(self.result)
        second = copy.deepcopy(r['pool']['candidates'][2])
        second['id'] = 'P/R1.P1/J:2'
        r['pool']['candidates'].append(second)
        r['applied_proposals']['P']['analyses']['R1.P1']['judgments'].append({'state': 'FALSE'})
        r['audit']['premise_judgments'].append({'premise': 'R1.P1', 'conditional_state': 'UNKNOWN', 'errors': ['UNVERIFIED']})
        book = guard.registry(self.case, [('P01', r)])
        self.assertEqual(book['accepted']['P01::P/R1.P1/J:1']['conditional_state'], 'TRUE')
        self.assertEqual(book['accepted']['P01::P/R1.P1/J:2']['conditional_state'], 'UNKNOWN')

    def test_rule_condition_polarity_not_exposed_as_a_factual_answer(self):
        self.assertNotIn('"expected"', self.task['prompt'])
        self.assertEqual(self.rules[0]['premises'][0]['expected'], 'TRUE')

    def test_real_failed_final_is_not_promoted_or_rewritten(self):
        path = ROOT/'outputs/proof-source-repair-v20-6/completion-01/final/1954254/formal-answer.json'
        if not path.exists(): self.skipTest('Archived development answer unavailable.')
        before = path.read_bytes()
        old = json.loads(before)['answer']
        self.assertEqual(len(old['conclusion']), 480)
        result = guard.accept_final(self.task, json.dumps(old), 'OK', case=self.case)
        self.assertIsNone(result['answer'])
        self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
