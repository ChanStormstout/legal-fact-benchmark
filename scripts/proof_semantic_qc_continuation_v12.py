#!/usr/bin/env python3
"""Prepare the single frozen-policy QC sample and audit actual input reconstruction.

This does not assign QC outcomes, repair labels, or open TEST materials.
Run only after the authorized TRAIN/DEV construction batch has ended.
"""
import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.semantic_features_v12 import graph, ce_pairs

ROOT = Path('outputs/proof-semantic-search-v12')


def read(path):
    return json.loads(Path(path).read_text())


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    with path.open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def prepare(rows_path, active, out, protocol_path=None):
    rows = read(rows_path)
    if any(row.get('split') not in ('TRAIN', 'DEV') for row in rows):
        raise ValueError('NON_TRAIN_DEV_ROW')
    policy = read(active / 'qc-policy.json')
    protocol_path = protocol_path or active / 'protocol.json'
    allowed = {c['case_id'] for c in read(protocol_path)['cases']
               if c['split'] in ('TRAIN', 'DEV')}
    if any(row['case_id'] not in allowed for row in rows):
        raise ValueError('OUTSIDE_FROZEN_QUEUE')
    # No filtering by label value, validity, source correctness or prediction.
    def key(row):
        return hashlib.sha256(
            f"{policy['seed']}|{row['dispute_id']}|{row['request_id']}|{row['use_id']}"
            .encode()).hexdigest()
    groups = defaultdict(list)
    for row in rows:
        groups[row['dispute_id']].append(row)
    first = [min(group, key=key) for group in groups.values()]
    if len(first) > policy['count'] or len(rows) < policy['count']:
        raise ValueError('QC_SAMPLE_POLICY_CANNOT_BE_SATISFIED')
    selected_keys = {row['key'] for row in first}
    rest = sorted((row for row in rows if row['key'] not in selected_keys), key=key)
    selected = sorted(first + rest[:policy['count'] - len(first)], key=key)
    out.mkdir(parents=True, exist_ok=False)
    cases = {}
    audit = []
    for cid in sorted({row['case_id'] for row in rows}):
        # The allowlist is checked above before opening any case payload.
        case_path = ROOT / 'cohort' / cid / 'case.json'
        case = read(case_path)
        if case['split'] not in ('TRAIN', 'DEV'):
            raise ValueError('CASE_SPLIT_CONFLICT')
        exemplar = next(row for row in rows if row['case_id'] == cid)
        input_dir = Path(exemplar['proposal_dir'])
        proposal_path = (input_dir.parent / 'resolved-address-v2.json'
                         if input_dir.name == 'address-v2' else input_dir / 'resolved.json')
        proposal = read(proposal_path)
        actual_graph = read(input_dir / 'graph.json')
        actual_pairs = read(input_dir / 'ce-pairs.json')
        # Compare the serialized interface (JSON represents edge tuples as lists).
        rebuilt_graph = json.loads(json.dumps(graph(case, proposal)))
        rebuilt_pairs = json.loads(json.dumps(ce_pairs(case, proposal)))
        audit.append({
            'case_id': cid, 'graph_equal': actual_graph == rebuilt_graph,
            'ce_pairs_equal': actual_pairs == rebuilt_pairs,
            'input_dependencies': {str(p): digest(p) for p in
                                   (case_path, proposal_path, input_dir / 'graph.json',
                                    input_dir / 'ce-pairs.json')},
            'review_loaded_for_reconstruction': False,
            'reference_loaded_for_reconstruction': False,
        })
        if cid in {row['case_id'] for row in selected}:
            cases[cid] = {'case': case, 'raw_proposal': proposal}
    save(out / 'selection.json', {'policy': policy, 'rows_sha256': digest(rows_path),
                                'protocol_path': str(protocol_path), 'protocol_sha256': digest(protocol_path),
                                'selected': selected, 'selection_uses_predictions': False})
    save(out / 'source-pack.json', cases)
    save(out / 'input-label-isolation.json', {
        'passed': all(x['graph_equal'] and x['ce_pairs_equal'] for x in audit),
        'cases': audit, 'test_opened': False,
        'scope': 'Exact reconstruction of actual graph and cross-encoder inputs from case and raw proposal; no supervision or reference dependency.',
    })
    save(out / 'review-instructions.json', {
        'audited': 0, 'status': 'AWAITING_SINGLE_CONCENTRATED_SOURCE_REVIEW',
        'reference_kind': 'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
        'checks': ['statement attribution and court stage', 'objects and scope',
                   'whole-premise usability rather than evidence relevance',
                   'opposition and exceptions', 'real versus invented gaps'],
        'major_error_threshold': policy['major_error_threshold'],
        'systemic_errors_block': True,
        'no_automatic_qc_pass': True,
    })
    print(json.dumps({'selected': len(selected), 'disputes': len(groups),
                      'input_isolation': all(x['graph_equal'] and x['ce_pairs_equal'] for x in audit)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--rows', required=True)
    parser.add_argument('--active-root', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--protocol')
    args = parser.parse_args()
    prepare(Path(args.rows), Path(args.active_root), Path(args.out), Path(args.protocol) if args.protocol else None)
