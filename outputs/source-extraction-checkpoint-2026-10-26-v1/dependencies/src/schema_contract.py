"""Fail-closed validation for the schema subset emitted by the current pipeline.

Independent of decoder claims. Historical schema bytes are not rewritten.
"""
import copy
import json
import math
import re


class ContractError(ValueError):
    pass


def decoder_schema(schema):
    """Compile conjunctions into self-contained hosted-decoder alternatives.

    The semantic contract stays unchanged. Some hosted decoders ignore siblings
    of anyOf and fail on branch-local arrays without items. Distribute the common
    constraints into each alternative instead of weakening them. Unsupported
    intersections fail before dispatch; this function never edits a model value.
    """
    minimums = {'minItems', 'minLength', 'minimum'}
    maximums = {'maxItems', 'maxLength', 'maximum'}
    annotations = {'description', 'title', '$schema'}

    def merge(left, right):
        for closed, other in ((left, right), (right, left)):
            if closed.get('additionalProperties') is False:
                extra = set(other.get('properties', {})) - set(closed.get('properties', {}))
                if extra:
                    raise ContractError('DECODER_CLOSED_OBJECT_INTERSECTION:' + ','.join(sorted(extra)))
        out = copy.deepcopy(left)
        for key, value in right.items():
            if key not in out:
                out[key] = copy.deepcopy(value)
            elif key == 'properties':
                for name, prop in value.items():
                    out[key][name] = merge(out[key][name], prop) if name in out[key] else copy.deepcopy(prop)
            elif key == 'items':
                out[key] = merge(out[key], value)
            elif key == 'required':
                out[key] = list(dict.fromkeys(out[key] + value))
            elif key == 'enum':
                out[key] = [x for x in out[key] if any(type(x) is type(y) and x == y for y in value)]
                if not out[key]:
                    raise ContractError('DECODER_EMPTY_ENUM_INTERSECTION')
            elif key in minimums:
                out[key] = max(out[key], value)
            elif key in maximums:
                out[key] = min(out[key], value)
            elif key == 'uniqueItems':
                out[key] = out[key] or value
            elif key == 'additionalProperties' and isinstance(out[key], bool) and isinstance(value, bool):
                out[key] = out[key] and value
            elif key in annotations:
                pass
            elif out[key] != value:
                raise ContractError('DECODER_UNSUPPORTED_INTERSECTION:' + key)
        for low, high in [('minItems', 'maxItems'), ('minLength', 'maxLength'), ('minimum', 'maximum')]:
            if low in out and high in out and out[low] > out[high]:
                raise ContractError('DECODER_EMPTY_BOUND_INTERSECTION:' + low)
        return out

    def visit(node):
        if not isinstance(node, dict):
            raise ContractError('DECODER_SCHEMA_OBJECT_REQUIRED')
        if any(key in node for key in ('$ref', '$defs', 'allOf', 'oneOf', 'not')):
            raise ContractError('DECODER_UNSUPPORTED_SCHEMA_CONSTRUCT')
        if 'anyOf' in node:
            choices = node['anyOf']
            if not isinstance(choices, list) or not choices:
                raise ContractError('DECODER_EMPTY_ALTERNATIVES')
            common = {key: value for key, value in node.items() if key != 'anyOf'}
            return {'anyOf': [visit(merge(common, branch)) for branch in choices]}
        out = copy.deepcopy(node)
        if 'properties' in node:
            out['properties'] = {name: visit(prop) for name, prop in node['properties'].items()}
        if 'items' in node:
            out['items'] = visit(node['items'])
        if node.get('type') == 'array' and 'items' not in node:
            raise ContractError('DECODER_ARRAY_ITEMS_REQUIRED')
        return out

    return visit(schema)


def violations(value, schema):
    errors = []
    definitions = schema.get('$defs', {})
    supported = {'type', 'properties', 'required', 'additionalProperties', 'items',
                 'minItems', 'maxItems', 'uniqueItems', 'enum', 'pattern',
                 'minLength', 'maxLength', 'minimum', 'maximum', '$ref', '$defs',
                 'title', 'description', '$schema', 'anyOf'}

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
        if 'anyOf' in spec:
            choices = spec['anyOf']
            if not isinstance(choices, list) or not choices:
                bad('INVALID_ANYOF_SCHEMA'); return
            failures = []
            for branch in choices:
                start = len(errors)
                walk(data, branch, path)
                branch_errors = errors[start:]
                del errors[start:]
                if not branch_errors:
                    break
                failures.append(branch_errors)
            else:
                errors.append({'path': path, 'reason': 'NO_ANYOF_BRANCH', 'branches': failures})
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
