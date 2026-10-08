#!/usr/bin/env python3
"""Single resumable study entry: prepare, encode, freeze, train, report."""
import argparse,json,hashlib,time,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
DEFAULT=ROOT/'outputs/gnn-irac-application-development-01'
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False))
def hashfile(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load_packages(root):
 import numpy as np
 from legal_bench.irac_application.application_models import tensorize
 vectors=np.load(root/'text-cache/vectors.npz');out=[]
 admitted=None
 if (root/'source-review-admission.json').exists():admitted={r['case_id'] for r in json.loads((root/'source-review-admission.json').read_text()) if r['input_admitted']}
 for p in sorted((root/'graphs').glob('*.json')):
  if admitted is not None and p.stem not in admitted:continue
  g=json.loads(p.read_text());meta=json.loads((root/'packages'/p.name).read_text());target=json.loads((root/'targets'/p.name).read_text())
  t=tensorize(g,{n['id']:vectors[hashlib.sha256(n['text'].encode()).hexdigest()] for n in g['nodes']})
  byid={r['condition_id']:r for r in target['adapted_targets']};ids=t['condition_ids'];r=[byid[i] for i in ids]
  out.append(dict(package_id=meta['package_id'],group_id=meta['group_id'],family=meta['family'],target_stage=meta['target_stage'],tensors=t,labels=[x['class_index'] if x['supervision_mask'] else -1 for x in r],mask=[x['supervision_mask'] for x in r],template_condition_ids=[meta['condition_templates'][i] for i in ids],condition_ids=ids))
 return out

def freeze(root):
 from legal_bench.irac_application.train_eval import grouped_split
 packages=load_packages(root)
 files=[p for d in ['inputs','targets','graphs','packages','templates'] for p in (root/d).glob('*.json')]
 files+=list((ROOT/'legal_bench/irac_application').glob('*.py'))+[Path(__file__)]+[ROOT/'legal_bench/rules_verdict_v1'/p for p in ['irac_native_schema_v1.py','irac_graph_builder_v1.py','irac_gate_v2.py']]
 files+=[root/p for p in ['scope-selection.json','construction-manifest.json','source-review-admission.json','template-review-audit.json','case-study-protocol.json','protocol-initial.json','dispute-groups-final.json']]
 files+=[ROOT/'tests/test_irac_application.py',ROOT/'tests/test_irac_native_v1.py']
 files+=[Path(r['source_path']) for r in json.loads((root/'construction-manifest.json').read_text())]
 files+=list((root/'tasks').glob('*.txt'))+list((root/'law-sources').glob('*.json'))
 files+=[root/'text-cache/encoder.json',root/'text-cache/encoding.json',root/'text-cache/vectors.npz']
 files=[(p if p.is_absolute() else ROOT/p).resolve() for p in files]
 cfg=json.loads((root/'protocol-initial.json').read_text());cfg['runtime']=json.loads((root/'engineering/runtime.json').read_text());cfg.update(status='FROZEN_BEFORE_REAL_FITS',actual_packages=len(packages),supervised_packages=sum(any(p['mask']) for p in packages),folds=grouped_split([p for p in packages if any(p['mask'])]),hashes={str(p.relative_to(ROOT)):hashfile(p) for p in files},scope='EXPOSED_DEVELOPMENT_RULE_GIVEN_RETROSPECTIVE_CONDITION_TARGETS_NOT_WIN_LOSE',no_test_early_stop=True,prior_smoothing=1,unknown_labels_not_negatives=True,actual_environment='MLX .runtime/qwen35-v1; E5 separate .runtime/irac-e5-v1')
 for p in files:
  if p.suffix=='.py':
   dest=root/'freeze/code'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
 save(root/'training-freeze.json',cfg)
 return cfg

def train(root):
 import numpy as np,mlx.core as mx
 from legal_bench.irac_application.train_eval import fit,prior_fit,metrics,paired_group_bootstrap
 cfg=json.loads((root/'training-freeze.json').read_text())
 for name,want in cfg['hashes'].items():
  if hashfile(ROOT/name)!=want:raise ValueError('FROZEN_FILE_CHANGED:'+name)
 packages=load_packages(root);runs=root/'training';runs.mkdir(exist_ok=True);weights=root/'weights';weights.mkdir(exist_ok=True);all_rows=[];logs=[]
 if not cfg['folds']:
  save(runs/'stop.json',dict(reason='FEWER_THAN_TWO_SUPERVISED_DISPUTES_NO_HOLDOUT_COMPARISON',training_runs=0));return
 for split in cfg['folds']:
  pick=lambda key:[p for p in packages if p['group_id'] in split[key]]
  tr,va,te=pick('fit_groups'),pick('validation_groups'),pick('test_groups')
  prior=prior_fit(tr)
  prior_rows=[]
  for p in te:
   for i,c in enumerate(p['condition_ids']):
    prior_rows.append(dict(method='P',seed=None,fold=split['fold'],package_id=p['package_id'],group_id=p['group_id'],family=p['family'],target_stage=p['target_stage'],condition_id=c,supervision_mask=p['mask'][i],label=p['labels'][i] if p['mask'][i] else None,probabilities=prior['per_condition'].get(p['template_condition_ids'][i],prior['fallback'])))
  save(runs/('fold%d-P.json'%split['fold']),dict(prior=prior,predictions=prior_rows));all_rows+=prior_rows
  for seed in [20261006,20261007,20261008]:
   for kind in ['Flat','Graph']:
    name='fold%d-%s-%d'%(split['fold'],kind,seed);path=runs/(name+'.json')
    if path.exists():
     old=json.loads(path.read_text());all_rows+=old['predictions'];logs.append(old['run']);continue
    t=time.perf_counter()
    try:
     model,run=fit(kind,tr,va,seed);rows=[]
     for p in te:
      probabilities=np.array(mx.softmax(model(p['tensors']),axis=-1))
      for i,c in enumerate(p['condition_ids']):rows.append(dict(method=kind,seed=seed,fold=split['fold'],package_id=p['package_id'],group_id=p['group_id'],family=p['family'],target_stage=p['target_stage'],condition_id=c,supervision_mask=p['mask'][i],label=p['labels'][i] if p['mask'][i] else None,probabilities=probabilities[i].tolist()))
     model.save_weights(str(weights/(name+'.npz')));run.update(status='OK',fold=split['fold']);save(path,dict(run=run,predictions=rows));all_rows+=rows;logs.append(run)
    except Exception as e:
     save(path,dict(run=dict(status='FAILED',method=kind,seed=seed,fold=split['fold'],error=str(e),seconds=time.perf_counter()-t),predictions=[]));raise
 summary={'P':metrics([r for r in all_rows if r['method']=='P'])}
 for kind in ['Flat','Graph']:
  summary[kind]={str(seed):metrics([r for r in all_rows if r['method']==kind and r['seed']==seed]) for seed in [20261006,20261007,20261008]}
 breakdown={}
 for method in ['P','Flat','Graph']:
  rr=[r for r in all_rows if r['method']==method and r['seed'] in [None,20261006]]
  breakdown[method]={field:{v:metrics([r for r in rr if r[field]==v]) for v in sorted({r[field] for r in rr})} for field in ['family','target_stage']}
 save(runs/'summary.json',dict(metrics=summary,breakdown_seed_20261006=breakdown,fits=len(logs),runs=logs,paired_bootstrap=paired_group_bootstrap(all_rows),development_only=True,not_human_gold=True))
 save(runs/'all-predictions.json',all_rows)
 print(json.dumps(summary,indent=2))
def main():
 parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','prepare-inputs','import-inputs','prepare-targets','prepare-reviews','admit','encode','freeze','train']);parser.add_argument('--root',type=Path,default=DEFAULT);a=parser.parse_args()
 if a.command=='prepare':
  from legal_bench.irac_application.corpus_inventory import prepare
  print(prepare(a.root))
 elif a.command in ['prepare-inputs','import-inputs','prepare-targets','prepare-reviews','admit']:
  from legal_bench.irac_application import data_tasks
  fn={'prepare-inputs':data_tasks.prepare_inputs,'import-inputs':data_tasks.import_inputs,'prepare-targets':data_tasks.prepare_targets,'prepare-reviews':data_tasks.prepare_reviews,'admit':data_tasks.admit_reviewed}[a.command]
  print(json.dumps(fn(a.root),ensure_ascii=False,indent=2))
 elif a.command=='encode':
  from legal_bench.irac_application.text_cache import encode
  print(encode(a.root))
 elif a.command=='freeze':print(freeze(a.root))
 else:train(a.root)
if __name__=='__main__':main()
