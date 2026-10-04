"""Bounded two-route authority retrieval; no inferred law or semantic repairs."""
import copy
import json
import re
from pathlib import Path

from . import authority_index, retrieve
from .final_v9 import EXAMPLES
from .source_views import digest

VERSION = 'V21_BM25_RULE_RRF_1'
CONFIG = {'A_text_candidates': 40, 'B_text_candidates': 20,
          'B_rule_candidates': 20, 'rrf_k': 60, 'max_units': 8,
          'max_legal_characters': 20000, 'seed': 20261003}
FINAL = '''Use ONLY the allowed target record and original legal units in this task. No external search, other conversations, target judgment versions or project history. Examples are fictional teaching material, not target evidence. Historical authority facts never become target facts.
Return one complete JSON object with outcome, grounds, reason, followed by END. outcome is SUPPORT_GROUND, OPPOSE_GROUND, UNDETERMINED or UNSUPPORTED for the fixed ground only. Usually use 3-6 grounds; this is a writing target, not a hard array limit. Each ground contains point, case_refs, law_refs, assessment, explanation. point is one short factual or legal proposition, not a paragraph of reasoning or a statement about missing coverage. assessment is SUPPORTED, REFUTED, UNRESOLVED or UNSUPPORTED for the proposition itself, not the direction of eviction. Cite only source IDs supplied in this task. Empty reference arrays are allowed when the specific absence or scope gap is explained; do not fabricate IDs. explanation normally uses 1-3 sentences: relevant objects and statement/court status -> supplied rule premises and scope -> application and strongest relevant opposition -> decisive gap and its consequence. Preserve prior court findings at their actual level; do not upgrade party allegations or erase a prior finding just because the target court's reasons are withheld. Distinguish an unproved fact from its negation, statutory vesting from immunity from tenancy restrictions, and a genuine legal coverage gap from an input-scope or factual gap. Unsatisfied conditions do not make a controlling law irrelevant. Assess lawful analogies with their actual statute, adoption status, exceptions and limits. reason is 1-2 sentences explaining the legal consequence of the grounds; no new facts or rules. Concision cannot justify dropping decisive opposing evidence. Do not guess the withheld historical outcome.'''


def output_schema():
    string = {'type': 'string'}
    refs = {'type': 'array', 'items': string}
    ground = {'type': 'object', 'additionalProperties': False,
              'required': ['point', 'case_refs', 'law_refs', 'assessment', 'explanation'],
              'properties': {'point': string, 'case_refs': refs, 'law_refs': refs,
                             'assessment': {'type': 'string', 'enum': ['SUPPORTED', 'REFUTED', 'UNRESOLVED', 'UNSUPPORTED']},
                             'explanation': string}}
    return {'type': 'object', 'additionalProperties': False, 'required': ['outcome', 'grounds', 'reason'],
            'properties': {'outcome': {'type': 'string', 'enum': ['SUPPORT_GROUND', 'OPPOSE_GROUND', 'UNDETERMINED', 'UNSUPPORTED']},
                           'grounds': {'type': 'array', 'items': ground}, 'reason': string}}


def parse_answer(raw, case_ids, law_ids):
    """Validate structure, retain all content and classify address/count problems separately."""
    text = raw.strip(); changes = []
    if text.startswith('```'):
        m = re.fullmatch(r'```(?:json)?\r?\n([\s\S]*?)\r?\n```(?:\s*END)?', text)
        if not m:
            raise ValueError('FORMAT_ERROR: ambiguous/incomplete Markdown fence')
        text = m.group(1); changes.append('COMPLETE_JSON_FENCE')
    value, end = json.JSONDecoder().raw_decode(text)
    if text[end:].strip() not in ('', 'END'):
        raise ValueError('FORMAT_ERROR: unexpected text outside complete JSON')
    if text[end:].strip(): changes.append('INDEPENDENT_END')
    validate_output(value)
    warnings = []; issues = []
    if len(value['grounds']) > 6: warnings.append({'kind': 'GROUND_COUNT', 'actual': len(value['grounds']), 'suggestion': 6})
    for n, g in enumerate(value['grounds'], 1):
        for field, allowed in [('case_refs', set(case_ids)), ('law_refs', set(law_ids))]:
            if len(g[field]) > 4: warnings.append({'kind': 'REFERENCE_COUNT', 'ground': n, 'field': field, 'actual': len(g[field]), 'suggestion': 4})
            for ref in g[field]:
                if ref not in allowed: issues.append({'ground': n, 'field': field, 'id': ref, 'kind': 'UNKNOWN_SOURCE_ADDRESS'})
        if len(g['point'].split()) > 35: warnings.append({'kind': 'LONG_POINT', 'ground': n})
        if len(g['explanation'].split()) > 100: warnings.append({'kind': 'LONG_EXPLANATION', 'ground': n})
    return value, {'run_status': 'OK', 'format_status': 'OK', 'warnings': warnings,
                   'source_issues': issues, 'wrapper_removals': changes,
                   'values_unchanged': True, 'semantic_correctness_certified': False}


