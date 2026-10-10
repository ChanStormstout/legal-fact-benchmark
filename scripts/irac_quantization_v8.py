"""Two immutable A-only attempts. No prompt changes, semantic repairs or retry."""
import argparse
import datetime
import hashlib
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import irac_semantic_v6 as entry
from scripts.irac_semantic_v6_run import CODE as V6_CODE
from legal_bench.rules_verdict_v1.runtime_quant_v8 import MODEL, REVISION, VERSIONS, Runner

ROOT = Path('outputs/irac-quantization-v8')
BASE = Path('outputs/irac-semantic-interface-v6')
CASES = ('112400', '188721101')
CODE = V6_CODE + ['legal_bench/rules_verdict_v1/runtime_quant_v8.py',
                 'scripts/irac_quantization_v8.py', 'tests/test_irac_quantization_v8.py']


def read(p):
    return json.loads(Path(p).read_text())


def save(p, value):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def hf(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def freeze():
    assert not (ROOT / 'freeze/config.json').exists()
    gate = read(ROOT / 'engineering/acceptance.json')
    assert gate['passed'] and gate['skipped_tests'] == 0 and gate['model_calls'] == 0
    env = read(ROOT / 'environment/model-compatibility.json')
    assert env['comparable'] and env['runtime_versions'] == VERSIONS
    base = read(BASE / 'freeze/config.json')
    for p, h in {**base['code_hashes'], **base['material_hashes']}.items():
        assert hf(p) == h, 'Changed V6 dependency: ' + p
    code = {}
    for p in CODE:
        dst = ROOT / 'freeze/code' / p; dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, dst); code[p] = hf(p)
    tasks = {}; baselines = {}
    for cid in CASES:
        old = BASE / 'runs' / cid / 'A'; dst = ROOT / 'freeze/tasks' / cid
        dst.mkdir(parents=True)
        for name in ('prompt.txt', 'schema.json', 'rendered.txt'):
            shutil.copyfile(old / name, dst / name)
            tasks[str(dst / name)] = hf(dst / name)
        baselines[cid] = {str(old / name): hf(old / name) for name in
                          ('prompt.txt', 'schema.json', 'rendered.txt', 'raw-response.txt', 'run.json', 'result.json', 'effective-parameters.json')}
    settings = dict(base['settings']); settings.update(model=MODEL, revision=REVISION)
    save(ROOT / 'freeze/config.json', {
        'version': 'IRAC_QUANTIZATION_V8', 'frozen_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'workspace_status': subprocess.check_output(['git', 'status', '--short'], text=True),
        'cases': CASES, 'order': [[c, 'A'] for c in CASES], 'max_calls': 2,
        'max_generation_seconds': 1200, 'max_single_seconds': 600, 'max_tokens': 3072,
        'settings': settings, 'constraint_mode': 'FIXED', 'retries': 0, 'web_calls': 0,
        'code_hashes': code, 'material_hashes': base['material_hashes'], 'task_hashes': tasks,
        'baseline_files': baselines, 'model_path': env['model_path'], 'model_file_hashes': env['file_hashes'],
        'gate': gate, 'compatibility': env,
        'stop_policy': 'Single format/truncation/repetition failure does not block the other A. OOM/framework/storage failure or total time exhaustion stops remaining slots. No retry or semantic correction.',
        'evaluation': 'One source review of four final A answers. Preserve decisive fact/status/OR/polarity/contradiction/opposition checks including uncited supplied material. No accuracy estimate, no human gold. Input does not contain review or old answers.',
        'limitations': ['Exposed two-case development diagnostic', 'Same published base_model declaration does not prove identical upstream unquantized SHA', 'No BF16 control', 'No P or GNN contribution tested'],
        'repetition_rule': 'Identical substring of at least 64 characters four times within one JSON text field, not necessarily consecutive. Unchanged V6 guard.',
        'metadata_failure': 'A metadata serialization failure preceded all downloads/generations and is retained separately.'})
    print('FROZEN', hf(ROOT / 'freeze/config.json'), flush=True)


