"""Bounded V6 semantic interface comparison. No retries, no semantic edits, no new materials."""
import argparse
import datetime
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import irac_semantic_v6 as entry
from legal_bench.irac_application.contract_v5 import display
from legal_bench.irac_application.semantic_v6_tasks import prompt, schema

R = entry.R
CASES = ('112400', '188721101')
ORDER = [(cid, stage) for cid in CASES for stage in ('A', 'P', 'B')]
MAX_TOKENS = {'A': 3072, 'P': 4096, 'B': 3072}
CODE = [
    'scripts/irac_semantic_v6.py', 'scripts/irac_semantic_v6_run.py',
    'scripts/irac_semantic_v6_acceptance.py', 'scripts/irac_semantic_v6_tokenizer.py',
    'legal_bench/irac_application/semantic_v6.py', 'legal_bench/irac_application/semantic_v6_tasks.py',
    'tests/test_irac_semantic_v6.py',
    'scripts/irac_contract_v5.py', 'scripts/irac_contract_v5_run.py',
    'scripts/irac_contract_v5_tokenizer.py',
    'legal_bench/irac_application/contract_v5.py',
    'legal_bench/irac_application/contract_v5_tasks.py',
    'legal_bench/irac_application/pipeline_v4.py',
    'legal_bench/irac_application/pipeline_v4_tasks.py',
    'legal_bench/irac_application/hybrid_v3.py',
    'legal_bench/irac_application/hybrid_v3_tasks.py',
    'legal_bench/irac_application/aligned_logic.py',
    'legal_bench/irac_application/aligned_v2_runtime.py',
    'legal_bench/rules_verdict_v1/runtime_constraint_diag_v1.py',
    'legal_bench/mlx_json_constraint.py', 'legal_bench/mlx_json_constraint_v2.py',
    'legal_bench/rules_verdict_v1/repetition_v9.py',
    'legal_bench/rules_verdict_v1/contracts.py',
    'legal_bench/rules_verdict_v1/source_views.py',
    'tests/test_irac_contract_v5.py', 'tests/test_irac_contract_v5_run.py', 'tests/test_mlx_constraint_v2.py',
]


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def preserved():
    old = entry.read(R / 'registration.json')['old_files']
    changed = [p for p, h in old.items() if not Path(p).is_file() or entry.hf(p) != h]
    return {'passed': not changed, 'files_checked': len(old), 'changed': changed}


def freeze():
    assert not (R / 'freeze/config.json').exists(), 'Frozen already; do not overwrite'
    gate = entry.read(R / 'engineering/acceptance.json')
    assert gate['E'] == 'PASS' and gate['model_calls'] == 0
    assert all(entry.hf(p) == h for p, h in gate['code_hashes'].items())
    assert preserved()['passed']
    files = {}
    for p in CODE:
        dst = R / 'freeze/code' / p
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, dst)
        files[p] = entry.hf(p)
    inputs = {}
    for cid in CASES:
        m, t, law, sm = entry.inputs(cid)
        for p in [Path('outputs/irac-contract-repair-v5/sources') / (cid + '.json'), Path('outputs/irac-contract-repair-v5/templates') / (m['family'] + '.json'),
                  Path('outputs/irac-contract-repair-v5/sources') / (m['family'] + '-law.json'), Path('outputs/irac-contract-repair-v5/input-audit') / (cid + '.json')]:
            inputs[str(p)] = entry.hf(p)
        for stage in ('A', 'P'):
            text = prompt('proposal' if stage == 'P' else 'final', m, t, law, sm)
            sc = schema('proposal' if stage == 'P' else 'final', m, t, law)
            d = R / 'freeze/tasks' / cid / stage
            d.mkdir(parents=True)
            (d / 'prompt.txt').write_text(text)
            entry.save(d / 'schema.json', sc)
            entry.save(d / 'delivery.json', entry.delivery(text, m, law, sm))
    settings = entry.read('outputs/irac-contract-repair-v5/continuation-01/freeze/config.json')['settings']
    # These formerly descriptive fields now agree with explicit per-call limits.
    settings['extract_max_tokens'] = 4096
    settings['direct_max_tokens'] = settings['merge_max_tokens'] = 3072
    protocol = {'version': 'IRAC_SEMANTIC_INTERFACE_V6', 'frozen_at': now(),
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'cases': CASES, 'order': ORDER, 'max_calls': 6, 'max_generation_seconds': 1800,
        'max_tokens': MAX_TOKENS, 'settings': settings, 'constraint_mode': 'FIXED',
        'retry_count': 0, 'web_calls': 0, 'semantic_repairs': False, 'code_hashes': files,
        'material_hashes': inputs, 'engineering_gate': gate,
        'failure_policy': 'A failure only affects A. Technical P failure skips B; local semantic issues do not. Independent slots continue. OOM/framework failure/total time exhaustion stop remaining slots. No retries or old answers.',
        'dynamic_prompts': 'B assembled once only from the unchanged actual P by frozen final_task, with no program checks; saved and audited before each call; no editing after first generation.',
        'repetition_guard': 'At least 64-character identical substring occurs four times inside one JSON free-text string; occurrences need not be consecutive; state spans streaming chunks, never fields.',
        'evaluation': {'E': 'Evidence relevance never automatically becomes condition truth; source roles, independent records, local uses/limits, explicit model premises for AND/OR/NOT, exact-once request answers, real-entry delivery/save; not semantic truth.',
          'M': 'Once after batch: actual arrangements versus legal questions; attribution, objects, directions, independent records and declared uses; no full reannotation.',
          'L': 'Once after batch: decisive allowed facts and opposing evidence including uncited content, court stages, law scope, condition polarity, reason/prediction consistency and real gaps. Model-assisted source review, no human gold, no historical-verdict target.'},
        'A_reuse': 'Not compatible: final completeness schema and final contract, source role catalogue and P interface changed. Six new calls; no old answers reused.',
        'stop': 'After up to six calls and one concentrated review; no semantic rerun, GNN, new cases/law, SEALED, commit or push.'}
    entry.save(R / 'freeze/config.json', protocol)
    entry.save(R / 'freeze/preservation.json', preserved())
    print('FROZEN', entry.hf(R / 'freeze/config.json'))


