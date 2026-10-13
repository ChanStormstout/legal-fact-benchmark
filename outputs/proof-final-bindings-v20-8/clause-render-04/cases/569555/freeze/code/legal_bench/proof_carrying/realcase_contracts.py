"""Real judgment reconstruction v2. Data contracts, not legal adjudication."""
from legal_bench.rules_verdict_v1.contracts import obj, array, enum, nullable, validate
from .contracts import STATES, content_hash, byte_hash, write_once, read_json

TEXT = {'type': 'string'}
ROLES = ('subject', 'opponent', 'property', 'transaction')
STATUSES = ('PARTY_CLAIM', 'TESTIMONY', 'RECORDED_DOCUMENT', 'LOWER_COURT_FINDING',
            'TARGET_COURT_FINDING', 'PROCEDURAL_RECORD', 'LEGAL_RULE', 'TARGET_DISPOSITION', 'UNKNOWN')
BINDING = array(obj({'role': enum(ROLES), 'entity': TEXT}), 8)
REFS = array(TEXT, 30)

def schemas(kind):
    slot = obj({'name': TEXT, 'predicate': TEXT, 'description': TEXT, 'expected': enum(STATES),
        'allowed_statuses': array(enum(STATUSES), 10), 'required_roles': array(enum(ROLES), 4),
        'time_required': enum([True, False])})
    rule = obj({'id': TEXT, 'version': enum([1]), 'description': TEXT, 'conclusion_predicate': TEXT,
        'conclusion_text': TEXT, 'jurisdiction': TEXT, 'stage': TEXT,
        'origin': enum(['TARGET_ADOPTED_RULE', 'TARGET_REPORT_OF_PRECEDENT', 'RESEARCH_TRANSLATION']),
        'source_refs': REFS, 'source_quote': TEXT, 'operator': enum(['ALL', 'ANY', 'OPEN_TEXT']),
        'slots': array(slot, 20), 'exception_slots': array(TEXT, 10),
        'scope_limits': array(TEXT, 15), 'burden_policy': TEXT, 'unimplemented': array(TEXT, 15)})
    premise = obj({'id': TEXT, 'predicate': TEXT, 'text': TEXT, 'bindings': BINDING,
        'time_scope': nullable(TEXT), 'statement_status': enum(STATUSES), 'speaker': TEXT,
        'court_level': TEXT, 'stage': TEXT, 'state': enum(STATES), 'refs': REFS,
        'quote': TEXT, 'limitations': array(TEXT, 12)})
    if kind == 'rules':
        return obj({'rules': array(rule, 10), 'coverage_limits': array(TEXT, 15)})
    if kind == 'rule_review':
        return obj({'reviews': array(obj({'rule_id': TEXT, 'decision': enum(['ACCEPT_AS_RESEARCH_TRANSLATION', 'ISSUE', 'UNCERTAIN']),
            'refs': REFS, 'quote': TEXT, 'reason': TEXT, 'exceptions_or_scope_missing': array(TEXT, 12)}), 20),
            'approval': enum(['MODEL_SOURCE_REVIEW_NOT_LEGAL_APPROVAL']), 'coverage_limits': array(TEXT, 15)})
    if kind == 'facts':
        return obj({'entities': array(obj({'id': TEXT, 'kind': TEXT, 'label': TEXT, 'refs': REFS}), 30),
            'premises': array(premise, 30),
            'relations': array(obj({'from': TEXT, 'to': TEXT, 'sign': enum(['SUPPORT', 'OPPOSE', 'UNRESOLVED']),
                'refs': REFS, 'reason': TEXT}), 40), 'coverage_limits': array(TEXT, 15)})
    if kind == 'reference':
        return obj({'judgments': array(obj({'proposition': TEXT, 'predicate': TEXT, 'state': enum(STATES),
            'objects': array(TEXT, 8), 'statement_status': enum(STATUSES), 'stage': TEXT,
            'refs': REFS, 'quote': TEXT, 'opposition_refs': REFS, 'gap': TEXT}), 30),
            'decisive_counterarguments': array(TEXT, 15), 'conclusion_boundary': TEXT,
            'approval': enum(['MODEL_REFERENCE_NOT_HUMAN_GOLD'])})
    if kind == 'derivation':
        step = obj({'id': TEXT, 'rule_ref': TEXT, 'bindings': BINDING, 'time_scope': nullable(TEXT),
            'inputs': array(obj({'slot': TEXT, 'kind': enum(['PREMISE', 'STEP']), 'id': TEXT}), 30),
            'proposed_state': enum(STATES), 'explanation': TEXT})
        return obj({'steps': array(step, 30), 'requests': array(obj({'id': TEXT, 'step_id': TEXT,
            'predicate': TEXT, 'text': TEXT, 'proposed_state': enum(STATES)}), 10),
            'counterarguments': array(TEXT, 15), 'gaps': array(TEXT, 15)})
    raise ValueError(kind)

def unique(rows, key='id'):
    ids = [r[key] for r in rows]
    if not all(ids) or len(ids) != len(set(ids)):
        raise ValueError('EMPTY_OR_DUPLICATE_ID')
    return {r[key]: r for r in rows}

def binding_map(rows):
    return unique(rows, 'role') and {r['role']: r['entity'] for r in rows}

