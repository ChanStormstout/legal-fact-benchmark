#!/usr/bin/env python3
"""One authorized 569555/P01 attempt after lossless cache and reference gates."""
import argparse
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from legal_bench.proof_carrying import declared_references_v20_4 as refs
from legal_bench.proof_carrying import shared_sources_v20_3 as transport
from legal_bench.proof_carrying.artifact_state_v20_2 import freeze_files, verify_files, byte_hash, digest, paused
from legal_bench.proof_carrying.schema_contract_v19_6 import validate
from scripts.proof_shared_sources_v20_3 import read, save, utc, serialized, process_saved, collections_count_analyses

OUT = ROOT/'outputs/proof-declared-references-v20-4'
SHARED = ROOT/'outputs/proof-shared-sources-v20-3'
PARENT = ROOT/'outputs/proof-source-verification-v20/continuation-01'
REPAIR = ROOT/'outputs/proof-source-verification-repair-v20-2'


def prepare():
    if (OUT/'preparation/plan.json').exists(): return read(OUT/'preparation/plan.json')
    verify_files(ROOT, read(SHARED/'freeze/protocol.json'))
    assert str(OUT.relative_to(ROOT)) in read(ROOT/'docs/repository-artifacts.json')['artifact_roots']
    preserved = read(SHARED/'preserved-old-files.json')
    for base in (SHARED,):
        preserved.update({str(p.relative_to(ROOT)): byte_hash(p) for p in base.rglob('*') if p.is_file()})
    preserved.update(read(SHARED/'freeze/protocol.json')['code_hashes'])
    save(OUT/'preserved-old-files.json', preserved)
    prior = SHARED/'preparation/569555/P01'; dest = OUT/'preparation/569555/P01'
    for name in ('schema.json', 'original-schema.json', 'fixture.json'):
        save(dest/name, read(prior/name))
    (dest/'prompt.txt').write_text(refs.INSTRUCTION+(prior/'prompt.txt').read_text())
    slot = copy.deepcopy(read(SHARED/'preparation/plan.json')['tasks'][0])
    assert (slot['case_id'], slot['part']['id']) == ('569555', 'P01')
    prior_budget = read(SHARED/'preparation/plan.json')
    shared_used = sum(read(p)['elapsed_seconds'] for p in (SHARED/'local').glob('*/*/run.json'))
    plan = {'version': refs.VERSION, 'task': slot, 'created_at': utc(),
            'model_runtime': prior_budget['model_runtime'], 'per_call_seconds': 3600,
            'bounded_run_seconds': 3600, 'max_output_tokens': 16384, 'retry_count': 0,
            'old_P_stage_budget': prior_budget['old_P_stage_budget'],
            'previous_P_seconds_used': prior_budget['old_P_seconds_used']+shared_used,
            'remaining_P_seconds': prior_budget['old_P_remaining_seconds']-shared_used,
            'scope': 'ONE_USER_AUTHORIZED_569555_P01_ATTEMPT_ONLY',
            'original_batch_stays_paused': True, 'no_training': True, 'no_Q': True, 'no_web': True, 'no_push': True,
            'change': 'Declared local reference masks and dependency field order only; source transport, full input, rules, model and token budgets retained.'}
    assert plan['bounded_run_seconds'] <= plan['remaining_P_seconds']
    save(OUT/'preparation/plan.json', plan); return plan


def character_replay(value, schema):
    from legal_bench.mlx_json_constraint_v20_4 import DeclaredReferenceParser
    text = serialized(value); parser = DeclaredReferenceParser(schema)
    for i, char in enumerate(text):
        try: parser = parser.add_character(char)
        except ValueError:
            return {'accepted': False, 'rejected_character': i, 'value_path': list(parser.value_path())}
    assert parser.can_end()
    return {'accepted': True, 'characters': len(text)}


def token_replay(value, schema, tok, data):
    from legal_bench.mlx_json_constraint_v20_4 import SchemaMask
    mask = SchemaMask(data, schema); ids = tok.encode(serialized(value), add_special_tokens=False)
    for i, tid in enumerate(ids):
        if tid not in mask.enforcer.get_allowed_tokens(ids[:i]).allowed_tokens:
            raise ValueError('REAL_TOKEN_REPLAY_REJECTED:'+str(i))
    assert tok.eos_token_id in mask.enforcer.get_allowed_tokens(ids).allowed_tokens
    return {'tokens': len(ids), 'EOS_allowed': True}


