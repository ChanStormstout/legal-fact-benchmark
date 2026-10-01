"""Convert fetched sources and prepare rank-ordered full-context screening batches."""
import argparse
from pathlib import Path
from legal_bench.core import read, digest, write_new
from legal_bench.source_screening import import_screen_source, screening_task

p = argparse.ArgumentParser()
p.add_argument('--root', default='outputs/benchmark-pilot-v04/sampling-v1')
p.add_argument('--batch-size', type=int, default=10)
args = p.parse_args()
root = Path(args.root)
queue = read(root / 'candidate-queue.json')
policy = read(root / 'sampling-policy.json')
rows, sources = [], []
for row in queue['cases'][:130]:
    paths = sorted((root / 'source-exports').glob(row['case_id'] + '*.json'))
    successes, failures = [], []
    for path in paths:
        try:
            parent, source = import_screen_source(read(path), path.read_bytes())
            successes.append((path, parent, source))
        except (ValueError, KeyError) as error:
            failures.append({'path': str(path), 'error': str(error)})
    hashes = {s[2]['text_sha256'] for s in successes}
    if len(hashes) != 1:
        rows.append({'case_id': row['case_id'], 'rank': row['rank'], 'state': 'SOURCE_IMPORT_REQUIRES_REVIEW', 'failures': failures})
        continue
    path, parent, source = successes[0]
    folder = root / 'sources' / row['case_id']
    write_new(folder / 'paragraphs.json', parent)
    write_new(folder / 'segments.json', source)
    sources.append(source)
    rows.append({'case_id': row['case_id'], 'rank': row['rank'], 'state': 'SOURCE_PAGE_SEQUENCE_VALID_TERMINAL_REVIEW_PENDING',
                 'export': str(path), 'source': str(folder / 'segments.json'), 'text_sha256': source['text_sha256'],
                 'page_count': source['completeness_basis']['page_count'], 'segments': len(source['segments']),
                 'failed_metadata_alternatives': failures})
write_new(root / 'source-import-report-v1.json', {'rows': rows, 'source_count': len(sources), 'verified_full_count': 0,
          'export_files_are_not_original_pdf_bytes': True})
prepared = []
for start in range(0, len(sources), args.batch_size):
    task = screening_task(sources[start:start+args.batch_size], policy, 'screen-%03d' % (start // args.batch_size + 1))
    folder = root / 'web-tasks' / task['batch_id']
    write_new(folder / 'task.json', task)
    prompt_path = folder / 'task.txt'
    if prompt_path.exists():
        if digest(prompt_path.read_bytes()) != task['prompt_sha256']: raise ValueError('Prompt changed')
    else:
        prompt_path.write_text(task['prompt'])
    prepared.append({'batch_id': task['batch_id'], 'case_ids': task['case_ids'], 'prompt_sha256': task['prompt_sha256'],
                     'prompt_file': str(prompt_path.resolve()), 'characters': len(task['prompt']), 'state': task['state']})
write_new(root / 'web-tasks/index.json', prepared)
print(__import__('json').dumps({'source_count': len(sources), 'page_count': sum(r.get('page_count',0) for r in rows),
      'prepared_batches': len(prepared), 'terminal_review_pending': len(sources),
      'source_import_failures': [r['case_id'] for r in rows if 'REQUIRES' in r['state']]}))
