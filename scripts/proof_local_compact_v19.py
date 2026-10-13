#!/usr/bin/env python3
"""V19 bounded phases. No references in inference; safe pause at saved-task boundaries."""
import argparse,datetime,hashlib,json,math,os,random,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from legal_bench.proof_carrying import local_pipeline_v19_compact as pipe
from legal_bench.proof_carrying.local_evaluation_v17 import LABELS,CLAIM_RULE,hash_value,blind_order,local_metrics
from legal_bench.proof_carrying.local_schedule_v19 import run as schedule,checkpoint,state
BASE=ROOT/'outputs/proof-local-comparison-v18';HISTORY=ROOT/'outputs/proof-local-pipeline-v19';OUT=HISTORY/'continuation-04';OLD=ROOT/'outputs/proof-local-comparison-v17';SEED=20261001
PREP=OUT/'preparation'; OLD_PREP=BASE/'continuation-02/preparation'

def read(p):return json.loads(Path(p).read_text())
def save(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);s=json.dumps(v,ensure_ascii=False,indent=2)+'\n'
 if p.exists():
  if p.read_text()!=s:raise ValueError('IMMUTABLE_RECORD_MISMATCH:'+str(p))
 else:p.write_text(s)
def text(p,s):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists() and p.read_text()!=s:raise ValueError('IMMUTABLE_TEXT_MISMATCH:'+str(p))
 if not p.exists():p.write_text(s)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def fixture(cid):return read(PREP/'inputs'/cid/'fixture.json')
def protocol():return read(OUT/'freeze/protocol.json')
def assert_frozen():
 p=protocol()
 for name,h in p['code_hashes'].items():
  if sha(ROOT/name)!=h:raise ValueError('FROZEN_CODE_CHANGED:'+name)
 for name,h in p.get('prepared_input_hashes',{}).items():
  if sha(ROOT/name)!=h:raise ValueError('FROZEN_INPUT_CHANGED:'+name)
 return p

