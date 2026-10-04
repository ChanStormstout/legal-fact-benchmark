#!/usr/bin/env python3
"""One frozen six-case grouped development run. No model API access."""
import sys,json,time,hashlib,random,datetime,shutil,importlib.metadata
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1 import rgcn_development_v2 as g,rgcn_train_v2 as train,legal_rule_support_study as pack
from mlx.utils import tree_flatten
import mlx.core as mx
R=Path('outputs/rgcn-ranking-development-06');OLD=Path('outputs/legal-rule-support-study-02')
def rd(p):return json.loads(p.read_text())
def save(name,x):
 p=R/name;p.parent.mkdir(parents=True,exist_ok=True)
 body=json.dumps(x,ensure_ascii=False,indent=2)+'\n' if not isinstance(x,str) else x
 if p.exists():
  if not (R/'training-freeze.json').exists() and p.read_text()==body:return
  raise FileExistsError(p)
 p.write_text(body)
def quote_ok(q,text):return bool(q) and q in text

def prepare():
 units=rd(R/'sources/laws.json');um={u['id']:u for u in units};samples=rd(R/'sources/samples.json');laws=rd(R/'law-proposals.json');rejectlaws=[]
 for i in range(1,5):
  reviews=rd(R/('parsed/LAWREV%02d.json'%i))['reviews'];rm={(x['unit_id'],x['condition_id']):x for x in reviews}
  for law in rd(R/('parsed/LAW%02d.json'%i))['units']:
   for c in law['conditions']:
    rev=rm.get((law['unit_id'],c['id']),{})
    if rev.get('decision')!='SUPPORTED' or not quote_ok(rev.get('quote'),um[law['unit_id']]['text']):rejectlaws.append(law['unit_id']+'::'+c['id'])
 raw={};labels={};graphs={};audits={};rankings={}
 for i,s in enumerate(samples,1):
  cid=s['case_id'];source=rd(R/('sources/'+cid+'.json'));refs={x['id']:x['text'] for x in source['segments']};p=rd(R/('parsed/GRAPH%02d.json'%i));assert p['case_id']==cid
  if {a['unit_id'] for a in p['alignments']}!=set(um):raise ValueError('ALIGNMENT_COVERAGE '+cid)
  grev=rd(R/('parsed/GREV%02d.json'%i));assert grev['case_id']==cid
  rejected=rejectlaws+[x['id'] for x in grev['rejections']]
  graph=g.make_graph(p,laws,source,units,rejected);graphs[cid]=graph;save('graphs/'+cid+'.json',graph)
  ranks=rd(OLD/('retrieval/'+cid+'/result.json'))['rankings']['A'];rankings[cid]=ranks;raw[cid]=g.numeric(graph,ranks,units)
  use=rd(R/('parsed/USE%02d.json'%i));prefs=rd(R/('parsed/PREF%02d.json'%i));rev=rd(R/('parsed/REVIEW%02d.json'%i));assert use['case_id']==prefs['case_id']==rev['case_id']==cid
  ur={x['unit_id']:x for x in rev['use_reviews']};pr={(x['a'],x['b']):x for x in rev['preference_reviews']};validuses=[];validprefs=[];excluded=[]
  for x in use['uses']:
   rr=ur.get(x['unit_id'],{});u=um[x['unit_id']]
   if rr.get('decision')=='SUPPORTED' and quote_ok(x.get('law_quote'),u['text']) and quote_ok(rr.get('law_quote'),u['text']) and all(k in refs for k in x['case_refs']+rr['case_refs']):validuses.append(x)
   else:excluded.append(dict(kind='use',record=x,review=rr))
  for x in prefs['preferences']:
   rr=pr.get((x['a'],x['b']),{});decision=x['decision']
   checks=rr.get('decision')=='SUPPORTED' and quote_ok(x.get('a_quote'),um[x['a']]['text']) and quote_ok(x.get('b_quote'),um[x['b']]['text']) and any(quote_ok(rr.get('law_quote'),um[y]['text']) for y in [x['a'],x['b']]) and all(k in refs for k in x['case_refs']+rr.get('case_refs',[]))
   if checks and decision in ['A','B']:
    pos,neg=(x['a'],x['b']) if decision=='A' else (x['b'],x['a']);validprefs.append(dict(preferred=pos,other=neg,source=x,review=rr))
   else:excluded.append(dict(kind='preference',record=x,review=rr,reason='dispute/location/non-directional; not a negative label'))
  labels[cid]=dict(uses=validuses,preferences=validprefs,excluded=excluded,reference_type='MODEL_GENERATED_SOURCE_REVIEW_NOT_HUMAN_GOLD');save('labels/'+cid+'.json',labels[cid])
 return samples,units,raw,labels,graphs,rankings

