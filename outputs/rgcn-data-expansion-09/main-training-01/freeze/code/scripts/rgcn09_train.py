"""One fixed27-case S/B/C training, two seeds; old six-case development only."""
import sys,json,copy,time,hashlib,shutil,datetime,importlib.metadata,csv
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import mlx.core as mx
from mlx.utils import tree_flatten
from legal_bench.rules_verdict_v1 import rgcn_use_v2 as use, rgcn_train_v2 as tr, rgcn_development_v3 as graph, legal_rule_support_study as pack, authority_index
from scripts.rgcn08_run import evaluate
R=Path('outputs/rgcn-data-expansion-09/main-training-01'); B=R.parent
I=B/'continuation-03/imports/final-01'; D=Path('outputs/rgcn-ranking-development-06'); OLD=Path('outputs/rgcn-ranking-diagnostic-07/pilot')
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,x):
 p=R/name;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError(p)
 p.write_text(x if isinstance(x,str) else json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def augment_dev(g,units,conditions):
 """Add source-only new authorities; missing case alignments remain UNKNOWN."""
 g=copy.deepcopy(g);existing={n['id'] for n in g['nodes']};oldids=set(g['validlinks']);newids={u['id'] for u in units}-oldids
 empty={'case_id':g['case_id'],'needs':[],'objects':[],'facts':[],'relations':[],'alignments':[]}
 lawg=graph.make_graph(empty,[x for x in conditions if x['unit_id'] in newids],{'segments':[]},units)
 for n in lawg['nodes']:
  if n['id'] not in existing:g['nodes'].append(n);existing.add(n['id'])
 for e in lawg['edges']:
  if e not in g['edges']:g['edges'].append(e)
 for uid in [u['id'] for u in units if u['id'] in newids]:
  g['validlinks'][uid]=[];g['alignments'].append({'unit_id':uid,'scope':'UNKNOWN','state':'UNKNOWN','links':[],'coverage_limit':'NO_CASE_ALIGNMENT_ANNOTATION_FOR_NEW_AUTHORITY'})
 g['quarantine']+=lawg['quarantine'];return g

def prepare():
 units=read(B/'authority-pool/laws.json');uid=[u['id'] for u in units];split=read(B/'continuation-03/split-manifest.json')['cases'];trainids=[x['case_id'] for x in split if x['split']=='TRAIN'];dev=[x['case_id'] for x in split if x['split']=='DEVELOPMENT'];sealed=[x['case_id'] for x in split if x['split']=='SEALED_TEST']
 assert len(uid)==30 and len(set(uid))==30 and len(trainids)==27 and len(dev)==6 and len(sealed)==8
 groups={s:{x['group_id'] for x in split if x['split']==s} for s in ['TRAIN','DEVELOPMENT','SEALED_TEST']};assert not(groups['TRAIN']&groups['DEVELOPMENT'] or groups['TRAIN']&groups['SEALED_TEST'] or groups['DEVELOPMENT']&groups['SEALED_TEST'])
 lawdocs={str(u.get('source',{}).get('document_id')) for u in units};assert not lawdocs&set(trainids+dev+sealed)
 config=read(B/'continuation-01/main-training-protocol.json');cfg=config['reuse_v08_settings'];cfg.update(methods=['S','B','C'],train_ids=trainids,dev_ids=dev,sealed_ids=sealed,units=30,max_fits=6,max_training_seconds=1800,web_calls=0)
 save('protocol.json',{'config':cfg,'authorization':'27-case partial labels approved, count and duplicate hold no longer absolute gate','deviation_case':'125596702 accepts8 unchanged anchor-passing records,22 remain isolated; not single-pass','dev_limit':'old14 annotated; new16 law nodes/conditions present but case alignment UNKNOWN; evaluation references only old14. Not complete30-source validation.','score_scope':'source-anchored model-reference coverage; not accuracy or exhaustive recall','no_hyperparameter_search':True})
 save('split-manifest.json',split);save('sources-laws.json',units)
 inputs=[];supervision={};devrefs={}
 for cid in trainids:
  oldfile=OLD/'labels'/f'{cid}.json';uses=read(oldfile)['uses'] if oldfile.exists() else []
  if oldfile.exists():inputs.append(oldfile)
  lp=I/'labels'/f'{cid}.json' if cid!='125596702' else B/'continuation-03/duplicate-label-format-audit.json';lab=read(lp);uses+=lab['known'];inputs.append(lp)
  labels={'uses':uses,'preferences':[]};targets=use.supervision(labels,uid);assert targets and len({p[0] for p in targets})==len(targets)
  supervision[cid]=targets;save(f'labels/{cid}.json',{'uses':uses,'isolated':lab['isolated'],'unknown':lab['unknown'],'missing':lab['missing'],'duplicate_deviation':cid=='125596702'})
  npz=I/'numeric'/f'{cid}.npz';meta=read(npz.with_suffix('.json'));assert meta['unit_ids']==uid and meta['labels_in_input']==False;inputs.extend([npz,npz.with_suffix('.json')]);dest=R/'numeric'/f'{cid}.npz';dest.parent.mkdir(exist_ok=True);shutil.copyfile(npz,dest)
 conditions=read(B/'continuation-01/freeze/source-condition-proposals.json');inputs+=[B/'authority-pool/laws.json',B/'continuation-01/freeze/source-condition-proposals.json',B/'continuation-03/split-manifest.json']
 authority_index.build(units,R/'index.sqlite');samples={x['case_id']:x for x in read(D/'sources/samples.json')}
 for cid in dev:
  gf=D/'graphs'/f'{cid}.json';sf=D/'sources'/f'{cid}.json';lf=D/'labels'/f'{cid}.json';inputs.extend([gf,sf,lf,D/'sources/samples.json']);g=augment_dev(read(gf),units,conditions);save(f'dev-graphs/{cid}.json',g)
  source=read(sf);query=samples[cid]['question']+'\n'+'\n'.join(x['text'] for x in source['segments']);ranking=authority_index.search(R/'index.sqlite',query,40);save(f'retrieval/{cid}.json',{'query':query,'ranking':ranking,'new_alignment_unknown_ids':uid[14:]})
  raw=graph.numeric(g,ranking,units);np.savez_compressed(R/'numeric'/f'{cid}.npz',**raw);devrefs[cid]=read(lf);save(f'dev-reference/{cid}.json',devrefs[cid])
 save('supervision.json',supervision)
 raw={c:dict(np.load(R/'numeric'/f'{c}.npz')) for c in trainids+dev};assert all(d['z'].shape==(30,18) and np.isfinite(d['z']).all() for d in raw.values());_,scale=tr.fold_data(raw,trainids);save('scaler.json',scale)
 save('preflight.json',{'train_cases':len(trainids),'dev_cases':len(dev),'known_training_uses':sum(len(t) for t in supervision.values()),'case_counts':{c:len(t) for c,t in supervision.items()},'labels_feature_separated':True,'known_cross_split_group_overlap':False,'broader_association_unconfirmed':True,'target_ids_in_authority_documents':[],'sealed_content_read':False,'dev_new16_alignment':'UNKNOWN_NOT_NEGATIVE','dev_reference_counts':{c:len(use.supervision(devrefs[c],uid)) for c in dev}})
 codes=[Path(__file__),Path('legal_bench/rules_verdict_v1/rgcn_use_v2.py'),Path('legal_bench/rules_verdict_v1/rgcn_use_v1.py'),Path('legal_bench/rules_verdict_v1/rgcn_train_v2.py'),Path('legal_bench/rules_verdict_v1/rgcn_development_v3.py'),Path('legal_bench/rules_verdict_v1/legal_rule_support_study.py'),Path('scripts/rgcn08_run.py'),Path('tests/test_rgcn09_train.py')]
 for p in codes:
  dst=R/'freeze/code'/p.resolve().relative_to(Path.cwd());dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
 save('environment.json',{'python':sys.version,'numpy':np.__version__,'mlx':importlib.metadata.version('mlx'),'executable':sys.executable})
 inputs=list(dict.fromkeys(inputs+codes+list((R/'numeric').glob('*.npz'))+[R/'protocol.json',R/'supervision.json',R/'scaler.json',R/'test-results.txt']))
 save('training-freeze.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':{str(p):sha(p) for p in inputs},'max_fits':6,'order':[[s,k] for s in cfg['seeds'] for k in cfg['methods']]})
 print(read(R/'preflight.json'),flush=True)

