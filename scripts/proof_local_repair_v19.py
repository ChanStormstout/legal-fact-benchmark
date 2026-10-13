#!/usr/bin/env python3
"""V19 bounded phases. No references in inference; safe pause at saved-task boundaries."""
import argparse,datetime,hashlib,json,math,os,random,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from legal_bench.proof_carrying import local_pipeline_v19_repair as pipe
from legal_bench.proof_carrying.local_evaluation_v17 import LABELS,CLAIM_RULE,hash_value,blind_order,local_metrics
from legal_bench.proof_carrying.local_schedule_v19 import run as schedule,checkpoint,state
BASE=ROOT/'outputs/proof-local-comparison-v18';HISTORY=ROOT/'outputs/proof-local-pipeline-v19';OUT=HISTORY/'continuation-01';OLD=ROOT/'outputs/proof-local-comparison-v17';SEED=20261001
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

def capacity():
 if (PREP/'capacity-plan.json').exists():return read(PREP/'capacity-plan.json')
 original=read(OLD_PREP/'capacity-plan.json');tok=tokenizer();issues=[];slots=[];cases=[]
 for row in original['cases']:
  cid=row['case_id'];source=OLD_PREP/'inputs'/cid/'fixture.json';f=read(source)
  if sha(ROOT/f['case']['source_path'])!=f['case']['source_sha256']:raise ValueError('SOURCE_CHANGED')
  text(PREP/'inputs'/cid/'fixture.json',source.read_text())
  groups=[]
  for s in original['P_slots']:
   if s['case_id']==cid and s['part']['rule_ids'] not in groups:groups.append(s['part']['rule_ids'])
  for n,group in enumerate(groups,1):
   part={'id':'P%02d'%n,'rule_ids':group,'source_ids':[s['id'] for s in f['case']['segments']], 'source_policy':'COMPLETE_ALLOWED_SOURCE_IF_CAPACITY; NO_MECHANICAL_4000_WINDOW'}
   prompt=pipe.proposal_prompt(f['case'],f['rules'],part);nt=count(tok,render(tok,prompt))
   parts=[part] if nt+16384+256<=65536 else [s['part'] for s in original['P_slots'] if s['case_id']==cid and s['part']['rule_ids']==group]
   for part in parts:
    prompt=pipe.proposal_prompt(f['case'],f['rules'],part);nt=count(tok,render(tok,prompt));sc=pipe.schema([r for r in f['rules'] if r['id'] in part['rule_ids']])
    slot={'role':'P','case_id':cid,'dest':'local/'+cid+'/'+part['id'],'part':part,'max_tokens':16384,'rendered_input_tokens':nt,'reserved_output_tokens':16384,'required_total_tokens':nt+16384+256}
    if slot['required_total_tokens']>65536:issues.append({'case_id':cid,'part':part['id'],'status':'INPUT_TOO_LONG','required':slot['required_total_tokens']})
    text(PREP/'inputs'/cid/(part['id']+'-prompt.txt'),prompt);save(PREP/'inputs'/cid/(part['id']+'-schema.json'),sc);slots.append(slot)
  prompt=pipe.final_prompt(f['case'],f['rules'],{});nt=count(tok,render(tok,prompt));text(PREP/'inputs'/cid/'A-prompt.txt',prompt)
  cases.append({**row,'A_input_tokens':nt,'A_reserved_output_tokens':8192,'A_required_total_tokens':nt+8192+256})
 # First DEV is fixed by prior split order. Its formal P calls are the first two, not a pre-run.
 first=read(BASE/'continuation-02/freeze/protocol.json')['DEV'][0]
 slots=[s for s in slots if s['case_id']==first]+[s for s in slots if s['case_id']!=first]
 finals=[{**s,'max_tokens':8192} for s in original['final_slots']]
 early=[next(s for s in finals if s['case_id']==first and s['role']==m) for m in 'ABCD']
 finals=early+[s for s in finals if s not in early]
 plan={**original,'at':utc(),'cases':cases,'P_slots':slots,'final_slots':finals,'static_issues':issues,'launch_permitted':not issues and len(slots)<=87,
       'generation_seconds_cap':129600,'P_seconds_allocation':86400,'final_seconds_reserved':43200,'per_call_seconds_cap':3600,
       'total_context_tokens':65536,'template_margin_tokens':256,'first_DEV':first,'first_two_P_stop':'Both same repetition or truncation, unreadable => stop further P; no prompt retry',
       'source_policy':'Full allowed case where it fits; otherwise old exact windows with preserved boundary and coverage.',
       'old_P_reuse':'NONE; new premise-local contract; raw history retained',
       'dynamic_C_G_capacity':'Fixed lossless display; complete source retained; overflow technical null'}
 save(PREP/'capacity-plan.json',plan);return plan

