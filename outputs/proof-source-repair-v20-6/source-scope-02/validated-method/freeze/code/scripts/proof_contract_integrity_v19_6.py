#!/usr/bin/env python3
"""Joint entry for cached import, coverage, audit and input preparation.

No generate/train/web command: current experiment remains paused. A later
authorized run must use the V19_6 runner and this same ingestion path.
"""
import argparse
import copy
import datetime
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from legal_bench.proof_carrying import local_pipeline_v19_6 as pipe
from legal_bench.proof_carrying import local_checker_v19_6 as checker
from legal_bench.proof_carrying.schema_contract_v19_6 import loads, violations
from legal_bench.proof_carrying.local_schedule_v19 import run as schedule

OUT = ROOT / 'outputs/proof-contract-integrity-v19-6'
BASE = ROOT / 'outputs/proof-local-pipeline-v19/continuation-04'
API = ROOT / 'outputs/proof-together-diagnostic-v1/transport-02'


def read(path): return json.loads(Path(path).read_text())
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
    if path.exists() and path.read_text() != text: raise ValueError('IMMUTABLE_RECORD_MISMATCH:' + str(path))
    if not path.exists(): path.write_text(text)
def text(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() != value: raise ValueError('IMMUTABLE_TEXT_MISMATCH:' + str(path))
    if not path.exists(): path.write_text(value)


def process_saved(case, rules, part, raw_text, original_schema, version, technical_status):
    """Used by replay and the actual saved-output acceptance boundary.

Readable contract failures retain an explicitly qualitative audit; formal answer
is null. Dynamic reference defects remain per-use failures, not global deletion.
"""
    selected = [r for r in rules if r['id'] in part['rule_ids']]
    view = {**case, 'segments': [s for s in case['segments'] if s['id'] in part['source_ids']]}
    result = {'production_version': version, 'technical_status': technical_status, 'formal_answer': None,
              'raw_sha256': hashlib.sha256(raw_text.encode()).hexdigest(), 'semantic_approval': False,
              'legal_approval': False, 'reference_used': False}
    try: raw = loads(raw_text)
    except (ValueError, TypeError) as e:
        return {**result, 'contract_status': 'UNREADABLE_JSON', 'parse_error': str(e), 'coverage': None,
                'conditional_audit': None, 'not_repaired_or_guessed': True}
    errors = violations(raw, original_schema)
    result.update(schema_violations=errors, contract_status='CONTRACT_REJECTED' if errors else 'CONTRACT_VALID')
    analyses = raw.get('analyses') if isinstance(raw, dict) else None
    if not isinstance(analyses, (list, dict)):
        return {**result, 'coverage': None, 'conditional_audit': None,
                'audit_role': 'READABLE_TEXT_INVALID_INTERFACE_NOT_FORMAL_SUCCESS'}
    result['coverage'] = pipe.coverage(raw, selected)
    shape_errors = {'MISSING_REQUIRED_FIELD', 'OBJECT_TYPE', 'ARRAY_TYPE', 'STRING_TYPE', 'INTEGER_TYPE', 'BOOLEAN_TYPE'}
    if any(e['reason'] in shape_errors for e in errors):
        return {**result, 'conditional_audit': None, 'audit_role': 'READABLE_TEXT_INVALID_INTERFACE_NOT_FORMAL_SUCCESS'}
    if not errors and technical_status == 'OK': result['formal_answer'] = raw
    result['audit_role'] = 'ACCEPTED_TRANSPORT_UNVERIFIED_SEMANTICS' if result['formal_answer'] is not None else 'QUALITATIVE_ONLY_NOT_FORMAL_SUCCESS'
    try:
        converted, ledger = pipe.convert(raw, view, version)
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        return {**result, 'formal_answer': None, 'contract_status': 'IMPORT_INTERFACE_ERROR',
                'audit_role': 'READABLE_TEXT_INVALID_INTERFACE_NOT_FORMAL_SUCCESS',
                'entry_error': type(exc).__name__ + ':' + str(exc), 'conditional_audit': None}
    imported = checker.check_import(raw, converted, view, version)
    result['independent_import'] = imported
    if imported['status'] != 'OK':
        result['formal_answer'] = None; result['contract_status'] = 'IMPORT_REJECTED'; return result
    merged, merge_ledger = pipe.merge_parts([(part['id'], converted)])
    audit = pipe.apply_connection_decisions(case, selected, merged)
    independent = checker.check(case, selected, merged, None, audit)
    result.update(conversion_ledger=ledger, merge_ledger=merge_ledger, canonical_P=merged,
                  conditional_audit=audit, independent_check=independent,
                  learner_inputs=pipe.learner_inputs(case, selected, merged))
    if independent['status'] != 'OK': result['formal_answer'] = None; result['contract_status'] = 'CHECK_REJECTED'
    result['generation_complete'] = technical_status == 'OK'
    result['analysis_coverage_complete'] = result['coverage']['status'] == 'ANALYSIS_REPORTED'
    roles = {p['id']: set(p.get('variables', {})) for r in selected for p in r['premises']}
    result['role_coverage'] = []
    for unit in converted['analyses']:
        for i, j in enumerate(unit['judgments']):
            mapped = {b['address'].split('::')[-1] for b in j['bindings'] if type(b['object']) is int and 0 < b['object'] <= len(unit['objects'])}
            result['role_coverage'].append({'premise': unit['premise'], 'judgment': i + 1,
                 'required_roles': sorted(roles.get(unit['premise'], set())), 'mapped_existing_roles': sorted(mapped),
                 'missing_roles': sorted(roles.get(unit['premise'], set()) - mapped),
                 'evidence_objects_saved': len(unit['objects']), 'no_automatic_judgment_binding': True})
    return result


def assemble(records):
    """Transport completion, coverage and semantics are different fields."""
    transport = 'ALL_GENERATIONS_ENDED' if records and all(r['technical_status'] == 'OK' for r in records) else 'PARTIAL_OR_FAILED_GENERATION'
    successful = [r for r in records if r.get('formal_answer') is not None]
    coverage = 'ANALYSIS_REPORTED' if records and len(successful) == len(records) and all(r.get('analysis_coverage_complete') for r in records) else 'PARTIAL_ANALYSIS'
    return {'transport_status': transport, 'contract_successful_parts': len(successful), 'planned_parts': len(records),
            'analysis_coverage_status': coverage, 'semantic_status': 'NOT_INDEPENDENTLY_VERIFIED',
            'empty_is_not_complete': True, 'legal_approval': False}


def accept_saved_output(case, rules, part, dest):
    """The same validation/import path is invoked after a saved runner result."""
    dest = Path(dest); meta = read(dest / 'run.json')
    result = process_saved(case, rules, part, (dest / 'raw-response.txt').read_text(),
                           read(dest / 'schema.json'), pipe.VERSION, meta['run_status'])
    save(dest / 'formal-answer.json', {'answer': result['formal_answer'], 'technical_status': meta['run_status'],
                                     'contract_status': result['contract_status']})
    save(dest / 'entry-audit.json', result)
    return result


def saved_batch(root, slots, perform):
    """Reuse the existing safe boundary; no batch is launched by this CLI."""
    return schedule(root, slots, perform)


def inventory():
    cfg = read(BASE / 'freeze/protocol.json'); slots = cfg['local_generation_slots']; tasks = []
    for p in sorted((BASE / 'local').glob('*/P*/run.json')):
        if p.parent.name == 'P': continue
        cid, part_id = p.parent.parent.name, p.parent.name
        slot = next(s for s in slots if s['case_id'] == cid and s.get('part', {}).get('id') == part_id)
        tasks.append({'origin': 'local_saved', 'case_id': cid, 'part': slot['part'], 'directory': str(p.parent.relative_to(ROOT)),
                      'version': read(p.parent / 'production-version.json')['version']})
    for t in read(API / 'freeze/protocol.json')['tasks']:
        slot = next(s for s in slots if s['case_id'] == t['case_id'] and s.get('part', {}).get('id') == t['part'])
        tasks.append({'origin': 'api_saved', 'case_id': t['case_id'], 'part': slot['part'],
                      'directory': str((API / 'runs' / t['case_id'] / t['part']).relative_to(ROOT)),
                      'schema_path': str((API / t['task'] / 'schema.json').relative_to(ROOT)), 'version': 'V19_5'})
    return tasks


def prepare():
    reg = read(ROOT / 'docs/repository-artifacts.json')
    assert str(OUT.relative_to(ROOT)) in reg['artifact_roots']
    if (OUT / 'startup/inventory.json').exists(): return
    tasks = inventory(); preserved = {}
    for task in tasks:
        d = ROOT / task['directory']
        for p in sorted(d.glob('*')):
            if p.is_file() and p.name in ('run.json', 'raw-response.txt', 'parsed.json', 'schema.json', 'prompt.txt', 'production-version.json', 'token-ids.json'):
                preserved[str(p.relative_to(ROOT))] = sha(p)
        f = BASE / 'preparation/inputs' / task['case_id'] / 'fixture.json'; preserved[str(f.relative_to(ROOT))] = sha(f)
        if task.get('schema_path'): preserved[task['schema_path']] = sha(ROOT / task['schema_path'])
    save(OUT / 'startup/inventory.json', tasks)
    save(OUT / 'startup/preserved-hashes.json', preserved)
    save(OUT / 'startup/workspace.json', {'HEAD': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
       'dirty_files': subprocess.check_output(['git', 'status', '--short'], text=True).splitlines(),
       'scope': 'CURRENT_V19_SAVED_LOCAL_PARTS_AND_TWO_TOGETHER_OUTPUTS_ONLY', 'generation_calls': 0, 'fits': 0})
    save(OUT / 'PAUSE_REQUESTED.json', {'reason': 'USER_AUTHORIZED_CONTRACT_REPAIR_ONLY_NO_NEW_GENERATION'})
    prepared = []
    for task in [t for t in tasks if t['origin'] == 'api_saved']:
        f = read(BASE / 'preparation/inputs' / task['case_id'] / 'fixture.json'); part = task['part']
        selected = [r for r in f['rules'] if r['id'] in part['rule_ids']]
        view = {**f['case'], 'segments': [s for s in f['case']['segments'] if s['id'] in part['source_ids']]}
        dest = OUT / 'prepared' / task['case_id'] / part['id']
        text(dest / 'prompt.txt', pipe.proposal_prompt(f['case'], f['rules'], part)); save(dest / 'schema.json', pipe.schema(selected, view))
        save(dest / 'source-directory.json', pipe.source_directory(view))
        prepared.append({'case_id': task['case_id'], 'part': part['id'], 'source_count': len(view['segments']),
                         'expected_premises': [p['id'] for r in selected for p in r['premises']],
                         'characters': len((dest / 'prompt.txt').read_text()), 'prompt_hash': sha(dest / 'prompt.txt'),
                         'schema_hash': sha(dest / 'schema.json'), 'source_bytes_unchanged': True})
    save(OUT / 'preparation-summary.json', prepared)


def replay():
    rows = []
    for task in read(OUT / 'startup/inventory.json'):
        d = ROOT / task['directory']; f = read(BASE / 'preparation/inputs' / task['case_id'] / 'fixture.json')
        meta = read(d / 'run.json'); sc = read(ROOT / task['schema_path'] if task.get('schema_path') else d / 'schema.json')
        result = process_saved(f['case'], f['rules'], task['part'], (d / 'raw-response.txt').read_text(), sc, task['version'], meta['run_status'])
        save(OUT / 'replay-final' / task['origin'] / task['case_id'] / task['part']['id'] / 'entry-result.json', result)
        audit = result.get('conditional_audit') or {}
        rows.append({**task, 'technical_status': meta['run_status'], 'contract_status': result['contract_status'],
                     'formal_answer_present': result.get('formal_answer') is not None,
                     'schema_violation_reasons': dict(Counter(x['reason'] for x in result.get('schema_violations', []))),
                     'coverage': result.get('coverage'), 'audit_role': result.get('audit_role'),
                     'independent_import': result.get('independent_import'), 'independent_check_status': result.get('independent_check', {}).get('status'),
                     'records_retained': audit.get('raw_records_retained'),
                     'uses': dict(Counter(x['disposition'] for x in audit.get('checks', []))),
                     'premise_states': dict(Counter(x['conditional_state'] for x in audit.get('premise_judgments', []))),
                     'OPEN_TEXT_rules': sum(bool(x.get('not_executed')) for x in audit.get('conditional_rules', [])),
                     'missing_role_judgments': sum(bool(x['missing_roles']) for x in result.get('role_coverage', []))})
    save(OUT / 'replay-final-summary.json', rows)
    print(json.dumps({'replayed': len(rows), 'formal_parts': sum(x['formal_answer_present'] for x in rows),
                      'contract_states': dict(Counter(x['contract_status'] for x in rows))}, ensure_ascii=False))


def freeze():
    gate = read(OUT / 'engineering-acceptance.json')
    assert gate['status'] == 'PASS'
    preserved = read(OUT / 'startup/preserved-hashes.json')
    assert all(sha(ROOT / p) == h for p, h in preserved.items())
    old = read(BASE / 'freeze/protocol.json'); files = set(old['code_hashes']) | set(read(OUT / 'startup/new-code-files.json'))
    hashes = {f: sha(ROOT / f) for f in sorted(files)}
    for name in hashes: text(OUT / 'freeze/code' / name, (ROOT / name).read_text())
    save(OUT / 'freeze/protocol.json', {'version': pipe.VERSION, 'frozen_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'HEAD': read(OUT / 'startup/workspace.json')['HEAD'], 'code_hashes': hashes,
        'prepared': read(OUT / 'preparation-summary.json'), 'preserved_original_count': len(preserved),
        'replay_summary_hash': sha(OUT / 'replay-final-summary.json'), 'engineering_acceptance_hash': sha(OUT / 'engineering-acceptance.json'),
        'runtime_settings_unchanged': old['runtime_settings'], 'new_generation_authorized': False,
        'training_authorized': False, 'new_cases': 0, 'new_sources': 0, 'TEST_SEALED_read': False,
        'contract_changes': ['Inline source aliases', 'Fixed analysis keys', 'Premise-specific role maps', 'Single-anchor witnesses',
                             'Full emitted-schema validation', 'Unique string-array decoder', 'Second-copy reference guard',
                             'Coverage separate from generation status', 'Independent transport count checks'],
        'old_outputs_not_upgraded_to_V19_6_generation': True, 'formal_approval': 'NOT_GRANTED', 'no_commit_or_push': True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('phase', choices=['prepare', 'replay', 'freeze'])
    args = parser.parse_args(); globals()[args.phase]()
