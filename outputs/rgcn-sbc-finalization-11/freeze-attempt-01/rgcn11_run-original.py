"""Unique V11 readiness/freeze guarded method-major six-fit closeout."""
import sys,json,hashlib,copy,shutil,datetime,time,importlib.metadata
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from legal_bench.rules_verdict_v1 import family_overlay_v11 as over,rgcn_development_v4 as graph,authority_use_v10 as cats,authority_evaluation_v10 as ev,legal_material_v10 as pack
R=Path('outputs/rgcn-sbc-finalization-11');V=Path('outputs/rgcn-dev-contract-repair-10')
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
 p=R/p;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError(p)
 p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def prepared_reviews(path):
 results={};failures=[]
 for task in read(R/'task-ledger.json'):
  if task['path']!=path:continue
  name=task['id'];assert (R/'web'/f'{name}.completed.json').exists() or (R/'web'/f'{name}.failure.json').exists(),'WAIT_FOR_TASK '+name
  f=R/'web'/f'{name}.raw.json'
  if not f.exists():failures.append({'task':name,'reason':'NO_COMPLETE_PARSEABLE_OUTPUT'});continue
  try:
   raw=read(f);assert raw['task_id']==name
   seen=set();blocked=set();expected={(c,u) for c in task['cases'] for u in over.FAMILY}
   for row in raw['reviews']:
    key=(str(row['case_id']),row['unit_id']);assert key in expected
    if key in seen:blocked.add(key);results.pop(key,None);failures.append({'task':name,'position':key,'reason':'DUPLICATE_POSITION'});continue
    seen.add(key)
    if key not in blocked:results[key]=row
  except (AssertionError,KeyError,TypeError,ValueError) as e:
   for key in [(c,u) for c in task['cases'] for u in over.FAMILY]:results.pop(key,None)
   failures.append({'task':name,'reason':str(e)})
 return results,failures

def build():
 f=read(R/'preparation-freeze.json');assert all(sha(k)==v for k,v in f['files'].items());cfg=read(R/'protocol.json');units=read(V/'sources-laws.json');conds=read(V/'source-conditions.json');L,lf=prepared_reviews('L');G,gf=prepared_reviews('G');labels={};lt=[];gt=[];ch=[];counts=[];identity=[]
 save('sources-laws.json',units);save('source-conditions.json',conds)
 for cid in cfg['train']+cfg['dev']:
  src=read(V/'sources'/f'{cid}.json');old=read(V/'labels'/f'{cid}.json');p=read(V/'graph-inputs'/f'{cid}.json');rej=read(V/'rejections'/f'{cid}.json')
  identity.append({'case_id':cid,'case_id_matches':str(src['case_id'])==cid,'all_segment_document_ids':all(str(s.get('source_document',cid))==cid for s in src['segments']),'all_segment_prefixes':all(s['id'].startswith('IK-'+cid+':') for s in src['segments']),'unchanged_allowed_source_sha256':sha(V/'sources'/f'{cid}.json'),'no_new_target_material':True})
  labels[cid],l,lch=over.label_overlay(old,{u:L.get((cid,u)) for u in over.FAMILY},src,units);p2,masks,g,gch=over.graph_overlay(p,{u:G.get((cid,u)) for u in over.FAMILY},src,rej);lt+=l;gt+=g;ch+=lch+gch
  outg=graph.make_graph(p2,conds,src,units,masks);ret=read(V/'retrieval'/f'{cid}.json');numeric=graph.numeric(outg,ret['ranking'],units)
  assert numeric['z'].shape==(30,18) and all(np.isfinite(a).all() for a in numeric.values())
  for folder,value in [('labels',labels[cid]),('graph-inputs',p2),('graphs',outg),('rejections',masks)]:save(f'{folder}/{cid}.json',value)
  for folder in ['sources','retrieval']:
   dst=R/folder/f'{cid}.json';dst.parent.mkdir(exist_ok=True);shutil.copyfile(V/folder/f'{cid}.json',dst)
  (R/'numeric').mkdir(exist_ok=True);np.savez_compressed(R/'numeric'/f'{cid}.npz',**numeric)
  counts.append({'case_id':cid,'split':'TRAIN' if cid in cfg['train'] else 'DEV','states':{s:sum(x['state']==s for x in labels[cid]['slots'].values()) for s in ['KNOWN','UNKNOWN','ISOLATED','UNPROCESSED','REVIEW_NOT_COMPLETED']},'known_categories':{s:sum(x['state']=='KNOWN' and x['canonical_category']==s for x in labels[cid]['slots'].values()) for s in ['CORE','BACKGROUND','IRRELEVANT']},'nodes':len(outg['nodes']),'edges':len(outg['edges'])})
 save('L-dispositions.json',lt);save('G-dispositions.json',gt);save('overlay-changes.json',ch);save('cohort-counts.json',counts);save('review-import-failures.json',lf+gf);save('source-identity-evidence.json',identity)
 independent=True
 for task in read(R/'task-ledger.json'):
  material=json.loads(Path(task['file']).read_text().split('\nMATERIAL\n',1)[1].rsplit('\nEND_OF_INPUT ',1)[0]);cases=material['cases']
  if task['path']=='L':independent &= all('graph_proposal' not in c and 'alignments' not in c for c in cases)
  else:independent &= all('old_proposals' not in c for c in cases)
  independent &= all('ranking' not in c and 'selection' not in c for c in cases)
 readiness=over.gate(cfg,labels,lt,gt,identity_ok=all(all(x[k] for k in ['case_id_matches','all_segment_document_ids','all_segment_prefixes']) for x in identity),freeze_paths_isolated=independent)
 readiness.update(review_import_failures=lf+gf,source_identity_file='source-identity-evidence.json',new_unique_version='RGCN_SBC_FINALIZATION_11',preparation_freeze_sha256=sha(R/'preparation-freeze.json'),old_v10_gate_preserved=True,no_review_zero_error_requirement=True)
 save('readiness.json',readiness);print(readiness)

