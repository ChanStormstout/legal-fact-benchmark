#!/usr/bin/env python3
"""Build separate TRAIN/DEV supervision from frozen proposed uses and source-reviewed labels.
This entry never opens TEST outputs. QC is an independent required saved artifact.
"""
import json,sys,hashlib,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.semantic_data_v12 import validate_use,training_gate
from scripts.proof_semantic_run_v12 import save
ROOT=Path('outputs/proof-semantic-search-v12')
def read(p):return json.loads(p.read_text())
def provenance_exclusions(root):
 p=root/'provenance-exclusions.json'
 return set(read(p)['cases']) if p.exists() else set()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();rows=[];missing=[]
 excluded=provenance_exclusions(ROOT)
 for d in sorted((ROOT/'cohort').iterdir()):
  case=read(d/'case.json')
  if case['split']=='TEST':continue
  if case['case_id'] in excluded:missing.append(case['case_id']);continue
  p=ROOT/'generated'/case['case_id'];proposal=p/'proposal/parsed.json';review=p/'review/parsed.json'
  if not proposal.exists() or not review.exists():missing.append(case['case_id']);continue
  raw=read(proposal);input_graph=read(p/'proposal/graph.json') if (p/'proposal/graph.json').exists() else {'ids':[]};reviews=read(review).get('use_reviews',[]);review_index={}
  for r in reviews:review_index.setdefault(r.get('use_id'),[]).append(r)
  premises={pr['id']:(r,pr) for r in raw['rules'] for pr in r['premises']};sources={s['id']:{**s,'document':s['source_document']} for s in case['segments']};source_hash=case['source_sha256']
  for u in raw['uses']:
   rr,pr=premises.get(u.get('rule_premise'),({},{}));rv=review_index.get(u.get('id'),[]);lab=rv[0] if len(rv)==1 else {}
   row={'key':case['case_id']+'::'+u['id'],'id':u['id'],'use_id':u['id'],'dispute_id':case['dispute_id'],'case_id':case['case_id'],'split':case['split'],'request_id':u['request_id'],'rule_ref':rr.get('id','')+'@'+str(rr.get('version','')),'premise':pr.get('text'),'premise_family':pr.get('family','UNSPECIFIED'),'evidence_ids':u.get('evidence_ids'),'bindings':u.get('bindings'),'label':lab.get('label','UNLABELED'),'basis':lab.get('basis'),'refs':lab.get('refs',[]),'quote':lab.get('quote',''),'mechanism':case['mechanism'],'synthetic':False,'source_sha256':source_hash,'proposal_sha256':hashlib.sha256(proposal.read_bytes()).hexdigest(),'review_sha256':hashlib.sha256(review.read_bytes()).hexdigest(),'reference_kind':'MODEL_GENERATED_SOURCE_REVIEW_NOT_HUMAN_GOLD'}
   errors=validate_use(row,sources)
   if len(rv)>1:errors.append('DUPLICATE_REVIEW')
   if not rr or not pr:errors.append('UNKNOWN_RULE_PREMISE')
   if u['id'] not in input_graph['ids']:errors.append('INPUT_USE_NOT_REPRESENTABLE')
   if not source_hash:errors.append('SOURCE_VERSION_MISSING')
   row.update(valid=not errors,errors=errors);rows.append(row)
 qcpath=ROOT/'qc/source-review.json';qc=read(qcpath) if qcpath.exists() else {}
 dest=Path(a.out);dest.mkdir(parents=True,exist_ok=False);save(dest/'rows.json',rows);save(dest/'gate.json',training_gate(rows,qc));save(dest/'missing.json',missing)
 save(dest/'provenance-excluded.json',sorted(excluded))
 print(json.dumps({'rows':len(rows),'missing_cases':len(missing),'gate':training_gate(rows,qc)}))
if __name__=='__main__':main()
