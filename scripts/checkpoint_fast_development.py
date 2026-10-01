# coding: utf-8
"""Checkpoint actual submissions/imports/runs without counting prepared tasks as work done."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read, write_new, digest

p = argparse.ArgumentParser()
p.add_argument('--version', required=True)
args = p.parse_args()
r = Path('outputs/development-20-single-pass-v1')
if Path(args.version).name != args.version: raise ValueError('Invalid checkpoint name')
tasks = []
for path in sorted((r / 'web-tasks').glob('extract-*/task.json')):
    t = read(path)
    if digest((path.parent / 'task.txt').read_bytes()) != t['prompt_sha256']:
        raise ValueError('Prompt changed: ' + t['batch_id'])
    submitted = (path.parent / 'submission.json').exists()
    item = {'batch_id': t['batch_id'], 'case_ids': t['case_ids'],
            'state': 'SUBMITTED' if submitted else 'PREPARED_NOT_SUBMITTED',
            'prompt_sha256': t['prompt_sha256'],
            'prompt_characters': len((path.parent / 'task.txt').read_text())}
    if submitted: item['submission'] = read(path.parent / 'submission.json')
    if (path.parent / 'import-v1/manifest.json').exists():
        item['import'] = read(path.parent / 'import-v1/manifest.json')
        item['state'] = 'IMPORTED_WITH_REPORTED_ISOLATIONS'
    tasks.append(item)
status = {'sample_role': 'DEVELOPMENT_ALLOW_METHOD_CHANGES', 'selected_cases': 20,
          'independence_proven': False, 'tasks': tasks,
          'submitted_batches': sum('submission' in t for t in tasks),
          'extracted_cases': sum(len(t.get('import', {}).get('usable_cases', [])) for t in tasks),
          'failed_case_imports': [x for t in tasks for x in t.get('import', {}).get('failures', [])],
          'experiment_runs': [str(path) for path in sorted((r / 'runs').glob('*/summary.json'))],
          'held_out': False, 'formal_check_set_frozen': False,
          'last_program_verification': {'tests_passed': 122, 'added_tests': 14,
                                        'meaning': 'Program semantics only, not legal accuracy'},
          'config_hash': digest(read(r / 'config.json')),
          'code_hashes': {str(path): digest(path.read_bytes()) for path in
                         [Path('legal_bench/fast_development.py'), Path('scripts/run_fast_development.py'),
                          Path('tests/test_fast_development.py')]},
          'label_origin': 'SINGLE_WEB_MODEL_EXTRACTION_NOT_HUMAN_GOLD',
          'next': 'Read saved run results and the fixed small audit; decide the next method revision.' if (r/'web-tasks/pattern-audit-001/import-v1/audit.json').exists() else 'Complete the fixed small pattern audit; extracted cases can already be computed.',
          'pattern_audit': {'submitted': (r/'web-tasks/pattern-audit-001/submission.json').exists(),
                            'imported': (r/'web-tasks/pattern-audit-001/import-v1/audit.json').exists()}}
write_new(r / (args.version + '.json'), status)
print({k: status[k] for k in ['selected_cases', 'submitted_batches', 'extracted_cases', 'experiment_runs']})
