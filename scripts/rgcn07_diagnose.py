"""One bounded diagnostic: authority-only baseline and a content-preserving source repair."""
import sys,json,hashlib,shutil,time,datetime,importlib.util
from pathlib import Path
from collections import defaultdict
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx.utils import tree_flatten
from legal_bench.rules_verdict_v1 import rgcn_development_v3 as g,rgcn_train_v2 as t,legal_rule_support_study as pack
from legal_bench.rules_verdict_v1.source_location_v3 import locate_all,quote_supported_address
OLD=Path('outputs/rgcn-ranking-development-06');R=Path('outputs/rgcn-ranking-diagnostic-07/run1')
def rd(p):return json.loads(p.read_text())
def save(p,v):
 p=R/p;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError(p)
 p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
class Shared(nn.Module):
 def __init__(self,n):super().__init__();self.scores=mx.zeros((n,))
 def __call__(self):return self.scores

def fit_shared(prefs,n,seed):
 mx.random.seed(seed);m=Shared(n);opt=optim.Adam(.003)
 def loss(m):
  a=[]
  for pairs in prefs.values():
   if pairs:
    p=mx.array(pairs);s=m();a.append(mx.mean(mx.logaddexp(mx.array(0.),s[p[:,1]]-s[p[:,0]])))
  if not a:raise ValueError('NO_SUPERVISION')
  return mx.mean(mx.stack(a))+.001*mx.sum(m.scores**2)
 vg=nn.value_and_grad(m,loss);hist=[]
 for i in range(200):
  v,gr=vg(m);opt.update(m,gr);mx.eval(m.parameters(),opt.state,v);hist.append(float(v.item()))
 return m,{'loss':hist,'updates':200,'parameter_delta':float(mx.sqrt(mx.sum(m.scores**2)).item()),'trained_cases':list(prefs),'preferences':sum(map(len,prefs.values())),'seed':seed,'initialization':'all zero; convex authority-only scores; seeds intentionally identical'}

