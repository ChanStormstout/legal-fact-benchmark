"""Validate and freeze blind results, then and only then open target sources."""
import sys,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.irac_gate_v2 import validate_blind_binding
from irac02_prepare import R,OLD,IDS,rd,put,sha,task
inp=rd(R/'blind-binding-input-freeze-address-v2.json');assert inp['rule_condition_freeze']==sha(R/'rule-condition-freeze-address-v2.json')
assert inp['stage_partition_freeze']==sha(R/'stage-partition-freeze.json')
binding_files={f'B-{n}':next(p for p in [R/'web'/f'B-{n}.raw.json',R/'web'/f'B-{n}.skipped.json'] if p.exists()) for n in range(1,5)}
raw={c['case_id']:c for p in binding_files.values() for c in rd(p)['cases']}
for cid in IDS:
 assert inp['input_hashes'][cid]==sha(R/'blind-binding-tasks-address-v2'/f'{cid}.json')
 st=rd(R/'stage-partition'/f'{cid}.json');rule=rd(R/'rule-package-address-v2'/f'{cid}.json');rs={x['record_id']:x for x in st['records']};sg={k[7:]:v for k,v in rs.items() if k.startswith('source:')};fg={k[6:]:v for k,v in rs.items() if k.startswith('facts:')};facts={f['id']:f for f in st['admitted_inventory']['facts']};cs={c['condition_id']:c for c in rule['conditions']}
 accepted=[];rejected=[];ids=set()
 for b in raw[cid]['bindings']:
  errors=validate_blind_binding(b,facts,cs,sg,fg)
  if not rule['rule_complete']:errors.append('RULE_INCOMPLETE_BINDING_NOT_ALLOWED')
  if b['binding_id'] in ids:errors.append('DUPLICATE_BINDING_ID')
  ids.add(b['binding_id'])
  (rejected if errors else accepted).append({'binding':b,'errors':errors} if errors else b)
 put('blind-bindings/'+cid+'.json',{'case_id':cid,'raw_proposal':raw[cid],'bindings':accepted,'rejected_bindings':rejected,'target_aware_binding_used':False,'target_not_read_for_generation':True,'input_sha256':inp['input_hashes'][cid],'candidate_not_court_adoption':True,'skipped':not rule['rule_complete']})
put('blind-binding-freeze.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'rule_condition_freeze':sha(R/'rule-condition-freeze-address-v2.json'),'stage_partition_freeze':sha(R/'stage-partition-freeze.json'),'input_freeze':sha(R/'blind-binding-input-freeze-address-v2.json'),'bindings':{c:sha(R/'blind-bindings'/f'{c}.json') for c in IDS},'raw_or_explicit_skips':{k:{'path':str(p),'sha256':sha(p)} for k,p in binding_files.items()},'task_prompts':inp['prompt_hashes'],'targets_not_opened_before_this_freeze':True})
# Supervision construction is physically separate; old target-aware proposals never input.
cases=[]
for cid in IDS:
 old=rd(OLD/'target-construction'/f'{cid}.json');put('target-construction/'+cid+'.json',{'case_id':cid,'full_historical_source':old['full_historical_source'],'old_source_sha256':sha(OLD/'target-construction'/f'{cid}.json'),'blind_freeze_sha256':sha(R/'blind-binding-freeze.json'),'supervision_only':True})
 inp=rd(OLD/'inputs'/f'{cid}.json');rule=rd(R/'rule-package-address-v2'/f'{cid}.json');cases.append({'case_id':cid,'fixed_issue':inp['fixed_issue'],'procedure_scope':inp['stage'],'frozen_conditions':rule['conditions'],'independent_rules':rule['rules'],'rule_complete':rule['rule_complete'],'target_source':old['full_historical_source']})
for j in range(2):
 task('T-'+str(j+1),'''SUPERVISION-ONLY retrospective Application target reconstruction, after blind binding output freeze. Use frozen conditions and supplied full target historical narrative. No external search, new facts, complete legal answer, or Rule changes. Return downloadable JSON {cases:[{case_id,application_targets:[{condition_id,label,basis_kind,source_refs,exact_quote,reason,target_finding_level,uncertainty}],issue_target:{label,source_refs,exact_quote,reason,procedural_limit},target_passage_stage:[{source_id,semantic_stage,reason}],gaps:[string]}]}. Exactly one row per supplied condition even when source does not independently decide it: label SATISFIED/DEFEATED/UNRESOLVED; basis_kind FACT_ACCEPTED/FACT_FALSE/BURDEN_NOT_CARRIED/NOT_DECIDED/INSUFFICIENT_RECORD/LEGAL_INTERPRETATION/AMBIGUOUS_REASONING. Target finding must explicitly distinguish actual target court application from lower findings/reported arguments. Issue label SUPPORTED/NOT_SUPPORTED/UNRESOLVED separately; no issue disposition→all elements propagation. Procedural restoration/remand or Article227 limitation does not prove every substantive condition; rejecting a sole legal contention is not a de novo fact finding of every element. Missing proof or burden failure is NOT factual falsehood. Unknown/undecided fields remain unresolved with precise reason. A retained-control/absence-of-written-consent condition may have negative legal consequence; labels evaluate exact condition proposition, not general victory. Cite exact supplied source IDs and exact short quotation; whitespace-only locator, no invented words. For no direct target basis source_refs may be empty, quote empty, NOT_DECIDED/INSUFFICIENT_RECORD. Enumerate semantic stage for target passages used, respecting allowed earlier court findings versus target reasoning/disposition. Rule incomplete remains GAP even if history shows outcome; do not reverse-engineer missing law. Do not see blind bindings or prior labels in this task.''',cases[j*4:j*4+4])
print('Blind results frozen; supervision source opened and target tasks prepared')
