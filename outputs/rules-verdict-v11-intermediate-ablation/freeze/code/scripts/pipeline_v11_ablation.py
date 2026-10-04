"""Frozen six-call intermediate ablation; stop entire round on first failure."""
import ast
import difflib
import json
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import digest, write_new
from legal_bench.rules_verdict_v1.final_v9 import prompt, final_schema, compact_display, expand_display, FINAL, EXAMPLES
from legal_bench.rules_verdict_v1.intermediate_v8 import compact_checks
from legal_bench.rules_verdict_v1.checks_v8 import check_facts

ROOT = Path('outputs/rules-verdict-v11-intermediate-ablation')
V8 = Path('outputs/rules-verdict-v8-paired')
V9 = Path('outputs/rules-verdict-v9-final-examples')
DIAG = Path('outputs/json-constraint-diagnosis-v1')
BASE = 'c59cdaf1fda485a75d31a494d6cc6e01abb799b6'
ORDER = ['D', 'A-notes', 'A-clean', 'B-proposal', 'B-P', 'B-C']
CODE = ['scripts/pipeline_v11_ablation.py',
        'legal_bench/rules_verdict_v1/runtime_constraint_diag_v1.py',
        'legal_bench/mlx_json_constraint.py', 'legal_bench/mlx_json_constraint_v2.py',
        'legal_bench/rules_verdict_v1/repetition_v9.py',
        'legal_bench/rules_verdict_v1/checks_v8.py',
        'legal_bench/rules_verdict_v1/intermediate_v8.py',
        'legal_bench/rules_verdict_v1/intermediate_v7.py',
        'legal_bench/rules_verdict_v1/final_v9.py',
        'legal_bench/rules_verdict_v1/contracts.py',
        'legal_bench/rules_verdict_v1/source_views.py',
        'tests/test_mlx_constraint_v2.py']
read = lambda p: json.loads(p.read_text())

def copy(a, b):
    b.parent.mkdir(parents=True, exist_ok=True)
    if b.exists(): assert a.read_bytes() == b.read_bytes(), str(b)
    else: b.write_bytes(a.read_bytes())

