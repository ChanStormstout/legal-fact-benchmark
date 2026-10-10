#!/usr/bin/env python3
"""Output-only report assembly after V16's single concentrated source review."""
import json,hashlib,datetime as dt,csv
from collections import Counter
from pathlib import Path
from scripts.proof_source_alignment_v16 import ROOT,read,save,textsave,assert_frozen

def main():
 assert_frozen()
 observed=read(ROOT/'source-review-observations.json');rows=[];costs=[];summary=Counter();traces=[]
 for c in read(ROOT/'selection.json')['cases']:
  cid=c['case_id'];b=read(ROOT/'inputs'/cid/'bundle.json');zs={}
  for v in ['D','P','R']:
   folder=ROOT/'runs'/cid/(v+'-recovered' if (ROOT/'runs'/cid/(v+'-recovered')/'checked.json').exists() else v);fp=folder/'checked.json';zs[v]=read(fp) if fp.exists() else read(folder/'failure.json')
  imp=ROOT/'raw'/cid/'proposal/import-recovered.json'
  if not imp.exists():imp=ROOT/'raw'/cid/'proposal/import.json'
  proposal=read(imp)['answer'];rvp=ROOT/'raw'/cid/'review/import-recovered.json';rvp=rvp if rvp.exists() else ROOT/'raw'/cid/'review/import.json';rv=read(rvp)['answer'] if rvp.exists() else None
  checks=zs['R'].get('structure_checks',zs['P'].get('structure_checks',{}))
  row={'case_id':cid,'request_id':c['request_id'],'operators':c['effective_operators'],'D':zs['D']['requests'][0]['answer'],
       'P':zs['P']['requests'][0]['answer'] if 'requests' in zs['P'] else None,'R':zs['R']['requests'][0]['answer'] if 'requests' in zs['R'] else None,
       'technical_status':{'proposal':read(imp)['status'],'review':read(rvp)['status'] if rvp.exists() else 'SKIPPED_DEPENDENCY_FAILURE'},
       'slots':[],'formal_legal_approval':False,**observed['cases'][cid]}
  for d in b['directory']:
   ck=checks.get(d['address']);raw=next((a for a in (proposal or {}).get('alignments',[]) if a['address']==d['address']),None)
   row['slots'].append({'address':d['address'],'premise_id':d['premise_id'],'proposition':d['proposition'],'raw_model_state':(raw or {}).get('whole_premise',{}).get('state'),
    'structural_status':(ck or {}).get('structural_status'),'conditional_state':(ck or {}).get('conditional_state'),'independent_conditional_judgment':(ck or {}).get('independent_conditional_judgment'),
    'accepted_state':(ck or {}).get('accepted_state'),'accepted_independent_judgment':(ck or {}).get('accepted_independent_judgment'),'pending':(ck or {}).get('pending',[]),'review':(ck or {}).get('review')})
   if ck:
    summary['structure_'+ck['structural_status']]+=1;summary['conditional_'+ck['conditional_state']]+=1;summary['accepted_'+ck.get('accepted_state','UNKNOWN')]+=1
    for sr in ck.get('review',{}).get('scoped_records',[]):summary['review_'+sr['decision']]+=1
  rows.append(row)
  trace={'case':cid,'request':b['requests'][0],'source_order':b['source_order'],'directory':b['directory'],'source_map':b['snapshot']['sources'],
         'proposal':proposal,'review':rv,'checks':checks,'views':zs,'deterministic_repairs':b['deterministic_repairs'],'formal_legal_approval':False,'original_P_unchanged':True}
  save(ROOT/'paths'/cid/'trace.json',trace);traces.append({'case':cid,'path':str(ROOT/'paths'/cid/'trace.json')})
  for role in ['proposal','review']:
   rp=ROOT/'raw'/cid/role/'run.json'
   if not rp.exists():continue
   run=read(rp);recovery=rp.parent/'recovery-run.json';run={**run,**(read(recovery) if recovery.exists() else {})};tf=ROOT/'tasks'/cid/(role+'-task.txt');raw=rp.parent/'download-recovered.json';raw=raw if raw.exists() else rp.parent/'assistant.txt'
   start=run.get('submitted_at');end=run.get('completed_observed_at',run.get('observed_complete_at'));interval=None
   if start and end:interval=(dt.datetime.fromisoformat(end.replace('Z','+00:00'))-dt.datetime.fromisoformat(start.replace('Z','+00:00'))).total_seconds()
   costs.append({**run,'case_id':cid,'role':role,'task_file':str(tf),'task_bytes':tf.stat().st_size,'task_sha256':hashlib.sha256(tf.read_bytes()).hexdigest(),
                 'raw_bytes':raw.stat().st_size if raw.exists() else None,'raw_sha256':hashlib.sha256(raw.read_bytes()).hexdigest() if raw.exists() else None,
                 'observed_submit_to_capture_seconds':interval,'not_exact_generation_time':True,'input_tokens':None,'output_tokens':None})
 save(ROOT/'case-comparison.json',rows)
 save(ROOT/'three-views-final.json',{'rows':[{'case_id':r['case_id'],'views':read(ROOT/'paths'/r['case_id']/'trace.json')['views']} for r in rows],'initial_failure_views_retained':True,'formal_legal_approval':False})
 save(ROOT/'cost.json',{'web_calls':len(costs),'local_model_calls':0,'new_fits':0,'retries':0,'web_search':0,'model_visible':'GPT-6','mode_visible':'High',
      'exact_revision':None,'exact_tokens':None,'exact_generation_seconds':None,'task_bytes':sum(c['task_bytes'] for c in costs),'tasks':costs,'old_V12_fit_not_a_V16_fit':True})
 save(ROOT/'final-submission-manifest.json',{'actual_submissions':costs,'dynamic_reviews':read(ROOT/'review-task-assembly.json'),'failed_condition_not_removed':True})
 save(ROOT/'final-source-review.json',{'identity':'ONE_CONCENTRATED_MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD','after_all_tasks':True,'cases':rows,'counts':dict(summary),
      'same_case_addresses_not_independent_cases':True,'formal_legal_approval':False,'web_review_and_main_source_review_separate':True})
 with (ROOT/'comparison.csv').open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['case_id','request_id','D','P','R','finding','boundary','natural_problem']);w.writeheader()
  for r in rows:w.writerow({k:r[k] for k in w.fieldnames})
 md=['# V16 来源到限定推导的轨迹','','本轮六个固定请求的根规则均为OPEN_TEXT。前提连接及来源可审阅，开放法律解释未由程序执行。技术失败为null，UNKNOWN只用于真实保存的分析。正式法律批准缺失。','']
 for r in rows:
  cid=r['case_id'];md +=[f"## {cid} / {r['request_id']}",'',f"D={r['D']}，P={r['P']}，R={r['R']}。{r['finding']}",'',r['boundary'],'',r['natural_problem'],'',f'[完整来源与逐步记录](paths/{cid}/trace.json)','']
  for s in r['slots']:
   md +=[f"- {s['address']} / {s['premise_id']}：{s['proposition']}。原提议={s['raw_model_state']}；条件性执行前提={s['conditional_state']}；独立判断={s['independent_conditional_judgment']}；审阅后执行前提={s['accepted_state']}；审阅后独立判断={s['accepted_independent_judgment']}。阻碍：{', '.join(s['pending']) or ('未取得提议，结构检查不可评价' if s['raw_model_state'] is None else '无结构阻碍')}。"]
  md+=['']
 textsave(ROOT/'walkthrough.md','\n'.join(md))
 print(json.dumps({'counts':dict(summary),'web_calls':len(costs),'rows':[{'case':r['case_id'],'D':r['D'],'P':r['P'],'R':r['R']} for r in rows]},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