def freeze():
 import mlx.core as mx
 from legal_bench.rules_verdict_v1 import rgcn_train_v2 as tr
 cfg=read(R/'protocol.json');assert read(R/'readiness.json')['training_allowed'];ids=cfg['train']+cfg['dev'];units=read(R/'sources-laws.json');uid=[u['id'] for u in units];raw={c:dict(np.load(R/'numeric'/f'{c}.npz')) for c in ids};targets={}
 for c in cfg['train']:
  slots=read(R/'labels'/f'{c}.json')['slots'];targets[c]=cats.targets([dict(s['record'],category=s['canonical_category']) for s in slots.values() if s['state']=='KNOWN'],uid)
 assert all(targets.values());_,scale=tr.fold_data(raw,cfg['train']);save('supervision.json',targets);save('scaler.json',scale)
 # Predeclare reference legal roles for interpretation, never used in training.
 roles=[];cm={c['unit_id']:c for c in read(R/'source-conditions.json')}
 for cid in cfg['dev']:
  for uid,s in read(R/'labels'/f'{cid}.json')['slots'].items():
   if s['state']=='KNOWN' and s['canonical_category']=='CORE':
    kinds=sorted({x['kind'] for x in cm[uid]['conditions']});roles.append({'case_id':cid,'unit_id':uid,'source_condition_kinds':kinds,'existing_use_reason':s['record']['reason'],'case_refs':s['record']['case_refs'],'equivalence':'NO_AUTOMATIC_INTERCHANGEABILITY; overlapping providers require substantive case comparison'})
 save('core-role-register.json',roles)
 codes=[Path('scripts/rgcn11_prepare.py'),Path(__file__),Path('scripts/rgcn11_report.py'),Path('tests/test_rgcn11_overlay.py')]+[Path('legal_bench/rules_verdict_v1')/(s+'.py') for s in ['family_overlay_v11','rgcn_use_v3','rgcn_train_v2','rgcn_development_v4','authority_use_v10','authority_evaluation_v10','coarse_label_v10','legal_material_v10','authority_index','source_location_v3']]
 files=codes+[R/p for p in ['protocol.json','criteria.json','sources-laws.json','source-conditions.json','supervision.json','scaler.json','readiness.json','L-dispositions.json','G-dispositions.json','overlay-changes.json','cohort-counts.json','source-identity-evidence.json','core-role-register.json','preparation-freeze.json']]
 for cid in ids:
  for d,ext in [('numeric','npz'),('labels','json'),('graph-inputs','json'),('graphs','json'),('sources','json'),('retrieval','json'),('rejections','json')]:files.append(R/d/f'{cid}.{ext}')
 for p in codes:
  dest=R/'freeze/code'/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 save('pretraining-freeze.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':{str(p):sha(p) for p in files},'config':cfg,'unique_readiness_path':str(R/'readiness.json'),'readiness_sha256':sha(R/'readiness.json'),'order':cfg['fit_order'],'no_sealed_content':True})
 save('environment.json',{'python':sys.version,'executable':sys.executable,'numpy':np.__version__,'mlx':importlib.metadata.version('mlx'),'training_framework':'MLX existing environment; no installation or model download'})
 print('freeze ready',sum(map(len,targets.values())))

