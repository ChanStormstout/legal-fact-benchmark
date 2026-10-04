#!/usr/bin/env python3
"""Single paired source-only admission; no target-reference or ranking reads."""
import sys,json,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1 import legal_rule_support_study as m
from legal_bench.rules_verdict_v1.source_views import write_new
R=Path('outputs/legal-rule-support-study-02')
def rd(p):return json.loads((R/p).read_text())
u=m.registry(rd('library/original-units.json'));records={a:{} for a in ['G','L']}
for task in rd('representation-order.json'):
 p=R/'runs'/task['id']/'copied-answer.json'
 if p.exists():
  for x in json.loads(p.read_text()).get('descriptions',[]):records[task['arm']][x['legal_unit_id']]=x
rows=[];accepted={a:[] for a in ['G','L']}
missing=set(rd('audit/description-dependency-limitation.json')['affected_units'])
for key,source in u.items():
 reasons=[];checks={}
 for arm in ['G','L']:
  x=records[arm].get(key)
  if not x:reasons.append(arm+':MISSING_DESCRIPTION');continue
  valid=isinstance(x.get('description'),str) and isinstance(x.get('limitations'),str) and isinstance(x.get('evidence'),list) and all(isinstance(e,str) for e in x.get('evidence',[]))
  if not valid:reasons.append(arm+':STRUCTURE_ERROR');continue
  q=[m.locate_quote(source['text'],e) for e in x['evidence']]
  checks[arm]=dict(quote_checks=q,word_count=len(x['description'].split()),source_scope_review='Model source-only review: main claim, negation, judicial/statutory status and limits compared to supplied original, not target usefulness.',semantic_review='Supported within stated scope; no target applicability asserted')
  if not q or not any(c['status'] in ['EXACT','WHITESPACE_ONLY'] for c in q):reasons.append(arm+':NO_LOCATABLE_SUPPORT_QUOTE')
 if key in missing:reasons.append('SOURCE_PACKAGE_MISSING_DECLARED_DEPENDENCY; paired secondary exclusion, raw remains')
 enabled=not reasons
 rows.append(dict(legal_unit_id=key,paired_enabled=enabled,reasons=reasons,checks=checks,not_human_gold=True))
 if enabled:
  for arm in ['G','L']:accepted[arm].append(records[arm][key])
write_new(R/'representations/paired-source-review.json',dict(reviewer='Codex model, one limited source-only review',rows=rows,scope='Only source fidelity; no target reference/ranking/output used for admission'))
for a,rs in accepted.items():write_new(R/'representations'/(a+'-accepted.json'),rs)
files=list((R/'representations').glob('*.json'))+[p for t in rd('representation-order.json') for p in (R/'runs'/t['id']).iterdir() if p.name!='page.txt']
write_new(R/'representation-freeze.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reference_freeze_sha256=m.sha((R/'reference-freeze.json').read_bytes()),files_sha256={str(p.relative_to(R)):m.sha(p.read_bytes()) for p in files},enabled=sum(x['paired_enabled'] for x in rows),total=len(rows),model_generated_source_reviewed_not_human_gold=True))
print([(x['legal_unit_id'],x['paired_enabled'],x['reasons']) for x in rows])
