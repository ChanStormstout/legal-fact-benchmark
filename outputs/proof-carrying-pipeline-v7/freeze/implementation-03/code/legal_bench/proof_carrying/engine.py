"""Untrusted proposal builder. The checker does NOT import this module.

Existing aligned_logic is reused only for determinate AND/OR/NOT proposal
calculation. CONFLICTED is not silently converted into a determinate state.
"""
from legal_bench.irac_application.aligned_logic import evaluate
from .contracts import content_hash


def propose(snapshot, registry, policy, premise_ids, rule_ref='COVERAGE_DEMO@1', certificate_id='C1'):
    rule = registry['rules'][rule_ref]
    items = [snapshot['propositions'].get(p) for p in premise_ids]
    result = 'UNKNOWN'
    binding = {'person': 'Person_A', 'property': 'Parcel_P'}
    if items and items[0]:
        binding = {k: items[0]['bindings'][k] for k in binding}
    if rule['kind'] == 'PERMISSION_COVERAGE' and len(items) == 2 and all(items):
        a, b = items
        if a['assessment'] == b['assessment'] == 'TRUE':
            result = 'TRUE' if (a['bindings']['person'] == b['bindings']['person'] and
                a['bindings']['property'] == b['bindings']['property'] and
                a['interval'][0] <= b['event_time'] <= a['interval'][1] and
                b['activity'] in a['activity_scope']) else 'FALSE'
    elif rule['kind'] == 'EXPRESSION' and all(items) and len(items) == len(rule['inputs']):
        forward = {'TRUE': 'SUPPORTED', 'FALSE': 'REFUTED', 'UNKNOWN': 'UNRESOLVED'}
        def expression(node):
            row = dict(node, source_refs=['DEMO_ONLY_RULE'])
            if node['op'] == 'REF':
                row['id'] = node['role']
                del row['role']
            elif node['op'] == 'NOT':
                row['arg'] = expression(node['arg'])
            else:
                row['args'] = [expression(x) for x in node['args']]
            return row
        if any(x['assessment'] == 'CONFLICTED' for x in items):
            result = 'CONFLICTED'
        else:
            states = {r['role']: {'status': forward[p['assessment']]} for r, p in zip(rule['inputs'], items)}
            reverse = {v: k for k, v in forward.items()}
            result = reverse[evaluate(expression(rule['expression']), states)['status']]
    return {'certificate_id': certificate_id, 'snapshot_id': snapshot['snapshot_id'],
            'snapshot_sha256': content_hash(snapshot), 'registry_sha256': content_hash(registry),
            'policy_sha256': content_hash(policy), 'mode': 'TEACHING',
            'steps': [{'id': 'T1', 'rule_ref': rule_ref, 'premise_ids': premise_ids,
                       'depends_on': [], 'bindings': binding, 'proposed_result': result}],
            'requests': [{'id': 'Q1', 'step_id': 'T1', 'claim': rule['conclusion'], 'proposed_result': result}]}
