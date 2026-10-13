import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tests.test_compact_proposals_v19 import fixture as previous_fixture
from legal_bench.proof_carrying import local_pipeline_v19_6 as pipe
from legal_bench.proof_carrying import local_checker_v19_6 as checker
from legal_bench.proof_carrying.schema_contract_v19_6 import loads, validate
from legal_bench.proof_carrying.repetition_v19_6 import ExpansionGuard
from legal_bench.rules_verdict_v1.repetition_v9 import RepetitionAbort
from scripts import proof_contract_integrity_v19_6 as entry


def fixture():
    c, r, raw = previous_fixture()
    result = {'analyses': {}, 'object_links': copy.deepcopy(raw['object_links']), 'coverage_limits': copy.deepcopy(raw['coverage_limits'])}
    for unit in raw['analyses']:
        pid = unit['premise']; u = copy.deepcopy(unit); del u['premise']
        for row in u['uses'] + u['judgments']:
            row['role_objects'] = {k: 'UNMAPPED' for k in r[0]['premises'][0]['variables']}
            for b in row.pop('bindings'): row['role_objects'][b['address'].split('::')[-1]] = b['object']
        for use in u['uses']:
            for witness in use['witnesses']: witness['source'] = witness.pop('refs')[0]
        result['analyses'][pid] = u
    return c, r, result


def process(c, r, x):
    part = {'id': 'P01', 'rule_ids': [a['id'] for a in r], 'source_ids': [s['id'] for s in c['segments']]}
    return entry.process_saved(c, r, part, json.dumps(x), pipe.schema(r, c), pipe.VERSION, 'OK')


