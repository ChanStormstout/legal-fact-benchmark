"""Explicit split, freeze and evaluation contracts. Never manufacture pending results."""
import copy
import random
from pathlib import Path
from .core import read, digest, canonical, write_new
from .engine import execute
from .sampling import reviewed_dispute_groups


def check_manifest(manifest, complete=False):
    targets = manifest.get('target_counts', {'dev': 5, 'check': 20})
    if (set(targets) != {'dev', 'check'} or targets['dev'] != 5
            or type(targets['check']) is not int or targets['check'] < 1):
        raise ValueError('Invalid target counts: require 5 dev and a positive integer check count')
    cases = manifest['cases']
    ids = [r['case_id'] for r in cases]
    groups = [r['dispute_group'] for r in cases]
    if len(ids) != len(set(ids)) or len(groups) != len(set(groups)):
        raise ValueError('Duplicate cases or dispute groups')
    seen_disputes = set()
    for r in cases:
        if r['split'] not in ['dev', 'check']:
            raise ValueError('Invalid split')
        if not r.get('eligibility_evidence') or not r.get('group_review'):
            raise ValueError('Eligibility and dispute-group review must be documented')
        groups = reviewed_dispute_groups(r)
        if groups & seen_disputes:
            raise ValueError('Related documents share a primary or companion dispute')
        seen_disputes.update(groups)
    if complete:
        counts = {s: sum(r['split'] == s for r in cases) for s in ['dev', 'check']}
        if counts != targets:
            raise ValueError('Freeze requires exactly {} dev + {} check cases'.format(targets['dev'], targets['check']))


def select_split(eligible, dev_ids, seed=20260930, check_count=20):
    if type(check_count) is not int or check_count < 1:
        raise ValueError('check_count must be a positive integer')
    if len(dev_ids) != 5 or len(set(dev_ids)) != 5:
        raise ValueError('Specify 5 reviewed development cases')
    by_id = {r['case_id']: r for r in eligible}
    if len(by_id) != len(eligible) or any(x not in by_id for x in dev_ids):
        raise ValueError('Invalid eligible case list')
    dev = [by_id[x] for x in dev_ids]
    used = set().union(*(reviewed_dispute_groups(x) for x in dev))
    pool = sorted([r for r in eligible if r['case_id'] not in dev_ids and not reviewed_dispute_groups(r) & used], key=lambda x: x['case_id'])
    random.Random(seed).shuffle(pool)
    selected, reserve = [], []
    for r in pool:
        groups = reviewed_dispute_groups(r)
        if groups & used:
            continue
        used.update(groups)
        (selected if len(selected) < check_count else reserve).append(r)
    if len(selected) < check_count:
        raise ValueError('Insufficient independent eligible groups')
    manifest = {'seed': seed, 'target_counts': {'dev': 5, 'check': check_count},
                'cases': [dict(r, split='dev') for r in dev] + [dict(r, split='check') for r in selected],
                'reserve_order': [r['case_id'] for r in reserve],
                'label_origin': 'MODEL_GENERATED_NOT_HUMAN_GOLD'}
    check_manifest(manifest, True)
    return manifest


def freeze(manifest_path, file_paths, dest):
    m = read(manifest_path)
    check_manifest(m, True)
    # Every mutable experimental input is copied, not just named in a manifest.
    files = [Path(manifest_path)] + [Path(x) for x in file_paths]
    names = [p.name for p in files]
    if len(names) != len(set(names)):
        raise ValueError('Freeze files need distinct basenames')
    payload = {'manifest': m, 'files': {p.name: {'sha256': digest(p.read_bytes()), 'text': p.read_text()} for p in files}}
    payload['freeze_id'] = digest(payload)
    write_new(dest, payload)
    return payload


def ablate(query, annotation, mode):
    q, a = copy.deepcopy(query), copy.deepcopy(annotation)
    if mode == 'remove_identity':
        q['constraints'] = [c for c in q.get('constraints', []) if not (c['op'] in ['same', 'different'] and '.roles.' in c['left'])]
    elif mode == 'ignore_status':
        for atom in q['atoms']:
            atom['status'] = 'ANY'
    elif mode != 'unknown_as_negative':
        raise ValueError('Unknown ablation')
    result = execute(a, q)
    if mode == 'unknown_as_negative' and result['status'] in ['UNKNOWN', 'NOT_FOUND']:
        result['status'] = 'MISMATCH'
        result['diagnostic_false_closed_world'] = True
    return result


def score(predictions, references):
    """Macro case agreement with model reference; pending/contested excluded visibly."""
    key = lambda x: (x['case_id'], x['unit_id'], x['query_id'])
    if len({key(x) for x in predictions}) != len(predictions):
        raise ValueError('Duplicate prediction')
    if len({key(x) for x in references}) != len(references):
        raise ValueError('Duplicate reference')
    pred = {key(x): x for x in predictions}
    per_case, excluded, missing, rows = {}, [], [], []
    for ref in references:
        k = key(ref)
        if ref.get('review_state') != 'RESOLVED':
            excluded.append(k)
            continue
        if k not in pred:
            missing.append(k)
            continue
        p = pred[k]
        same = p['status'] == ref['status']
        per_case.setdefault(k[0], []).append(int(same))
        rows.append({'key': k, 'status_agrees': same, 'predicted': p['status'], 'reference': ref['status']})
    macro = sum(sum(v) / len(v) for v in per_case.values()) / len(per_case) if per_case else None
    return {'case_macro_status_agreement': macro, 'cases_scored': len(per_case),
            'comparisons_scored': len(rows), 'missing_predictions': missing, 'excluded_unresolved': excluded,
            'rows': rows, 'interpretation': 'Agreement with model reference, not human-gold accuracy; binding/evidence require separate assessment.'}
