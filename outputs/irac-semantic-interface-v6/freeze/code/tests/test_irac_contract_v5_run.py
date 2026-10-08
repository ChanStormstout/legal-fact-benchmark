import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import irac_contract_v5 as entry
from scripts import irac_contract_v5_run as batch
from legal_bench.irac_application.contract_v5 import compact, expand_compact, address_directory
from legal_bench.irac_application.contract_v5_tasks import prompt, schema


class FakeRunner:
    """File-accurate runner stub; no model weights or generation."""
    def __init__(self, raw, status='OK'):
        self.raw, self.status = raw, status

    def run(self, text, sc, out, **kwargs):
        assert kwargs['constraint_mode'] == 'FIXED'
        (out / 'raw-response.txt').write_text(self.raw)
        (out / 'prompt.txt').write_text(text)
        entry.save(out / 'schema.json', sc)
        return {'run_status': self.status, 'schema_mask_calls': 1, 'elapsed_seconds': 0,
                'offline_replay': True}


class RunV5Tests(unittest.TestCase):
    def base(self):
        m, t, law, sm = entry.inputs('112400')
        addr = next(iter(address_directory(t)))
        sid = next(iter(m['sources']))
        p = {'bindings': [{'id': 'b', 'claim_ids': [t['claims'][0]['id']], 'objects': 'Synthetic object',
                          'event': 'Synthetic arrangement', 'stage': 'Synthetic review', 'refs': [sid]}],
             'evidence': [{'id': 'e1', 'binding_id': 'b', 'record': 'Synthetic recorded statement.',
                           'statement_status': 'TESTIMONY', 'refs': [sid],
                           'uses': [{'condition_address': addr, 'direction': 'SUPPORT', 'use': 'CONDITION_INFERENCE'}]}],
             'limitations': [], 'conditions': [], 'coverage_limits': ['Synthetic interface fixture, not case facts.']}
        return p, m, t, law, sm

    def accept(self, p, m, t, law, sm, stage='P', status='OK'):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            raw = json.dumps(p)
            task = 'proposal' if stage == 'P' else 'final'
            meta, result = batch.execute_slot(FakeRunner(raw, status), out, m['case_id'], stage,
                        prompt(task, m, t, law, sm), schema(task, m, t, law), 1800)
            self.assertEqual((out / 'raw-response.txt').read_text(), raw)
            self.assertTrue(entry.read(out / 'delivery.json')['passed'])
            files = {name: entry.read(out / name) for name in
                     ('import.json', 'checks-full.json', 'evidence-records.json') if (out / name).exists()}
            return result, files

    def test_unbound_evidence_survives_and_independent_use_executes(self):
        p, m, t, law, sm = self.base()
        e2 = copy.deepcopy(p['evidence'][0]); e2.update(id='e2', binding_id='')
        p['evidence'].append(e2)
        result, f = self.accept(p, m, t, law, sm)
        self.assertEqual(result['run_status'], 'OK')
        self.assertEqual([e['id'] for e in f['import.json']['projection']['evidence']], ['e1', 'e2'])
        self.assertEqual(f['import.json']['projection']['evidence'][1]['uses'], [])
        self.assertEqual(f['evidence-records.json'][1]['raw_record'], e2)
        self.assertEqual(len(f['checks-full.json']['evidence_use_checks']), 1)
        self.assertEqual(f['checks-full.json']['conditions'][0]['program_assessment']['status'], 'SUPPORTED')

    def test_no_binding_does_not_erase_evidence_or_abort_final(self):
        p, m, t, law, sm = self.base()
        p['bindings'] = []
        result, f = self.accept(p, m, t, law, sm)
        self.assertEqual(result['run_status'], 'OK')
        self.assertEqual(len(f['evidence-records.json']), 1)
        self.assertEqual(f['checks-full.json']['bindings'], [])
        text, sc, inter = entry.final_task(m['case_id'], 'C', p, f['import.json'], f['checks-full.json'])
        self.assertEqual(inter['proposal'], p)
        self.assertEqual(expand_compact(inter['program_checks'])['evidence_records'][0]['binding_available'], False)
        self.assertTrue(batch.delivery(text, m, law, sm)['passed'])

    def test_invalid_use_array_and_source_preserved_independently(self):
        p, m, t, law, sm = self.base()
        e2 = copy.deepcopy(p['evidence'][0]); e2.update(id='e2', refs=['bad-address'])
        p['evidence'].append(e2)
        p['evidence'][0]['uses'] = None
        result, f = self.accept(p, m, t, law, sm)
        self.assertEqual(result['run_status'], 'OK')
        self.assertEqual([x['raw_record'] for x in f['evidence-records.json']], p['evidence'])
        self.assertEqual(f['import.json']['projection']['evidence'][0]['uses'], [])
        self.assertFalse(f['evidence-records.json'][1]['source_addresses_valid'])
        self.assertEqual(f['checks-full.json']['evidence_use_checks'], [])

    def test_semantically_empty_proposal_is_not_format_failure(self):
        p, m, t, law, sm = self.base()
        p['bindings'] = []; p['evidence'] = []
        result, f = self.accept(p, m, t, law, sm)
        self.assertEqual(result['run_status'], 'OK')
        self.assertTrue(f['import.json']['empty_projection'])
        self.assertEqual(f['checks-full.json']['conditions'], [])

    def test_failure_preserves_null_and_raw(self):
        p, m, t, law, sm = self.base()
        result, f = self.accept(p, m, t, law, sm, status='OUTPUT_TRUNCATED')
        self.assertIsNone(result['prediction'])
        self.assertEqual(result['run_status'], 'OUTPUT_TRUNCATED')
        self.assertEqual(f, {})

    def test_batch_failure_only_blocks_dependent_slots(self):
        calls = []
        class BatchFake:
            versions = {}; loaded_seconds = 0; model_config_hash = 'synthetic'
            def __init__(self, *a, **kw): pass
            def run(self, text, sc, out, **kw):
                cid, stage = out.parent.name, out.name
                calls.append((cid, stage))
                entry.save(out / 'start.json', {'fake': True})
                raw = json.dumps({'bindings': [], 'evidence': [], 'limitations': [], 'conditions': [], 'coverage_limits': []}) if stage == 'P' else '{"answers": []}'
                status = 'OUTPUT_TRUNCATED' if cid == '112400' and stage == 'P' else 'OK'
                meta = FakeRunner(raw, status).run(text, sc, out, **kw)
                entry.save(out / 'run.json', meta)
                return meta
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entry.save(root / 'freeze/config.json', {'code_hashes': {}, 'material_hashes': {},
                'engineering_gate': {'E': 'PASS'}, 'settings': {}})
            for cid in batch.CASES:
                m, t, law, sm = entry.inputs(cid)
                for stage in ('A', 'P'):
                    d = root / 'freeze/tasks' / cid / stage; d.mkdir(parents=True)
                    task = 'proposal' if stage == 'P' else 'final'
                    (d / 'prompt.txt').write_text(prompt(task, m, t, law, sm))
                    entry.save(d / 'schema.json', schema(task, m, t, law))
            with patch.object(batch, 'R', root), patch('legal_bench.rules_verdict_v1.runtime_constraint_diag_v1.Runner', BatchFake):
                batch.run()
            self.assertEqual(calls, [('112400', 'A'), ('112400', 'P'), ('188721101', 'A'), ('188721101', 'P'), ('188721101', 'B'), ('188721101', 'C')])
            for stage in ('B', 'C'):
                r = entry.read(root / 'runs/112400' / stage / 'result.json')
                self.assertEqual(r['run_status'], 'SKIPPED')
                self.assertIsNone(r['prediction'])
            self.assertFalse((root / 'RUNNING.lock').exists())


if __name__ == '__main__':
    unittest.main()
