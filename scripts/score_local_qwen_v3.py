"""Post-run scoring; preserves model claims, evidence errors and failures separately."""
import json,sys,copy
from pathlib import Path
from collections import Counter,defaultdict
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read,digest,canonical
from legal_bench.model_output import failure_answers
from scripts.local_qwen_experiment_v3 import ROOT,TASKS,write

def output(cid,m,role='runs'):
 p=ROOT/role/cid/m
 if not (p/'run.json').exists():
  run={'run_status':None,'answer_status':None,'operational_state':'NOT_STARTED','reason':'Paused or not yet run; not technical failure'}
  return {t['task_id']:dict(task_id=t['task_id'],**run) for t in TASKS()},run
 run=read(p/'run.json')
 if run['run_status']!='OK' or not (p/'answers.json').exists():return {r['task_id']:r for r in failure_answers(TASKS(),run['run_status'],run.get('error',run.get('reason','No parsed output')))},run
 return {r['task_id']:r for r in read(p/'answers.json')['answers']},run

def match_structure(answer,card,source):
 """Checks source location and supplied schema; never proves semantic support."""
 if answer.get('answer_status')!='MATCH':return {'valid':None,'errors':[]}
 errors=[];sm={s['id']:s['text'] for s in source['segments']};found=False
 def anchors(es):return isinstance(es,list) and bool(es) and all(e.get('quote') and e['quote'] in sm.get(e.get('segment_id'),'') for e in es)
 for binding in answer.get('bindings',[]):
  problems=[];atoms={a.get('var'):a for a in binding.get('atoms',[])};relation=binding.get('relation',{})
  for atom in card['query']['atoms']:
   a=atoms.get(atom['var'],{})
   if a.get('type')!=atom['type'] or a.get('status')!=atom['status'] or a.get('polarity')!='POSITIVE':problems.append('ATOM_TYPE_OR_STATE_INCORRECT')
   if not anchors(a.get('evidence')):problems.append('ATOM_EVIDENCE_MISSING_OR_UNLOCATED')
  con=next(c for c in card['query']['constraints'] if c['op'] in ['part_of','member_of'])
  for side in ['left','right']:
   v,_,role=con[side].split('.',2)
   if not atoms.get(v,{}).get('objects',{}).get(role):problems.append('REQUIRED_ROLE_BINDING_MISSING:'+side)
  if relation.get('op')!=con['op'] or not relation.get('left') or not relation.get('right'):problems.append('RELATION_ENDPOINT_OR_DIRECTION_MISSING')
  if not anchors(relation.get('evidence')):problems.append('RELATION_EVIDENCE_MISSING_OR_UNLOCATED')
  if not problems:found=True
  errors+=problems
 if not answer.get('bindings'):errors.append('NO_BINDING')
 return {'valid':found,'errors':sorted(set(errors)),'semantic_validity':'STRUCTURAL_CHECK_ONLY'}

def compare(ref,result,matchcheck):
 if result.get('operational_state')=='NOT_STARTED':return 'NOT_RUN'
 if result['run_status']!='OK':return 'TECHNICAL_FAILURE'
 status=result['answer_status'];expected=ref['answer']['answer_status']
 if status=='MATCH' and matchcheck.get('valid') is False:return 'CLAIMED_MATCH_INVALID_BINDING_OR_EVIDENCE'
 if expected=='MATCH':return {'MATCH':'MATCH_STATUS_CONSISTENT_SEMANTICS_PENDING','NOT_FOUND':'MISSED_MATCH','UNKNOWN':'MATCH_NOT_DECIDED'}[status]
 if expected=='NOT_FOUND':return {'MATCH':'FALSE_POSITIVE_RELATIVE_REFERENCE','NOT_FOUND':'NOT_FOUND_CONSISTENT','UNKNOWN':'UNNECESSARY_UNKNOWN_RELATIVE_REFERENCE'}[status]
 return {'MATCH':'OVERDETERMINED_MATCH_RELATIVE_REFERENCE','NOT_FOUND':'OVERDETERMINED_NOT_FOUND_RELATIVE_REFERENCE','UNKNOWN':'UNKNOWN_CONSISTENT'}[status]

