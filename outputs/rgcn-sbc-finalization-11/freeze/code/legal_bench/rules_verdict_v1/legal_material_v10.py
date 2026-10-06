"""Versioned bounded source/representation study. No model calls or semantic repair."""
import copy
import hashlib
import itertools
import json
import re
from pathlib import Path

from . import authority_index, retrieve, rule_retrieval_v21 as legacy

VERSION = 'LEGAL_MATERIAL_VIEW_V10'
PRIMARY_CONFIG = dict(raw_candidates=20, description_candidates=20,
                      fused_candidates=40, rrf_k=60, max_units=None,
                      max_legal_characters=20000, seed=20261003)
V23_CONFIG = dict(PRIMARY_CONFIG, raw_candidates=40, augmented_raw_candidates=20,
                 max_units=8)
PAYLOAD_FIELDS = ('id', 'text', 'source', 'version_status', 'scope', 'dependencies',
                  'coverage_limit', 'date', 'status', 'authority_status', 'source_status')


def sha(data):
    if not isinstance(data, bytes):
        data = data.encode() if isinstance(data, str) else json.dumps(data, ensure_ascii=False, sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


AUDIT_KEYS = {'raw_provenance','raw_path','raw_sha256','raw_char_range','raw_byte_range','raw_physical_line','response_index','storage_path','cache_path'}
def strip_audit(value):
    if isinstance(value, dict): return {k:strip_audit(v) for k,v in value.items() if k not in AUDIT_KEYS}
    if isinstance(value, list): return [strip_audit(v) for v in value]
    return copy.deepcopy(value)
def payload(unit):
    # All legal/status/version/limits fields retained; only named engineering trace omitted.
    return strip_audit(unit)


def render(units):
    return json.dumps([payload(u) for u in units], ensure_ascii=False, separators=(',', ':'))


def registry(units):
    result = {u['id']: u for u in units}
    if len(result) != len(units):
        raise ValueError('DUPLICATE_UNIT_ID')
    return result


def closure(key, units):
    table = registry(units); seen = set(); active = set(); ordered = []; cycles = []
    def visit(k):
        if k in active:
            cycles.append(k); return
        if k in seen: return
        if k not in table: raise KeyError(k)
        seen.add(k); active.add(k); ordered.append(k)
        for dep in sorted(table[k].get('dependencies', [])): visit(dep)
        active.remove(k)
    visit(key)
    return ordered, cycles


def select(ranking, units, config, mandatory=(), excluded=None):
    """Atomically deliver declared dependency sets; same renderer counts and submits."""
    table = registry(units); order = {u['id']: i for i, u in enumerate(units)}
    excluded = excluded or {}; chosen = []; decisions = []
    def expand(keys):
        required = []; cycles = []
        for key in keys:
            keys2, cycles2 = closure(key, units); cycles.extend(cycles2)
            for k in keys2:
                if k in excluded: raise ValueError(k)
                if k not in required: required.append(k)
        return required, cycles
    def sized(keys):
        material = [table[k] for k in sorted(set(keys), key=order.get)]
        return material, len(render(material))
    try: chosen, cycles = expand(mandatory)
    except (KeyError, ValueError) as err:
        return dict(run_status='BUDGET_ASSEMBLY_ERROR', error='MANDATORY_BUNDLE_INVALID', detail=str(err), selected_ids=[], units=[], decisions=[])
    material, count = sized(chosen)
    limit = config.get('max_units')
    if count > config['max_legal_characters'] or (limit is not None and len(chosen) > limit):
        return dict(run_status='BUDGET_ASSEMBLY_ERROR', error='MANDATORY_BUNDLE_TOO_LONG', legal_characters=count, selected_ids=[], units=[], decisions=[])
    for item in ranking:
        key = item['id']
        if key in chosen:
            decisions.append(dict(id=key, decision='ALREADY_DELIVERED')); continue
        try: required, cycles = expand([key])
        except KeyError as err:
            decisions.append(dict(id=key, decision='MISSING_REQUIRED_SOURCE', missing=str(err))); continue
        except ValueError as err:
            decisions.append(dict(id=key, decision='EXPLICIT_SCOPE_EXCLUSION', excluded=str(err))); continue
        candidate = chosen + [k for k in required if k not in chosen]
        proposed, characters = sized(candidate)
        if characters > config['max_legal_characters'] or (limit is not None and len(candidate) > limit):
            decisions.append(dict(id=key, decision='ATOMIC_BUNDLE_EXCEEDS_BUDGET', required_ids=required,
                                  would_be_characters=characters, would_be_units=len(candidate))); continue
        chosen = candidate
        decisions.append(dict(id=key, decision='SELECTED', required_ids=required, cycles=cycles))
    material, count = sized(chosen)
    return dict(run_status='OK', units=material, selected_ids=[u['id'] for u in material],
                decisions=decisions, mandatory_ids=list(mandatory), legal_characters=count,
                dependency_complete=True, semantic_completeness_certified=False)


def retrieve_arms(units, descriptions, query, directory, config=None, mandatory=(), excluded=None):
    config = copy.deepcopy(config or PRIMARY_CONFIG); directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True); table = registry(units)
    raw_path = directory/'original.sqlite'
    manifests = {'raw': authority_index.build(units, raw_path)}
    base = authority_index.search(raw_path, query, config['raw_candidates'])
    rankings = {'A': base}; traces = {}; selections = {}
    for arm, records in descriptions.items():
        if len({r['legal_unit_id'] for r in records}) != len(records): raise ValueError('DUPLICATE_DESCRIPTION_UNIT')
        if any(r['legal_unit_id'] not in table for r in records): raise ValueError('UNKNOWN_DESCRIPTION_SOURCE')
        indexed = [dict(id=r['legal_unit_id'], text=r['description'], source=table[r['legal_unit_id']]['source'],
                        version_status=table[r['legal_unit_id']]['version_status']) for r in records]
        path = directory/(arm+'.sqlite'); manifests[arm] = authority_index.build(indexed, path)
        raw = authority_index.search(raw_path, query, config.get('augmented_raw_candidates', config['raw_candidates']))
        secondary = authority_index.search(path, query, config['description_candidates']) if records else []
        rankings[arm] = retrieve.fuse({'raw': raw, 'description': secondary}, k=config['rrf_k'], limit=config['fused_candidates'])
        traces[arm] = dict(raw=raw, description=secondary, fused=rankings[arm])
    for arm, ranks in rankings.items(): selections[arm] = select(ranks, units, config, mandatory, excluded)
    return dict(version=VERSION, configuration=config, query=query, index_manifests=manifests,
                rankings=rankings, route_traces=traces, selected=selections,
                retrieval_certifies_applicability=False)


