"""Versioned actual training entry. Freeze check precedes each scheduled fit."""
import sys,json,hashlib,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import mlx.core as mx
from legal_bench.irac_application.aligned_v2_models import tensorize,ApplicationModel
from legal_bench.irac_application.aligned_v2_train import fit,prior_fit,metrics
from legal_bench.irac_application.aligned_v2_runtime import atomic_json,run_schedule
from legal_bench.irac_application.aligned_v2 import render
R=Path('outputs/gnn-irac-aligned-v2');LABELS=['SUPPORTED','REFUTED','UNRESOLVED']
def read(p):return json.loads(p.read_text())
def load(use_anco=False):
 vectors=np.load(R/'text-cache/vectors.npz');out=[]
 for path in sorted((R/'graphs').glob('*.json')):
  g=read(path);cid=str(g['case_id']);rp=R/'references'/f'{cid}.json'
  rows={x['unit_id']:x for x in read(rp)['tests']} if rp.exists() else {};source=read(R/'sources'/f'{cid}.json');um={u['id']:u for u in g['prediction_units']}
  d=tensorize(g,{n['id']:vectors[hashlib.sha256(n['text'].encode()).hexdigest()] for n in g['nodes']},use_anco);ids=d['condition_ids'];mask=[rows.get(u,{}).get('supervision_mask',False) for u in ids]
  out.append({'package_id':cid,'group_id':source['group_id'],'family':source['family'],'units':[um[u] for u in ids],'issue_ids':[um[u]['claim_id'] for u in ids],'labels':[LABELS.index(rows[u]['status']) if m else 0 for u,m in zip(ids,mask)],'mask':mask,'template_condition_ids':[um[u]['test_id'] for u in ids],'tensors':d})
 return out

def verify_frozen():
 for path,h in read(R/'freeze/manifest.json').items():
  if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=h:raise ValueError('FROZEN_INPUT_CHANGED:'+path)
def predict(model,ps):
 rows=[]
 for p in ps:
  probs=np.array(mx.softmax(model(p['tensors']),axis=1)).tolist()
  for i,u in enumerate(p['units']):rows.append({'package_id':p['package_id'],'group_id':p['group_id'],'unit_id':u['id'],'test_id':u['test_id'],'binding_id':u['binding_id'],'probabilities':probs[i],'label':p['labels'][i] if p['mask'][i] else None,'supervision_mask':p['mask'][i]})
 return rows

def callbacks(spec):
 verify_frozen();ps=load(spec['anco']);fold=next(f for f in read(R/'freeze/splits.json') if f['fold']==spec['fold']);train=[p for p in ps if p['group_id'] in fold['fit_groups']];test=[p for p in ps if p['group_id'] in fold['test_groups']]
 def pred(m):return {'rows':predict(m,test)}
 def verify(path,saved):
  loaded=ApplicationModel(spec['kind'],train[0]['tensors']['x'].shape[1]);loaded.load_weights(str(path));loaded.eval();again=predict(loaded,test)
  diff=max((abs(a-b) for x,y in zip(saved['rows'],again) for a,b in zip(x['probabilities'],y['probabilities'])),default=0.)
  if diff>1e-6:raise ValueError('WEIGHT_READBACK_PREDICTION_MISMATCH')
  return {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'max_probability_difference':diff,'readable':True}
 return dict(fit_call=lambda:fit(spec['kind'],train,[],spec['seed'],epochs=spec['epochs'],patience=10,progress=lambda log:atomic_json(R/'training'/f"{spec['id']}-progress.json",log)),predict_call=pred,export_call=lambda m,p:m.save_weights(str(p)),verify_call=verify)
def main():
 verify_frozen();specs=read(R/'freeze/run-order.json');packs=load(False);folds=read(R/'freeze/splits.json')
 for f in folds:
  dest=R/'predictions'/f"prior-fold{f['fold']}.json"
  if dest.exists():continue
  pri=prior_fit([p for p in packs if p['group_id'] in f['fit_groups']]);rows=[]
  for p in packs:
   if p['group_id'] not in f['test_groups']:continue
   for i,u in enumerate(p['units']):rows.append({'package_id':p['package_id'],'group_id':p['group_id'],'unit_id':u['id'],'test_id':u['test_id'],'binding_id':u['binding_id'],'probabilities':pri['per_condition'].get(u['test_id'],pri['fallback']),'label':p['labels'][i] if p['mask'][i] else None,'supervision_mask':p['mask'][i]})
  atomic_json(dest,{'prior':pri,'rows':rows})
 result=run_schedule(R,specs,callbacks);atomic_json(R/'training-status.json',result);print(result)
 # Render from saved predictions only; persistence errors here do not erase fits.
 for p in sorted((R/'predictions').glob('*.json')):
  rows=read(p)['rows']
  for cid in sorted({r['package_id'] for r in rows}):
   pred={r['unit_id']:{'status':LABELS[int(np.argmax(r['probabilities']))],'probabilities':r['probabilities']} for r in rows if r['package_id']==cid}
   atomic_json(R/'analysis'/p.stem/f'{cid}.json',render(read(R/'graphs'/f'{cid}.json'),pred))
if __name__=='__main__':main()