def main():
 if (R/'training-freeze.json').exists():raise FileExistsError('Already frozen; do not rerun')
 samples,units,raw,labels,graphs,rankings=prepare();ids=[s['case_id'] for s in samples];uid=[u['id'] for u in units];config=rd(R/'protocol.json')
 files=list((R/'tasks').glob('*.txt'))+[R/'execution-wrapper.txt',R/'final-execution-wrapper.txt',R/'evaluation-rules.json',R/'implementation-notes.txt',Path('tests/test_rgcn_development_v2.py')]+list((R/'parsed').glob('*.json'))+list((R/'sources').glob('*.json'))+list((R/'graphs').glob('*.json'))+list((R/'labels').glob('*.json'))+[R/'protocol.json',Path(__file__)]+[Path('legal_bench/rules_verdict_v1')/x for x in ['rgcn_development_v2.py','rgcn_train_v2.py','legal_rule_support_study.py','rule_retrieval_v21.py','authority_index.py','retrieve.py']]
 for path in files:
  if path.suffix=='.py':
   dest=R/'freeze/code'/path.resolve().relative_to(Path.cwd());dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
 save('environment.json',dict(python=sys.version,executable=sys.executable,numpy=np.__version__,mlx=importlib.metadata.version('mlx')))
 save('training-freeze.json',dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),config=config,hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},groups={c:c for c in ids},group_limits='No known duplicate; broader associations unconfirmed',seeds=config['seeds'],no_labels_in_graph_features=True,steps=200,kind='EXPOSED_DEVELOPMENT_GROUPED_CHECK_NOT_INDEPENDENT'))
 allrows=[];start=time.monotonic()
 for held in ids:
  training=[c for c in ids if c!=held];data,scaler=train.fold_data(raw,training)
  pp={c:[(uid.index(p['preferred']),uid.index(p['other'])) for p in labels[c]['preferences']] for c in training};pp={c:p for c,p in pp.items() if p}
  save('folds/'+held+'/scaler.json',scaler)
  for seed in config['seeds']:
   for kind in ['B','C','C0']:
    prefix='folds/'+held+'/'+str(seed)+'-'+kind;t=time.monotonic()
    if not pp:save(prefix+'-failure.json',dict(status='NO_VALID_TRAINING_PREFERENCE',answer=None));continue
    try:
     model,log=train.fit(kind,data,pp,seed,steps=200);scores=np.array(model(data[held])).astype(float).tolist();log.update(seconds=time.monotonic()-t,held_case=held,seed=seed,peak_active_bytes=int(mx.get_peak_memory()),leave_out_preferences_used_for_training=False)
     order=sorted(range(len(uid)),key=lambda k:(-scores[k],k));ranking=[dict(id=uid[k],score=scores[k]) for k in order]
     mx.savez(str(R/(prefix+'-weights.npz')),**dict(tree_flatten(model.parameters())))
     save(prefix+'-train.json',log);save(prefix+'-ranking.json',ranking)
     if kind=='B':save(prefix+'-coefficients.json',dict(zip(g.Z_NAMES,np.array(model.linear.weight).reshape(-1).astype(float).tolist())))
     allrows.append(dict(case_id=held,method=kind,seed=seed,status='OK',ranking=ranking,seconds=log['seconds']))
    except Exception as e:
     save(prefix+'-failure.json',dict(status='TRAINING_ERROR',error=repr(e),answer=None));allrows.append(dict(case_id=held,method=kind,seed=seed,status='TRAINING_ERROR',answer=None))
  a=rankings[held];allrows.append(dict(case_id=held,method='A',seed=None,status='OK',ranking=a))
  z=raw[held]['z'];scores=g.fixed_scores(z);order=sorted(range(len(uid)),key=lambda k:(-float(scores[k]),k));allrows.append(dict(case_id=held,method='B-fixed',seed=None,status='OK',ranking=[dict(id=uid[k],score=float(scores[k])) for k in order]))
 metrics=[];tasks={};slots=[]
 for row in allrows:
  if row['status']!='OK':continue
  cid=row['case_id'];ranks={x['id']:i for i,x in enumerate(row['ranking'],1)};prefs=labels[cid]['preferences'];agree=sum(ranks[p['preferred']]<ranks[p['other']] for p in prefs)
  selected=pack.select(row['ranking'],units,pack.PRIMARY_CONFIG,mandatory=['LAW:S02:DRC14:1b']);known=[x for x in labels[cid]['uses'] if x['category'] in ['DIRECT','EXCEPTION_COUNTER']];sup=set(selected['selected_ids'])
  key=cid+'/'+str(row['seed'])+'-'+row['method'];save('selections/'+key+'.json',selected)
  rr=dict(case_id=cid,method=row['method'],seed=row['seed'],preference_agreement_n=agree,preference_den=len(prefs),known_use_delivered=sum(x['unit_id'] in sup for x in known),known_use_total=len(known),selected_ids=selected['selected_ids'],characters=selected['legal_characters'],ranking=row['ranking']);metrics.append(rr)
  if row['method'] in ['A','B','C'] and row['seed'] in [None,config['downstream_primary_seed']]:
   sample=next(s for s in samples if s['case_id']==cid);text=pack.prompt(rd(R/('sources/'+cid+'.json')),selected['units'],sample['question']);h=hashlib.sha256(text.encode()).hexdigest()
   if h not in tasks:
    taskid='ANS%02d'%(len(tasks)+1);tasks[h]=dict(id=taskid,case_id=cid,sha256=h,methods=[],replicate=0);save('tasks/'+taskid+'.txt',text)
   tasks[h]['methods'].append(row['method']);slots.append(dict(case_id=cid,method=row['method'],id=tasks[h]['id'],sha256=h))
 # Prespecified repeats, reverse no answer-based choice. Same inputs shared in base only.
 varied=[c for c in ids if len({s['sha256'] for s in slots if s['case_id']==c})>1]
 chosen=random.Random(20261004).sample(varied,min(2,len(varied)))
 repeats=[]
 for c in chosen:
  for method in ['A','C']:
   item=next((s for s in slots if s['case_id']==c and s['method']==method),None)
   if item:
    tid='ANS%02d'%(len(tasks)+len(repeats)+1);save('tasks/'+tid+'.txt',(R/('tasks/'+item['id']+'.txt')).read_text());repeats.append(dict(id=tid,case_id=c,sha256=item['sha256'],methods=[method],replicate=1))
 save('ranking-results.json',metrics);save('training-runs.json',allrows);save('answer-order.json',list(tasks.values())+repeats);save('answer-slots.json',slots);save('compute-cost.json',dict(seconds=time.monotonic()-start,training_runs=sum(x['method'] in ['B','C','C0'] and x['status']=='OK' for x in allrows),actual_unique_basic=len(tasks),repeats=len(repeats),failure_count=sum(x['status']!='OK' for x in allrows)))
 print('Finished real fits; unique answer count:',len(tasks)+len(repeats))
if __name__=='__main__':main()
