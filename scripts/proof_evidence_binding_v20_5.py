"""Prepare versioned gates and cache acceptance. This CLI has no generation mode."""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from legal_bench.proof_carrying import evidence_binding_gate_v20_5 as gate
from legal_bench.proof_carrying import shared_sources_v20_3 as shared
from legal_bench.proof_carrying.declared_references_v20_4 import wire_order
from legal_bench.proof_carrying.artifact_state_v20_2 import immutable

OUT = ROOT/'outputs/proof-evidence-binding-v20-5'
CHECKS = OUT/'engineering/validation-04'
PREP = OUT/'preparation-02'
SHARED = ROOT/'outputs/proof-shared-sources-v20-3'
DECLARED = ROOT/'outputs/proof-declared-references-v20-4'
PARENT = ROOT/'outputs/proof-source-verification-v20/continuation-01'


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    return immutable(path, value)


def prepare():
    if str(OUT.relative_to(ROOT)) not in read(ROOT/'docs/repository-artifacts.json')['artifact_roots']:
        raise ValueError('UNREGISTERED_OUTPUT_ROOT')
    slots = read(SHARED/'preparation/plan.json')['tasks']
    for slot in slots:
        cid, part = slot['case_id'], slot['part']['id']
        origin = (DECLARED if cid == '569555' else SHARED)/'preparation'/cid/part
        dest = PREP/cid/part
        f, original = read(origin/'fixture.json'), read(origin/'original-schema.json')
        previous = (origin/'prompt.txt').read_text()
        prompt = gate.prompt(previous)
        separator = '\nALLOWED SOURCE (copy the adjacent SRC address):\n'
        assert prompt.split(separator, 1)[1] == previous.split(separator, 1)[1]
        assert 'dynamic existence is checked on import, not guaranteed by the decoder' not in prompt.split(separator, 1)[0]
        save(dest/'fixture.json', f)
        save(dest/'original-schema.json', original)
        save(dest/'schema.json', gate.generation_schema(original, f['case'], f['rules']))
        dest.mkdir(parents=True, exist_ok=True)
        p = dest/'prompt.txt'
        if p.exists() and p.read_text() != prompt: raise ValueError('PREPARED_PROMPT_CHANGED')
        if not p.exists(): p.write_text(prompt)
        save(dest/'part.json', slot['part'])
        save(dest/'material-audit.json', {
            'case_id': cid, 'part': part, 'all_source_values_and_order_preserved': True,
            'original_source_count': len(f['case']['segments']),
            'citable_source_count': len(gate.citation_choices(f['case'])),
            'blank_source_count': len(f['case']['segments'])-len(gate.citation_choices(f['case'])),
            'source_addresses_renumbered': False, 'source_text_tail_identical': True,
            'generation_authorized': False})
    return slots


def cached_acceptance():
    inputs = [ROOT/x['origin'] for x in read(DECLARED/'engineering/cache-acceptance.json')['cache_rows']]
    inputs.append(DECLARED/'local/569555/P01/expanded.json')
    rows = []
    for path in inputs:
        cid, part = path.parent.parent.name, path.parent.name
        if path.is_relative_to(SHARED): prep = SHARED/'preparation'/cid/part
        elif path.is_relative_to(DECLARED): prep = DECLARED/'preparation'/cid/part
        else: prep = PARENT/'preparation'/cid
        f = read(prep/'fixture.json')
        original = read(prep/'original-schema.json') if (prep/'original-schema.json').exists() else read(path.parent/'schema.json')
        raw = read(path); before = copy.deepcopy(raw)
        compact = wire_order(shared.pack(raw), shared.schema(original))
        a = gate.audit(compact, original, f['case'], f['rules'])
        slot = next(s for s in read(PARENT/'freeze/protocol.json')['slots']
                    if s['case_id'] == cid and s['part']['id'] == part)
        entry = gate.process_saved(f['case'], f['rules'], slot['part'], compact, original)
        assert raw == before and shared.expand(compact) == raw
        if a['status'] != 'READY_FOR_CONDITIONAL_PROCESSING':
            assert entry['formal_answer'] is None and entry['conditional_audit'] is None
        else:
            assert entry['formal_answer'] == raw and entry['contract_status'] == 'CONTRACT_VALID'
        label = 'declared' if path.is_relative_to(DECLARED) else 'shared' if path.is_relative_to(SHARED) else 'original'
        save(OUT/'engineering/private/validation-04'/label/cid/part/'gate.json', a)
        row = {'origin': str(path.relative_to(ROOT)), 'status': a['status'],
               'error_counts': dict(Counter(x.get('kind', 'FORMAT') for x in a['errors'] if isinstance(x, dict))),
               'pending_bindings': a.get('pending_bindings'), 'raw_values_preserved': True,
               'formal_answer_null': entry['formal_answer'] is None,
               'automatic_computation_not_run': entry['conditional_audit'] is None}
        previous = path.parent/'entry-audit.json'
        if previous.exists():
            old = read(previous).get('conditional_audit') or {}
            row['saved_old_use_dispositions'] = dict(Counter(x['disposition'] for x in old.get('checks', [])))
        rows.append(row)
    save(CHECKS/'cache-acceptance.json', {'count':len(rows), 'rows':rows,
         'old_answers_repaired':False, 'model_calls':0, 'training_calls':0,
         'semantic_accuracy_evaluated':False})
    return rows


