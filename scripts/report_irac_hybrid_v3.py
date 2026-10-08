"""Aggregate immutable attempts; no model execution or answer modification."""
import json,csv,hashlib
from pathlib import Path
from collections import Counter, defaultdict
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.irac_application.aligned_logic import evaluate
R=Path('outputs/irac-hybrid-decision-v3')
read=lambda p:json.loads(Path(p).read_text())
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def formula_audit(parsed,template):
 rows=[]
 if not parsed:return rows
 defs={e['id']:e['expression'] for e in template['elements']}
 for a in parsed['answers']:
  claim=next(c for c in template['claims'] if c['id']==a['claim_id']);groups=defaultdict(dict)
  for x in a['conditions']:
   # Literal declared binding grouping only: no string similarity or cross-event join.
   groups[x['binding']][x['test_id']]={'status':'SUPPORTED' if x['prediction']=='PREDICT_SUPPORTED' else 'REFUTED'}
  for binding,states in groups.items():
   result=evaluate(claim['expression'],states,defs)
   rows.append({'claim_id':a['claim_id'],'literal_declared_binding':binding,'formula_from_predicted_directions':result,'request_prediction':a['prediction'],'review_flag':'PREDICTED_CONDITION_FORMULA_DISAGREEMENT' if (result['status']=='SUPPORTED' and a['prediction']=='PREDICT_DENY') or (len(groups)==1 and result['status']=='REFUTED' and a['prediction']=='PREDICT_GRANT') else None,'limitations':'No identity verification; incomplete bindings not joined. Formula checks model directions, not proof or evidence truth. Flag is reviewed, never overwrites answer.'})
 return rows

def main():
 ledger=read(R/'run-ledger.json');assert ledger['status'] in ('COMPLETE','STOPPED','ENVIRONMENT_BLOCKED'),'wait until batch ends'
 order=read(R/'protocol.json')['order'];details=[];case_rows=[];dossiers=[]
 for cid in read(R/'protocol.json')['cases']:
  material=read(R/'sources'/f'{cid}.json');law=read(R/'sources'/f"{material['family']}-law.json");sources=dict(material['sources']);sources.update({x['source_id']:x for x in law})
  case={'case_id':cid,'family':material['family']};dossier={'case_id':cid,'allowed_sources':sources,'outputs':{},'existing_reference_path':str(Path('outputs/gnn-irac-aligned-v2/references')/f'{cid}.json'),'warning':'Existing UNRESOLVED labels are not binary gold. Binding compatibility requires source review.'}
  for stage in ['A','proposal','B','C']:
   p=R/'runs'/cid/stage;result=read(p/'result.json') if (p/'result.json').exists() else {'run_status':'NOT_RUN','prediction':None}
   meta=read(p/'run.json') if (p/'run.json').exists() else {};parsed=result.get('prediction')
   row={'case_id':cid,'method':stage,'run_status':result['run_status'],'prediction':parsed,'input_tokens':meta.get('prompt_tokens'),'output_tokens':meta.get('output_tokens'),'seconds':meta.get('elapsed_seconds'),'peak_mlx_gb':meta.get('peak_mlx_memory_gb'),'peak_process_rss_gb':meta.get('peak_rss_gb'),'reason':result.get('reason',meta.get('error')),'path':str(p),'finish_reason':meta.get('finish_reason'),'mask_calls':meta.get('schema_mask_calls')};details.append(row);dossier['outputs'][stage]=row
   if stage!='proposal':dossier['outputs'][stage]['formula_audit']=formula_audit(parsed,read(R/'templates'/f"{material['family']}.json"))
   case[stage+'_status']=row['run_status'];case[stage+'_seconds']=row['seconds'];case[stage+'_input_tokens']=row['input_tokens'];case[stage+'_output_tokens']=row['output_tokens']
   if stage!='proposal':case[stage+'_direction']=';'.join(a['claim_id']+':'+a['prediction'] for a in parsed['answers']) if parsed else None
  for stage in ['B','C']:
   case[stage+'_pipeline_seconds']=(case['proposal_seconds'] or 0)+(case[stage+'_seconds'] or 0)
   case[stage+'_pipeline_input_tokens']=(case['proposal_input_tokens'] or 0)+(case[stage+'_input_tokens'] or 0)
   case[stage+'_pipeline_output_tokens']=(case['proposal_output_tokens'] or 0)+(case[stage+'_output_tokens'] or 0)
  if (R/'checks'/f'{cid}.json').exists():dossier['program_checks']=read(R/'checks'/f'{cid}.json')
  dest=R/'review-dossiers';dest.mkdir(exist_ok=True);save(dest/f'{cid}.json',dossier);case_rows.append(case)
 save(R/'all-results.json',details)
 with (R/'technical-comparison.csv').open('w') as h:
  w=csv.DictWriter(h,fieldnames=list(case_rows[0]));w.writeheader();w.writerows(case_rows)
 completed=[x for x in details if x['run_status']=='OK'];actual=[x for x in details if (Path(x['path'])/'start.json').exists()]
 save(R/'cost.json',{'generation_calls':len(actual),'status_counts':dict(Counter(x['run_status'] for x in details)),'final_status_counts':dict(Counter(x['run_status'] for x in details if x['method']!='proposal')),'successful_proposals':sum(x['method']=='proposal' for x in completed),'generation_seconds':sum(x['seconds'] or 0 for x in actual),'input_tokens_actual_attempts':sum(x['input_tokens'] or 0 for x in actual),'output_tokens_actual_attempts':sum(x['output_tokens'] or 0 for x in actual),'peak_mlx_gb':max([x['peak_mlx_gb'] or 0 for x in actual],default=0),'peak_process_rss_gb':max([x['peak_process_rss_gb'] or 0 for x in actual],default=0),'load_seconds':read(R/'freeze/token-preflight.json').get('load_seconds'),'training_calls':0,'web_calls':0,'retries':0,'B_C_shared_proposal':'counted once in actual experiment total; counted for each two-stage method cost','note':'source review and preparation time not included; process RSS is cumulative process maximum, MLX peak is per call.'})
 before=read(R/'preservation-before.json');changed=[p for p,h in before.items() if not Path(p).exists() or hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h];save(R/'preservation-after.json',{'checked':len(before),'changed_or_missing':changed});assert not changed,changed
 frozen=read(R/'freeze/config.json');files={**frozen['files'],**frozen['live_code'],**frozen['original_v2_prediction_hashes']};bad=[p for p,h in files.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h];save(R/'freeze-integrity.json',{'checked':len(files),'changed':bad});assert not bad,bad
 print(json.dumps(read(R/'cost.json'),indent=2))
if __name__=='__main__':main()
