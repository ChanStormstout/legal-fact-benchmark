import sys,json,pathlib,collections,random,csv,re
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np
from legal_bench.irac_application.aligned_v2_train import metrics
from legal_bench.irac_application.aligned_v2_runtime import atomic_json
R=pathlib.Path('outputs/gnn-irac-aligned-v2');S=['SUPPORTED','REFUTED','UNRESOLVED']
def read(p):return json.loads(p.read_text())
def main():
 cov=read(R/'freeze/split-coverage.json');scope={(x['fold'],x['unit_id']):x['scope'] for x in cov['evaluation_scope']};allrows=[];per=collections.defaultdict(list)
 for p in sorted((R/'predictions').glob('*.json')):
  stem=p.stem;fold=int(re.search(r'fold(\d+)',stem).group(1));method=stem.split('-fold')[0];seed=int(stem.split('-seed')[1]) if '-seed' in stem else None
  for row in read(p)['rows']:
   row=dict(row,run=stem,fold=fold,method=method,seed=seed,evaluation_scope=scope[(fold,row['unit_id'])],predicted_status=S[int(np.argmax(row['probabilities']))]);allrows.append(row);per[(method,seed)].append(row)
 summary=[]
 for (method,seed),rows in per.items():
  primary=[x for x in rows if x['evaluation_scope']=='PRIMARY_CASE_VARIATION'];secondary=[x for x in rows if x['evaluation_scope']=='COVERAGE_OUTSIDE_DIAGNOSTIC']
  summary.append({'method':method,'seed':seed,'primary':metrics(primary),'outside':metrics(secondary),'all_admitted':metrics(rows)})
 atomic_json(R/'comparison.json',summary);atomic_json(R/'comparison-rows.json',allrows)
 with (R/'case-comparison.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['case','method','seed','scope','units','agreement','probability_loss'])
  for (method,seed),rows in per.items():
   for cid in sorted({x['package_id'] for x in rows}):
    for sc in ['PRIMARY_CASE_VARIATION','COVERAGE_OUTSIDE_DIAGNOSTIC']:
     a=[x for x in rows if x['package_id']==cid and x['evaluation_scope']==sc];m=metrics(a);w.writerow([cid,method,seed,sc,m['supervised_conditions'],m['dispute_mean_correct'],m['dispute_balanced_probability_loss']])
 claims=[]
 for p in (R/'analysis').glob('*/*.json'):
  d=read(p);claims.append({'run':p.parent.name,'case_id':d['case_id'],'claims':[c['status'] for c in d['claims']],'bindings':dict(collections.Counter(b['result']['status'] for b in d['bindings'])),'program_test_states':dict(collections.Counter(u['program_state']['status'] for u in d['units'])),'blocking':dict(collections.Counter(x['kind'] for b in d['bindings'] for x in b['join_limits']))})
 atomic_json(R/'analysis-summary.json',claims)
 # Choose before reading source-review conclusions; reserve one random package.
 cases=sorted({x['package_id'] for x in allrows});rank=[]
 for cid in cases:
  rs=[x for x in allrows if x['package_id']==cid and x['method']!='prior'];by=collections.defaultdict(set);unit=collections.defaultdict(set)
  for x in rs:by[(x['run'],x['test_id'])].add(x['predicted_status']);unit[x['unit_id']].add(x['predicted_status'])
  flags={'different_binding':any(len(s)>1 for s in by.values()),'method_disagreement':any(len(s)>1 for s in unit.values()),'definite_reference_opposition':any(x['predicted_status'] in S[:2] and x['label'] is not None and S[x['label']]!=x['predicted_status'] for x in rs),'persistent_unknown':any(x['predicted_status']=='UNRESOLVED' for x in rs)}
  rank.append((tuple(-int(flags[k]) for k in flags),cid,flags))
 rank.sort();selected=rank[:5];remaining=[x for x in rank if x not in selected];rng=random.Random(20261007)
 if remaining:selected.append(rng.choice(remaining))
 atomic_json(R/'source-review-selection.json',{'rule':read(R/'freeze/evaluation.json')['review_selection'],'seed':20261007,'selected':[{'case_id':cid,'flags':flags,'selection':'random reserve' if i==5 else 'priority'} for i,(_,cid,flags) in enumerate(selected)],'all_candidates':[{'case_id':cid,'flags':flags} for _,cid,flags in rank]})
 for _,cid,flags in selected:
  atomic_json(R/'review-dossiers'/f'{cid}.json',{'case_id':cid,'flags':flags,'sources':read(R/'sources'/f'{cid}.json'),'reference':read(R/'references'/f'{cid}.json'),'bindings':read(R/'bindings'/f'{cid}.json'),'predictions':[x for x in allrows if x['package_id']==cid]})
 print('rows',len(allrows),'review',[x[1] for x in selected]);print([(x['method'],x['seed'],x['primary']['dispute_mean_correct'],x['primary']['dispute_balanced_probability_loss']) for x in summary])
if __name__=='__main__':main()