def tokenizer():
 from transformers import AutoTokenizer
 path=(ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip()
 return AutoTokenizer.from_pretrained(path,local_files_only=True)
def count(tok,s):return len(tok.encode(s,add_special_tokens=False))
def render(tok,s):return tok.apply_chat_template([{'role':'user','content':s}],tokenize=False,add_generation_prompt=True,enable_thinking=False)




def skip(dest,reason):
 save(dest/'run.json',{'run_status':reason,'answer':None,'failure_stage':'DEPENDENCY','model_called':False})
 save(dest/'formal-answer.json',{'answer':None,'status':reason});return {'run_status':reason}

def early_P_stop():
 slots=[s for s in protocol()['local_generation_slots'] if s['role']=='P'][:2]
 rr=[read(OUT/s['dest']/'run.json') for s in slots if (OUT/s['dest']/'run.json').exists()]
 return len(rr)==2 and rr[0]['run_status']==rr[1]['run_status'] and rr[0]['run_status'] in ('REPETITION_ABORT','OUTPUT_TRUNCATED')

def run_local(phase,runner=None):
 cfg=assert_frozen()
 from legal_bench.proof_carrying.local_runtime_v19_compact import Runner,SETTINGS
 if cfg['runtime_settings']!=SETTINGS:raise ValueError('FROZEN_RUNTIME_SETTINGS_MISMATCH')
 if False:return 'STOPPED_BY_FROZEN_RULE'
 allslots=cfg['local_generation_slots'];first=cfg['first_DEV']
 slots=[s for s in allslots if (s['role']=='P')==(phase=='P')]
 if phase=='early':slots=[s for s in allslots if s['case_id']==first and s['role'] in ('P','A','B','C','D')]
 if runner is None:runner=Runner((ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),SETTINGS)
 def perform(s,d):
  cid=s['case_id'];f=fixture(cid);role=s['role'];isP=role=='P'
  used=sum(read(p).get('elapsed_seconds',0) or 0 for p in (OUT/'local').glob('*/*/run.json') if p.parent.name.startswith('P')==isP)
  carried=cfg.get('carried_cost',{})
  original_slots={x['dest'] for x in carried.get('calls',[])}
  used=(carried.get('P_seconds' if isP else 'final_seconds',0) or 0)+sum(read(q).get('elapsed_seconds',0) or 0 for q in (OUT/'local').glob('*/*/run.json') if q.parent.name.startswith('P')==isP and str(q.parent.relative_to(OUT)) not in original_slots)
  remaining=cfg['P_seconds_cap' if isP else 'final_seconds_cap']-used
  if remaining<=0:return skip(d,'STAGE_BUDGET_EXHAUSTED')
  if isP:prompt=(PREP/'inputs'/cid/(s['part']['id']+'-prompt.txt')).read_text();sc=read(PREP/'inputs'/cid/(s['part']['id']+'-schema.json'))
  else:
   intermediate={};sc=pipe.FINAL_SCHEMA
   if role=='B':
    a=OUT/'local'/cid/'A/formal-answer.json'
    if not a.exists() or read(a)['answer'] is None:return skip(d,'SKIPPED_A_DEPENDENCY')
    intermediate={'previous_direct_answer_model_proposed':read(a)['answer']}
   elif role!='A':
    path=OUT/'local'/cid/'P/merged.json';m=read(path) if path.exists() else {'answer':None}
    if m['answer'] is None:return skip(d,'SKIPPED_P_DEPENDENCY')
    p=m['answer'];intermediate={'raw_premise_local_proposals':[read(OUT/t['dest']/'parsed.json') for t in allslots if t['role']=='P' and t['case_id']==cid and (OUT/t['dest']/'parsed.json').exists()], 'proposal_address_mapping':[{'id':'K%03d'%(i+1),'unit':u['unit_scope'],'premise':u['premise'],'local_use':sum(1 for v in p['uses'][:i+1] if v['unit_scope']==u['unit_scope'])} for i,u in enumerate(p['uses'])],'proposal_coverage':m['status']}
    directories=[]
    for task in allslots:
     if task['role']!='P' or task['case_id']!=cid:continue
     version=OUT/task['dest']/'production-version.json'
     if version.exists() and read(version)['version'] in ('V19_2','V19_4','V19_5'):
      directories.append({'part':task['part']['id'],'source_directory':[{'choice':('SRC:'+str(i)) if read(version)['version'] in ('V19_4','V19_5') else i,'address':seg['id']} for i,seg in enumerate([x for x in f['case']['segments'] if x['id'] in task['part']['source_ids']],1)]})
    if directories:intermediate['raw_proposal_source_directories']=directories
    if role!='C':
     decisions=None
     if role in 'EFG':
      model={'E':'Flat','F':'CrossEncoder','G':'RGCN'}[role];pr=OUT/'training'/model/'all-candidate-predictions.json';manifest=pr.parent/'prediction-manifest.json'
      if not pr.exists() or not manifest.exists():return skip(d,'SKIPPED_MODEL_PREDICTION_MISSING')
      expected=[x['key'] for x in read(OUT/'encoding/inference-rows.json') if x['split']=='DEV']
      try:
       if read(manifest).get('predictions_sha256')!=sha(pr):raise ValueError('PREDICTION_FILE_HASH_MISMATCH')
       allpred=pipe.validate_predictions(read(pr),expected,read(manifest),sha(OUT/'encoding/pairs.json'))
      except ValueError as exc:
       save(d/'prediction-failure.json',{'error':str(exc),'model':model});return skip(d,'SKIPPED_MODEL_PREDICTION_INVALID')
      decisions={x.split('::')[-1]:v for x,v in allpred.items() if x.startswith(cid+'::')}
     audit=pipe.apply_connection_decisions(f['case'],f['rules'],p,decisions);save(d/'offline-audit.json',audit)
     from legal_bench.proof_carrying.local_checker_v19_refs import check
     ind=check(f['case'],f['rules'],p,decisions,audit);save(d/'independent-check.json',ind)
     if ind['status']!='OK':raise ValueError('INDEPENDENT_RECOMPUTATION_REJECTED')
     intermediate['program_checks']=pipe.compact_checks(audit)
     save(d/'prediction-transfer.json',[{'connection':x['connection_id'],'P':x['P_label'],'applied':x['applied_label'],'effect':x['disposition']} for x in audit['checks']])
   intermediate,receipt=pipe.display_material(intermediate);save(d/'display-receipt.json',receipt);prompt=pipe.final_prompt(f['case'],f['rules'],intermediate)
  if isP:save(d/'production-version.json',{'version':'V19_5','source_directory_sha256':hash_value([seg['id'] for seg in f['case']['segments'] if seg['id'] in s['part']['source_ids']])})
  result=runner.run(prompt,sc,d,s['max_tokens'],min(cfg['per_call_seconds_cap'],remaining),'FIXED')
  save(d/'formal-answer.json',{'answer':read(d/'parsed.json') if result['run_status']=='OK' else None,'status':result['run_status']})
  if isP:consolidate(cid)
  return result
 def after(s,r):
  if False:
   checkpoint(OUT,'early-P-stop',{'stopped':True,'reason':'FIRST_TWO_SAME_UNREADABLE_FLOW_FAILURE','calls':[x['dest'] for x in [s for s in allslots if s['role']=='P'][:2]]});return True
  return False
 result=schedule(OUT,slots,perform,after=after)
 checkpoint(OUT,'phase-'+phase,{'status':result,'slot_states':[{'dest':s['dest'],'state':state(OUT/s['dest'])} for s in slots]})
 if result=='STOPPED_BY_FROZEN_RULE':
  for cid in cfg['TRAIN']+cfg['DEV']:consolidate(cid,closed=True)
 return result

from legal_bench.proof_carrying.local_annotation_v18_recovery import ANNOTATION, label_admissibility

def annotation_task(cid):
 f=fixture(cid);p=read(OUT/'local'/cid/'P/merged.json')['answer'];data=read(OUT/'inputs'/cid/'learner-inputs.json');packets=[]
 for k,pkg in data['materials'].items():
  q=copy_packet(pkg);q['use'].pop('self_assessment',None);packets.append(q)
 task=ANNOTATION+'\nLEARNER-VISIBLE PACKETS (self assessment hidden only for reviewer):\n'+json.dumps(packets,ensure_ascii=False)+'\nCOMPLETE ALLOWED SOURCE FOR COVERAGE DIAGNOSTIC:\n'+pipe.source_text(f['case'])
 text(OUT/'web/tasks'/cid/'connection-annotation.txt',task)
 save(OUT/'web/tasks'/cid/'annotation-size.json',{'characters':len(task),'uses':len(p['uses']),'estimated_output_tokens':500+300*len(p['uses']),
      'outside_packet_supervision_excluded':True})
def copy_packet(x):return json.loads(json.dumps(x))

def encoding():
 assert_frozen();texts={};plans={};graphs={};pairs={};pool=[]
 for cid in protocol()['TRAIN']+protocol()['DEV']:
  path=OUT/'inputs'/cid/'learner-inputs.json'
  if not path.exists():continue
  data=read(path);g=data['graph'];plan=[];f=fixture(cid)
  for n in g['nodes']:
   h=hash_value(n['text']);texts[h]=n['text'];plan.append({'node':n['id'],'part_sha256':[h]})
  plans[cid]={'graph':plan};graphs[cid]=g
  for pair in data['ce_pairs']:
   key=cid+'::'+pair['id'];pairs[key]=pair;pool.append({'key':key,'case_id':cid,'dispute_id':f['case']['dispute_id'],'request_id':'Q1','use_id':pair['id'],'split':f['case']['split']})
 for name,value in [('texts',texts),('plans',plans),('graphs',graphs),('pairs',pairs),('inference-rows',pool)]:save(OUT/'encoding'/(name+'.json'),value)

def rows():
 good=[];excluded=[]
 for base in read(OUT/'encoding/inference-rows.json'):
  cid=base['case_id'];path=OUT/'web/labels'/cid/'parsed.json'
  if not path.exists():excluded.append({**base,'reason':'LABEL_TECHNICAL_MISSING'});continue
  raw_label_file=read(path)
  if not isinstance(raw_label_file,dict):excluded.append({**base,'reason':'LABEL_TECHNICAL_FAILURE'});continue
  matches=[r for r in raw_label_file['connections'] if r['connection_id']==base['use_id']]
  if len(matches)!=1:excluded.append({**base,'reason':'LABEL_ADDRESS_MISSING_OR_DUPLICATE'});continue
  label=matches[0];f=fixture(cid);location=pipe.source_match(label,pipe.sources(f['case']));data=read(OUT/'inputs'/cid/'learner-inputs.json');pkg=data['materials'][base['use_id']]
  visible=set(data['common_material_manifest']['saved_source_ids'])
  verdict=label_admissibility(label,visible,location)
  if not verdict['supervised']:
   excluded.append({**base,'reason':verdict['reason'],'raw':label,'location':location});continue
  p=read(OUT/'local'/cid/'P/merged.json')['answer'];u=p['uses'][int(base['use_id'][1:])-1];prem=next(x for r in f['rules'] for x in r['premises'] if x['id']==u['premise']);a=pipe.apply_connection_decisions(f['case'],f['rules'],p)
  check=next(x for x in a['checks'] if x['connection_id']==base['use_id'])
  good.append({**base,'label':label['label'],'premise_family':prem.get('family') or 'EXACT:'+hash_value(prem['text']),
      'P_self_assessment':u['self_assessment'],'structurally_valid':not check['errors'],'basis':label['basis'],'source_location':location,
      'origin':'EXTRA_HIGH_MODEL_SOURCE_REVIEW_NOT_HUMAN_GOLD','input_coverage_limited':False})
 save(OUT/'freeze/training-rows.json',good);save(OUT/'freeze/unsupervised-candidates.json',excluded)
 train=[x for x in good if x['split']=='TRAIN'];dev=[x for x in good if x['split']=='DEV'];classes={x['label'] for x in train}
 gate=len({x['dispute_id'] for x in train})>=2 and {'SUPPORTED','UNSUPPORTED'}<=classes and bool(dev)
 save(OUT/'training-gate.json',{'start_permitted':gate,'effective_TRAIN_disputes':len({x['dispute_id'] for x in train}),
   'effective_DEV_disputes':len({x['dispute_id'] for x in dev}),'TRAIN_classes':sorted(classes),'reference_used_in_input':False,
   'excluded_not_removed_from_pool':len(excluded),'scope':'DEVELOPMENT_USE_CLASSIFICATION_NOT_WHOLE_LEGAL_TRUTH'})
 from legal_bench.proof_carrying.local_reporting_v18 import local_report
 save(OUT/'pretraining-baselines.json',local_report(good,{}))
 save(OUT/'pretraining-data-audit.json',{'TRAIN_cases':sorted({x['case_id'] for x in train}),'DEV_cases':sorted({x['case_id'] for x in dev}),'labels':{split:{label:sum(r['split']==split and r['label']==label for r in good) for label in LABELS} for split in ('TRAIN','DEV')},'structurally_valid':sum(r['structurally_valid'] for r in good),'source_coverage_excluded':sum(x['reason']=='INPUT_COVERAGE_LIMITED' for x in excluded),'P_errors':sum(r['label']!=r['P_self_assessment'] for r in good),'input_references':False,'no_baseline_ceiling_gate':True,'prior_family_match_scope':'EXACT explicit family or exact proposition SHA; no automatic synonyms'})
 return good

def fit(kind):
 cfg=assert_frozen();gate=read(OUT/'training-gate.json')
 if not gate['start_permitted']:raise ValueError('TRAINING_GATE_NOT_MET')
 from legal_bench.proof_carrying.local_fit_v19 import fit_graph,fit_ce
 data=read(OUT/'freeze/training-rows.json');inf=[r for r in read(OUT/'encoding/inference-rows.json') if r['split']=='DEV'];dest=OUT/'training'/kind
 if dest.exists():raise ValueError('NO_FIT_RESTART')
 deadline=time.monotonic()+cfg['models'][kind]['max_seconds']
 if kind=='CrossEncoder':
  result=fit_ce(SEED,read(OUT/'encoding/pairs.json'),data,dest,deadline,inference_rows=inf);prediction_manifest(dest);return result
 import numpy as np,mlx.core as mx
 from legal_bench.proof_carrying.semantic_model_inputs_v19 import graph_arrays
 vectors=np.load(OUT/'encoding/vectors.npz');graphs=read(OUT/'encoding/graphs.json');plans=read(OUT/'encoding/plans.json')
 allgraphs={fixture(cid)['case']['dispute_id']:graph_arrays(g,plans[cid],vectors) for cid,g in graphs.items()}
 for g in allgraphs.values():
  for k in ('x','adj','edges'):g[k]=mx.array(g[k])
 result=fit_graph(kind,SEED,allgraphs,data,dest,deadline,inference_rows=inf);prediction_manifest(dest);return result

def prediction_manifest(dest):
 path=dest/'all-candidate-predictions.json'
 if path.exists():save(dest/'prediction-manifest.json',{'version':'V19_4','class_order':list(LABELS),'input_sha256':sha(OUT/'encoding/pairs.json'),'predictions_sha256':sha(path)})

def main():
 parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['capacity','freeze','early','P','final','encoding','rows','fit']);parser.add_argument('--kind',choices=['Flat','RGCN','CrossEncoder']);args=parser.parse_args();os.chdir(ROOT)
 if args.phase=='capacity':print(json.dumps({k:v for k,v in capacity().items() if k not in ('cases','P_slots','final_slots')},indent=2))
 elif args.phase=='freeze':freeze()
 elif args.phase in ('early','P','final'):run_local(args.phase)
 elif args.phase=='encoding':encoding()
 elif args.phase=='rows':rows()
 elif args.phase=='fit':fit(args.kind)