def run():
    cfg = entry.read(R / 'freeze/config.json')
    for p, h in dict(cfg['code_hashes'], **cfg['material_hashes']).items():
        assert entry.hf(p) == h, 'Frozen mismatch: ' + p
    assert cfg['engineering_gate']['E'] == 'PASS'
    lock = R / 'RUNNING.lock'
    with lock.open('x') as f:
        import os
        f.write(str(os.getpid()))
    runner = None
    rows = []
    spent = 0.0
    fatal = None
    started = now()
    try:
        for cid, stage in ORDER:
            out = R / 'runs' / cid / stage
            out.mkdir(parents=True, exist_ok=True)
            if (out / 'result.json').exists():
                result = entry.read(out / 'result.json')
                meta = entry.read(out / 'run.json') if (out / 'run.json').exists() else {}
                spent += meta.get('elapsed_seconds', 0)
                if meta.get('run_status') in ('OUT_OF_MEMORY', 'UNSUPPORTED', 'TIMEOUT'):
                    fatal = 'REUSED_FATAL_' + meta['run_status']
                rows.append(dict(case_id=cid, stage=stage, result=result, reused=True))
                continue
            if (out / 'start.json').exists():
                fatal = 'INTERRUPTED_ATTEMPT_NOT_RETRIED'
            reason = fatal or ('TOTAL_GENERATION_BUDGET_EXHAUSTED' if spent >= 1800 else None)
            pdir = R / 'runs' / cid / 'P'
            if stage == 'B':
                pr = entry.read(pdir / 'result.json') if (pdir / 'result.json').exists() else {}
                if pr.get('prediction') is None:
                    reason = reason or 'DEPENDENCY_P_TECHNICAL_FAILURE'
            if reason:
                result = {'case_id': cid, 'method': stage, 'run_status': 'SKIPPED', 'prediction': None, 'reason': reason}
                entry.save(out / 'result.json', result)
                rows.append(dict(case_id=cid, stage=stage, result=result, called=False))
                continue
            if stage in ('A', 'P'):
                d = R / 'freeze/tasks' / cid / stage
                text, sc = (d / 'prompt.txt').read_text(), entry.read(d / 'schema.json')
            else:
                text, sc, inter = entry.final_task(cid, pr['prediction'])
                entry.save(out / 'intermediate.json', inter)
            if runner is None:
                from legal_bench.rules_verdict_v1.runtime_constraint_diag_v1 import Runner
                model = Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip()
                runner = Runner(model, settings=cfg['settings'])
                entry.save(R / 'environment.json', {'versions': runner.versions, 'model_path': model,
                    'model_config_hash': runner.model_config_hash, 'loaded_seconds': runner.loaded_seconds,
                    'settings': cfg['settings']})
            meta, result = entry.execute_slot(runner, out, cid, stage, text, sc, 1800 - spent)
            spent += meta.get('elapsed_seconds', 0)
            rows.append(dict(case_id=cid, stage=stage, result=result, called=True))
            entry.save(R / 'progress.json', {'started': started, 'updated': now(), 'elapsed_generation_seconds': spent, 'slots': rows})
            if meta['run_status'] in ('OUT_OF_MEMORY', 'UNSUPPORTED', 'TIMEOUT'):
                fatal = 'RESOURCE_OR_FRAMEWORK_STOP:' + meta['run_status']
        entry.save(R / 'run-summary.json', {'started': started, 'finished': now(), 'elapsed_generation_seconds': spent,
            'generation_calls': sum((R / 'runs' / c / s / 'start.json').exists() for c, s in ORDER),
            'slots': rows, 'fatal_stop': fatal, 'retries': 0, 'web_calls': 0})
    except Exception as exc:
        import traceback
        entry.save(R / 'entry-failure.json', {'time': now(), 'error': repr(exc), 'traceback': traceback.format_exc(),
                   'completed_slots': rows, 'elapsed_generation_seconds': spent})
        # Unexpected framework/storage failures never turn into UNKNOWN and
        # never erase attempts or imply that independent slots were completed.
        for cid, stage in ORDER:
            out = R / 'runs' / cid / stage
            if not (out / 'result.json').exists():
                attempted = (out / 'start.json').exists()
                entry.save(out / 'result.json', {'case_id': cid, 'method': stage,
                    'run_status': 'RUN_LOG_ERROR' if attempted else 'SKIPPED', 'prediction': None,
                    'reason': 'FRAMEWORK_OR_ENTRY_FAILURE:' + repr(exc)})
        raise
    finally:
        lock.unlink()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=('freeze', 'run', 'preserved'))
    args = ap.parse_args()
    result = globals()[args.command]()
    if result is not None:
        print(json.dumps(result))
