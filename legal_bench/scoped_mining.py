"""Two-event mining over explicitly reviewed, scoped development views.

Names/role semantics must already be comparable across cases. This module never
infers aliases, adoption, field approval, legal significance, or closed-world
absence. Uncertain fields cannot seed candidates but remain in execution pools.
"""
import argparse
import json
from pathlib import Path
from .core import read, write_new, canonical, digest, log_run
from .engine import cooccurrence_query
from .conditional_engine import generate_from_seeds
from .scoped_engine import execute, field_value


def seed_annotation(view):
    events = []
    for event in view['events']:
        core = [field_value(event, f) for f in ['id', 'type', 'status', 'polarity']]
        if any(reason for _, reason in core):
            continue
        if event['status'] != 'COURT_FOUND' or event['polarity'] != 'POSITIVE':
            continue
        roles, attributes = {}, {}
        for root, dest in [('roles', roles), ('attributes', attributes)]:
            for key in sorted(event[root]):
                value, reason = field_value(event, root + '.' + key)
                if not reason:
                    dest[key] = value
        time, reason = field_value(event, 'time')
        if reason:
            time = None
        events.append({'id': event['id'], 'type': event['type'], 'roles': roles,
                       'attributes': attributes, 'time': time, 'status': 'COURT_FOUND',
                       'polarity': 'POSITIVE', 'unresolved': [], 'unit_id': view['unit_id']})
    return {'case_id': view['case_id'], 'units': [{'id': view['unit_id'], 'primary': True}],
            'events': events}


def mine(views, budget=1000, min_support=2, candidates=None, max_joins=2):
    if budget < 1 or min_support < 1:
        raise ValueError('Positive budget and support threshold required')
    views = sorted(views, key=lambda v: (v['case_id'], v['unit_id']))
    if len({v['case_id'] for v in views}) != len(views):
        raise ValueError('One reviewed primary unit per case; A/B are not independent cases')
    if candidates is None:
        candidates = generate_from_seeds([seed_annotation(v) for v in views], max_joins=max_joins)
    patterns = []
    for key in candidates[:budget]:
        query = dict(json.loads(key), mode='SCOPED_EXISTENTIAL')
        baseline = dict(cooccurrence_query(query), mode='SCOPED_EXISTENTIAL')
        results = []
        for view in views:
            results.append({'case_id': view['case_id'], 'unit_id': view['unit_id'],
                            'relation': execute(view, query), 'cooccurrence': execute(view, baseline)})
        support = sum(r['relation']['status'] == 'MATCH' for r in results)
        patterns.append({'id': digest(query)[:16], 'query': query, 'origin': 'DATA_SEARCH',
                         'support': support, 'repeated': support >= min_support,
                         'unknown': sum(r['relation']['status'] == 'UNKNOWN' for r in results),
                         'cooccurrence_support': sum(r['cooccurrence']['status'] == 'MATCH' for r in results),
                         'results': results})
        patterns[-1]['same_type_pair'] = len({a['type'] for a in query['atoms']}) == 1
        patterns[-1]['distinctness'] = 'DISTINCT_RECORD_IDS_NOT_PROVEN_DISTINCT_EVENTS'
    patterns.sort(key=lambda p: (-p['support'], len(p['query']['constraints']), canonical(p['query'])))
    return {'patterns': patterns, 'generated': len(candidates), 'executed': len(patterns),
            'budget': budget, 'min_support': min_support,
            'search_complete': len(candidates) <= budget, 'frontier': candidates[budget:],
            'max_joins': max_joins, 'candidate_hash': digest(candidates),
            'inputs': [{'case_id': v['case_id'], 'unit_id': v['unit_id'], 'view_hash': digest(v),
                        'material_scope': v['material_scope']} for v in views],
            'limitations': ['Development mining only; no held-out result',
                            'Supplied names and role meanings; no automatic cross-case equivalence',
                            'Scopes preserved with witnesses; no common-time snapshot or legal rule inferred',
                            'Support counts cases, not independent disputes unless grouping is separately verified',
                            'No legal-importance or open-space recall claim']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--views', nargs='+', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--budget', type=int, default=1000)
    p.add_argument('--min-support', type=int, default=2)
    args = p.parse_args()
    result = mine([read(path) for path in args.views], args.budget, args.min_support)
    write_new(args.out, result)
    log_run(Path(args.out).parent, 'scoped-mine budget=%d min_support=%d' % (args.budget, args.min_support),
            args.views + [__file__], [args.out])
    print({k: result[k] for k in ['generated', 'executed', 'search_complete']})


if __name__ == '__main__':
    main()
