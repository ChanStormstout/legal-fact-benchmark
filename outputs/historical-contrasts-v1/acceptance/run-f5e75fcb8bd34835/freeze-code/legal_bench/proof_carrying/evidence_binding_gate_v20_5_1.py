"""Accept explicit optional absence without treating it as a reviewed identity.

Generation remains frozen V20.5. All nonempty bindings still require source
review. Required unknowns and erroneous optional bindings remain blocked.
"""
import json
from collections import Counter
from pathlib import Path
from . import evidence_binding_gate_v20_5 as previous
from . import shared_sources_v20_3 as shared
from .artifact_state_v20_2 import immutable

VERSION = 'V20_5_1_OPTIONAL_ABSENCE_GATE'


def audit(value, original_schema, case, rules, reviews=None):
    result = previous.audit(value, original_schema, case, rules, reviews)
    if result['status'] == 'REJECTED_FORMAT':
        return result
    optional = {}
    for rule in rules:
        for premise in rule['premises']:
            contract = premise.get('input_contract', {})
            optional[premise['id']] = (set(contract.get('optional_roles', []))
                - set(contract.get('required_roles', []))) & set(premise['variables'])
    for row in result['bindings']:
        path = row['path']
        if row['state'] == 'UNMAPPED_BINDING' and path[5] in optional.get(path[1], ()):
            row['state'] = 'OPTIONAL_UNMAPPED_PRESERVED'
    resolved = {'REVIEW_SUPPORTED', 'REVIEW_UNSUPPORTED', 'EXPLICIT_TYPE_CONFLICT',
                'OPTIONAL_UNMAPPED_PRESERVED'}
    pending = sum(row['state'] not in resolved for row in result['bindings'])
    rejected = sum(row['state'] == 'REVIEW_UNSUPPORTED' for row in result['bindings'])
    analyzed = sum(unit['analysis_status'] == 'ANALYZED'
                   for unit in shared.expand(value)['analyses'].values())
    result.update(version=VERSION, pending_bindings=pending, rejected_bindings=rejected,
        binding_state_counts=dict(Counter(row['state'] for row in result['bindings'])),
        optional_absence_is_source_review=False,
        status=('REJECTED_EVIDENCE_OR_BINDING' if result['errors'] else
                'NO_ANALYZED_UNITS' if not analyzed else
                'BINDING_REVIEW_REJECTED' if rejected else
                'BINDING_REVIEW_PENDING' if pending or result['review_errors'] else
                'READY_FOR_CONDITIONAL_PROCESSING'))
    return result


def process_saved(case, rules, part, compact, original_schema,
                  technical_status='OK', reviews=None):
    checked = audit(compact, original_schema, case, rules, reviews)
    result = {'version': VERSION, 'technical_status': technical_status,
              'contract_status': checked['status'], 'gate': checked,
              'formal_answer': None, 'conditional_audit': None,
              'automatic_computation_status': 'NOT_RUN_GATE_NOT_READY',
              'usability': {'checked_use_count': 0, 'status': 'NOT_COMPUTED_GATE_NOT_READY'},
              'semantic_approval': False, 'legal_approval': False}
    if technical_status != 'OK' or checked['status'] != 'READY_FOR_CONDITIONAL_PROCESSING':
        return result
    from scripts.proof_pipeline_contract_v19_8 import process_saved as original_entry
    raw = shared.expand(compact)
    entry = original_entry(case, rules, part,
        json.dumps(raw, ensure_ascii=False, separators=(',', ':')),
        original_schema, 'V19_8', technical_status)
    result.update(original_entry=entry, formal_answer=entry['formal_answer'],
        conditional_audit=entry.get('conditional_audit'), contract_status=entry['contract_status'],
        automatic_computation_status='PROCESSED_SOURCE_REVIEWED_MODEL_BINDINGS')
    uses = (entry.get('conditional_audit') or {}).get('checks', [])
    result['usability'] = {'checked_use_count': len(uses),
        'use_dispositions': dict(Counter(row['disposition'] for row in uses)),
        'analysis_coverage': entry.get('coverage'),
        'status': 'REPORTED_SEPARATELY_FROM_TRANSPORT'}
    return result


def accept_saved(input_dir, output_dir, case, rules, part, original_schema, reviews=None):
    source, destination = Path(input_dir).resolve(), Path(output_dir).resolve()
    if source == destination or source in destination.parents:
        raise ValueError('ACCEPTANCE_MUST_NOT_WRITE_INTO_GENERATION')
    run = json.loads((source/'run.json').read_text())
    if run.get('run_status') != 'OK':
        result = {'version': VERSION, 'technical_status': run.get('run_status'),
            'formal_answer': None, 'contract_status': 'GENERATION_FAILED',
            'conditional_audit': None, 'automatic_computation_status': 'NOT_RUN_GENERATION_FAILED'}
    else:
        result = process_saved(case, rules, part,
            json.loads((source/'parsed.json').read_text()), original_schema, 'OK', reviews)
    immutable(destination/'acceptance.json', result)
    immutable(destination/'formal-answer.json', {'answer': result['formal_answer'],
        'status': result['contract_status'], 'semantic_approval': False, 'legal_approval': False})
    return result
