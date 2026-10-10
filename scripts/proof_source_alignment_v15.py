#!/usr/bin/env python3
"""Actual bounded V15 preparation/import/run entry; never generates a model reply."""
import argparse, datetime, hashlib, json, subprocess, sys, time, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.source_alignment_v15 import prepare, schemas, task, supplement, CONTRACT
from legal_bench.proof_carrying.semantic_interface_v13 import adapt
from legal_bench.proof_carrying.semantic_search_v12 import complete_search
from legal_bench.proof_carrying.contracts import content_hash
from legal_bench.rules_verdict_v1.irac_contract_v1 import validate

ROOT = Path('outputs/proof-source-alignment-v15')
def read(p): return json.loads(Path(p).read_text())
def save(p, obj):
    p = Path(p);p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists(): raise FileExistsError(p)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
def textsave(p, text):
    p = Path(p);p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists(): raise FileExistsError(p)
    p.write_text(text)

def paths(cid):
    b = Path('outputs/proof-semantic-interface-v13/final-audit-03/dev-restored') / cid
    if not (b / 'proposal.json').exists(): b = Path('outputs/proof-semantic-interface-v13/inputs-v13-02') / cid
    cp = b / 'case.json'
    if not cp.exists(): cp = Path('outputs/proof-semantic-search-v12/cohort') / cid / 'case.json'
    return cp, b / 'proposal.json'

def prepare_batch():
    selection = []; screening = []
    fixed = [('396336', 'Q1::R1'), ('594273', 'Q2::R5')]
    queue = read('outputs/proof-semantic-interface-v13/dev-inventory.json')
    for entry in queue:
        cid = entry['case']['case_id']
        if cid in {'396336', '594273'}: continue
        cp, pp = paths(cid)
        if not cp.exists() or not pp.exists():
            screening.append({'case': cid, 'reason': 'EXISTING_SOURCE_OR_P_UNAVAILABLE'});continue
        case, prop = read(cp), read(pp)
        s, _, requests = adapt(case, prop)
        compatible = [q for q in requests if any(r['operator'] in {'ALL', 'ANY'} and r['conclusion_predicate'] == q['predicate'] for r in s['rules'].values())]
        screening.append({'case': cid, 'effective_rules': {k: r['operator'] for k, r in s['rules'].items()},
                          'reason': 'FIRST_COMPATIBLE_REQUEST' if compatible else 'NO_EXECUTABLE_ALL_ANY_WITH_EXISTING_EXCEPTIONS'})
        if compatible:
            fixed.append((cid, compatible[0]['id']))
        if len(fixed) == 4: break
    for cid, qid in fixed:
        cp, pp = paths(cid);case, prop = read(cp), read(pp)
        bundle = prepare(case, prop, qid)
        out = ROOT / 'inputs' / cid
        save(out / 'bundle.json', bundle)
        save(out / 'case.json', case);save(out / 'original-P.json', prop)
        ps, rs = schemas([d['address'] for d in bundle['directory']])
        save(ROOT / 'tasks' / cid / 'proposal.schema.json', ps)
        save(ROOT / 'tasks' / cid / 'review.schema.json', rs)
        textsave(ROOT / 'tasks' / cid / 'proposal-task.txt', task(bundle))
        selection.append({'case_id': cid, 'request_id': qid, 'dispute_id': case['dispute_id'], 'split': case['split'],
            'source_case': str(cp), 'source_P': str(pp), 'case_sha256': hashlib.sha256(cp.read_bytes()).hexdigest(),
            'P_sha256': hashlib.sha256(pp.read_bytes()).hexdigest(), 'bundle_hash': content_hash(bundle),
            'addresses': len(bundle['directory']), 'candidates': len(bundle['candidates']),
            'deep_V14_development': cid in {'396336', '594273'}, 'not_independent_test': True})
    save(ROOT / 'selection.json', {'selection_rule': 'Two fixed V14 requests, then first effective ALL/ANY request in V13 frozen DEV queue, without reading labels/outcomes', 'screening': screening, 'cases': selection})
    # Old calibration is an output-only compatibility ledger, never web input.
    old = read('outputs/proof-semantic-calibration-v14/supervision-calibration.json')
    save(ROOT / 'training-compatibility.json', {'sample_reused': 20, 'new_sampling': False, 'all_other_labels': 'UNREVIEWED_NOT_CERTIFIED',
        'entries': [{'key': d['key'], 'old_label': d['old_label'], 'classification': d['category'],
            'compatibility': 'CHECKED_LIMITED_USE_ONLY' if d['category'] == 'CONTRACT_CONSISTENT' else 'HOLD_FOR_PURPOSE_CLARIFICATION_OR_DISPUTE',
            'old_label_preserved': True, 'reason': d['basis']} for d in old['decisions']]})
    return selection

