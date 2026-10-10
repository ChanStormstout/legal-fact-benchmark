"""Frozen cached pool, state supervision, common search and one grouped fit batch."""
import sys,json,copy,itertools,time,hashlib,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.proof_search_delivery_v11 import OUT as R,BASE,read,save,prepare_case,run_case
from legal_bench.proof_carrying.search_v11 import search,simple_scores,state_features,rule_goals
from legal_bench.proof_carrying.contracts import byte_hash

def eligible(cid):
 cs=read(R/'prepared'/cid/'candidates.json');allowed={e['id'] for e in read(R/'prepared'/cid/'eligibility.json') if not e['errors']};return [c for c in cs if c['id'] in allowed]
def verify():
 f=read(R/'freeze.json')
 for p,h in {**f['method_hashes'],**f['input_hashes']}.items():
  if byte_hash(Path(p))!=h:raise ValueError('FROZEN_CHANGED:'+p)

def pool_and_supervision():
 verify();cfg=read(R/'protocol.json');rows=[];supervision={};diag=[]
 for cid in cfg['cases']:
  prep=prepare_case(cid);rules=prep[0];qs=read(BASE/'inputs'/cid/'requests.json');cs=eligible(cid)
  rows.append(run_case(cid,'pool',prep));oracle=read(R/'results/pool'/cid/'oracle.json');negative=read(R/'prepared'/cid/'negative-use-review.json');states=[];conflicts=[]
  for q in qs:
   paths=[set(p['members']) for p in oracle['valid_paths'] if p['request']==q['id']];unique=[]
   for p in paths:
    if p not in unique:unique.append(p)
   selections=[frozenset()]
   for path in sorted(unique,key=lambda p:(len(p),sorted(p))):
    # Empty state, prefixes, then fixed cardinality/ID subsets, up to32 per request.
    order=sorted(path)
    for n in range(1,len(order)+1):
     s=frozenset(order[:n])
     if s not in selections:selections.append(s)
    for n in range(1,len(order)):
     for sub in itertools.combinations(order,n):
      s=frozenset(sub)
      if s not in selections:selections.append(s)
      if len(selections)>=cfg['states_per_request']:break
     if len(selections)>=cfg['states_per_request']:break
    if len(selections)>=cfg['states_per_request']:break
   for chosen in selections[:cfg['states_per_request']]:
    if len(chosen)>=6:continue
    feasible=[p for p in unique if len(p|set(chosen))<=6];pos=set().union(*(p-set(chosen) for p in feasible)) if feasible else set();goals=rule_goals(q,rules);neg={c['id'] for c in cs if c['id'] in negative and c['rule_ref'] in goals and c['id'] not in chosen}
    both=pos&neg
    if both:conflicts.append({'request':q['id'],'selected':sorted(chosen),'ids':sorted(both),'handling':'MASK_BOTH_PENDING_SEMANTIC_REVIEW'})
    pos-=both;neg-=both;pairs=list(itertools.islice(itertools.product(sorted(pos),sorted(neg)),cfg['pairs_per_state']))
    state={'request':q['id'],'selected':sorted(chosen),'remaining_budget':6-len(chosen),'positive':sorted(pos),'negative':sorted(neg),'unknown':[c['id'] for c in cs if c['id'] not in pos|neg|set(chosen)],'pairs':pairs,'positive_basis':'EXISTS_CHECKED_ROUTE_UNDER_RESEARCH_POLICY_NOT_LEGAL_GOLD','negative_basis':'VERSIONED_SPECIFIC_SLOT_NONAPPLICABILITY_NOT_REFERENCE_COMPLEMENT'};states.append(state)
  save(R/'supervision'/f'{cid}.json',{'states':states,'conflicts':conflicts,'enumeration_gaps':read(R/'results/pool'/cid/'derivation.json')['gaps'],'group':cid});supervision[cid]=states
  selection=search(cs,rules,qs,6,lambda q,s,b,f:simple_scores(f));rows.append(run_case(cid,'Simple',prep,selection))
  delivered=read(R/'results/Simple'/cid/'analysis.json');simple={q['id'] for q in delivered['requests'] if q['answer']=='TRUE'}
  diag.append({'case':cid,'known_budgeted':oracle['covered_requests'],'simple_true':sorted(simple),'missed_known':sorted(set(oracle['covered_requests'])-simple),'state_count':len(states),'pair_states':sum(bool(s['pairs']) for s in states),'pair_count':sum(len(s['pairs']) for s in states),'conflicts':conflicts,'all_eligible_count':len(cs)})
 save(R/'common-comparison.json',rows);save(R/'supervision/coverage.json',diag)
 gate={'remaining_known_selection_headroom':any(d['missed_known'] for d in diag),'training_folds':[]}
 for held in cfg['folds']:
  active=[c for c in cfg['cases'] if c not in held and any(s['pairs'] for s in supervision[c])];gate['training_folds'].append({'heldout':held,'contributing_train_groups':active,'has_pairs':bool(active)})
 gate['run_learned']=gate['remaining_known_selection_headroom'] and all(x['has_pairs'] for x in gate['training_folds']);gate['interpretation']='Operational bounded comparison, not a statistical sample-size guarantee.'
 save(R/'supervision/gate.json',gate);save(R/'freeze/data-training.json',{'hashes':{str(p):byte_hash(p) for p in (R/'supervision').glob('*.json')},'folds':cfg['folds'],'config':cfg});print(json.dumps(gate))

