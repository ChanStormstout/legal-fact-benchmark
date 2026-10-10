"""Prepare faithful full-rendering tasks; no labels or prior answers as input."""
import sys,json,hashlib,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.semantic_tasks_v12 import task
R=Path('outputs/proof-semantic-search-v12')
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError(p)
 p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
 rows=json.loads((R/'candidate-order.json').read_text())['rows'];decisions=[]
 for row in rows:
  if not row.get('source'):continue
  cid=row['case_id'];src=json.loads(Path(row['source']).read_text());reason=[]
  if src.get('status')!='COMPLETE_RENDERING':reason.append('INCOMPLETE_RENDERING')
  if src.get('conflicts') or src.get('missing_lines'):reason.append('SOURCE_CONFLICT_OR_GAP')
  if src.get('document_id')!=cid or any(s.get('source_document')!=cid for s in src['segments']):reason.append('IDENTITY_CONFLICT')
  titles=src.get('titles',[]);starts=[i for i,s in enumerate(src['segments']) if s['text'].startswith('## ') and any(t in s['text'] for t in titles)]
  if len(starts)!=1:reason.append('BODY_START_NOT_UNIQUE')
  if reason:decisions.append({'case_id':cid,'status':'SOURCE_BLOCKED','reasons':reason});continue
  start=starts[0];ends=[i for i,s in enumerate(src['segments']) if i>start and 'Related AI tags, queries and research notes' in s['text']]
  if len(ends)!=1:decisions.append({'case_id':cid,'status':'SOURCE_BLOCKED','reasons':['BODY_END_NOT_UNIQUE']});continue
  seg=src['segments'][start:ends[0]]
  case={'case_id':cid,'title':titles[0],'source_path':row['source'],'source_sha256':row['sha256'],'dispute_id':'V12-'+cid,'split':'TRAIN','exposure':'PRIOR_SOURCE_AND_POSSIBLE_METHOD_EXPOSURE; never presented as unseen TEST','grouping':'No known linked case in this batch; party/property and proceeding linkage still requires concentrated check','targets':[{'id':'Q1','text':'Reconstruct the court\'s reasoning on the principal contested property, possession or tenancy entitlement in this judgment. Identify the specific actors, property, event, court stage, adopted legal premise and decisive contrary account. Do not treat a quoted claim or the final order as proof of the entitlement.'},{'id':'Q2','text':'Reconstruct the scope of the court\'s disposition of that dispute: which procedural or legal limits, alternative arguments and unresolved rights constrain the conclusion? Distinguish findings, legal application and matters left open; do not infer absence from proof failure.'}],'segments':seg}
  dest=R/'data'/cid;save(dest/'case.json',case)
  for kind in ['proposal','reference']:
   text=task(kind,case);(dest/(kind+'-task.txt')).write_text(text)
  save(dest/'delivery-map.json',{'complete_original_rendering':src['status'],'body_start_line':seg[0]['original_line'],'body_end_line':seg[-1]['original_line'],'segment_ids':[s['id'] for s in seg],'input_hashes':{kind:hashlib.sha256((dest/(kind+'-task.txt')).read_bytes()).hexdigest() for kind in ['proposal','reference']},'headnotes_not_judicial_findings':True,'no_old_answers_or_labels':True})
  decisions.append({'case_id':cid,'status':'SOURCE_TASKS_PREPARED_SCOPE_AND_GROUP_REVIEW_PENDING','split':'TRAIN','source_segments':len(seg),'task_bytes':(dest/'proposal-task.txt').stat().st_size,'not_training_ready':True})
 save(R/'source-preparation.json',decisions);print(json.dumps(decisions))
if __name__=='__main__':main()
