"""V7 immutable two-stage comparison. No retries, new retrieval or model substitution."""
import argparse,json,sys,subprocess,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import write_new,digest
from legal_bench.rules_verdict_v1.runtime import SETTINGS
from legal_bench.rules_verdict_v1.intermediate_v7 import notes_schema,fact_schema,final_schema,first_prompt,final_prompt,check_facts,COMMON,FINAL,NOTES,FACTS
R=Path('outputs/rules-verdict-v7-intermediate');OLD=Path('outputs/rules-verdict-v6-end-to-end');CASES=['661475','69305','1134266'];ARMS=['A2','B2'];OUT=2048;RESERVE=14000
CODE=['scripts/pipeline_v7.py','legal_bench/rules_verdict_v1/intermediate_v7.py','legal_bench/rules_verdict_v1/runtime.py','legal_bench/rules_verdict_v1/contracts.py','legal_bench/rules_verdict_v1/source_views.py','legal_bench/model_output.py','legal_bench/mlx_json_constraint.py','tests/test_intermediate_v7.py']
def read(p):return json.loads(Path(p).read_text())
def copynew(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True);raw=src.read_bytes()
 if dst.exists():
  if dst.read_bytes()!=raw:raise ValueError('Immutable file differs '+str(dst))
 else:dst.write_bytes(raw)
