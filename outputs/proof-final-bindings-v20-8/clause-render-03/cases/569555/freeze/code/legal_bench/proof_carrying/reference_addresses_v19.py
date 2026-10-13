"""Typed transport references; no semantic repair, identity inference or label input."""
import copy
import re
from .source_contract_v19 import catalog, convert as legacy_convert

VERSION = 'V19_REFERENCE_1'
PRODUCTION_VERSION = 'V19_4'
PREFIXES = {'records': 'EV', 'objects': 'OBJ', 'uses': 'USE'}


def contract():
    return {
        'version': VERSION, 'production_version': PRODUCTION_VERSION,
        'source': 'SRC:n selects the n-th entry of the frozen allowed-source directory',
        'record': 'EV:n selects the n-th record within the current analysis',
        'object': 'OBJ:n selects the n-th object within the current analysis',
        'use': 'USE:n selects the n-th use within the current analysis',
        'component': 'COMP:n selects the n-th component; WHOLE_JUDGMENT is explicit whole scope',
        'ordinal_policy': 'One-based array positions assigned by code; no model-declared duplicate IDs',
        'generation_guarantees': ['Exact finite source enum', 'Local reference namespace and positive ordinal syntax'],
        'import_only_checks': ['Dynamic declared-array existence', 'Unique cross-analysis premise scope', 'Dependency membership and object/source semantics'],
        'legacy_policy': 'Only valid original one-based indices retain their meaning; zero/out-of-range/wrong-namespace references are never guessed or shifted',
        'source_presence_not_semantic_support': True,
        'local_failure_preserves_records_and_independent_uses': True,
    }


def source_directory(case):
    return [{**row, 'choice': 'SRC:' + str(i)} for i, row in enumerate(catalog(case), 1)]


def audit(raw, case, production_version):
    """Check raw namespaces/counts before conversion. Numerical overlap is only a clue."""
    rows = []
    typed = production_version == PRODUCTION_VERSION
    sources = source_directory(case)
    source_ids = {row['address'] for row in sources}
    source_choices = {row['choice'] for row in sources}

    def reference(value, prefix, size, path):
        if typed:
            match = re.fullmatch(re.escape(prefix) + r':([1-9][0-9]*)', value) if isinstance(value, str) else None
            index = int(match[1]) if match else None
            status = ('VALID' if index <= size else 'NONEXISTENT_LOCAL_REFERENCE') if match else 'WRONG_NAMESPACE_OR_ORDINAL_SYNTAX'
        else:
            index = value if type(value) is int else None
            status = 'VALID' if index is not None and 1 <= index <= size else 'ZERO_REFERENCE' if index == 0 else 'NEGATIVE_REFERENCE' if index is not None and index < 0 else 'NONEXISTENT_LOCAL_REFERENCE' if index is not None else 'WRONG_REFERENCE_TYPE'
        row = {'path': path, 'original': value, 'namespace': prefix, 'declared_count': size, 'status': status}
        if status != 'VALID' and type(value) is int and 1 <= value <= len(sources):
            row['also_valid_source_choice'] = sources[value - 1]['address']
            row['interpretation'] = 'POSSIBLE_NAMESPACE_CONFUSION_NOT_AUTO_REPAIR'
        rows.append(row)
        return index if status == 'VALID' else 0

    def refs(v, path):
        if isinstance(v, dict):
            for key, value in v.items():
                if key == 'refs' and isinstance(value, list):
                    for i, item in enumerate(value):
                        valid = item in source_choices if typed else ((type(item) is int and 1 <= item <= len(sources)) or (isinstance(item, str) and item in source_ids))
                        rows.append({'path': path + '/refs/' + str(i), 'original': item, 'namespace': 'SRC', 'declared_count': len(sources), 'status': 'VALID' if valid else 'SOURCE_REQUIRES_LEGACY_RESOLUTION' if not typed else 'WRONG_OR_NONEXISTENT_SOURCE_REFERENCE'})
                else:
                    refs(value, path + '/' + key)
        elif isinstance(v, list):
            for i, value in enumerate(v):
                refs(value, path + '/' + str(i))

    refs(raw, '')
    for i, unit in enumerate(raw['analyses']):
        path = '/analyses/' + str(i)
        for j, use in enumerate(unit['uses']):
            for k, value in enumerate(use['records']):
                reference(value, 'EV', len(unit['records']), path + '/uses/' + str(j) + '/records/' + str(k))
            for k, binding in enumerate(use['bindings']):
                reference(binding['object'], 'OBJ', len(unit['objects']), path + '/uses/' + str(j) + '/bindings/' + str(k) + '/object')
        for j, judgment in enumerate(unit['judgments']):
            jp = path + '/judgments/' + str(j)
            for k, binding in enumerate(judgment['bindings']):
                reference(binding['object'], 'OBJ', len(unit['objects']), jp + '/bindings/' + str(k) + '/object')
            for field in ('uses', 'opposition_uses'):
                for k, value in enumerate(judgment[field]):
                    reference(value, 'USE', len(unit['uses']), jp + '/' + field + '/' + str(k))
            for k, component in enumerate(judgment['components']):
                for n, bundle in enumerate(component['alternatives']):
                    for m, value in enumerate(bundle):
                        reference(value, 'USE', len(unit['uses']), jp + '/components/' + str(k) + '/alternatives/' + str(n) + '/' + str(m))
            if typed:
                for k, limit in enumerate(judgment['necessary_limits']):
                    if limit['component'] != 'WHOLE_JUDGMENT':
                        reference(limit['component'], 'COMP', len(judgment['components']), jp + '/necessary_limits/' + str(k) + '/component')
    for i, link in enumerate(raw.get('object_links', [])):
        for side in ('left', 'right'):
            units = [u for u in raw['analyses'] if u['premise'] == link[side + '_premise']]
            size = len(units[0]['objects']) if len(units) == 1 else 0
            reference(link[side + '_object'], 'OBJ', size, '/object_links/' + str(i) + '/' + side + '_object')
    return rows