def validate_output(value):
    """V21 contract intentionally has no hard writing/count limits; V20 is unchanged."""
    schema = output_schema()
    def check(data, spec, path='$'):
        if 'enum' in spec and data not in spec['enum']:
            raise ValueError('FORMAT_ERROR: '+path+' outside enum')
        kind = spec['type']
        if kind == 'object':
            if not isinstance(data, dict) or set(data) != set(spec['required']):
                raise ValueError('FORMAT_ERROR: '+path+' missing/extra fields')
            for key, item in data.items(): check(item, spec['properties'][key], path+'.'+key)
        elif kind == 'array':
            if not isinstance(data, list): raise ValueError('FORMAT_ERROR: '+path+' not array')
            for n, item in enumerate(data): check(item, spec['items'], path+'[%d]' % n)
        elif kind == 'string' and not isinstance(data, str):
            raise ValueError('FORMAT_ERROR: '+path+' not string')
    check(value, schema)


def reading_view(segments):
    """Strip balanced citation wrappers across contiguous lines without moving visible text."""
    ids = [s['id'] for s in segments]
    if len(ids) != len(set(ids)): raise ValueError('Duplicate source IDs')
    text = '\n'.join(s['text'] for s in segments)
    starts = []; offset = 0
    for s in segments:
        starts.append(offset); offset += len(s['text']) + 1
    removed = set(); spans = []
    for match in re.finditer(r'cite([^†]*?)†([^]*?)', text):
        begin, finish = match.span()
        touched = [i for i, start in enumerate(starts)
                   if start < finish and start + len(segments[i]['text']) > begin]
        # Cross-line edits require explicit provenance and consecutive original lines.
        if len(touched) > 1:
            group = [segments[i] for i in touched]
            if any('original_line' not in s or 'source_document' not in s for s in group): continue
            if any(b['source_document'] != a['source_document'] or
                   b['original_line'] != a['original_line'] + 1 for a, b in zip(group, group[1:])): continue
        # No nested starts: an ambiguous pair remains untouched.
        if 'cite' in match.group(1) or 'cite' in match.group(2): continue
        prefix_end = match.start(2)
        removed.update(range(begin, prefix_end)); removed.add(finish - 1)
        spans.append({'raw_joined_start': begin, 'raw_joined_end': finish,
                      'removed_prefix': text[begin:prefix_end], 'removed_suffix': text[finish-1:finish]})
    result = []; maps = []
    for i, s in enumerate(segments):
        start = starts[i]
        kept = [j for j in range(len(s['text'])) if start + j not in removed]
        result.append({**copy.deepcopy(s), 'text': ''.join(s['text'][j] for j in kept)})
        maps.append({'id': s['id'], 'original_text_sha256': digest(s['text'].encode()),
                     'view_character_to_original_character': kept})
    return {'segments': result, 'original_segments_sha256': digest(segments),
            'mapping': maps, 'removed_wrappers': spans,
            'unresolved_markup': any('cite' in s['text'] or '' in s['text'] for s in result),
            'semantic_rewrite': False}


def query_text(issue, explicit_act_names, neutral_description):
    """Inputs are pre-frozen issue/explicit names/neutral facts, never model answers."""
    return '\n'.join([issue] + list(explicit_act_names) + [neutral_description])


def legal_payload(unit):
    return {k: copy.deepcopy(unit[k]) for k in ('id', 'text', 'source', 'version_status', 'scope', 'dependencies') if k in unit}


def render_units(units):
    # This exact string is measured and delivered to the final model.
    return json.dumps([legal_payload(u) for u in units], ensure_ascii=False, separators=(',', ':'))


