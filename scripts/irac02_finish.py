"""Aggregate bounded review without altering proposals, facts or frozen results."""
from irac02_prepare import R,OLD,IDS,rd,put,sha,integrity
from collections import Counter
from pathlib import Path
import csv,datetime,json
reviews={c['case_id']:c for n in [1,2] for c in rd(R/'web'/f'F-{n}.raw.json')['cases']}
put('final-source-review.json',{'cases':[reviews[c] for c in IDS],'systemic_blockers':[b for n in [1,2] for b in rd(R/'web'/f'F-{n}.raw.json').get('systemic_blockers',[])],'reference_role':'MODEL_ASSISTED_INDEPENDENT_SOURCE_REVIEW_NOT_HUMAN_GOLD','semantic_retry':0,'raw_review_hashes':{f'F-{n}':sha(R/'web'/f'F-{n}.raw.json') for n in [1,2]}})
rows=[];comparison=[];audits=[]
expected={'Issue','Rule','Conditions','Stage_partition','Input_facts','Blind_bindings','Application_targets','Issue_target','Leakage','Logical_consistency'}
for cid in IDS:
 rev=reviews[cid];rule=rd(R/'rule-package-address-v2'/f'{cid}.json');st=rd(R/'stage-partition'/f'{cid}.json');b=rd(R/'blind-bindings'/f'{cid}.json');t=rd(R/'targets'/f'{cid}.json');records=st['records'];ds={d['dimension']:d for d in rev['dimensions']};extra=[]
 if set(ds)!=expected:extra.append('FINAL_REVIEW_DIMENSION_COVERAGE_INCOMPLETE')
 if not rule['rule_complete'] or not rev.get('rule_complete',False):extra.append('DECISIVE_RULE_INCOMPLETE')
 if not t['condition_coverage_complete']:extra.append('TARGET_CONDITION_COVERAGE_INCOMPLETE')
 loc=[z for z in t['locator_checks'] if z['errors']]
 if loc:extra.append('TARGET_SOURCE_LOCATOR_OR_REFERENCE_GAP')
 if any(d['status']=='BLOCKING_GAP' for d in ds.values()):extra.append('FINAL_SOURCE_REVIEW_BLOCKING_GAP')
 final=rev['recommended_status']
 if extra:final='GAP'
 retained=st['admitted_inventory'];rawfacts=rd(OLD/'inputs'/f'{cid}.json')['existing_inventory']['facts'];fm={f['id']:f for f in rawfacts};unmodified=all(f==fm[f['id']] for f in retained['facts'])
 assert unmodified
 prior=[x for x in records if x['semantic_stage']=='PRIOR_COURT_FINDING' and x['record_id'].startswith('facts:')];priorids={x['record_id'][6:] for x in prior};priorretained=[f for f in retained['facts'] if f['id'] in priorids]
 forbidden=[x['record_id'] for x in records if x['semantic_stage'] in ['TARGET_COURT_REASONING','TARGET_DISPOSITION']]
 admitted_ids={'facts:'+f['id'] for f in retained['facts']}|{'relations:'+f['id'] for f in retained['relations']}|{'objects:'+f['id'] for f in retained['objects']}|{'source:'+f['id'] for f in retained['sources']}
 illegal=[x['record_id'] for x in records if x['record_id'] in admitted_ids and not x['input_allowed']]
 assert not illegal
 row={'case_id':cid,'rule_complete':bool(rule['rule_complete'] and rev.get('rule_complete',False)),'frozen_rule_complete':rule['rule_complete'],'decisive_tests_count':rule['decisive_tests_count'],'added_decisive_tests_count':rule['added_decisive_tests_count'],'conditions_count':len(rule['conditions']),'stage_partition_clean':not illegal and ds.get('Stage_partition',{}).get('status')!='BLOCKING_GAP','forbidden_target_records':len(forbidden),'prior_findings_preserved':len(priorretained),'prior_findings_mixed_source_excluded':len(prior)-len(priorretained),'input_facts_count':len(retained['facts']),'input_relations_count':len(retained['relations']),'blind_bindings_count':len(b['bindings']),'blind_bindings_rejected':len(b['rejected_bindings']),'target_aware_binding_used':False,'application_targets_count':len(t['proposal']['application_targets']),'issue_target':t['proposal']['issue_target']['label'],'leakage_status':rev['leakage_status'],'prospective_availability_limit':'RETROSPECTIVELY_RECONSTRUCTED_PRE_TARGET_NO_PROSPECTIVE_CLAIM','final_status':final,'blocking_reason':rev.get('blocking_reason',[]) + extra if isinstance(rev.get('blocking_reason',[]),list) else [rev.get('blocking_reason','')]+extra,'qualification':rev.get('qualification',[])};rows.append(row)
 # This legacy reading occurs only after all new blind outputs have frozen.
 old=rd(OLD/'web'/f'P-{cid}.raw.json');oldbindings=old.get('bindings',[])
 comparison.append({'case_id':cid,'old_binding_origin':'POST_AWARE_NOT_INPUT','old_count':len(oldbindings),'new_input_only_count':len(b['bindings']),'new_rejected_count':len(b['rejected_bindings']),'old_bindings':oldbindings,'new_bindings':b['bindings'],'comparison_limit':'Conditions changed; count differences are not precision/recall. Review meaningful links, preserved status and excluded target evidence.','source_review_meaningful':rev.get('blind_bindings_meaningful')})
 audits.append({'case_id':cid,'forbidden_records_quarantined':forbidden,'ambiguous_count':sum(x['semantic_stage']=='AMBIGUOUS' for x in records),'all_types_reviewed':True,'admitted_forbidden_records':illegal,'source_gate_exclusions':st['source_gate_exclusions'],'raw_graph_gate_audit':st['graph_gate_audit'],'facts_original_values_preserved':unmodified,'prior_finding_count':len(prior),'prior_retained_ids':[f['id'] for f in priorretained],'prior_excluded_ids':sorted(priorids-{f['id'] for f in priorretained}),'blind_task_sha256':sha(R/'blind-binding-tasks-address-v2'/f'{cid}.json'),'target_used_only_after_blind_freeze':True,'final_leakage_review':ds.get('Leakage')})
