import json,sys,hashlib,shutil,collections,random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.irac_application.aligned_v2_split import split,coverage
from legal_bench.irac_application.aligned_v2_runtime import atomic_json
R=Path('outputs/gnn-irac-aligned-v2');ST=['SUPPORTED','REFUTED','UNRESOLVED']
def main():
 if (R/'freeze/manifest.json').exists():raise ValueError('ALREADY_FROZEN')
 ps=[]
 for path in sorted((R/'graphs').glob('*.json')):
  g=json.loads(path.read_text());cid=str(g['case_id']);s=json.loads((R/'sources'/f'{cid}.json').read_text());rp=R/'references'/f'{cid}.json';rs={r['unit_id']:r for r in json.loads(rp.read_text())['tests']} if rp.exists() else {};units=g['prediction_units'];m=[rs.get(u['id'],{}).get('supervision_mask',False) for u in units]
  ps.append({'package_id':cid,'group_id':s['group_id'],'family':s['family'],'units':units,'labels':[ST.index(rs[u['id']]['status']) if mask else 0 for u,mask in zip(units,m)],'mask':m})
 folds=split(ps);cov=coverage(ps,folds);atomic_json(R/'freeze/splits.json',folds);atomic_json(R/'freeze/split-coverage.json',cov);atomic_json(R/'freeze/packages.json',ps)
 if not cov['primary_count']:atomic_json(R/'training-status.json',{'status':'NO_CASE_VARYING_PRIMARY_SUPERVISION','fits':0});return
 specs=[];weights=[]
 for f in folds:
  train=[p for p in ps if p['group_id'] in f['fit_groups'] and any(p['mask'])]
  ng=len({p['group_id'] for p in train})
  for p in train:
   issues={u['claim_id'] for u,m in zip(p['units'],p['mask']) if m};npack=sum(q['group_id']==p['group_id'] for q in train)
   for u,m in zip(p['units'],p['mask']):
    if m:
     n=sum(v['claim_id']==u['claim_id'] and mm for v,mm in zip(p['units'],p['mask']));weights.append({'fold':f['fold'],'unit_id':u['id'],'epoch_objective_weight':1/ng/npack/len(issues)/n,'note':'Minibatch group mean; shuffle fixed by seed.'})
  for method,kind,a in [('Flat','Flat',False),('Flat-ANCO','Flat',True),('R-GCN','Graph',False),('R-GCN-ANCO','Graph',True)]:
   for seed in [20261007,20261008,20261009]:specs.append({'id':f'{method}-fold{f["fold"]}-seed{seed}','method':method,'kind':kind,'anco':a,'seed':seed,'fold':f['fold'],'epochs':100,'early_stopping':False,'optimizer':'AdamW','lr':.001,'weight_decay':.0001,'dropout':.1,'hidden':64,'layers':2,'bases':4,'batch_size':4})
 atomic_json(R/'freeze/run-order.json',specs);atomic_json(R/'freeze/loss-weights.json',weights)
 atomic_json(R/'freeze/evaluation.json',{'primary':'same-test case variation in both fit and held-out plus seen state; determined before predictions','secondary':'all other admitted units separately; masked not scored','review_max':6,'review_selection':'priority different binding predictions; between-method disagreement; predicted definite against input opposition; persistent unresolved; reserve last slot deterministic random seed20261007','no_historical_outcome_accuracy':True,'reference':'MODEL_GENERATED_WITH_SOURCE_REVIEW_NOT_HUMAN_GOLD','fits_max':len(specs),'no_new_web_legal_answers':True})
 files=[]
 for folder in ['sources','templates','bindings','graphs','references','input-payloads','tasks','freeze','text-cache']:
  files += [p for p in (R/folder).rglob('*') if p.is_file()]
 code=list(Path('legal_bench/irac_application').glob('*.py'))+list(Path('scripts').glob('irac_aligned_v2*.py'))+[Path('scripts/repository_bridge.py')]
 for p in code:
  dest=R/'freeze/code'/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);files.append(dest)
 files+=code+[R/'runtime.json',R/'preparation-policy.json',R/'preparation-coverage.json']
 atomic_json(R/'freeze/manifest.json',{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files});print('frozen',len(ps),'packages',cov['primary_count'],'primary',len(specs),'fits')
if __name__=='__main__':main()
