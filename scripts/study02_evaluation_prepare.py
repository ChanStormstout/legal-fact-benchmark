#!/usr/bin/env python3
"""One batch source review; anonymous answers, frozen references, no final judgments."""
import sys,json,random,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1 import legal_rule_support_study as m
from legal_bench.rules_verdict_v1.source_views import write_new
R=Path('outputs/legal-rule-support-study-02')
def rd(p):return json.loads((R/p).read_text())
def save(p,v):write_new(R/p,v)
INSTRUCTION='''Perform ONE limited model-assisted source review, NOT human gold, of the anonymous complete answers below. Do not use outside law, other conversations, target final reasoning or historical outcome. Material/wording may reveal treatments: not fully blind. Judge factual fidelity against each answer's ACTUALLY DELIVERED original units and the allowed target record; judge important coverage separately against the full common library and frozen finite model references. A reference may be wrong: independently check source wording, preserve genuine interpretation disputes. Do not equate a missing delivered source with hallucination or legal nonexistence. Check important allowed content even when the answer did not cite it. Distinguish parties' allegations, evidence, lower court findings and target court adoption; objects, event timing, alternatives, consent direction, precedent facts vs target facts, scope/status, counterarguments, genuine gaps, and point/assessment/explanation/reason consistency. UNKNOWN, caution, more citations or completion alone are not correctness. Assess only decisive issues, not all facts. Same-input shared answers are a single treatment, not independent observations. Repeats do not replace first answers. For distinct first-treatment pairs give NET_IMPROVEMENT only if an important improvement has no equally serious new error or deterioration; otherwise CLOSE, WORSE, MIXED or UNJUDGEABLE. Identify direction by anonymous ID only. For one first treatment, record SAME_TREATMENT, not equivalence. Report repeat changes separately; one repeat cannot estimate variance.
Output one complete JSON with case_id, answer_reviews:[{answer_id,source_supported_points,confirmed_errors:[{claim,source_ids,source_words,why_decisive}],important_omissions,internal_contradictions,real_gaps,source_delivery_vs_use,overall}], pair_comparisons:[{first_id,second_id,result,source_grounded_reason}], repeat_stability, reference_disputes, limitations. Empty lists are permitted. Use source IDs and short exact source words for decisive findings. No recommendations to alter/reanswer this batch.'''
def main():
 groups=rd('run-order.json');samples=rd('samples.json');conf=rd('selection-config.json');rng=random.Random(20261003);orders=[]
 for i,s in enumerate(samples):
  cid=s['case_id'];gs=[g for g in groups if g['case_id']==cid];rng.shuffle(gs);answers=[];mapping={}
  for j,g in enumerate(gs):
   name='N'+str(j+1);mapping[name]=g['id'];p=R/'runs'/g['id']/'parse-record.json'
   if not p.exists():raise ValueError('UNFINISHED '+g['id'])
   state=json.loads(p.read_text());a=rd('runs/'+g['id']+'/copied-answer.json') if state['status']=='OK' else None
   answers.append(dict(answer_id=name,replicate_id=g['replicate'],technical_status=state['status'],delivered_unit_ids=g['selected_ids'],answer=a))
  source=rd(s['source']);ref=rd('references/'+cid+'.json');ref['items']=[{k:v for k,v in item.items() if k not in ['quote_checks','review_source_anchors']} for item in ref['items']]
  task=INSTRUCTION+'\nQUESTION\n'+s['question']+'\nALLOWED TARGET RECORD\n'+json.dumps(source,ensure_ascii=False,separators=(',',':'))+'\nFULL COMMON ORIGINAL LIBRARY\n'+m.render(rd('library/original-units.json'))+'\nFROZEN MODEL REFERENCE (fallible, not exhaustive)\n'+json.dumps(ref,ensure_ascii=False,separators=(',',':'))+'\nANONYMOUS ANSWERS AND DELIVERED MATERIAL IDS\n'+json.dumps(answers,ensure_ascii=False,separators=(',',':'))
  name='EVAL%02d'%(i+1);p=R/'tasks'/(name+'.txt');p.write_text(task);save('evaluation/'+name+'-mapping.json',dict(case_id=cid,anonymous_mapping=mapping,not_fully_blind=True));orders.append(dict(id=name,case_id=cid,path='tasks/'+name+'.txt',sha256=m.sha(task)))
 save('evaluation-order.json',orders);save('evaluation-task-freeze.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),tasks=orders,criteria_sha256=m.sha(INSTRUCTION),rule_source='Frozen full protocol; no answer-contingent criteria',all_generated_before_reviews=True))
 print([(x['id'],x['case_id']) for x in orders])
if __name__=='__main__':main()