put('feasibility-table.json',rows)
p=R/'feasibility-table.csv';assert not p.exists()
with p.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows)
put('blind-vs-postaware-comparison.json',comparison);put('leakage-audit.json',{'cases':audits,'target_feature_gate':'Frozen input-only API; no target or oracle selection fields accepted','test_result':rd(R/'engineering-checks.json'),'blind_freeze_sha256':sha(R/'blind-binding-freeze.json')})
counts=Counter(r['final_status'] for r in rows);system=rd(R/'final-source-review.json')['systemic_blockers'];n=counts['READY_FOR_RETROSPECTIVE_APPLICATION_TRAINING'];limited_engineering_only=all(not any(x in str(r['blocking_reason']) for x in ['DECISIVE_RULE_INCOMPLETE','FINAL_SOURCE_REVIEW_BLOCKING_GAP']) for r in rows if r['final_status']!='READY_FOR_RETROSPECTIVE_APPLICATION_TRAINING')
decision='GO' if n>=6 and not system else 'CONDITIONAL_GO' if n in [4,5] and not system and limited_engineering_only else 'NO_GO'
put('readiness.json',{'IRAC_DATA_READINESS':decision,'GROUP_CANONICAL_ADAPTER_STATUS':rd(R/'real-canonical-adapter-audit.json')['status'],'case_status_counts':dict(counts),'ready_case_ids':[r['case_id'] for r in rows if r['final_status']=='READY_FOR_RETROSPECTIVE_APPLICATION_TRAINING'],'systemic_blockers':system,'remaining_gap_only_limited_engineering':limited_engineering_only,'conditions_rule_complete_cases':sum(r['rule_complete'] for r in rows),'no_training':True,'sealed_not_opened':True,'reference_role':'MODEL_ASSISTED_NOT_HUMAN_GOLD','prospective_prediction_supported':False,'next_training_not_authorized':True})
runs=[rd(p) for p in sorted((R/'web').glob('*.run.json'))];calls=sum(r.get('submission_count',1) for r in runs)
put('cost.json',{'ordinary_High_calls':calls,'calls_max':16,'runs':runs,'exact_model':None,'visible_mode':'High','technical_generation_failures':0,'technical_retries':0,'semantic_retry':0,'model_training':0,'legal_answers':0,'local_LLM_calls':0,'paid_API_calls':0,'token_counts':None,'cost_limit':'Wall time from submission/download includes polling, UI and concurrent tasks; not exact generation latency. Visible thinking times are observations only.','transport_anomalies':['S-1 showed transient network interruption but completed original task without resubmission','S-2 download event wait timed out in UI tool; downloaded file present and copied intact, no generation retry']})
assert calls<=16
end=integrity();assert end['all_unchanged'];put('parent-integrity-end.json',end)
put('completion.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'all_eight_included':True,'calls':calls,'stopped_after_bounded_round':True,'no_commit_no_push':True,'immutable_rules_and_blind_freezes_preserved':True})
print(json.dumps({'readiness':decision,'counts':dict(counts),'calls':calls,'rule_complete':sum(r['rule_complete'] for r in rows)},ensure_ascii=False,indent=2))