def compare_entries(old, new):
    """Check every result; explicitly decode only the learner's serialized P block.

    Dependency ordering can alter JSON key order inside prompt text and hashes.
    This is not byte-identical learner input and is recorded, never hidden.
    """
    a = copy.deepcopy(old); b = copy.deepcopy(new)
    a.pop('raw_sha256', None); b.pop('raw_sha256', None)
    def normalize(entry):
        learner = entry['learner_inputs']; p_texts = set()
        for pair in learner.get('ce_pairs', []):
            for block in pair['shared_material_blocks']:
                if block['id'] == 'P':
                    p_texts.add(block['text']); block['text'] = serialized(json.loads(block['text']))
                    block['text'] = json.dumps(json.loads(block['text']), sort_keys=True, ensure_ascii=False, separators=(',', ':'))
            pair['shared_material_hash'] = 'SERIALIZED_MATERIAL_HASH_CHECKED_SEPARATELY'
        for block in learner['common_material_manifest']['blocks']:
            if block['id'] == 'P': block['sha256'] = 'SERIALIZED_P_HASH_CHECKED_SEPARATELY'
        for node in learner['graph']['nodes']:
            for text in p_texts:
                if text in node['text']:
                    canonical = json.dumps(json.loads(text), sort_keys=True, ensure_ascii=False, separators=(',', ':'))
                    node['text'] = node['text'].replace(text, canonical)
        return entry
    # Other hashes, source text, arrays, graph edges and deterministic judgments
    # still compare exactly. Only identified P serialization hashes differ.
    assert normalize(a) == normalize(b)
    return {'deterministic_results_and_learner_data_equal': True,
            'learner_input_bytes_equal': old['learner_inputs'] == new['learner_inputs'],
            'serialized_P_key_order_may_change': True}


