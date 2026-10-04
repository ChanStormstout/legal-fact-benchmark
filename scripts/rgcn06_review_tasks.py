import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from rgcn06_tasks import *
if sys.argv[1]=='law':
 for i in range(1,5):
  p=rd(R/('parsed/LAW%02d.json'%i));ids={x['unit_id'] for x in p['units']}
  body={'originals':[u for u in LAW if u['id'] in ids],'proposals':p}
  task('LAWREV%02d'%i,'''One independent source review. Check EVERY proposed condition against original and necessary context, including adoption/scope/exception/AND-OR. Output {"reviews":[{"unit_id":"...","condition_id":"...","decision":"SUPPORTED|DISPUTED|UNSUPPORTED","quote":"exact source support or counterevidence","reason":"brief"}],"unit_omissions":[{"unit_id":"...","issue":"important missing condition if any","quote":"exact"}],"limits":[]}. No rewriting or adding input graph records; disputed or unsupported are excluded. Location alone is not semantics. No ranking or model output available.''',json.dumps(body,ensure_ascii=False))
elif sys.argv[1]=='graph':
 for i,s in enumerate(S,1):
  p=R/('parsed/GRAPH%02d.json'%i)
  if not p.exists() or (R/('tasks/GREV%02d.txt'%i)).exists():continue
  body=dict(material(s),graph=rd(p),law_proposals=rd(R/'law-proposals.json'))
  task('GREV%02d'%i,"""One independent input-only source review. You cannot see usefulness labels, reference answers or rankings. Check facts, objects, needs, relationships, and all14 candidate alignment scopes against supplied originals. Do not select correct authorities or add records. Output {"case_id":"...","rejections":[{"id":"existing fact/need/object/relation ID or lawID::alignmentN with zero-based link index","reason":"specific source problem","refs":["source IDs"]}],"omissions":["important missing information; never fill it"],"limits":[]}. Retain unchallenged proposals provisionally; only clear errors rejected, uncertainty stays uncertainty. A candidate link need not establish a condition, so do not reject simply because it cannot prove eviction. Check claims vs findings, stage, direction and forbidden mixing of precedent facts. Do not correct via invented source or final outcome.""",json.dumps(body,ensure_ascii=False))
elif sys.argv[1]=='reference':
 for i,s in enumerate(S,1):
  if (R/('tasks/REVIEW%02d.txt'%i)).exists() or not (R/('parsed/PREF%02d.json'%i)).exists():continue
  body=dict(material(s),uses=rd(R/('parsed/USE%02d.json'%i)),preferences=rd(R/('parsed/PREF%02d.json'%i)))
  task('REVIEW%02d'%i,"""One independent reference-only source review. No input graph, model ranking, trained result or final answer available. Check all14 use judgments and EVERY preference against originals and budget/dependency context. Output {"case_id":"...","use_reviews":[{"unit_id":"...","decision":"SUPPORTED|DISPUTED|UNSUPPORTED","reason":"...","case_refs":["..."],"law_quote":"exact"}],"preference_reviews":[{"a":"...","b":"...","decision":"SUPPORTED|DISPUTED|UNSUPPORTED","reason":"check direction/budget; ties and incomparable/unknown can be supported","case_refs":["..."],"law_quote":"exact"}],"limits":[]}. Disagreement preserved, no forced consensus. Do not rewrite judgments. Lower priority is not irrelevance; opposing material may be essential. Cover every entry; unreviewed remains disputed. Model-assisted source reference, never human gold.""",json.dumps(body,ensure_ascii=False))