def run():
 import mlx.core as mx
 from mlx.utils import tree_flatten
 from legal_bench.rules_verdict_v1 import rgcn_train_v2 as tr,rgcn_use_v3 as use
 f=read(R/'pretraining-freeze.json');assert all(sha(p)==h for p,h in f['files'].items()),'FROZEN_INPUT_CHANGED';assert f['unique_readiness_path']==str(R/'readiness.json') and sha(f['unique_readiness_path'])==f['readiness_sha256'] and read(f['unique_readiness_path'])['training_allowed']
 cfg=f['config'];settings=cfg['training'];units=read(R/'sources-laws.json');uid=[u['id'] for u in units];data,scale=tr.fold_data({c:dict(np.load(R/'numeric'/f'{c}.npz')) for c in cfg['train']+cfg['dev']},cfg['train']);assert scale==read(R/'scaler.json');targets=read(R/'supervision.json');rows=[];cost=[];start=time.monotonic();stop=False
 for kind,seed in f['order']:
  prefix=f'runs/{seed}-{kind}'
  if stop or time.monotonic()-start>settings['max_training_seconds']:
   stop=True;cost.append({'method':kind,'seed':seed,'status':'SKIPPED','reason':'PRIOR_TECHNICAL_FAILURE_OR_TOTAL_BUDGET'});continue
  save(prefix+'/started.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'freeze_sha256':sha(R/'pretraining-freeze.json'),'readiness_sha256':f['readiness_sha256']});t=time.monotonic()
  try:
   mx.reset_peak_memory();m,log=use.fit(kind,data,targets,seed,settings['updates'],settings['lr'],settings['l2'],units=30);log.update(seconds=time.monotonic()-t,peak_active_bytes=int(mx.get_peak_memory()));save(prefix+'/train.json',log);mx.savez(str(R/prefix/'weights.npz'),**dict(tree_flatten(m.parameters())))
   for cid in cfg['dev']:
    probs,scores=use.probabilities_and_scores(m(data[cid]));ranking=[{'id':uid[i],'score':float(scores[i])} for i in sorted(range(30),key=lambda i:(-scores[i],i))];sel=pack.select(ranking,units,pack.PRIMARY_CONFIG,mandatory=settings['mandatory']);assert sel['run_status']=='OK';slots=read(R/'labels'/f'{cid}.json')['slots'];metrics=ev.evaluate(cid,kind,seed,ranking,slots,units,sel,probs.argmax(1));metrics['material_sha256']=hashlib.sha256(pack.render(sel['units']).encode()).hexdigest();rows.append(metrics)
    save(prefix+f'/{cid}.json',{'status':'OK','ranking':ranking,'probabilities':probs.tolist(),'selection':sel,'metrics':metrics});dest=R/'materials'/f'{seed}-{kind}-{cid}.txt';dest.parent.mkdir(exist_ok=True);dest.write_text(pack.render(sel['units']))
   c={'method':kind,'seed':seed,'status':'OK','seconds':log['seconds'],'peak_active_bytes':log['peak_active_bytes']};del m
  except Exception as e:
   c={'method':kind,'seed':seed,'status':'FAILED','error':repr(e),'answer':None,'seconds':time.monotonic()-t};save(prefix+'/failure.json',c);stop=True
  cost.append(c);print(c,flush=True)
 save('selection-results.json',rows);save('training-results.json',cost);save('training-cost.json',{'seconds':time.monotonic()-start,'fits_completed':sum(c['status']=='OK' for c in cost),'fits_failed':sum(c['status']=='FAILED' for c in cost),'fits_skipped':sum(c['status']=='SKIPPED' for c in cost),'legal_answers':0,'sealed_read':False,'runs':cost})
if __name__=='__main__':{'build':build,'freeze':freeze,'run':run}[sys.argv[1]]()
