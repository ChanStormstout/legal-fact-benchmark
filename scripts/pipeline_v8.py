"""Bounded V8: four sequential calls or immediate whole-round stop. Never retry."""
import json,sys,time,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import write_new,digest
from legal_bench.rules_verdict_v1.runtime_v8 import SETTINGS
from legal_bench.rules_verdict_v1.intermediate_v8 import *
R=Path('outputs/rules-verdict-v8-paired');OLD=Path('outputs/rules-verdict-v7-intermediate');OUT=3072
ORDER=[('A','stage1'),('B','stage1'),('A','final'),('B','final')]
CODE=['scripts/pipeline_v8.py']+['legal_bench/rules_verdict_v1/'+x+'.py' for x in ['checks_v8','intermediate_v8','runtime_v8','repetition_v8','intermediate_v7','contracts','source_views']]+['legal_bench/mlx_json_constraint.py','tests/test_intermediate_v8.py','tests/test_intermediate_v7.py']
def read(p):return json.loads(Path(p).read_text())
def copy(a,b):
 b.parent.mkdir(parents=True,exist_ok=True)
 if b.exists():assert a.read_bytes()==b.read_bytes(),str(b)
 else:b.write_bytes(a.read_bytes())
def inputs():return read(R/'sources/69305.json'),read(R/'prepared/69305/law-package.json')
def prepare():
 for rel in ['sources/69305.json','prepared/69305/law-package.json','retrieval/69305/result.json','inherited-scope-audit.json']:copy(OLD/rel,R/rel)
 s,p=inputs();case=[x['id'] for x in s['segments']];law=[x['id'] for x in p['law_segments']]
 for arm in ['A','B']:
  d=R/'prepared'/arm;d.mkdir(parents=True,exist_ok=True)
  (d/'stage1-prompt.txt').write_text(first_prompt(s,p,arm));write_new(d/'stage1-schema.json',notes_schema(case+law) if arm=='A' else fact_schema(case));write_new(d/'final-schema.json',final_schema(case,law))
 write_new(R/'freeze/templates.json',{'common':COMMON,'notes':NOTES,'facts':FACTS8,'final':FINAL,'final_order':['law package','intermediate','complete allowed source','shared final instructions']})
 write_new(R/'protocol.json',{'review_parent':'a6550471a962775f366598c773f8ea7d3a3ba0ab','case':'69305','call_order':ORDER,'calls_max':4,'web_calls':0,'retries':0,'max_tokens':OUT,'total_budget':32768,'inference_wall_limit_seconds':1800,'failure':'Stop entire round on any non-OK; all remaining slots SKIPPED; no semantic repair or partial answer','repetition':'Four nonoverlapping identical contiguous 64-character substrings within one free-text JSON string; state across chunks, reset per string; intervening text permitted; enums and refs excluded','review':'Only if all four calls OK: one concentrated source review of decisive final grounds; model-assisted development review, no gold; assess proposition polarity independently of eviction direction','decision':'On technical failure only: frozen configuration did not complete paired 69305; no general model/framework conclusion. Otherwise retain lightweight structure / prefer text / common model or material limits leave benefit uncertain.','scope':'V7 retrospective exposed development material and limitations retained; no independent prediction','auto_push':False})
 for name in CODE:copy(Path(name),R/'freeze/code'/name)
 write_new(R/'freeze/config.json',{'settings':{**SETTINGS,'extract_max_tokens':OUT,'direct_max_tokens':OUT,'merge_max_tokens':OUT},'max_tokens':OUT,'actual_generation_parameters':{**{k:SETTINGS[k] for k in ['temperature','top_p','top_k','min_p','repetition_penalty','enable_thinking','prefill_step_size']},'max_tokens':OUT,'logits_processors':'SchemaMask'},'files':{str(x):digest(x.read_bytes()) for x in R.rglob('*') if x.is_file() and x.name!='config.json'},'live_code':{x:digest(Path(x).read_bytes()) for x in CODE},'frozen_epoch':time.time()})
