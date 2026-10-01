"""Positive existential queries under incomplete observations, with explicit witnesses."""
import itertools
from datetime import datetime
from .core import canonical, digest


OPS = {'same', 'different', 'before', 'equals'}


def query_error(q):
    if not isinstance(q, dict) or set(q) - {'atoms', 'constraints'}:
        return 'Unsupported query fields'
    atoms = q.get('atoms')
    if not isinstance(atoms, list) or not 1 <= len(atoms) <= 4:
        return 'Expected 1..4 atoms'
    names = [a.get('var') for a in atoms]
    if None in names or len(names) != len(set(names)):
        return 'Atom variables must be unique'
    for a in atoms:
        if not isinstance(a.get('type'), str) or not a['type']:
            return 'Missing atom type'
        if set(a) - {'var', 'type', 'status', 'polarity', 'event_id'}:
            return 'Unsupported atom condition'
    for c in q.get('constraints', []):
        if c.get('op') not in OPS:
            return 'Unsupported operator: ' + str(c.get('op'))
        allowed = {'op', 'left', 'value'} if c['op'] == 'equals' else {'op', 'left', 'right'}
        if set(c) != allowed:
            return 'Missing or unsupported constraint fields'
        for side in ['left'] + ([] if c['op'] == 'equals' else ['right']):
            ref = c.get(side, '').split('.')
            if len(ref) < 2 or ref[0] not in names:
                return 'Invalid field reference'
            if ref[1] not in {'roles', 'attributes', 'time', 'id', 'status', 'polarity'}:
                return 'Unsupported field'
            if len(ref) != (3 if ref[1] in {'roles', 'attributes'} else 2):
                return 'Invalid field depth'
    return None


def value(binding, ref):
    bits = ref.split('.')
    e = binding[bits[0]]
    # Unscoped unresolved modifiers conservatively block every use of this event.
    if e.get('unresolved'):
        return None
    v = e
    for b in bits[1:]:
        if not isinstance(v, dict):
            return None
        v = v.get(b)
    return v


def execute(annotation, q, unit_id=None):
    error = query_error(q)
    if error:
        return {'status': 'UNSUPPORTED', 'reason': error, 'witnesses': [], 'conflicts': []}
    if unit_id is None:
        ids = sorted({u['id'] for u in annotation['units']})
        if len(ids) != 1:
            return {'status': 'UNSUPPORTED', 'reason': 'Select one analysis unit', 'witnesses': [], 'conflicts': []}
        unit_id = ids[0]
    events = [e for e in annotation['events'] if e['unit_id'] == unit_id]
    pools = [[e for e in events if e['type'] == a['type'] and
              ('event_id' not in a or e['id'] == a['event_id'])] for a in q['atoms']]
    witnesses, uncertain, rejected, conflicts = [], [], 0, []
    for combo in itertools.product(*pools):
        binding = dict(zip([a['var'] for a in q['atoms']], combo))
        unknown, failed = False, False
        for a, e in zip(q['atoms'], combo):
            if e.get('unresolved'):
                unknown = True
            for k, default in [('status', 'COURT_FOUND'), ('polarity', 'POSITIVE')]:
                required = a.get(k, default)
                if required == 'ANY':
                    continue
                if e.get(k) in (None, 'UNDETERMINED'):
                    unknown = True
                elif e[k] != required:
                    failed = True
            if e.get('status') == 'DISPUTED' or e.get('conflicts_with') or e.get('polarity') == 'NEGATIVE':
                conflicts.append({'event_id': e['id'], 'evidence': e['evidence']})
        for c in q.get('constraints', []):
            left = value(binding, c['left'])
            right = c.get('value') if c['op'] == 'equals' else value(binding, c['right'])
            if left is None or right is None:
                unknown = True
                continue
            if c['op'] in ('same', 'equals'):
                passed = left == right
            elif c['op'] == 'different':
                # Explicit IDs denote separately resolved objects, not merely different mentions.
                passed = left != right
            else:
                try:
                    passed = datetime.strptime(left, '%Y-%m-%d') < datetime.strptime(right, '%Y-%m-%d')
                except (ValueError, TypeError):
                    unknown = True
                    continue
            if not passed:
                failed = True
        w = {'binding': {a: e['id'] for a, e in binding.items()},
             'evidence': [v for e in combo for v in e.get('evidence', [])]}
        if failed:
            rejected += 1
        elif unknown:
            uncertain.append(w)
        else:
            witnesses.append(w)
    specified = all('event_id' in a for a in q['atoms'])
    if witnesses:
        status = 'MATCH'
    elif uncertain:
        status = 'UNKNOWN'
    elif specified and all(pools):
        status = 'MISMATCH'
    else:
        status = 'NOT_FOUND'
    unique_conflicts = {canonical(c): c for c in conflicts}
    return {'status': status, 'unit_id': unit_id, 'witnesses': witnesses,
            'uncertain_bindings': uncertain, 'rejected_bindings': rejected,
            'conflicts': list(unique_conflicts.values()), 'closed_world': False}


