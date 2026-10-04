#!/usr/bin/env python3
"""One frozen deterministic local run. No final-answer model calls or original writes."""
import json,sys,time,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1 import legal_rule_support_study as m
from legal_bench.rules_verdict_v1.scope_rerank_diagnostic_v1 import rerank
S=Path('outputs/legal-rule-support-study-02');R=Path('outputs/legal-rule-support-diagnostic-03')
def rd(root,p):return json.loads((root/p).read_text())
def save(p,v):
 path=R/p;path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():raise FileExistsError(path)
 path.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
cfg=rd(R,'trial-config-execution.json');assert not (R/'trial-results.json').exists()
for f,h in cfg['frozen_hashes'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h
units=rd(S,'library/original-units.json');samples=rd(S,'samples.json');summary=[]
for sample in samples:
 cid=sample['case_id'];old=rd(S,'retrieval/'+cid+'/result.json');base=old['selected']['A'];start=time.perf_counter_ns()
 ranking=rerank(old['rankings']['A'],units,sample['explicit_act_names'])
 new=m.select(ranking,units,old['configuration'],base['mandatory_ids'])
 elapsed=(time.perf_counter_ns()-start)/1e6
 source=rd(S,sample['source']);task=m.prompt(source,new['units'],sample['question'],old['configuration']);prior=m.prompt(source,base['units'],sample['question'],old['configuration'])
 (R/'trial-tasks').mkdir(exist_ok=True);(R/'trial-tasks'/(cid+'.txt')).write_text(task)
 # References enter evaluation only after ranked selection is complete.
 refs=rd(S,'references/'+cid+'.json');refs=[x for x in refs['items'] if x['status'] in ('VERIFIED_SOURCE_ANCHORED','DISPUTED') and all(k in {u['id'] for u in units} for k in x['unit_ids'])]
 oldmetric=m.delivery(refs,base['selected_ids'],base['mandatory_ids'],units)
 metric=m.delivery(refs,new['selected_ids'],base['mandatory_ids'],units)
 row={'case_id':cid,'new_ranking':ranking,'old_ranking':old['rankings']['A'],'old_selection':base,'new_selection':new,'added':sorted(set(new['selected_ids'])-set(base['selected_ids'])),'removed':sorted(set(base['selected_ids'])-set(new['selected_ids'])),'materials_changed':base['selected_ids']!=new['selected_ids'],'full_prompt_changed':prior!=task,'submitted':False,'old_metric':oldmetric,'new_metric':metric,'elapsed_rerank_select_ms':elapsed,'new_task_sha256':m.sha(task),'no_new_source_or_case_text':True}
 save('trial/'+cid+'.json',row);summary.append({k:row[k] for k in ['case_id','added','removed','materials_changed','full_prompt_changed','elapsed_rerank_select_ms'] }|{'old_rate':oldmetric['rate'],'new_rate':metric['rate'],'old_numerator':oldmetric['numerator'],'new_numerator':metric['numerator'],'denominator':metric['denominator'],'legal_characters_before':base['legal_characters'],'legal_characters_after':new['legal_characters']})
save('trial-results.json',summary)
print(json.dumps(summary,ensure_ascii=False,indent=2))