def verify():
 f=read(R/'freeze/config.json')
 for p,h in {**f['files'],**f['live_code']}.items():assert digest(Path(p).read_bytes())==h,p
 return f

def run():
 from legal_bench.rules_verdict_v1.runtime_v8 import Runner
 f=verify();runner=Runner(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),f['settings']);s,p=inputs()
 pre={a:len(runner.tokenizer.encode(runner.render((R/'prepared'/a/'stage1-prompt.txt').read_text()))) for a in ['A','B']}
 base=len(runner.tokenizer.encode(runner.render(final_prompt(s,p,{}))))
 from mlx_vlm.generate.types import GenerateKwargs
 unsupported=set(f['actual_generation_parameters'])-set(GenerateKwargs.__annotations__)
 write_new(R/'freeze/token-preflight.json',{'stage1_input_tokens':pre,'final_without_dynamic_intermediate':base,'final_dynamic_checked_before_each_call':True,'max_tokens':OUT,'total_budget':32768,'versions':runner.versions,'model_config_hash':runner.model_config_hash,'unsupported_parameters':sorted(unsupported),'thinking_off':all('<think>\n\n</think>' in runner.render((R/'prepared'/a/'stage1-prompt.txt').read_text())[-150:] for a in ['A','B'])})
 if unsupported or max(pre.values())+OUT>32768 or base+OUT>32768:raise ValueError('Preflight failed without generation')
 started=time.monotonic();rows=[];materials={};stop=None
 for arm,stage in ORDER:
  verify();out=R/'runs'/arm/stage
  if stop:
   row={'method':arm,'stage':stage,'run_status':'SKIPPED','answer_status':None,'reason':stop};write_new(out/'run.json',row);rows.append(row);continue
  if stage=='stage1':prompt=(R/'prepared'/arm/'stage1-prompt.txt').read_text();schema=read(R/'prepared'/arm/'stage1-schema.json')
  else:prompt=final_prompt(s,p,materials[arm]);schema=read(R/'prepared'/arm/'final-schema.json')
  remaining=1800-(time.monotonic()-started)
  if remaining<=0:
   row={'run_status':'TIMEOUT','answer_status':None,'reason':'ROUND_BUDGET_BEFORE_CALL'};write_new(out/'run.json',row)
  else:row=runner.run(prompt,schema,out,OUT,remaining)
  rows.append({'method':arm,'stage':stage,**row})
  if row['run_status']!='OK':stop=arm+'/'+stage+':'+row['run_status'];continue
  data=read(out/'parsed.json')
  if stage=='stage1':
   material={'proposal':data}
   if arm=='B':
    full,restored=check_facts(data,s);compact,mapping=compact_checks(full)
    write_new(R/'runs/B/program-checks-full.json',full);write_new(R/'runs/B/restored-sources.json',restored);write_new(R/'runs/B/program-checks-compact.json',compact);write_new(R/'runs/B/compact-trace-map.json',mapping)
    material['program_checks']=compact
   materials[arm]=material;write_new(R/'runs'/arm/'intermediate.json',material)
   text=json.dumps(material,ensure_ascii=False,separators=(',',':'));checks=json.dumps(material.get('program_checks',{}),ensure_ascii=False,separators=(',',':'))
   write_new(R/'runs'/arm/'intermediate-size.json',{'chars':len(text),'tokens':runner.count(text),'program_chars':len(checks) if arm=='B' else 0,'program_tokens':runner.count(checks) if arm=='B' else 0})
 write_new(R/'results.json',{'rows':rows,'calls':sum('identity' in x for x in rows),'web_calls':0,'retries':0,'stop_reason':stop,'round_wall_seconds':time.monotonic()-started,'inference_seconds':sum(x.get('elapsed_seconds',0) for x in rows),'review_allowed':stop is None})
 write_new(R/'stop.json',{'reason':stop or 'FOUR_CALLS_COMPLETED','no_further_calls':True,'remaining_slots_skipped':sum(x['run_status']=='SKIPPED' for x in rows)})
if __name__=='__main__':
 if sys.argv[1]=='prepare':prepare()
 elif sys.argv[1]=='run':run()
 else:verify()
