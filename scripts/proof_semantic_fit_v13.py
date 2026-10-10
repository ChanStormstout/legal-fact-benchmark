#!/usr/bin/env python3
"""Hash-pinned V13 one-fit entry. Closed gates cannot initialize a learner."""
import json,sys,time,argparse,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

def main():
    p=argparse.ArgumentParser();p.add_argument('--freeze',required=True);p.add_argument('--kind',choices=['Flat','RGCN','CrossEncoder'],required=True);p.add_argument('--seed',type=int,choices=[20261001,20261002,20261003],required=True);a=p.parse_args()
    freeze=json.loads(Path(a.freeze).read_text())
    # Evaluate gates before importing frameworks/loading any weights.
    if freeze.get('training_authorized_by_frozen_gates') is not True:
        raise SystemExit('V13_TRAINING_GATES_CLOSED')
    for name,digest in freeze['files'].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:raise SystemExit('FROZEN_INPUT_CHANGED:'+name)
    rows=json.loads(Path(freeze['rows']).read_text())
    if any(r['split'] not in ('TRAIN','DEV') for r in rows):raise SystemExit('TEST_OR_SEALED_NOT_ALLOWED')
    rows=[r for r in rows if r.get('valid') and r['label'] in ('USABLE','UNUSABLE','UNRESOLVED')]
    deadline=freeze['deadline_unix']-time.time()
    if deadline<=0:raise SystemExit('TOTAL_BUDGET_EXHAUSTED')
    dest=Path(freeze['run_root'])/f'{a.kind}-{a.seed}'
    if dest.exists():raise SystemExit('FIT_ALREADY_ATTEMPTED_NO_RETRY')
    from legal_bench.proof_carrying.semantic_fit_v13 import fit_ce,fit_graph
    inference_rows=json.loads(Path(freeze['inference_rows']).read_text())
    if any(r['split']!='DEV' for r in inference_rows):raise SystemExit('INFERENCE_POOL_MUST_BE_FROZEN_DEV')
    if a.kind=='CrossEncoder':
        pairs=json.loads(Path(freeze['pairs']).read_text());contexts=json.loads(Path(freeze['contexts']).read_text())
        for pair in pairs.values():pair['shared_case_context']=contexts[pair['shared_case_context_ref']]
        fit_ce(a.seed,pairs,rows,dest,time.monotonic()+deadline,inference_rows=inference_rows)
    else:
        import numpy as np,mlx.core as mx
        from legal_bench.proof_carrying.semantic_model_inputs_v13 import graph_arrays
        data=json.loads(Path(freeze['graphs']).read_text());plans=json.loads(Path(freeze['encoding_plan']).read_text());vectors=np.load(freeze['vectors']);graphs={}
        for cid,g in data.items():
            arrays=graph_arrays(g,plans[cid],vectors)
            graphs[cid]={k:mx.array(v) if k in ('x','adj','edges') else v for k,v in arrays.items()}
        fit_graph(a.kind,a.seed,graphs,rows,dest,time.monotonic()+deadline,inference_rows=inference_rows)
if __name__=='__main__':main()
