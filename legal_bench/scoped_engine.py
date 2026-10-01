"""Opt-in, reviewed field projections for scoped existential queries (Python 3.9).

An assertion's original scope always travels with its witness. A reviewed
projection permits selected fields to answer an existential question within that
scope; it never establishes current truth, universal truth, or absence.
The legacy executor remains unchanged.
"""
import argparse
import copy
import itertools
from datetime import datetime
from pathlib import Path
from .core import digest, read, write_new, canonical, log_run
from .engine import query_error


def projection_view(annotation, review):
    if review['annotation_hash'] != digest(annotation):
        raise ValueError('Review is for a different annotation version')
    if review.get('mode') != 'SCOPED_EXISTENTIAL' or not review.get('provenance'):
        raise ValueError('Explicit scope mode and review provenance required')
    amap = {a['id']: a for a in annotation['assertions']}
    events, seen = [], set()
    for decision in review['decisions']:
        aid = decision['assertion_id']
        if aid in seen or aid not in amap: raise ValueError('Duplicate or unknown reviewed assertion')
        seen.add(aid)
        a = amap[aid]
        if decision['assertion_hash'] != digest(a): raise ValueError('Stale assertion review')
        if decision['decision'] not in ['ACCEPT', 'EXCLUDE', 'UNCERTAIN']:
            raise ValueError('Unsupported review decision')
        if decision['decision'] == 'EXCLUDE': continue
        if not decision.get('basis') or not decision.get('evidence'):
            raise ValueError('Review requires source evidence and a basis')
        # This view is deliberately limited to factual/procedural adopted assertions.
        # Allegation and legal-reasoning queries require a separate semantics.
        accepted = decision['decision'] == 'ACCEPT'
        if a['kind'] not in ['FACT', 'PROCEDURAL_ACT'] or (accepted and a['deciding_court_treatment']['value'] != 'ADOPTED'):
            raise ValueError('Cannot promote non-adopted assertion into an adopted fact')
        fields = decision['approved_fields']
        if not isinstance(fields, list) or (accepted and not {'type', 'polarity', 'status', 'id'} <= set(fields)):
            raise ValueError('Core proposition fields must be reviewed')
        event = {'id': aid, 'type': a['predicate'], 'roles': copy.deepcopy(a['roles']),
                 'attributes': copy.deepcopy(a['attributes']), 'time': a['time']['date'] if a['time'] else None,
                 'polarity': a['polarity'], 'status': 'COURT_FOUND' if accepted else 'UNDETERMINED', 'scope': copy.deepcopy(a['scope']),
                 'origin': copy.deepcopy(a['origin']), 'evidence': copy.deepcopy(a['evidence']),
                 'treatment_evidence': copy.deepcopy(a['deciding_court_treatment']['evidence']),
                 'unresolved': copy.deepcopy(a['unresolved']), 'approved_fields': fields,
                 'review_basis': decision['basis'], 'review_evidence': copy.deepcopy(decision['evidence'])}
        event['source_treatment'] = copy.deepcopy(a['deciding_court_treatment'])
        event['review_decision'] = decision['decision']
        if not accepted:
            event['unresolved'].append({'field': 'predicate', 'reason': 'Review unresolved: ' + decision['basis']})
        available = {'type', 'status', 'polarity', 'id', 'time'} | {
            root + '.' + key for root in ['roles', 'attributes'] for key in event[root]}
        if set(fields) - available: raise ValueError('Unsupported or missing approved field')
        events.append(event)
    selected = {e['id'] for e in events}
    conflicts = [copy.deepcopy(r) for r in annotation['relations'] if r['type'] == 'DIRECT_CONTRADICTION'
                 and (r['from_id'] in selected or r['to_id'] in selected)]
    return {'case_id': annotation['case_id'], 'unit_id': review['unit_id'], 'events': events,
            'conflicts': conflicts, 'input_hash': digest(annotation), 'review_hash': digest(review),
            'mode': review['mode'], 'material_scope': review.get('material_scope', 'REVIEWED_SUBSET'),
            'reviewed_assertion_ids': sorted(selected), 'closed_world': False}


def field_value(event, field):
    if field not in event['approved_fields']:
        return None, 'FIELD_NOT_REVIEWED: ' + field
    for u in event['unresolved']:
        affected = u['field']
        # Unknown/unrecognized domains remain conservative. Known leaf domains
        # affect only that field, not a separate identity or amount query.
        recognized = affected in {'time', 'origin', 'scope'} or affected.startswith(('roles.', 'attributes.', 'scope.', 'origin.'))
        if not recognized or affected in {'predicate', 'polarity', 'status', 'roles', 'attributes'}:
            return None, 'UNRESOLVED_PROPOSITION: ' + u['reason']
        if field == affected or field.startswith(affected + '.'):
            return None, 'UNRESOLVED_FIELD: ' + u['reason']
        # A scope qualifier has no computational meaning without review. Approval
        # of each projected field certifies only its explicitly scoped use.
    value = event
    for part in field.split('.'):
        value = value.get(part) if isinstance(value, dict) else None
    return (value, None) if value is not None else (None, 'MISSING_FIELD: ' + field)