def main():
 if (R/'run-freeze.json').exists():raise RuntimeError('Frozen diagnostic exists; inspect, do not duplicate')
 units=rd(OLD/'sources/laws.json');uids=[u['id']for u in units];samples=rd(OLD/'sources/samples.json');ids=[s['case_id']for s in samples]
 # Reuse exact V06 prepare logic, changing only its output root, graph module, and quote locator.
 for directory in ['sources','parsed']:
  for p in (OLD/directory).glob('*.json'):
   dst=R/'repaired'/directory/p.name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
 shutil.copy2(OLD/'law-proposals.json',R/'repaired/law-proposals.json')
 spec=importlib.util.spec_from_file_location('v06prepare',Path('scripts/rgcn06_run.py'));mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 locations=[]
 def traced(q,text):
  result=locate_all(text,q);locations.append({'quote':q,'source_text_sha256':hashlib.sha256(text.encode()).hexdigest(),**result});return result['status']in ['EXACT','WHITESPACE_ONLY']
 mod.R=R/'repaired';mod.g=g;mod.quote_ok=traced
 _,_,raw,newlabels,graphs,ranks=mod.prepare()
 # Add graph field evidence addresses as well as label/review lookups.
 for cid in ids:
  src=rd(OLD/('sources/'+cid+'.json'));refs={x['id']:x['text']for x in src['segments']}
  p=rd(OLD/('parsed/GRAPH%02d.json'%(ids.index(cid)+1)))
  for x in p['facts']+p.get('relations',[]):
   for ref in x.get('refs',[]):
    if ref in refs:locations.append({'case_id':cid,'record_id':x['id'],'source_ref':ref,'quote':x.get('quote'),**locate_all(refs[ref],x.get('quote'))})
 for law in rd(OLD/'law-proposals.json'):
  text=next(u['text']for u in units if u['id']==law['unit_id'])
  for c in law['conditions']:locations.append({'unit_id':law['unit_id'],'record_id':c['id'],'quote':c.get('quote'),**locate_all(text,c.get('quote'))})
 save('location-audit.json',locations)
 oldlabels={c:rd(OLD/('labels/'+c+'.json'))for c in ids}
 pairs=defaultdict(list)
 for c,l in oldlabels.items():
  for p in l['preferences']:pairs[tuple(sorted([p['preferred'],p['other']]))].append({'case':c,'preferred':p['preferred'],'reason':p['source']['reason']})
 save('crosscase-preference-directions.json',{'only_observed_pairs':True,'pairs':[{'pair':list(k),'observed_cases':len(v),'directions':len({x['preferred']for x in v}),'records':v}for k,v in sorted(pairs.items())]})
 files=[Path(__file__),Path('legal_bench/rules_verdict_v1/rgcn_development_v3.py'),Path('legal_bench/rules_verdict_v1/source_location_v3.py'),Path('legal_bench/rules_verdict_v1/rgcn_train_v2.py'),Path('scripts/rgcn06_run.py'),R/'protocol.json']+list((R/'repaired').rglob('*.json'))
 save('run-freeze.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'hashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in files},'config':rd(R/'protocol.json'),'old_reference_target':'budget-mixed preference; no semantic relabeling','no_model_answers':True})
 for p in files[:5]:
  dst=R/'freeze/code'/p.resolve().relative_to(Path.cwd());dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
 results=[];start=time.monotonic()
 for version,labels,kinds in [('original',oldlabels,['S']),('repaired',newlabels,['S','B','C','C0'])]:
  for held in ids:
   trainids=[c for c in ids if c!=held];data,scale=t.fold_data(raw,trainids);save(f'{version}/folds/{held}/scaler.json',scale)
   prefs={c:[(uids.index(p['preferred']),uids.index(p['other']))for p in labels[c]['preferences']]for c in trainids}
   for seed in [20261004,20261005]:
    for kind in kinds:
     prefix=f'{version}/folds/{held}/{seed}-{kind}';st=time.monotonic()
     try:
      if kind=='S':m,log=fit_shared(prefs,len(uids),seed);scores=np.array(m()).tolist()
      else:m,log=t.fit(kind,data,prefs,seed);scores=np.array(m(data[held])).tolist()
      log['seconds']=time.monotonic()-st;save(prefix+'-train.json',log);mx.savez(str(R/(prefix+'-weights.npz')),**dict(tree_flatten(m.parameters())))
      ranking=[{'id':uids[i],'score':float(scores[i])}for i in sorted(range(len(uids)),key=lambda i:(-scores[i],i))]
      results.append(dict(version=version,case_id=held,method=kind,seed=seed,ranking=ranking,status='OK'))
     except Exception as e:results.append(dict(version=version,case_id=held,method=kind,seed=seed,status='FAILED',error=repr(e),answer=None))
   if version=='repaired':
    for name,ranking in [('A',ranks[held]),('B-fixed',[{'id':uids[i],'score':float(g.fixed_scores(raw[held]['z'])[i])}for i in sorted(range(len(uids)),key=lambda i:(-float(g.fixed_scores(raw[held]['z'])[i]),i))])]:results.append(dict(version=version,case_id=held,method=name,seed=None,ranking=ranking,status='OK'))
 save('training-results.json',results)
 metrics=[];oldmetrics=rd(OLD/'ranking-results.json')
 for row in results:
  if row['status']!='OK':continue
  c=row['case_id'];labels=oldlabels if row['version']=='original'else newlabels;rank={p['id']:i for i,p in enumerate(row['ranking'])};sel=pack.select(row['ranking'],units,pack.PRIMARY_CONFIG,mandatory=['LAW:S02:DRC14:1b']);save(f"{row['version']}/selections/{c}/{row['seed']}-{row['method']}.json",sel)
  def agreement(ps):return [sum(rank[p['preferred']]<rank[p['other']]for p in ps),len(ps)]
  known=[p for p in labels[c]['uses']if p['category']in ['DIRECT','EXCEPTION_COUNTER']];sample=next(s for s in samples if s['case_id']==c);text=pack.prompt(rd(OLD/('sources/'+c+'.json')),sel['units'],sample['question']);h=hashlib.sha256(text.encode()).hexdigest()
  ref=next(x for x in oldmetrics if x['case_id']==c and x['method']=='C'and x['seed']==20261004)
  metrics.append({k:row[k]for k in ['version','case_id','method','seed']}|{'agreement':agreement(labels[c]['preferences']),'agreement_on_original_labels':agreement(oldlabels[c]['preferences']),'known_delivery':[sum(x['unit_id']in sel['selected_ids']for x in known),len(known)],'selected_ids':sel['selected_ids'],'characters':sel['legal_characters'],'task_sha256':h,'same_set_as_original_C':set(sel['selected_ids'])==set(ref['selected_ids'])})
 save('comparison.json',metrics);save('cost.json',{'training_runs':sum(x['method']in ['S','B','C','C0']for x in results),'seconds':time.monotonic()-start,'web_calls':0,'failures':sum(x['status']!='OK'for x in results)})
 save('repair-delta.json',[dict(case_id=c,old_nodes=len(rd(OLD/('graphs/'+c+'.json'))['nodes']),new_nodes=len(graphs[c]['nodes']),old_uses=len(oldlabels[c]['uses']),new_uses=len(newlabels[c]['uses']),old_prefs=len(oldlabels[c]['preferences']),new_prefs=len(newlabels[c]['preferences']),new_conditions=sum(n['type']=='condition'for n in graphs[c]['nodes']))for c in ids])
 print(rd(R/'cost.json'))
if __name__=='__main__':main()
