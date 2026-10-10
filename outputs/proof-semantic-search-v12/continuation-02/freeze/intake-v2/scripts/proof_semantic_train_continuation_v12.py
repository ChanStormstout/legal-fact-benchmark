#!/usr/bin/env python3
"""One frozen gated training batch. No TEST data, no retries or hyperparameter search."""
import argparse,json,sys,hashlib,subprocess,time,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.semantic_data_v12 import training_gate
ROOT=Path('outputs/proof-semantic-search-v12')
def read(p):return json.loads(Path(p).read_text())
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError(p)
 p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--rows',required=True);ap.add_argument('--qc',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();dest=Path(a.out)
 if dest.exists():raise SystemExit('BATCH_ALREADY_ATTEMPTED')
 dest.mkdir(parents=True);rows=read(a.rows);qc=read(a.qc);gate=training_gate(rows,qc);save(dest/'gate.json',gate)
 if not gate['open']:save(dest/'status.json',{'status':'NOT_STARTED_DATA_GATE','fits':0,'reason':gate['reasons']});return
 if any(r['split']=='TEST' for r in rows):raise ValueError('TEST_LABEL_IN_TRAIN_BATCH')
 graphs={};pairs={};texts={};files={a.rows:None,a.qc:None};seen=set()
 for row in rows:
  if not row.get('valid') or row['label']=='UNLABELED':continue
  cid=row['case_id'];d=row['dispute_id']
  if cid in seen:continue
  seen.add(cid);p=Path(row['proposal_dir']);gp=p/'graph.json';cp=p/'ce-pairs.json';g=read(gp);graphs[d]=g
  for pair in read(cp):pairs[cid+'::'+pair['id']]=pair
  for node in g['nodes']:texts[hashlib.sha256(node['text'].encode()).hexdigest()]=node['text']
  files[str(gp)]=None;files[str(cp)]=None
 save(dest/'graphs.json',graphs);save(dest/'pairs.json',pairs);save(dest/'texts.json',texts)
 # Deterministic existing E5 encoder; no fine-tuning or source truncation.
 cmd=['.runtime/irac-e5-v1/bin/python','scripts/proof_semantic_encode_v12.py',str(dest)]
 proc=subprocess.run(cmd,capture_output=True,text=True);(dest/'encoding.stdout.txt').write_text(proc.stdout);(dest/'encoding.stderr.txt').write_text(proc.stderr)
 if proc.returncode:save(dest/'status.json',{'status':'ENCODING_FAILURE','fits':0,'answer':None});return
 for p in list(Path('legal_bench/proof_carrying').glob('*v12.py'))+list(Path('scripts').glob('*semantic*v12.py'))+[dest/'graphs.json',dest/'pairs.json',dest/'vectors.npz',dest/'encoding.json',ROOT/'preparation-freeze.json']:
  files[str(p)]=None
 files={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files}
 freeze={'files':files,'rows':a.rows,'qc':a.qc,'graphs':str(dest/'graphs.json'),'pairs':str(dest/'pairs.json'),'vectors':str(dest/'vectors.npz'),'run_root':str(dest/'runs'),'deadline_unix':time.time()+21600,'seeds':[20261001,20261002,20261003],'max_fits':9,'test_read':False,'protocol':read(ROOT/'preparation-freeze.json')['training']}
 save(dest/'training-freeze.json',freeze);attempts=[]
 for kind in ['Flat','RGCN','CrossEncoder']:
  for seed in freeze['seeds']:
   if time.time()>=freeze['deadline_unix']:break
   env='.runtime/proof-semantic-v12/bin/python' if kind=='CrossEncoder' else '.runtime/qwen35-v1/bin/python'
   cmd=[env,'scripts/proof_semantic_fit_v12.py','--freeze',str(dest/'training-freeze.json'),'--kind',kind,'--seed',str(seed)]
   t=time.time()
   try:result=subprocess.run(cmd,capture_output=True,text=True,timeout=max(1,freeze['deadline_unix']-t));status='RETURNED';rc=result.returncode;stdout=result.stdout;stderr=result.stderr
   except subprocess.TimeoutExpired as e:status='TOTAL_TIME_BUDGET';rc=None;stdout=str(e.stdout or '');stderr=str(e.stderr or '')
   (dest/f'{kind}-{seed}.stdout.txt').write_text(stdout);(dest/f'{kind}-{seed}.stderr.txt').write_text(stderr)
   attempts.append({'kind':kind,'seed':seed,'status':status,'returncode':rc,'observed_seconds':time.time()-t});save(dest/f'attempt-{len(attempts):02}.json',attempts[-1])
   predicted=dest/'runs'/f'{kind}-{seed}'/'dev-reloaded-predictions.json'
   if rc==0 and predicted.exists():
    for cid in sorted({r['case_id'] for r in rows if r['split']=='DEV'}):
     delivery=dest/'delivery'/f'{kind}-{seed}'/cid
     command=[sys.executable,'scripts/proof_semantic_apply_v12.py','--proposal-dir',str(Path(next(r['proposal_dir'] for r in rows if r['case_id']==cid))),'--predictions',str(predicted),'--out',str(delivery)]
     check=subprocess.run(command,capture_output=True,text=True,timeout=120)
     save(dest/f'delivery-{kind}-{seed}-{cid}.json',{'returncode':check.returncode,'stdout':check.stdout,'stderr':check.stderr,'prediction_origin':'RELOADED_TRAINED_WEIGHTS','reference_read':False})

 save(dest/'status.json',{'status':'BATCH_FINISHED_NO_AUTOMATIC_TEST_ANSWERS','attempts':attempts,'test_read':False})
if __name__=='__main__':main()
