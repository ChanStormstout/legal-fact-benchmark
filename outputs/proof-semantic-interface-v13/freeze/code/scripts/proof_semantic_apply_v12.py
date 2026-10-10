#!/usr/bin/env python3
"""Apply a cached/reloaded model's use predictions to the same raw candidate graph.
Only use status changes; no reference, evidence, premise truth, or legal approval is added.
"""
import argparse,json,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.proof_semantic_run_v12 import run
LABELS=('USABLE','UNUSABLE','UNRESOLVED')
def apply(snapshot,predictions,case_id):
 result=copy.deepcopy(snapshot);p={x['key']:x for x in predictions}
 for u in result.get('model_uses',{}).values():
  key=case_id+'::'+u['raw_use_id'];row=p.get(key)
  u['raw_proposal_label']=u['label']
  if row is None:u['label']='UNRESOLVED';u['prediction_status']='NOT_SCORED';continue
  probs=row['probabilities']
  import math
  if len(probs)!=3 or any(not math.isfinite(x) or x<0 for x in probs) or abs(sum(probs)-1)>1e-4:raise ValueError('INVALID_PROBABILITIES')
  u['label']=LABELS[max(range(3),key=lambda i:probs[i])];u['probabilities']=probs;u['prediction_status']='MODEL_PREDICTION_NOT_APPROVAL'
 return result
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--proposal-dir',required=True);ap.add_argument('--predictions',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();p=Path(a.proposal_dir);read=lambda f:json.loads(Path(f).read_text());s=read(p/'input-snapshot.json');s=apply(s,read(a.predictions),s['case_id']);run(s,read(p/'candidates.json'),read(p/'requests.json'),a.out)