def capacity():
 if (PREP/'capacity-plan.json').exists():return read(PREP/'capacity-plan.json')
 cfg=read(HISTORY/'continuation-03/freeze/protocol.json');tok=tokenizer();issues=[];slots=[];cases=[]
 for cid in cfg['TRAIN']+cfg['DEV']:
  source=HISTORY/'continuation-03/preparation/inputs'/cid/'fixture.json';text(PREP/'inputs'/cid/'fixture.json',source.read_text());f=read(source)
  for original in [s for s in cfg['local_generation_slots'] if s['role']=='P' and s['case_id']==cid]:
   part=original['part'];view={**f['case'],'segments':[x for x in f['case']['segments'] if x['id'] in part['source_ids']]};selected=[r for r in f['rules'] if r['id'] in part['rule_ids']];dest=OUT/original['dest']
   if (dest/'run.json').exists():
    prompt=(dest/'prompt.txt').read_text();sc=read(dest/'schema.json');version=read(dest/'production-version.json')['version'];reuse=True
   else:prompt=pipe.proposal_prompt(f['case'],f['rules'],part);sc=pipe.schema(selected,view);version='V19_5';reuse=False
   n=count(tok,render(tok,prompt));slot={**original,'rendered_input_tokens':n,'required_total_tokens':n+16384+256,'production_contract':version,'already_completed_reused_no_new_call':reuse}
   if not reuse and slot['required_total_tokens']>65536:issues.append({'case_id':cid,'part':part['id'],'reason':'TYPED_INPUT_TOO_LONG_NO_SOURCE_TRUNCATION','required':slot['required_total_tokens']})
   text(PREP/'inputs'/cid/(part['id']+'-prompt.txt'),prompt);save(PREP/'inputs'/cid/(part['id']+'-schema.json'),sc);slots.append(slot)
  prompt=pipe.final_prompt(f['case'],f['rules'],{});n=count(tok,render(tok,prompt));text(PREP/'inputs'/cid/'A-prompt.txt',prompt);cases.append({'case_id':cid,'A_input_tokens':n,'A_required_total_tokens':n+8192+256})
 order={s['dest']:i for i,s in enumerate(cfg['local_generation_slots'])};slots.sort(key=lambda s:order[s['dest']]);finals=[s for s in cfg['local_generation_slots'] if s['role']!='P']
 plan={'launch_permitted':True,'issues':issues,'overflow_policy':'Single affected slot technical null; preserve full material and continue independent slots, no repartition','cases':cases,'P_slots':slots,'final_slots':finals,'web_plan':cfg['web_slots'],'first_DEV':cfg['first_DEV'],'first_two_P_stop':cfg['early_P_stop'],'source_policy':cfg['context_policy'],'history_counts_against_budget':True,'remaining_P_contract':'V19_4_TYPED_REFERENCE_NAMESPACE','whole_batch_uniform_production_contract':False}
 save(PREP/'capacity-plan.json',plan);return plan

