#!/usr/bin/env python3
"""One source-anchored review, fixed before rankings; never edits raw references."""
import sys,json,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1 import legal_rule_support_study as m
from legal_bench.rules_verdict_v1.source_views import write_new
R=Path('outputs/legal-rule-support-study-02')
def read(p):return json.loads(p.read_text())
units=read(R/'library/original-units.json');table=m.registry(units)
verified={'REF01':['r1','r3'],'REF02':['r1','r2'],'REF03':['r1','r2','r4','r5','r6'],'REF04':['r1','r4'],'REF05':['r1','r5'],'REF06':['r1','r2','r5']}
allrows=[]
for task in read(R/'reference-order.json'):
 d=R/'runs'/task['id'];p=d/'format-only-answer.json'
 if not p.exists():p=d/'answer.json'
 a=read(p);assert a['case_id']==task['case_id']
 view=read(R/'sources'/(a['case_id']+'-allowed.json'));pool={**table,**{s['id']:s for s in view['segments']}}
 rows=[]
 for item in a['reference_items']:
  row=dict(item);unknown=[k for k in item['unit_ids'] if k not in table]
  row['quote_checks']=[dict(unit_id=e['unit_id'],**m.locate_quote(pool.get(e['unit_id'],{}).get('text',''),e['quote'])) for e in item['evidence']]
  if unknown:
   row.update(status='UNVERIFIABLE',review_reason='Contains target-record IDs rather than an all-library legal-source bundle. Retained as qualitative analysis, not converted into invented legal units or a legal retrieval denominator.',invalid_legal_unit_ids=unknown)
  elif item['id'] in verified[task['id']]:
   row.update(status='VERIFIED_SOURCE_ANCHORED',review_reason='One model-assisted review of original unit text confirms the stated proposition and limited role. The Delhi statute is a version-limited reproduction; GR reported Delhi is a report of precedent, not its full opinion. For bank succession, TS remains prima facie/reserved and GR an AP-law analogy, not a Delhi holding. Unlocated model quotation strings are retained as quotation defects; reviewer anchors below point to the unaltered source, not a silently repaired quotation.',review_source_anchors=[dict(unit_id=k,text_sha256=m.sha(table[k]['text']),span=[0,len(table[k]['text'])]) for k in item['unit_ids']])
  else:
   row.update(status='DISPUTED',review_reason='Main proposition is supported with the recorded scope limits, but its inclusion as a useful legal reference for this non-amalgamation target is disputable. Full source/quotation defects retained; exclude from primary denominator and include symmetrically in sensitivity analysis.')
  rows.append(row)
 out=dict(case_id=a['case_id'],reference_task=task['id'],label='MODEL_GENERATED_AND_MODEL_SOURCE_REVIEWED_NOT_HUMAN_GOLD',items=rows,analysis_points=a['analysis_points'],gaps=a['gaps'],disputes=a['disputes'],raw_answer_path=str(p.relative_to(R)),exhaustive=False)
 write_new(R/'references'/(a['case_id']+'.json'),out);allrows.append(out)
files=[p for p in (R/'references').glob('*.json')]+[p for d in (R/'runs').glob('REF*') for p in d.iterdir() if p.name!='page.txt']
write_new(R/'reference-freeze.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_freeze_sha256=m.sha((R/'source-freeze.json').read_bytes()),files_sha256={str(p.relative_to(R)):m.sha(p.read_bytes()) for p in files},reviewer='Codex model source review; no additional web review; not human gold',rankings_created=False,verified=sum(x['status']=='VERIFIED_SOURCE_ANCHORED' for a in allrows for x in a['items']),disputed=sum(x['status']=='DISPUTED' for a in allrows for x in a['items']),unverifiable=sum(x['status']=='UNVERIFIABLE' for a in allrows for x in a['items'])))
print('Reference frozen',[(x['case_id'],[i['id'] for i in x['items'] if i['status']=='VERIFIED_SOURCE_ANCHORED']) for x in allrows])