class ContractIntegrity(unittest.TestCase):
    def test_actual_saved_entry_full_chain_and_source_inputs(self):
        c, r, x = fixture(); part = {'id': 'P01', 'rule_ids': ['R1'], 'source_ids': [s['id'] for s in c['segments']]}
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d); entry.text(dest / 'raw-response.txt', json.dumps(x)); entry.save(dest / 'schema.json', pipe.schema(r, c)); entry.save(dest / 'run.json', {'run_status': 'OK'})
            a = entry.accept_saved_output(c, r, part, dest)
            self.assertTrue(a['analysis_coverage_complete']); self.assertEqual(a['independent_check']['status'], 'OK')
            self.assertEqual(a['conditional_audit']['conditional_rules'][0]['conditional_result'], 'TRUE')
            common = a['learner_inputs']['ce_pairs'][0]['shared_material_blocks']
            self.assertIn('not Nia', json.dumps(common)); self.assertIn('not Nia', next(n['text'] for n in a['learner_inputs']['graph']['nodes'] if n['id'] == 'Q:Q1'))
            self.assertEqual(entry.read(dest / 'formal-answer.json')['answer'], x)
            self.assertEqual((dest / 'raw-response.txt').read_text(), json.dumps(x))

    def test_source_alias_adjacent_and_rule_specific_roles(self):
        c, r, x = fixture(); part = {'id': 'P01', 'rule_ids': ['R1'], 'source_ids': [s['id'] for s in c['segments']]}
        prompt = pipe.proposal_prompt(c, r, part)
        for i, s in enumerate(c['segments'], 1): self.assertIn('SRC:' + str(i) + ' | ' + s['id'] + '\n' + s['text'], prompt)
        self.assertNotIn('Array position n selects', prompt)
        spec = pipe.schema(r, c)['properties']['analyses']['properties']['R1.P1']
        self.assertEqual(spec['properties']['judgments']['items']['properties']['role_objects']['required'], ['tenant'])

    def test_second_duplicate_rejected_in_validator_and_stream(self):
        c, r, x = fixture(); x['analyses']['R1.P1']['records'][0]['refs'] = ['SRC:1', 'SRC:1']
        with self.assertRaises(ValueError): validate(x, pipe.schema(r, c))
        g = ExpansionGuard()
        with self.assertRaises(RepetitionAbort):
            for s in ('{"refs":["SRC:1",', '"SRC:1"'): g.feed(s)
        self.assertEqual(g.hit['count'], 2)
        g = ExpansionGuard(); g.feed('{"first":{"refs":["SRC:1"]},"second":{"refs":["SRC:1"]}}')
        self.assertIsNone(g.hit)

    def test_duplicate_keys_never_last_value_wins(self):
        with self.assertRaises(ValueError): loads('{"analyses":{},"analyses":{}}')

    def test_readable_invalid_interface_still_saved_with_null(self):
        c, r, x = fixture(); part = {'id': 'P01', 'rule_ids': ['R1'], 'source_ids': [s['id'] for s in c['segments']]}
        for raw in ('{}', '[]', '{"analyses":{},"object_links":[],"coverage_limits":[]}'):
            with tempfile.TemporaryDirectory() as d:
                dest = Path(d); entry.text(dest / 'raw-response.txt', raw); entry.save(dest / 'schema.json', pipe.schema(r, c)); entry.save(dest / 'run.json', {'run_status': 'FORMAT_ERROR'})
                result = entry.accept_saved_output(c, r, part, dest)
                self.assertIsNone(result['formal_answer']); self.assertIsNone(entry.read(dest / 'formal-answer.json')['answer'])
                self.assertEqual((dest / 'raw-response.txt').read_text(), raw)

    def test_empty_missing_duplicate_and_explicit_not_analyzed(self):
        c, r, x = fixture()
        z = copy.deepcopy(x); z['analyses'] = {}
        with self.assertRaises(ValueError): validate(z, pipe.schema(r, c))
        self.assertEqual(pipe.coverage(z, r)['missing'], ['R1.P1'])
        a = process(c, r, x); empty = {**a, 'formal_answer': {'analyses': []}, 'analysis_coverage_complete': False}
        self.assertEqual(entry.assemble([empty])['analysis_coverage_status'], 'PARTIAL_ANALYSIS')
        z = copy.deepcopy(x); z['analyses']['R1.P1'].update(analysis_status='NOT_ANALYZED', records=[], objects=[], uses=[], judgments=[], limits=['No available analysis.'])
        a = process(c, r, z); self.assertIsNotNone(a['formal_answer']); self.assertFalse(a['analysis_coverage_complete'])
        self.assertEqual(a['coverage']['explicit_not_analyzed'], ['R1.P1'])

    def test_independent_missing_unit_record_component_and_link_rejected(self):
        c, r, x = fixture(); converted, _ = pipe.convert(x, c, pipe.VERSION)
        for kind in ('analyses', 'records', 'uses', 'judgments', 'components'):
            z = copy.deepcopy(converted)
            if kind == 'analyses': z['analyses'].pop()
            elif kind == 'components': z['analyses'][0]['judgments'][0]['components'].pop()
            else: z['analyses'][0][kind].pop()
            self.assertEqual(checker.check_import(x, z, c, pipe.VERSION)['status'], 'REJECTED', kind)
        old_c, _, old_x = previous_fixture(); old_z, _ = pipe.convert(old_x, old_c, 'V19_5'); old_z['analyses'] = []
        self.assertEqual(checker.check_import(old_x, old_z, old_c, 'V19_5')['status'], 'REJECTED')

    def test_semantic_values_and_full_basis_not_silently_changed(self):
        c, r, x = fixture(); z, _ = pipe.convert(x, c, pipe.VERSION); z['analyses'][0]['judgments'][0]['state'] = 'FALSE'
        self.assertEqual(checker.check_import(x, z, c, pipe.VERSION)['status'], 'REJECTED')
        z, _ = pipe.convert(x, c, pipe.VERSION); z['analyses'][0]['records'][0]['court_level'] = 'Supreme Court'
        self.assertEqual(checker.check_import(x, z, c, pipe.VERSION)['status'], 'REJECTED')
        z, _ = pipe.convert(x, c, pipe.VERSION); z['analyses'][0]['uses'][0]['bindings'][0]['address'] = 'R1.P1::person'
        self.assertEqual(checker.check_import(x, z, c, pipe.VERSION)['status'], 'REJECTED')
        x['analyses']['R1.P1']['judgments'][0]['complete'] = False
        a = process(c, r, x)
        self.assertEqual(a['conditional_audit']['checks'][0]['disposition'], 'CONDITIONALLY_AVAILABLE_USE')
        self.assertEqual(a['conditional_audit']['conditional_rules'][0]['conditional_result'], 'UNKNOWN')

    def test_missing_role_not_filled_from_declared_object(self):
        c, r, x = fixture(); x['analyses']['R1.P1']['judgments'][0]['role_objects']['tenant'] = 'UNMAPPED'
        a = process(c, r, x); self.assertEqual(a['role_coverage'][0]['missing_roles'], ['tenant'])
        self.assertEqual(a['conditional_audit']['premise_judgments'][0]['conditional_state'], 'UNKNOWN')
        self.assertEqual(a['conditional_audit']['raw_records_retained'], 1)

    def test_role_keys_wrong_namespace_and_dynamic_existence(self):
        c, r, x = fixture(); x['analyses']['R1.P1']['uses'][0]['role_objects'] = {'other': 'OBJ:1'}
        with self.assertRaises(ValueError): validate(x, pipe.schema(r, c))
        c, r, x = fixture(); x['analyses']['R1.P1']['uses'][0]['records'] = ['SRC:1']
        with self.assertRaises(ValueError): validate(x, pipe.schema(r, c))
        c, r, x = fixture(); u = x['analyses']['R1.P1']; u['uses'].append(copy.deepcopy(u['uses'][0])); u['uses'][0]['records'] = ['EV:999']
        u['judgments'][0]['uses'] = ['USE:1', 'USE:2']; u['judgments'][0]['components'][0]['alternatives'] = [['USE:1'], ['USE:2']]
        a = process(c, r, x)
        self.assertEqual([z['disposition'] for z in a['conditional_audit']['checks']], ['STRUCTURAL_INVALID', 'CONDITIONALLY_AVAILABLE_USE'])
        self.assertEqual(a['conditional_audit']['conditional_rules'][0]['conditional_result'], 'TRUE')
        self.assertEqual(a['canonical_P']['uses'][0]['records'], [0]); self.assertEqual(len(a['canonical_P']['records']), 1)

    def test_wrong_document_not_relocated_and_open_rules_remain_open(self):
        c, r, x = fixture(); x['analyses']['R1.P1']['uses'][0]['witnesses'][0]['source'] = 'SRC:999'
        a = process(c, r, x); self.assertIsNone(a['formal_answer']); self.assertEqual(a['conditional_audit']['checks'][0]['disposition'], 'STRUCTURAL_INVALID')
        c, r, x = fixture(); r[0]['operator'] = 'OPEN_TEXT'; a = process(c, r, x)
        self.assertEqual(a['conditional_audit']['conditional_rules'][0]['conditional_result'], 'UNKNOWN')
        self.assertTrue(a['conditional_audit']['conditional_rules'][0]['not_executed'])

    def test_notes_scopes_blockers_and_opposition_separate(self):
        c, r, x = fixture(); u = x['analyses']['R1.P1']; u['uses'].append(copy.deepcopy(u['uses'][0])); u['uses'][1]['direction'] = 'OPPOSE'
        u['judgments'][0]['opposition_uses'] = ['USE:2']
        for kind, state in [('NOTE', 'TRUE'), ('STAGE_SCOPE', 'TRUE'), ('BLOCK_SCOPE', 'UNKNOWN'), ('UNMAPPED', 'UNKNOWN')]:
            u['judgments'][0]['necessary_limits'] = [{'kind': kind, 'component': 'WHOLE_JUDGMENT', 'reason': 'Explicit synthetic qualification.', 'refs': ['SRC:2']}]
            a = process(c, r, x); self.assertEqual(a['conditional_audit']['premise_judgments'][0]['conditional_state'], state)
            self.assertEqual(len(a['conditional_audit']['raw_opposition_retained']), 1)

    def test_actual_entry_prediction_changes_use_not_truth_or_role(self):
        c, r, x = fixture(); a = process(c, r, x); p = a['canonical_P']
        changed = pipe.apply_connection_decisions(c, r, p, {'K001': 'UNSUPPORTED'})
        self.assertEqual(changed['checks'][0]['disposition'], 'MODEL_REJECTED_USE')
        self.assertEqual(changed['premise_judgments'][0]['model_state'], 'TRUE')
        self.assertEqual(changed['premise_judgments'][0]['conditional_state'], 'UNKNOWN')
        self.assertEqual(checker.check(c, r, p, {'K001': 'UNSUPPORTED'}, changed)['status'], 'OK')

    def test_actual_boundary_saves_before_pause_no_next_dispatch(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); seen = []
            def perform(slot, dest):
                seen.append(slot['dest']); entry.save(dest / 'run.json', {'run_status': 'OK'}); entry.save(dest / 'formal-answer.json', {'answer': {}})
                entry.save(root / 'PAUSE_REQUESTED.json', {'reason': 'SYNTHETIC_STOP_AFTER_SAVED'})
                return {'run_status': 'OK'}
            self.assertEqual(entry.saved_batch(root, [{'dest': 'one'}, {'dest': 'two'}], perform), 'PAUSED')
            self.assertEqual(seen, ['one']); self.assertFalse((root / 'two').exists())

    def test_actual_runner_strict_contract_failure_saves_null_without_model(self):
        from legal_bench.proof_carrying.local_runtime_v19_6 import Runner, SETTINGS
        runner = Runner.__new__(Runner); runner.settings = dict(SETTINGS); runner.versions = {}; runner.model_config_hash = 'synthetic'; runner.loaded_seconds = 0
        runner.render = lambda prompt: '<think>\n\n</think>'; runner.tokenizer = SimpleNamespace(encode=lambda t: [1]); runner.model = None; runner.processor = None
        sc = {'type': 'array', 'items': {'type': 'integer'}, 'uniqueItems': True}
        raw = '[1,1]'
        def stream(*args, **kwargs):
            yield SimpleNamespace(text=raw, token_ids=[1,2], token=None, generation_tokens=2, prompt_tokens=1, finish_reason='stop')
        with tempfile.TemporaryDirectory() as d, patch('mlx_vlm.generate.stream_generate', stream):
            result = runner.run('synthetic', sc, Path(d), 100, 60, 'NONE')
            self.assertEqual(result['run_status'], 'FORMAT_ERROR'); self.assertEqual((Path(d) / 'raw-response.txt').read_text(), raw)
            self.assertTrue((Path(d) / 'token-ids.json').exists()); self.assertFalse((Path(d) / 'parsed.json').exists())
        # Mocked stream tests saving/validation only; no weights are loaded.


if __name__ == '__main__': unittest.main()
