"""One joint contract repair: visible anchors, fixed work keys and role maps.

No reference labels, semantic repair or case-ID branches. Reuses V19_5 semantics.
"""
import copy
from collections import Counter
from . import local_pipeline_v19_compact as old
from .local_pipeline_v17 import obj, arr, enum, STR
from .schema_contract_v19_6 import validate, violations, loads

VERSION = 'V19_6'
role_directory = old.role_directory
directory = old.directory
merge_parts = old.merge_parts
apply_connection_decisions = old.apply_connection_decisions
learner_inputs = old.learner_inputs
FINAL_SCHEMA = old.FINAL_SCHEMA
FINAL_INSTRUCTION = old.FINAL_INSTRUCTION


def source_directory(case):
    rows = old.source_directory(case)
    if len({x['address'] for x in rows}) != len(rows):
        raise ValueError('DUPLICATE_ALLOWED_SOURCE_ADDRESS')
    return rows


def source_text(case):
    """Preserve every source byte; its actual selectable alias is adjacent."""
    return '\n\n'.join(x['choice'] + ' | ' + x['address'] + '\n' + x['text'] for x in source_directory(case))


def schema(rules, case):
    choices = [x['choice'] for x in source_directory(case)]
    source = {'$ref': '#/$defs/source_choice'}
    def refs(minimum=0):
        return {**arr(source, minimum, len(choices)), 'uniqueItems': True}
    def local(prefix):
        return {'type': 'string', 'pattern': '^' + prefix + r':[1-9][0-9]*$'}
    def addresses(prefix, minimum=0):
        return {**arr(local(prefix), minimum), 'uniqueItems': True}
    statuses = sorted(set(old.STATUS) | {s for r in rules for p in r['premises'] for s in p.get('allowed_statuses', [])})
    record = obj({'proposition': STR, 'status': enum(statuses), 'stage': STR, 'court_level': STR, 'refs': refs(1)})
    entity = obj({'label': STR, 'type': STR, 'refs': refs(1), 'identity_basis': STR})
    witness = obj({'source': source, 'necessity': enum(('REQUIRED', 'SUPPLEMENTARY'))})
    component = obj({'description': STR, 'alternatives': arr(addresses('USE', 1), 1)})
    limit = obj({'kind': enum(('NOTE', 'STAGE_SCOPE', 'BLOCK_SCOPE', 'UNMAPPED')),
                 'component': {'type': 'string', 'pattern': r'^(WHOLE_JUDGMENT|COMP:[1-9][0-9]*)$'},
                 'reason': STR, 'refs': refs()})
    units = {}
    for rule in rules:
        for premise in rule['premises']:
            pid = premise['id']
            if pid in units: raise ValueError('DUPLICATE_WORK_ADDRESS')
            bindings = obj({role: {'type': 'string', 'pattern': r'^(OBJ:[1-9][0-9]*|UNMAPPED)$'}
                            for role in premise.get('variables', {})})
            use = obj({'records': addresses('EV', 1), 'role_objects': bindings,
                       'direction': enum(('SUPPORT', 'OPPOSE', 'CONTEXT')), 'claim': STR, 'stage': STR,
                       'witnesses': arr(witness, 1, max(1, len(choices))),
                       'self_assessment': enum(old.LABELS), 'limits': arr()})
            judgment = obj({'role_objects': bindings, 'uses': addresses('USE'),
                            'state': enum(old.STATES), 'complete': {'type': 'boolean'}, 'stage': STR,
                            'basis': STR, 'components': arr(component), 'opposition_uses': addresses('USE'),
                            'gaps': arr(), 'necessary_limits': arr(limit)})
            units[pid] = obj({'analysis_status': enum(('ANALYZED', 'NOT_ANALYZED')),
                             'records': arr(record), 'objects': arr(entity), 'uses': arr(use),
                             'judgments': arr(judgment), 'limits': arr()})
    link = obj({'left_premise': enum(units), 'left_object': local('OBJ'),
                'right_premise': enum(units), 'right_object': local('OBJ'), 'refs': refs(1), 'identity_basis': STR})
    result = obj({'analyses': obj(units), 'object_links': arr(link), 'coverage_limits': arr()})
    result['$defs'] = {'source_choice': enum(choices)}
    return result