def freeze():
 if (OUT/'freeze/protocol.json').exists():return assert_frozen()
 plan=capacity()
 if not plan['launch_permitted']:raise ValueError('STATIC_CAPACITY_BLOCKED; no generation started')
 old=read(BASE/'continuation-02/freeze/protocol.json');files=['legal_bench/proof_carrying/local_pipeline_v18.py','legal_bench/proof_carrying/local_runtime_v18.py','legal_bench/proof_carrying/local_checker_v18.py','legal_bench/proof_carrying/local_schedule_v18.py','scripts/proof_local_comparison_v18.py','legal_bench/proof_carrying/local_fit_v17.py','legal_bench/proof_carrying/semantic_models_v12.py','legal_bench/proof_carrying/semantic_model_inputs_v13.py','legal_bench/proof_carrying/semantic_interface_v13.py','legal_bench/proof_carrying/quote_locator_v16.py','legal_bench/mlx_json_constraint_v2.py','scripts/proof_semantic_encode_v13.py','legal_bench/proof_carrying/local_pipeline_v17.py','legal_bench/proof_carrying/local_evaluation_v17.py','legal_bench/proof_carrying/local_reporting_v18.py','legal_bench/proof_carrying/local_fit_v18.py','scripts/proof_local_integrate_v18.py','legal_bench/irac_application/text_cache.py','legal_bench/mlx_json_constraint.py','legal_bench/rules_verdict_v1/source_views.py','legal_bench/rules_verdict_v1/repetition_v9.py','outputs/gnn-irac-aligned-v2/text-cache/encoder.json']
 files += ['scripts/proof_local_comparison_v18_recovery.py','scripts/proof_local_integrate_v18_recovery.py','scripts/proof_local_recovery_accept_v18.py','legal_bench/proof_carrying/local_pipeline_v18_recovery.py','legal_bench/proof_carrying/local_runtime_v19.py','legal_bench/proof_carrying/local_annotation_v18_recovery.py']
 import ast
 todo=list(files);allfiles=set(files)
 while todo:
  name=todo.pop()
  if not name.endswith('.py'):continue
  tree=ast.parse((ROOT/name).read_text());package=name.replace('/','.').rsplit('.',2)[0]
  for node in ast.walk(tree):
   module=None
   if isinstance(node,ast.ImportFrom):
    if node.level:
     base=package.split('.')
     if node.level>1:base=base[:-(node.level-1)]
     module='.'.join(base)+('.'+node.module if node.module else '')
    else:module=node.module
   if module and module.startswith(('legal_bench.','scripts.')):
    path=module.replace('.','/')+'.py'
    if (ROOT/path).exists() and path not in allfiles:allfiles.add(path);todo.append(path)
 allfiles.update(['legal_bench/proof_carrying/local_pipeline_v19.py','legal_bench/proof_carrying/local_runtime_v19.py','legal_bench/proof_carrying/local_schedule_v19.py','legal_bench/proof_carrying/local_checker_v19.py','legal_bench/proof_carrying/repetition_v19.py','legal_bench/proof_carrying/local_fit_v19.py','legal_bench/proof_carrying/semantic_model_inputs_v19.py','scripts/proof_local_comparison_v19.py','scripts/proof_local_integrate_v19.py','tests/test_local_pipeline_v19.py']);allfiles.update(['legal_bench/proof_carrying/source_contract_v19.py','legal_bench/proof_carrying/local_runtime_v19_repair.py','legal_bench/proof_carrying/local_pipeline_v19_repair.py','legal_bench/proof_carrying/local_checker_v19_repair.py','scripts/proof_local_repair_v19.py','scripts/proof_local_integrate_v19_repair.py','scripts/proof_local_replay_v19_repair.py','tests/test_local_repair_v19.py']);files=sorted(allfiles);hashes={f:sha(ROOT/f) for f in files}
 for f in files:text(OUT/'freeze/code'/f,(ROOT/f).read_text())
 cfg={**old,'version':'V19_2','frozen_at':utc(),'code_hashes':hashes,'local_generation_slots':plan['P_slots']+plan['final_slots'],
      'P_slot_cap':87,'final_slot_cap':70,'local_slot_cap':157,'total_local_generation_seconds_cap':129600,'P_seconds_cap':86400,'final_seconds_cap':43200,'per_call_seconds_cap':3600,
      'web_slot_cap':70,'web_mode':'Extra High required; actual visible model/settings verified before first new submission, never inferred',
      'label_contract':{'unit':'ONE_DECLARED_USE_EXACT_SOURCE_OBJECT_STAGE_DIRECTION_SCOPE','classes':LABELS,
        'SUPPORTED_not_whole_TRUE':True,'valid_opposition_supported':True,'out_of_packet_labels_not_supervised':True,'wrong_quote_not_rescued':True},
      'context_policy':plan['source_policy'],'restore_policy':'ALL_RECORD_USE_WITNESS_OPPOSITION_OBJECT_REFS_PLUS_FIXED_ADJACENT_CONTEXT; NEIGHBOUR_CONTEXT_ONLY',
      'same_information':'ALL_NODE_AND_EDGE_CONTENT_VISIBLE_TO_ALL_THREE_METHODS; CE_DIFFERENT_ENCODER_NOT_PURE_GRAPH_ABLATION',
      'training_gate':'MULTIPLE_TRAIN_DISPUTES_WITH_POSITIVE_AND_NEGATIVE_VALID_LABELS; NO_LEAKAGE; COMMON_INPUT_VALID',
      'stage_reservations':{'P':86400,'final':43200},'retries':0}
 from legal_bench.proof_carrying.local_runtime_v19_repair import SETTINGS
 cfg['runtime_settings']=dict(SETTINGS);cfg['local_model']={**old['local_model'],'P_max_tokens':16384,'final_max_tokens':8192,'context_tokens':65536,'timeout_seconds':3600};cfg['web_slots']=plan['web_plan']
 cfg['label_contract']=read(OUT/'freeze/annotation-contract.json');cfg['resource_support']=read(BASE/'continuation-02/engineering/resource-support.json')
 cfg['display_policy']=pipe.DISPLAY_POLICY;cfg['early_P_stop']=plan['first_two_P_stop'];cfg['first_DEV']=plan['first_DEV'];cfg['generation_organization']='PREMISE_LOCAL_WITH_EXPLICIT_EVIDENCE_DEPENDENCIES';cfg['cross_rule_contract_inventory']=read(OUT/'engineering/rule-contract-inventory.json');cfg['engineering_gate']=read(OUT/'engineering/integration-acceptance.json')
 if cfg['engineering_gate']['status']!='PASS':raise ValueError('ACTUAL_ENTRY_GATE_FAILED')
 cfg['prepared_input_hashes']={str(p.relative_to(ROOT)):sha(p) for p in (PREP/'inputs').rglob('*') if p.is_file()}
 cfg['carried_cost']=read(OUT/'startup/carried-cost.json');cfg['repair_recovery_gate']=read(OUT/'engineering/recovery-gate.json')
 if not cfg['repair_recovery_gate']['resume_remaining_P_permitted']:raise ValueError('REPAIR_RECOVERY_GATE_NOT_MET')
 cfg['repair_record_hashes']={str(path.relative_to(ROOT)):sha(path) for path in [OUT/'label-compatibility.json',OUT/'replay-summary.json',OUT/'remaining-tasks.json',OUT/'final-reuse-compatibility.json',OUT/'engineering/recovery-gate.json']}
 cfg['production_policy']={'cached_P':'V19_1_UNCHANGED_RAW_WITH_DETERMINISTIC_ADAPTER','remaining_P':'V19_2_SOURCE_DIRECTORY_AND_EXPLICIT_LIMIT_SCOPE','whole_batch_uniform_production_contract':False,'historical_calls_counted':True}
 save(OUT/'freeze/protocol.json',cfg);save(OUT/'freeze/evaluation-contract.json',old['evaluation']);save(OUT/'freeze/final-schema.json',pipe.FINAL_SCHEMA)
 # Reuse the full frozen reference; preserve old High provenance and all amendments.
 ref=[]
 for cid in old['DEV']:
  path=BASE/'continuation-02/private/frozen-references'/cid/'checklist.json';v=read(path)
  save(OUT/'private/frozen-references'/cid/'checklist.json',{**v,'V19_reuse_provenance':{'path':str(path.relative_to(ROOT)),'sha256':sha(path),'original_web_setting':'High; NOT_EXTRA_HIGH','content_unchanged':True}})
  ref.append({'case_id':cid,'path':str(path.relative_to(ROOT)),'source_sha256':sha(path),'key_items':len(v['key_items']),'original_setting':'High'})
 save(OUT/'freeze/reference-checklists-manifest.json',ref)
 return cfg