def run():
    cfg = read(ROOT / 'freeze/config.json')
    for p, h in {**cfg['code_hashes'], **cfg['material_hashes'], **cfg['task_hashes']}.items():
        assert hf(p) == h, 'Frozen hash mismatch: ' + p
    # Do not repeat an interrupted or completed batch.
    save(ROOT / 'batch-start.json', {'pid': os.getpid(), 'started_at_epoch': time.time(), 'max_calls': 2})
    runner = None; fatal = None; spent = 0.0; rows = []
    try:
        runner = Runner(cfg['model_path'], cfg['settings'])
        save(ROOT / 'environment/loaded.json', {'seconds': runner.loaded_seconds, 'versions': runner.versions, 'config_hash': runner.model_config_hash})
        # Both complete rendered inputs and IDs checked BEFORE the first generation.
        preflight = []
        for cid in CASES:
            task = ROOT / 'freeze/tasks' / cid
            text = (task / 'prompt.txt').read_text(); rendered = runner.render(text)
            assert rendered.encode() == (task / 'rendered.txt').read_bytes(), 'Rendered input differs from V6'
            ids = runner.tokenizer.encode(rendered)
            assert len(ids) + 3072 <= 32768, 'INPUT_TOO_LONG'
            assert '<think>\n\n</think>' in rendered[-150:]
            save(ROOT / 'preflight' / (cid + '-input-token-ids.json'), ids)
            preflight.append({'case_id': cid, 'input_tokens': len(ids), 'ids_hash': hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
                              'rendered_same_bytes': True, 'v6_ids': 'Deterministically reconstructed from V6 rendered bytes with verified identical tokenizer',
                              'full_sources': entry.delivery(text, *[entry.inputs(cid)[i] for i in (0, 2, 3)])})
        save(ROOT / 'preflight/inputs.json', preflight)
    except Exception as exc:
        fatal = type(exc).__name__ + ': ' + str(exc)
        save(ROOT / 'environment/load-or-preflight-failure.json', {'error': fatal, 'traceback': traceback.format_exc(), 'model_calls': 0})
    for cid in CASES:
        out = ROOT / 'runs' / cid / 'A'; out.mkdir(parents=True, exist_ok=True)
        reason = fatal or ('TOTAL_GENERATION_BUDGET_EXHAUSTED' if spent >= 1200 else None)
        if reason:
            result = {'case_id': cid, 'method': 'A', 'run_status': 'SKIPPED', 'prediction': None, 'reason': reason}
            save(out / 'result.json', result); rows.append({'case_id': cid, 'called': False, 'result': result}); continue
        task = ROOT / 'freeze/tasks' / cid
        begin = time.perf_counter()
        try:
            meta, result = entry.execute_slot(runner, out, cid, 'A', (task / 'prompt.txt').read_text(), read(task / 'schema.json'), min(600, 1200 - spent))
            spent += meta.get('elapsed_seconds', time.perf_counter() - begin)
            rows.append({'case_id': cid, 'called': True, 'result': result, 'elapsed_seconds': meta.get('elapsed_seconds')})
            if meta['run_status'] in ('OUT_OF_MEMORY', 'UNSUPPORTED'):
                fatal = meta['run_status']
        except Exception as exc:
            spent += time.perf_counter() - begin
            fatal = 'ENTRY_OR_STORAGE_ERROR:' + repr(exc)
            if not (out / 'result.json').exists():
                save(out / 'result.json', {'case_id': cid, 'method': 'A', 'run_status': 'RUN_LOG_ERROR', 'prediction': None, 'reason': fatal})
            save(out / 'entry-error.json', {'error': fatal, 'traceback': traceback.format_exc()})
            rows.append({'case_id': cid, 'called': (out / 'start.json').exists(), 'result': read(out / 'result.json')})
        save(ROOT / ('progress-' + cid + '.json'), {'rows': rows, 'generation_seconds': spent, 'fatal': fatal})
    save(ROOT / 'batch-result.json', {'rows': rows, 'generation_seconds': spent, 'fatal': fatal,
                                    'model_calls': sum(x['called'] for x in rows), 'retries': 0, 'web_calls': 0})
    print('COMPLETE', spent, 'seconds', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('action', choices=['freeze', 'run'])
    args = parser.parse_args(); globals()[args.action]()