def run():
 freeze=read(R/'training-freeze.json');assert all(sha(p)==h for p,h in freeze['files'].items())
 cfg=read(R/'protocol.json')['config'];units=read(R/'sources-laws.json');uid=[u['id'] for u in units];ids=cfg['train_ids']+cfg['dev_ids'];raw={c:dict(np.load(R/'numeric'/f'{c}.npz')) for c in ids};data,scale=tr.fold_data(raw,cfg['train_ids']);assert scale==read(R/'scaler.json');targets=read(R/'supervision.json');assert set(targets)==set(cfg['train_ids'])
 start=time.monotonic();metrics=[];runs=[]
 for seed,kind in freeze['order']:
  prefix=f'runs/{seed}-{kind}'; marker=R/(prefix+'/started.json')
  if marker.exists():raise RuntimeError('ALREADY_STARTED_NO_AUTOMATIC_REFIT')
  if time.monotonic()-start>cfg['max_training_seconds']:break
  save(prefix+'/started.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat()});st=time.monotonic()
  try:
   mx.reset_peak_memory();model,log=use.fit(kind,data,targets,seed,cfg['updates'],cfg['lr'],cfg['l2'],units=30)
   log.update(seconds=time.monotonic()-st,peak_active_bytes=int(mx.get_peak_memory()));save(prefix+'/train.json',log);mx.savez(str(R/prefix/'weights.npz'),**dict(tree_flatten(model.parameters())))
   for cid in cfg['dev_ids']:
    probs,scores=use.probabilities_and_scores(model(data[cid]));pred=probs.argmax(1);ranking=[{'id':uid[i],'score':float(scores[i])} for i in sorted(range(30),key=lambda i:(-scores[i],i))];selection=pack.select(ranking,units,pack.PRIMARY_CONFIG,mandatory=cfg['mandatory']);assert selection['legal_characters']<=20000
    row={'case_id':cid,'method':kind,'seed':seed,'status':'OK','ranking':ranking};ref=read(R/'dev-reference'/f'{cid}.json');metric=evaluate(row,ref,units,selection,pred);metric['material_sha256']=hashlib.sha256(pack.render(selection['units']).encode()).hexdigest();metric['not_accuracy']=True;metrics.append(metric);save(prefix+f'/{cid}.json',dict(row,probabilities=probs.tolist(),selection=selection,metrics=metric))
   runs.append(dict(method=kind,seed=seed,status='OK',seconds=log['seconds'],peak_active_bytes=log['peak_active_bytes']));print(runs[-1],flush=True)
  except Exception as e:
   failure=dict(method=kind,seed=seed,status='FAILED',error=repr(e),answer=None);save(prefix+'/failure.json',failure);runs.append(failure);print(failure,flush=True)
 save('training-results.json',runs);save('selection-results.json',metrics);save('cost.json',{'seconds':time.monotonic()-start,'fits':len(runs),'training_calls':len(runs),'web_calls':0,'sealed_evaluation':False})
 with (R/'comparison.csv').open('w') as f:
  fields=['case_id','method','seed','core_delivered','irrelevant_selected','unlabeled_selected','legal_characters','material_sha256'];w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(metrics)
if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