def tokenizer_acceptance():
    from transformers import AutoTokenizer
    from legal_bench.mlx_json_constraint import tokenizer_data
    from legal_bench.mlx_json_constraint_v20_5 import SchemaMask
    from legal_bench.proof_carrying import local_pipeline_v19_8 as core
    from tests.test_evidence_binding_v20_5 import setup, reviews
    from tests.test_pipeline_diagnostic_v19_8 import part
    c, r, raw, original, compact = setup()
    schema = gate.generation_schema(original, c, r)
    tok = AutoTokenizer.from_pretrained((ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(), local_files_only=True)
    data = tokenizer_data(tok, getattr(tok, 'eos_token_ids', tok.eos_token_id))
    mask = SchemaMask(data, schema)
    ids = tok.encode(json.dumps(compact, separators=(',', ':')), add_special_tokens=False)
    for i, tid in enumerate(ids):
        assert tid in mask.enforcer.get_allowed_tokens(ids[:i]).allowed_tokens, i
    assert tok.eos_token_id in mask.enforcer.get_allowed_tokens(ids).allowed_tokens
    actual = gate.process_saved(c, r, part(c, r), compact, original, reviews=reviews(raw, c, r))
    assert actual['contract_status'] == 'CONTRACT_VALID'
    assert all(actual['original_entry'][k]['status'] == 'OK' for k in ('independent_import','independent_merge','independent_check'))
    value = {'scope':'SYNTHETIC_TWO_ANALYSIS_FIXTURE_ONLY', 'tokens':len(ids),'EOS_allowed':True,
             'actual_original_entry_passed':True, 'all_raw_values_preserved':actual['formal_answer']==raw,
             'binding_reviews':'SYNTHETIC_FIXTURE_NOT_REAL_MODEL_ANNOTATIONS',
             'model_weights_loaded':False, 'model_calls':0}
    save(CHECKS/'tokenizer-and-entry.json', value)
    return value


def preserve():
    hashes = read(OUT/'preservation.json')
    changed = [p for p,h in hashes.items() if not (ROOT/p).is_file() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    if changed: raise ValueError('OLD_FILES_CHANGED:'+repr(changed))
    pause = read(PARENT/'pause-summary.json')
    value = {'checked_old_files':len(hashes), 'changed_old_files':0,
             'pause_summary_sha256':hashlib.sha256((PARENT/'pause-summary.json').read_bytes()).hexdigest(),
             'original_pause_preserved':True}
    save(CHECKS/'preservation-check.json', value)
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['verify', 'accept'])
    parser.add_argument('--case-id'); parser.add_argument('--part'); parser.add_argument('--input-dir'); parser.add_argument('--reviews')
    args = parser.parse_args()
    slots = prepare()
    if args.mode == 'accept':
        if not any(s['case_id']==args.case_id and s['part']['id']==args.part for s in slots):
            raise ValueError('TASK_NOT_IN_PREPARED_SCOPE')
        p = PREP/args.case_id/args.part; f = read(p/'fixture.json')
        input_dir = Path(args.input_dir)
        stamp = hashlib.sha256((input_dir/'run.json').read_bytes()).hexdigest()[:16]
        rv = read(args.reviews) if args.reviews else None
        if rv: stamp += '-'+hashlib.sha256(Path(args.reviews).read_bytes()).hexdigest()[:16]
        result = gate.accept_saved(input_dir, OUT/'engineering/private/accepted'/args.case_id/args.part/stamp,
                   f['case'], f['rules'], read(p/'part.json'), read(p/'original-schema.json'), rv)
        print(result['contract_status']); return
    tests = ['tests.test_constraint_viability_v20_1','tests.test_source_verification_v20',
             'tests.test_pipeline_diagnostic_v19_8','tests.test_final_capacity_v19_8_1',
             'tests.test_source_verification_v20_2','tests.test_shared_sources_v20_3',
             'tests.test_declared_references_v20_4','tests.test_evidence_binding_v20_5']
    result = subprocess.run([sys.executable,'-B','-m','unittest',*tests,'-q'], cwd=ROOT,capture_output=True,text=True)
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    log = CHECKS/'tests.txt';log.parent.mkdir(parents=True,exist_ok=True)
    log.write_text(result.stdout+result.stderr)
    caches = cached_acceptance(); tokens = tokenizer_acceptance(); old = preserve()
    print(json.dumps({'cache_count':len(caches),'tokenizer':tokens,'preservation':old,'model_calls':0},ensure_ascii=False))


if __name__ == '__main__': main()
