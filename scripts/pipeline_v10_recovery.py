"""One final A call after constraint repair; compatible completed B reused unchanged."""
import ast
import json
import subprocess
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import digest, write_new

ROOT = Path('outputs/rules-verdict-v10-constraint-recovery')
V9 = Path('outputs/rules-verdict-v9-final-examples')
DIAG = Path('outputs/json-constraint-diagnosis-v1')
CODE = ['scripts/pipeline_v10_recovery.py', 'legal_bench/mlx_json_constraint.py',
        'legal_bench/mlx_json_constraint_v2.py',
        'legal_bench/rules_verdict_v1/runtime_constraint_diag_v1.py',
        'legal_bench/rules_verdict_v1/contracts.py',
        'legal_bench/rules_verdict_v1/source_views.py',
        'legal_bench/rules_verdict_v1/repetition_v9.py']
read = lambda path: json.loads(path.read_text())

def copy(source, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        assert dest.read_bytes() == source.read_bytes(), dest
    else:
        dest.write_bytes(source.read_bytes())

def definitions(path, names):
    return {node.name: ast.dump(node, include_attributes=False)
            for node in ast.parse(path.read_text()).body
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names}

def prepare():
    assert not (ROOT / 'freeze/config.json').exists(), 'Prepared round already exists'
    old_roots = [p for p in Path('outputs').iterdir() if p.is_dir() and
                 (p.name.startswith('rules-verdict-') or p.name == DIAG.name)]
    write_new(ROOT / 'start-audit.json', {
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'branch': subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip(),
        'status': subprocess.check_output(['git', 'status', '--short'], text=True),
        'old_outputs': {str(p): digest(p.read_bytes()) for d in old_roots for p in d.rglob('*')
                        if p.is_file() and '__pycache__' not in p.parts and not str(p).startswith(str(ROOT))}})
    for relative in ['sources/69305.json', 'prepared/69305/law-package.json',
                     'retrieval/69305/result.json', 'inherited-scope-audit.json']:
        copy(V9 / relative, ROOT / relative)
    for method in ['A', 'B']:
        for name in ['prompt.txt', 'schema.json', 'intermediate.json']:
            copy(V9 / 'prepared' / method / name, ROOT / 'prepared' / method / name)
    for p in (V9 / 'inherited').rglob('*'):
        if p.is_file(): copy(p, ROOT / 'inherited' / p.relative_to(V9 / 'inherited'))
    for p in (DIAG / 'runs/FIXED').iterdir():
        if p.is_file(): copy(p, ROOT / 'runs/B' / p.name)
    # The diagnostic fix and current correction have the same executable definitions.
    for name, names in [('legal_bench/mlx_json_constraint_v2.py', ['CompositeQuoteEnforcer', 'SchemaMask']),
                        ('legal_bench/mlx_json_constraint.py', ['tokenizer_data'])]:
        assert definitions(Path(name), names) == definitions(DIAG / 'freeze/code' / name, names)
    for name in ['prompt.txt', 'schema.json']:
        assert (ROOT / 'runs/B' / name).read_bytes() == (ROOT / 'prepared/B' / name).read_bytes()
    b = read(ROOT / 'runs/B/run.json')
    settings = read(V9 / 'freeze/config.json')['settings']
    assert b['settings'] == settings and b['constraint_mode'] == 'FIXED' and b['run_status'] == 'OK'
    write_new(ROOT / 'reuse-audit.json', {
        'B_origin': str(DIAG / 'runs/FIXED'), 'B_raw_unchanged': True,
        'same_V9_prompt_and_schema': True, 'same_settings': True,
        'fixed_mask_and_tokenizer_definitions_identical': True,
        'current_module_change_since_B': 'Removal of unused import only in versioned mask module',
        'old_intermediate_generation_constraint': 'V8 legacy mask; neither intermediate re-extracted',
        'role': 'Recovered final-stage pairing of existing intermediate outputs, not a newly run full two-stage pipeline'})
    write_new(ROOT / 'protocol.json', {
        'case': '69305', 'methods': ['A: V8 text notes then final model',
                                    'B: V8 proposed facts and checks then final model'],
        'new_calls': ['A_FINAL_FIXED_MASK'], 'maximum_new_calls': 1, 'retries': 0, 'web_calls': 0,
        'B': 'Reuse compatible completed FIXED diagnostic call; no generation',
        'max_tokens': 3072, 'total_budget': 32768, 'timeout_seconds': 1200,
        'stop': 'Stop after one A attempt and one concentrated source review. Failure retained; no rerun or prompt change.',
        'evaluation': 'Decisive source facts, statement status, object binding, law scope, counterevidence, gap types and label consistency. Check shared errors, not historical outcome recovery.',
        'scope': 'Exposed retrospective old-case development. Inherited later-law and lower-court-information limits retained.',
        'publication': 'LOCAL_ONLY_NO_COMMIT_OR_PUSH'})
    for name in CODE: copy(Path(name), ROOT / 'freeze/code' / name)
    write_new(ROOT / 'freeze/config.json', {
        'settings': settings, 'max_tokens': 3072,
        'actual_parameters': b['actual_parameters'], 'constraint_mode': 'FIXED',
        'files': {str(p): digest(p.read_bytes()) for p in ROOT.rglob('*') if p.is_file()},
        'live_code': {p: digest(Path(p).read_bytes()) for p in CODE}, 'frozen_at_epoch': time.time()})

def verify():
    frozen = read(ROOT / 'freeze/config.json')
    for name, value in {**frozen['files'], **frozen['live_code']}.items():
        assert digest(Path(name).read_bytes()) == value, name
    return frozen

def run():
    from legal_bench.rules_verdict_v1.runtime_constraint_diag_v1 import Runner
    frozen = verify()
    runner = Runner(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),
                    frozen['settings'])
    text = (ROOT / 'prepared/A/prompt.txt').read_text()
    rendered = runner.render(text)
    assert rendered == (V9 / 'runs/A/rendered.txt').read_text()
    write_new(ROOT / 'freeze/token-preflight.json', {
        'A_input_tokens': len(runner.tokenizer.encode(rendered)), 'output_budget': 3072,
        'total_budget': 32768, 'full_source_truncated': False, 'exact_V9_A_rendered_input': True,
        'versions': runner.versions, 'model_config_hash': runner.model_config_hash})
    a = runner.run(text, read(ROOT / 'prepared/A/schema.json'), ROOT / 'runs/A',
                   3072, 1200, constraint_mode='FIXED')
    b = read(ROOT / 'runs/B/run.json')
    write_new(ROOT / 'results.json', {
        'rows': [{'method': 'A', 'generation_role': 'NEW_CALL', **a},
                 {'method': 'B', 'generation_role': 'REUSED_COMPATIBLE_CALL', **b}],
        'new_model_calls': 1 if 'output_tokens' in a else 0,
        'reused_final_calls': 1, 'web_calls': 0, 'retries': 0,
        'new_inference_seconds': a.get('elapsed_seconds', 0),
        'concentrated_source_review_required': True, 'not_independent_testing': True})
    write_new(ROOT / 'stop.json', {'reason': 'ONE_A_ATTEMPT_FINISHED_NO_MORE_CALLS',
                                 'additional_calls_authorized': 0})

if __name__ == '__main__':
    {'prepare': prepare, 'verify': verify, 'run': run}[sys.argv[1]]()
