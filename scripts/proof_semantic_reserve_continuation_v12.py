#!/usr/bin/env python3
"""Admit already qualified reserves in their saved order without changing old splits.

Only run after the original TRAIN/DEV queue has finished. This is a data admission
amendment, not a new label, prompt, candidate selection or model method.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.semantic_tasks_v12 import task

ROOT = Path('outputs/proof-semantic-search-v12')


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def admit(active, cid, out_protocol, previous_path=None):
    original = read(active / 'protocol.json')
    if out_protocol.exists():
        raise ValueError('PROTOCOL_DESTINATION_EXISTS')
    previous = read(previous_path) if previous_path else original
    if cid in {x['case_id'] for x in previous['cases']}:
        raise ValueError('ALREADY_ALLOCATED_NO_RESPLIT')
    reserves = [x for x in read(ROOT / 'qualification.json')
                if x['status'] == 'ELIGIBLE_RESERVE_NOT_SELECTED']
    admitted = {x['case_id'] for x in previous['cases']} - {
        x['case_id'] for x in original['cases']}
    remaining = [x for x in reserves if x['case_id'] not in admitted]
    if not remaining or remaining[0]['case_id'] != cid:
        raise ValueError('NOT_NEXT_SAVED_RESERVE')
    dec = remaining[0]
    source_path = Path(dec['source'])
    if sha(source_path) != dec['source_sha256']:
        raise ValueError('SOURCE_VERSION_CHANGED')
    source = read(source_path)
    if source['status'] != 'COMPLETE_RENDERING':
        raise ValueError('SOURCE_NOT_COMPLETE')
    segments = source['segments']
    starts = [i for i, s in enumerate(segments)
              if s['text'].startswith('## ') and ' vs ' in s['text']]
    ends = [i for i, s in enumerate(segments)
            if 'Related AI tags, queries and research notes' in s['text']]
    if len(starts) != 1 or len(ends) != 1 or starts[0] >= ends[0]:
        raise ValueError('BODY_BOUNDARY_NOT_UNIQUE')
    body = segments[starts[0]:ends[0]]
    cache = {}
    for segment in body:
        if segment['source_document'] != cid:
            raise ValueError('DOCUMENT_IDENTITY')
        for provenance in segment['provenance']:
            path = Path(provenance['raw_path'])
            if str(path) not in cache:
                cache[str(path)] = (path.read_text(), sha(path))
            raw, digest = cache[str(path)]
            a, b = provenance['raw_char_range']
            if (digest != provenance['raw_sha256'] or
                    raw[a:b] != segment['text'] or provenance['document_id'] != cid):
                raise ValueError('ORIGINAL_SOURCE_TRACE_FAILED')
    # Read one already TRAIN target contract; no TEST payload or evaluation labels.
    targets = read(ROOT / 'cohort/444449/case.json')['targets']
    case = dict(targets=targets, case_id=cid, title=source['titles'][0],
                source_path=str(source_path), source_sha256=dec['source_sha256'],
                dispute_id=dec['group'], split='TRAIN',
                exposure='QUALIFICATION_ONLY_NOT_METHOD_DEVELOPMENT',
                mechanism=dec['primary_mechanism'], stage=dec['stage'], segments=body)
    dst = ROOT / 'cohort' / cid
    if dst.exists():
        raise ValueError('COHORT_DESTINATION_EXISTS')
    save(dst / 'case.json', case)
    hashes = {}
    for kind in ('proposal', 'reference'):
        text = task(kind, case)
        with (dst / f'{kind}-task.txt').open('x') as stream:
            stream.write(text)
        hashes[kind] = sha(dst / f'{kind}-task.txt')
    save(dst / 'delivery-map.json', dict(source_hash=dec['source_sha256'],
         source_ids=[s['id'] for s in body], all_original_provenance_verified=True,
         task_hashes=hashes, source_address_not_semantic_approval=True))
    item = {k: case[k] for k in ('case_id', 'dispute_id', 'split', 'exposure',
                                  'mechanism', 'stage', 'source_path', 'source_sha256')}
    amended = dict(previous, cases=previous['cases'] + [item],
                   original_protocol_sha256=sha(active / 'protocol.json'),
                   reserve_admission_order=[x['case_id'] for x in reserves],
                   admission_policy='Next already-qualified reserve in saved source order; stop at original data and QC gates or hard budgets. Preserve failed original cases and all TEST allocations.',
                   prompts_changed=False, evaluation_labels_used=False,
                   test_payloads_read=False, max_data_calls=210)
    # New protocol versions are exclusive. The caller supplies the previous via
    # --previous for subsequent admissions; no frozen artifact is overwritten.
    save(out_protocol, amended)
    save(active / f'reserve-admission-{cid}.json', dict(
        at=datetime.now(timezone.utc).isoformat(), case=item,
        qualification_sha256=sha(ROOT / 'qualification.json'),
        candidate_order_sha256=sha(ROOT / 'candidate-order.json'),
        original_protocol_sha256=sha(active / 'protocol.json'),
        protocol_sha256=sha(out_protocol), tasks=hashes,
        detailed_documents_added=0, original_failed_cases_retained=True,
        prior_test_allocations_unchanged=True, semantic_review_status='NOT_STARTED'))
    print(json.dumps({'admitted': cid, 'segments': len(body), 'protocol': str(out_protocol)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--active-root', required=True)
    parser.add_argument('--case', required=True)
    parser.add_argument('--out-protocol', required=True)
    parser.add_argument('--previous')
    args = parser.parse_args()
    admit(Path(args.active_root), args.case, Path(args.out_protocol), Path(args.previous) if args.previous else None)
