#!/usr/bin/env python3
import json,datetime
from pathlib import Path
R=Path('outputs/legal-rule-support-study-02')
def read(p):return json.loads(p.read_text())
p=R/'call-ledger.json';a=read(p);rows=[]
for d in (R/'runs').iterdir():
 if not (d/'submission.json').exists():continue
 s=read(d/'submission.json');c=read(d/'copy-completion.json') if (d/'copy-completion.json').exists() else (read(d/'completion.json') if (d/'completion.json').exists() else {}); parsed=read(d/'parse-record.json') if (d/'parse-record.json').exists() else {}
 rows.append(dict(id=d.name,started_utc=s['started_utc'],completed_observed_utc=c.get('completed_observed_utc'),url=c.get('url'),status=parsed.get('status',c.get('status','SUBMITTED_PENDING')),input_characters=len(s['submitted_text'])+len(s['wrapper']),output_characters=c.get('raw_characters'),model_visible=s.get('visible_model'),exact_model=s.get('exact_model'),mode=s.get('mode'),tokens=None,precise_generation_seconds=None))
a['new_calls']=sorted(rows,key=lambda x:x['started_utc']);a['actual_calls']=len(rows);a['updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();assert len(rows)<=58
p.write_text(json.dumps(a,ensure_ascii=False,indent=2)+'\n');print(len(rows),'calls')
