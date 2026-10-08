#!/usr/bin/env python3
"""Frozen four-method comparison. Refuse unreviewed/newly changed inputs."""
import sys,json,hashlib,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from legal_bench.irac_application.aligned_models import tensorize
from legal_bench.irac_application.aligned_train import fit,prior_fit,metrics,stratified_group_split
from legal_bench.irac_application.aligned_tasks import ROOT,put
from legal_bench.irac_application.aligned_analysis import render
LABELS=['SUPPORTED','REFUTED','UNRESOLVED']
def load(use_anco):
    vectors=np.load(ROOT/'text-cache/vectors.npz');out=[]
    for p in sorted((ROOT/'graphs').glob('*.json')):
        g=json.loads(p.read_text());cid=str(g['case_id']);rp=ROOT/'references-admitted-v2'/f'{cid}.json'
        if not rp.exists():continue
        refs=json.loads(rp.read_text());rows={r['test_id']:r for r in refs['tests']}
        embeddings={n['id']:vectors[hashlib.sha256(n['text'].encode()).hexdigest()] for n in g['nodes']};t=tensorize(g,embeddings,use_anco)
        material=json.loads((ROOT/'sources'/f'{cid}.json').read_text())
        ids=t['condition_ids'];mask=[rows.get(i,{}).get('supervision_mask',False) and rows[i]['status'] in LABELS for i in ids]
        labels=[LABELS.index(rows[i]['status']) if m else 0 for i,m in zip(ids,mask)]
        out.append(dict(package_id=cid,group_id=material['group_id'],family=material['family'],stage=material['target_stage'],tensors=t,labels=labels,mask=mask,template_condition_ids=ids))
    return out

def main():
    manifest=json.loads((ROOT/'freeze/manifest.json').read_text())
    for path,d in manifest.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=d:raise ValueError('FROZEN_INPUT_CHANGED:'+path)
    packs=load(False);folds=json.loads((ROOT/'freeze/splits.json').read_text());cfg=json.loads((ROOT/'protocol.json').read_text())['training']
    for fold in folds:
        prior=prior_fit([p for p in packs if p['group_id'] in fold['fit_groups']]);prior_rows=[]
        for p in packs:
            if p['group_id'] not in fold['test_groups']:continue
            for i,c in enumerate(p['template_condition_ids']):prior_rows.append(dict(package_id=p['package_id'],group_id=p['group_id'],test_id=c,probabilities=prior['per_condition'].get(c,prior['fallback']),label=p['labels'][i] if p['mask'][i] else None,supervision_mask=p['mask'][i]))
        put(ROOT/'training'/f"prior-fold{fold['fold']}.json",dict(prior=prior,rows=prior_rows,metrics=metrics(prior_rows)))
        for method,kind,anco in [('Flat','Flat',False),('Flat-ANCO','Flat',True),('R-GCN','Graph',False),('R-GCN-ANCO','Graph',True)]:
            ps=load(anco);train=[p for p in ps if p['group_id'] in fold['fit_groups']];val=[p for p in ps if p['group_id'] in fold['validation_groups']];test=[p for p in ps if p['group_id'] in fold['test_groups']]
            for seed in cfg['seeds']:
                run=ROOT/'training'/f"{method}-fold{fold['fold']}-seed{seed}.json"
                if run.exists():continue
                if len(list((ROOT/'training').glob('*-seed*.json')))>=36:raise ValueError('FIT_BUDGET')
                if not any(any(p['mask']) for p in train):put(run,dict(status='NO_TRAINING_LABELS',answer=None));continue
                t0=time.perf_counter()
                try:
                    model,log=fit(kind,train,val,seed,epochs=100,patience=10);rows=[]
                    for p in test:
                        import mlx.core as mx
                        probs=np.array(mx.softmax(model(p['tensors']),axis=1)).tolist()
                        for i,c in enumerate(p['template_condition_ids']):rows.append(dict(package_id=p['package_id'],group_id=p['group_id'],test_id=c,probabilities=probs[i],label=p['labels'][i] if p['mask'][i] else None,supervision_mask=p['mask'][i]))
                        graph=json.loads((ROOT/'graphs'/f"{p['package_id']}.json").read_text())
                        prediction={c:dict(status=LABELS[int(np.argmax(probs[i]))],probabilities=probs[i]) for i,c in enumerate(p['template_condition_ids'])}
                        put(ROOT/'analysis'/run.stem/f"{p['package_id']}.json",render(graph,prediction))
                    dest=ROOT/'weights'/run.with_suffix('.safetensors').name;model.save_weights(str(dest))
                    put(run,dict(status='OK',method=method,log=log,rows=rows,metrics=metrics(rows)))
                except Exception as e:put(run,dict(status='TECHNICAL_FAILURE',answer=None,error=repr(e),seconds=time.perf_counter()-t0))
if __name__=='__main__':main()
