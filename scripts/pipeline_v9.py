"""Two final-only development calls; V8 completed intermediates are immutable inputs."""
import json,sys,time,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import write_new,digest
from legal_bench.rules_verdict_v1.final_v9 import prompt,final_schema,compact_display,expand_display,EXAMPLES,FINAL
R=Path('outputs/rules-verdict-v9-final-examples');OLD=Path('outputs/rules-verdict-v8-paired');OUT=3072
CODE=['scripts/pipeline_v9.py','legal_bench/rules_verdict_v1/final_v9.py','legal_bench/rules_verdict_v1/runtime_v9.py','legal_bench/rules_verdict_v1/repetition_v9.py','legal_bench/rules_verdict_v1/intermediate_v7.py','legal_bench/rules_verdict_v1/intermediate_v8.py','legal_bench/rules_verdict_v1/checks_v8.py','legal_bench/rules_verdict_v1/source_views.py','legal_bench/rules_verdict_v1/contracts.py','legal_bench/mlx_json_constraint.py','tests/test_final_v9.py']
def read(p):return json.loads(Path(p).read_text())
def copy(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists():assert src.read_bytes()==dst.read_bytes(),str(dst)
 else:dst.write_bytes(src.read_bytes())
def prepare():
 for rel in ['sources/69305.json','prepared/69305/law-package.json','retrieval/69305/result.json','inherited-scope-audit.json']:copy(OLD/rel,R/rel)
 for arm in ['A','B']:copy(OLD/'runs'/arm/'intermediate.json',R/'inherited'/arm/'intermediate-original.json')
 for name in ['program-checks-full.json','program-checks-compact.json','compact-trace-map.json','restored-sources.json']:copy(OLD/'runs/B'/name,R/'inherited/B'/name)
 source=read(R/'sources/69305.json');package=read(R/'prepared/69305/law-package.json');cids=[x['id'] for x in source['segments']];lids=[x['id'] for x in package['law_segments']]
 sizes={}
 for arm in ['A','B']:
  material=read(R/'inherited'/arm/'intermediate-original.json')
  if arm=='B':
   previous=material['program_checks'];material['program_checks']=compact_display(previous)
   assert expand_display(material['program_checks'])==previous
   write_new(R/'prepared/B/display-integrity.json',{'exact_roundtrip':True,'all_combinations_retained':len(material['program_checks']['combinations']),'all_joins_retained':len(material['program_checks']['joins']),'compression':'Intern EXACT repeated result, condition_signals and state values; keep each distinct object binding and all source indices. No semantic modification or selection.'})
  write_new(R/'prepared'/arm/'intermediate.json',material)
  f=R/'prepared'/arm/'prompt.txt';f.parent.mkdir(parents=True,exist_ok=True);f.write_text(prompt(source,package,material));write_new(R/'prepared'/arm/'schema.json',final_schema(cids,lids))
 write_new(R/'freeze/templates.json',{'final':FINAL,'examples':EXAMPLES,'input_order':['inherited common issue','two complete fictional examples','full target law package','unverified intermediate','full allowed target source','final output instructions']})
 settings=read(OLD/'freeze/config.json')['settings']
 protocol={'case':'69305','hypothesis':'Combined complete fictional examples and shorter nonoverlapping final field duties may permit complete source-grounded legal outputs; root cause unconfirmed, not isolated few-shot ablation.','calls':['A_FINAL','B_FINAL'],'max_calls':2,'web_calls':0,'retries':0,'max_tokens':OUT,'total_budget':32768,'round_wall_limit_seconds':1800,'per_call_limit_seconds':1200,'stop':'A FORMAT_ERROR/OUTPUT_TRUNCATED/REPETITION_ABORT does not cancel B. OOM or unsupported framework aborts remaining call; no retry or after-output changes. Stop after two attempts and one concentrated final-result source review.','repetition':'Unchanged V8 rule: within one free-text string, four nonoverlapping occurrences of an identical contiguous 64-character substring; occurrences need NOT be adjacent. Never combine fields. Add merged explanation field to same guard.','outcome_failure':None,'scope':'Exposed old-case retrospective development validation; no new sources, extraction or gold.','publication':'NO_COMMIT_OR_PUSH','base_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()}
 write_new(R/'protocol.json',protocol)
 for name in CODE:copy(Path(name),R/'freeze/code'/name)
 write_new(R/'freeze/config.json',{'settings':settings,'max_tokens':OUT,'actual_parameters':{**{k:settings[k] for k in ['temperature','top_p','top_k','min_p','repetition_penalty','enable_thinking','prefill_step_size']},'max_tokens':OUT,'logits_processors':'SchemaMask'},'files':{str(p):digest(p.read_bytes()) for p in R.rglob('*') if p.is_file() and p.name!='config.json'},'live_code':{p:digest(Path(p).read_bytes()) for p in CODE},'frozen_epoch':time.time()})
def verify():
 f=read(R/'freeze/config.json')
 for path,h in {**f['files'],**f['live_code']}.items():assert digest(Path(path).read_bytes())==h,path
 return f
def run():
 from legal_bench.rules_verdict_v1.runtime_v9 import Runner
 from mlx_vlm.generate.types import GenerateKwargs
 f=verify();runner=Runner(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),f['settings'])
 unsupported=set(f['actual_parameters'])-set(GenerateKwargs.__annotations__)
 pre=[]
 for a in ['A','B']:
  text=(R/'prepared'/a/'prompt.txt').read_text();rendered=runner.render(text);original=read(R/'inherited'/a/'intermediate-original.json');material=read(R/'prepared'/a/'intermediate.json');serial=lambda x:json.dumps(x,ensure_ascii=False,separators=(',',':'))
  pre.append({'method':a,'input_tokens':len(runner.tokenizer.encode(rendered)),'max_output_tokens':OUT,'total_tokens':len(runner.tokenizer.encode(rendered))+OUT,'thinking_off_verified':'<think>\n\n</think>' in rendered[-150:],'intermediate_original_tokens':runner.count(serial(original)),'intermediate_display_tokens':runner.count(serial(material)),'program_original_tokens':runner.count(serial(original['program_checks'])) if a=='B' else 0,'program_display_tokens':runner.count(serial(material['program_checks'])) if a=='B' else 0})
 write_new(R/'freeze/token-preflight.json',{'rows':pre,'versions':runner.versions,'model_config_hash':runner.model_config_hash,'unsupported_parameters':sorted(unsupported),'no_generation_yet':True,'source_truncated':False})
 print('PREFLIGHT',json.dumps(pre),flush=True);start=time.monotonic();rows=[];environment_failure=None
 for a in ['A','B']:
  verify();out=R/'runs'/a
  if environment_failure:
   row={'run_status':'SKIPPED','answer_status':None,'reason':environment_failure};write_new(out/'run.json',row)
  elif unsupported:
   row={'run_status':'UNSUPPORTED','answer_status':None,'reason':'UNSUPPORTED_GENERATION_PARAMETERS'};write_new(out/'run.json',row);environment_failure=row['reason']
  elif 1800-(time.monotonic()-start)<=0:
   row={'run_status':'TIMEOUT','answer_status':None,'reason':'ROUND_TIME_BUDGET_EXHAUSTED'};write_new(out/'run.json',row)
  else:
   row=runner.run((R/'prepared'/a/'prompt.txt').read_text(),read(R/'prepared'/a/'schema.json'),out,OUT,min(1200,1800-(time.monotonic()-start)))
   if row['run_status'] in ['OUT_OF_MEMORY','UNSUPPORTED']:environment_failure='Environment failure in '+a+':'+row['run_status']
  rows.append({'method':a,**row})
 write_new(R/'results.json',{'rows':rows,'local_generation_calls':sum('output_tokens' in x for x in rows),'attempts_with_saved_identity':sum('identity' in x for x in rows),'web_calls':0,'retries':0,'round_wall_seconds':time.monotonic()-start,'inference_seconds':sum(x.get('elapsed_seconds',0) for x in rows),'environment_failure':environment_failure,'concentrated_source_review_required':True,'development_only':True})
 write_new(R/'stop.json',{'reason':environment_failure or 'TWO_FINAL_SLOTS_FINISHED','additional_calls_authorized':0,'no_auto_next_round':True})
if __name__=='__main__':
 {'prepare':prepare,'verify':verify,'run':run}[sys.argv[1]]()
