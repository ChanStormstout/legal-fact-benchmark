#!/usr/bin/env python3
"""V19_7 actual acceptance, dependency, learning-input and final-answer entry.
No CLI starts extra generations or training. Transport calls this same entry.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.proof_together_diagnostic import read,save,sha,utc
from scripts.proof_contract_integrity_v19_6 import text
from legal_bench.proof_carrying import local_pipeline_v19_7 as pipe,local_checker_v19_7 as checker
from legal_bench.proof_carrying.schema_contract_v19_6 import loads,violations
from legal_bench.proof_carrying.local_schedule_v19 import run as schedule
from legal_bench.proof_carrying.rule_contracts_v19_7 import attach,digest
OUT=ROOT/'outputs/proof-pipeline-contract-v19-7'
OLD=ROOT/'outputs/proof-together-contract-v19-6'
BASE=ROOT/'outputs/proof-local-pipeline-v19/continuation-04'

def context(task):
    f=read(BASE/'preparation/inputs'/task['case_id']/'fixture.json')
    f['full_rules']=f['rules']
    part=task['part_contract']
    selected=[r for r in f['rules'] if r['id'] in part['rule_ids']]
    f['rules']=attach(selected,read(OUT/'contracts'/ (task['case_id']+'.json')))
    return f,part

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
        converted, ledger = pipe.convert(raw, view, version, selected)
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        return {**result, 'formal_answer': None, 'contract_status': 'IMPORT_INTERFACE_ERROR',
                'audit_role': 'READABLE_TEXT_INVALID_INTERFACE_NOT_FORMAL_SUCCESS',
                'entry_error': type(exc).__name__ + ':' + str(exc), 'conditional_audit': None}
    imported = checker.check_import(raw, converted, view, version, selected)
    result['independent_import'] = imported
    if imported['status'] != 'OK':
        result['formal_answer'] = None; result['contract_status'] = 'IMPORT_REJECTED'; return result
    merged, merge_ledger = pipe.merge_parts([(part['id'], converted)])
    merged_check = checker.check_merge([(part['id'], converted)], merged)
    result['independent_merge'] = merged_check
    if merged_check['status'] != 'OK':
        result['formal_answer'] = None; result['contract_status'] = 'MERGE_REJECTED'; return result
    audit = pipe.apply_connection_decisions(case, selected, merged)
    independent = checker.check(case, selected, merged, None, audit)
    result.update(conversion_ledger=ledger, merge_ledger=merge_ledger, canonical_P=merged,
                  conditional_audit=audit, independent_check=independent,
                  learner_inputs=pipe.learner_inputs(case, selected, merged))
    if independent['status'] != 'OK': result['formal_answer'] = None; result['contract_status'] = 'CHECK_REJECTED'
    result['generation_complete'] = technical_status == 'OK'
    result['analysis_coverage_complete'] = result['coverage']['status'] == 'ANALYSIS_REPORTED'
    roles = {p['id']: set(p['input_contract']['required_roles']) for r in selected for p in r['premises']}
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


def final_run(case,rules,entry,method,dest,perform,prediction=None,full_rules=None):
    """Complete final preparation, saved runner, acceptance and audit boundary.
    perform may be an authorized runner; tests use an explicit mock, not a model.
    """
    dest=Path(dest)
    task=pipe.final_task(case,rules,entry,method,prediction,full_rules)
    save(dest/'task.json',task);text(dest/'prompt.txt',task['prompt']);save(dest/'schema.json',task['schema'])
    if (dest/'formal-answer.json').exists():return read(dest/'formal-answer.json')
    if (dest/'start.json').exists():raise ValueError('UNKNOWN_SUBMISSION_STATE_NO_RESEND')
    save(dest/'start.json',{'version':pipe.VERSION,'started_at':utc(),'input_sha256':task['input_sha256']})
    try:
        raw,receipt=perform(task)
        text(dest/'raw-response.txt',raw);save(dest/'run.json',receipt)
        result=pipe.accept_final(task,raw,receipt['run_status'])
    except Exception as exc:
        receipt={'run_status':'TECHNICAL_FAILURE','error':type(exc).__name__+':'+str(exc)}
        save(dest/'failure.json',receipt)
        result=pipe.accept_final(task,'','TECHNICAL_FAILURE')
    save(dest/'formal-answer.json',result)
    return result


def replay():
    rows=[]
    for task in read(OLD/'freeze/protocol.json')['tasks']:
        f,part=context(task);d=OLD/'runs'/task['case_id']/task['part']
        result=process_saved(f['case'],f['rules'],part,(d/'raw-response.txt').read_text(),read(d/'schema.json'),'V19_6',read(d/'run.json')['run_status'])
        save(OUT/'replay'/task['case_id']/'entry.json',result)
        rows.append({'case_id':task['case_id'],'generation_version':'V19_6_UNMODIFIED_CACHE','processing_version':pipe.VERSION,
                     'contract':result['contract_status'],'formal_present':result['formal_answer'] is not None,
                     'coverage':result['coverage'],'states':[x['conditional_state'] for x in (result.get('conditional_audit') or {}).get('premise_judgments',[])],
                     'old_model_semantics_not_backfilled':True})
    save(OUT/'cache-replay-summary.json',rows)
    print(json.dumps(rows,ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['replay'])
    globals()[parser.parse_args().phase]()