def score():
 sample=read(ROOT/'evaluation-sample.json');rows=[];runs={}
 for ref in sample['rows']:
  cid=ref['case_id'];card=next(c for c in TASKS() if c['task_id']==ref['task_id']);source=read(ROOT/'sources'/(cid+'.json'))
  maps={}
  for m in ['A','B']:
   maps[m],run=output(cid,m);runs[cid+'/'+m]=run
  a=maps['A'][ref['task_id']];b=maps['B'][ref['task_id']]
  co=b.get('cooccurrence',dict(answer_status=None,run_status=b['run_status'],reason=b.get('reason','B no usable facts'),operational_state=b.get('operational_state')))
  check=match_structure(a,card,source)
  bc={'valid':True if b['answer_status']=='MATCH' else None,'semantic_validity':'EXECUTION_CHECK_ONLY_NOT_SOURCE_MEANING'}
  cc={'valid':True if co['answer_status']=='MATCH' else None,'semantic_validity':'COOCCURRENCE_DOES_NOT_CHECK_COMPLETE_TASK'}
  row={'case_id':cid,'task_id':ref['task_id'],'rank':ref['rank'],'reference':ref,'A':a,'B':b,'cooccurrence':co,'A_match_validation':check,'A_comparison':compare(ref,a,check),'B_comparison':compare(ref,b,bc),'cooccurrence_comparison':compare(ref,co,cc)}
  rows.append(row)
 summary={}
 for cls in ['MATCH','NOT_FOUND','UNKNOWN']:
  rs=[r for r in rows if r['reference']['answer']['answer_status']==cls]
  summary[cls]={'questions':len(rs),'methods':{m:{'run_status':dict(Counter(r[m]['run_status'] for r in rs)),'answer_status':dict(Counter(str(r[m]['answer_status']) for r in rs)),'comparison':dict(Counter(r[m+'_comparison'] for r in rs))} for m in ['A','B','cooccurrence']}}
 write(ROOT/'scoring/results-v1.json',{'rows':rows,'summary':summary,'question_count':len(rows),'actual_cases':len(sample['cases']),'interpretation':'Consistency against model source-reviewed references; not human-gold accuracy. Failures retained in all class denominators. MATCH also requires binding/evidence review.'})
 write(ROOT/'scoring/run-costs.json',{'runs':runs,'generation_passes':sum(r.get('run_status') is not None for r in runs.values()),'wall_seconds_sum':sum(r.get('elapsed_seconds',0) for r in runs.values()),'output_tokens_sum':sum(r.get('output_tokens',0) for r in runs.values()),'peak_mlx_memory_gb':max((r.get('peak_mlx_memory_gb',0) for r in runs.values()),default=0)})
 # Deterministic priority, one review per question, never enlarge sample.
 candidates=[]
 for r in rows:
  ref=r['reference']['answer']['answer_status'];statuses=[r[m]['answer_status'] for m in ['A','B']]
  priority=0 if any(st=='MATCH' for st in statuses) and (ref!='MATCH' or r['A_match_validation'].get('valid') is False) else 1 if ref=='MATCH' and any(st in ['NOT_FOUND','UNKNOWN'] for st in statuses) else 2 if ref=='NOT_FOUND' and 'UNKNOWN' in statuses else None
  if priority is not None:candidates.append((priority,r['rank'],r['task_id'],r))
 candidates.sort(key=lambda x:x[:3]);selected=[x[3] for x in candidates[:2]]
 write(ROOT/'scoring/review-selection.json',{'rule':'Priority unsupported claimed MATCH, missed MATCH, unnecessary UNKNOWN; then fixed case rank and task id. No technical-only failures substituted. Maximum2 new questions, one v1 source review already consumed from the total3 budget.', 'selected':[{'case_id':r['case_id'],'task_id':r['task_id']} for r in selected],'eligible':len(candidates),'results_hash':digest(rows)})
 print(json.dumps({'questions':len(rows),'cases':len(sample['cases']),'summary':summary,'review':[(r['case_id'],r['task_id']) for r in selected]},ensure_ascii=False))

if __name__=='__main__':score()