def prepare():
 origins={}
 for cid in CASES:
  for rel in ['sources/'+cid+'.json','prepared/'+cid+'/law-package.json','retrieval/'+cid+'/result.json']:
   copynew(OLD/rel,R/rel);origins[rel]={'source':str(OLD/rel),'sha256':digest((OLD/rel).read_bytes())}
  s=read(R/'sources'/(cid+'.json'));p=read(R/'prepared'/cid/'law-package.json');target=[x['id'] for x in s['segments']];ids=target+[x['id'] for x in p['law_segments']]
  for arm in ARMS:
   d=R/'prepared'/cid/arm;d.mkdir(parents=True,exist_ok=True);prompt=first_prompt(s,p,arm);f=d/'stage1-prompt.txt'
   if f.exists() and f.read_text()!=prompt:raise ValueError('Changed prompt')
   f.write_text(prompt);write_new(d/'stage1-schema.json',notes_schema(ids) if arm=='A2' else fact_schema(target));write_new(d/'final-schema.json',final_schema(ids))
 copynew(OLD/'scope-audit.json',R/'inherited-scope-audit.json')
 write_new(R/'protocol.json',{'cases':CASES,'methods':{'A2':'full input -> substantive sourced text notes -> full input plus notes -> shared final model','B2':'same full input -> partial model facts -> local checks -> same full input plus proposals and checks -> shared final model'},'calls_maximum':12,'web_calls':0,'retries':0,'max_output_each':OUT,'final_intermediate_reserve_tokens':RESERVE,'stage1_failure':'Method fails; skip its final stage; other methods continue','no_source_truncation':True,'review':'One concentrated Codex source review of decisive grounds of every available final answer; not exhaustive intermediate gold; no additional inference calls','review_dimensions':['decisive factual support','statement status','object and event binding','law scope','label/reason consistency','critical versus irrelevant gaps','actual use or rejection of intermediate material'], 'decision_rules':{'RETAIN_LIGHTWEIGHT_STRUCTURE':'Concrete source-checkable complete-answer improvement without an added equally serious error; development signal only','PREFER_TEXT':'No additional benefit or representation burden loses useful information','BATCH_INDETERMINATE':'Shared decisive fact/law gaps dominate'},'inherited_scope':'Exposed retrospective cases, lower-court information, some later authorities, target-derived generic researcher formula. No independent prediction, rule induction, accuracy estimate or retrieval comparison.','origins':origins,'base_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'branch':subprocess.check_output(['git','branch','--show-current'],text=True).strip(),'earlier_outputs_not_reused':'Different two-stage roles; sources/laws/runtime only reused','no_character_caps':'Unlimited schema strings; 2048 global token limit. Closed JSON alone is not semantic completeness.'})
 write_new(R/'freeze/templates.json',{'common':COMMON,'notes':NOTES,'facts':FACTS,'final':FINAL})
 for name in CODE:copynew(Path(name),R/'freeze/code'/name)
 files={str(p):digest(p.read_bytes()) for p in R.rglob('*') if p.is_file() and p.name!='config.json'}
 write_new(R/'freeze/config.json',{'settings':SETTINGS,'max_output_tokens':OUT,'files':files,'live_code':{p:digest(Path(p).read_bytes()) for p in CODE},'created_at_epoch':time.time()})
def verify():
 f=read(R/'freeze/config.json')
 for p,h in {**f['files'],**f['live_code']}.items():
  if digest(Path(p).read_bytes())!=h:raise ValueError('Frozen content changed '+p)
 return f

def runall():
 from legal_bench.rules_verdict_v1.runtime import Runner
 f=verify();runner=Runner(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),f['settings'])
 pre=[]
 for cid in CASES:
  s=read(R/'sources'/(cid+'.json'));p=read(R/'prepared'/cid/'law-package.json')
  base=len(runner.tokenizer.encode(runner.render(final_prompt(s,p,{}))))
  for arm in ARMS:
   n=len(runner.tokenizer.encode(runner.render((R/'prepared'/cid/arm/'stage1-prompt.txt').read_text())))
   pre.append({'case':cid,'arm':arm,'stage1_input_tokens':n,'final_empty_material_input_tokens':base,'final_reserved_total':base+RESERVE+OUT,'stage1_total':n+OUT,'fits':max(n+OUT,base+RESERVE+OUT)<=f['settings']['total_budget']})
 preflight={'rows':pre,'versions':runner.versions,'model_config_hash':runner.model_config_hash,'settings':f['settings'],'no_generation_preflight':True,'source_truncated':False}
 write_new(R/'freeze/token-preflight.json',preflight)
 if not all(x['fits'] for x in pre):raise ValueError('Preflight failed; no calls started')
 for cid in CASES:
  s=read(R/'sources'/(cid+'.json'));p=read(R/'prepared'/cid/'law-package.json')
  for arm in ARMS:
   verify();d=R/'runs'/cid/arm
   print('METHOD',cid,arm,flush=True)
   m=runner.run((R/'prepared'/cid/arm/'stage1-prompt.txt').read_text(),read(R/'prepared'/cid/arm/'stage1-schema.json'),d/'stage1',OUT)
   if m['run_status']!='OK':
    write_new(d/'method.json',{'run_status':m['run_status'],'answer_status':None,'failed_stage':1,'stage2':'NOT_ATTEMPTED_NO_BYPASS'});continue
   proposal=read(d/'stage1/parsed.json');material={'kind':'SOURCE_GROUNDED_TEXT_NOTES' if arm=='A2' else 'MODEL_PROPOSED_PARTIAL_FACTS_WITH_LIMITED_CHECKS','proposal':proposal}
   if arm=='B2':
    checks,restored=check_facts(proposal,s);write_new(d/'program-checks.json',checks);write_new(d/'restored-sources.json',restored);material['program_checks']=checks
   write_new(d/'intermediate.json',material)
   serial=json.dumps(material,ensure_ascii=False,separators=(',',':'));prompt=final_prompt(s,p,material);tokens=runner.count(serial)
   checks_serial=json.dumps(material.get('program_checks',{}),ensure_ascii=False,separators=(',',':'))
   deriv={'stage1_raw_hash':m['raw_hash'],'intermediate_hash':digest(material),'final_prompt_hash':digest(prompt.encode()),'intermediate_chars':len(serial),'intermediate_tokens':tokens,'program_chars':len(checks_serial) if arm=='B2' else 0,'program_tokens':runner.count(checks_serial) if arm=='B2' else 0,'full_final_input_tokens':len(runner.tokenizer.encode(runner.render(prompt))),'frozen_template':str(R/'freeze/templates.json')}
   write_new(d/'final-input-derivation.json',deriv)
   if tokens>RESERVE:
    write_new(d/'method.json',{'run_status':'INPUT_TOO_LONG','answer_status':None,'failed_stage':2,'reason':'INTERMEDIATE_EXCEEDS_FROZEN_RESERVE_NO_TRUNCATION'});continue
   result=runner.run(prompt,read(R/'prepared'/cid/arm/'final-schema.json'),d/'stage2',OUT)
   answer=read(d/'stage2/parsed.json') if result['run_status']=='OK' else None
   write_new(d/'method.json',{'run_status':result['run_status'],'answer_status':answer['outcome'] if answer else None,'answer':answer,'intermediate_tokens':tokens})
 collect()
def collect():
 rows=[];calls=[]
 for cid in CASES:
  for arm in ARMS:
   d=R/'runs'/cid/arm
   if not (d/'method.json').exists():continue
   m=read(d/'method.json');metas=[read(x) for x in sorted(d.glob('stage*/run.json'))];calls.extend(metas)
   rows.append({'case_id':cid,'method':arm,**m,'calls':len(metas),'input_tokens':sum(x.get('prompt_tokens_actual',x.get('prompt_tokens',0)) for x in metas),'output_tokens':sum(x.get('output_tokens',0) for x in metas),'seconds':sum(x.get('elapsed_seconds',0) for x in metas)})
 write_new(R/'results.json',{'rows':rows,'calls':len(calls),'web_calls':0,'retries':0,'seconds':sum(c.get('elapsed_seconds',0) for c in calls),'peak_memory_gb':max([c.get('peak_mlx_memory_gb',0) for c in calls] or [0]),'technical_failures':sum(r['run_status']!='OK' for r in rows),'evaluation':'SOURCE_REVIEW_REQUIRED_NOT_AUTOMATIC_ACCURACY'})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run','collect']);a=p.parse_args()
 if a.action=='prepare':prepare()
 elif a.action=='run':runall()
 else:collect()
