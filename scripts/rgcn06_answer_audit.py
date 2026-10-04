"""Non-semantic final contract/source-address audit; does not change replies."""
import json,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1 import rule_retrieval_v21 as legacy
R=Path('outputs/rgcn-ranking-development-06')
def rd(p):return json.loads(p.read_text())
def main():
 rows=[];masked=R/'source-review';masked.mkdir(exist_ok=True)
 for task in rd(R/'answer-order.json'):
  tid=task['id'];p=R/('parsed/'+tid+'.json');raw=R/('raw/'+tid+'.txt')
  if not p.exists():rows.append(dict(id=tid,status='FORMAT_OR_RUN_FAILURE',answer=None,raw_exists=raw.exists()));continue
  ans=rd(p);source=rd(R/('sources/'+task['case_id']+'.json'));caseids={s['id'] for s in source['segments']}
  text=(R/('tasks/'+tid+'.txt')).read_text();a=text.index('SELECTED ORIGINAL LEGAL UNITS (metadata are context, not target facts)\n')+len('SELECTED ORIGINAL LEGAL UNITS (metadata are context, not target facts)\n');b=text.index('\nCOMPLETE ALLOWED TARGET RECORD\n');laws=json.loads(text[a:b]);lawids={u['id'] for u in laws}
  try:legacy.validate_output(ans);status='OK'
  except ValueError as e:status=str(e)
  bad=[dict(ground=n,field=k,ref=x) for n,g in enumerate(ans.get('grounds',[])) for k,valid in [('case_refs',caseids),('law_refs',lawids)] for x in g.get(k,[]) if x not in valid]
  neutral='R'+hashlib.sha256(tid.encode()).hexdigest()[:8]
  (masked/(neutral+'.json')).write_text(json.dumps(dict(case_id=task['case_id'],answer=ans,allowed_source=source,delivered_laws=laws),ensure_ascii=False,indent=2)+'\n')
  rows.append(dict(id=tid,neutral=neutral,status=status,source_address_errors=bad,outcome=ans.get('outcome'),input_characters=len(text),raw_characters=len(raw.read_text()) if raw.exists() else None,semantic_correctness_certified=False))
 (R/'answer-format-audit.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 print([(x['id'],x['status'],len(x.get('source_address_errors',[]))) for x in rows])
if __name__=='__main__':main()