def prompt(source, selected, question, config=None):
    config = config or PRIMARY_CONFIG
    legal = render(selected)
    if len(legal) > config['max_legal_characters']: raise ValueError('LEGAL_INPUT_TOO_LONG')
    # Exactly V21's final instructions/examples; only payload metadata preservation changes.
    return ('SELF-CONTAINED LEGAL DEVELOPMENT TASK\nQUESTION\n'+question+
            '\nTARGET METADATA\n'+json.dumps({k:source[k] for k in ('case_id','court','date','input_scope','limitations') if k in source},ensure_ascii=False)+
            '\nTWO COMPLETE FICTIONAL TEACHING EXAMPLES\n'+json.dumps(legacy.EXAMPLES,ensure_ascii=False,separators=(',',':'))+
            '\nSELECTED ORIGINAL LEGAL UNITS (metadata are context, not target facts)\n'+legal+
            '\nCOMPLETE ALLOWED TARGET RECORD\n'+'\n'.join('['+s['id']+'] '+s['text'] for s in source['segments'])+
            '\nFINAL TASK\n'+legacy.FINAL+'\nOUTPUT SCHEMA (web has no local token mask)\n'+json.dumps(legacy.output_schema(),separators=(',',':')))


def normalize_whitespace(text):
    """Keep original bytes separately; each normalized character maps to a raw span."""
    chars = []; mapping = []
    for match in re.finditer(r'\s+|\S', text):
        value = ' ' if match.group().isspace() else match.group()
        chars.append(value); mapping.append([match.start(), match.end()])
    return ''.join(chars), mapping


def locate_quote(text, quote):
    if not quote: return dict(status='EMPTY_QUOTE')
    start = text.find(quote)
    if start >= 0: return dict(status='EXACT', raw_start=start, raw_end=start+len(quote))
    normalized, mapping = normalize_whitespace(text); needle, _ = normalize_whitespace(quote)
    start = normalized.find(needle)
    if start < 0: return dict(status='UNLOCATED', semantic_support_certified=False)
    return dict(status='WHITESPACE_ONLY', normalized_start=start, normalized_end=start+len(needle),
                raw_start=mapping[start][0], raw_end=mapping[start+len(needle)-1][1],
                normalized_to_original_spans=mapping[start:start+len(needle)], semantic_support_certified=False)


def exact_slice(parent, start, end, key):
    if not 0 <= start < end <= len(parent['text']): raise ValueError('INVALID_SLICE')
    result = copy.deepcopy(parent); result['id'] = key; result['text'] = parent['text'][start:end]
    result['source']['parent_unit_id'] = parent['id']
    result['source']['parent_start'] = start; result['source']['parent_end'] = end
    if 'joined_start' in result['source']:
        result['source']['joined_start'] += start
        result['source']['joined_end'] = result['source']['joined_start']+end-start
    return result


def shared_key(case_id, replicate_id, complete_submission, visible_profile):
    return sha(dict(case_id=case_id, replicate_id=replicate_id,
                    complete_submission_hash=sha(complete_submission), visible_generation_profile=visible_profile))


def delivery(reference_items, delivered_ids, mandatory_ids, units, max_characters=20000):
    def bundle(item):
        keys = set()
        for key in item['unit_ids']:
            expanded, _ = closure(key, units); keys.update(expanded)
        return keys
    rows = []; supplied = set(delivered_ids); compulsory = set(mandatory_ids)
    for item in reference_items:
        need = bundle(item)
        rows.append(dict(id=item['id'], role=item['role'], status=item['status'], bundle=sorted(need),
                         satisfied_by_mandatory=need <= compulsory, delivered=need <= supplied,
                         reachable=len(render([u for u in units if u['id'] in need | compulsory])) <= max_characters))
    primary = [r for r in rows if r['status']=='VERIFIED_SOURCE_ANCHORED' and not r['satisfied_by_mandatory']]
    disputed = [r for r in rows if r['status']=='DISPUTED' and not r['satisfied_by_mandatory']]
    variants = []
    for mask in itertools.product([False, True], repeat=len(disputed)):
        included = primary+[r for r, active in zip(disputed, mask) if active]
        variants.append(dict(disputed_included=[r['id'] for r, active in zip(disputed, mask) if active],
                             numerator=sum(r['delivered'] for r in included), denominator=len(included),
                             rate=sum(r['delivered'] for r in included)/len(included) if included else None))
    return dict(rows=rows, numerator=sum(r['delivered'] for r in primary), denominator=len(primary),
                rate=sum(r['delivered'] for r in primary)/len(primary) if primary else None,
                symmetric_sensitivity=variants, finite_reference_not_exhaustive_recall=True)