def acceptance():
    prepare()
    tests = ['tests.test_constraint_viability_v20_1', 'tests.test_source_verification_v20',
             'tests.test_pipeline_diagnostic_v19_8', 'tests.test_final_capacity_v19_8_1',
             'tests.test_source_verification_v20_2', 'tests.test_shared_sources_v20_3',
             'tests.test_declared_references_v20_4']
    result = subprocess.run([sys.executable, '-B', '-m', 'unittest', *tests, '-q'], cwd=ROOT, capture_output=True, text=True)
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    (OUT/'engineering').mkdir(parents=True, exist_ok=True)
    (OUT/'engineering/tests.txt').write_text(result.stdout+result.stderr)
    from transformers import AutoTokenizer
    from legal_bench.mlx_json_constraint import tokenizer_data
    tok = AutoTokenizer.from_pretrained((ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(), local_files_only=True)
    data = tokenizer_data(tok, getattr(tok, 'eos_token_ids', tok.eos_token_id))
    rows = []; legal_values = []; legal_units = []; partial_rows = []
    paths = sorted((PARENT/'local').glob('*/P*/parsed.json')) + sorted((SHARED/'local').glob('*/P*/expanded.json'))
    for path in paths:
        prior = path.parent; cid = prior.parent.name; part = prior.name; raw = read(path)
        s = read(prior/'original-schema.json') if (prior/'original-schema.json').exists() else read(prior/'schema.json')
        if prior.is_relative_to(SHARED): s = read(SHARED/'preparation'/cid/part/'original-schema.json')
        cs = transport.schema(s); compact = refs.wire_order(transport.pack(raw), cs)
        validate(compact, cs); expanded = transport.expand(compact)
        assert expanded == raw; assert transport.check_expansion(compact, expanded, s)['status'] == 'OK'
        f = read(PARENT/'preparation'/cid/'fixture.json')
        slot = next(x for x in read(PARENT/'freeze/protocol.json')['slots'] if x['case_id'] == cid and x['part']['id'] == part)
        old_entry = process_saved(f['case'], f['rules'], slot['part'], serialized(raw), s, 'V19_8', 'OK')
        new_entry = process_saved(f['case'], f['rules'], slot['part'], serialized(expanded), s, 'V19_8', 'OK')
        comparison = compare_entries(old_entry, new_entry)
        a = refs.audit(compact, cs); replay = character_replay(compact, cs)
        assert replay['accepted'] == (a['status'] == 'PASS')
        label = 'shared' if prior.is_relative_to(SHARED) else 'original'
        save(OUT/'engineering/replays'/label/cid/part/'reference-audit.json', a)
        row = {'origin': str(path.relative_to(ROOT)), 'case_id': cid, 'part': part,
               'all_values_and_array_order_preserved': True, 'actual_entry_comparison': comparison,
               'invalid_occurrences': len(a['violations']), 'reference_gate': a['status'], 'character_replay': replay}
        rows.append(row)
        if a['status'] == 'PASS': legal_values.append((compact, cs, row))
        for pid, unit in raw['analyses'].items():
            ps = copy.deepcopy(s); ps['properties'] = {'analyses': copy.deepcopy(s['properties']['analyses'])}; ps['required'] = ['analyses']
            ps['properties']['analyses']['properties'] = {pid: ps['properties']['analyses']['properties'][pid]}; ps['properties']['analyses']['required'] = [pid]
            pc = refs.wire_order(transport.pack({'analyses': {pid: unit}}), transport.schema(ps))
            if refs.audit(pc, transport.schema(ps))['status'] == 'PASS':
                assert character_replay(pc, transport.schema(ps))['accepted']; legal_units.append((pc, transport.schema(ps)))
    # Failed prefixes remain failures; only fully closed units can be checked for information fidelity.
    dec = json.JSONDecoder()
    failed = list((PARENT/'local').glob('*/P*/run.json')) + list((SHARED/'local').glob('*/P*/run.json'))
    for path in failed:
        if read(path)['run_status'] != 'OUTPUT_TRUNCATED': continue
        prior = path.parent; cid = prior.parent.name; part = prior.name
        s = read(SHARED/'preparation'/cid/part/'original-schema.json') if prior.is_relative_to(SHARED) else read(prior/'schema.json')
        text = (prior/'raw-response.txt').read_text(); closed = {}
        for m in re.finditer(r'"([^"\\]+)"\s*:\s*\{', text):
            if m[1] not in s['properties']['analyses']['properties']: continue
            try: unit, _ = dec.raw_decode(text, text.find('{', m.start()))
            except ValueError: continue
            closed[m[1]] = unit
        ps = copy.deepcopy(s); ps['properties'] = {'analyses': copy.deepcopy(s['properties']['analyses'])}; ps['required'] = ['analyses']
        ps['properties']['analyses']['properties'] = {k:v for k,v in ps['properties']['analyses']['properties'].items() if k in closed}; ps['properties']['analyses']['required'] = list(closed)
        value = {'analyses': closed}
        if prior.is_relative_to(SHARED):
            table, _ = dec.raw_decode(text, text.index('[', text.index('"source_sets"')))
            value = transport.expand({'source_sets': table, **value})
        cs = transport.schema(ps); compact = refs.wire_order(transport.pack(value), cs)
        assert transport.expand(compact) == value; transport.check_expansion(compact, value, ps)
        a = refs.audit(compact, cs); replay = character_replay(compact, cs)
        assert replay['accepted'] == (a['status'] == 'PASS')
        partial_rows.append({'origin': str(path.relative_to(ROOT)), 'complete_units_checked': len(closed),
                             'all_values_preserved': True, 'invalid_occurrences': len(a['violations']),
                             'character_replay': replay, 'not_formal_answer': True})
    assert legal_values and legal_units
    real_tokens = token_replay(*legal_values[0][:2], tok, data)
    # Separate real-token replay of a nonempty reference-bearing legal cached unit.
    cached_unit = next((v,s) for v,s in legal_units if sum(refs.audit(v,s)['checked'].values()) > 0)
    unit_tokens = token_replay(*cached_unit, tok, data)
    gate = {'status': 'PASS', 'tests': int(re.search(r'Ran (\d+) tests', result.stderr)[1]),
            'complete_cache_count': len(rows), 'legal_complete_caches': len(legal_values),
            'invalid_complete_caches_rejected_without_repair': len(rows)-len(legal_values),
            'legal_cached_units_character_replayed': len(legal_units), 'cache_rows': rows,
            'failed_prefix_rows': partial_rows, 'actual_tokenizer_full_cache': real_tokens,
            'actual_tokenizer_reference_bearing_unit': unit_tokens, 'model_calls': 0,
            'model_weights_loaded': False, 'semantic_approval': False}
    save(OUT/'engineering/cache-acceptance.json', gate)
    print(json.dumps({k:v for k,v in gate.items() if k not in ('cache_rows','failed_prefix_rows')}), flush=True)
    return gate


def freeze():
    gate = read(OUT/'engineering/cache-acceptance.json'); assert gate['status'] == 'PASS'
    plan = read(OUT/'preparation/plan.json')
    entries = ['scripts/proof_declared_references_v20_4.py', 'legal_bench/proof_carrying/local_runtime_v20_4.py', 'tests/test_declared_references_v20_4.py']
    prepared = [str(p.relative_to(ROOT)) for p in (OUT/'preparation').rglob('*') if p.is_file()]
    cfg = {**plan, **freeze_files(ROOT, OUT, entries, prepared, read(SHARED/'freeze/protocol.json')['configuration_hashes']),
           'frozen_at': utc(), 'cache_acceptance_sha256': byte_hash(OUT/'engineering/cache-acceptance.json')}
    save(OUT/'freeze/protocol.json', cfg); return cfg


def run():
    cfg = read(OUT/'freeze/protocol.json'); verify_files(ROOT, cfg)
    assert cfg['cache_acceptance_sha256'] == byte_hash(OUT/'engineering/cache-acceptance.json')
    if paused(OUT): print('PAUSED', flush=True); return
    from legal_bench.proof_carrying.local_runtime_v20_4 import Runner, SETTINGS
    assert SETTINGS == cfg['model_runtime']
    dest = OUT/'local/569555/P01'; p = OUT/'preparation/569555/P01'
    if (dest/'run.json').exists(): return summary()
    if (dest/'start.json').exists(): raise ValueError('UNCERTAIN_TASK_NOT_RESUBMITTED')
    runner = Runner((ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(), SETTINGS)
    meta = runner.run((p/'prompt.txt').read_text(), read(p/'schema.json'), dest, 16384, 3600, 'FIXED')
    status = meta['run_status']; formal = None
    if status == 'OK':
        try:
            compact = read(dest/'parsed.json'); a = refs.audit(compact, read(p/'schema.json'))
            save(dest/'reference-audit.json', a)
            if a['status'] != 'PASS': raise ValueError('INDEPENDENT_REFERENCE_AUDIT_REJECTED')
            expanded = transport.expand(compact)
            save(dest/'expansion-check.json', transport.check_expansion(compact, expanded, read(p/'original-schema.json')))
            save(dest/'expanded.json', expanded); f = read(p/'fixture.json')
            entry = process_saved(f['case'], f['rules'], cfg['task']['part'], serialized(expanded), read(p/'original-schema.json'), 'V19_8', 'OK')
            save(dest/'entry-audit.json', entry)
            if entry.get('formal_answer') is None: status = entry['contract_status']
            else: formal = expanded
        except (ValueError, KeyError, TypeError) as exc:
            status = 'REFERENCE_EXPANSION_OR_ENTRY_REJECTED'; save(dest/'entry-failure.json', {'error': repr(exc), 'answer': None})
    save(dest/'formal-answer.json', {'answer': formal, 'status': status, 'semantic_approval': False, 'legal_approval': False})
    summary(); print('ONE_TASK_FINISHED', flush=True)


def summary():
    meta = read(OUT/'local/569555/P01/run.json'); formal = read(OUT/'local/569555/P01/formal-answer.json')
    preserved = read(OUT/'preserved-old-files.json')
    changed = [k for k,v in preserved.items() if byte_hash(ROOT/k) != v]
    if changed: raise ValueError('OLD_FILES_CHANGED:'+str(changed))
    old = read(SHARED/'local/569555/P01/run.json')
    d = OUT/'local/569555/P01'; parsed = read(d/'parsed.json') if (d/'parsed.json').exists() else None
    result = {'version': refs.VERSION, 'case_id': '569555', 'part': 'P01', 'attempts': 1,
              'old_run_status': old['run_status'], 'old_output_tokens': old['output_tokens'],
              'run_status': meta['run_status'], 'formal_status': formal['status'],
              'formal_answer_present': formal['answer'] is not None, 'output_tokens': meta['output_tokens'],
              'finish_reason': meta['finish_reason'], 'seconds': meta['elapsed_seconds'],
              'source_sets': len(parsed['source_sets']) if parsed else None,
              'analysis_coverage': collections_count_analyses(formal['answer']) if formal['answer'] else None,
              'local_reference_audit': read(d/'reference-audit.json') if (d/'reference-audit.json').exists() else None,
              'old_files_verified': len(preserved), 'original_batch_pause_preserved': (PARENT/'PAUSE_REQUESTED.json').exists(),
              'training_calls': 0, 'Q_calls': 0, 'web_calls': 0, 'commit_or_push': False, 'semantic_success': False}
    save(OUT/'results/summary.json', result); return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('command', choices=['prepare', 'accept', 'freeze', 'run', 'summary'])
    {'prepare': prepare, 'accept': acceptance, 'freeze': freeze, 'run': run, 'summary': summary}[parser.parse_args().command]()