def select_units(ranking, units, max_units=8, max_characters=20000, excluded_ids=None):
    registry = {u['id']: u for u in units}; excluded_ids = excluded_ids or {}
    if len(registry) != len(units): raise ValueError('Duplicate legal units')
    chosen = []; decisions = []
    def closure(key, active, visited):
        if key in active: return []  # cyclic dependencies are a finite set, not recursive text
        if key in visited: return []
        if key not in registry: raise KeyError(key)
        if key in excluded_ids: raise ValueError(key)
        visited.add(key); active.add(key); order = [key]
        for dep in sorted(registry[key].get('dependencies', [])):
            order.extend(closure(dep, active, visited))
        active.remove(key); return order
    for item in ranking:
        key = item['id']
        if key in chosen:
            decisions.append({'id': key, 'decision': 'ALREADY_INCLUDED_AS_UNIT_OR_DEPENDENCY'}); continue
        try: required = closure(key, set(), set())
        except KeyError as e:
            decisions.append({'id': key, 'decision': 'MISSING_REQUIRED_DEPENDENCY', 'missing': str(e)}); continue
        except ValueError as e:
            decisions.append({'id': key, 'decision': 'DEFINITELY_INCOMPATIBLE', 'excluded': str(e), 'reason': excluded_ids.get(str(e), excluded_ids.get(key))}); continue
        candidate = chosen + [k for k in required if k not in chosen]
        characters = len(render_units([registry[k] for k in candidate]))
        if len(candidate) > max_units or characters > max_characters:
            decisions.append({'id': key, 'decision': 'ATOMIC_CONTEXT_EXCEEDS_BUDGET', 'required_ids': required,
                              'would_be_units': len(candidate), 'would_be_characters': characters}); continue
        chosen = candidate
        decisions.append({'id': key, 'decision': 'SELECTED_WITH_COMPLETE_DEPENDENCIES', 'required_ids': required})
    selected = [registry[k] for k in chosen]
    return {'selected_ids': chosen, 'units': selected, 'decisions': decisions,
            'legal_characters': len(render_units(selected)), 'dependency_complete': True,
            'scope_note': 'No scope/condition inference: only explicitly supplied definite exclusions are applied.'}


def dedupe_rules(ranking, cards):
    registry = {c['id']: c for c in cards}; seen = set(); result = []; trace = []
    if len(registry) != len(cards): raise ValueError('Duplicate rule IDs')
    for r in ranking:
        unit = registry[r['id']]['legal_unit_id']
        duplicate = unit in seen
        trace.append({**r, 'legal_unit_id': unit, 'duplicate_legal_unit': duplicate})
        if not duplicate:
            seen.add(unit); result.append({'id': unit, 'rank': len(result)+1, 'first_card': r['id']})
    return result, trace


def retrieve_pair(units, cards, query, directory, excluded_ids=None):
    unit_ids = {u['id'] for u in units}
    if any(c['legal_unit_id'] not in unit_ids for c in cards):
        raise ValueError('Rule points to missing original legal unit')
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    raw_path = directory / 'original.sqlite'; rule_path = directory / 'rules.sqlite'
    original_manifest = authority_index.build(units, raw_path)
    rule_units = [{'id': c['id'], 'text': c['text'], 'source': c['source'], 'version_status': c['version_status']} for c in cards]
    rule_manifest = authority_index.build(rule_units, rule_path)
    a = authority_index.search(raw_path, query, CONFIG['A_text_candidates'])
    b_original = authority_index.search(raw_path, query, CONFIG['B_text_candidates'])
    b_rule = authority_index.search(rule_path, query, CONFIG['B_rule_candidates']) if cards else []
    b_dedup, dedup_trace = dedupe_rules(b_rule, cards)
    b = retrieve.fuse({'original': b_original, 'rules': b_dedup}, k=CONFIG['rrf_k'], limit=40)
    selected = {'A': select_units(a, units, excluded_ids=excluded_ids),
                'B': select_units(b, units, excluded_ids=excluded_ids)}
    return {'version': VERSION, 'configuration': CONFIG, 'query': query,
            'index_manifests': {'original': original_manifest, 'rules': rule_manifest},
            'candidates': {'A_original': a, 'B_original': b_original, 'B_rule': b_rule,
                           'B_rule_dedup_trace': dedup_trace, 'B_rule_units': b_dedup, 'B_fused': b},
            'selected': selected, 'legal_blocks_identical': render_units(selected['A']['units']) == render_units(selected['B']['units']),
            'retrieval_is_legal_applicability': False}


def prompt(source, units, question):
    legal = render_units(units)
    if len(legal) > CONFIG['max_legal_characters']: raise ValueError('LEGAL_INPUT_TOO_LONG')
    return ('SELF-CONTAINED LEGAL DEVELOPMENT TASK\nQUESTION\n'+question+
            '\nTARGET METADATA\n'+json.dumps({k:source[k] for k in ('case_id','court','date','input_scope','limitations') if k in source},ensure_ascii=False)+
            '\nTWO COMPLETE FICTIONAL TEACHING EXAMPLES\n'+json.dumps(EXAMPLES,ensure_ascii=False,separators=(',',':'))+
            '\nSELECTED ORIGINAL LEGAL UNITS (metadata are context, not target facts)\n'+legal+
            '\nCOMPLETE ALLOWED TARGET RECORD\n'+'\n'.join('['+s['id']+'] '+s['text'] for s in source['segments'])+
            '\nFINAL TASK\n'+FINAL+'\nOUTPUT SCHEMA (web has no local token mask)\n'+json.dumps(output_schema(),separators=(',',':')))
