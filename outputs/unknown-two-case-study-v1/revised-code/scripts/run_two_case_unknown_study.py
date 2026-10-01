"""One bounded diagnostic rerun; no web requests, extraction or new samples."""
import copy,json,sys
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read,write_new,digest
from legal_bench.type_projection import apply_type_projections,REVIEW_KIND,SCOPE
from legal_bench.typed_relations import execute
OLD=Path('outputs/new-10-pattern-matching-v1')
OUT=Path('outputs/unknown-two-case-study-v1')
if (OUT/'status-complete-v1.json').exists():
    print('Completed diagnostic rerun retained; no new run.');sys.exit(0)
old_result=read(OLD/'runs/first-run/results.json');sample=read(OLD/'sample.json')['cases']
shared=[r for c in sample if c['case_id']!='1982777' for r in old_result['rows'] if r['case_id']==c['case_id'] and r['A']['status']==r['B']['status']=='UNKNOWN']
second=shared[0];assert second['case_id']=='500624'
selection={'case1':{'case_id':'1982777','task_id':'9c74983b08ed3850'},'case2':{'case_id':second['case_id'],'task_id':second['task_id']},'rule':'Case 1 fixed by user; case 2 first different case in saved sample order with A/B UNKNOWN, first task in saved task order. No replacement.','new_semantic_cases':2,'web_tasks':0}
write_new(OUT/'selection.json',selection)
# Only these six type fields are source reviewed. No inference from a label alone.
def item(cid,eid,sid,quote,rationale):
    view=read(OLD/'views'/f'{cid}.json');src=read(OLD/'sources'/f'{cid}.json');e=next(e for e in view['events'] if e['id']==eid)
    return {'case_id':cid,'event_id':eid,'view_hash':digest(view),'source_hash':digest(src),'review_kind':REVIEW_KIND,'scope':SCOPE,'field':'type','value':e['type'],'source_support':True,'rationale':rationale,'evidence':[{'segment_id':sid,'quote':quote}]}
reviews=[
 item('1982777','a3','p0001.s002','According to the respondents, the appellants had defaulted in payment of rent for a period running over three years since 29.11.1952.','The signed allegation concerns rent payment/default. The period is stated, but the fixed individual-event language cannot represent it fully. This type judgement does not assert positive payment, one event, exact dates or occurrence outside the interval.'),
 item('1982777','a6','p0001.s003','the appellants having incurred liability for eviction on the ground of default in payment of rent as alleged by the respondents.','The adopted assertion concerns rent default, so its coarse signed type remains PAY_RENT. Court treatment, polarity and the interval are retained; no individual payment or current truth is certified.'),
 item('500624','a4','p0001.s002','certain heirs, being co-owner landlords','The phrase explicitly concerns partial ownership, not an eviction filing or other proceeding. Exact owners and shares remain blocked; whole ownership and narrated status are not certified.'),
 item('500624','a5','p0001.s002','It is the case of the appellants that they have taken assignment of the rights of certain heirs, being co-owner landlords, on 29.12.1988.','The assertion is about an assignment of partial rights. Its coarse TRANSFER_TITLE type is supported; the allegation is not promoted to an adopted finding and the transferor/share restrictions remain.'),
 item('500624','a11','p0001.s003','seeking eviction of the appellants on grounds of non payment of rent','The embedded allegation is about rent non-payment. It is not itself a procedural filing atom. This certifies only PAY_RENT as the signed type; amount, period, polarity and occurrence remain subject to the old contract.'),
 item('500624','a14','p0010.s002','Here in this case, the lessee has acquired only the rights of certain co- owner landlords','The assertion concerns acquisition of partial rights, hence the coarse TRANSFER_TITLE type. It does not establish transfer of the entire building or resolve the transferor set, shares or date.')]
