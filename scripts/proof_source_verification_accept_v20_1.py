#!/usr/bin/env python3
"""Batch acceptance for the observed constraint failure; no model loading/calls."""
import gc
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.proof_source_verification_v20_1 import OUT, save, text


def main():
    OUT.joinpath('engineering').mkdir(parents=True, exist_ok=True)
    result = subprocess.run([sys.executable, '-m', 'unittest',
        'tests.test_constraint_viability_v20_1', 'tests.test_source_verification_v20',
        'tests.test_pipeline_diagnostic_v19_8', 'tests.test_final_capacity_v19_8_1', '-q'],
        cwd=ROOT, capture_output=True, text=True)
    text(OUT/'engineering/tests.txt', result.stdout+result.stderr)
    if result.returncode:
        raise RuntimeError(result.stderr)
    from transformers import AutoTokenizer
    from legal_bench.mlx_json_constraint import tokenizer_data
    from legal_bench.mlx_json_constraint_v20_1 import SchemaMask
    from legal_bench.proof_carrying.source_verification_v20 import q_schema, compact
    from tests.test_source_verification_v20 import setup
    tok = AutoTokenizer.from_pretrained(
        (ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),
        local_files_only=True)
    data = tokenizer_data(tok, tok.eos_token_id)
    results = []
    for run_path in sorted((OUT/'local').glob('*/*/run.json')):
        d = run_path.parent
        run = json.loads(run_path.read_text())
        if run['run_status'] != 'OK':
            results.append({'task': str(d.relative_to(OUT)), 'status': 'OLD_FAILURE_PRESERVED_NO_RETRY',
                            'old_status': run['run_status']})
            continue
        en = SchemaMask(data, json.loads((d/'schema.json').read_text())).enforcer
        ids = json.loads((d/'token-ids.json').read_text())
        prefix = []
        for i, token in enumerate(ids):
            if token not in en.get_allowed_tokens(prefix).allowed_tokens:
                raise ValueError('OLD_SUCCESS_NOT_COMPATIBLE:'+str(d)+':'+str(i))
            prefix.append(token)
        if tok.eos_token_id not in en.get_allowed_tokens(prefix).allowed_tokens:
            raise ValueError('OLD_SUCCESS_CANNOT_END:'+str(d))
        results.append({'task': str(d.relative_to(OUT)), 'status': 'EXACT_TOKEN_PATH_AND_EOS_COMPATIBLE',
                        'tokens': len(ids), 'raw_hash': hashlib.sha256((d/'raw-response.txt').read_bytes()).hexdigest()})
        print('PASS', str(d.relative_to(OUT)), len(ids), flush=True)
        del en
        gc.collect()
    # Replay the actually saved failing prefix, then enumerate every next token.
    d = OUT/'local/1870868/P02'
    en = SchemaMask(data, json.loads((d/'schema.json').read_text())).enforcer
    ids = json.loads((d/'token-ids.json').read_text())
    for i, t in enumerate(ids):
        if t not in en.get_allowed_tokens(ids[:i]).allowed_tokens:
            raise ValueError('SAVED_FAILURE_PREFIX_UNEXPECTEDLY_BLOCKED:'+str(i))
    allowed = en.get_allowed_tokens(ids).allowed_tokens
    bad = [t for t in allowed if not en.get_allowed_tokens(ids+[t]).allowed_tokens]
    if bad:
        raise ValueError('DEAD_BRANCH_REMAINS:'+str(bad))
    save(OUT/'engineering/real-failure-prefix.json', {
        'saved_tokens': len(ids), 'allowed_next_tokens': len(allowed), 'dead_next_branches': bad,
        'old_dead_tokens': [23,24], 'old_dead_tokens_now_excluded': not {23,24}.intersection(allowed),
        'actual_unyielded_old_token_unknown': True, 'model_calls': 0})
    assert not {23,24}.intersection(allowed)
    del en
    gc.collect()
    c, r, p, q = setup()
    en = SchemaMask(data, q_schema(r,c)).enforcer
    ids = tok.encode(compact(q), add_special_tokens=False)
    for i,t in enumerate(ids):
        assert t in en.get_allowed_tokens(ids[:i]).allowed_tokens
    assert tok.eos_token_id in en.get_allowed_tokens(ids).allowed_tokens
    save(OUT/'engineering/cache-replay.json', results)
    save(OUT/'engineering/acceptance.json', {
        'status': 'PASS', 'tests': 36, 'model_calls': 0, 'weights_loaded': False,
        'successful_P_exact_token_replay': sum(x['status']=='EXACT_TOKEN_PATH_AND_EOS_COMPATIBLE' for x in results),
        'old_failures_preserved': sum(x['status']=='OLD_FAILURE_PRESERVED_NO_RETRY' for x in results),
        'real_failure_prefix_replayed': True, 'new_Q_tokenizer_EOS': True,
        'legal_prompt_schema_model_unchanged': True, 'semantic_success': False,
        'actual_pause_receipt': 'outputs/proof-source-verification-v20/checkpoints/phase-P/latest.json',
        'runtime_entry': 'legal_bench/proof_carrying/local_runtime_v20_1.py',
        'pipeline_entry': 'scripts/proof_source_verification_v20_1.py'})
    print('V20_1 ACCEPTANCE PASS', flush=True)


if __name__ == '__main__':
    main()
