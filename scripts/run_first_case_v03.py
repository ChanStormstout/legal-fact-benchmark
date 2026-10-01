"""Reproduce the first-case development diagnostic after importing its web review.

This is not E2 held-out scoring: these ten queries were used during development
and the reference was adjudicated using the same records.
"""
import argparse
from pathlib import Path
from legal_bench.core import read, write_new, digest
from legal_bench.scoped_engine import projection_view, execute


def queries(side):
    def atom(var, typ, aid=None):
        r = {'var': var, 'type': typ}
        if aid: r['event_id'] = aid
        return r
    def query(atoms, constraints):
        return {'mode': 'SCOPED_EXISTENTIAL', 'atoms': atoms, 'constraints': constraints}
    def comp(op, left, right): return {'op': op, 'left': left, 'right': right}
    def equal(left, value): return {'op': 'equals', 'left': left, 'value': value}
    if side == 'A':
        lease = atom('l', 'LEASE_PROPERTY', 'a24'); rent = atom('p', 'PAY_RENT', 'a28')
        surrender = atom('s', 'SURRENDER_POSSESSION', 'a29'); suit = atom('f', 'FILE_POSSESSION_SUIT', 'a33')
        tenant, surrenderer = 'lessee', 'surrendering_party'
    else:
        lease = atom('l', 'EXECUTE_LEASE', 'a23'); rent = atom('p', 'PAY_RENT', 'a26')
        surrender = atom('s', 'SURRENDER_POSSESSION', 'a27'); suit = atom('f', 'FILE_POSSESSION_SUIT', 'a32')
        tenant, surrenderer = 'tenant', 'subject'
    rate = atom('r', 'RENT_AMOUNT', 'a6')
    other = atom('o', 'OCCUPY_PROPERTY', 'a14'); shop = atom('t', 'OCCUPY_PROPERTY', 'a3')
    residence = atom('h', 'OCCUPY_PROPERTY', 'a2')
    return [
        query([rate, rent], [comp('same', 'r.roles.property', 'p.roles.property')]),
        query([lease, rent], [comp('same', 'l.roles.' + tenant, 'p.roles.payer')]),
        query([other, shop], [comp('different', 'o.roles.property', 't.roles.property')]),
        query([residence, shop], [comp('same', 'h.roles.property', 't.roles.property')]),
        query([rate], [equal('r.attributes.amount', 'Rs. 25/-')]),
        query([rent], [equal('p.attributes.amount', 'Rs. 25/-')]),
        query([lease, suit], [comp('before', 'l.time', 'f.time')]),
        query([surrender, rent], [comp('before', 's.time', 'p.time')]),
        query([other, surrender], [comp('same', 'o.roles.occupant', 's.roles.' + surrenderer),
                                  comp('same', 'o.roles.property', 's.roles.property')]),
        query([atom('c', 'RECEIVE_COMPENSATION')], [])]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', default='outputs/benchmark-pilot-v03')
    p.add_argument('--reviews', default='review-import-v1')
    p.add_argument('--out', default='first-case-v1')
    args = p.parse_args(); root = Path(args.root)
    task = read(root / 'reconciliation-task.json')
    expected = {q['id']: q for q in read(root / args.reviews / 'reference.json')}
    report = {'case_id': '1064407', 'evaluation_kind': 'DEVELOPMENT_DIAGNOSTIC_NOT_HELD_OUT',
              'reference_origin': 'MODEL_GENERATED_AND_MODEL_REVIEWED_NOT_HUMAN_GOLD', 'sides': {}}
    for side in ['A', 'B']:
        ann = read('outputs/benchmark-pilot-v02/downloads/' + side + '-semantic-1/annotation.json')
        review = read(root / args.reviews / (side + '-review.json'))
        view = projection_view(ann, review)
        definitions = []
        results = []
        for i, q in enumerate(queries(side), 1):
            qid = 'Q%d' % i; meaning = task['questions'][i - 1][1]
            definitions.append({'id': qid, 'meaning': meaning, 'query': q})
            result = execute(view, q)
            results.append({'id': qid, 'meaning': meaning, 'result': result,
                            'reference_status': expected[qid]['status'],
                            'agrees_with_model_reference': result['status'] == expected[qid]['status']})
        write_new(root / args.out / (side + '-queries.json'), definitions)
        write_new(root / args.out / (side + '-results.json'), results)
        report['sides'][side] = {'annotation_hash': digest(ann), 'review_hash': digest(review),
                                  'material_scope': view['material_scope'], 'records_in_view': len(view['events']),
                                  'statuses': {r['id']: r['result']['status'] for r in results},
                                  'reference_disagreements': [r['id'] for r in results if not r['agrees_with_model_reference']]}
    report['limitations'] = ['Selected assertions, not a completed reconciled case',
                             'Manual per-side query adaptations, not learned global canonicalization',
                             'Shared-model reference bias', 'No held-out evaluation or cross-case pattern support']
    write_new(root / args.out / 'summary.json', report)
    print(report['sides'])


if __name__ == '__main__': main()
