"""Saved ranking re-evaluation precedes one frozen six-fit existing S/B/C comparison."""
import sys,json,hashlib,shutil,time,datetime,importlib.metadata
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import mlx.core as mx
from mlx.utils import tree_flatten
from legal_bench.rules_verdict_v1 import rgcn_train_v2 as tr,rgcn_use_v3 as use,authority_evaluation_v10 as ev,legal_material_v10 as pack,authority_use_v10 as cats
R=Path('outputs/rgcn-dev-contract-repair-10');OLD=Path('outputs/rgcn-data-expansion-09/main-training-01')
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
 p=R/p;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError(p)
 p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def old_reference(cid,units):
 old=read(OLD/'dev-reference'/f'{cid}.json');out={u['id']:{'state':'UNPROCESSED'} for u in units};review=read(R/'labels'/f'{cid}.json')['slots']
 for row in old['uses']:
  category=cats.normalize(row['category']);uid=row['unit_id']
  if row['category']=='NO_USE':
   rv=review[uid]
   category='IRRELEVANT' if rv['state']=='KNOWN' and rv['canonical_category']=='IRRELEVANT' else 'UNKNOWN'
  out[uid]={'state':'UNKNOWN' if category=='UNKNOWN' else 'KNOWN','canonical_category':category}
 return out

def reevaluate():
 cfg=read(R/'protocol.json')['training_settings'];units=read(R/'sources-laws.json');allrows=[]
 for seed in cfg['seeds']:
  for kind in ['S','B','C']:
   for cid in cfg['dev_ids']:
    old=read(OLD/'runs'/f'{seed}-{kind}'/f'{cid}.json');ranking=old['ranking'];sel=pack.select(ranking,units,pack.PRIMARY_CONFIG,mandatory=cfg['mandatory']);newslots=read(R/'labels'/f'{cid}.json')['slots'];oldslots=old_reference(cid,units)
    controlled=ev.evaluate(cid,kind,seed,ranking,oldslots,units,sel);new=ev.evaluate(cid,kind,seed,ranking,newslots,units,sel,np.array(old['probabilities']).argmax(1));new['material_sha256']=hashlib.sha256(pack.render(sel['units']).encode()).hexdigest()
    row={'case_id':cid,'method':kind,'seed':seed,'legacy_metrics':old['metrics'],'same_historical_reference_fixed_mapping_material':controlled,'expanded_all30_reference':new,'old_selected_ids':old['selection']['selected_ids'],'new_selected_ids':sel['selected_ids'],'old_characters':old['selection']['legal_characters'],'new_characters':sel['legal_characters'],'ranking_changed':False,'no_fits':True}
    allrows.append(row)
 save('saved-ranking-reevaluation.json',allrows);print('saved ranks re-evaluated',len(allrows),flush=True)

