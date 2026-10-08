"""One immutable 24-slot local development comparison, no semantic repairs/retries."""
import argparse,copy,hashlib,json,shutil,subprocess,sys,time
from collections import Counter,defaultdict
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.irac_application.hybrid_v3 import branches,analyze,compact,legacy_replay,source_errors
from legal_bench.irac_application.hybrid_v3_tasks import schema,prompt
from legal_bench.irac_application.aligned_v2_runtime import atomic_json
R=Path('outputs/irac-hybrid-decision-v3');V=Path('outputs/gnn-irac-aligned-v2')
CASES=['1114159','112400','188721101','52547606','55384096','68065690']
read=lambda p:json.loads(Path(p).read_text())
hashfile=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
CODE=['scripts/irac_hybrid_v3.py','legal_bench/irac_application/hybrid_v3.py','legal_bench/irac_application/hybrid_v3_tasks.py','legal_bench/irac_application/aligned_logic.py','legal_bench/irac_application/aligned_v2.py','legal_bench/irac_application/aligned_graph.py','legal_bench/irac_application/aligned_v2_runtime.py','legal_bench/rules_verdict_v1/runtime_constraint_diag_v1.py','legal_bench/mlx_json_constraint.py','legal_bench/mlx_json_constraint_v2.py','legal_bench/rules_verdict_v1/repetition_v9.py','legal_bench/rules_verdict_v1/source_views.py','legal_bench/rules_verdict_v1/contracts.py','tests/test_irac_hybrid_v3.py']

def inputs(cid):
 m=read(R/'sources'/f'{cid}.json');t=read(R/'templates'/f"{m['family']}.json");law=read(R/'sources'/f"{m['family']}-law.json")
 return m,t,law

def prepare():
 assert not (R/'freeze/config.json').exists(),'already frozen'
 for p in (V/'templates').glob('*.json'):atomic_json(R/'templates'/p.name,branches(read(p)))
 replay_summary=[]
 for p in sorted((V/'predictions').glob('*.json')):
  d=read(p); rows=d['rows'];groups=defaultdict(dict)
  for row in rows:
   probs=row['probabilities'];idx=max(range(len(probs)),key=probs.__getitem__)
   groups[row['package_id']][row['unit_id']]={'status':['SUPPORTED','REFUTED','UNRESOLVED'][idx],'probabilities':probs}
  for cid,preds in groups.items():
   g=read(V/'graphs'/f'{cid}.json');out=legacy_replay(g,preds);atomic_json(R/'replay'/p.stem/f'{cid}.json',out)
   replay_summary.append({'run':p.stem,'case_id':cid,'units':len(out['units']),'old_blocked':sum(bool(u['v2_program_state']['blocking']) for u in out['units']),'retained_predictions_different_from_old_program':sum(u['v3_prediction_preserved']['status']!=u['v2_program_state']['status'] for u in out['units']),'branch_detail_unavailable':sum(u['replay_status']=='BRANCH_DETAIL_UNAVAILABLE' for u in out['units']),'legacy_attribution_unavailable':True,'old_claim_states':[x['status'] for x in out['old_claims']],'new_claim_states':[x['status'] for x in out['new_claims']]})
 atomic_json(R/'replay/summary.json',replay_summary)
 for cid in CASES:
  m,t,l=inputs(cid)
  for stage in ['A','proposal']:
   kind='proposal' if stage=='proposal' else 'final';dest=R/'prepared'/cid/stage;dest.mkdir(parents=True,exist_ok=True)
   (dest/'prompt.txt').write_text(prompt(kind,m,t,l));atomic_json(dest/'schema.json',schema(kind,m,t,l))
 atomic_json(R/'protocol.json',{'cases':CASES,'order':[f'{c}/{s}' for c in CASES for s in ['A','proposal','B','C']], 'max_calls':24,'max_tokens':3072,'context':32768,'generation_seconds_budget':5400,'web':0,'training':0,'retries':0,'source_role':'Exposed development; same complete allowed v2 material, no target final reasoning','conditions':{'A':'direct explicit prediction','B':'same source plus new semantic proposal','C':'same proposal plus deterministic full checks'},'failure':'A or B independent failure does not block others. Proposal interface failure skips B/C. OOM/framework or total generation budget stops remainder. No retry.', 'evaluation':'One six-case source review after all attempts. Existing definite compatible references are secondary; unresolved references never converted to binary. No target outcome score. No target-specific evaluation hints in prompts.','stop':'Deliver after one replay and <=24 calls; no next round, commit or push'})


