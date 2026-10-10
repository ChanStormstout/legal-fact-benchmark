"""Whole-entry delivery checks, not component efficacy experiments."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from legal_bench.proof_carrying.workflow_v7 import ROOT

CLI = ROOT / 'scripts/proof_pipeline_v7.py'
SPEC = ROOT / 'outputs/proof-carrying-pipeline-v7/inputs/789051/spec.json'


class WorkflowDelivery(unittest.TestCase):
    def run_cli(self, *args, ok=True):
        p = subprocess.run([sys.executable, str(CLI), *map(str, args)], capture_output=True, text=True)
        if ok: self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        else: self.assertNotEqual(p.returncode, 0, p.stdout)
        return json.loads(p.stdout)

    def copied_spec(self, folder, cached=True):
        spec = json.loads(SPEC.read_text())
        spec['sources'] = str(SPEC.parent / 'sources.json')
        for entry in spec['cached'].values():
            p = Path(entry['path'])
            entry['path'] = str(p if p.is_absolute() else SPEC.parent / p)
        if not cached: spec['cached'] = {}
        out = folder / 'spec.json'; out.write_text(json.dumps(spec))
        return out

    def test_complete_chain_and_immutable_resume(self):
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t); spec = self.copied_spec(folder); out = folder / 'run'
            completed = self.run_cli('init', '--spec', spec, '--out', out)
            self.assertEqual(completed['status'], 'DELIVERED')
            self.assertGreater(completed['request_count'], 0)
            for name in ('graph.json', 'review-queue.json', 'source-map.json', 'certificate.json', 'index.html', 'analysis.json', 'review-packet.json'):
                self.assertTrue((out / name).exists(), name)
            self.assertTrue(json.loads((out / 'invocation.json').read_text())['independent_process'])
            previous = (out / 'checker-result.json').read_bytes()
            self.assertEqual(self.run_cli('advance', out), completed)
            self.assertEqual((out / 'checker-result.json').read_bytes(), previous)
            self.run_cli('verify', out)
            (out / 'stages/facts/usable.json').write_text('{}')
            self.run_cli('verify', out, ok=False)

    def test_source_to_tasks_and_real_ingress_no_automatic_approval(self):
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t); spec = self.copied_spec(folder, False); out = folder / 'run'
            result = self.run_cli('init', '--spec', spec, '--out', out)
            self.assertEqual(result['status'], 'WAITING_INPUT')
            reference = (out / 'stages/reference/task.txt').read_text()
            self.assertIn('TASK ATTACHMENTS:\n{}', reference)
            self.assertFalse((out / 'stages/derivation/task.txt').exists())
            for kind in ('rules', 'facts', 'derivation'):
                task = json.loads((out / 'stages' / kind / 'task-manifest.json').read_text())
                meta = folder / (kind + '-meta.json')
                meta.write_text(json.dumps({'origin': 'SAVED_FIXTURE_FOR_ENTRY_CHECK_NOT_MODEL_CALL',
                    'submitted_task_sha256': task['prompt_sha256']}))
                result = self.run_cli('ingest', out, kind, '--response', SPEC.parent / (kind + '.json'), '--metadata', meta)
            self.assertEqual(result['status'], 'DELIVERED')
            snapshot = json.loads((out / 'snapshot.json').read_text())
            self.assertEqual(snapshot['reviews'], {'premises': {}, 'rules': {}})
            self.assertFalse(result['legal_approval'])
            self.assertTrue(all(q['answer'] is None or q['answer'] == 'UNKNOWN' for q in json.loads((out / 'checker-result.json').read_text())['requests']))
            self.run_cli('ingest', out, 'facts', '--response', SPEC.parent / 'facts.json', '--metadata', meta, ok=False)

    def test_revision_uses_new_workspace_and_source_conflict_blocks(self):
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t); spec = self.copied_spec(folder); first = folder / 'first'
            self.run_cli('init', '--spec', spec, '--out', first)
            self.run_cli('revise', first, '--spec', spec, '--out', folder / 'second', '--reason', 'Packaging replay; no semantic changes')
            self.assertTrue((folder / 'second/revision.json').exists())
            self.run_cli('verify', first)
            s = json.loads(spec.read_text()); source = json.loads(Path(s['sources']).read_text())
            source[next(iter(source))]['text'] = 'Wrong source text'
            bad = folder / 'bad-source.json'; bad.write_text(json.dumps(source)); s['sources'] = str(bad)
            spec.write_text(json.dumps(s))
            error = self.run_cli('init', '--spec', spec, '--out', folder / 'third', ok=False)
            self.assertIn('SOURCE_INDEX_DOES_NOT_RESTORE_ORIGINAL', error['reason'])
            self.assertFalse((folder / 'third').exists())


if __name__ == '__main__': unittest.main()
