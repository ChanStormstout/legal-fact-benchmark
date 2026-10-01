"""Versioned orchestration; references precede model testing, one case at a time."""
import argparse,copy,json,sys,subprocess,time,shutil,re
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read,digest
from legal_bench.model_output import parse_one,failure_answers
from scripts.local_qwen_worker import ROOT,SETTINGS,write,computed,scoreable_direct,prompt_for
TASKS=lambda:read(ROOT/'tasks.json')['tasks']
CODE=['legal_bench/field_pipeline_v2.py','legal_bench/model_output.py','legal_bench/fast_development.py','legal_bench/conditional_engine.py','legal_bench/type_projection.py','legal_bench/typed_relations.py','legal_bench/core.py','legal_bench/engine.py','scripts/local_qwen_worker.py','scripts/local_qwen_experiment.py','scripts/diagnose_declared_old10.py']

def freeze_method():
 if (ROOT/'freeze.json').exists():print('Existing freeze retained');return
 env=ROOT/'environment';model=Path((env/'model-path.txt').read_text().strip())
 for p in model.iterdir():
  if p.is_file() and p.suffix!='.safetensors':shutil.copyfile(p,env/p.name)
 versions=json.loads(subprocess.check_output([str(Path('.runtime/qwen35-v1/bin/python').absolute()),'-c','import importlib.metadata as m,json;print(json.dumps({k:m.version(k) for k in ["mlx-vlm","mlx","mlx-metal","transformers","huggingface_hub"]}))']))
 write(env/'versions.json',versions);write(ROOT/'config.json',SETTINGS)
 for p in CODE:
  f=ROOT/'method-snapshot'/p;f.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,f)
 (ROOT/'extraction-protocol.txt').write_text(prompt_for(read(ROOT/'development-sources/103193047.json'),'B').split('BEGIN_FULL_SOURCE')[0])
 (ROOT/'direct-protocol.txt').write_text(prompt_for(read(ROOT/'development-sources/103193047.json'),'A').split('BEGIN_FULL_SOURCE')[0])
 write(ROOT/'freeze.json',{'saved_at':datetime.now(timezone.utc).isoformat(),'before_new_model_test':True,'config_hash':digest(SETTINGS),'tasks_hash':digest(read(ROOT/'tasks.json')),'method_hashes':{p:digest(Path(p).read_bytes()) for p in CODE},'resource_case':'103193047','resource_results':{m:read(ROOT/'resource-check/103193047'/m/'run.json') for m in ['A','B']},'budget_decision':'Retain initial 32768 total, A2048/B8192. Actual development full prompts 7633/8462 tokens; output1277/1594 approximately, normal EOS and about6.9GB. JSON format errors retained; not a memory or incomplete-generation failure. Full 32768-token memory envelope not empirically proven. Syntax-only parser can drop trailing closing tokens after a complete root, never repair internal structure. No semantic prompt tuning from new evaluation.'})
 print('Method frozen')

