#!/usr/bin/env python3
"""Recover saved predictions only. Never retrain, synthesize an answer or repair weights."""
import sys,json,hashlib,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.irac_application.aligned_tasks import ROOT,put
from legal_bench.irac_application.aligned_train import metrics
LABELS=['SUPPORTED','REFUTED','UNRESOLVED']
def main():
    splits=json.loads((ROOT/'freeze/splits.json').read_text());manifest=json.loads((ROOT/'input-manifest.json').read_text());groups={str(r['case_id']):r['group_id'] for r in manifest};audit=[]
    for p in sorted((ROOT/'training').glob('*-seed*.json')):
        raw=json.loads(p.read_text());m=re.fullmatch(r'(.*)-fold(\d+)-seed(\d+)',p.stem);method,fold,seed=m.group(1),int(m.group(2)),int(m.group(3));expected={c for c,g in groups.items() if g in splits[fold]['test_groups']};files=list((ROOT/'analysis'/p.stem).glob('*.json'));found={q.stem for q in files}
        if raw.get('status')!='TECHNICAL_FAILURE' or '[save_safetensors] Failed to open file' not in raw.get('error','') or found!=expected:raise ValueError('NOT_A_COMPLETE_SAVED_PREDICTION_SET:'+str(p))
        rows=[];evidence={}
        for q in sorted(files):
            d=json.loads(q.read_text());ref=json.loads((ROOT/'references-admitted-v2'/q.name).read_text());byid={t['test_id']:t for t in ref['tests']};evidence[str(q)]=hashlib.sha256(q.read_bytes()).hexdigest()
            for t in d['tests']:
                rr=byid[t['test_id']];prob=t['prediction']['probabilities'];assert len(prob)==3
                rows.append(dict(package_id=q.stem,group_id=groups[q.stem],test_id=t['test_id'],probabilities=prob,label=LABELS.index(rr['status']) if rr['supervision_mask'] else None,supervision_mask=rr['supervision_mask']))
        out=dict(status='PREDICTIONS_RECOVERED_FROM_SAVED_ANALYSIS',original_run_status=raw['status'],training_artifact_status='WEIGHTS_AND_FIT_LOG_UNAVAILABLE',method=method,fold=fold,seed=seed,rows=rows,metrics=metrics(rows),seconds_observed=raw['seconds'],source_hashes=evidence,not_retrained=True,limitations=['Optimizer history, selected epoch, parameter delta and peak MLX memory were not saved; cannot reconstruct them.','Original run remains a technical failure with answer null. Recovered predictions are a separate evidence product, not a successful checkpoint run.'])
        put(ROOT/'training-recovered'/p.name,out);audit.append(dict(run=p.stem,prediction_packages=len(files),status=out['status']))
    put(ROOT/'engineering/artifact-recovery.json',dict(root_cause='scripts/irac_aligned_train.py attempts model.save_weights before ensuring weights directory exists; exception path drops fit log.',runs=audit,extra_fits=0,original_failures_preserved=True,fix='For any future authorized run, create and test artifact directories before fitting and write fit log before optional weight export. No frozen training code was changed or rerun.'))
if __name__=='__main__':main()