def consolidate(cid,closed=False):
 f=fixture(cid);slots=[s for s in protocol()['local_generation_slots'] if s['role']=='P' and s['case_id']==cid];parts=[];states=[]
 for s in slots:
  d=OUT/s['dest'];ss=state(d);states.append({'part':s['part']['id'],'state':ss})
  parts.append((s['part']['id'],read(d/'parsed.json') if ss=='COMPLETED' else None))
 any_valid=any(v is not None for _,v in parts);terminal=all(x['state'] in ('COMPLETED','ACTUAL_TECHNICAL_FAILURE','SKIPPED_DEPENDENCY') for x in states)
 p,ledger=pipe.merge_parts(parts) if any_valid else (None,[])
 result={'answer':p,'status':'COMPLETE' if all(x['state']=='COMPLETED' for x in states) else 'PARTIAL' if any_valid else 'NO_READABLE_PART',
         'finalized':terminal or closed,'part_states':states,'part_ledger':ledger,'batch_closed':closed}
 path=checkpoint(OUT,cid+'-P',result)
 if result['finalized'] and not (OUT/'local'/cid/'P/merged.json').exists():save(OUT/'local'/cid/'P/merged.json',result)
 if p is not None:
  audit=pipe.apply_connection_decisions(f['case'],f['rules'],p);checkpoint(OUT,cid+'-audit',audit)
  from legal_bench.proof_carrying.local_checker_v19_repair import check
  independent=check(f['case'],f['rules'],p,None,audit)
  if independent['status']!='OK':raise ValueError('INDEPENDENT_RECOMPUTATION_REJECTED')
  if result['finalized']:
   save(OUT/'local'/cid/'P/offline-audit.json',audit);save(OUT/'local'/cid/'P/independent-check.json',independent)
   save(OUT/'inputs'/cid/'learner-inputs.json',pipe.learner_inputs(f['case'],f['rules'],p));annotation_task(cid)
 return result

