#!/usr/bin/env python3
"""Reference-free entry and one historical eight-case regression, never training labels."""
import sys,json,hashlib,time,argparse,traceback,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.semantic_search_v12 import complete_search
from legal_bench.proof_carrying.selection_v10 import eligibility,load_contracts
OUT=Path('outputs/proof-semantic-search-v12');OLD=Path('outputs/proof-carrying-state-search-v11');BASE=Path('outputs/proof-carrying-graph-integration-v8')
def read(p):return json.loads(Path(p).read_text())
def save(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError(p)
 p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest()
def run(snapshot,candidates,requests,dest):
 dest=Path(dest);t=time.perf_counter()
 if dest.exists():raise FileExistsError(dest)
 dest.mkdir(parents=True)
 try:
  search=complete_search(candidates,snapshot['rules'],requests,snapshot['contracts'])
  save(dest/'snapshot.json',snapshot);save(dest/'search.json',search)
  save(dest/'manifest.json',{'snapshot_sha256':digest(snapshot),'search_sha256':digest(search)})
  p=subprocess.run([sys.executable,'scripts/check_semantic_v12.py',str(dest)],capture_output=True,text=True,timeout=120)
  (dest/'checker.stdout.txt').write_text(p.stdout);(dest/'checker.stderr.txt').write_text(p.stderr)
  if p.returncode:raise RuntimeError(p.stderr)
  checked=json.loads(p.stdout);save(dest/'checked.json',checked)
  save(dest/'analysis.json',{'case':snapshot['case_id'],'requests':checked['requests'],'raw_relations':snapshot.get('relations',[]),'coverage_limits':snapshot.get('coverage_limits',[]),'input_track':'AUTOMATIC_MODEL_PROPOSALS_NO_REFERENCE','source_address_check_is_not_semantics':True,'legal_approval':False})
  cost={'run_status':'OK','answer':checked['requests'],'seconds':time.perf_counter()-t,'candidates':len(candidates),'steps':len(search['steps']),'state_expansions':sum(r['state_expansions'] for r in search['requests']),'search_incomplete':sum(r['search_status']=='SEARCH_INCOMPLETE' for r in search['requests'])};save(dest/'run.json',cost);return cost
 except Exception as e:
  save(dest/'failure.json',{'run_status':'TECHNICAL_FAILURE','answer':None,'error':repr(e),'traceback':traceback.format_exc(),'seconds':time.perf_counter()-t});raise

def regression():
 rows=[]
 for cid in read(OLD/'protocol.json')['cases']:
  facts=read(BASE/'runs'/cid/'proposal/usable.json');rules={r['id']+'@'+str(r['version']):r for r in read(BASE/'inputs'/cid/'rules.json')};sources=read(BASE/'inputs'/cid/'sources.json');contracts=load_contracts(OLD/'contracts/registry.json',rules);ps={p['id']:p for p in facts['premises']}
  # No reference, old acceptance snapshot or composite accepted by reference is opened.
  cs=read(OLD/'prepared'/cid/'candidates.json');e=eligibility(cs,rules,ps,sources,contracts);keep={x['id'] for x in e if x['status']!='EXCLUDE_EXPLICIT_CONTRACT_ERROR'}
  snap={'case_id':cid,'premises':ps,'entities':facts['entities'],'rules':rules,'sources':sources,'contracts':{k:v['variables'] for k,v in contracts.items()},'coverage_contracts':{k:{slot:{z:w for z,w in cv.items() if z in ('mode','required_components')} for slot,cv in v['coverage'].items()} for k,v in contracts.items()},'model_uses':{},'relations':facts.get('relations',[]),'coverage_limits':facts.get('coverage_limits',[])+['Historical raw proposal lacks V12 whole-premise use judgment; no labels or verdicts were converted.','Historical composites requiring external acceptance are unavailable in automatic track.']}
  rr=run(snap,[c for c in cs if c['id'] in keep],read(BASE/'inputs'/cid/'requests.json'),OUT/'regression'/cid);rows.append({'case':cid,**{k:v for k,v in rr.items() if k!='answer'}})
 save(OUT/'regression-summary.json',rows);print(json.dumps(rows))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--regression',action='store_true');p.add_argument('--snapshot');p.add_argument('--candidates');p.add_argument('--requests');p.add_argument('--out');a=p.parse_args()
 if a.regression:regression()
 else:run(read(a.snapshot),read(a.candidates),read(a.requests),a.out)