def freeze():
 if not read(R/'readiness.json')['training_allowed']:
  raise RuntimeError('READINESS_CLOSED: preserve semantic disputes; six fits are not authorized by this gate')
 cfg=read(R/'protocol.json')['training_settings'];units=read(R/'sources-laws.json');uid=[u['id'] for u in units];targets={};ids=cfg['train_ids']+cfg['dev_ids'];raw={c:dict(np.load(R/'numeric'/f'{c}.npz')) for c in ids}
 for c in cfg['train_ids']:
  slots=read(R/'labels'/f'{c}.json')['slots'];rows=[dict(s['record'],category=s['canonical_category']) for s in slots.values() if s['state']=='KNOWN'];targets[c]=cats.targets(rows,uid)
 assert set(targets)==set(cfg['train_ids']) and all(targets.values()) and not set(cfg['sealed_ids'])&set(ids)
 _,scale=tr.fold_data(raw,cfg['train_ids']);save('supervision.json',targets);save('scaler.json',scale)
 codes=[Path(__file__),Path('scripts/rgcn10_import.py')]+[Path('legal_bench/rules_verdict_v1')/(s+'.py') for s in ['rgcn_use_v3','rgcn_train_v2','rgcn_development_v4','authority_use_v10','authority_evaluation_v10','coarse_label_v10','legal_material_v10','authority_index','source_location_v3']]
 for p in codes:
  dst=R/'freeze/code'/p;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
 files=codes+[R/'protocol.json',R/'sources-laws.json',R/'source-conditions.json',R/'supervision.json',R/'scaler.json',R/'readiness.json',R/'saved-ranking-reevaluation.json']
 for c in ids:
  files += [R/d/f'{c}.{ext}' for d,ext in [('numeric','npz'),('labels','json'),('graph-inputs','json'),('sources','json')]]
 save('training-freeze.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':{str(p):sha(p) for p in files},'order':[[s,k] for s in cfg['seeds'] for k in ['S','B','C']],'fits':6,'config':cfg,'sealed_content_read':False,'comparison':'existing implementations, not nested effects; no architecture change'})
 save('environment.json',{'python':sys.version,'numpy':np.__version__,'mlx':importlib.metadata.version('mlx'),'executable':sys.executable});print('freeze complete',sum(map(len,targets.values())),flush=True)

def run():
 f=read(R/'training-freeze.json');assert all(sha(p)==h for p,h in f['files'].items());assert read(R/'readiness.json')['training_allowed']
 cfg=f['config'];units=read(R/'sources-laws.json');uid=[u['id'] for u in units];ids=cfg['train_ids']+cfg['dev_ids'];data,_=tr.fold_data({c:dict(np.load(R/'numeric'/f'{c}.npz')) for c in ids},cfg['train_ids']);targets=read(R/'supervision.json');rows=[];costs=[];begin=time.monotonic()
 for seed,kind in f['order']:
  prefix=f'runs/{seed}-{kind}';assert not(R/prefix/'started.json').exists()
  if time.monotonic()-begin>cfg['max_training_seconds']:break
  save(prefix+'/started.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat()});start=time.monotonic()
  try:
   mx.reset_peak_memory();model,log=use.fit(kind,data,targets,seed,cfg['updates'],cfg['lr'],cfg['l2'],units=30);log.update(seconds=time.monotonic()-start,peak_active_bytes=int(mx.get_peak_memory()));save(prefix+'/train.json',log);mx.savez(str(R/prefix/'weights.npz'),**dict(tree_flatten(model.parameters())))
   for cid in cfg['dev_ids']:
    probs,scores=use.probabilities_and_scores(model(data[cid]));ranking=[{'id':uid[i],'score':float(scores[i])} for i in sorted(range(30),key=lambda i:(-scores[i],i))];sel=pack.select(ranking,units,pack.PRIMARY_CONFIG,mandatory=cfg['mandatory']);slots=read(R/'labels'/f'{cid}.json')['slots'];m=ev.evaluate(cid,kind,seed,ranking,slots,units,sel,probs.argmax(1));m['material_sha256']=hashlib.sha256(pack.render(sel['units']).encode()).hexdigest();rows.append(m);save(prefix+f'/{cid}.json',{'status':'OK','ranking':ranking,'probabilities':probs.tolist(),'selection':sel,'metrics':m})
   cost={'kind':kind,'seed':seed,'status':'OK','seconds':log['seconds'],'peak_active_bytes':log['peak_active_bytes']}
  except Exception as e:
   cost={'kind':kind,'seed':seed,'status':'FAILED','error':repr(e),'answer':None};save(prefix+'/failure.json',cost)
  costs.append(cost);print(cost,flush=True)
 save('selection-results.json',rows);save('training-results.json',costs);save('cost.json',{'seconds':time.monotonic()-begin,'fits':len(costs),'legal_answers':0,'sealed_used':False})
if __name__=='__main__':{'reevaluate':reevaluate,'freeze':freeze,'run':run}[sys.argv[1]]()
