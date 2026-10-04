"""Two final-only thinking calls, immutable inputs, no retries or inference repair."""
import importlib.metadata
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import digest, write_new

ROOT = Path('outputs/rules-verdict-v12-thinking')
OLD = Path('outputs/rules-verdict-v11-intermediate-ablation')
ORDER = [('D-thinking', 'D'), ('B-P-thinking', 'B-P')]
CODE = ['scripts/pipeline_v12_thinking.py', 'legal_bench/rules_verdict_v1/runtime_thinking_v12.py',
        'legal_bench/rules_verdict_v1/thinking_v12.py', 'tests/test_thinking_v12.py',
        'legal_bench/rules_verdict_v1/runtime_constraint_diag_v1.py',
        'legal_bench/mlx_json_constraint.py', 'legal_bench/mlx_json_constraint_v2.py',
        'legal_bench/rules_verdict_v1/repetition_v9.py', 'legal_bench/rules_verdict_v1/contracts.py',
        'legal_bench/rules_verdict_v1/source_views.py']
read = lambda p: json.loads(p.read_text())

def copy(a, b):
    b.parent.mkdir(parents=True, exist_ok=True)
    if b.exists(): assert a.read_bytes() == b.read_bytes(), str(b)
    else: b.write_bytes(a.read_bytes())

def prepare():
    assert not (ROOT / 'freeze/config.json').exists(), 'Already frozen'
    assert 'Ran 9 tests' in (ROOT / 'gate/separation-tests.txt').read_text()
    assert (ROOT / 'gate/separation-tests.txt').read_text().rstrip().endswith('OK')
    assert 'skipped' not in (ROOT / 'gate/separation-tests.txt').read_text()
    from transformers import AutoTokenizer
    from mlx_vlm.prompt_utils import apply_chat_template
    import mlx_vlm
    model_path = Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip()
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model_config = read(Path(model_path) / 'config.json')
    settings = read(OLD / 'freeze/config.json')['settings']
    write_new(ROOT / 'settings.json', dict(settings, enable_thinking=True))
    for rel in ['sources/69305.json', 'prepared/69305/law-package.json', 'retrieval/69305/result.json', 'inherited-scope-audit.json']:
        copy(OLD / rel, ROOT / rel)
    for name, old in ORDER:
        for file in ['prompt.txt', 'schema.json']:
            copy(OLD / 'runs' / old / file, ROOT / 'prepared' / name / file)
        copy(OLD / 'prepared' / old / 'intermediate.json', ROOT / 'prepared' / name / 'intermediate.json')
        for file in ['parsed.json', 'raw-response.txt', 'token-ids.json', 'run.json']:
            copy(OLD / 'runs' / old / file, ROOT / 'lineage' / old / file)
        text = (ROOT / 'prepared' / name / 'prompt.txt').read_text()
        rendered = apply_chat_template(tokenizer, model_config, text, enable_thinking=True, num_images=0, num_audios=0)
        off = apply_chat_template(tokenizer, model_config, text, enable_thinking=False, num_images=0, num_audios=0)
        assert off == (OLD / 'runs' / old / 'rendered.txt').read_text()
        assert off.endswith('<think>\n\n</think>\n\n') and rendered == off[:-len('<think>\n\n</think>\n\n')] + '<think>\n'
        (ROOT / 'prepared' / name / 'rendered.txt').write_text(rendered)
        write_new(ROOT / 'prepared' / name / 'preflight.json', {
            'input_tokens': len(tokenizer.encode(rendered)), 'max_generation_tokens': 8192,
            'total_budget': 32768, 'no_source_truncation': True,
            'thinking_open': rendered.endswith('<think>\n'), 'legal_prompt_exact_V11': True,
            'rendered_change_only_thinking_suffix': True})
    assert set(read(ROOT / 'prepared/B-P-thinking/intermediate.json')) == {'proposal'}
    copy(OLD / 'intermediates/B-new.json', ROOT / 'inherited/B-proposal.json')
    assert read(ROOT / 'prepared/B-P-thinking/intermediate.json')['proposal'] == read(ROOT / 'inherited/B-proposal.json')
    write_new(ROOT / 'protocol.json', {
        'case': '69305', 'conditions': [x[0] for x in ORDER], 'max_calls': 2,
        'max_generation_each': 8192, 'native_thinking_budget': 4096,
        'separate_final_budget_parameter': False, 'final_3072_reserved': False,
        'native_forcing_semantics': 'Counter > budget; one additional ordinary token, forced newline, then forced </think>. Exact generated partition recorded. No forced JSON/text repair.',
        'generation_time_limit_seconds': 1200, 'web_calls': 0, 'retries': 0,
        'extra_model_diagnostic_calls': 0, 'new_intermediate_calls': 0,
        'failure_policy': 'Single format/truncation/repetition failure does not cancel B-P. Resource/framework failure or exhausted shared inference time stops subsequent call as SKIPPED.',
        'evaluation': 'One final-source review; thinking not evidence. Compare each final to its V11 off baseline, not a single-case accuracy ranking.',
        'scope': 'Retrospective exposed development, later authority, lower-court information and inherited target-origin formula restrictions',
        'publication': 'NO_COMMIT_NO_PUSH_NO_NEXT_ROUND'})
    write_new(ROOT / 'evaluation-rules.json', {
        'reference': 'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
        'checks': ['party allegations versus court adoption', 'retained lower-court findings and their limited appellate status',
                   'contract clause existence versus transaction scope versus statutory written consent',
                   'objects and transfer mode/direction', 'point assessment explanation reason consistency',
                   'omitted counterevidence or indiscriminate unknown', 'new errors'],
        'no_reasoning_correctness_scoring': True, 'no_full_intermediate_annotation': True,
        'review_targets_not_added_to_model_prompts': True})
    for p in CODE: copy(Path(p), ROOT / 'freeze/code' / p)
    pkg = Path(mlx_vlm.__file__).parent
    write_new(ROOT / 'framework-audit.json', {
        'package_versions': {name: importlib.metadata.version(name) for name in ['mlx-vlm', 'mlx', 'mlx-metal', 'lm-format-enforcer', 'transformers']},
        'framework_file_hashes': {rel: digest((pkg / rel).read_bytes()) for rel in ['generate/ar.py', 'generate/dispatch.py', 'generate/types.py', 'utils.py', 'prompt_utils.py']},
        'mechanism': 'Native ThinkingBudgetCriteria; versioned final-only mask and raw-text demultiplexing; no package edits',
        'mask': 'Unchanged corrected CompositeQuoteEnforcer with empty final prefix',
        'final_repetition_rule': 'Existing v9 same-field four nonoverlapping identical64-character fragments; no reasoning guard',
        'real_token_ids': {'start': tokenizer.encode('<think>', add_special_tokens=False), 'end': tokenizer.encode('</think>', add_special_tokens=False)},
        'no_model_pre_run': True})
    write_new(ROOT / 'freeze/config.json', {
        'v11_settings': settings, 'effective_max_tokens': 8192, 'thinking_budget': 4096,
        'actual_parameters': {**{k: settings[k] for k in ['temperature', 'top_p', 'top_k', 'min_p', 'repetition_penalty', 'prefill_step_size']},
                              'enable_thinking': True, 'max_tokens': 8192, 'thinking_budget': 4096,
                              'thinking_start_token': '<think>', 'thinking_end_token': '</think>'},
        'files': {str(p): digest(p.read_bytes()) for p in ROOT.rglob('*') if p.is_file()},
        'live_code': {p: digest(Path(p).read_bytes()) for p in CODE}, 'frozen_epoch': time.time()})