def consolidate(cid,closed=False):
 from legal_bench.proof_carrying.local_pipeline_v19_compact import convert
 f=fixture(cid);slots=[s for s in protocol()['local_generation_slots'] if s['role']=='P' and s['case_id']==cid];parts=[];rawparts=[];states=[];maps=[]
 for slot in slots:
  d=OUT/slot['dest'];ss=state(d);states.append({'part':slot['part']['id'],'state':ss})
  raw=read(d/'parsed.json') if ss=='COMPLETED' else None;rawparts.append(raw)
  if raw is not None:
   view={**f['case'],'segments':[x for x in f['case']['segments'] if x['id'] in slot['part']['source_ids']]}
   production=read(d/'production-version.json')['version'] if (d/'production-version.json').exists() else 'V19_2'
   transformed,ledger=convert(raw,view,production)
   from legal_bench.proof_carrying.local_pipeline_v19_compact import independent_import as check_import
   transport=check_import(raw,transformed,view,production)
   if transport['status']!='OK':raise ValueError('INDEPENDENT_REFERENCE_IMPORT_REJECTED:'+str(transport['errors']))
   parts.append((slot['part']['id'],transformed));maps.append({'part':slot['part']['id'],'production':production,'ledger':ledger,'raw_unchanged_sha256':sha(d/'parsed.json')})
  else:parts.append((slot['part']['id'],None))
 any_valid=any(v is not None for _,v in parts);terminal=all(x['state'] in ('COMPLETED','ACTUAL_TECHNICAL_FAILURE','SKIPPED_DEPENDENCY') for x in states);p,ledger=pipe.merge_parts(parts) if any_valid else (None,[])
 result={'answer':p,'status':'COMPLETE' if all(x['state']=='COMPLETED' for x in states) else 'PARTIAL' if any_valid else 'NO_READABLE_PART','finalized':terminal or closed,'part_states':states,'part_ledger':ledger,'batch_closed':closed,'production_versions':sorted(set(x['production'] for x in maps))}
 checkpoint(OUT,cid+'-P',result)
 if result['finalized'] and not (OUT/'local'/cid/'P/merged.json').exists():save(OUT/'local'/cid/'P/merged.json',result)
 if p is not None and result['finalized']:
  save(OUT/'local'/cid/'P/address-ledger.json',maps);audit=pipe.apply_connection_decisions(f['case'],f['rules'],p)
  from legal_bench.proof_carrying.local_checker_v19_refs import check
  ind=check(f['case'],f['rules'],p,None,audit)
  if ind['status']!='OK':raise ValueError('INDEPENDENT_RECOMPUTATION_REJECTED')
  save(OUT/'local'/cid/'P/offline-audit.json',audit);save(OUT/'local'/cid/'P/independent-check.json',ind);save(OUT/'inputs'/cid/'learner-inputs.json',pipe.learner_inputs(f['case'],f['rules'],p));annotation_task(cid)
 return result

