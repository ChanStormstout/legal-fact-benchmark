"""Bounded same-B-input diagnosis: mask disabled once, corrected mask once. No prompt tuning."""
import json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import digest,write_new
R=Path('outputs/json-constraint-diagnosis-v1');OLD=Path('outputs/rules-verdict-v9-final-examples')
CODE=['scripts/constraint_diagnosis_v1.py','scripts/audit_constraint_v1.py','scripts/audit_constraint_fix_v1.py','legal_bench/mlx_json_constraint.py','legal_bench/mlx_json_constraint_v2.py','legal_bench/rules_verdict_v1/runtime_constraint_diag_v1.py','legal_bench/rules_verdict_v1/repetition_v9.py','legal_bench/rules_verdict_v1/source_views.py','legal_bench/rules_verdict_v1/contracts.py','tests/test_mlx_constraint_v2.py']
def read(p):return json.loads(p.read_text())
def copy(a,b):
 b.parent.mkdir(parents=True,exist_ok=True)
 if b.exists():assert b.read_bytes()==a.read_bytes(),str(b)
 else:b.write_bytes(a.read_bytes())
def prepare():
 for name in ['prompt.txt','schema.json']:copy(OLD/'runs/B'/name,R/'prepared'/name)
 for rel in ['sources/69305.json','prepared/69305/law-package.json']:copy(OLD/rel,R/'materials'/rel)
 for name in CODE:copy(Path(name),R/'freeze/code'/name)
 write_new(R/'protocol.json',{'case':'69305','input':'EXACT V9 B final prompt and schema, no legal or text changes','hypothesis':'Composite quote-bearing tokens omitted by LMFE free-text shortcut may prevent favored field endings; not all quote tokens are blocked. Offline reproduction independent of model inference.','calls':['NONE','FIXED'],'maximum_new_generation_calls':2,'web_calls':0,'retries':0,'settings':'EXACT V9 settings; max_tokens3072, context32768, greedy, repetition1, thinking off','guard':'Same-field exact 64-character fragment at four nonoverlapping positions, not necessarily adjacent. Stop incomplete output; do not rewrite.','stop':'Maximum two calls; same prompt and model; no sampling/framework scan. Stop remaining on OOM or unsupported environment. Otherwise each gets one attempt. Round1800sec, each at most1200sec. No additional legal experiment or automatic push.','diagnostic_scope':'Execution/format only; completion does not establish legal correctness or A/B efficacy.'})
 write_new(R/'freeze/config.json',{'settings':read(OLD/'freeze/config.json')['settings'],'max_tokens':3072,'files':{str(p):digest(p.read_bytes()) for p in R.rglob('*') if p.is_file() and p.name!='config.json'},'live_code':{p:digest(Path(p).read_bytes()) for p in CODE},'created_epoch':time.time()})
def verify():
 f=read(R/'freeze/config.json')
 for p,h in {**f['files'],**f['live_code']}.items():assert digest(Path(p).read_bytes())==h,p
 return f
def run():
 from legal_bench.rules_verdict_v1.runtime_constraint_diag_v1 import Runner
 f=verify();runner=Runner(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),f['settings']);prompt=(R/'prepared/prompt.txt').read_text();schema=read(R/'prepared/schema.json');rendered=runner.render(prompt);n=len(runner.tokenizer.encode(rendered))
 assert rendered==(OLD/'runs/B/rendered.txt').read_text()
 write_new(R/'freeze/token-preflight.json',{'input_tokens':n,'max_tokens':3072,'total_budget':32768,'exact_v9_rendered_input':True,'prompt_hash':digest(prompt.encode()),'schema_hash':digest(schema),'versions':runner.versions,'model_config_hash':runner.model_config_hash,'thinking_off':True,'only_mode_difference':'NONE omits logits_processors; FIXED uses versioned corrected SchemaMask'})
 started=time.monotonic();rows=[];stop=None
 for mode in ['NONE','FIXED']:
  verify();d=R/'runs'/mode
  if stop or time.monotonic()-started>=1800:
   row={'run_status':'SKIPPED','answer_status':None,'reason':stop or 'ROUND_BUDGET'};write_new(d/'run.json',row)
  else:
   row=runner.run(prompt,schema,d,3072,min(1200,1800-(time.monotonic()-started)),constraint_mode=mode)
   if row['run_status'] in ['OUT_OF_MEMORY','UNSUPPORTED']:stop=mode+':'+row['run_status']
  rows.append({'mode':mode,**row})
 write_new(R/'results.json',{'rows':rows,'new_calls':sum('output_tokens' in x for x in rows),'web_calls':0,'retries':0,'inference_seconds':sum(x.get('elapsed_seconds',0) for x in rows),'round_seconds':time.monotonic()-started,'remaining_environment_failure':stop,'no_additional_calls':True})
if __name__=='__main__':{'prepare':prepare,'verify':verify,'run':run}[sys.argv[1]]()
