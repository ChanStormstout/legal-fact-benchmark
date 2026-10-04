#!/usr/bin/env python3
"""Read saved six-case evidence; deterministic replay of selection only, no model calls."""
import csv, hashlib, io, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1 import legal_rule_support_study as m
S=Path('outputs/legal-rule-support-study-02');R=Path('outputs/legal-rule-support-diagnostic-03')
def rd(p):return json.loads((S/p).read_text())
def save(p,v):
 path=R/p;path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():raise FileExistsError(path)
 path.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def ids(x):return [z['id'] for z in x]
u=rd('library/original-units.json');samples=rd('samples.json');runs=rd('run-order.json');wrapper=(S/'execution-wrapper.txt').read_text();rows=[]
for sample in samples:
 cid=sample['case_id'];d=rd('retrieval/'+cid+'/result.json');view=rd(sample['source']);arms={};prompts={}
 for arm in ['A','G','L']:
  selected=d['selected'][arm];ranking=d['rankings'][arm]
  replay=m.select(ranking,u,d['configuration'],selected['mandatory_ids']);assert replay==selected
  traversal=list(selected['mandatory_ids'])
  for step in selected['decisions']:
   if step['decision']=='SELECTED':
    for key in step['required_ids']:
     if key not in traversal:traversal.append(key)
  prompt=m.prompt(view,selected['units'],sample['question'],d['configuration']);run=next(x for x in runs if x['case_id']==cid and x['replicate']==0 and arm in x['arms']);submitted=rd('runs/'+run['id']+'/submission.json')
  assert prompt==submitted['submitted_text'] and wrapper==submitted['wrapper']
  prompts[arm]=prompt+'\n'+wrapper
  arms[arm]={'searched_index_units':14 if arm=='A' else {'raw':14,'description':10},'raw_ranking':ids(ranking if arm=='A' else d['route_traces'][arm]['raw']),'description_ranking':[] if arm=='A' else ids(d['route_traces'][arm]['description']),'fused_ranking':ids(ranking),'selected_source_order':selected['selected_ids'],'accepted_in_traversal_order':traversal,'budget_decisions':selected['decisions'],'legal_characters':selected['legal_characters'],'actual_task':run['prompt_path'],'actual_run':run['id'],'complete_submission_sha256':m.sha(prompts[arm]),'selection_replay_matches':True}
 pairs=[]
 for a,b in [('A','G'),('A','L'),('G','L')]:
  x,y=arms[a],arms[b];same_set=set(x['selected_source_order'])==set(y['selected_source_order']);same_rank=x['fused_ranking']==y['fused_ranking'];same_traversal=x['accepted_in_traversal_order']==y['accepted_in_traversal_order']
  pairs.append({'pair':a+'-'+b,'candidate_sets_same':set(x['fused_ranking'])==set(y['fused_ranking']),'ranking_same':same_rank,'selected_material_set_same':same_set,'acceptance_order_same':same_traversal,'final_display_order_same':x['selected_source_order']==y['selected_source_order'],'complete_submission_bytes_same':prompts[a]==prompts[b],'exclusive_candidates_left':sorted(set(x['fused_ranking'])-set(y['fused_ranking'])),'exclusive_candidates_right':sorted(set(y['fused_ranking'])-set(x['fused_ranking'])),'first_membership_difference_loss':'No membership difference at retrieval: all14 raw candidates' if same_set else 'Final budget sets remain different','ranking_difference_loss':('NONE_RANKS_IDENTICAL' if same_rank else 'ATOMIC_SELECTION' if same_traversal else 'FIXED_SOURCE_ORDER_RENDERING') if same_set else 'NOT_LOST_FINAL_INPUT_DIFFERENT'})
 row={'case_id':cid,'query':d['query'],'library_units':len(u),'full_library_payload_characters':len(m.render(u)),'budget':20000,'arms':arms,'pairs':pairs};save('traces/'+cid+'.json',row);rows.append(row)
summary=[]
for row in rows:
 for p in row['pairs']:summary.append({'case_id':row['case_id'],**p})
