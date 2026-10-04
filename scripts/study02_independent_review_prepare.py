#!/usr/bin/env python3
import json,datetime,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.legal_rule_support_study import sha
from legal_bench.rules_verdict_v1.source_views import write_new
R=Path('outputs/legal-rule-support-study-02')
def rd(p):return json.loads((R/p).read_text())
selected=rd('selection-config.json')['independent_review_cases'];evals=rd('evaluation-order.json');order=[]
for i,cid in enumerate(selected):
 e=next(x for x in evals if x['case_id']==cid);p=R/'runs'/e['id']/'copied-answer.json'
 if not p.exists():raise ValueError('Evaluation not finished '+e['id'])
 content=(R/e['path']).read_text();materials=content[content.index('\nQUESTION\n'):]
 instruction='''Perform the one preselected independent model-assisted source audit for this case. Not human gold and not an independent-bias guarantee. Read original supplied allowed record, common library, anonymous answers and frozen fallible references below. Then inspect the previous review. Check decisive source anchors, alleged errors, important omissions, legal scope/status, uncertainty and comparison direction. Do not rely on majority agreement. Do not use target final reasoning, outside sources or other conversations. Separate delivered-source fidelity from full-library coverage. Preserve disputed legal interpretations. Identify any reference correction without silently replacing frozen references, and explain whether it changes any treatment comparison. Do not request another run. Output complete JSON: {case_id,review_agreements,review_disagreements:[{item,source_ids,source_words,reason,impact}],reference_corrections,comparison_direction,repeat_assessment,limitations}. There is no mandatory disagreement.'''
 t=instruction+materials+'\nPRIOR FALLIBLE REVIEW\n'+p.read_text();name='AUD%02d'%(i+1);(R/'tasks'/(name+'.txt')).write_text(t);order.append(dict(id=name,case_id=cid,path='tasks/'+name+'.txt',sha256=sha(t),preselected=True))
write_new(R/'independent-review-order.json',order);print(order)
