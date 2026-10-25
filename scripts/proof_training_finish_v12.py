#!/usr/bin/env python3
"""Finish bookkeeping for the already frozen V12 batch; never generates or fits.

This process only waits for the existing batch status and summarizes saved DEV
predictions. It does not retry training, access TEST, alter labels or publish.
"""
import argparse
import collections
import csv
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'outputs/proof-semantic-search-v12/continuation-02'


def read(path):
    return json.loads(path.read_text())


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def finish():
    batch = RUN / 'training-01'
    frozen = read(batch / 'training-freeze.json')
    rows = read(RUN / 'supervision-35/rows.json')
    if any(r['split'] not in ('TRAIN', 'DEV') for r in rows):
        raise ValueError('NON_TRAIN_DEV_ROW')
    index = {r['key']: r for r in rows}
    results, cases = [], []
    labels = ['USABLE', 'UNUSABLE', 'UNRESOLVED']
    for kind in ['Flat', 'RGCN', 'CrossEncoder']:
        for seed in frozen['seeds']:
            dest = batch / 'runs' / f'{kind}-{seed}'
            completed = dest / 'training-complete.json'
            reloaded = dest / 'dev-reloaded-predictions.json'
            run = dest / 'run.json'
            failure = dest / 'failure.json'
            result = {'method': kind, 'seed': seed, 'answer': None}
            if completed.exists() and reloaded.exists() and run.exists() and read(run)['status'] == 'OK':
                info = read(completed)
                result.update(status='OK', evaluation=info['evaluation'],
                              seconds=info['seconds'], epochs=info.get('epochs'),
                              reload_verified=True,
                              prediction_sha256=hashlib.sha256(reloaded.read_bytes()).hexdigest())
                counter = collections.defaultdict(collections.Counter)
                confusion = collections.Counter()
                for pred in read(reloaded):
                    row = index[pred['key']]
                    if row['split'] != 'DEV' or not row['valid'] or row['label'] == 'UNLABELED':
                        raise ValueError('INVALID_EVALUATION_ROW')
                    actual = row['label']
                    guess = labels[max(range(3), key=lambda i: pred['probabilities'][i])]
                    c = counter[row['case_id']]
                    c['supervised_uses'] += 1
                    c['reference_agreement'] += actual == guess
                    c['false_accepts'] += actual == 'UNUSABLE' and guess == 'USABLE'
                    c['usable_covered'] += actual == guess == 'USABLE'
                    c['usable_total'] += actual == 'USABLE'
                    c['unresolved_preserved'] += actual == guess == 'UNRESOLVED'
                    confusion[actual + '->' + guess] += 1
                result['confusion'] = dict(confusion)
                for case_id, c in counter.items():
                    cases.append({'method': kind, 'seed': seed, 'case_id': case_id, **dict(c)})
            elif failure.exists():
                result.update(status='TECHNICAL_FAILURE', failure=read(failure))
            elif dest.exists():
                result.update(status='INCOMPLETE_FIT', reason='No completed reloaded prediction; retain all partial files.')
            else:
                result.update(status='SKIPPED', reason='Not started within frozen aggregate budget.')
            results.append(result)

    delivery = []
    for path in sorted((batch / 'delivery').glob('*/*/checked.json')):
        obj = read(path)
        outputs = obj.get('requests', [])
        if isinstance(outputs, dict):
            outputs = list(outputs.values())
        states = collections.Counter(x.get('answer', x.get('state', x.get('status', 'UNRECORDED'))) for x in outputs)
        delivery.append({'method_seed': path.parent.parent.name, 'case_id': path.parent.name,
                         'request_rule_outcomes': dict(states), 'file': str(path.relative_to(ROOT))})
    # Explicitly retain the unlearned cached proposal comparison; no new model.
    summary = {'status': 'FIXED_BATCH_FINISHED', 'planned_fits': 9,
               'successful_fits': sum(x['status'] == 'OK' for x in results),
               'results': results, 'per_case': cases, 'delivery': delivery,
               'cached_proposal_baseline': read(RUN / 'dev-cached-proposal-baseline.json'),
               'reference_kind': 'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
               'test_read': False, 'new_legal_answers': 0, 'no_automatic_next_round': True}
    save(RUN / 'training-comparison.json', summary)
    with (RUN / 'training-case-comparison.csv').open('w') as f:
        fields = ['method', 'seed', 'case_id', 'supervised_uses', 'reference_agreement',
                  'false_accepts', 'usable_covered', 'usable_total', 'unresolved_preserved']
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(cases)
    base = (RUN / 'report-zh.md').read_text()
    marker = '## Current Limits and Remaining Steps'
    if marker in base:
        base = base.split(marker)[0]
    base = base.replace('(in progress)', '(finished)').replace(
        'CrossEncoder is running under the same frozen protocol.',
        'CrossEncoder results and failures under the same frozen protocol are preserved.')
    lines = ['## Fixed-Batch Completion Record', '',
             f"Of nine prespecified fit slots, {summary['successful_fits']} were saved and reloaded successfully. Failed or unstarted slots remain preserved without replacement or retry.", '',
             '| Method | Seed | Technical status | Unusable uses falsely accepted | Usable coverage (56) | Training seconds |',
             '|---|---:|---|---:|---:|---:|']
    for result in results:
        e = result.get('evaluation', {})
        seconds = result.get('seconds', result.get('failure', {}).get('seconds'))
        lines.append(f"| {result['method']} | {result['seed']} | {result['status']} | "
                     f"{e.get('false_accepts', 'unavailable')} | {e.get('confirmed_usable_predicted', 'unavailable')} | "
                     f"{round(seconds, 2) if seconds is not None else 'unavailable'} |")
    outcome_counts = collections.Counter()
    for item in delivery:
        outcome_counts.update(item['request_rule_outcomes'])
    lines += ['', 'Downstream request-by-rule-candidate status totals (including repeated methods/seeds, not independent samples):' + json.dumps(dict(outcome_counts), ensure_ascii=False) + '。',
              '', 'Do not expand graph ranking or automatically run TEST or new full legal answers. Three DEV references are limited and original proposals already agree closely. Shared object-link and open-rule gaps remain in full derivation; local use metrics do not establish end-to-end legal benefit. Non-unknown results still need dependency checks, not automatic credit from labels. CrossEncoder and graph methods differ in input form and compute cost, so differences cannot be attributed entirely to graph propagation.',
              '', 'Peak memory was not reliably recorded and remains unavailable; sampled RSS is not a peak estimate. Training logs, weights, reloaded predictions, failures and downstream checks remain local. No commits or pushes.']
    (RUN / 'report-zh.md').write_text(base + '\n'.join(lines) + '\n')
    progress = read(RUN / 'training-progress.json')
    progress.update(status='FIXED_BATCH_FINISHED', successful_fits=summary['successful_fits'],
                    comparison='training-comparison.json', test_read=False)
    save(RUN / 'training-progress.json', progress)
    policy_path = ROOT / 'docs/repository-artifacts.json'
    policy = read(policy_path)
    old_summary = policy['current_review']['summary']
    new_summary = (f"V12 fixed batch finished: 30 TRAIN cases/722 labels and 3 DEV cases/72 labels; 33 review disagreements masked. "
                   f"Of nine fit slots, {summary['successful_fits']} were saved and reloaded successfully. All results and failures remain preserved. "
                   'No TEST or new legal-answer runs; graph expansion remains paused. No commits or pushes.')
    policy['current_review'].update(summary=new_summary, status='FIXED_BATCH_FINISHED')
    save(policy_path, policy)
    state_path = ROOT / 'docs/PROJECT_STATE.json'
    state = read(state_path)
    state['status'] = 'FIXED_BATCH_FINISHED'
    state['current_review'].update(summary=new_summary, status='FIXED_BATCH_FINISHED')
    save(state_path, state)
    for filename in ['README.md', 'docs/EXPERIMENTS.json']:
        path = ROOT / filename
        path.write_text(path.read_text().replace(old_summary, new_summary))
    changelog = ROOT / 'docs/CHANGELOG.md'
    changelog.write_text('## V12 Fixed Three-Method Batch Finished\n\n' + new_summary + '\n\n' + changelog.read_text())
    subprocess.run(['python3', 'scripts/repository_bridge.py', 'prepare'], cwd=ROOT, check=True)
    manifest = read(ROOT / 'review/MANIFEST.json')
    public = [x['path'] for x in manifest['source_files']
              if x['path'].startswith('outputs/proof-semantic-search-v12/continuation-02/')]
    bad = [x for x in public if any(s in x for s in ['/browser/', '/qc/', '/raw/', '/generated/',
                                                     '/supervision-', '/training-01/', 'weights.safetensors'])]
    if bad:
        raise ValueError('SENSITIVE_OR_BULK_PUBLICATION:' + repr(bad))
    save(ROOT / '.bridge/v12-publication-inspection-final.json',
         {'snapshot_id': manifest['snapshot_id'], 'sensitive_or_bulk_inclusion': bad,
          'public_files': len(public), 'passed': True, 'submitted_or_pushed': False})
    subprocess.run(['python3', 'scripts/repository_bridge.py', 'verify'], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--wait', action='store_true')
    args = parser.parse_args()
    status = RUN / 'training-01/status.json'
    if args.wait:
        deadline = read(RUN / 'training-01/training-freeze.json')['deadline_unix'] + 600
        while not status.exists():
            if time.time() >= deadline:
                raise TimeoutError('BATCH_TERMINAL_RECORD_NOT_AVAILABLE')
            time.sleep(30)
    if not status.exists():
        raise ValueError('BATCH_STILL_RUNNING')
    if (RUN / 'training-comparison.json').exists():
        raise FileExistsError('FINAL_SUMMARY_ALREADY_EXISTS')
    finish()


if __name__ == '__main__':
    main()