save('stage-comparison.json',summary)
b=io.StringIO();w=csv.DictWriter(b,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary);(R/'stage-comparison.csv').write_text(b.getvalue())
save('diagnosis.json',{'all_raw_candidates_14':all(len(x['arms']['A']['raw_ranking'])==14 for x in rows),'all_description_candidates_10':all(len(x['arms'][a]['description_ranking'])==10 for x in rows for a in ['G','L']),'all_fused_sets_equal_raw':all(set(x['arms']['A']['raw_ranking'])==set(x['arms'][a]['fused_ranking']) for x in rows for a in ['G','L']),'library_payload_chars':len(m.render(u)),'budget':20000,'paired_description_exclusions':rd('representations/paired-source-review.json'),'findings':['All raw14 units found: not an initial recall problem.','G/L rankings differ; dual-route RRF favors ten description-covered units over four raw-only units.','Atomic dependency budget removes many high-ranked large units. Fixed original-source display order erases remaining ordering differences.','No incorrect description-to-unit mapping found; all10 accepted descriptions unique and correspond to existing unit IDs.'],'replay_scope':'Existing stored rankings and deterministic select/prompt only; no new search/model run.'})
# Limited errors already identified in study02; keep exact allowed spans and actual uploaded positions.
errors=[('110204406','corporate_vesting_overstatement',['IK-110204406:L103','IK-110204406:L136'],['MODEL_USE_FAILURE','SOURCE_COVERAGE_GAP'],'Company vesting testimony does not fully establish tenancy-specific legal mechanism; original notification absent.'),('172908545','will_opposition_omission',['IK-172908545:L122','IK-172908545:L123','IK-172908545:L128','IK-172908545:L129','IK-172908545:L130','IK-172908545:L131'],['MODEL_USE_FAILURE','SOURCE_COVERAGE_GAP'],'The Will route and opposing arguments are delivered; directly governing substantive succession authorities absent from library.'),('58386394','mixed_respondent_positions',['IK-58386394:L108','IK-58386394:L112','IK-58386394:L113','IK-58386394:L114','IK-58386394:L115','IK-58386394:L116'],['MODEL_USE_FAILURE'],'Different respondents assert licences vs recognised subtenancies; no retrieval needed to preserve this distinction.'),('1908519','family_adoption_opposition_omission',['IK-1908519:L144','IK-1908519:L147','IK-1908519:L149','IK-1908519:L162@165:418','IK-1908519:L163'],['MODEL_USE_FAILURE','SOURCE_COVERAGE_GAP'],'Family/adoption counterargument and opposing prior decision delivered. Complete directly applicable possession/adoption authority absent; target counsel quotation is not the full opinion.'),('869439','consent_scope_and_counterargument',['IK-869439:L169','IK-869439:L171','IK-869439:L176','IK-869439:L177@0:232'],['MODEL_USE_FAILURE','SOURCE_COVERAGE_GAP','UNRESOLVED_INTERPRETATION'],'Argument about directory writing and express permission delivered; actual arrangement/date and prior reasoning absent. Using lower findings is not itself an error; definitive synthesis remains disputed.')]
evidence=[]
for cid,name,refs,causes,note in errors:
 view=rd('sources/'+cid+'-allowed.json');table={s['id']:s for s in view['segments']};spans=[]
 for ref in refs:
  seg=table[ref]
  for run in [x for x in runs if x['case_id']==cid and x['replicate']==0]:
   task=(S/run['prompt_path']).read_text();needle='['+ref+'] '+seg['text'];i=task.find(needle);assert i>=0
   spans.append({'source_id':ref,'source_words':seg['text'],'task':run['prompt_path'],'run':run['id'],'submitted_line':task[:i].count('\n')+1,'char_start':i,'char_end':i+len(needle),'utf8_byte_start':len(task[:i].encode()),'delivered_exact':True})
 evidence.append({'case_id':cid,'issue':name,'causes':causes,'note':note,'evidence':spans})
for row in rows:
 arm=row['arms']['A'];sec='LAW:S02:DRC:16';dec=next(x for x in arm['budget_decisions'] if x['id']==sec)
 evidence.append({'case_id':row['case_id'],'issue':'DRC16_delivery','causes':['MATERIAL_SELECTION_FAILURE_BUDGET'] if sec not in arm['selected_source_order'] else ['DELIVERED'],'unit':sec,'raw_rank':arm['raw_ranking'].index(sec)+1,'decision':dec,'note':'Existing reviewed legal reference, not inferred from word presence; source16 date and consent conditions remain to be applied.'})
save('error-attribution.json',evidence)
print('Six cases diagnosed; limited errors anchored; model calls0.')
