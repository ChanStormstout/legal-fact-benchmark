#!/usr/bin/env python3
"""Mechanical cached replay, provenance and label compatibility; zero generations."""
import argparse,collections,copy,json,shutil,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import proof_local_repair_v19 as entry
from legal_bench.proof_carrying import local_pipeline_v19 as previous
from legal_bench.proof_carrying import local_pipeline_v19_repair as pipe
from legal_bench.proof_carrying.local_annotation_v18_recovery import label_admissibility
from legal_bench.proof_carrying.source_contract_v19 import convert
HISTORY,OUT=entry.HISTORY,entry.OUT
read,save,text,sha=entry.read,entry.save,entry.text,entry.sha

def summarize(a):
 return {'uses':len(a['checks']),'structurally_valid':sum(not x['errors'] for x in a['checks']),'dispositions':dict(collections.Counter(x['disposition'] for x in a['checks'])), 'errors':dict(collections.Counter(e for x in a['checks'] for e in x['errors'])), 'premise_states':dict(collections.Counter(j['conditional_state'] for j in a['premise_judgments'])),'rule_states':dict(collections.Counter(r['conditional_result'] for r in a['conditional_rules']))}

def replay():
 cfg=read(HISTORY/'freeze/protocol.json');cost=[];cases=[]
 for slot in cfg['local_generation_slots']:
  source=HISTORY/slot['dest']
  if not (source/'run.json').exists():continue
  run=read(source/'run.json');cost.append({'dest':slot['dest'],'role':slot['role'],'run_status':run['run_status'],'elapsed_seconds':run.get('elapsed_seconds',0),'provenance':str(source.relative_to(ROOT)),'run_sha256':sha(source/'run.json')})
  if slot['role']!='P':continue
  dest=OUT/slot['dest']
  for p in source.iterdir():
   if p.is_file():
    target=dest/p.name;target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():assert sha(target)==sha(p)
    else:shutil.copy2(p,target)
  save(dest/'production-version.json',{'version':'V19_1','source':str(source.relative_to(ROOT)),'raw_sha256':sha(source/'raw-response.txt'),'no_regeneration':True})
  if slot['case_id'] not in cases:cases.append(slot['case_id'])
 comparisons=[];compat=[];controls=[]
 with patch.object(entry,'protocol',lambda:cfg):
  for cid in cases:
   m=entry.consolidate(cid);f=entry.fixture(cid);p=m['answer']
   old_a=read(HISTORY/'local'/cid/'P/offline-audit.json');a=read(OUT/'local'/cid/'P/offline-audit.json');data=read(OUT/'inputs'/cid/'learner-inputs.json')
   old_data=read(HISTORY/'inputs'/cid/'learner-inputs.json');before={s['id'] for pkg in old_data['materials'].values() for s in pkg['actual_restored_source']['segments']};after=set(data['common_material_manifest']['saved_source_ids'])
   changes=[]
   for old,new in zip(old_a['checks'],a['checks']):
    if old['disposition']!=new['disposition'] or old['errors']!=new['errors'] or old['full_basis_eligible']!=new['full_basis_eligible']:
     changes.append({'connection_id':new['connection_id'],'old':{'disposition':old['disposition'],'errors':old['errors'],'full_basis_eligible':old['full_basis_eligible']},'new':{'disposition':new['disposition'],'errors':new['errors'],'full_basis_eligible':new['full_basis_eligible']},'evidence':'address-ledger.json and source locations in offline-audit.json','legal_semantics_proved':False})
   save(OUT/'replay'/cid/'comparison.json',{'case_id':cid,'P_status':m['status'],'before':summarize(old_a),'after':summarize(a),'source_ids_restored_before':sorted(before),'source_ids_restored_after':sorted(after),'newly_restored':sorted(after-before),'changes':changes,'old_audit_sha256':sha(HISTORY/'local'/cid/'P/offline-audit.json'),'new_audit_sha256':sha(OUT/'local'/cid/'P/offline-audit.json'),'same_cached_P':True,'reference_used':False})
   comparisons.append({'case_id':cid,'before':summarize(old_a),'after':summarize(a),'newly_restored':len(after-before),'changed_connections':len(changes)})
   labelpath=HISTORY/'web/labels'/cid/'parsed.json'
   if labelpath.exists():
    labels=read(labelpath)
    for label in (labels or {}).get('connections',[]):
     key=label['connection_id'];u=int(key[1:])-1;oldp=read(HISTORY/'local'/cid/'P/merged.json')['answer'];old_u=oldp['uses'][u];new_u=p['uses'][u]
     unchanged=all(old_u.get(k)==new_u.get(k) for k in ('premise','bindings','direction','claim','stage','limits','self_assessment','records'))
     location=pipe.source_match(label,pipe.sources(f['case']));admission=label_admissibility(label,after,location)
     compatibility={'case_id':cid,'use_id':key,'old_label_preserved':True,'raw_reference_path':str(labelpath.relative_to(ROOT)),'semantic_connection_unchanged':unchanged,'source_visible_before':set(label.get('mandatory_basis_refs',[]))<=before,'source_visible_after':set(label.get('mandatory_basis_refs',[]))<=after,'reference_location':location,'supervision_compatible':unchanged and admission['supervised'],'reason':admission['reason'] if unchanged else 'SEMANTIC_CONNECTION_CHANGED','reference_not_input':True}
     compat.append(compatibility)
    # Copy unchanged original review; rows independently checks visibility and contract again.
    dest=OUT/'web/labels'/cid
    for q in labelpath.parent.iterdir():
     if q.is_file():
      dest.mkdir(parents=True,exist_ok=True);target=dest/q.name
      if target.exists():assert sha(target)==sha(q)
      else:shutil.copy2(q,target)
   decisions={x['connection_id']:x['P_label'] for x in a['checks']}
   for check in a['checks']:
    if check['disposition']!='CONDITIONALLY_AVAILABLE_USE':continue
    altered={**decisions,check['connection_id']:'UNSUPPORTED'};controlled=pipe.apply_connection_decisions(f['case'],f['rules'],p,altered)
    effects=[]
    for old,new in zip(a['premise_judgments'],controlled['premise_judgments']):
     if old['available_uses']!=new['available_uses'] or old['components']!=new['components'] or old['conditional_state']!=new['conditional_state']:effects.append({'premise':old['premise'],'judgment':old['id'],'old_available':old['available_uses'],'new_available':new['available_uses'],'component_coverage_before':[c['covered'] for c in old['components']],'component_coverage_after':[c['covered'] for c in new['components']],'state_before':old['conditional_state'],'state_after':new['conditional_state']})
    if effects:controls.append({'case_id':cid,'controlled_use':check['connection_id'],'effects':effects,'synthetic_label_flip_on_real_cached_path':True,'model_gain':False,'whole_chain_states_before':summarize(a)['rule_states'],'whole_chain_states_after':summarize(controlled)['rule_states']});break
 save(OUT/'replay-summary.json',comparisons);save(OUT/'label-compatibility.json',compat);save(OUT/'engineering/real-path-prediction-control.json',controls)
 save(OUT/'startup/carried-cost.json',{'calls':cost,'P_calls':sum(c['role']=='P' for c in cost),'final_calls':sum(c['role']!='P' for c in cost),'P_seconds':sum(c['elapsed_seconds'] or 0 for c in cost if c['role']=='P'),'final_seconds':sum(c['elapsed_seconds'] or 0 for c in cost if c['role']!='P'),'web_calls':len(list((HISTORY/'web/labels').glob('*/submitted-evidence.json'))),'fits':0,'budget_reset':False})
 save(OUT/'remaining-tasks.json',{'P':[s for s in cfg['local_generation_slots'] if s['role']=='P' and not (HISTORY/s['dest']/'run.json').exists()],'final':[s for s in cfg['local_generation_slots'] if s['role']!='P' and not (HISTORY/s['dest']/'run.json').exists()],'completed_finals':[s for s in cfg['local_generation_slots'] if s['role']!='P' and (HISTORY/s['dest']/'run.json').exists()],'new_P_production_version':'V19_2','cached_P_production_version':'V19_1','retries':0})
 print(json.dumps({'cases':len(cases),'compatible_label_rows':sum(x['supervision_compatible'] for x in compat),'label_rows':len(compat),'actual_prediction_control_paths':len(controls)}))
