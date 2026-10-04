#!/usr/bin/env python3
"""Content-preserving envelope handling for response-copy text; no value repair."""
import sys,json,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1 import legal_rule_support_study as m
from legal_bench.rules_verdict_v1.source_views import write_new
R=Path('outputs/legal-rule-support-study-02')
def read(p):return json.loads(p.read_text())
order={x['id']:x for x in read(R/'run-order.json')} if (R/'run-order.json').exists() else {}
for d in sorted((R/'runs').iterdir()):
 p=d/'copied-response.txt'
 if not p.exists() or (d/'parse-record.json').exists():continue
 raw=p.read_text();s=raw.strip();changes=[];value=None
 try:
  blocks=list(re.finditer(r'```(?:json)?\s*\n([\s\S]*?)\n```',s))
  if len(blocks)==1:
   b=blocks[0];changes.append(dict(kind='COMPLETE_FENCE',prefix=s[:b.start()],suffix=s[b.end():]));s=b[1]
  value,end=json.JSONDecoder().raw_decode(s)
  tail=s[end:].strip()
  if tail and tail not in ['END','粘贴的文本 (1)','粘贴的文本'] :raise ValueError('AMBIGUOUS_TRAILING_TEXT '+tail[:100])
  if tail:changes.append(dict(kind='NON_ANSWER_TRAILER',text=tail))
  status='JSON_READABLE';validation={}
  if d.name in order:
   g=order[d.name];v=read(R/'sources'/(g['case_id']+'-allowed.json'))
   value,validation=m.legacy.parse_answer(json.dumps(value),[s['id'] for s in v['segments']],g['selected_ids']);status=validation['run_status']
  if not (d/'copied-answer.json').exists():write_new(d/'copied-answer.json',value)
  out=dict(status=status,changes=changes,values_unchanged=True,validation=validation,answer_path='copied-answer.json',semantic_correctness_certified=False)
 except Exception as e:out=dict(status='FORMAT_ERROR',answer_path=None,error=str(e),changes=changes,raw_preserved=True)
 write_new(d/'parse-record.json',out);print(d.name,out['status'])
