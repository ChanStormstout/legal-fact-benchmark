#!/usr/bin/env python3
"""One-time raw web import, lossless wrapper removal, independently stored references."""
import sys,json,re,hashlib,argparse,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.semantic_import_v12 import adapt
from legal_bench.proof_carrying.semantic_tasks_v12 import task
from legal_bench.proof_carrying.semantic_features_v12 import graph,ce_pairs
from scripts.proof_semantic_run_v12 import run,save
ROOT=Path('outputs/proof-semantic-search-v12')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('case');ap.add_argument('role',choices=['proposal','reference','review']);ap.add_argument('raw');a=ap.parse_args()
 case=json.loads((ROOT/'cohort'/a.case/'case.json').read_text());root=ROOT/('test-isolated' if case['split']=='TEST' else 'generated')/a.case
 dest=root/a.role;dest.mkdir(parents=True,exist_ok=False);raw=Path(a.raw).read_text();(dest/'raw.txt').write_text(raw);clean=raw.strip();ops=[]
 if re.fullmatch(r'```(?:json)?\s*\n[\s\S]*\n```',clean):clean=re.sub(r'^```(?:json)?\s*\n|\n```$','',clean);ops.append('REMOVED_OUTER_MARKDOWN_FENCE_ONLY')
 try:
  data=json.loads(clean)
  if not isinstance(data,dict):raise ValueError('OBJECT_REQUIRED')
  save(dest/'parsed.json',data);save(dest/'format.json',{'status':'JSON_PARSED_ONLY','operations':ops,'raw_sha256':hashlib.sha256(raw.encode()).hexdigest(),'semantic_validity':'NOT_EVALUATED'})
 except (ValueError,TypeError) as e:
  save(dest/'failure.json',{'run_status':'FORMAT_ERROR','answer':None,'error':str(e),'operations':ops});return
 if a.role=='proposal':
  try:s,c,q=adapt(case,data)
  except (ValueError,TypeError,KeyError) as e:save(dest/'interface-failure.json',{'run_status':'FORMAT_ERROR','answer':None,'error':str(e)});return
  save(dest/'input-snapshot.json',s);save(dest/'candidates.json',c);save(dest/'requests.json',q)
  save(dest/'graph.json',graph(case,data));save(dest/'ce-pairs.json',ce_pairs(case,data))
  run(s,c,q,dest/'nonlearning')
  review=task('review',case,data);(root/'review-task.txt').write_text(review);save(root/'review-task-manifest.json',{'proposal_sha256':hashlib.sha256(clean.encode()).hexdigest(),'task_sha256':hashlib.sha256(review.encode()).hexdigest(),'independent_reference_read':False})
 print(json.dumps({'case':a.case,'role':a.role,'saved':str(dest),'reference_is_human_gold':False}))
if __name__=='__main__':main()
