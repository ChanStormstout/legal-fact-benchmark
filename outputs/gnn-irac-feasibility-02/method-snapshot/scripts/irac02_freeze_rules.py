"""Freeze source-reviewed rules and conditions BEFORE inference-only binding."""
import datetime,sys
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.irac_gate_v2 import validate_condition,inference_payload
from irac02_prepare import R,OLD,IDS,rd,put,sha,task
ps={c['case_id']:c for n in [1,2] for c in rd(R/'web'/f'P-{n}.raw.json')['cases']}
rs={c['case_id']:c for n in [1,2] for c in rd(R/'web'/f'R-{n}.raw.json')['cases']}
for cid in IDS:
 p=ps[cid];review=rs[cid];original=rd(R/'rule-candidates'/f'{cid}.json');rules={r['rule_id']:r for r in original['rules']};cr={c['condition_id']:c for c in p['conditions']};checks=[]
 for c in p['conditions']:
  errors=validate_condition(c,rules)
  allowed={c['rule_id']}|{a['id'] for a in rules.get(c['rule_id'],{}).get('source_document',{}).get('passage_addresses',[])}
  if not set(c.get('source_refs',[]))<=allowed:errors.append('CONDITION_SOURCE_OUTSIDE_RULE')
  if any(d.get('condition_id') not in cr for d in c.get('dependencies',[])):errors.append('UNKNOWN_DEPENDENCY')
  checks.append({'condition_id':c['condition_id'],'locator_and_reference_errors':errors})
 model_rules={r['rule_id']:r for r in p['rules']};rule_errors=[]
 for ident,r in rules.items():
  if ident not in model_rules or model_rules[ident]['exact_quote']!=r['exact_quote']:rule_errors.append(ident+':RULE_TEXT_NOT_PRESERVED')
 assert set(review['case_id'] for review in [review])=={cid}
 if {z['condition_id'] for z in review['condition_reviews']}!=set(cr):rule_errors.append('CONDITION_REVIEW_COVERAGE_INCOMPLETE')
 if {z['rule_id'] for z in review['rule_reviews']}!=set(rules):rule_errors.append('RULE_REVIEW_COVERAGE_INCOMPLETE')
 sem_block=[z for z in review['condition_reviews']+review['rule_reviews'] if z['status']=='BLOCKING_GAP']
 complete=bool(p['rule_complete'] and review['rule_complete'] and not rule_errors and not sem_block and not any(x['locator_and_reference_errors'] for x in checks))
 # Selection provenance is saved per Rule but stripped by inference_payload.
 for r in rules.values():r['oracle_selection_basis']=rd(R/'oracle-selection'/f'{cid}.json')
 # Original independent text preserved; decomposition proposals never semantically repaired.
 out={'case_id':cid,'rules':list(rules.values()),'conditions':p['conditions'],'rule_complete':complete,'decisive_tests_count':review.get('decisive_tests_count',p['decisive_tests_count']),'added_decisive_tests_count':rd(R/'oracle-selection'/f'{cid}.json')['added_decisive_tests_count'],'proposal':p,'independent_review':review,'program_checks':checks,'rule_errors':rule_errors,'oracle_selection_basis':rd(R/'oracle-selection'/f'{cid}.json'),'reference_role':'MODEL_GENERATED_AND_INDEPENDENTLY_SOURCE_REVIEWED_NOT_HUMAN_GOLD'};put('rule-package/'+cid+'.json',out)
freeze={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rules':{c:sha(R/'rule-package'/f'{c}.json') for c in IDS},'stage_freeze_sha256':sha(R/'stage-partition-freeze.json'),'independent_source_hashes':{str(p):sha(p) for p in sorted((R/'independent-sources').glob('*.json'))},'no_binding_yet':not (R/'blind-bindings').exists(),'no_change_after_binding':True};put('rule-condition-freeze.json',freeze)
# No target files, labels or old target-aware bindings are read in this path.
cases=[]
for cid in IDS:
 rule=rd(R/'rule-package'/f'{cid}.json');stage=rd(R/'stage-partition'/f'{cid}.json');x=rd(OLD/'inputs'/f'{cid}.json');inv=stage['admitted_inventory']
 payload=inference_payload(x['fixed_issue'],rule['rules'],rule['conditions'],inv['facts'],inv['relations'],inv['objects'],inv['sources'])
 grants={v['record_id']:v for v in stage['records']}
 payload['record_stage']=[{k:v for k,v in grants['facts:'+f['id']].items() if k!='reason'} for f in inv['facts']]
 item={'case_id':cid,'rule_complete':rule['rule_complete'],'input':payload if rule['rule_complete'] else None,'skip_reason':None if rule['rule_complete'] else 'RULE_CONDITION_BLOCKING_GAP_SKIP_BINDING'}
 put('blind-binding-tasks/'+cid+'.json',item);cases.append(item)
for j in range(4):
 instruction='''INFERENCE-ONLY BLIND Fact/Evidence to Condition candidate binding. No target reasoning, target outcome, reference answers, old bindings or review conclusions are supplied. Read only fixed issue, frozen independent rules/conditions and approved historical input records. No external search, new fact extraction or full legal answer. Return downloadable JSON {cases:[{case_id,bindings:[{binding_id,fact_id,condition_id,relation,reason,source_refs,statement_status,court_stage:{court,stage},uncertainty}],gaps:[string],skipped:boolean}]}. For rule_complete=false return skipped=true, empty bindings and the given skip reason; no repair. For eligible cases bindings only reference supplied existing fact IDs and condition IDs, relation SUPPORTS/DEFEATS/RELEVANT_TO. Preserve exact fact.status in statement_status and exact fact.court/fact.stage in court_stage; retain attribution, uncertainty and prior finding level. Binding.source_refs must be a nonempty subset of that fact.refs, not a law source or different fact. Candidate SUPPORTS does not mean court adoption or proved fact: a party allegation may propose relevant signed evidence with its status explicit; no inventing truth. UNKNOWN is never wildcard identity. Do not create fact, modify status, infer document contents from its existence, or infer facts from a legal test. Reason states the legal relationship briefly and uncertainty where evidence does not establish it. Distinguish negative condition polarity (absence of written landlord consent), alternatives and inference prerequisites; mere third-party presence cannot automatically prove legal divestment. May produce no binding. Never target labels; do not give issue verdict.'''
 task('B-'+str(j+1),instruction,cases[j*2:j*2+2]);(R/'blind-binding-tasks'/f'B-{j+1}.txt').write_bytes((R/'tasks'/f'B-{j+1}.txt').read_bytes())
put('blind-binding-input-freeze.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rule_condition_freeze':sha(R/'rule-condition-freeze.json'),'stage_partition_freeze':sha(R/'stage-partition-freeze.json'),'input_hashes':{c:sha(R/'blind-binding-tasks'/f'{c}.json') for c in IDS},'prompt_hashes':{f'B-{n}':sha(R/'tasks'/f'B-{n}.txt') for n in range(1,5)},'code_hashes':{p:sha(p) for p in ['legal_bench/rules_verdict_v1/irac_gate_v2.py','scripts/irac02_freeze_rules.py']}})
print('Rules/conditions frozen; eligible',sum(rd(R/'rule-package'/f'{c}.json')['rule_complete'] for c in IDS),'of8; blind tasks prepared')
