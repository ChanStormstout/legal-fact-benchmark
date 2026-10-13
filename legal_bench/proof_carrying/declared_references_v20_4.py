"""Local address integrity; no reference repair or change to source transport."""
import copy
import re

VERSION = 'V20_4_DECLARED_REFERENCES'
PATTERNS = {
    '^EV:[1-9][0-9]*$': ('EV', 'records'),
    '^OBJ:[1-9][0-9]*$': ('OBJ', 'objects'),
    '^(OBJ:[1-9][0-9]*|UNMAPPED)$': ('OBJ', 'objects'),
    '^USE:[1-9][0-9]*$': ('USE', 'uses'),
}
UNIT_ORDER = ('analysis_status', 'records', 'objects', 'uses', 'judgments', 'limits')
LINK_ORDER = ('left_premise', 'left_object', 'right_premise', 'right_object')


def field_order(path, spec):
    """Only dependency-bearing objects require wire order. Values are unchanged."""
    keys = list(spec.get('properties', {}))
    if path == () and 'analyses' in keys:
        head = ['source_sets', 'analyses']
    elif len(path) == 2 and path[0] == 'analyses':
        head = list(UNIT_ORDER)
    elif len(path) == 2 and path[0] == 'object_links':
        head = list(LINK_ORDER)
    else:
        return None
    return [k for k in head if k in keys] + [k for k in keys if k not in head]


def wire_order(value, schema, path=(), root=None):
    """Reorder object keys only, so saved legal payloads declare before referencing."""
    root = schema if root is None else root
    if '$ref' in schema:
        schema = root['$defs'][schema['$ref'].split('/')[-1]]
    if isinstance(value, dict):
        order = field_order(path, schema) or list(value)
        keys = [k for k in order if k in value] + [k for k in value if k not in order]
        return {k: wire_order(value[k], schema.get('properties', {}).get(k, {}), path+(k,), root) for k in keys}
    if isinstance(value, list):
        return [wire_order(v, schema.get('items', {}), path+(i,), root) for i, v in enumerate(value)]
    return copy.deepcopy(value)


def audit(value, schema):
    """Independent completed-payload audit: scope from JSON, counts from actual arrays."""
    units = value.get('analyses', {})
    counts = {pid: {k: len(unit.get(k, [])) for k in ('records', 'objects', 'uses')}
              for pid, unit in units.items()}
    violations = []; checked = {'EV': 0, 'OBJ': 0, 'USE': 0, 'UNMAPPED': 0}

    def walk(node, spec, path):
        if '$ref' in spec:
            spec = schema['$defs'][spec['$ref'].split('/')[-1]]
        pattern = spec.get('pattern')
        if isinstance(node, str) and pattern in PATTERNS:
            prefix, collection = PATTERNS[pattern]
            if node == 'UNMAPPED' and 'UNMAPPED' in pattern:
                checked['UNMAPPED'] += 1; return
            if len(path) > 2 and path[0] == 'analyses':
                pid = path[1]
            elif len(path) == 3 and path[0] == 'object_links':
                link = value['object_links'][path[1]]
                pid = link.get('left_premise' if path[-1] == 'left_object' else 'right_premise')
            else:
                pid = None
            count = counts.get(pid, {}).get(collection, 0)
            checked[prefix] += 1
            match = re.fullmatch(prefix+r':([1-9][0-9]*)', node)
            if not match or int(match[1]) > count:
                violations.append({'path': list(path), 'value': node, 'premise': pid,
                                   'declared_collection': collection, 'declared_count': count})
        elif isinstance(node, dict):
            for k, v in node.items(): walk(v, spec.get('properties', {}).get(k, {}), path+(k,))
        elif isinstance(node, list):
            for i, v in enumerate(node): walk(v, spec.get('items', {}), path+(i,))
    walk(value, schema, ())
    return {'status': 'PASS' if not violations else 'REJECTED_INVALID_LOCAL_REFERENCE',
            'checked': checked, 'declared_counts': counts, 'violations': violations,
            'information_rewritten': False, 'semantic_approval': False}


INSTRUCTION = '''DECLARED LOCAL REFERENCES (V20.4): Generate source_sets first, then analyses, then the remaining root fields. Within EACH analysis generate analysis_status, records, objects, uses, judgments, limits in that order. Array positions declare EV:1..N for completed records, OBJ:1..N for completed objects, and USE:1..N for completed uses. These addresses are local to that analysis; never enumerate undeclared numbers or borrow another analysis's addresses. Use UNMAPPED when no role object is established. With no records, uses must be []; with no uses, judgment uses/opposition_uses/components must be []. For object_links generate left_premise before left_object, and right_premise before right_object; each object must exist in its selected premise's object array. If no object endpoint exists, object_links is []. Include all supported information; do not invent declarations to populate an address range. The decoder enforces declared addresses and preserves the original source transport and meaning.\n'''