def interface_check(value,stage,template,sources,cid):
 errors=[]
 expected={t['id'] for t in template['tests']};claims={c['id'] for c in template['claims'] if c['expression']['op']!='UNSUPPORTED'}
 if stage=='proposal':
  ids=[b['id'] for b in value['bindings']];eids=[e['id'] for e in value['evidence']]
  if not ids or len(ids)!=len(set(ids)) or len(eids)!=len(set(eids)):errors.append('EMPTY_OR_DUPLICATE_LOCAL_ID')
  for b in value['bindings']:
   if not b['claim_ids'] or not set(b['claim_ids'])<=claims:errors.append('INVALID_CLAIM')
   # The interface requires directions, not correct directions.
   if {x['test_id'] for x in value['conditions'] if x['binding_id']==b['id']}!=expected:errors.append('MISSING_REQUIRED_CONDITION_DIRECTION:'+b['id'])
  for x in value['conditions']:
   if x['binding_id'] not in ids or not set(x['evidence_ids'])<=set(eids):errors.append('DANGLING_CONDITION_REFERENCE')
  for e in value['evidence']:
   if e['binding_id'] not in ids:errors.append('DANGLING_EVIDENCE_BINDING')
  for l in value['limitations']:
   if l['binding_id'] not in ids or not set(l['evidence_ids'])<=set(eids):errors.append('DANGLING_LIMIT_REFERENCE')
 else:
  if {a['claim_id'] for a in value['answers']}!=claims:errors.append('MISSING_OR_WRONG_REQUEST')
  for a in value['answers']:
   if {x['test_id'] for x in a['conditions']}!=expected:errors.append('MISSING_REQUIRED_CONDITION_DIRECTION')
 # Bad individual source addresses are isolated in checks, not repaired as facts.
 return errors

def complete_slot(runner,cid,stage,text,contract,remaining,out):
 run=runner.run(text,contract,out,max_tokens=3072,remaining_seconds=remaining,constraint_mode='FIXED')
 m,t,law=inputs(cid);sources=dict(m['sources']);sources.update({s['source_id']:s for s in law})
 result={'case_id':cid,'method':stage,'run_status':run['run_status'],'prediction':None,'raw_run':'run.json'}
 if run['run_status']=='OK':
  if run.get('schema_mask_calls',0)<=0:result.update(run_status='UNSUPPORTED',reason='FIXED_MASK_NOT_EFFECTIVE')
  else:
   parsed=read(out/'parsed.json');errors=interface_check(parsed,stage,t,sources,cid)
   if errors:result.update(run_status='FORMAT_ERROR',reason=errors)
   else:
    result['prediction']=parsed
    if stage=='proposal':atomic_json(R/'checks'/f'{cid}.json',analyze(parsed,t,sources,cid))
 atomic_json(out/'result.json',result);return result,run

def freeze():
 assert not (R/'freeze/config.json').exists()
 tests=(R/'engineering/tests.txt').read_text();assert '\nOK' in tests and 'skipped=' not in tests
 s=read('outputs/rules-verdict-v11-intermediate-ablation/freeze/config.json')['settings']
 files={str(p):hashfile(p) for d in ['sources','templates','prepared','replay'] for p in (R/d).rglob('*') if p.is_file()}
 files[str(R/'protocol.json')]=hashfile(R/'protocol.json')
 for p in CODE:
  dest=R/'freeze/code'/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);files[str(dest)]=hashfile(dest)
 atomic_json(R/'freeze/config.json',{'settings':s,'actual_max_tokens':3072,'constraint_mode':'FIXED','live_code':{p:hashfile(p) for p in CODE},'files':files,'time':time.time(),'evaluation_before_generation':'protocol.json; source review only after all conditions; no new binary gold','original_v2_prediction_hashes':{str(p):hashfile(p) for p in (V/'predictions').glob('*.json')}})

def verify():
 f=read(R/'freeze/config.json')
 for p,h in {**f['live_code'],**f['files'],**f['original_v2_prediction_hashes']}.items():assert hashfile(p)==h,p
 return f