def prepare():
    assert not (ROOT / 'freeze/config.json').exists(), 'Already frozen; do not re-prepare'
    assert read(ROOT / 'gate/regression.json')['passed']
    assert not read(ROOT / 'gate/regression.json')['skipped']
    for p in CODE[1:]:
        published = subprocess.check_output(['git', 'show', BASE + ':' + p])
        assert digest(Path(p).read_bytes()) == digest(published), p
    for name in ['offline-fix-audit.json', 'post-run-token-replay.json']:
        copy(DIAG / name, ROOT / 'gate' / name)
    fixture = read(ROOT / 'gate/offline-fix-audit.json')
    replay = read(ROOT / 'gate/post-run-token-replay.json')
    assert not fixture['invalid_tokens_after_fix'] and fixture['eos_allowed_after_complete']
    assert replay['prefix_tracking_matches_actual_token_ids'] and replay['all_generated_tokens_allowed_by_corrected_mask']
    for relative in ['sources/69305.json', 'prepared/69305/law-package.json',
                     'retrieval/69305/result.json', 'inherited-scope-audit.json']:
        copy(V8 / relative, ROOT / relative)
    source, package = inputs()
    schema = final_schema([x['id'] for x in source['segments']],
                          [x['id'] for x in package['law_segments']])
    assert schema == read(V9 / 'prepared/A/schema.json')
    write_new(ROOT / 'prepared/final-schema.json', schema)
    for method in ['A', 'B']:
        old = V8 / 'runs' / method / 'stage1'
        for name in ['prompt.txt', 'schema.json']:
            copy(old / name, ROOT / 'prepared' / (method + '-stage1') / name)
        copy(old / 'effective-parameters.json', ROOT / 'lineage' / method / 'v8-effective-parameters.json')
        copy(old / 'parsed.json', ROOT / 'lineage' / method / 'v8-intermediate.json')
    write_new(ROOT / 'prepared/D/intermediate.json', {})
    (ROOT / 'prepared/D/prompt.txt').write_text(prompt(source, package, {}))
    guard8 = (V8 / 'freeze/code/legal_bench/rules_verdict_v1/repetition_v8.py').read_text()
    guard9 = Path('legal_bench/rules_verdict_v1/repetition_v9.py').read_text()
    assert guard9.replace(",'explanation'", '') == guard8
    write_new(ROOT / 'runtime-differences.json', {
        'stage1_prompt_schema': 'Exact V8 ACTUAL saved run bytes',
        'sampling': 'Unchanged effective V8 values, same max_tokens3072',
        'generation_mask': 'Published CompositeQuoteEnforcer correction; no schema relaxation',
        'mask_token_history': 'Additional audit recording, no text rewrite',
        'repetition_guard': 'Identical threshold and behavior; v9 additionally monitors explanation, a field absent from both stage1 schemas',
        'final_contract': 'All four use final_v9, same examples and output schema',
        'scope_of_old_new_comparison': 'Diagnostic only, not gold or substitute for final-condition comparisons'})
    frozen_old_runtime = V8 / 'freeze/code/legal_bench/rules_verdict_v1/runtime_v8.py'
    current_runtime = Path('legal_bench/rules_verdict_v1/runtime_constraint_diag_v1.py')
    (ROOT / 'runtime-entry-diff.txt').write_text(''.join(difflib.unified_diff(
        frozen_old_runtime.read_text().splitlines(True), current_runtime.read_text().splitlines(True),
        fromfile=str(frozen_old_runtime), tofile=str(current_runtime))))
    write_new(ROOT / 'protocol.json', {
        'review_parent': BASE, 'case': '69305', 'order': ORDER, 'max_new_calls': 6,
        'max_tokens_each': 3072, 'total_context_budget': 32768, 'round_wall_budget_seconds': 1800,
        'conditions': {'D': {}, 'A-clean': {'proposal': 'NEW_A_NOTES'},
                       'B-P': {'proposal': 'NEW_B_PROPOSAL'},
                       'B-C': {'proposal': 'EXACT_SAME_NEW_B_PROPOSAL',
                               'program_checks': 'check_facts -> compact_checks -> final_v9.compact_display unchanged'}},
        'final_inputs': 'Same final_v9 template, examples, full source and law package; only intermediate material differs',
        'failure_stop': 'Any run_status other than OK, context preflight failure or deterministic check failure stops remaining slots as SKIPPED; no retries, old answers, partial fills or runtime changes',
        'repetition_rule': 'Four nonoverlapping identical contiguous64-character fragments in one JSON string, not necessarily adjacent; reset across fields',
        'web_calls': 0, 'extra_model_diagnostics': 0, 'retries': 0,
        'review': 'One concentrated decisive-source review of final answers after stop/completion; skipped/failed slots have no legal answer or score',
        'comparison_limits': ['D has one call, others two: not same-call-budget baseline',
                              'B-P/B-C difference is net effect of entire check block, not isolated length/authority/attention effect',
                              'Old-new intermediates are diagnostics, not human gold',
                              'Single retrospective exposed case with later legal materials and lower-court information'],
        'publication': 'NO_AUTO_COMMIT_OR_PUSH', 'no_auto_next_round': True})
    write_new(ROOT / 'freeze/templates.json', {'final': FINAL, 'examples': EXAMPLES})
    for p in CODE: copy(Path(p), ROOT / 'freeze/code' / p)
    settings = read(V8 / 'freeze/config.json')['settings']
    for method in ['A', 'B']:
        old = read(ROOT / 'lineage' / method / 'v8-effective-parameters.json')
        expected = {**{k: settings[k] for k in ['temperature', 'top_p', 'top_k', 'min_p', 'repetition_penalty', 'enable_thinking', 'prefill_step_size']}, 'max_tokens': 3072}
        assert old == expected
    write_new(ROOT / 'freeze/config.json', {
        'settings': settings, 'max_tokens': 3072, 'constraint_mode': 'FIXED',
        'actual_parameters': expected, 'mask_source': 'legal_bench/mlx_json_constraint_v2.py',
        'mask_sha256': digest(Path('legal_bench/mlx_json_constraint_v2.py').read_bytes()),
        'files': {str(p): digest(p.read_bytes()) for p in ROOT.rglob('*') if p.is_file()},
        'live_code': {p: digest(Path(p).read_bytes()) for p in CODE}, 'frozen_epoch': time.time()})

def inputs():
    return read(ROOT / 'sources/69305.json'), read(ROOT / 'prepared/69305/law-package.json')

def verify():
    frozen = read(ROOT / 'freeze/config.json')
    for p, value in {**frozen['files'], **frozen['live_code']}.items():
        assert digest(Path(p).read_bytes()) == value, p
    return frozen