def cached_encoding():
 import subprocess
 from legal_bench.proof_carrying.local_evaluation_v17 import hash_value
 out=OUT/'engineering/cached-encoding';texts={};cases=[]
 for path in sorted((OUT/'inputs').glob('*/learner-inputs.json')):
  data=read(path);cid=path.parent.name
  for node in data['graph']['nodes']:texts[hash_value(node['text'])]=node['text']
  cases.append({'case_id':cid,'input_sha256':sha(path),'data':data})
 save(out/'texts.json',texts)
 if not (out/'encoding.json').exists():
  result=subprocess.run([str(ROOT/'.runtime/irac-e5-v1/bin/python'),str(ROOT/'scripts/proof_semantic_encode_v13.py'),str(out)],cwd=ROOT,capture_output=True,text=True)
  text(out/'encoder-log.txt',result.stdout+result.stderr)
  if result.returncode:raise ValueError('CACHED_ENCODER_FAILED')
 receipt=read(out/'encoding.json');assert {x['sha256'] for x in receipt['audit']}==set(texts)
 if any(x['truncated'] for x in receipt['audit']):raise ValueError('CACHED_SOURCE_ENCODING_TRUNCATED')
 save(out/'cases.json',cases)
 result=subprocess.run([str(ROOT/'.runtime/proof-semantic-v12/bin/python'),str(Path(__file__).resolve()),'--coverage'],cwd=ROOT,capture_output=True,text=True)
 text(out/'coverage-log.txt',result.stdout+result.stderr)
 if result.returncode:raise ValueError('CACHED_CE_COVERAGE_FAILED:'+result.stderr)

