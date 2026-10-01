import sys,copy,json
from pathlib import Path
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read,digest
from legal_bench.field_pipeline_v2 import execute_declared
R=Path('outputs/local-qwen-pattern-eval-v1');OLD=Path('outputs/new-10-pattern-matching-v1');OUT=R/'old10-diagnostic'
if (OUT/'results.json').exists():print('Retained existing diagnostic; not rerun');sys.exit(0)
OUT.mkdir(parents=True,exist_ok=True)
rows=[];manifest=[]
for case in read(OLD/'sample.json')['cases']:
 cid=case['case_id'];p=Path('outputs/unknown-two-case-study-v1/projected-views')/(cid+'.json')
 if not p.exists():p=OLD/'views'/(cid+'.json')
 view=read(p);reg=read(OLD/'relations'/(cid+'.json'));manifest.append({'case_id':cid,'view_file':str(p),'view_hash':digest(view),'relation_hash':digest(reg),'no_new_type_declarations':True})
 for c in read(R/'tasks.json')['tasks']:
  q=c['query'];co=copy.deepcopy(q);co['constraints']=[x for x in q['constraints'] if x['op'] not in ['part_of','member_of']]
  rows.append({'case_id':cid,'task_id':c['task_id'],'B':execute_declared(view,reg,q),'cooccurrence':execute_declared(view,reg,co)})
summary={m:dict(Counter(r[m]['status'] for r in rows)) for m in ['B','cooccurrence']}
(OUT/'results.json').write_text(json.dumps({'kind':'OLD_SAMPLE_DIAGNOSTIC_REPLAY_NOT_NEW_TEST','input_manifest':manifest,'rows':rows,'summary':summary},indent=2,ensure_ascii=False));print(summary)