def canonical_query(q):
    # For two-event mining, normalize permutation AND variable renaming.
    variants = []
    for order in itertools.permutations(q['atoms']):
        rename = {a['var']: 'e%d' % i for i, a in enumerate(order)}
        atoms = [dict(a, var=rename[a['var']]) for a in order]
        cons = []
        for c in q.get('constraints', []):
            c = dict(c)
            for side in ['left', 'right']:
                if side in c:
                    v, rest = c[side].split('.', 1)
                    c[side] = rename[v] + '.' + rest
            if c['op'] in ['same', 'different'] and c['left'] > c['right']:
                c['left'], c['right'] = c['right'], c['left']
            cons.append(c)
        variants.append(canonical({'atoms': atoms, 'constraints': sorted(cons, key=canonical)}))
    return min(variants)


def generate(annotations):
    candidates = {}
    for ann in annotations:
        for u in ann['units']:
            if not u.get('primary', False):
                continue
            es = sorted([e for e in ann['events'] if e['unit_id'] == u['id'] and
                         e['status'] == 'COURT_FOUND' and e['polarity'] == 'POSITIVE' and not e['unresolved']], key=lambda e: e['id'])
            for a, b in itertools.combinations(es, 2):
                atoms = [{'var': 'a', 'type': a['type']}, {'var': 'b', 'type': b['type']}]
                distinct = {'op': 'different', 'left': 'a.id', 'right': 'b.id'}
                for ra, va in sorted(a['roles'].items()):
                    for rb, vb in sorted(b['roles'].items()):
                        if va is None or va != vb:
                            continue
                        base = [distinct, {'op': 'same', 'left': 'a.roles.' + ra, 'right': 'b.roles.' + rb}]
                        variants = [base]
                        if a['time'] and b['time'] and a['time'] != b['time']:
                            left, right = ('a.time', 'b.time') if a['time'] < b['time'] else ('b.time', 'a.time')
                            variants.append(base + [{'op': 'before', 'left': left, 'right': right}])
                        for var, event in [('a', a), ('b', b)]:
                            for key, v in sorted(event.get('attributes', {}).items()):
                                if isinstance(v, (str, int, float, bool)):
                                    variants.append(base + [{'op': 'equals', 'left': var + '.attributes.' + key, 'value': v}])
                        for constraints in variants:
                            q = {'atoms': atoms, 'constraints': constraints}
                            candidates[canonical_query(q)] = None
    return sorted(candidates, key=lambda s: (len(__import__('json').loads(s)['constraints']), s))


def mine(annotations, budget=1000, min_support=2):
    import json
    if budget < 1:
        raise ValueError('budget must be positive')
    annotations = sorted(annotations, key=lambda a: a['case_id'])
    if len({a['case_id'] for a in annotations}) != len(annotations):
        raise ValueError('Duplicate case annotations would inflate support')
    candidates = generate(annotations)
    result = []
    for key in candidates[:budget]:
        q = json.loads(key)
        matches, unknown, not_found, witnesses = [], [], [], []
        for ann in annotations:
            for u in ann['units']:
                if not u.get('primary', False):
                    continue
                r = execute(ann, q, u['id'])
                uid = [ann['case_id'], u['id']]
                if r['status'] == 'MATCH':
                    matches.append(uid)
                    witnesses.append({'unit': uid, 'matches': r['witnesses']})
                elif r['status'] == 'UNKNOWN':
                    unknown.append(uid)
                else:
                    not_found.append(uid)
        result.append({'id': digest(q)[:16], 'query': q, 'origin': 'DATA_SEARCH',
                       'support': len(matches), 'matches': matches, 'unknown': unknown,
                       'not_found': not_found, 'witnesses': witnesses, 'repeated': len(matches) >= min_support})
    result.sort(key=lambda x: (-x['support'], len(x['query']['constraints']), canonical(x['query'])))
    return {'patterns': result, 'generated': len(candidates), 'executed': len(result),
            'search_complete': len(candidates) <= budget, 'frontier': candidates[budget:],
            'budget': budget, 'min_support': min_support, 'scope': 'two distinct events; shared object; at most one extra condition'}


def cooccurrence_query(q):
    return {'atoms': q['atoms'], 'constraints': [c for c in q['constraints'] if c['op'] == 'different' and c['left'].endswith('.id')]}
