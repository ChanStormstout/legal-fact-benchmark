"""Frozen format-repaired replay; same13 questions, exposed development sample."""
import sys,json,shutil,subprocess,time,argparse
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read,digest
from scripts.local_qwen_worker_v3 import ROOT,SETTINGS,write
TASKS=lambda:read(ROOT/'tasks.json')['tasks']
CODE=['legal_bench/compact_output_v3.py','legal_bench/mlx_json_constraint.py','legal_bench/field_pipeline_v2.py','legal_bench/model_output.py','legal_bench/fast_development.py','legal_bench/conditional_engine.py','legal_bench/type_projection.py','legal_bench/typed_relations.py','legal_bench/core.py','legal_bench/engine.py','scripts/local_qwen_worker_v3.py','scripts/local_qwen_experiment_v3.py']

def freeze():
 if (ROOT/'freeze.json').exists():return
 assert read(ROOT/'development-check-result.json')['format_gate_passed']
 for f in CODE:
  target=ROOT/'method-snapshot'/f;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target)
 write(ROOT/'config.json',SETTINGS)
 write(ROOT/'freeze.json',{'saved_at':datetime.now(timezone.utc).isoformat(),'sample_role':'DEVELOPMENT_VALIDATION_AFTER_OBSERVED_FORMAT_FAILURES','config_hash':digest(SETTINGS),'tasks_hash':digest(TASKS()),'sample_hash':digest(read(ROOT/'evaluation-sample.json')),'reference_hash':digest(read(ROOT/'references/all-v1.json')),'method_hashes':{f:digest(Path(f).read_bytes()) for f in CODE},'format_checks':read(ROOT/'development-check-result.json'),'semantics_not_tuned':'No change to questions, states, relations, references or source ranges. Format checks do not require expected matches.','generated_string_limit':240,'array_limit':20,'full_sources_and_expanded_evidence_not_truncated':True})
 write(ROOT/'evaluation-freeze.json',{'saved_at':datetime.now(timezone.utc).isoformat(),'role':'DEVELOPMENT_FORMAT_REPAIR_VALIDATION','sample_hash':digest(read(ROOT/'evaluation-sample.json')),'reference_hash':digest(read(ROOT/'references/all-v1.json')),'method_freeze_hash':digest(read(ROOT/'freeze.json')),'selection_unchanged_from_v1':True,'references_precede_all_local_outputs':True,'source_review_limit_total':3})

def run():
 f=read(ROOT/'freeze.json');assert all(digest(Path(p).read_bytes())==h for p,h in f['method_hashes'].items())
 assert digest(read(ROOT/'evaluation-sample.json'))==f['sample_hash']
 assert digest(read(ROOT/'references/all-v1.json'))==f['reference_hash']
 for cid in read(ROOT/'evaluation-sample.json')['cases']:
  out=ROOT/'runs'/cid
  if (out/'complete.json').exists():continue
  out.mkdir(parents=True,exist_ok=True);t=time.perf_counter()
  with (out/'process.log').open('w') as log:
   try:
    result=subprocess.run([str(Path('.runtime/qwen35-v1/bin/python').absolute()),'scripts/local_qwen_worker_v3.py','--source',str(ROOT/'sources'/(cid+'.json')),'--out',str(out),'--config',str(ROOT/'config.json')],stdout=log,stderr=subprocess.STDOUT,timeout=2700)
    if result.returncode!=0:raise RuntimeError('Worker exited '+str(result.returncode))
   except (subprocess.TimeoutExpired,RuntimeError) as exc:
    status='TIMEOUT' if isinstance(exc,subprocess.TimeoutExpired) else 'UNSUPPORTED'
    for m in ['A','B']:
     if not (out/m/'run.json').exists():write(out/m/'run.json',{'run_status':status,'answer_status':None,'reason':str(exc),'elapsed_seconds':time.perf_counter()-t})
    write(out/'complete.json',{'case_id':cid,'failure':status})
  print(cid,read(out/'complete.json'),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','run']);a=p.parse_args();{'freeze':freeze,'run':run}[a.command]()