def convert(raw, case, production_version):
    """Convert transport addresses to existing canonical IDs, preserving all records."""
    typed = production_version == PRODUCTION_VERSION
    checks = audit(raw, case, production_version)
    if not typed:
        p, ledger = legacy_convert(raw, case, production_version == 'V19_2')
        return p, ledger + [{**row, 'version': VERSION, 'legacy_reference_unchanged': True} for row in checks if row['namespace'] != 'SRC']
    p = copy.deepcopy(raw)
    results = {row['path']: row for row in checks}
    ledger = []
    source_map = {s['choice']: s['address'] for s in source_directory(case)}

    def local(value, path):
        row = results[path]
        resolved = int(value.split(':')[1]) if row['status'] == 'VALID' else 0
        ledger.append({**row, 'resolved': resolved, 'version': VERSION, 'semantic_repair': False})
        return resolved

    def sources(v, path):
        if isinstance(v, dict):
            for key, value in list(v.items()):
                if key == 'refs' and isinstance(value, list):
                    mapped = []
                    for i, item in enumerate(value):
                        resolved = source_map.get(item) if isinstance(item, str) else None
                        mapped.append(resolved if resolved is not None else 'UNMAPPED_SOURCE:' + str(item))
                        ledger.append({'path': path + '/refs/' + str(i), 'original': item, 'resolved': resolved, 'status': 'EXACT_FROZEN_TYPED_SOURCE' if resolved else 'UNMAPPED_SOURCE', 'version': VERSION, 'semantic_approval': False})
                    v[key] = mapped
                else:
                    sources(value, path + '/' + key)
        elif isinstance(v, list):
            for i, value in enumerate(v):
                sources(value, path + '/' + str(i))
    sources(p, '')
    for i, unit in enumerate(p['analyses']):
        path = '/analyses/' + str(i)
        for j, use in enumerate(unit['uses']):
            use['records'] = [local(v, path + '/uses/' + str(j) + '/records/' + str(k)) for k, v in enumerate(use['records'])]
            for k, binding in enumerate(use['bindings']):
                binding['object'] = local(binding['object'], path + '/uses/' + str(j) + '/bindings/' + str(k) + '/object')
        for j, judgment in enumerate(unit['judgments']):
            jp = path + '/judgments/' + str(j)
            for k, binding in enumerate(judgment['bindings']):
                binding['object'] = local(binding['object'], jp + '/bindings/' + str(k) + '/object')
            for field in ('uses', 'opposition_uses'):
                judgment[field] = [local(v, jp + '/' + field + '/' + str(k)) for k, v in enumerate(judgment[field])]
            for k, component in enumerate(judgment['components']):
                component['alternatives'] = [[local(v, jp + '/components/' + str(k) + '/alternatives/' + str(n) + '/' + str(m)) for m, v in enumerate(bundle)] for n, bundle in enumerate(component['alternatives'])]
            for k, limit in enumerate(judgment['necessary_limits']):
                limit['component'] = 0 if limit['component'] == 'WHOLE_JUDGMENT' else local(limit['component'], jp + '/necessary_limits/' + str(k) + '/component') or -1
                # Invalid scope must remain pending, never masquerade as an ordinary note.
                if limit['component'] == -1:
                    limit['kind'] = 'UNMAPPED'
        for j, use in enumerate(unit['uses']):
            for witness in use['witnesses']:
                witness.setdefault('quote', '')
    for i, link in enumerate(p.get('object_links', [])):
        for side in ('left', 'right'):
            link[side + '_object'] = local(link[side + '_object'], '/object_links/' + str(i) + '/' + side + '_object')
    # Reuse unchanged source-anchor restoration and legacy metadata handling.
    p, old_ledger = legacy_convert(p, case, True)
    return p, ledger + old_ledger
