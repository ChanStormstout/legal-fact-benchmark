#!/usr/bin/env python3
"""Version supervision after a concentrated source review; never change inputs.

Decisions must be source-reviewed explicitly. Unknown review outcomes are masked,
not repaired into a trainable class. Raw annotations and proposal inputs survive.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def revise(rows_path, decisions_path, out):
    rows = read(rows_path)
    decisions = read(decisions_path)
    if decisions.get('source_review_complete') is not True:
        raise ValueError('SOURCE_REVIEW_NOT_COMPLETE')
    if any(r['split'] not in ('TRAIN', 'DEV') for r in rows):
        raise ValueError('TEST_NOT_ALLOWED')
    index = {r['key']: r for r in rows}
    if len(index) != len(rows):
        raise ValueError('DUPLICATE_ROW')
    changes = decisions['changes']
    if len({x['key'] for x in changes}) != len(changes):
        raise ValueError('DUPLICATE_DECISION')
    revised = copy.deepcopy(rows)
    revised_index = {r['key']: r for r in revised}
    for change in changes:
        row = revised_index[change['key']]
        if row['label'] != change['old_label']:
            raise ValueError('STALE_LABEL:' + row['key'])
        if change['new_label'] not in ('USABLE', 'UNUSABLE', 'UNRESOLVED', 'UNLABELED'):
            raise ValueError('INVALID_LABEL')
        if not change.get('basis') or not change.get('source_refs'):
            raise ValueError('UNSUPPORTED_REVISION')
        row['original_supervision'] = {k: copy.deepcopy(row[k]) for k in
                                       ('label', 'basis', 'refs', 'review_sha256')}
        row['label'] = change['new_label']
        row['basis'] = change['basis']
        row['revision_refs'] = change['source_refs']
        row['supervision_revision'] = 'SOURCE_REVIEW_V2_NOT_HUMAN_GOLD'
        if row['label'] == 'UNLABELED':
            row['supervision_mask_reason'] = change['basis']
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    save(out / 'rows.json', revised)
    save(out / 'revision.json', {
        'original_rows': str(rows_path), 'decisions': str(decisions_path),
        'original_sha256': hashlib.sha256(Path(rows_path).read_bytes()).hexdigest(),
        'decision_sha256': hashlib.sha256(Path(decisions_path).read_bytes()).hexdigest(),
        'changes': changes, 'proposal_graph_and_pairs_changed': False,
        'test_read': False, 'performance_used': False,
    })


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rows', required=True)
    parser.add_argument('--decisions', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    revise(args.rows, args.decisions, args.out)