def skip(dest,reason):
 save(dest/'run.json',{'run_status':reason,'answer':None,'failure_stage':'DEPENDENCY','model_called':False})
 save(dest/'formal-answer.json',{'answer':None,'status':reason});return {'run_status':reason}

def early_P_stop():
 slots=[s for s in protocol()['local_generation_slots'] if s['role']=='P'][:2]
 rr=[read(OUT/s['dest']/'run.json') for s in slots if (OUT/s['dest']/'run.json').exists()]
 return len(rr)==2 and rr[0]['run_status']==rr[1]['run_status'] and rr[0]['run_status'] in ('REPETITION_ABORT','OUTPUT_TRUNCATED')

def run_local(phase,runner=None):
 cfg=assert_frozen()
 from legal_bench.proof_carrying.local_runtime_v19_repair import Runner,SETTINGS
 if cfg['runtime_settings']!=SETTINGS:raise ValueError('FROZEN_RUNTIME_SETTINGS_MISMATCH')
 if phase in ('P','early') and early_P_stop():return 'STOPPED_BY_FROZEN_RULE'
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
     if version.exists() and read(version)['version']=='V19_2':
      directories.append({'part':task['part']['id'],'source_directory':[seg['id'] for seg in f['case']['segments'] if seg['id'] in task['part']['source_ids']]})
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
     from legal_bench.proof_carrying.local_checker_v19_repair import check
     ind=check(f['case'],f['rules'],p,decisions,audit);save(d/'independent-check.json',ind)
     if ind['status']!='OK':raise ValueError('INDEPENDENT_RECOMPUTATION_REJECTED')
     intermediate['program_checks']=pipe.compact_checks(audit)
     save(d/'prediction-transfer.json',[{'connection':x['connection_id'],'P':x['P_label'],'applied':x['applied_label'],'effect':x['disposition']} for x in audit['checks']])
   intermediate,receipt=pipe.display_material(intermediate);save(d/'display-receipt.json',receipt);prompt=pipe.final_prompt(f['case'],f['rules'],intermediate)
  if isP:save(d/'production-version.json',{'version':'V19_2','source_directory_sha256':hash_value([seg['id'] for seg in f['case']['segments'] if seg['id'] in s['part']['source_ids']])})
  result=runner.run(prompt,sc,d,s['max_tokens'],min(cfg['per_call_seconds_cap'],remaining),'FIXED')
  save(d/'formal-answer.json',{'answer':read(d/'parsed.json') if result['run_status']=='OK' else None,'status':result['run_status']})
  if isP:consolidate(cid)
  return result
 def after(s,r):
  if s['role']=='P' and early_P_stop():
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
 if path.exists():save(dest/'prediction-manifest.json',{'version':'V19_2','class_order':list(LABELS),'input_sha256':sha(OUT/'encoding/pairs.json'),'predictions_sha256':sha(path)})

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
 cfg=read(HISTORY/'freeze/protocol.json');tok=tokenizer();issues=[];slots=[];cases=[]
 for cid in cfg['TRAIN']+cfg['DEV']:
  source=HISTORY/'preparation/inputs'/cid/'fixture.json';text(PREP/'inputs'/cid/'fixture.json',source.read_text());f=read(source)
  for original in [s for s in cfg['local_generation_slots'] if s['role']=='P' and s['case_id']==cid]:
   part=original['part'];view={**f['case'],'segments':[x for x in f['case']['segments'] if x['id'] in part['source_ids']]};selected=[r for r in f['rules'] if r['id'] in part['rule_ids']]
   prompt=pipe.proposal_prompt(f['case'],f['rules'],part);sc=pipe.schema(selected,view);n=count(tok,render(tok,prompt));slot={**original,'rendered_input_tokens':n,'required_total_tokens':n+16384+256,'production_version':'V19_1' if (HISTORY/original['dest']/'run.json').exists() else 'V19_2'}
   if slot['required_total_tokens']>65536 and slot['production_version']=='V19_2':issues.append({'dest':slot['dest'],'required':slot['required_total_tokens'],'no_source_truncation':True})
   text(PREP/'inputs'/cid/(part['id']+'-prompt.txt'),prompt);save(PREP/'inputs'/cid/(part['id']+'-schema.json'),sc);slots.append(slot)
  prompt=pipe.final_prompt(f['case'],f['rules'],{});n=count(tok,render(tok,prompt));text(PREP/'inputs'/cid/'A-prompt.txt',prompt);cases.append({'case_id':cid,'A_input_tokens':n,'A_required_total_tokens':n+8192+256})
 order={s['dest']:i for i,s in enumerate(cfg['local_generation_slots'])};slots.sort(key=lambda s:order[s['dest']]);finals=[s for s in cfg['local_generation_slots'] if s['role']!='P']
 plan={'launch_permitted':not issues,'issues':issues,'cases':cases,'P_slots':slots,'final_slots':finals,'web_plan':cfg['web_slots'],'first_DEV':cfg['first_DEV'],'first_two_P_stop':cfg['early_P_stop'],'source_policy':cfg['context_policy'],'history_counts_against_budget':True}
 save(PREP/'capacity-plan.json',plan);return plan

