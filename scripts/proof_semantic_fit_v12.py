#!/usr/bin/env python3
"""Gated one-fit worker; caller freezes inputs and enforces total nine fits/six hours."""
import sys,json,time,argparse,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.semantic_data_v12 import training_gate
from legal_bench.proof_carrying.semantic_fit_v12 import fit_ce,fit_graph

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--freeze',required=True);ap.add_argument('--kind',choices=['Flat','RGCN','CrossEncoder'],required=True);ap.add_argument('--seed',type=int,choices=[20261001,20261002,20261003],required=True);a=ap.parse_args();fp=Path(a.freeze);f=json.loads(fp.read_text())
 for path,sha in f['files'].items():
  if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=sha:raise SystemExit('FROZEN_INPUT_CHANGED:'+path)
 rows=json.loads(Path(f['rows']).read_text());qc=json.loads(Path(f['qc']).read_text());gate=training_gate(rows,qc)
 if not gate['open']:raise SystemExit(json.dumps(gate))
 if any(r['split']=='TEST' for r in rows):raise SystemExit('TEST_NOT_ALLOWED_IN_TRAINING_ENTRY')
 rows=[r for r in rows if r.get('valid') and r['label']!='UNLABELED'];dest=Path(f['run_root'])/f'{a.kind}-{a.seed}'
 # Shared wall-clock deadline is registered once by batch launcher, never extended per fit.
 remaining=f['deadline_unix']-time.time()
 if remaining<=0:raise SystemExit('TOTAL_BUDGET_EXHAUSTED')
 if dest.exists():raise SystemExit('FIT_ALREADY_ATTEMPTED_NO_RETRY')
 if a.kind=='CrossEncoder':
  pairs=json.loads(Path(f['pairs']).read_text());fit_ce(a.seed,pairs,rows,dest,time.monotonic()+remaining)
 else:
  import numpy as np,mlx.core as mx
  gs=json.loads(Path(f['graphs']).read_text());vectors=np.load(f['vectors']);graphs={}
  for cid,g in gs.items():
   x=[]
   for n in g['nodes']:x.append(np.concatenate([vectors[hashlib.sha256(n['text'].encode()).hexdigest()],np.eye(5)[n['kind']]]))
   adj=np.zeros((16,len(x),len(x)),np.float32)
   for aa,b,r in g['edges']:adj[r,b,aa]+=1
   adj/=np.maximum(adj.sum(axis=2,keepdims=True),1)
   graphs[cid]={'x':mx.array(np.asarray(x,np.float32)),'adj':mx.array(adj),'edges':mx.array(np.asarray(g['edges'],np.int32).reshape(-1,3)),**{k:g[k] for k in ['ids','candidate_indices','request_indices']}}
  fit_graph(a.kind,a.seed,graphs,rows,dest,time.monotonic()+remaining)
if __name__=='__main__':main()
