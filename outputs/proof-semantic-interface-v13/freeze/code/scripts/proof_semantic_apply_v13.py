#!/usr/bin/env python3
"""Local V13 prediction delivery. Changes use class only; no reference binding/truth."""
import sys,json,argparse,copy,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.proof_semantic_run_v13 import run,read
CLASSES=('USABLE','UNUSABLE','UNRESOLVED')
def apply(snapshot,predictions):
 out=copy.deepcopy(snapshot);index={p['key']:p for p in predictions};audit=[]
 for key,u in out.get('model_uses',{}).items():
  pk=out['case_id']+'::'+u['raw_use_id'];p=index.get(pk)
  if p is None:
   audit.append({'use':key,'prediction':'NOT_SCORED','action':'RETAIN_RAW_P_NOT_EXCLUDE_CANDIDATE'});continue
  values=p.get('probabilities')
  if not isinstance(values,list) or len(values)!=3 or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):raise ValueError('INVALID_PREDICTION:'+pk)
  u['raw_P_label']=u['label'];u['label']=CLASSES[max(range(3),key=lambda i:values[i])];u['prediction_origin']='LEARNED_USE_CLASS_ONLY';audit.append({'use':key,'prediction':u['label'],'whole_premise_state_unchanged':True})
 out['prediction_delivery_audit']=audit;return out
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--snapshot',required=True);p.add_argument('--candidates',required=True);p.add_argument('--requests',required=True);p.add_argument('--predictions',required=True);p.add_argument('--out',required=True);a=p.parse_args()
 run(apply(read(a.snapshot),read(a.predictions)),read(a.candidates),read(a.requests),a.out)