INSTRUCTION = '''Reconstruct fixed Q1 in English from only the supplied unchanged source and rules. This is historical reasoning reconstruction, not prediction. Return compact JSON in the response body. The decoder receives the schema separately.
Code fixes analyses keys from the work directory. Return each key exactly once, including an explicit NOT_ANALYZED entry when you cannot analyze it; this is different from an analyzed UNKNOWN. Within each analysis, array positions assign EV:n, OBJ:n and USE:n starting at 1. Do not generate separate IDs, hashes, rules, versions or offsets. Reference only declared local items; dynamic existence is checked on import, not guaranteed by the decoder. Missing items must never be guessed from names or type equality.
Each source paragraph has its actual SRC:n address beside its original address. Copy that SRC address, not the original line number. records and objects cite only relevant unique refs; a witness selects ONE source address in its source field. Multiple discontinuous locations are separate witnesses, not a fabricated continuous quote. Code restores exact original fragments. A proposition is your attributed interpretation, not a copy of a source paragraph. Do not duplicate attributed records or enumerate every source line.
Every use and judgment has role_objects with the exact role keys supplied for that premise. Select a declared OBJ:n for each relevant role; write UNMAPPED when unknown or not involved in a partial use. Code forms full premise::role addresses. Unknown roles do not match other unknown roles. Different arrangements do not merge merely because names/types coincide. More than one judgment for a premise can express distinct arrangements. Explicit object_links require actual source identity grounds.
A use retains records, role_objects, direction SUPPORT/OPPOSE/CONTEXT, claim, stage, witnesses, self_assessment and limits. SUPPORTED concerns that particular evidentiary use, including legitimate opposition; it is not premise truth. Keep speaker, status, court and stage. Party claims establish that a claim was made, not its truth. Lower court findings are not automatically appellate adoption. Sources describing documents are not independently inspected originals. Final disposition cannot prove itself.
A whole-premise judgment separately retains role_objects, uses, state TRUE/FALSE/UNKNOWN/CONFLICTED, complete, stage, basis, components, opposition_uses, gaps and necessary_limits. Complete coverage requires all required roles and all necessary components. Components are ALL; alternative USE bundles within one component are OR; each bundle needs ALL its uses. These dependencies are fallible model proposals, not new legal rules. Background/partial support or lack of opposition does not establish a whole premise. Do not count votes; explain counterevidence and negation. Partial/unknown role coverage remains local, not whole-case failure.
necessary_limits: NOTE is an explanation; STAGE_SCOPE qualifies the recorded court/stage without changing truth; BLOCK_SCOPE names an actual missing prerequisite of this judgment/component; UNMAPPED retains unclear scope. component is WHOLE_JUDGMENT or COMP:n. Do not turn ordinary cautions into blockers. Preserve opposing uses, independent alternatives, limitations, and OPEN_TEXT; do not rewrite rule meaning or exceptions. No legal approval is conferred.
'''


def synthetic_example():
    return {'analyses': {'SYN.P1': {'analysis_status': 'ANALYZED',
        'records': [{'proposition': 'The trial found Rowan entered Garden Z on Monday.', 'status': 'COURT_FINDING',
                     'stage': 'trial', 'court_level': 'Trial Court', 'refs': ['SRC:2']},
                    {'proposition': 'Rowan denied Monday entry.', 'status': 'PARTY_CLAIM', 'stage': 'pleading',
                     'court_level': 'UNMAPPED', 'refs': ['SRC:1']},
                    {'proposition': 'The witness reported Tuesday departure.', 'status': 'TESTIMONY',
                     'stage': 'trial', 'court_level': 'Trial Court', 'refs': ['SRC:3']}],
        'objects': [{'label': 'Rowan', 'type': 'person', 'refs': ['SRC:1', 'SRC:2'], 'identity_basis': 'Both statements explicitly identify Rowan in this dispute.'}],
        'uses': [{'records': ['EV:1'], 'role_objects': {'actor': 'OBJ:1'}, 'direction': 'SUPPORT',
                  'claim': 'Report the trial finding, not independent proof of entry.', 'stage': 'trial',
                  'witnesses': [{'source': 'SRC:2', 'necessity': 'REQUIRED'}], 'self_assessment': 'SUPPORTED', 'limits': []},
                 {'records': ['EV:2'], 'role_objects': {'actor': 'OBJ:1'}, 'direction': 'CONTEXT',
                  'claim': 'Denial of the event does not deny the court made its finding.', 'stage': 'pleading',
                  'witnesses': [{'source': 'SRC:1', 'necessity': 'REQUIRED'}], 'self_assessment': 'SUPPORTED', 'limits': []},
                 {'records': ['EV:3'], 'role_objects': {'actor': 'OBJ:1'}, 'direction': 'CONTEXT',
                  'claim': 'Tuesday departure does not establish Monday entry.', 'stage': 'trial',
                  'witnesses': [{'source': 'SRC:3', 'necessity': 'REQUIRED'}], 'self_assessment': 'SUPPORTED', 'limits': []}],
        'judgments': [{'role_objects': {'actor': 'OBJ:1'}, 'uses': ['USE:1', 'USE:2', 'USE:3'], 'state': 'TRUE',
                       'complete': True, 'stage': 'trial', 'basis': 'The trial finding is explicitly recorded; the denial concerns the event, and the other testimony concerns another date.',
                       'components': [{'description': 'The attributed trial finding.', 'alternatives': [['USE:1']]}],
                       'opposition_uses': [], 'gaps': [], 'necessary_limits': [{'kind': 'STAGE_SCOPE', 'component': 'WHOLE_JUDGMENT', 'reason': 'Only reports a trial finding.', 'refs': ['SRC:2']}]}], 'limits': []},
        'SYN.P2': {'analysis_status': 'NOT_ANALYZED', 'records': [], 'objects': [], 'uses': [], 'judgments': [], 'limits': ['No appellate adoption record.']}},
        'object_links': [], 'coverage_limits': ['No independent Monday-entry or liability conclusion.']}


