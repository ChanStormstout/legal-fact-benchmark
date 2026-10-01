"""Prepare an explicit continuation of the fixed queue, preserving earlier tasks."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read, digest, write_new
from legal_bench.source_screening import import_screen_source, screening_task

p = argparse.ArgumentParser()
p.add_argument('--root', default='outputs/benchmark-pilot-v04/sampling-v1')
p.add_argument('--first-rank', type=int, required=True)
p.add_argument('--last-rank', type=int, required=True)
args = p.parse_args()
root = Path(args.root)
queue = read(root / 'candidate-queue.json')
if not 1 <= args.first_rank <= args.last_rank <= len(queue['cases']):
    raise ValueError('Invalid queue range')
if (args.first_rank - 1) % 10 or args.last_rank % 10:
    raise ValueError('Continuation requires complete ten-case blocks')
policy = read(root / 'sampling-policy.json')
policy['eligibility_interpretation'] = ('Eligibility is based on the tenancy-based request expressly pleaded in the own dispute, including an alleged or denied tenancy. A judicial finding rejecting tenancy does not itself exclude such a request. A redemption/title suit does not become a tenancy eviction request solely because its defendant raises tenancy as a defense. Record this distinction without inventing a proven lease.')
sources, rows = [], []
for row in queue['cases'][args.first_rank-1:args.last_rank]:
    successes, failures = [], []
    for path in sorted((root / 'source-exports').glob(row['case_id'] + '*.json')):
        try:
            parent, source = import_screen_source(read(path), path.read_bytes())
            successes.append((path, parent, source))
        except (ValueError, KeyError) as error:
            failures.append({'path': str(path), 'error': str(error)})
    if len({s[2]['text_sha256'] for s in successes}) != 1:
        raise ValueError('Source unresolved at rank %s: %s' % (row['rank'], failures))
    path, parent, source = successes[0]
    folder = root / 'sources' / row['case_id']
    write_new(folder / 'paragraphs.json', parent)
    write_new(folder / 'segments.json', source)
    sources.append(source)
    rows.append({'case_id': row['case_id'], 'rank': row['rank'], 'export': str(path),
                 'text_sha256': source['text_sha256'], 'page_count': source['completeness_basis']['page_count'],
                 'failed_metadata_alternatives': failures})
prepared = []
for start in range(0, len(sources), 10):
    number = (args.first_rank-1+start)//10+1
    task = screening_task(sources[start:start+10], policy, 'screen-%03d' % number)
    folder = root / 'web-tasks' / task['batch_id']
    write_new(folder / 'task.json', task)
    prompt_path = folder / 'task.txt'
    if prompt_path.exists():
        if digest(prompt_path.read_bytes()) != task['prompt_sha256']: raise ValueError('Prompt changed')
    else: prompt_path.write_text(task['prompt'])
    prepared.append({'batch_id': task['batch_id'], 'case_ids': task['case_ids'],
                     'prompt_sha256': task['prompt_sha256'], 'prompt_file': str(prompt_path.resolve()),
                     'state': task['state']})
name = 'extension-%s-%s' % (args.first_rank, args.last_rank)
write_new(root / (name + '.json'), {'rows': rows, 'prepared': prepared,
           'policy': policy, 'queue_sha256': digest(queue), 'state': 'PREPARED_NOT_SUBMITTED'})
print(__import__('json').dumps({'source_count': len(sources), 'prepared_batches': len(prepared)}))
