import copy
import json
import tempfile
import unittest
from pathlib import Path

from legal_bench.rules_verdict_v1 import runtime_constraint_diag_v1 as old
from legal_bench.rules_verdict_v1 import runtime_quant_v8 as new
from scripts import irac_semantic_v6 as entry


class QuantV8Tests(unittest.TestCase):
    def test_same_generation_and_rendering(self):
        self.assertIs(new.Runner.run, old.Runner.run)
        self.assertIs(new.Runner.render, old.Runner.render)
        self.assertIs(new.Runner.count, old.Runner.count)

    def test_strict_snapshot_and_settings(self):
        cfg = json.loads(Path('outputs/irac-semantic-interface-v6/freeze/config.json').read_text())['settings']
        cfg.update(model=new.MODEL, revision=new.REVISION)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'snapshots' / new.REVISION; path.mkdir(parents=True)
            (path / 'config.json').write_text(json.dumps({k: {'bits': 8, 'group_size': 64, 'mode': 'affine'} for k in ('quantization', 'quantization_config')}))
            self.assertEqual(new.verify_settings(path, cfg), path.resolve())
            for k, bad in [('model', old.SETTINGS['model']), ('revision', old.SETTINGS['revision']),
                           ('enable_thinking', True), ('direct_max_tokens', 4096), ('seed', 7)]:
                c = copy.deepcopy(cfg); c[k] = bad
                with self.assertRaises(ValueError): new.verify_settings(path, c)
            with self.assertRaises(ValueError): new.verify_settings(path.parent / 'wrong', cfg)

    def test_actual_entry_preserves_input_and_failure_null(self):
        olddir = Path('outputs/irac-semantic-interface-v6/runs/112400/A')
        prompt = (olddir / 'prompt.txt').read_text(); schema = json.loads((olddir / 'schema.json').read_text())
        seen = {}
        class Fake:
            def run(self, text, sc, out, **kw):
                seen.update(text=text, schema=sc, kw=kw)
                return {'run_status': 'OUTPUT_TRUNCATED', 'elapsed_seconds': 0}
        with tempfile.TemporaryDirectory() as tmp:
            _, result = entry.execute_slot(Fake(), Path(tmp), '112400', 'A', prompt, schema, 600)
            self.assertIsNone(result['prediction'])
            self.assertTrue(json.loads((Path(tmp) / 'delivery.json').read_text())['passed'])
        self.assertEqual(seen['text'], prompt); self.assertEqual(seen['schema'], schema)
        self.assertEqual(seen['kw'], {'max_tokens': 3072, 'remaining_seconds': 600, 'constraint_mode': 'FIXED'})


if __name__ == '__main__': unittest.main()
