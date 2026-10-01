"""Evidence-based alignment candidates, never automatic semantic merges."""
import argparse
from .core import canonical, digest, read, write_new


def alignment(a, b):
    if a['case_id'] != b['case_id']:
        raise ValueError('Different cases')
    ad = {d['id']: d for d in a['predicate_definitions']}
    bd = {d['id']: d for d in b['predicate_definitions']}
    candidates = []
    covered_a, covered_b = set(), set()
    for x in a['assertions']:
        sx = {e['segment_id'] for e in x['evidence']}
        for y in b['assertions']:
            common = sx & {e['segment_id'] for e in y['evidence']}
            if not common:
                continue
            covered_a.add(x['id']); covered_b.add(y['id'])
            changes = [k for k in ['kind', 'predicate', 'polarity', 'attributes', 'scope', 'time',
                                   'origin', 'deciding_court_treatment'] if x[k] != y[k]]
            # Object IDs and role names have only local meaning. Even identical IDs
            # are not sufficient evidence of equivalent propositions across passes.
            candidates.append({'a': x['id'], 'b': y['id'], 'common_segments': sorted(common),
                               'same_predicate_name': x['predicate'] == y['predicate'],
                               'changed_fields': changes,
                               'definitions': {'A': ad[x['predicate']], 'B': bd[y['predicate']]},
                               'role_bindings': {'A': x['roles'], 'B': y['roles']},
                               'state': 'SEMANTIC_REVIEW_PENDING'})
    candidates.sort(key=lambda c: (not c['same_predicate_name'], len(c['changed_fields']), c['a'], c['b']))
    return {'version': 'evidence-alignment-v1', 'case_id': a['case_id'],
            'input_hashes': {'A': digest(a), 'B': digest(b)}, 'candidates': candidates,
            'without_overlapping_evidence': {
                'A': [x['id'] for x in a['assertions'] if x['id'] not in covered_a],
                'B': [x['id'] for x in b['assertions'] if x['id'] not in covered_b]},
            'note': 'Overlap locates review candidates; absence of overlap is not proof of omission. No annotations merged.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['a', 'b', 'out']: p.add_argument('--' + name, required=True)
    args = p.parse_args()
    result = alignment(read(args.a), read(args.b))
    write_new(args.out, result)
    print(canonical({'candidates': len(result['candidates']), 'out': args.out}))


if __name__ == '__main__': main()