def run():
    from legal_bench.rules_verdict_v1.runtime_constraint_diag_v1 import Runner
    frozen = verify()
    assert not (ROOT / 'results.json').exists(), 'Finished round cannot be generated again'
    assert not any((ROOT / 'runs' / name / 'start.json').exists() for name in ORDER), 'Partial round: preserve, do not restart'
    runner = Runner(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(), frozen['settings'])
    source, package = inputs()
    finals = read(ROOT / 'prepared/final-schema.json')
    preflight = {}
    for method in ['A', 'B']:
        text = (ROOT / 'prepared' / (method + '-stage1') / 'prompt.txt').read_text()
        rendered = runner.render(text)
        assert rendered == (V8 / 'runs' / method / 'stage1/rendered.txt').read_text()
        preflight[method + '-stage1'] = len(runner.tokenizer.encode(rendered))
    preflight['D'] = len(runner.tokenizer.encode(runner.render(prompt(source, package, {}))))
    write_new(ROOT / 'freeze/token-preflight.json', {
        'known_input_tokens': preflight, 'dynamic_final_inputs_checked_before_every_call': True,
        'max_output_tokens': 3072, 'total_budget': 32768,
        'full_sources_truncated': False, 'exact_v8_stage1_rendered_inputs': True,
        'versions': runner.versions, 'model_config_hash': runner.model_config_hash,
        'loaded_seconds': runner.loaded_seconds})
    started = time.monotonic()
    rows, materials, stop = [], {}, None
    for name in ORDER:
        verify()
        directory = ROOT / 'runs' / name
        if stop:
            row = {'run_status': 'SKIPPED', 'answer_status': None, 'reason': stop}
            write_new(directory / 'run.json', row)
        else:
            if name in ['A-notes', 'B-proposal']:
                method = name[0]
                text = (ROOT / 'prepared' / (method + '-stage1') / 'prompt.txt').read_text()
                schema = read(ROOT / 'prepared' / (method + '-stage1') / 'schema.json')
            else:
                material = {} if name == 'D' else {'proposal': materials['A']} if name == 'A-clean' else {'proposal': materials['B']}
                if name == 'B-C': material['program_checks'] = materials['checks']
                write_new(ROOT / 'prepared' / name / 'intermediate.json', material)
                text, schema = prompt(source, package, material), finals
            remaining = 1800 - (time.monotonic() - started)
            if remaining <= 0:
                row = {'run_status': 'TIMEOUT', 'answer_status': None, 'reason': 'ROUND_BUDGET_BEFORE_CALL'}
                write_new(directory / 'run.json', row)
            else:
                row = runner.run(text, schema, directory, 3072, remaining, constraint_mode='FIXED')
            if row['run_status'] != 'OK':
                stop = name + ':' + row['run_status']
            else:
                assert row['constraint_mode'] == 'FIXED' and row['schema_mask_calls'] > 0
                if name in ['A-notes', 'B-proposal']:
                    parsed = read(directory / 'parsed.json')
                    materials[name[0]] = parsed
                    write_new(ROOT / 'intermediates' / (name[0] + '-new.json'), parsed)
                    if name == 'B-proposal':
                        try:
                            full, restored = check_facts(parsed, source)
                            compact, mapping = compact_checks(full)
                            display = compact_display(compact)
                            assert expand_display(display) == compact
                            write_new(ROOT / 'checks/full.json', full)
                            write_new(ROOT / 'checks/restored-sources.json', restored)
                            write_new(ROOT / 'checks/compact-v8.json', compact)
                            write_new(ROOT / 'checks/trace-map.json', mapping)
                            write_new(ROOT / 'checks/display-final-v9.json', display)
                            write_new(ROOT / 'checks/display-integrity.json', {
                                'unchanged_existing_functions': True, 'exact_display_roundtrip': True,
                                'all_combinations_kept': len(display['combinations']),
                                'all_distinct_joins_kept': len(display['joins'])})
                            materials['checks'] = display
                        except Exception as exc:
                            stop = 'B-proposal:DETERMINISTIC_CHECK_FAILURE'
                            write_new(ROOT / 'checks/failure.json', {'error': type(exc).__name__ + ':' + str(exc), 'run_status': 'FORMAT_ERROR'})
        rows.append({'slot': name, **row})
        write_new(ROOT / 'progress' / (str(len(rows)) + '.json'), {
            'rows': rows, 'stop_reason': stop, 'elapsed_seconds': time.monotonic() - started})
    write_new(ROOT / 'results.json', {
        'rows': rows, 'new_model_calls': sum('output_tokens' in row for row in rows),
        'web_calls': 0, 'extra_model_diagnostics': 0, 'retries': 0, 'stop_reason': stop,
        'inference_seconds': sum(row.get('elapsed_seconds', 0) for row in rows),
        'round_wall_seconds': time.monotonic() - started,
        'model_load_seconds_excluded_from_inference': runner.loaded_seconds,
        'all_six_complete': stop is None,
        'final_source_review_required': True})
    write_new(ROOT / 'stop.json', {'reason': stop or 'SIX_CALLS_COMPLETED',
        'remaining_skipped': [r['slot'] for r in rows if r['run_status'] == 'SKIPPED'],
        'additional_calls_authorized': 0, 'no_auto_retry_or_next_round': True})

if __name__ == '__main__':
    {'prepare': prepare, 'verify': verify, 'run': run}[sys.argv[1]]()
