#!/usr/bin/env python3
"""Prepare, verify and import bounded analysis tasks without UI/network/model execution."""
import argparse,datetime,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.analysis_prompt_study04 import ADDITION,sha,treatment,order_cases,parse_raw
S=Path('outputs/legal-rule-support-study-02');D=Path('outputs/legal-rule-support-diagnostic-03');R=Path('outputs/legal-analysis-study-04')
def read(p):return json.loads(p.read_text())
def write(p,v):
 if p.exists():raise FileExistsError(p)
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def text(p,v):
 if p.exists():raise FileExistsError(p)
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(v)
def verify():
 f=read(R/'freeze.json')
 for p,h in f['files'].items():
  if sha(Path(p).read_bytes())!=h:raise ValueError('Frozen file changed '+p)
 return {'status':'FROZEN_FILES_OK','count':len(f['files'])}
def prepare():
 if (R/'freeze.json').exists():return verify()
 runs=read(S/'run-order.json');samples=read(S/'samples.json');seed=20261004
 order=order_cases([x['case_id'] for x in samples],seed);checks=[];filepaths=[]
 text(R/'generic-analysis-addition.txt',ADDITION);text(R/'execution-wrapper.txt',(S/'execution-wrapper.txt').read_text())
 for item in order:
  old=next(x for x in runs if x['case_id']==item['case_id'] and x['replicate']==0 and 'A' in x['arms'])
  base=(S/old['prompt_path']).read_text();actual=read(S/'runs'/old['id']/'submission.json');assert base==actual['submitted_text']
  task=base if item['arm']=='CONTROL' else treatment(base)
  if item['arm']=='TREATMENT':assert task.replace(ADDITION+'\n','',1)==base
  path=R/'tasks'/(item['id']+'.txt');text(path,task);item.update(task=str(path.relative_to(R)),task_sha256=sha(task),complete_submission_sha256=sha(task+'\n'+actual['wrapper']),old_A_run=old['id'],selected_ids=old['selected_ids'],legal_characters=old['legal_characters'],task_characters=len(task))
  checks.append({'id':item['id'],'case_id':item['case_id'],'arm':item['arm'],'old_A_task':str(S/old['prompt_path']),'base_hash':sha(base),'input_delta':'NONE' if item['arm']=='CONTROL' else 'EXACT_SHARED_ADDITION_ONLY','case_and_law_text_order_unchanged':True,'retrieval_unchanged':True})
  filepaths.extend([path,S/old['prompt_path'],S/'sources'/(item['case_id']+'-allowed.json')])
 # Evaluation anchors are separate from submitted tasks, copied from the prior bounded diagnostic.
 write(R/'evaluation'/'existing-error-anchors.json',read(D/'error-attribution.json'))
 write(R/'evaluation'/'existing-review-qualifications.json',read(S/'final-source-review.json'))
 extra={'case_id':'890045','prior_review':'outputs/legal-rule-support-study-02/runs/EVAL04/copied-answer.json','source_ids':[x['id'] for x in read(S/'sources/890045-allowed.json')['segments']],'meaning':'Do not count more uncertainty as improvement; preserved assignment/contract words and honest legal interpretation limits matter.'}
 write(R/'evaluation'/'coverage-case.json',extra)
 rules={'role':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD','review_passes':1,'reviewer':'Main session source comparison; no additional reviewer agent','extra_web_review_calls_planned':0,'axes':['speaker/proposition/court-stage fidelity','material opposing reasons not merely more points','rule premises scope and real gaps','new unsupported claims contradictions or omissions'],'categories':['NET_IMPROVEMENT','CLOSE_OR_MIXED','WORSE','NOT_COMPARABLE'],'separate_source_gaps_from_use_failure':True,'outcome_label_not_accuracy':True,'do_not_require_historical_outcome':True,'do_not_force_unknown_when_prior_findings_support_condition':True,'neutral_labels_before_review':True,'not_fully_blind':'instruction style may expose treatment','fixed_existing_anchors':'evaluation/existing-error-anchors.json','do_not_transmit_anchors_to_tested_model':True,'new_errors_recorded_without_repairs':True,'failed_answer_null_not_UNKNOWN':True,'no_six_case_accuracy_rank':True}
 write(R/'evaluation-rules.json',rules)
 rng=__import__('random').Random(seed+1);mapping={}
 for s in samples:
  pair=[x for x in order if x['case_id']==s['case_id']];rng.shuffle(pair);mapping[s['case_id']]={'N1':pair[0]['id'],'N2':pair[1]['id']}
 write(R/'evaluation'/'hidden-condition-mapping.json',mapping)
 write(R/'run-order.json',order);write(R/'task-checks.json',checks)
 cfg={'version':'ANALYSIS_STUDY_04','seed':seed,'cases':[s['case_id'] for s in samples],'calls':{'final_max':12,'extra_review_max':1,'planned_extra_review':0,'total_max':13,'model_calls_started':0},'requested_profile':{'provider':'ChatGPT Web','mode':'ordinary High','Pro':False,'paid_API':False,'exact_model':None,'current_UI_profile_observed':False},'comparison':'Original study02 A input/control vs exact same input plus uniform analysis organization','no_search_or_material_change':True,'case_role':'ERROR_EXPOSED_DEVELOPMENT_VALIDATION','per_task':'fresh independent dialogue, once, full attachment preview match','failure':'No semantic retry; raw preserved; format-only wrapper handling; null on technical failure; environment obstruction stops dependent calls','resume':'verify frozen files; inspect run metadata and conversation URL; reuse submitted/completed tasks, continue only unsubmitted order entries','stopping_rule':'After12answers and at most1concentratedreview, stop regardless outcomes; no prompt tuning or next experiment','no_commit_no_push':True}
 write(R/'config.json',cfg)
 write(R/'run-state.json',{'status':'NOT_STARTED_ACCESS_BLOCKED','answer_count':0,'model_calls':0,'rows':[{'id':x['id'],'status':'NOT_STARTED_ACCESS_BLOCKED','answer':None,'conversation_url':None} for x in order]})
 code=[Path('scripts/study04_analysis.py'),Path('legal_bench/rules_verdict_v1/analysis_prompt_study04.py'),Path('legal_bench/rules_verdict_v1/rule_retrieval_v21.py')]
 frozen=filepaths+code+list((R/'evaluation').glob('*.json'))+[R/x for x in ['generic-analysis-addition.txt','execution-wrapper.txt','run-order.json','task-checks.json','evaluation-rules.json','config.json']]
 write(R/'freeze.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':{str(p):sha(p.read_bytes()) for p in frozen},'before_model_calls':True,'visible_current_model_not_assumed':True})
 return {'prepared':12,**verify()}