def consolidate(cid,closed=False):
 from legal_bench.proof_carrying.source_contract_v19 import convert
 f=fixture(cid);slots=[s for s in protocol()['local_generation_slots'] if s['role']=='P' and s['case_id']==cid];parts=[];rawparts=[];states=[];maps=[]
 for slot in slots:
  d=OUT/slot['dest'];ss=state(d);states.append({'part':slot['part']['id'],'state':ss})
  raw=read(d/'parsed.json') if ss=='COMPLETED' else None;rawparts.append(raw)
  if raw is not None:
   view={**f['case'],'segments':[x for x in f['case']['segments'] if x['id'] in slot['part']['source_ids']]}
   production=read(d/'production-version.json')['version'] if (d/'production-version.json').exists() else 'V19_2'
   transformed,ledger=convert(raw,view,production=='V19_2');parts.append((slot['part']['id'],transformed));maps.append({'part':slot['part']['id'],'production':production,'ledger':ledger,'raw_unchanged_sha256':sha(d/'parsed.json')})
  else:parts.append((slot['part']['id'],None))
 any_valid=any(v is not None for _,v in parts);terminal=all(x['state'] in ('COMPLETED','ACTUAL_TECHNICAL_FAILURE','SKIPPED_DEPENDENCY') for x in states);p,ledger=pipe.merge_parts(parts) if any_valid else (None,[])
 result={'answer':p,'status':'COMPLETE' if all(x['state']=='COMPLETED' for x in states) else 'PARTIAL' if any_valid else 'NO_READABLE_PART','finalized':terminal or closed,'part_states':states,'part_ledger':ledger,'batch_closed':closed,'production_versions':sorted(set(x['production'] for x in maps))}
 checkpoint(OUT,cid+'-P',result)
 if result['finalized'] and not (OUT/'local'/cid/'P/merged.json').exists():save(OUT/'local'/cid/'P/merged.json',result)
 if p is not None and result['finalized']:
  save(OUT/'local'/cid/'P/address-ledger.json',maps);audit=pipe.apply_connection_decisions(f['case'],f['rules'],p)
  from legal_bench.proof_carrying.local_checker_v19_repair import check
  ind=check(f['case'],f['rules'],p,None,audit)
  if ind['status']!='OK':raise ValueError('INDEPENDENT_RECOMPUTATION_REJECTED')
  save(OUT/'local'/cid/'P/offline-audit.json',audit);save(OUT/'local'/cid/'P/independent-check.json',ind);save(OUT/'inputs'/cid/'learner-inputs.json',pipe.learner_inputs(f['case'],f['rules'],p));annotation_task(cid)
 return result

if __name__=='__main__':main()