def import_refs():
 rows=[];issues=[];caseorder={c['case_id']:i for i,c in enumerate(read(ROOT/'reference-reading-manifest.json')['cases'])}
 for folder in sorted((ROOT/'web-tasks').glob('reference-*')):
  path=folder/'raw-response.json'
  if not path.exists():continue
  data,repairs=parse_one(path.read_bytes());manifest=read(folder/'task.json');write(folder/'format-import.json',{'repairs':repairs,'raw_hash':digest(path.read_bytes())})
  if data.get('batch_id')!=manifest['batch_id']:raise ValueError('Wrong batch')
  if {c['case_id'] for c in data['cases']}!=set(manifest['case_ids']):raise ValueError('Wrong cases')
  for case in data['cases']:
   source=read(ROOT/'sources'/(case['case_id']+'.json'));sm={s['id']:s['text'] for s in source['segments']};objs={o['id']:o for o in case.get('objects',[])}
   for a in case['answers']:
    if a['task_id'] not in {t['task_id'] for t in TASKS()}:raise ValueError('Wrong task')
    errors=[]
    def walk(x):
     if isinstance(x,dict):
      if 'quote' in x and (not x.get('quote') or x['quote'] not in sm.get(x.get('segment_id'),'')):errors.append({'reason':'UNLOCATED_QUOTE','evidence':x})
      for v in x.values():walk(v)
     elif isinstance(x,list):
      for v in x:walk(v)
    walk(a);walk(case.get('main_unit',{}))
    if a.get('answer_status')=='MATCH':
     if not a.get('bindings'):errors.append({'reason':'MATCH_WITHOUT_BINDING'})
     card=next(t for t in TASKS() if t['task_id']==a['task_id'])
     valid_witness=False
     for b in a.get('bindings',[]):
      atoms={e.get('var'):e for e in b.get('atoms',[])};rel=b.get('relation',{});bindingok=True
      for needed in card['query']['atoms']:
       got=atoms.get(needed['var'],{})
       if any(got.get(k)!=needed.get(k,'POSITIVE' if k=='polarity' else None) for k in ['type','status','polarity']) or not got.get('evidence'):bindingok=False
      con=next(c for c in card['query']['constraints'] if c['op'] in ['part_of','member_of'])
      ends=[]
      for side in ['left','right']:
       var,_,role=con[side].split('.',2);ends.append(atoms.get(var,{}).get('roles',{}).get(role))
      if rel.get('op')!=con['op'] or [rel.get('left'),rel.get('right')]!=ends or not rel.get('evidence'):bindingok=False
      if any(x not in objs for x in ends) or ends[0]==ends[1]:bindingok=False
      elif con['op']=='part_of' and any(objs[x].get('kind')!='PROPERTY' for x in ends):bindingok=False
      elif con['op']=='member_of' and (objs[ends[0]].get('kind') not in ['PERSON','ORGANIZATION'] or objs[ends[1]].get('kind')!='GROUP'):bindingok=False
      if bindingok:valid_witness=True
     if not valid_witness:errors.append({'reason':'NO_COMPLETE_TYPED_EXACT_STATE_WITNESS'})
    if a.get('answer_status')=='UNKNOWN' and not a.get('missing_fields'):errors.append({'reason':'UNKNOWN_WITHOUT_DECISIVE_GAP'})
    if a.get('answer_status')=='NOT_FOUND' and not a.get('other_combinations_considered'):errors.append({'reason':'NOT_FOUND_WITHOUT_ALTERNATIVE_SCAN'})
    settled=a.get('reference_status')=='RESOLVED' and a.get('answer_status') in ['MATCH','NOT_FOUND','UNKNOWN'] and not errors
    r={'case_id':case['case_id'],'task_id':a['task_id'],'rank':caseorder[case['case_id']],'answer':a,'main_unit':case.get('main_unit'),'objects':case.get('objects',[]),'settled':settled,'automatic_errors':errors,'source_file':str(ROOT/'sources'/(case['case_id']+'.json')),'source_hash':digest(source),'batch_id':folder.name,'reference_kind':'MODEL_GENERATED_WITH_SOURCE_REVIEW_NOT_HUMAN_GOLD','semantic_validity':'MODEL_SOURCE_REVIEW_NOT_INDEPENDENT_HUMAN_VERIFICATION'}
    rows.append(r)
    if not settled:issues.append(r)
 rows.sort(key=lambda r:(r['rank'],r['task_id']));write(ROOT/'references/all-v1.json',{'rows':rows,'issues_count':len(issues)});write(ROOT/'references/unresolved-v1.json',{'rows':issues})
 expected=len(caseorder)*len(TASKS());seen=[(r['case_id'],r['task_id']) for r in rows]
 if len(seen)!=len(set(seen)) or len(seen)!=expected:raise ValueError('Incomplete references %d/%d'%(len(seen),expected))
 selected=[];coverage={}
 for t in TASKS():
  coverage[t['task_id']]={}
  for cls,n in [('MATCH',2),('NOT_FOUND',2),('UNKNOWN',1)]:
   pool=[r for r in rows if r['settled'] and r['task_id']==t['task_id'] and r['answer']['answer_status']==cls]
   selected+=pool[:n];coverage[t['task_id']][cls]={'available':len(pool),'selected':min(len(pool),n),'target':n}
 selected.sort(key=lambda r:(r['rank'],r['task_id']))
 write(ROOT/'evaluation-sample.json',{'rows':selected,'coverage':coverage,'cases':list(dict.fromkeys(r['case_id'] for r in selected)),'selection':'First source-confirmed references of each exact task/answer class in fixed reading order; selected before local outputs; no forced quotas','reading_cases':len(caseorder),'reference_hash':digest(rows),'new_dispute_independence_verified':False})
 write(ROOT/'evaluation-freeze.json',{'saved_at':datetime.now(timezone.utc).isoformat(),'before_new_model_test':True,'sample_hash':digest(read(ROOT/'evaluation-sample.json')),'reference_hash':digest(read(ROOT/'references/all-v1.json')),'method_freeze_hash':digest(read(ROOT/'freeze.json')),'posttest_review_limit':3,'review_order':'Unsupported claimed MATCH; missed reference MATCH; method UNKNOWN when source decisive. Fixed case/task order within priority.'})
 print({'coverage':coverage,'new_cases':len(read(ROOT/'evaluation-sample.json')['cases']),'new_questions':len(selected),'unresolved':len(issues)})