def freeze():
    code = [Path('legal_bench/proof_carrying/source_alignment_v15.py'), Path('legal_bench/proof_carrying/semantic_checker_v15.py'),
            Path('scripts/proof_source_alignment_v15.py'), Path('scripts/check_semantic_v15.py'), Path('tests/test_proof_source_alignment_v15.py')]
    code += [Path('legal_bench/proof_carrying') / name for name in ['semantic_interface_v13.py','semantic_import_v12.py','semantic_search_v12.py','semantic_checker_v13.py','grounding_v9.py','contracts.py','use_contract_v14.py','realcase_grounding_v3.py']]
    code.append(Path('legal_bench/rules_verdict_v1/irac_contract_v1.py'))
    frozen = {}
    for p in code:
        target = ROOT / 'freeze' / 'code' / p
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists(): raise FileExistsError(target)
        target.write_bytes(p.read_bytes());frozen[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    files = [p for sub in ('inputs', 'tasks') for p in (ROOT / sub).rglob('*') if p.is_file()]
    save(ROOT / 'freeze' / 'use-contract.json', CONTRACT)
    save(ROOT / 'freeze' / 'config.json', {'version': 'V15.1', 'head': subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip(),
        'source_sha256': frozen, 'input_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
        'cases': read(ROOT / 'selection.json')['cases'], 'model_visible': 'ChatGPT', 'mode_visible': 'High', 'exact_model': None,
        'web_calls_max': 8, 'local_model_calls': 0, 'fits': 0, 'retries': 0, 'prompt_language': 'English',
        'sequence': [{'case_id': c['case_id'], 'role': role} for role in ('proposal', 'review') for c in read(ROOT / 'selection.json')['cases']],
        'review_task_assembly': 'Frozen task(bundle, role=review, proposed=actual raw JSON); actual content saved/hash-pinned after proposal, no manual correction',
        'failure_policy': 'Null technical answer, dependency-local skip, no retry. Access failure: preserve unknown submission state and resume only unsent positions.',
        'evaluation': ['object mapping and attribution', 'specific use versus whole-premise completeness', 'opposition and stage preservation', 'conditional paths and erroneous acceptance', 'independent review cost and remaining semantic reliance'],
        'legal_approval': 'PENDING_DISTINCT_FROM_ENGINEERING_AND_MODEL_REVIEW', 'TEST_SEALED_read': False})

def assert_frozen():
    cfg = read(ROOT / 'freeze/config.json')
    for name, digest in {**cfg['source_sha256'], **cfg['input_sha256']}.items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
            raise ValueError('FROZEN_FILE_CHANGED:' + name)

def import_reply(cid, role):
    assert_frozen()
    rawfile = ROOT / 'raw' / cid / role / 'assistant.txt'
    dest = ROOT / 'raw' / cid / role / 'import.json'
    raw = rawfile.read_text();normalized = raw.strip();operations = []
    if normalized.startswith('```') and normalized.endswith('```'):
        normalized = normalized.split('\n', 1)[1].rsplit('```', 1)[0].strip();operations.append('REMOVED_OUTER_MARKDOWN_FENCE_ONLY')
    try:
        obj = json.loads(normalized)
        errors = validate(obj, read(ROOT / 'tasks' / cid / (role + '.schema.json')))
        if errors: raise ValueError(errors)
        save(dest, {'status': 'OK', 'answer': obj, 'format_operations': operations, 'raw_sha256': hashlib.sha256(rawfile.read_bytes()).hexdigest()})
        if role == 'proposal':
            bundle = read(ROOT / 'inputs' / cid / 'bundle.json')
            save(ROOT / 'raw' / cid / role / 'supplement.json', supplement(bundle, obj))
            textsave(ROOT / 'tasks' / cid / 'review-task.txt', task(bundle, 'review', obj))
        else:
            proposal = read(ROOT / 'raw' / cid / 'proposal' / 'supplement.json')
            save(ROOT / 'raw' / cid / role / 'review.json', {'origin': 'ACTUAL_INDEPENDENT_MODEL_ASSISTED_SOURCE_REVIEW', 'proposal_sha256': proposal['proposal_sha256'], 'raw': obj, 'formal_legal_approval': False})
    except Exception as e:
        save(dest, {'status': 'TECHNICAL_FAILURE', 'answer': None, 'error': repr(e), 'raw_preserved': True, 'format_operations': operations})

def run(bundle, supplement_, review_, view, dest):
    dest = Path(dest);start = time.perf_counter()
    if dest.exists(): raise FileExistsError(dest)
    dest.mkdir(parents=True)
    try:
        search = complete_search(bundle['candidates'], bundle['snapshot']['rules'], bundle['requests'], bundle['snapshot']['contracts'])
        for name, data in [('bundle', bundle), ('search', search), ('settings', {'view': view}), ('supplement', supplement_), ('review', review_)]:
            if data is not None: save(dest / (name + '.json'), data)
        p = subprocess.run([sys.executable, 'scripts/check_semantic_v15.py', str(dest)], capture_output=True, text=True, timeout=120)
        textsave(dest / 'checker.stdout.txt', p.stdout);textsave(dest / 'checker.stderr.txt', p.stderr)
        if p.returncode: raise RuntimeError(p.stderr)
        checked = json.loads(p.stdout);save(dest / 'checked.json', checked)
        save(dest / 'run.json', {'status': 'OK', 'seconds': time.perf_counter() - start, 'answer': checked['requests'], 'formal_legal_approval': False})
        return checked
    except Exception as e:
        save(dest / 'failure.json', {'status': 'TECHNICAL_FAILURE', 'answer': None, 'error': repr(e), 'traceback': traceback.format_exc()})
        raise

def run_batch():
    assert_frozen();rows = []
    for c in read(ROOT / 'selection.json')['cases']:
        cid = c['case_id'];bundle = read(ROOT / 'inputs' / cid / 'bundle.json')
        sp = ROOT / 'raw' / cid / 'proposal/supplement.json';rp = ROOT / 'raw' / cid / 'review/review.json'
        sup = read(sp) if sp.exists() else None;rev = read(rp) if rp.exists() else None
        for view in ['D', 'P', 'R']:
            dest = ROOT / 'runs' / cid / view
            if view != 'D' and sup is None:
                save(dest / 'failure.json', {'status': 'SKIPPED_DEPENDENCY_FAILURE', 'answer': None, 'reason': 'Proposal unavailable'});continue
            if view == 'R' and rev is None:
                save(dest / 'failure.json', {'status': 'SKIPPED_DEPENDENCY_FAILURE', 'answer': None, 'reason': 'Independent review unavailable'});continue
            result = run(bundle, sup if view != 'D' else None, rev if view == 'R' else None, view, dest)
            rows.append({'case_id': cid, 'view': view, 'requests': result['requests'], 'structure_checks': result['structure_checks']})
    save(ROOT / 'three-views.json', {'rows': rows, 'legal_approval': False, 'not_learning_scores': True})

if __name__ == '__main__':
    ap = argparse.ArgumentParser();ap.add_argument('action', choices=['prepare','freeze','import','run']);ap.add_argument('--case');ap.add_argument('--role', choices=['proposal','review']);a = ap.parse_args()
    if a.action == 'prepare': print(json.dumps(prepare_batch()))
    elif a.action == 'freeze': freeze()
    elif a.action == 'import': import_reply(a.case, a.role)
    else: run_batch()
