"""Same-source card application comparison; no legal inference or semantic repair."""
import copy
import hashlib
import json
import re

from .contracts import validate

INTERMEDIATE = 'TARGET INTERMEDIATE MATERIAL (UNVERIFIED)\n'
CASE = '\nTARGET COMPLETE ALLOWED CASE SOURCE\n'
AUTHORITY_HEADER = 'ADDITIONAL SHARED ORIGINAL AUTHORITIES (other-case sources, not target facts)\n'


def digest(value):
    data = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def source_map(segments):
    result = {}
    for segment in segments:
        key = segment['id']
        if key in result:
            raise ValueError('Duplicate source ID: ' + key)
        if not isinstance(segment['text'], str) or not segment['text']:
            raise ValueError('Missing source text: ' + key)
        result[key] = segment
    return result


def material_parts(prompt):
    if prompt.count(INTERMEDIATE) != 1:
        raise ValueError('Ambiguous intermediate marker')
    before, body = prompt.split(INTERMEDIATE, 1)
    material, end = json.JSONDecoder().raw_decode(body)
    tail = body[end:]
    if not tail.startswith(CASE):
        raise ValueError('Unexpected material/source boundary')
    return before, material, tail


def build_pair(base_prompt, base_schema, case_source, law_package, authorities, collection):
    before, material, tail = material_parts(base_prompt)
    if material != {}:
        raise ValueError('Baseline must have empty intermediate material')
    cases = source_map(case_source['segments'])
    laws = source_map(law_package['law_segments'] + [s for a in authorities for s in a['segments']])
    base_laws = [s['id'] for s in law_package['law_segments']]
    ground = base_schema['properties']['grounds']['items']['properties']
    if ground['case_refs']['items']['enum'] != list(cases):
        raise ValueError('Case schema differs from actual allowed source')
    if ground['law_refs']['items']['enum'] != base_laws:
        raise ValueError('Law schema differs from original package')
    if set(cases) & set(case_source.get('excluded_segment_ids', [])):
        raise ValueError('Excluded target case segment included')
    # Addresses resolve; this does not certify the card propositions.
    authority_ids = [a['case_id'] for a in authorities]
    if [b['case_id'] for b in collection['bundles']] != authority_ids:
        raise ValueError('Card authority order differs from original source order')
    seen = set()
    for bundle in collection['bundles']:
        local = source_map(next(a for a in authorities if a['case_id'] == bundle['case_id'])['segments'])
        for card in bundle['rule_cards']:
            if card['id'] in seen:
                raise ValueError('Duplicate card ID')
            seen.add(card['id'])
            refs = list(card['evidence']) + [r for c in card['conditions'] for r in c['evidence']]
            if any(r not in local for r in refs):
                raise ValueError('Card cites another or unknown authority')
    common_block = AUTHORITY_HEADER + json.dumps(authorities, ensure_ascii=False) + '\n'
    common_before = before + common_block
    schema = copy.deepcopy(base_schema)
    schema['properties']['grounds']['items']['properties']['law_refs']['items']['enum'] = list(laws)
    prompts = {
        'A_COMMON': common_before + INTERMEDIATE + '{}' + tail,
        'B_PLUS_V16': common_before + INTERMEDIATE + json.dumps({'proposal': collection}, ensure_ascii=False, separators=(',', ':')) + tail,
    }
    a = material_parts(prompts['A_COMMON'])
    b = material_parts(prompts['B_PLUS_V16'])
    if a[0] != b[0] or a[2] != b[2] or b[1] != {'proposal': collection}:
        raise ValueError('Unexpected difference outside card material')
    if prompts['A_COMMON'].replace(common_block, '', 1) != base_prompt:
        raise ValueError('Original prompt cannot be recovered')
    return {'prompts': prompts, 'schema': schema, 'case_source_map': cases,
            'law_source_map': laws, 'authority_block': common_block,
            'checks': {'common_prefix_sha256': digest(a[0].encode()),
                       'common_suffix_sha256': digest(a[2].encode()),
                       'schema_sha256': digest(schema), 'original_prompt_recovered': True,
                       'same_original_case_law_examples_task': True,
                       'same_added_original_authorities': True,
                       'B_proposal_values_unchanged': True,
                       'common_old_cards': len(law_package['cards']),
                       'new_cards_B': len(seen), 'new_cards_A': 0,
                       'semantic_correctness_certified': False}}


def parse_final(raw, schema):
    """Remove only a complete unambiguous JSON fence and independent END."""
    text = raw.strip()
    changes = []
    if text.startswith('```'):
        match = re.fullmatch(r'```(?:json)?\r?\n([\s\S]*?)\r?\n```(?:\s*END)?', text)
        if not match:
            raise ValueError('Ambiguous or incomplete Markdown wrapper')
        text = match.group(1)
        changes.append('COMPLETE_JSON_CODE_FENCE')
        if raw.strip().endswith('END'):
            changes.append('INDEPENDENT_END_AFTER_FENCE')
    leading = len(text) - len(text.lstrip())
    text = text.lstrip()
    answer, end = json.JSONDecoder().raw_decode(text)
    suffix = text[end:]
    if suffix.strip() not in ('', 'END'):
        raise ValueError('Unexpected text outside complete JSON')
    if suffix.strip():
        changes.append('INDEPENDENT_END_SUFFIX')
    validate(answer, schema)
    return answer, text[:end], {'format_status': 'OK', 'removed_wrappers_only': changes,
                               'leading_whitespace_characters': leading,
                               'json_values_unchanged': True,
                               'semantic_correctness_certified': False,
                               'grounds_empty': not answer['grounds']}


def restore_evidence(answer, case_segments, law_segments):
    cases, laws = source_map(case_segments), source_map(law_segments)
    restored = []
    for i, ground in enumerate(answer['grounds'], 1):
        restored.append({'ground': i, 'point': ground['point'],
                         'case_sources': [cases[r] for r in ground['case_refs']],
                         'law_sources': [laws[r] for r in ground['law_refs']],
                         'semantic_correctness_certified': False})
    return restored