def proposal_prompt(case, rules, part):
    selected = [r for r in rules if r['id'] in part['rule_ids']]
    view = {**case, 'segments': [s for s in case['segments'] if s['id'] in part['source_ids']]}
    work = [{'premise': p['id'], 'proposition': p['text'], 'role_objects_keys_and_types': p.get('variables', {}),
             'analysis_status_choices': ['ANALYZED', 'NOT_ANALYZED']}
            for r in selected for p in r['premises']]
    example = ('\nFICTIONAL EXAMPLE ONLY:\nSRC:1 | SYN:L1\nRowan denied Monday entry.\n'
               'SRC:2 | SYN:L2\nThe trial court found Rowan entered Garden Z on Monday.\n'
               'SRC:3 | SYN:L3\nA witness saw Rowan leave on Tuesday.\n'
               'SYN.P1: report the trial finding; actor:person. SYN.P2: appellate adoption; actor:person.\n'
               + old.compact_json(synthetic_example()))
    return (INSTRUCTION + example + '\nFIXED REQUEST:\n' + old.compact_json(next(x for x in case['targets'] if x['id'] == 'Q1'))
            + '\nUNCHANGED RULES:\n' + old.compact_json(directory(selected))
            + '\nFIXED WORK AND ROLE KEYS:\n' + old.compact_json(work)
            + '\nALLOWED SOURCE (copy the adjacent SRC address):\n' + source_text(view))


def expand(raw):
    """Shape-only adapter. It does not fill any missing role or factual claim."""
    result = {**copy.deepcopy(raw), 'analyses': []}
    for pid, value in raw['analyses'].items():
        unit = {**copy.deepcopy(value), 'premise': pid}
        for row in unit['uses'] + unit['judgments']:
            mapping = row.pop('role_objects')
            row['bindings'] = [{'address': pid + '::' + role, 'object': ref} for role, ref in mapping.items() if ref != 'UNMAPPED']
        for use in unit['uses']:
            for witness in use['witnesses']: witness['refs'] = [witness.pop('source')]
        result['analyses'].append(unit)
    return result


def convert(raw, case, version):
    if version == VERSION:
        expanded = expand(raw)
        converted, ledger = old.convert(expanded, case, old.VERSION)
        return converted, [{'conversion': 'FIXED_KEYS_AND_ROLE_MAP_TO_CANONICAL', 'version': VERSION, 'semantics_changed': False}] + ledger
    return old.convert(raw, case, version)


def coverage(raw, rules):
    expected = [p['id'] for r in rules for p in r['premises']]
    units = ([{'premise': k, **v} for k, v in raw['analyses'].items()] if isinstance(raw.get('analyses'), dict) else raw.get('analyses', []))
    units = [u for u in units if isinstance(u, dict)]
    counts = Counter(u.get('premise', 'UNMAPPED_ANALYSIS_ADDRESS') for u in units)
    missing = [pid for pid in expected if not counts[pid]]
    duplicates = [pid for pid, count in counts.items() if count > 1]
    extra = [pid for pid in counts if pid not in expected]
    not_analyzed = [u.get('premise', 'UNMAPPED_ANALYSIS_ADDRESS') for u in units if u.get('analysis_status') == 'NOT_ANALYZED']
    empty = [u.get('premise', 'UNMAPPED_ANALYSIS_ADDRESS') for u in units if u.get('analysis_status') == 'ANALYZED' and not u.get('judgments')]
    status = 'PARTIAL_ANALYSIS' if missing or extra or duplicates or not_analyzed or empty else 'ANALYSIS_REPORTED'
    return {'status': status, 'expected': expected, 'returned': [u.get('premise', 'UNMAPPED_ANALYSIS_ADDRESS') for u in units], 'missing': missing,
            'duplicate': duplicates, 'extra': extra, 'explicit_not_analyzed': not_analyzed,
            'analyzed_without_judgment': empty, 'semantic_completeness_verified': False}