def freeze():
 if (OUT/'freeze/protocol.json').exists():return assert_frozen()
 cfg=read(OUT/'startup/pending-protocol.json')
 for name,h in cfg['code_hashes'].items():
  if sha(ROOT/name)!=h:raise ValueError('PARENT_FROZEN_SOURCE_CHANGED:'+name)
 gate=read(OUT/'engineering/acceptance.json')
 if gate['status']!='PASS':raise ValueError('REFERENCE_ENTRY_NOT_ACCEPTED')
 files=read(OUT/'startup/new-code-files.json')
 cfg['code_hashes'].update({name:sha(ROOT/name) for name in files})
 for name in cfg['code_hashes']:text(OUT/'freeze/code'/name,(ROOT/name).read_text())
 cfg['prepared_input_hashes']={str(p.relative_to(ROOT)):sha(p) for p in (PREP/'inputs').rglob('*') if p.is_file()}
 cfg['repair_record_hashes']={str(p.relative_to(ROOT)):sha(p) for p in [OUT/'freeze/generation-contract.json',OUT/'startup/window-preregistration.json',OUT/'engineering/acceptance.json',OUT/'startup/carried-cost.json']}
 cfg['frozen_at']=utc();save(OUT/'freeze/protocol.json',cfg)
 return assert_frozen()

if __name__=='__main__':main()
