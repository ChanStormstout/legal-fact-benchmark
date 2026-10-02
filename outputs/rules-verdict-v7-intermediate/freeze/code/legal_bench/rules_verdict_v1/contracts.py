"""Constrained generation contracts, independent from historical task vocabularies."""
import json

PREDICATES = {
    'LEASE': ['landlord', 'tenant', 'premises', 'contract'],
    'POSSESSION': ['holder', 'premises'],
    'PART_WITH_POSSESSION': ['transferor', 'recipient', 'premises'],
    'SUBLET': ['tenant', 'subtenant', 'premises'],
    'ASSIGN': ['assignor', 'assignee', 'premises', 'contract'],
    'CONSENT': ['landlord', 'tenant', 'recipient', 'premises'],
    'PAY_RENT': ['payer', 'recipient', 'premises', 'contract'],
    'FILE_PROCEEDING': ['filer', 'respondent', 'premises'],
    'OTHER': ['subject', 'object'], 'UNKNOWN': ['subject', 'object'],
}
STATUSES = ['NARRATED', 'COURT_FOUND', 'PARTY_CLAIMED', 'COURT_REJECTED', 'UNKNOWN']
KINDS = ['PERSON', 'ORGANIZATION', 'GROUP', 'PROPERTY', 'CONTRACT', 'NOTICE', 'OTHER', 'UNKNOWN']
FIELDS = ['predicate', 'status', 'polarity', 'context', 'stage', 'time', 'attributes', '*'] + [
    'roles.' + r for r in sorted({r for rs in PREDICATES.values() for r in rs})]


def obj(props):
    return {'type': 'object', 'properties': props, 'required': list(props), 'additionalProperties': False}


def array(item, limit):
    return {'type': 'array', 'items': item, 'maxItems': limit}


def string(limit=240):
    return {'type': 'string', 'maxLength': limit}


def enum(values):
    return {'enum': list(values)}


def nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def extraction_schema(source):
    evidence = array(enum(s['id'] for s in source['segments']), 12)
    unknown = obj({'affects': array(enum(FIELDS), 16), 'reason': string(), 'evidence': evidence})
    record = obj({
        'id': string(48), 'predicate': enum(PREDICATES), 'text': string(320),
        'roles': array(obj({'name': enum(sorted({r for rs in PREDICATES.values() for r in rs})),
                            'object': nullable(string(48))}), 8),
        'status': enum(STATUSES), 'polarity': enum(['POSITIVE', 'NEGATIVE', 'UNKNOWN']),
        'speaker': string(100), 'stage': string(120),
        'context': enum(['MAIN_CASE', 'QUOTED_PRECEDENT', 'HYPOTHETICAL', 'UNKNOWN']),
        'time': nullable(string(100)),
        'attributes': array(obj({'name': string(40), 'value': string(120)}), 8),
        'known': array(enum([f for f in FIELDS if f != '*']), 24),
        'unknown': array(unknown, 8), 'evidence': evidence,
    })
    relation = obj({'id': string(48), 'op': enum(['part_of', 'member_of']),
                    'left': string(48), 'right': string(48),
                    'decision': enum(['SUPPORTED', 'DENIED', 'UNRESOLVED']),
                    'status': enum(STATUSES), 'stage': string(120),
                    'context': enum(['MAIN_CASE', 'QUOTED_PRECEDENT', 'HYPOTHETICAL', 'UNKNOWN']),
                    'reason': string(), 'evidence': evidence})
    return obj({'case_id': enum([source['case_id']]),
                'objects': array(obj({'id': string(48), 'label': string(160), 'kind': enum(KINDS),
                                      'evidence': evidence}), 64),
                'records': array(record, 32), 'relations': array(relation, 32),
                'coverage': enum(['COMPLETE_FOR_TASK', 'INCOMPLETE']),
                'limitations': array(string(), 12)})


def decision_schema(source):
    return obj({'case_id': enum([source['case_id']]),
                'outcome': enum(['ALLOW_APPEAL', 'DISMISS_APPEAL', 'PARTIAL_OR_REMAND', 'UNDETERMINED']),
                'assessment_status': enum(['SUPPORTED', 'UNRESOLVED', 'DISPUTED', 'UNSUPPORTED']),
                'reason': string(700),
                'evidence': array(enum(s['id'] for s in source['segments']), 16),
                'missing': array(string(), 12), 'other_combinations': string(320)})


def validate(data, schema, path='$'):
    """Fail closed on schema violations, including booleans in numeric/enumerated slots."""
    if 'enum' in schema:
        if not any(type(data) is type(v) and data == v for v in schema['enum']):
            raise ValueError(path + ': outside enum')
        return
    if 'anyOf' in schema:
        for choice in schema['anyOf']:
            try:
                validate(data, choice, path)
                return
            except ValueError:
                pass
        raise ValueError(path + ': invalid union value')
    typ = schema['type']
    if typ == 'object':
        if not isinstance(data, dict) or set(data) != set(schema['required']):
            raise ValueError(path + ': missing or extra keys')
        for k, v in data.items():
            validate(v, schema['properties'][k], path + '.' + k)
    elif typ == 'array':
        if not isinstance(data, list) or len(data) > schema['maxItems']:
            raise ValueError(path + ': invalid array')
        for i, v in enumerate(data):
            validate(v, schema['items'], path + '[%d]' % i)
    elif typ == 'string':
        if not isinstance(data, str) or len(data) > schema.get('maxLength', float('inf')):
            raise ValueError(path + ': invalid string')
    elif typ == 'null':
        if data is not None:
            raise ValueError(path + ': null required')
    else:
        raise ValueError('Unsupported validator type: ' + typ)


def schema_text(schema):
    # Replace only evidence enums in prompts; decoder retains the exact IDs.
    return json.dumps(schema, ensure_ascii=False, separators=(',', ':'))
