"""Version actual task/source state; prepared jobs are never counted as submitted."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read, digest, write_new

p = argparse.ArgumentParser()
p.add_argument('--root', default='outputs/benchmark-pilot-v04/sampling-v1')
p.add_argument('--version', required=True)
args = p.parse_args()
root = Path(args.root)
if Path(args.version).name != args.version: raise ValueError('Invalid checkpoint name')
queue = read(root / 'candidate-queue.json')
original = read(root / 'input-manifest.json')
if digest(Path(original['db']).read_bytes()) != original['sha256']:
    raise ValueError('Corpus database changed')
source_paths = sorted((root / 'sources').glob('*/segments.json'))
source_records = [read(path) for path in source_paths]
batches = []
eligibility_counts = {}
resolved_eligibility = {}
for task_path in sorted((root / 'web-tasks').glob('screen-*/task.json')):
    folder = task_path.parent
    bid = folder.name
    task = read(task_path)
    if digest((folder / 'task.txt').read_bytes()) != task['prompt_sha256']:
        raise ValueError('Changed task ' + bid)
    state, submission = 'PREPARED_NOT_SUBMITTED', None
    if (folder / 'submission.json').exists():
        submission = read(folder / 'submission.json')
        if submission.get('prompt_sha256') != task['prompt_sha256']:
            raise ValueError('Submission lacks matching task hash ' + bid)
        state = submission['state']
    attempts = []
    for path in sorted(folder.glob('*/import-manifest.json')):
        result = read(path)
        attempts.append({'path': str(path), 'state': result['state'], 'validation': result['validation']})
    if any(a['validation']['valid'] for a in attempts):
        state = 'ANCHORED_SCREENING_REFERENCE_GROUP_REVIEW_PENDING'
        latest = [a for a in attempts if a['validation']['valid']][-1]
        reference = read(Path(latest['path']).parent / 'screening-reference.json')
        for row in reference['cases']:
            key = row['eligibility']
            eligibility_counts[key] = eligibility_counts.get(key, 0) + 1
            resolved_eligibility[row['case_id']] = key
    batches.append({'batch_id': bid, 'case_ids': task['case_ids'], 'state': state,
                    'submission': submission, 'imports': attempts, 'prompt_sha256': task['prompt_sha256']})
auxiliary = []
for path in sorted((root / 'web-tasks').glob('*/task.json')):
    if path.parent.name.startswith('screen-'): continue
    attempts = [read(p) for p in sorted(path.parent.glob('*/import-manifest.json'))]
    auxiliary.append({'task': str(path), 'submission': read(path.parent / 'submission.json')
                      if (path.parent / 'submission.json').exists() else None, 'imports': attempts})
    if read(path).get('task_type') == 'ELIGIBILITY_AND_SOURCE_SCREEN_ONLY':
        for attempt in sorted(path.parent.glob('*/screening-reference.json')):
            manifest = read(attempt.parent / 'import-manifest.json')
            if manifest['validation']['valid']:
                for row in read(attempt)['cases']:
                    if row['case_id'] not in resolved_eligibility: raise ValueError('Review without initial screening')
                    resolved_eligibility[row['case_id']] = row['eligibility']
resolved_counts = {key: list(resolved_eligibility.values()).count(key)
                   for key in sorted(set(resolved_eligibility.values()))}
status = {'phase': 'P0_CHECK_EXPANSION_SOURCE_SCREENING_P3_NOT_FROZEN',
          'target_counts': {'dev': 5, 'check': queue['target_check_cases']},
          'corpus_records': 6954, 'corpus_unchanged': True, 'candidate_count': queue['candidate_count'],
          'source_texts_prepared': len(source_records),
          'printed_pdf_pages': sum(r['completeness_basis']['page_count'] for r in source_records),
          'submitted_batches': sum(b['submission'] is not None for b in batches),
          'structurally_valid_screen_batches': sum(b['state'].startswith('ANCHORED') for b in batches),
          'initial_model_eligibility_counts': eligibility_counts,
          'eligibility_counts_after_versioned_review': resolved_counts,
          'eligibility_counts_are_not_selected_independent_cases': True,
          'implementation_hashes': {str(path): digest(path.read_bytes()) for path in
                                   sorted(Path('legal_bench').glob('*.py')) +
                                   sorted(set(Path('scripts').glob('*screen*.py')) | set(Path('scripts').glob('*group*.py')))},
          'selected_check_cases': 0, 'method_frozen': False, 'sample_frozen': False,
          'new_fact_annotations': 0, 'new_check_experiments': 0, 'paid_api_calls': 0,
          'batches': batches,
          'auxiliary_web_reviews': auxiliary,
          'eligibility_interpretation': 'Prepared sources and screening jobs are not an accepted sample; full-source eligibility and cross-case grouping review are required',
          'sampling_coverage': 'Random ordering within a summary-keyword candidate pool, not all Supreme Court disputes',
          'next': ['Retrieve screening responses and validate source anchors',
                   'Review cross-batch dispute links against all five development cases',
                   'Select the first 100 qualifying independent disputes; extend reserves if needed',
                   'Freeze method, prompts, metrics and sample before fact annotation or algorithm evaluation'],
          'previous_completed_development': 'outputs/benchmark-pilot-v03/experiments/source-reviewed-five-case-v2/report-v2.txt'}
write_new(root / (args.version + '.json'), status)
print(__import__('json').dumps({k: v for k, v in status.items() if k != 'batches'}, ensure_ascii=False))
