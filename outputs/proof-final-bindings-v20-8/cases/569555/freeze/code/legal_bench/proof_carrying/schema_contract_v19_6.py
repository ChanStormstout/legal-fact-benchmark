"""Fail-closed validation for the schema subset emitted by the current pipeline.

Independent of decoder claims. Historical schema bytes are not rewritten.
"""
import json
import math
import re


class ContractError(ValueError):
    pass


def violations(value, schema):
    errors = []
    definitions = schema.get('$defs', {})
    supported = {'type', 'properties', 'required', 'additionalProperties', 'items',
                 'minItems', 'maxItems', 'uniqueItems', 'enum', 'pattern',
                 'minLength', 'maxLength', 'minimum', 'maximum', '$ref', '$defs',
                 'title', 'description', '$schema'}

    def walk(data, spec, path):
        unknown = set(spec) - supported
        if unknown:
            errors.append({'path': path, 'reason': 'UNSUPPORTED_SCHEMA_KEYWORD', 'keys': sorted(unknown)})
            return
        if '$ref' in spec:
            ref = spec['$ref']
            if not ref.startswith('#/$defs/') or ref[8:] not in definitions:
                errors.append({'path': path, 'reason': 'SCHEMA_REFERENCE_UNRESOLVED'})
                return
            walk(data, definitions[ref[8:]], path)
            return
        def bad(reason):
            errors.append({'path': path, 'reason': reason})
        if 'enum' in spec and not any(type(data) is type(x) and data == x for x in spec['enum']):
            bad('OUTSIDE_ENUM')
        typ = spec.get('type')
        if typ == 'object':
            if not isinstance(data, dict): bad('OBJECT_TYPE'); return
            props = spec.get('properties', {})
            if set(spec.get('required', [])) - set(data): bad('MISSING_REQUIRED_FIELD')
            if spec.get('additionalProperties') is False and set(data) - set(props): bad('EXTRA_FIELD')
            for k, v in data.items():
                if k in props: walk(v, props[k], path + '/' + str(k))
        elif typ == 'array':
            if not isinstance(data, list): bad('ARRAY_TYPE'); return
            if not spec.get('minItems', 0) <= len(data) <= spec.get('maxItems', math.inf): bad('ARRAY_CARDINALITY')
            if spec.get('uniqueItems'):
                encoded = [json.dumps(x, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')) for x in data]
                if len(set(encoded)) != len(encoded): bad('DUPLICATE_ARRAY_ITEM')
            for i, item in enumerate(data): walk(item, spec.get('items', {}), path + '/' + str(i))
        elif typ == 'string':
            if not isinstance(data, str): bad('STRING_TYPE'); return
            if not spec.get('minLength', 0) <= len(data) <= spec.get('maxLength', math.inf): bad('STRING_LENGTH')
            if 'pattern' in spec and re.search(spec['pattern'], data) is None: bad('PATTERN')
        elif typ == 'integer':
            if type(data) is not int: bad('INTEGER_TYPE'); return
            if not spec.get('minimum', -math.inf) <= data <= spec.get('maximum', math.inf): bad('INTEGER_RANGE')
        elif typ == 'boolean':
            if type(data) is not bool: bad('BOOLEAN_TYPE')
        elif typ == 'null':
            if data is not None: bad('NULL_TYPE')
        elif typ is not None: bad('UNSUPPORTED_SCHEMA_TYPE')
    walk(value, schema, '$')
    return errors


def validate(value, schema, path='$'):
    errors = violations(value, schema)
    if errors:
        raise ContractError(json.dumps(errors, ensure_ascii=False))


def loads(text):
    """Duplicate JSON keys must not disappear during json.loads."""
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result: raise ContractError('DUPLICATE_JSON_KEY:' + k)
            result[k] = v
        return result
    def constant(token):
        raise ContractError('NON_FINITE_JSON:' + token)
    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
