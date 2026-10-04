"""Continue only unstarted B-P after logging error. Never rerun D or edit outputs."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.pipeline_v12_thinking import ROOT, verify, read, copy
from legal_bench.rules_verdict_v1.source_views import digest, write_new
from legal_bench.rules_verdict_v1.runtime_thinking_v12_logging import ThinkingRunner

frozen = verify()
assert not (ROOT / 'results.json').exists() and not (ROOT / 'runs/B-P-thinking').exists()
droot = ROOT / 'runs/D-thinking'
assert not (droot / 'run.json').exists()
assert (droot / 'parsed.json').exists() and (droot / 'token-ids.json').exists()
assert 'ThinkingSchemaMask is not JSON serializable' in (ROOT / 'execution.log').read_text()
original = Path('legal_bench/rules_verdict_v1/runtime_thinking_v12.py').read_text()
fixed = Path('legal_bench/rules_verdict_v1/runtime_thinking_v12_logging.py').read_text()
assert fixed == original.replace("'actual_parameters': kwargs", "'actual_parameters': dict(kwargs)")
for p in ['legal_bench/rules_verdict_v1/runtime_thinking_v12_logging.py', 'scripts/resume_v12_thinking_logging.py']:
    copy(Path(p), ROOT / 'freeze/logging-only-addendum/code' / p)
write_new(ROOT / 'freeze/logging-only-addendum/config.json', {
    'frozen_before_B': time.time(), 'old_freeze_unchanged': True,
    'change': 'Log metadata owns a copy of parameters. No prompt, model parameters, token generation or legal interface changes.',
    'live_code': {p: digest(Path(p).read_bytes()) for p in ['legal_bench/rules_verdict_v1/runtime_thinking_v12_logging.py', 'scripts/resume_v12_thinking_logging.py']},
    'D_retry': False, 'D_output_not_filled_or_repaired': True,
    'B_prompt_settings_must_equal_original_freeze': True})
parts = read(droot / 'partitioned-token-ids.json')
start = read(droot / 'start.json')
estimated_d = (droot / 'native-budget-events.json').stat().st_mtime - start['started_epoch']
d = {'condition': 'D-thinking', 'off_baseline': 'D', 'run_status': 'RUN_LOG_ERROR', 'answer_status': None,
     'reason': 'Output parsed, but run metadata serialization failed; missing exact duration and memory. Do not count as completed experiment answer.',
     'prompt_tokens': read(ROOT / 'prepared/D-thinking/preflight.json')['input_tokens'],
     'actual_parameters': start['actual_parameters'], 'output_tokens': len(read(droot / 'token-ids.json')),
     'elapsed_seconds': None, 'elapsed_file_timestamp_estimate_seconds': estimated_d,
     'peak_mlx_memory_gb': None, 'peak_rss_gb': None,
     'finish_reason': 'RUN_LOG_ERROR', 'generation_finish_inferred_not_original_metadata': 'stop, because parsed.json exists and token IDs terminate in EOS',
     'generation_final_json_retained_but_experiment_answer_null': True,
     'native_forced_boundary': bool(read(droot / 'native-budget-events.json')),
     'format_repairs': [], 'thinking_is_not_evidence': True,
     **{k + '_tokens': len(v) for k, v in parts.items() if isinstance(v, list)}}
write_new(droot / 'run.json', d)
write_new(ROOT / 'progress/1.json', {'rows': [d], 'logging_error': True, 'no_D_retry': True})

runner = ThinkingRunner(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(), frozen['v11_settings'])
name = 'B-P-thinking'
text = (ROOT / 'prepared' / name / 'prompt.txt').read_text()
assert runner.render(text) == (ROOT / 'prepared' / name / 'rendered.txt').read_text()
write_new(ROOT / 'B-load-after-logging-error.json', {'loaded_seconds': runner.loaded_seconds, 'versions': runner.versions,
          'model_config_hash': runner.model_config_hash, 'actual_template_equals_original_freeze': True})
# Conservative wall-clock deadline also counts the gap while fixing only logging.
remaining = start['started_epoch'] + 1200 - time.time()
if remaining <= 0:
    b = {'run_status': 'SKIPPED', 'answer_status': None, 'reason': 'CONSERVATIVE_SHARED_DEADLINE_EXHAUSTED'}
    write_new(ROOT / 'runs' / name / 'run.json', b)
else:
    b = runner.run_thinking(text, read(ROOT / 'prepared' / name / 'schema.json'), ROOT / 'runs' / name, remaining)
    assert b['actual_parameters'] == frozen['actual_parameters']
b = {'condition': name, 'off_baseline': 'B-P', **b}
write_new(ROOT / 'results.json', {'rows': [d, b], 'new_model_calls': 1 + int('output_tokens' in b),
          'known_exact_inference_seconds': b.get('elapsed_seconds', 0),
          'D_elapsed_unavailable_file_timestamp_estimate': estimated_d,
          'round_inference_estimate_seconds': estimated_d + b.get('elapsed_seconds', 0),
          'logging_only_addendum_after_D_failure': True, 'D_technical_failure_answer_null': True,
          'web_calls': 0, 'retries': 0, 'extra_diagnostic_model_calls': 0,
          'no_next_round': True, 'review_required': True})
write_new(ROOT / 'stop.json', {'reason': 'TWO_CALLS_USED_WITH_D_LOG_ERROR', 'additional_calls': 0,
          'automatic_commit_or_push': False})