def run():
 from legal_bench.rules_verdict_v1.runtime_constraint_diag_v1 import Runner
 frozen=verify(); specs=read(R/'protocol.json')['order']; ledger=R/'run-ledger.json'
 if ledger.exists():raise RuntimeError('Run already started; preserve; no automatic retry')
 rows=[];atomic_json(ledger,{'status':'STARTING','rows':rows,'planned':specs})
 try:runner=Runner(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),frozen['settings'])
 except Exception as e:
  atomic_json(ledger,{'status':'ENVIRONMENT_BLOCKED','error':repr(e),'rows':rows,'planned':specs});return
 known={}
 for cid in CASES:
  for stage in ['A','proposal']:
   text=(R/'prepared'/cid/stage/'prompt.txt').read_text();known[f'{cid}/{stage}']=len(runner.tokenizer.encode(runner.render(text)))
 atomic_json(R/'freeze/token-preflight.json',{'known_input_tokens':known,'max_tokens':3072,'total_context':32768,'dynamic_B_C':'Count complete rendered input before each generation; no truncation','versions':runner.versions,'load_seconds':runner.loaded_seconds,'model_config_hash':runner.model_config_hash,'chat_template_thinking_off':all('<think>\n\n</think>' in runner.render((R/'prepared'/cid/'A/prompt.txt').read_text())[-150:] for cid in CASES)})
 spent=0.;stop=None;proposals={}
 for slot in specs:
  verify();cid,stage=slot.split('/');out=R/'runs'/cid/stage
  if stop or (stage in ['B','C'] and cid not in proposals):
   result={'case_id':cid,'method':stage,'run_status':'SKIPPED','prediction':None,'reason':stop or 'PROPOSAL_TECHNICAL_OR_INTERFACE_FAILURE'};atomic_json(out/'result.json',result);rows.append(result);atomic_json(ledger,{'status':'RUNNING','rows':rows,'generation_seconds':spent});continue
  m,t,law=inputs(cid)
  if stage in ['A','proposal']:
   text=(R/'prepared'/cid/stage/'prompt.txt').read_text();contract=read(R/'prepared'/cid/stage/'schema.json')
  else:
   inter={'proposal':proposals[cid]}
   if stage=='C':inter['program_checks']=compact(read(R/'checks'/f'{cid}.json'))
   text=prompt('final',m,t,law,inter);contract=schema('final',m,t,law)
   dest=R/'prepared'/cid/stage;dest.mkdir(parents=True,exist_ok=True);(dest/'prompt.txt').write_text(text);atomic_json(dest/'schema.json',contract);atomic_json(dest/'intermediate.json',inter)
  remaining=5400-spent
  if remaining<=0:
   stop='TOTAL_GENERATION_BUDGET_EXHAUSTED';result={'case_id':cid,'method':stage,'run_status':'SKIPPED','prediction':None,'reason':stop};atomic_json(out/'result.json',result);rows.append(result);continue
  try:
   result,meta=complete_slot(runner,cid,stage,text,contract,remaining,out)
  except Exception as e:
   # Raw/start/partial token files from the runner remain; no fabricated answer.
   result={'case_id':cid,'method':stage,'run_status':'RUN_LOG_OR_FRAMEWORK_ERROR','prediction':None,'error':repr(e)};atomic_json(out/'result.json',result);meta={};stop='FRAMEWORK_OR_RECORDING_FAILURE'
  spent+=meta.get('elapsed_seconds',0)
  if result['run_status']=='OK' and stage=='proposal':proposals[cid]=result['prediction']
  if meta.get('run_status') in ('OUT_OF_MEMORY','UNSUPPORTED'):stop='RESOURCE_OR_FRAMEWORK_FAILURE'
  if meta.get('run_status')=='TIMEOUT':stop='TOTAL_GENERATION_BUDGET_EXHAUSTED'
  rows.append({'case_id':cid,'method':stage,'run_status':result['run_status'],'prediction_file':str(out/'result.json'),'elapsed_seconds':meta.get('elapsed_seconds'),'output_tokens':meta.get('output_tokens'),'input_tokens':meta.get('prompt_tokens')})
  atomic_json(ledger,{'status':'RUNNING','rows':rows,'generation_seconds':spent,'stop':stop})
 atomic_json(ledger,{'status':'COMPLETE' if not stop else 'STOPPED','rows':rows,'generation_seconds':spent,'stop':stop,'no_retry':True,'generation_calls':sum((R/'runs'/c/s/'start.json').exists() for c in CASES for s in ['A','proposal','B','C'])})

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','freeze','run','verify']);a=p.parse_args();globals()[a.command]()