def verify():
    frozen = read(ROOT / 'freeze/config.json')
    for p, h in {**frozen['files'], **frozen['live_code']}.items(): assert digest(Path(p).read_bytes()) == h, p
    return frozen

def run():
    from legal_bench.rules_verdict_v1.runtime_thinking_v12 import ThinkingRunner
    frozen = verify()
    assert not (ROOT / 'results.json').exists() and not (ROOT / 'runs').exists(), 'No repeats, completed or partial'
    runner = ThinkingRunner(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(), frozen['v11_settings'])
    for name, old in ORDER:
        actual = runner.render((ROOT / 'prepared' / name / 'prompt.txt').read_text())
        assert actual == (ROOT / 'prepared' / name / 'rendered.txt').read_text(), 'Actual processor template differs from frozen tokenizer template'
    write_new(ROOT / 'actual-load-audit.json', {'rendered_templates_verified_actual_processor': True,
              'versions': runner.versions, 'model_config_hash': runner.model_config_hash,
              'loaded_seconds': runner.loaded_seconds})
    rows, stop = [], None
    inference_seconds = 0
    for name, old in ORDER:
        verify()
        remaining = 1200 - inference_seconds
        if stop or remaining <= 0:
            row = {'run_status': 'SKIPPED', 'answer_status': None, 'reason': stop or 'TOTAL_INFERENCE_TIME_EXHAUSTED'}
            write_new(ROOT / 'runs' / name / 'run.json', row)
        else:
            row = runner.run_thinking((ROOT / 'prepared' / name / 'prompt.txt').read_text(),
                  read(ROOT / 'prepared' / name / 'schema.json'), ROOT / 'runs' / name, remaining)
            inference_seconds += row.get('elapsed_seconds', 0)
            if row['run_status'] in ['OUT_OF_MEMORY', 'UNSUPPORTED']:
                stop = name + ':' + row['run_status']
        rows.append({'condition': name, 'off_baseline': old, **row})
        write_new(ROOT / 'progress' / (str(len(rows)) + '.json'), {'rows': rows, 'inference_seconds': inference_seconds, 'stop_reason': stop})
    write_new(ROOT / 'results.json', {'rows': rows, 'new_model_calls': sum('output_tokens' in x for x in rows),
              'inference_seconds': inference_seconds, 'stop_reason': stop,
              'web_calls': 0, 'retries': 0, 'extra_diagnostic_model_calls': 0,
              'no_next_round': True, 'review_required': True})
    write_new(ROOT / 'stop.json', {'reason': stop or 'TWO_CONDITIONS_FINISHED',
              'additional_calls': 0, 'automatic_commit_or_push': False})

if __name__ == '__main__': {'prepare': prepare, 'verify': verify, 'run': run}[sys.argv[1]]()
