"""Bounded binding-table interpreter. Absence is never classical negation."""
import copy
from datetime import date
from decimal import Decimal, InvalidOperation
from .extract import field_value
from .contracts import PREDICATES, STATUSES


def validate_query(node):
    if not isinstance(node, dict) or 'op' not in node:
        raise ValueError('Condition object required')
    op = node['op']
    if op in ('all', 'any'):
        if set(node) != {'op', 'children'} or not isinstance(node['children'], list) or not node['children']:
            raise ValueError('Nonempty condition children required')
        for child in node['children']:
            validate_query(child)
    elif op == 'atom':
        if set(node) != {'op', 'id', 'predicate', 'roles', 'polarity'}:
            raise ValueError('Unexpected atom fields')
        if node['predicate'] not in PREDICATES or node['polarity'] not in ['POSITIVE', 'NEGATIVE']:
            raise ValueError('Unsupported atom predicate/polarity')
        if not isinstance(node['roles'], dict) or any(k not in PREDICATES[node['predicate']] for k in node['roles']):
            raise ValueError('Invalid atom role')
        if any(not isinstance(v, str) or not v.startswith('$') or len(v) < 2 for v in node['roles'].values()):
            raise ValueError('Typed object bindings must be variables')
    elif op == 'relation':
        if set(node) != {'op', 'id', 'relation', 'left', 'right'} or node['relation'] not in ['member_of', 'part_of']:
            raise ValueError('Unsupported relation')
        if any(not isinstance(node[k], str) or not node[k].startswith('$') for k in ['left', 'right']):
            raise ValueError('Relation variables required')
    else:
        raise ValueError('Unsupported operator: ' + str(op))


def execute(view, query, statuses=('NARRATED', 'COURT_FOUND'), budget=10000):
    """Positive existential queries over declared source evidence, not verdicts.

    Rows carry shared variables plus unknown dependencies. A known mismatch
    rejects just that candidate; another complete row can still satisfy the query.
    """
    try:
        validate_query(query)
        if budget < 1 or not statuses or any(s not in STATUSES for s in statuses):
            raise ValueError('Invalid execution budget/status policy')
    except (ValueError, TypeError) as exc:
        return {'run_status': 'UNSUPPORTED', 'answer_status': None, 'reason': str(exc), 'witnesses': []}
    decisions, rejected = [], []
    counter = [0]
    incomplete = [False]

    def spent():
        if counter[0] >= budget:
            incomplete[0] = True
            return True
        counter[0] += 1
        return False

    def atom(node, rows):
        output = []
        pool = []
        for record in view['records']:
            typ, why = field_value(record, 'predicate')
            excluded = typ is not None and typ != node['predicate']
            decisions.append({'condition': node['id'], 'record_id': record['id'], 'field': 'predicate',
                              'decision': 'EXCLUDE' if excluded else 'KEEP_UNKNOWN' if why else 'KEEP',
                              'required': node['predicate'], 'known': typ, 'reasons': why})
            if not excluded:
                pool.append(record)
        for row in rows:
            for record in pool:
                if spent():
                    return output
                current = copy.deepcopy(row)
                failures = []
                for field, allowed in [('predicate', [node['predicate']]), ('status', statuses),
                                       ('polarity', [node['polarity']]), ('context', ['MAIN_CASE'])]:
                    value, why = field_value(record, field)
                    if why:
                        current['unknown'].append({'condition': node['id'], 'record_id': record['id'], 'field': field, 'reasons': why})
                    elif value not in allowed:
                        failures.append({'field': field, 'value': value, 'required': list(allowed)})
                for role, variable in node['roles'].items():
                    value, why = field_value(record, 'roles.' + role)
                    if why or value is None:
                        current['unknown'].append({'condition': node['id'], 'record_id': record['id'],
                                                   'field': 'roles.' + role, 'reasons': why or ['MISSING_VALUE']})
                    elif variable in current['binding'] and current['binding'][variable] != value:
                        failures.append({'field': 'roles.' + role, 'variable': variable,
                                         'previous': current['binding'][variable], 'value': value})
                    else:
                        current['binding'][variable] = value
                witness = {'condition': node['id'], 'record_id': record['id'], 'evidence': record['evidence']}
                current['evidence'].append(witness)
                if failures:
                    rejected.append({'condition': node['id'], 'record_id': record['id'],
                                     'binding': current['binding'], 'reasons': failures})
                else:
                    output.append(current)
        return output

    def relation(node, rows):
        output = []
        for row in rows:
            if spent():
                break
            current = copy.deepcopy(row)
            left, right = (current['binding'].get(node[k]) for k in ['left', 'right'])
            if left is not None and left == right:
                rejected.append({'condition': node['id'], 'reason': 'IDENTITY_NOT_IRREFLEXIVE_RELATION', 'binding': current['binding']})
                continue
            edges = [e for e in view['relations'] if e['op'] == node['relation'] and
                     left is not None and right is not None and e['left'] == left and e['right'] == right and
                     e['context'] == 'MAIN_CASE' and e['status'] in statuses]
            supported = [e for e in edges if e['decision'] == 'SUPPORTED']
            denied = [e for e in edges if e['decision'] == 'DENIED']
            if supported and not denied:
                current['evidence'].extend({'condition': node['id'], 'relation_id': e['id'], 'evidence': e['evidence']} for e in supported)
            elif denied and not supported:
                rejected.append({'condition': node['id'], 'binding': current['binding'], 'reason': 'EXPLICIT_RELATION_DENIAL', 'evidence': denied})
                continue
            else:
                current['unknown'].append({'condition': node['id'], 'field': node['relation'],
                                           'reason': 'CONFLICTED' if supported and denied else 'NO_SUPPORTED_RELATION',
                                           'binding': current['binding'], 'evidence': edges})
            output.append(current)
        return output

    def visit(node, rows):
        if node['op'] == 'atom':
            return atom(node, rows)
        if node['op'] == 'relation':
            return relation(node, rows)
        if node['op'] == 'all':
            for child in node['children']:
                rows = visit(child, rows)
                if not rows:
                    break
            return rows
        result = []
        for index, child in enumerate(node['children']):
            branch = copy.deepcopy(rows)
            for row in branch:
                row['branches'].append(index)
            result.extend(visit(child, branch))
        return result

    rows = visit(query, [{'binding': {}, 'evidence': [], 'unknown': [], 'branches': []}])
    good, unknown = [r for r in rows if not r['unknown']], [r for r in rows if r['unknown']]
    if good:
        status, run_status = 'MATCH', 'OK'
    elif incomplete[0]:
        status, run_status = None, 'UNSUPPORTED'
    elif unknown or view.get('coverage_limited'):
        status, run_status = 'UNKNOWN', 'OK'
    else:
        status, run_status = 'NOT_FOUND', 'OK'
    return {'answer_status': status, 'run_status': run_status, 'witnesses': good, 'uncertain_bindings': unknown,
            'rejected_bindings': rejected, 'candidate_decisions': decisions, 'expanded_bindings': counter[0],
            'search_complete': not incomplete[0], 'coverage_limited': view.get('coverage_limited', False),
            'closed_world': False, 'reason': 'BINDING_BUDGET_EXHAUSTED' if incomplete[0] else
            'EXTRACTION_COVERAGE_INCOMPLETE' if view.get('coverage_limited') else None}