def functional_reimport():
 cid='103193047';source=read(ROOT/'development-sources'/(cid+'.json'));src=ROOT/'resource-check'/cid;out=ROOT/'functional'/cid;out.mkdir(parents=True,exist_ok=True)
 for method in ['A','B']:
  f=out/method;f.mkdir(exist_ok=True);raw=(src/method/'raw-response.txt').read_bytes();(f/'raw-response.txt').write_bytes(raw);meta=read(src/method/'run.json');meta['reuse']='Exact dev generation, same final model prompts/settings, syntax-only reimport; no new generation'
  try:
   data,repairs=parse_one(raw);write(f/'parsed.json',data);meta['format_repairs']=repairs
   if method=='A':rows=scoreable_direct(data,source)
   else:v,reg,rows=computed(data,source);write(f/'view.json',v);write(f/'relations.json',reg)
   write(f/'answers.json',{'case_id':cid,'answers':rows});meta['run_status']='OK';meta.pop('error',None)
  except (ValueError,KeyError,TypeError) as e:meta['run_status']='FORMAT_ERROR';meta['error']=str(e)
  write(f/'run.json',meta)
 write(out/'complete.json',{'reuse_resource_generation':True})

def run_model():
 freeze=read(ROOT/'freeze.json');assert all(digest(Path(p).read_bytes())==h for p,h in freeze['method_hashes'].items())
 functional_reimport();cases=[('OLD','444449')]+[('NEW',cid) for cid in read(ROOT/'evaluation-sample.json')['cases']]
 for role,cid in cases:
  out=ROOT/('functional' if role=='OLD' else 'runs')/cid
  if (out/'complete.json').exists():continue
  source=ROOT/('development-sources' if role=='OLD' else 'sources')/(cid+'.json');out.mkdir(parents=True,exist_ok=True)
  cmd=[str(Path('.runtime/qwen35-v1/bin/python').absolute()),'scripts/local_qwen_worker.py','--source',str(source),'--out',str(out),'--config',str(ROOT/'config.json')]
  t=time.perf_counter()
  with (out/'process.log').open('w') as log:
   try:
    p=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=2700)
    if p.returncode!=0:
     txt=(out/'process.log').read_text();status='OUT_OF_MEMORY' if ('out of memory' in txt.lower() or 'Metal' in txt and p.returncode<0) else 'UNSUPPORTED'
     for m in ['A','B']:
      if not (out/m/'run.json').exists():write(out/m/'run.json',{'run_status':status,'answer_status':None,'reason':'Worker exited '+str(p.returncode),'elapsed_seconds':time.perf_counter()-t})
     write(out/'complete.json',{'failure':status})
   except subprocess.TimeoutExpired:
    for m in ['A','B']:
     if not (out/m/'run.json').exists():write(out/m/'run.json',{'run_status':'TIMEOUT','answer_status':None,'reason':'Case process timeout','elapsed_seconds':time.perf_counter()-t})
    write(out/'complete.json',{'failure':'TIMEOUT'})
  print(role,cid,read(out/'complete.json'),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','import','run']);a=p.parse_args();{'freeze':freeze_method,'import':import_refs,'run':run_model}[a.command]()
