"""Bounded V5 continuation. No retries, no semantic edits, no new materials."""
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
from scripts import irac_contract_v5 as entry
from legal_bench.irac_application.contract_v5 import display, expand_compact
from legal_bench.irac_application.contract_v5_tasks import prompt, schema

R = entry.R / 'continuation-01'
CASES = ('112400', '188721101')
ORDER = [(cid, stage) for cid in CASES for stage in ('A', 'P', 'B', 'C')]
MAX_TOKENS = {'A': 3072, 'P': 4096, 'B': 3072, 'C': 3072}
CODE = [
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
    'tests/test_irac_contract_v5.py', 'tests/test_irac_contract_v5_run.py',
]


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def delivery(text, m, law, sm):
    """Audit the actual submitted JSON sections, not merely the template."""
    law_text = text.split('COMMON GIVEN LAW:\n\n', 1)[1].split('\n\nCOMMON LEGAL STRUCTURE:', 1)[0]
    assert json.loads(law_text) == law
    view = json.loads(text.split('COMPLETE ALLOWED CASE MATERIAL:\n\n', 1)[1].split('\n\nTASK:', 1)[0])
    expected, aliases, order = display(m, sm)
    assert view == expected
    by_id = {x['source_id']: x for x in view['records']}
    rows = []
    for sid, s in m['sources'].items():
        a = aliases[sid]
        row = by_id[a['display_id']]
        assert str(row['document_id']) == str(s['document_id']) == str(m['case_id'])
        assert row['text'][slice(*a['char_range'])] == s['text']
        rows.append({'source_id': sid, 'display_id': a['display_id'],
                     'range': a['char_range'], 'text_sha256': entry.digest(s['text']),
                     'exactly_delivered': True})
    return {'passed': True, 'case_id': m['case_id'], 'source_map': rows, 'ordering': order,
            'law_sha256': entry.digest(json.dumps(law, ensure_ascii=False)),
            'prompt_sha256': entry.digest(text), 'new_source_spans': 0,
            'semantic_correctness_verified': False}


def execute_slot(runner, out, cid, stage, text, sc, remaining, allow_legacy=False):
    """Production entry also exercised by deterministic tests with a fake runner."""
    m, t, law, sm = entry.inputs(cid)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    audit = delivery(text, m, law, sm)
    entry.save(out / 'delivery.json', audit)
    meta = runner.run(text, sc, out, max_tokens=MAX_TOKENS[stage],
                      remaining_seconds=remaining, constraint_mode='FIXED')
    result = entry.finish_attempt(meta, out, stage, m, t, law, allow_legacy=allow_legacy)
    if stage == 'P' and result['prediction'] is not None:
        checks = entry.read(out / 'checks-full.json')
        compact = entry.read(out / 'checks-compact.json')
        restored = expand_compact(compact)
        assert restored['conditions'] == checks['conditions']
        assert restored['evidence_records'] == checks['evidence_records']
        entry.save(out / 'display-validation.json', {'passed': True, 'conditions_exact': True,
                    'record_metadata_exact': True, 'model_proposal_unchanged': True})
    return meta, result


def preserved():
    reg = entry.read(R / 'registration.json')
    old = dict(entry.read(entry.R / 'registration.json')['old_files'])
    old.update(reg['preexisting_v5_files'])
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
        for p in [entry.R / 'sources' / (cid + '.json'), entry.R / 'templates' / (m['family'] + '.json'),
                  entry.R / 'sources' / (m['family'] + '-law.json'), entry.R / 'input-audit' / (cid + '.json')]:
            inputs[str(p)] = entry.hf(p)
        for stage in ('A', 'P'):
            text = prompt('proposal' if stage == 'P' else 'final', m, t, law, sm)
            sc = schema('proposal' if stage == 'P' else 'final', m, t, law)
            d = R / 'freeze/tasks' / cid / stage
            d.mkdir(parents=True)
            (d / 'prompt.txt').write_text(text)
            entry.save(d / 'schema.json', sc)
            entry.save(d / 'delivery.json', delivery(text, m, law, sm))
    settings = entry.read(entry.V4 / 'freeze/config.json')['settings']
    # These formerly descriptive fields now agree with explicit per-call limits.
    settings['extract_max_tokens'] = 4096
    settings['direct_max_tokens'] = settings['merge_max_tokens'] = 3072
    protocol = {'version': 'IRAC_V5_CONTINUATION_01', 'frozen_at': now(),
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'cases': CASES, 'order': ORDER, 'max_calls': 8, 'max_generation_seconds': 1800,
        'max_tokens': MAX_TOKENS, 'settings': settings, 'constraint_mode': 'FIXED',
        'retry_count': 0, 'web_calls': 0, 'semantic_repairs': False, 'code_hashes': files,
        'material_hashes': inputs, 'engineering_gate': gate,
        'failure_policy': 'A failure only affects A. Technical P failure skips B/C; local semantic issues do not. Independent slots continue. OOM/framework failure/total time exhaustion stop remaining slots. No retries or old answers.',
        'dynamic_prompts': 'B/C assembled once from the same actual P by frozen final_task; saved and audited before each call; no editing after first generation.',
        'repetition_guard': 'At least 64-character identical substring occurs four times inside one JSON free-text string; occurrences need not be consecutive; state spans streaming chunks, never fields.',
        'evaluation': {'E': 'Entry-level independence, scope isolation, legal addresses, ordering, source delivery and raw persistence; never source truth.',
          'M': 'Once after batch: actual arrangements versus legal questions; attribution, objects, directions, independent records and declared uses; no full reannotation.',
          'L': 'Once after batch: decisive allowed facts and opposing evidence including uncited content, court stages, law scope, condition polarity, reason/prediction consistency and real gaps. Model-assisted source review, no human gold, no historical-verdict target.'},
        'stop': 'After up to eight calls and one concentrated review; no semantic rerun, GNN, new cases/law, SEALED, commit or push.'}
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
            if stage in ('B', 'C'):
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
                text, sc, inter = entry.final_task(cid, stage, pr['prediction'], entry.read(pdir / 'import.json'), entry.read(pdir / 'checks-full.json'))
                entry.save(out / 'intermediate.json', inter)
            if runner is None:
                from legal_bench.rules_verdict_v1.runtime_constraint_diag_v1 import Runner
                model = Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip()
                runner = Runner(model, settings=cfg['settings'])
                entry.save(R / 'environment.json', {'versions': runner.versions, 'model_path': model,
                    'model_config_hash': runner.model_config_hash, 'loaded_seconds': runner.loaded_seconds,
                    'settings': cfg['settings']})
            meta, result = execute_slot(runner, out, cid, stage, text, sc, 1800 - spent)
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