def execute(view, query):
    if not isinstance(query, dict):
        return {'status': 'UNSUPPORTED', 'reason': 'Query must be an object', 'witnesses': []}
    if query.get('mode') != 'SCOPED_EXISTENTIAL':
        return {'status': 'UNSUPPORTED', 'reason': 'Only explicitly scoped existential uses supported', 'witnesses': []}
    q = {k: v for k, v in query.items() if k != 'mode'}
    try:
        error = query_error(q)
    except (TypeError, AttributeError, KeyError):
        error = 'Malformed query'
    if error: return {'status': 'UNSUPPORTED', 'reason': error, 'witnesses': []}
    if any(c['op'] == 'before' and (not c['left'].endswith('.time') or not c['right'].endswith('.time'))
           for c in q.get('constraints', [])):
        return {'status': 'UNSUPPORTED', 'reason': 'Temporal ordering requires event time fields', 'witnesses': []}
    for atom in q['atoms']:
        if atom.get('status', 'COURT_FOUND') != 'COURT_FOUND':
            return {'status': 'UNSUPPORTED', 'reason': 'This view supports adopted facts only', 'witnesses': []}
    pools = [[e for e in view['events'] if e['type'] == atom['type'] and
              ('event_id' not in atom or e['id'] == atom['event_id'])] for atom in q['atoms']]
    witnesses, uncertain, rejected = [], [], []
    for combo in itertools.product(*pools):
        binding = dict(zip([a['var'] for a in q['atoms']], combo))
        unknown, failed = [], []
        for atom, event in zip(q['atoms'], combo):
            for field, target in [('type', atom['type']), ('status', 'COURT_FOUND'), ('polarity', atom.get('polarity', 'POSITIVE'))]:
                value, reason = field_value(event, field)
                if reason: unknown.append({'assertion_id': event['id'], 'field': field, 'reason': reason})
                elif target != 'ANY' and value != target: failed.append({'assertion_id': event['id'], 'field': field})
        def resolve(ref):
            var, field = ref.split('.', 1)
            value, reason = field_value(binding[var], field)
            if reason: unknown.append({'assertion_id': binding[var]['id'], 'field': field, 'reason': reason})
            return value
        for c in q.get('constraints', []):
            left = resolve(c['left'])
            right = c['value'] if c['op'] == 'equals' else resolve(c['right'])
            if left is None or right is None: continue
            equal = left == right and isinstance(left, bool) == isinstance(right, bool)
            if c['op'] in ['same', 'equals']: passed = equal
            elif c['op'] == 'different': passed = not equal
            else:
                try:
                    # Reject lenient date parsing of non-ISO dates.
                    dates = [datetime.strptime(x, '%Y-%m-%d') for x in [left, right]]
                    if any(d.strftime('%Y-%m-%d') != x for d, x in zip(dates, [left, right])): raise ValueError()
                    passed = dates[0] < dates[1]
                except (TypeError, ValueError):
                    unknown.append({'constraint': c, 'reason': 'EXACT_ISO_DATE_REQUIRED'}); continue
            if not passed: failed.append({'constraint': c, 'left_value': left, 'right_value': right})
        witness = {'binding': {v: e['id'] for v, e in binding.items()},
                   'scopes': {v: e['scope'] for v, e in binding.items()},
                   'origins': {v: e['origin'] for v, e in binding.items()},
                   'evidence': [x for e in combo for x in e['evidence']],
                   'review_evidence': [x for e in combo for x in e['review_evidence']]}
        if failed: rejected.append(dict(witness, failed_conditions=failed, uncertainty=unknown))
        elif unknown: uncertain.append(dict(witness, uncertainty=unknown))
        else: witnesses.append(witness)
    specified = all('event_id' in a for a in q['atoms'])
    status = 'MATCH' if witnesses else 'UNKNOWN' if uncertain else 'MISMATCH' if specified and all(pools) else 'NOT_FOUND'
    return {'status': status, 'case_id': view['case_id'], 'unit_id': view['unit_id'], 'witnesses': witnesses,
            'uncertain_bindings': uncertain, 'rejected_bindings': rejected,
            'conflicts': view['conflicts'], 'material_scope': view['material_scope'], 'closed_world': False,
            'input_hash': view['input_hash'], 'review_hash': view['review_hash']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['annotation', 'review', 'queries', 'out']: p.add_argument('--' + name, required=True)
    args = p.parse_args()
    view = projection_view(read(args.annotation), read(args.review))
    results = [{'id': q['id'], 'meaning': q['meaning'], 'result': execute(view, q['query'])}
               for q in read(args.queries)]
    write_new(args.out, {'view': view, 'results': results})
    log_run(Path(args.out).parent, 'scoped-query',
            [args.annotation, args.review, args.queries, __file__], [args.out])
    print(canonical({'out': args.out, 'statuses': {r['id']: r['result']['status'] for r in results}}))


if __name__ == '__main__': main()