def import_reply(task_id,raw_path,metadata_path):
 verify();row=next(x for x in read(R/'run-order.json') if x['id']==task_id);dest=R/'runs'/task_id
 if (dest/'result.json').exists():return {'status':'ALREADY_IMPORTED_NO_OVERWRITE','id':task_id}
 meta=read(Path(metadata_path))
 for k in ['conversation_url','visible_model','visible_mode','submitted_utc','observed_complete_utc','submitted_task_sha256']:
  if k not in meta:raise ValueError('Missing actual UI record '+k)
 if meta['submitted_task_sha256']!=row['task_sha256']:raise ValueError('Actual input mismatch')
 raw=Path(raw_path).read_text();view=read(S/'sources'/(row['case_id']+'-allowed.json'));result=parse_raw(raw,[x['id'] for x in view['segments']],row['selected_ids']);text(dest/'raw.txt',raw);write(dest/'run.json',meta);write(dest/'result.json',result)
 return {'id':task_id,'run_status':result['run_status']}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','verify','import']);p.add_argument('--id');p.add_argument('--raw');p.add_argument('--metadata');a=p.parse_args()
 print(json.dumps(import_reply(a.id,a.raw,a.metadata) if a.command=='import' else prepare() if a.command=='prepare' else verify(),ensure_ascii=False,indent=2))
