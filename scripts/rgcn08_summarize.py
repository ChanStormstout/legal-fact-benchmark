import sys,json,collections
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from legal_bench.rules_verdict_v1.rule_retrieval_v21 import parse_answer
R=Path('outputs/rgcn-use-development-08'); P=Path('outputs/rgcn-ranking-diagnostic-07/pilot')
read=lambda p:json.loads(p.read_text())
rows=read(R/'selection-results.json'); out={}
for seed in [20261004,20261005]:
 out[str(seed)]={}
 for method in ['S','B','C0','C']:
  rs=[r for r in rows if r['seed']==seed and r['method']==method]; cm=[[sum(r['confusion'][i][j] for r in rs) for j in range(3)]for i in range(3)]
  out[str(seed)][method]={'confusion':cm,'core_delivered':[sum(r['core_delivered'][i]for r in rs)for i in [0,1]],'core_identification':[sum(r['core_identification'][i]for r in rs)for i in [0,1]],'false_core':sum(r['core_false_positive']for r in rs),'irrelevant_chars_mean':sum(r['irrelevant_payload_characters']for r in rs)/len(rs),'preferences':[sum(r['preference_agreement'][i]for r in rs)for i in [0,1]],'unreachable':{r['case_id']:r['individually_undeliverable_core']for r in rs if r['individually_undeliverable_core']}}
(R/'aggregate-results.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
variation=read(R/'same-authority-use-variation.json');print('Variation',[(r['unit_id'],r['classes'],collections.Counter(x['class']for x in r['records']))for r in variation])
(R/'parsed').mkdir(exist_ok=True)
for task in read(R/'answer-order.json'):
 id=task['id']; p=R/'raw'/f'{id}.txt'
 if not p.exists()or not p.read_text().strip():continue
 raw=p.read_text(); removals=[]
 if raw.startswith('ChatGPT 说：'):raw=raw[len('ChatGPT 说：'):].lstrip();removals.append('VISIBLE_ASSISTANT_HEADING')
 if raw.rstrip().endswith('粘贴的文本 (1)'):raw=raw.rstrip()[:-len('粘贴的文本 (1)')].rstrip();removals.append('VISIBLE_ATTACHMENT_CITATION_UI')
 material=read(P/'task-material'/f"{task['case_id']}.json")
 selected=read(R/'selections'/task['case_id']/f"20261004-{task['methods'][0]}.json")
 try:
  value,log=parse_answer(raw,[s['id']for s in material['case']['segments']],[u['id']for u in selected['units']]);log['display_removals']=removals
  (R/'parsed'/f'{id}.json').write_text(json.dumps({'answer':value,'validation':log},ensure_ascii=False,indent=2)+'\n');print(id,value['outcome'],len(value['grounds']),log['source_issues'])
 except Exception as e:print(id,'FORMAT ERROR',repr(e));(R/'parsed'/f'{id}.json').write_text(json.dumps({'answer':None,'error':repr(e),'run_status':'FORMAT_ERROR'},indent=2)+'\n')
