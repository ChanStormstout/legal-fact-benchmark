"""Record bounded constraint diagnosis and repair release; never generate or push."""
import csv
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import write_new

ROOT = Path('outputs/json-constraint-diagnosis-v1')
OLD = Path('outputs/rules-verdict-v9-final-examples/runs/B')
read = lambda path: json.loads(path.read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
start = read(ROOT / 'start-audit.json')
changed = [name for name, value in start['old_outputs'].items()
           if not Path(name).is_file() or sha(Path(name)) != value]
assert not changed, changed
frozen = read(ROOT / 'freeze/config.json')
for name, value in frozen['files'].items():
    assert sha(Path(name)) == value, name
live_changes = {name: {'frozen_hash': value, 'current_hash': sha(Path(name))}
                for name, value in frozen['live_code'].items() if sha(Path(name)) != value}
assert set(live_changes) == {'legal_bench/mlx_json_constraint.py',
                             'legal_bench/mlx_json_constraint_v2.py',
                             'tests/test_mlx_constraint_v2.py'}
write_new(ROOT / 'preservation-check.json', {
    'previous_output_files_checked': len(start['old_outputs']),
    'changed_previous_outputs': changed, 'frozen_run_files_unchanged': True,
    'intentional_post_run_public_integration': live_changes,
    'historical_reproduction': 'Use historical frozen source bytes. Live defaults now use the correction; do not reinterpret prior runs.'})
release_files = ['legal_bench/mlx_json_constraint.py', 'legal_bench/mlx_json_constraint_v2.py',
                 'tests/test_mlx_constraint_v2.py', 'scripts/replay_constraint_result_v1.py',
                 'scripts/report_constraint_diagnosis_v1.py']
for name in release_files:
    dest = ROOT / 'release/code' / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    assert not dest.exists()
    dest.write_bytes(Path(name).read_bytes())
write_new(ROOT / 'release/manifest.json', {
    'files': {name: sha(Path(name)) for name in release_files},
    'role': 'Public adapter integration after frozen validation, no additional inference',
    'new_generation_calls_after_integration': 0,
    'tests': 'public-fix-tests.txt: 5 relevant tests passed in project MLX environment'})
results = read(ROOT / 'results.json')
legacy = read(OLD / 'run.json')
replay = read(ROOT / 'post-run-token-replay.json')
legacy_ids = read(OLD / 'token-ids.json')
fixed_ids = read(ROOT / 'runs/FIXED/token-ids.json')
index = next(i for i, (a, b) in enumerate(zip(legacy_ids, fixed_ids)) if a != b)
assert index == replay['first_legacy_disallowed_transition']['position']
write_new(ROOT / 'same-input-comparison.json', {
    'prior_legacy_call_reused': True, 'new_calls': 2,
    'first_legacy_vs_fixed_token_difference': index,
    'legacy_token_id': legacy_ids[index], 'fixed_token_id': fixed_ids[index],
    'matching_token_prefix': legacy_ids[:index] == fixed_ids[:index],
    'same_prompt_schema_rendered_input': all(
        (ROOT / 'runs' / mode / name).read_bytes() == (OLD / name).read_bytes()
        for mode in ['NONE', 'FIXED'] for name in ['prompt.txt', 'schema.json', 'rendered.txt']),
    'different_library_or_sampling_settings': False,
    'not_a_new_A_vs_B_legal_comparison': True})
rows = []
for mode, row in [('LEGACY_V9_B_REUSED', legacy)] + [(r['mode'], r) for r in results['rows']]:
    rows.append({'mode': mode, 'case': '69305', 'run_status': row['run_status'],
                 'input_tokens': row['prompt_tokens'], 'output_tokens': row['output_tokens'],
                 'seconds': round(row['elapsed_seconds'], 2),
                 'peak_mlx_memory_gb': row.get('peak_mlx_memory_gb'),
                 'finish_reason': row['finish_reason'],
                 'answer_status': None, 'legal_correctness': 'NOT_SCORED',
                 'raw': str((OLD if mode.startswith('LEGACY') else ROOT / 'runs' / mode) / 'raw-response.txt')})
write_new(ROOT / 'comparison-table.json', {'role': 'SAME_B_INPUT_TECHNICAL_DIAGNOSIS', 'rows': rows})
with (ROOT / 'comparison-table.csv').open('x') as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
write_new(ROOT / 'final-source-review.json', {
    'role': 'TECHNICAL_SOURCE_REVIEW_NOT_NEW_LEGAL_GOLD',
    'basis': ['Installed MLX-VLM 0.7.4 processor/streaming source',
              'Installed LM Format Enforcer 0.11.2 free-text shortcut source',
              'Real tokenizer fixture', 'Frozen input and emitted token replay'],
    'confirmed': ['Fast shortcut omits a legal composite string-ending token.',
                  'Closing standalone quote was allowed; not all quote endings blocked.',
                  'First actual divergence at token42 is legacy-blocked token10152.',
                  'Fixed processor prefix counts match emitted token IDs.',
                  'Decoded actual IDs equal raw, no duplicate append found.',
                  'No-mask and fixed outputs identical and schema-valid.'],
    'limitations': ['Only V9 B on case69305 was rerun; A and earlier failures were not rerun.',
                    'Formatting completion is not legal correctness or proof of structured analysis benefit.',
                    'Generated ground3 says SUPPORTED but its own explanation says unverified. This remains an answer-content issue, untouched by format repair.',
                    'Program tests cover specific delimiter/type/enum/reference-state behaviors, not all possible schema semantics.'],
    'web_calls': 0, 'new_reference_annotations': 0})
(ROOT / 'final-answer-slots.md').write_text(
    '# Constraint Diagnostics on Identical Inputs\n\nThis is not an A/B legal-quality comparison. Both files are final generations from identical V9 B input.\n\n'
    '[Complete output without custom constraints](runs/NONE/parsed.json)；[Complete output with repaired constraints](runs/FIXED/parsed.json)。'
    'Both outputs are byte-identical and finish normally; legal correctness is unscored. V9 retains the original failure.\n', encoding='utf-8')
report = '''JSON constraint diagnosis and minimal repair (69305, development diagnosis)

A valid string-closing token was incorrectly masked by the constraint layer; this was located and repaired. The bounded V9 B comparison supports it as the immediate trigger of this repetition. There is no evidence of an MLX-VLM crash or duplicate appending of streamed text. Model, framework, prompts, schema, and generation settings were retained; legal prompts were not further edited.

Fault location
SchemaMask obtains allowed tokens from LM Format Enforcer 0.11.2. Its JSON free-text fast-path cache covers ordinary text and quote-ending tokens, then dynamically checks only quote-leading tokens. It misses valid tokens beginning with ordinary text/punctuation but containing a closing quote followed by JSON punctuation. Qwen token 10152 is .", . Character-level schema parsing allows it; the original fast path does not. An independent valid-JSON check reproduced the issue. Standalone quote token 1 remains allowed, so string closure is not impossible; the more natural combined closure was excluded.

Actual trace and comparison
Old V9 B and both new successful outputs share their first 42 tokens. At zero-based position 42, the new outputs use 10152 to close the first point. Old constraints exclude it; the old output chooses 1973, keeps extending the string, and triggers repetition stopping. All actual repaired-run tokens are allowed by the repaired parser. Prefix lengths/previous tokens in 642 processor callbacks match actual generation, as does streamed raw text versus token decoding.

Method                               Status              Input tokens Output tokens Seconds
Old V9 B, historical reuse only      REPETITION_ABORT     16983        99            33.90
Same input, no custom constraint     OK                   16983        641           58.84
Same input, repaired constraint      OK                   16983        641           65.54

Both successful outputs are byte-identical, finish_reason=stop, without repetition stops. Strict JSON and original schema checks pass without format repair. max_tokens remains 3072, context 32768, full input untruncated, thinking off. Two new calls, no browser calls/retries; total inference 124.37 seconds. MLX peaks are 7.316/7.319 GB, not whole-machine peaks. Actual IDs, parameters, raw text, and callbacks are saved. Model revision is 8b2b98c00a6b4d291155e4890773ca8f769aee53, MLX-VLM0.7.4, LM Format Enforcer0.11.2; greedy, seed20261001, repetition_penalty1 remain unchanged. No new A run occurred, so this is not a recovered A/B effectiveness comparison.

Repair and validation boundary
Versioned CompositeQuoteEnforcer retains original schema character parsing/fast caching and fully character-checks only omitted compound-quote candidates. The actual tokenizer has 471 such candidates; they are not all admitted, and each must pass the current parser state. Fields are not forcibly closed, schema not relaxed, repeated text not deleted, and answers not completed by the program.

The repair was frozen for these calls before default mlx_json_constraint.py adopted the same enforcer. Runtime and later shared-integration sources are separately saved under freeze/code and release/code. Five tests cover compound closure, required/extra fields, types/enums, escaped quotes, EOS, and shared-entry prefix handling. No extra model calls followed. Old experiments must use their own frozen versions for interpretation/reproduction, not silently rerun under the new default.

What this does not establish
This explains the local technical failure of this B case, not V9 A or every historical truncation/repetition. Complete generation is not legal correctness: the third assessment is SUPPORTED while its explanation says the key relation remains unverified. These semantic errors were not repaired, legal accuracy not reported, and structured superiority over text notes not established. No reference answers, cases, authorities, or browser tasks were added.

Delivery and stopping
comparison-table, post-run-token-replay, same-input-comparison, offline-audit, offline-fix-audit, and runs retain full evidence. preservation-check verifies V1–V9 files unchanged; the shared repair is separately archived. Pregeneration prompts/schema/settings/source hashes are retained. prepare/verify update local review materials only, without commit or push. Both bounded calls are complete; stop this round without automatically launching another experiment.
'''
(ROOT / 'report-zh.txt').write_text(report, encoding='utf-8')
print(json.dumps({'preserved_previous_files': len(start['old_outputs']),
                  'new_calls': results['new_calls'], 'report': str(ROOT / 'report-zh.txt')}, indent=2))
