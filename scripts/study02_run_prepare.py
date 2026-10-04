#!/usr/bin/env python3
"""Frozen inherited retrieval; no reference-dependent ranking or prompt edits."""
import sys,json,datetime,random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));sys.path.insert(0,str(Path(__file__).resolve().parent))
from legal_bench.rules_verdict_v1 import legal_rule_support_study as m
from legal_bench.rules_verdict_v1.source_views import write_new
from legal_rule_support_study02 import check_task
R=Path('outputs/legal-rule-support-study-02')
def rd(p):return json.loads((R/p).read_text())
def save(p,x):write_new(R/p,x)
def freezecheck(n):
 for p,h in rd(n)['files_sha256'].items():
  if m.sha((R/p).read_bytes())!=h:raise ValueError('FROZEN_FILE_CHANGED '+p)
def main():
 if (R/'run-freeze.json').exists():raise FileExistsError('Run already prepared')
 freezecheck('source-freeze.json');freezecheck('reference-freeze.json');freezecheck('representation-freeze.json')
 u=rd('library/original-units.json');samples=rd('samples.json');conf=rd('selection-config.json');profile=rd('visible-generation-config.json');wrapper=(R/'execution-wrapper.txt').read_text()
 descriptions={a:rd('representations/'+a+'-accepted.json') for a in ['G','L']}
 if not descriptions['G'] or not descriptions['L']:raise ValueError('NO_PAIRED_REPRESENTATION')
 slots=[];groups={};ranks={};first={};counter=0
 for s in samples:
  cid=s['case_id'];result=m.retrieve_arms(u,descriptions,s['query'],R/'retrieval'/cid/'indexes',config=m.PRIMARY_CONFIG,mandatory=['LAW:S02:DRC14:1b'])
  ranks[cid]=result;save('retrieval/'+cid+'/result.json',result)
 def add(cid,arm,replicate):
  nonlocal counter
  s=next(x for x in samples if x['case_id']==cid);selected=ranks[cid]['selected'][arm];slot=dict(case_id=cid,arm=arm,replicate=replicate,run_status=selected['run_status'])
  if selected['run_status']!='OK':slot.update(id=None,failure=selected);slots.append(slot);return
  source=rd(s['source']);prompt=m.prompt(source,selected['units'],s['question'],m.PRIMARY_CONFIG)
  key=m.shared_key(cid,replicate,prompt+'\n'+wrapper,profile)
  if key not in groups:
   counter+=1;taskid='ANS%02d'%counter
   path=R/'tasks'/(taskid+'.txt');path.write_text(prompt)
   save('audit/'+taskid+'-assembly.json',dict(**check_task(prompt,source),legal_characters=len(m.render(selected['units'])),legal_ids=selected['selected_ids'],selected_original_material_complete=m.render(selected['units']) in prompt))
   groups[key]=dict(id=taskid,case_id=cid,replicate=replicate,arms=[],prompt_path='tasks/'+taskid+'.txt',prompt_sha256=m.sha(prompt),complete_submission_sha256=m.sha(prompt+'\n'+wrapper),selected_ids=selected['selected_ids'],input_characters=len(prompt)+len(wrapper),legal_characters=selected['legal_characters'])
  groups[key]['arms'].append(arm);slot.update(id=groups[key]['id'],shared_key=key);slots.append(slot)
 for i,s in enumerate(samples):
  order=['A','G','L'][i%3:]+['A','G','L'][:i%3];first[s['case_id']]=order
  for a in order:add(s['case_id'],a,0)
 for cid in conf['repeat_cases']:
  for a in reversed(first[cid]):add(cid,a,1)
 save('run-slots.json',slots);save('run-order.json',list(groups.values()))
 files=[R/'run-order.json',R/'run-slots.json']+[R/'tasks'/(x['id']+'.txt') for x in groups.values()]+[R/'audit'/(x['id']+'-assembly.json') for x in groups.values()]+list((R/'retrieval').rglob('*.json'))
 save('run-freeze.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_freeze_sha256=m.sha((R/'source-freeze.json').read_bytes()),reference_freeze_sha256=m.sha((R/'reference-freeze.json').read_bytes()),representation_freeze_sha256=m.sha((R/'representation-freeze.json').read_bytes()),config=m.PRIMARY_CONFIG,profile=profile,files_sha256={str(p.relative_to(R)):m.sha(p.read_bytes()) for p in files},source_code_sha256={p:m.sha(Path(p).read_bytes()) for p in ['scripts/study02_run_prepare.py','legal_bench/rules_verdict_v1/legal_rule_support_study.py','legal_bench/rules_verdict_v1/authority_index.py','legal_bench/rules_verdict_v1/retrieve.py']},slots=len(slots),independent_calls=len(groups),no_model_final_calls_yet=True))
 print('Slots',len(slots),'calls',len(groups))
 for x in groups.values():print(x['id'],x['case_id'],x['replicate'],x['arms'],x['selected_ids'])
if __name__=='__main__':main()
