"""Independent V19_6 transport recomputation and exact count checks.

Shares format vocabulary, never production expand/convert/decision functions.
"""
import copy
from . import local_checker_v19_refs as historical
from . import local_pipeline_v19_compact as historical_format


def _typed(raw, version):
    if version != 'V19_6': return copy.deepcopy(raw)
    result = {'analyses': [], 'object_links': copy.deepcopy(raw['object_links']), 'coverage_limits': copy.deepcopy(raw['coverage_limits'])}
    for pid in raw['analyses']:
        unit = copy.deepcopy(raw['analyses'][pid]); unit['premise'] = pid
        for name in ('uses', 'judgments'):
            for row in unit[name]:
                fields = row.pop('role_objects')
                row['bindings'] = []
                for role in fields:
                    if fields[role] != 'UNMAPPED': row['bindings'].append({'address': pid + '::' + role, 'object': fields[role]})
        for use in unit['uses']:
            for w in use['witnesses']:
                w['refs'] = [w['source']]; del w['source']
        result['analyses'].append(unit)
    return result


def check_import(raw, converted, case, version):
    canonical = _typed(raw, version); errors = []
    if len(canonical['analyses']) != len(converted.get('analyses', [])): errors.append('ANALYSIS_COUNT_MISMATCH')
    if len(canonical.get('object_links', [])) != len(converted.get('object_links', [])): errors.append('OBJECT_LINK_COUNT_MISMATCH')
    if canonical.get('coverage_limits') != converted.get('coverage_limits'): errors.append('COVERAGE_LIMITS_CHANGED')
    for i, (a, b) in enumerate(zip(canonical['analyses'], converted.get('analyses', []))):
        for key in ('premise', 'analysis_status', 'limits'):
            if a[key] != b.get(key): errors.append('UNIT_VALUE_CHANGED:' + str(i) + ':' + key)
        for kind in ('records', 'objects', 'uses', 'judgments'):
            if len(a[kind]) != len(b.get(kind, [])): errors.append('UNIT_COUNT_MISMATCH:' + str(i) + ':' + kind)
        for ar, br in zip(a['records'], b.get('records', [])):
            for key in ('status', 'stage', 'court_level'):
                if ar.get(key) != br.get(key): errors.append('RECORD_ATTRIBUTION_CHANGED:' + key)
        for ao, bo in zip(a['objects'], b.get('objects', [])):
            for key in ('label', 'type', 'identity_basis'):
                if ao.get(key) != bo.get(key): errors.append('OBJECT_SEMANTICS_CHANGED:' + key)
        for aj, bj in zip(a['judgments'], b.get('judgments', [])):
            for key in ('state', 'complete', 'stage', 'basis', 'gaps'):
                if aj[key] != bj.get(key): errors.append('JUDGMENT_SEMANTICS_CHANGED:' + key)
            if len(aj['components']) != len(bj.get('components', [])): errors.append('COMPONENT_COUNT_MISMATCH')
            if len(aj['necessary_limits']) != len(bj.get('necessary_limits', [])): errors.append('LIMIT_COUNT_MISMATCH')
            if len(aj['bindings']) != len(bj.get('bindings', [])): errors.append('JUDGMENT_BINDING_COUNT_MISMATCH')
            if [x['address'] for x in aj['bindings']] != [x['address'] for x in bj.get('bindings', [])]: errors.append('JUDGMENT_ROLE_ADDRESS_CHANGED')
            for ac, bc in zip(aj['components'], bj.get('components', [])):
                if ac['description'] != bc.get('description') or len(ac['alternatives']) != len(bc.get('alternatives', [])):
                    errors.append('COMPONENT_CONTENT_OR_ALTERNATIVE_COUNT')
        for au, bu in zip(a['uses'], b.get('uses', [])):
            for key in ('direction', 'claim', 'stage', 'self_assessment', 'limits'):
                if au[key] != bu.get(key): errors.append('USE_SEMANTICS_CHANGED:' + key)
            if len(au['bindings']) != len(bu.get('bindings', [])): errors.append('USE_BINDING_COUNT_MISMATCH')
            if [x['address'] for x in au['bindings']] != [x['address'] for x in bu.get('bindings', [])]: errors.append('USE_ROLE_ADDRESS_CHANGED')
            expected_witnesses = sum(len(w['refs']) for w in au['witnesses']) if version in ('V19_2', 'V19_4', 'V19_5', 'V19_6') else len(au['witnesses'])
            if expected_witnesses != len(bu.get('witnesses', [])): errors.append('WITNESS_COUNT_MISMATCH')
    # Count checks precede zip-based historical verification; malformed conversions
    # return rejection rather than a crash or a false OK.
    if errors: return {'status': 'REJECTED', 'errors': errors, 'semantic_approval': False, 'legal_approval': False}
    typed_version = 'V19_5' if version == 'V19_6' else version
    result = historical_format.independent_import(canonical, converted, case, typed_version)
    result['count_checks'] = 'ALL_ANALYSES_AND_DECLARED_NESTED_COUNTS_CHECKED'
    return result


def check(case, rules, p, decisions, analysis):
    errors = []
    for rows, checked, name in ((p['uses'], analysis.get('checks', []), 'USES'),
                                (p['premises'], analysis.get('premise_judgments', []), 'JUDGMENTS'),
                                (p.get('analysis_units', []), analysis.get('analysis_units', []), 'ANALYSIS_UNITS')):
        if len(rows) != len(checked): errors.append(name + '_CHECK_COUNT_MISMATCH')
    if errors: return {'status': 'REJECTED', 'errors': errors, 'semantic_approval': False, 'legal_approval': False}
    return historical.check(case, rules, p, decisions, analysis)
