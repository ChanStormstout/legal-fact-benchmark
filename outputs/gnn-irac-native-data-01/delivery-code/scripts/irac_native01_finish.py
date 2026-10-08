"""Close the bounded discovery round; never promotes screening to READY."""
import csv
import datetime
import hashlib
import json
from pathlib import Path
from scripts.irac_native01_prepare import ROOT, save, sha


def main():
    screening = json.loads((ROOT/'suitability-screening.json').read_text())
    cohort = json.loads((ROOT/'construction-cohort.json').read_text())
    if cohort['status'] != 'NOT_RUN_BELOW_SIX_ELIGIBLE':
        raise ValueError('This closure is only for a failed discovery gate.')
    stop = 'NOT_RUN_DISCOVERY_GATE_BELOW_SIX'
    for folder in ('independent-rule-sources', 'rule-packages', 'stage-partition',
                   'blind-binding-tasks', 'blind-bindings', 'inputs', 'targets',
                   'irac-input-graphs'):
        p = ROOT/folder/'STATUS.json'
        save(str(p.relative_to(ROOT)), {'status':stop,'real_cases':0,
             'reason':'Eligible screen count < 6; no construction permitted.'})
    for name in ('rule-condition-freeze', 'stage-freeze', 'blind-binding-freeze'):
        save(name+'.json', {'status':stop,'frozen_cases':[],
                           'no_completed_freeze_claim':True})
    save('final-source-review.json', {'status':stop, 'cases':[],
         'screening_is_not_final_construction_review':True,'model_calls':0})
    save('leakage-audit.json', {'status':'DISCOVERY_ONLY_NO_REAL_INPUTS',
         'discovery_target_access':True,'discovery_fields_not_model_features':True,
         'blind_tasks_created':0,'real_input_graphs':0,'sealed_body_read':False,
         'program_tests':'graph-builder-validation-final.json',
         'real_case_semantic_leakage_evaluation':'NOT_RUN'})
    save('referential-integrity-audit.json', {'status':'SYNTHETIC_INTERFACE_ONLY',
         'real_graphs':0,'synthetic_fixture_validated':True,
         'excluded_endpoint_cascade_tested':True,'real_cases_not_certified':True})
    rows = []
    for c in screening['cases']:
        rows.append({'case_id':c['case_id'],'screen_status':c['status'],
                     'model_acceptable_borderline':c['acceptable_borderline'],
                     'construction':stop,'readiness':'NOT_EVALUATED',
                     'reason':c['reason']})
    save('feasibility-table.json', {'cases':rows,'model_reference_not_human_gold':True})
    with (ROOT/'feasibility-table.csv').open('x', newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    save('readiness.json', {'IRAC_NATIVE_DATA_STATUS':'IRAC_NATIVE_DISCOVERY_NO_GO',
         'GROUP_CANONICAL_ADAPTER_STATUS':'NOT_AVAILABLE','candidate_count':16,
         'SUITABLE':1,'model_acceptable_BORDERLINE':3,'REJECT':12,
         'eligible_screen_upper_bound':4,'construction_minimum':6,
         'constructed_cases':0,'READY_FOR_GNN_IRAC_PILOT':0,
         'construction_readiness':'NOT_EVALUATED_DISCOVERY_GATE_STOP',
         'next_training_allowed':False,'next_training_protocol_generated':False,
         'boundary_candidates_not_scope_certified':True,'stopped':True})
    calls=[]
    for n in range(1,5):
        run=json.loads((ROOT/'web'/f'SCREEN-{n}.run.json').read_text())
        completed=json.loads((ROOT/'web'/f'SCREEN-{n}.completed.json').read_text())
        calls.append({'task_id':f'SCREEN-{n}','submission':run,'completion':completed,
                      'input_file_bytes':(ROOT/'tasks'/f'SCREEN-{n}.txt').stat().st_size,
                      'raw_reply_bytes':(ROOT/'web'/f'SCREEN-{n}.json').stat().st_size})
    save('cost.json', {'ordinary_High_calls':4,'max_authorized':16,'Pro':0,
         'local_model_calls':0,'paid_api_calls':0,'semantic_retries':0,
         'technical_retries':0,'training':0,'full_legal_answers':0,
         'exact_model':None,'exact_tokens':None,'exact_generation_seconds':None,
         'timing_note':'Submission and observed completion times are saved; visible thinking duration is not exact end-to-end generation time.',
         'calls':calls})
    historical=json.loads((ROOT/'parent-integrity.json').read_text())
    local=json.loads((ROOT/'historical-local-preservation.json').read_text())
    mismatch=[r['path'] for r in historical['files'] if sha(r['path'])!=r['sha256']]
    mismatch += [p for p,h in local.items() if sha(p)!=h]
    freeze=json.loads((ROOT/'screening-freeze.json').read_text())
    frozen_mismatch=[p for key in ('files','source_files') for p,h in freeze[key].items() if sha(p)!=h]
    if mismatch or frozen_mismatch:raise ValueError((mismatch,frozen_mismatch))
    save('preservation-after.json', {'parent_files':len(historical['files']),
         'local_historical_files':len(local),'historical_unchanged':True,
         'screening_freeze_unchanged':True,'mismatches':[]})
    code_paths=['legal_bench/rules_verdict_v1/irac_native_schema_v1.py',
                'legal_bench/rules_verdict_v1/irac_graph_builder_v1.py',
                'scripts/irac_native_graph.py','tests/test_irac_native_v1.py']
    save('delivery-code-hashes.json', {p:sha(p) for p in code_paths})
    save('stop.json', {'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'reason':'Fewer than six eligible even with all model-borderline cases counted.',
         'no_second_cohort':True,'no_training':True,'no_commit_no_push':True})


if __name__=='__main__':
    main()