def train_and_deliver():
 verify();cfg=read(R/'protocol.json');gate=read(R/'supervision/gate.json')
 if not gate['run_learned']:
  save(R/'training-skipped.json',{'reason':'NO_KNOWN_HEADROOM_OR_NO_CONFIRMED_PAIRS','gate':gate});print('Skipped without random-weight comparison');return
 import numpy as np,mlx.core as mx
 from legal_bench.proof_carrying.state_ranker_v11 import base_data,state_tensor,fit
 for p,h in read(R/'freeze/data-training.json')['hashes'].items():assert byte_hash(Path(p))==h
 vectors=np.load(BASE/'encoding/candidate/vectors.npz');data={};examples={};prepared={};queries={};css={};graphcost=[]
 for cid in cfg['cases']:
  start=time.perf_counter();prep=prepare_case(cid);prepared[cid]=prep;rules,facts=prep[:2];cs=eligible(cid);css[cid]=cs;qs=read(BASE/'inputs'/cid/'requests.json');queries[cid]={q['id']:q for q in qs};data[cid]=base_data(facts,rules,cs,qs,vectors,prep[4]);examples[cid]=[]
  for e in read(R/'supervision'/f'{cid}.json')['states']:
   if not e['pairs']:continue
   features=state_features(cs,rules,queries[cid][e['request']],e['selected'],6);examples[cid].append({**e,'tensor':state_tensor(data[cid],features,e['request']),'pair_indices':[(data[cid]['ids'].index(a),data[cid]['ids'].index(b)) for a,b in e['pairs']]})
  graphcost.append({'case':cid,'seconds':time.perf_counter()-start,'nodes':data[cid]['node_count'],'edges_including_computational_reverse':data[cid]['edge_count'],'feature_width':data[cid]['x'].shape[1],'states':len(examples[cid])})
 save(R/'graph-cost.json',graphcost);deadline=time.perf_counter()+cfg['training_wall_budget_seconds'];rows=[]
 for fold,held in enumerate(cfg['folds']):
  train={k:d for k,d in data.items() if k not in held}
  for seed in cfg['seeds']:
   for kind in ('Flat','RGCN'):
    name=f'{kind}-fold{fold}-seed{seed}';dest=R/'training'/name
    try:m=fit(kind,seed,train,examples,dest,epochs=cfg['epochs'],deadline=deadline)
    except Exception as exc:
     save(R/'training-failure.json',{'fit':name,'stage':'TRAINING_EXPORT','reason':str(exc),'traceback':traceback.format_exc(),'remaining':'SKIPPED','no_retry':True});save(R/'learned-comparison.json',rows);return
    for cid in held:
     started=time.perf_counter()
     def score(q,selected,budget,features):
      values=np.array(m(data[cid],state_tensor(data[cid],features,q['id']),q['id']));return dict(zip(data[cid]['ids'],map(float,values)))
     selection=search(css[cid],prepared[cid][0],list(queries[cid].values()),6,score);selection['inference_seconds']=time.perf_counter()-started
     # Predictions and state trace saved before certificate export or other failure.
     save(dest/'predictions'/f'{cid}.json',selection);rows.append(run_case(cid,name,prepared[cid],selection))
 save(R/'learned-comparison.json',rows);print(json.dumps({'fits':12,'heldout_deliveries':len(rows)}))
if __name__=='__main__':
 if sys.argv[1]=='pool':pool_and_supervision()
 elif sys.argv[1]=='train':train_and_deliver()