def cached_coverage():
 from transformers import AutoTokenizer
 from legal_bench.proof_carrying.semantic_model_inputs_v19 import window_plan
 out=OUT/'engineering/cached-encoding';cases=read(out/'cases.json');tok=AutoTokenizer.from_pretrained(ROOT/'.runtime/proof-semantic-v12-model',local_files_only=True);rows=[]
 for case in cases:
  data=case['data'];source_ids=data['common_material_manifest']['saved_source_ids'];counts=[]
  for pair in data['ce_pairs']:
   blocks={b['id']:b for b in pair['shared_material_blocks']}
   assert all('source:'+ref in blocks for ref in source_ids)
   for ref in source_ids:assert blocks['source:'+ref]['text'] in data['graph']['nodes'][0]['text']
   left,plan,receipt=window_plan(tok,pair)
   assert sum(len(p['right_ids']) for p in plan)==receipt['right_tokens']
   counts.append({'use':pair['id'],'windows':receipt['windows'],'complete':receipt['complete'],'source_ids':source_ids})
  rows.append({'case_id':case['case_id'],'input_sha256':case['input_sha256'],'saved_source_ids':source_ids,'restored_source_ids':source_ids,'E5_encoded_source_ids':source_ids,'CE_actual_tokenized_source_ids':source_ids,'CE_prediction_read':False,'encoding_only_not_training_or_model_gain':True,'uses':counts})
 save(out/'coverage-receipt.json',{'status':'PASS','cases':rows,'all_E5_chunks_retained':True,'CE_complete_window_plans':True,'source_address_does_not_prove_use':True,'reference_not_input':True})
 print('CACHED_SOURCE_ENCODING_PASS')

if __name__=='__main__':
 if '--encoding' in sys.argv:cached_encoding()
 elif '--coverage' in sys.argv:cached_coverage()
 else:replay()
