#!/usr/bin/env python3
"""V13 durable parsing/address import, never rewrites semantics or old records."""
import sys,json,re,hashlib,argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.semantic_sources_v13 import resolve_record
from legal_bench.proof_carrying.semantic_interface_v13 import adapt,inputs
from legal_bench.proof_carrying.semantic_tasks_v13 import blind_review
from scripts.proof_semantic_run_v13 import save,run
ROOT=Path('outputs/proof-semantic-interface-v13')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('case');ap.add_argument('role',choices=['proposal','reference','review']);a=ap.parse_args();cid=a.case;d=ROOT/'web'/cid/a.role;d.mkdir(parents=True,exist_ok=True)
 case=json.loads((Path('outputs/proof-semantic-search-v12/cohort')/cid/'case.json').read_text());assert case['split']=='DEV'
 raw=(d/'raw.txt').read_text();clean=raw.strip();operations=[]
 if clean.startswith('```') and clean.endswith('```'):
  clean=re.sub(r'^```(?:json)?\s*\n|\n```$','',clean);operations.append('OUTER_MARKDOWN_FENCE_ONLY')
 try:
  p=json.loads(clean)
  if not isinstance(p,dict):raise ValueError('OBJECT_REQUIRED')
  save(d/'parsed.json',p);task=ROOT/'web'/cid/(a.role+'-task.txt')
  if not task.exists():task=Path('outputs/proof-semantic-search-v12/cohort')/cid/(a.role+'-task.txt')
  resolved,mapping=resolve_record(p,case,task);save(d/'resolved.json',resolved);save(d/'address-map.json',mapping);save(d/'format.json',{'status':'JSON_PARSED_ONLY','operations':operations,'raw_sha256':hashlib.sha256(raw.encode()).hexdigest(),'semantic_validity':'NOT_CERTIFIED'})
  if a.role=='proposal':
   s,c,q=adapt(case,resolved);x=inputs(case,resolved)
   for name,v in [('input-snapshot.json',s),('candidates.json',c),('requests.json',q),('model-information.json',x)]:save(d/name,v)
   # A deterministic checker failure does not invalidate the readable P or
   # cancel an independently authorized use review. Keep that failure intact.
   try:run(s,c,q,d/'nonlearning')
   except Exception:pass
   (ROOT/'web'/cid/'review-task.txt').write_text(blind_review(case,resolved))
   save(ROOT/'web'/cid/'review-task-assembly.json',{'proposal_raw_sha256':hashlib.sha256(raw.encode()).hexdigest(),'labels_and_basis_hidden':True,'reference_seen':False,'task_sha256':hashlib.sha256((ROOT/'web'/cid/'review-task.txt').read_bytes()).hexdigest()})
 except (ValueError,TypeError,KeyError) as e:save(d/'failure.json',{'answer':None,'status':'FORMAT_OR_INTERFACE_FAILURE','error':repr(e),'raw_preserved':True,'no_semantic_retry':True})
if __name__=='__main__':main()
