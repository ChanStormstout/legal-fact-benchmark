"""Disjoint model-selected object shapes, shared by generation and registration.

This enforces structural consistency only. No name, identity, ownership, source
meaning or ACCEPT judgment is inferred by this module.
"""
from schema_contract import validate

NON_PROPERTY_KINDS = ('PARTY', 'PERSON', 'COURT', 'ORGANIZATION', 'EVENT', 'OTHER')
SIMPLE_EXTENTS = ('SINGLE_UNIT', 'HOMOGENEOUS_SET', 'UNRESOLVED')


def object_schema(refs, text):
    def obj(fields):
        return {'type': 'object', 'properties': fields, 'required': list(fields),
                'additionalProperties': False}
    def choice(values):
        return {'type': 'string', 'enum': list(values)}
    references = {'type': 'array', 'items': choice(refs), 'minItems': 1,
                  'maxItems': 4, 'uniqueItems': True}
    component = obj({'name': text(160), 'description': text(260),
                     'extent': choice(SIMPLE_EXTENTS), 'refs': references})
    def shape(kinds, extents, maximum):
        return obj({'name': text(160), 'kind': choice(kinds),
                    'description': text(260), 'refs': references,
                    'extent': choice(extents),
                    'components': {'type': 'array', 'items': component,
                                   'minItems': 0, 'maxItems': maximum}})
    return {'anyOf': [
        shape(NON_PROPERTY_KINDS, ('NOT_PROPERTY',), 0),
        shape(('PROPERTY',), SIMPLE_EXTENTS, 0),
        shape(('PROPERTY',), ('HETEROGENEOUS_COLLECTION',), 8),
    ]}


def validate_object_shape(row):
    """Repeat the SAME structure guard at both registry entry points.

Source visibility remains the request schema's responsibility. Here the enum is
    derived from already supplied IDs, never by inventing or correcting a source.
    """
    refs = list(dict.fromkeys(row.get('refs', []) + [
        ref for component in row.get('components', []) for ref in component.get('refs', [])]))
    validate(row, object_schema(refs, lambda _: {'type': 'string', 'minLength': 1}))
