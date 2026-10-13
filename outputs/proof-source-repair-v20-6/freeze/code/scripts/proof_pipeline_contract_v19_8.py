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
from legal_bench.proof_carrying import local_pipeline_v19_8 as pipe,local_checker_v19_8 as checker
from legal_bench.proof_carrying.schema_contract_v19_6 import loads,violations
from legal_bench.proof_carrying.local_schedule_v19 import run as schedule
from legal_bench.proof_carrying.rule_contracts_v19_8 import attach,digest,validate_rules
OUT=ROOT/'outputs/proof-pipeline-diagnostic-repair-v19-8'
OLD=ROOT/'outputs/proof-together-contract-v19-6'
BASE=ROOT/'outputs/proof-local-pipeline-v19/continuation-04'

def context(task):
    f=read(BASE/'preparation/inputs'/task['case_id']/'fixture.json')
    f['full_rules']=f['rules']
    part=task['part_contract']
    selected=[r for r in f['rules'] if r['id'] in part['rule_ids']]
    f['rules']=attach(selected,read(ROOT/'outputs/proof-pipeline-contract-v19-7/contracts'/ (task['case_id']+'.json')))
    return f,part

def _process_saved(case, rules, part, raw_text, original_schema, version, technical_status):
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


def process_saved(case,rules,part,raw_text,original_schema,version,technical_status):
    """Durable processing boundary, also used by real cached acceptance."""
    try:
        validation=validate_rules(rules)
        result=_process_saved(case,rules,part,raw_text,original_schema,version,technical_status)
        result['processing_version']=pipe.VERSION;result['rule_contract_validation']=validation
        result['source_review_acceptance']='NOT_REVIEWED_BY_THIS_ENTRY'
        result['conditional_semantics']='UNVERIFIED_MODEL_ASSUMPTIONS'
        return result
    except (KeyError,TypeError,ValueError,IndexError,RuntimeError) as exc:
        return {'processing_version':pipe.VERSION,'production_version':version,'technical_status':technical_status,
                'raw_sha256':hashlib.sha256(raw_text.encode()).hexdigest(),'formal_answer':None,
                'contract_status':'PROCESSING_ERROR','entry_error':type(exc).__name__+':'+str(exc),
                'conditional_audit':None,'reference_used':False,'semantic_approval':False,'legal_approval':False}


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



def final_run(*args, **kwargs):
    from legal_bench.proof_carrying.final_delivery_v19_8 import run
    return run(*args, **kwargs)
