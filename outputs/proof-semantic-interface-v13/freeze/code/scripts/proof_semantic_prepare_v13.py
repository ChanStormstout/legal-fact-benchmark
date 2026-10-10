#!/usr/bin/env python3
"""V13 bounded TRAIN/DEV preparation, no TEST/SEALED paths are opened."""
import sys,json,copy,hashlib,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.semantic_interface_v13 import adapt,inputs
from scripts.proof_semantic_run_v13 import run,save
ROOT=Path('outputs/proof-semantic-interface-v13');OLD=Path('outputs/proof-semantic-search-v12/continuation-02')
def read(p):return json.loads(Path(p).read_text())
def main():
 rows=read(OLD/'supervision-35/rows.json');cases={}
 for r in rows:
  if r['split'] not in ('TRAIN','DEV'):continue
  cases.setdefault(r['case_id'],r)
 summary=[]
 for cid,row in cases.items():
  case=read(Path('outputs/proof-semantic-search-v12/cohort')/cid/'case.json');assert case['split'] in ('TRAIN','DEV')
  proposal=read(Path(row['proposal_dir'])/'input-snapshot.json')['raw_proposal'];s,c,q=adapt(case,proposal);features=inputs(case,proposal);d=ROOT/'inputs-v13-02'/cid;d.mkdir(parents=True,exist_ok=True)
  for n,x in [('case.json',case),('proposal.json',proposal),('snapshot.json',s),('candidates.json',c),('requests.json',q),('model-information.json',features)]:(save(d/n,x) if not (d/n).exists() else None)
  if row['split']=='DEV':
   base=read(Path(row['proposal_dir'])/'nonlearning/checked.json');save(ROOT/'replays-supervised'/cid/'old.json',base)
   run(s,c,q,ROOT/'replays-supervised'/cid/'repaired-P')
   diagnostic=copy.deepcopy(s);labels={r['use_id']:r['label'] for r in rows if r['case_id']==cid and r['valid'] and r['label'] in ('USABLE','UNUSABLE','UNRESOLVED')}
   for u in diagnostic['model_uses'].values():
    if u['raw_use_id'] in labels:u['label']=labels[u['raw_use_id']]
   diagnostic['diagnostic_reference_use_labels_only']=True;run(diagnostic,c,q,ROOT/'replays-supervised'/cid/'oracle-use-only')
   a=read(ROOT/'replays-supervised'/cid/'repaired-P/checked.json');b=read(ROOT/'replays-supervised'/cid/'oracle-use-only/checked.json')
   def counts(x):return dict(collections.Counter(r['answer'] for r in x['requests']))
   def blockers(x):return dict(collections.Counter(p.split(':')[1] if ':' in p else p for st in x['steps'].values() for p in st.get('pending',[])))
   summary.append({'case_id':cid,'old_requests':counts(base),'repaired_P_requests':counts(a),'oracle_requests':counts(b),'old_pending':blockers(base),'repaired_pending':blockers(a),'oracle_pending':blockers(b),'changed_use_labels':sum(u['label']!=diagnostic['model_uses'][k]['label'] for k,u in s['model_uses'].items()),'operators':dict(collections.Counter(r['operator'] for r in s['rules'].values()))})
 save(ROOT/'cache-replay-supervised-summary.json',summary)
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