write_new(OUT/'type-only-source-reviews.json',{'reviews':reviews,'semantic_scope':'Only the two selected cases and six implicated wildcard records; local model judgements, not gold labels. No other original field changed.'})
write_new(OUT/'run-config.json',{'saved_at':datetime.now(timezone.utc).isoformat(),'parent_result_hash':digest(old_result),'tasks_hash':digest(read(OLD/'tasks.json')),'old_freeze_hash':digest(read(OLD/'freeze.json')),'review_hash':digest(reviews),'single_repair':'Explicit source-reviewed type-only projection, retaining all other blocks','source_and_fact_files_unchanged':True,'A_reused':True,'sample_count':10,'question_count':30,'mode':'SAME_SAMPLE_DIAGNOSTIC_NOT_NEW_TEST','no_new_web_tasks':True})
rows=[];changes=[];traces=[]
for case in sample:
 cid=case['case_id'];before=read(OLD/'views'/f'{cid}.json');source=read(OLD/'sources'/f'{cid}.json');registry=read(OLD/'relations'/f'{cid}.json')
 view=apply_type_projections(before,source,[r for r in reviews if r['case_id']==cid])
 if cid in ['1982777','500624']:write_new(OUT/'projected-views'/f'{cid}.json',view)
 for oldrow in (r for r in old_result['rows'] if r['case_id']==cid):
  q=oldrow['query'];co=copy.deepcopy(q);co['constraints']=[c for c in co['constraints'] if c['op'] not in ['part_of','member_of']]
  newrow=dict(copy.deepcopy(oldrow),B=execute(view,registry,q),cooccurrence=execute(view,registry,co));rows.append(newrow)
  for method in ['B','cooccurrence']:
   if oldrow[method]['status']!=newrow[method]['status']:
    changes.append({'case_id':cid,'task_id':oldrow['task_id'],'method':method,'before':oldrow[method]['status'],'after':newrow[method]['status'],'before_unknown_combinations':len(oldrow[method]['uncertain_bindings']),'after_unknown_combinations':len(newrow[method]['uncertain_bindings'])})
  chosen=selection['case1'] if cid=='1982777' else selection['case2'] if cid=='500624' else None
  if chosen and oldrow['task_id']==chosen['task_id']:
   selected_pairs=[{'e0':'a3','e1':'a6'}] if cid=='1982777' else [{'e0':'a10','e1':'a11'},{'e0':'a10','e1':'a8'},{'e0':'a10','e1':'a9'}]
   examples=[]
   for binding in selected_pairs:
    before_tr=[{'category':key,'trace':t} for key in ['witnesses','uncertain_bindings','rejected_bindings'] for t in oldrow['B'][key] if t['binding']==binding]
    after_tr=[{'category':key,'trace':t} for key in ['witnesses','uncertain_bindings','rejected_bindings'] for t in newrow['B'][key] if t['binding']==binding]
    examples.append({'binding':binding,'before':before_tr,'after':after_tr,'after_no_candidate':not bool(after_tr)})
   traces.append({'case_id':cid,'task_id':chosen['task_id'],'query':q,'A':oldrow['A'],'before_counts':{k:len(oldrow['B'][k]) for k in ['witnesses','uncertain_bindings','rejected_bindings']},'after_counts':{k:len(newrow['B'][k]) for k in ['witnesses','uncertain_bindings','rejected_bindings']},'key_traces':examples})
write_new(OUT/'case-traces.json',{'cases':traces,'trace_keys':'case/task/event binding; original full traces remain in parent results.json'})
write_new(OUT/'results.json',{'rows':rows,'changes':changes,'diagnostic_only':True,'parent_result_hash':digest(old_result),'accuracy':None})
summary={'before':read(OLD/'runs/first-run/summary.json')['overall_status_counts'],'after':{m:dict(Counter(r[m]['status'] for r in rows)) for m in ['A','B','cooccurrence']},'changes':changes,'unreviewed_cases_unchanged':all(r[m]==o[m] for r,o in zip(rows,old_result['rows']) if r['case_id'] not in ['1982777','500624'] for m in ['A','B','cooccurrence']),'A_all_unchanged':all(r['A']==o['A'] for r,o in zip(rows,old_result['rows'])),'source_reference':'LOCAL_MODEL_SOURCE_REVIEW_NOT_HUMAN_GOLD','accuracy':None}
assert summary['unreviewed_cases_unchanged'] and summary['A_all_unchanged']
write_new(OUT/'summary.json',summary)
write_new(OUT/'status-complete-v1.json',{'completed_at':datetime.now(timezone.utc).isoformat(),'cases_studied':['1982777','500624'],'type_fields_reviewed':6,'uniform_repairs':1,'local_reruns':1,'existing_cases_recomputed':10,'existing_questions_recomputed':30,'web_tasks':0,'independent_new_test':False,'stopped':True})
print(json.dumps(summary,ensure_ascii=False))
