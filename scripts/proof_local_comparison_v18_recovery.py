#!/usr/bin/env python3
"""V18 bounded phases. No references in inference; safe pause at saved-task boundaries."""
import argparse,datetime,hashlib,json,math,os,random,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from legal_bench.proof_carrying import local_pipeline_v18_recovery as pipe
from legal_bench.proof_carrying.local_evaluation_v17 import LABELS,CLAIM_RULE,hash_value,blind_order,local_metrics
from legal_bench.proof_carrying.local_schedule_v18 import run as schedule
BASE=ROOT/'outputs/proof-local-comparison-v18';OUT=BASE/'continuation-02';OLD=ROOT/'outputs/proof-local-comparison-v17';SEED=20261001
PREP=OUT/'preparation'; OLD_PREP=BASE/'preparation-02'

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
 for cid in [x['case_id'] for x in original['cases']]:
  source=OLD_PREP/'inputs'/cid/'fixture.json';f=read(source)
  if sha(ROOT/f['case']['source_path'])!=f['case']['source_sha256']:raise ValueError('SOURCE_CHANGED')
  text(PREP/'inputs'/cid/'fixture.json',source.read_text())
 for oldslot in original['P_slots']:
  slot={**oldslot,'max_tokens':16384};cid=slot['case_id'];f=fixture(cid)
  prompt=pipe.proposal_prompt(f['case'],f['rules'],slot['part']);sc=pipe.schema([r for r in f['rules'] if r['id'] in slot['part']['rule_ids']])
  nt=count(tok,render(tok,prompt));slot.update(rendered_input_tokens=nt,reserved_output_tokens=16384,template_margin_tokens=256,required_total_tokens=nt+16384+256)
  if slot['required_total_tokens']>65536:issues.append({'case_id':cid,'part':slot['part']['id'],'status':'INPUT_TOO_LONG','required':slot['required_total_tokens']})
  text(PREP/'inputs'/cid/(slot['part']['id']+'-prompt.txt'),prompt);save(PREP/'inputs'/cid/(slot['part']['id']+'-schema.json'),sc);slots.append(slot)
 for row in original['cases']:
  cid=row['case_id'];f=fixture(cid);prompt=pipe.final_prompt(f['case'],f['rules'],{});nt=count(tok,render(tok,prompt))
  text(PREP/'inputs'/cid/'A-prompt.txt',prompt)
  cases.append({**row,'A_input_tokens':nt,'A_reserved_output_tokens':8192,'A_required_total_tokens':nt+8192+256})
 finals=[{**x,'max_tokens':8192} for x in original['final_slots']]
 plan={**original,'at':utc(),'cases':cases,'P_slots':slots,'final_slots':finals,'static_issues':issues,'launch_permitted':True,
       'authorization':read(OUT/'authorization.json'),'original_task_list_sha256':sha(OLD_PREP/'capacity-plan.json'),
       'task_boundaries_unchanged':True,'generation_seconds_cap':129600,'P_seconds_allocation':86400,'final_seconds_reserved':43200,'per_call_seconds_cap':3600,
       'total_context_tokens':65536,'template_margin_tokens':256,
       'estimate_limit':'Old 6144 output estimate is historical only, not a completion guarantee; runtime enforces stage budgets.',
       'dynamic_C_G_capacity':'Lossless fixed display policy; count full realized input +8192+256; overflow is technical null, no pruning',
       'old_P_reuse':'NONE: uniform prompt changes; old full and truncated P retained but not used as this version inputs'}
 save(PREP/'capacity-plan.json',plan);return plan

def freeze():
 plan=capacity()
 if not plan['launch_permitted']:raise ValueError('STATIC_CAPACITY_BLOCKED; no generation started')
 old=read(OLD/'freeze/protocol.json');files=['legal_bench/proof_carrying/local_pipeline_v18.py','legal_bench/proof_carrying/local_runtime_v18.py','legal_bench/proof_carrying/local_checker_v18.py','legal_bench/proof_carrying/local_schedule_v18.py','scripts/proof_local_comparison_v18.py','legal_bench/proof_carrying/local_fit_v17.py','legal_bench/proof_carrying/semantic_models_v12.py','legal_bench/proof_carrying/semantic_model_inputs_v13.py','legal_bench/proof_carrying/semantic_interface_v13.py','legal_bench/proof_carrying/quote_locator_v16.py','legal_bench/mlx_json_constraint_v2.py','scripts/proof_semantic_encode_v13.py','legal_bench/proof_carrying/local_pipeline_v17.py','legal_bench/proof_carrying/local_evaluation_v17.py','legal_bench/proof_carrying/local_reporting_v18.py','legal_bench/proof_carrying/local_fit_v18.py','scripts/proof_local_integrate_v18.py','legal_bench/irac_application/text_cache.py','legal_bench/mlx_json_constraint.py','legal_bench/rules_verdict_v1/source_views.py','legal_bench/rules_verdict_v1/repetition_v9.py','outputs/gnn-irac-aligned-v2/text-cache/encoder.json']
 files += ['scripts/proof_local_comparison_v18_recovery.py','scripts/proof_local_integrate_v18_recovery.py','scripts/proof_local_recovery_accept_v18.py','legal_bench/proof_carrying/local_pipeline_v18_recovery.py','legal_bench/proof_carrying/local_runtime_v18_recovery.py','legal_bench/proof_carrying/local_annotation_v18_recovery.py']
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
 files=sorted(allfiles);hashes={f:sha(ROOT/f) for f in files}
 for f in files:text(OUT/'freeze/code'/f,(ROOT/f).read_text())
 cfg={**old,'version':'V18_RECOVERY_02','frozen_at':utc(),'code_hashes':hashes,'local_generation_slots':plan['P_slots']+plan['final_slots'],
      'P_slot_cap':87,'final_slot_cap':70,'local_slot_cap':157,'total_local_generation_seconds_cap':129600,'P_seconds_cap':86400,'final_seconds_cap':43200,'per_call_seconds_cap':3600,
      'web_slot_cap':70,'web_mode':'GPT-6, Extra High (visible UI; user confirmed Ex High means Extra High)',
      'label_contract':{'unit':'ONE_DECLARED_USE_EXACT_SOURCE_OBJECT_STAGE_DIRECTION_SCOPE','classes':LABELS,
        'SUPPORTED_not_whole_TRUE':True,'valid_opposition_supported':True,'out_of_packet_labels_not_supervised':True,'wrong_quote_not_rescued':True},
      'context_policy':plan['source_windows'],'restore_policy':'ALL_RECORD_USE_WITNESS_OPPOSITION_OBJECT_REFS_PLUS_FIXED_ADJACENT_CONTEXT; NEIGHBOUR_CONTEXT_ONLY',
      'same_information':'ALL_NODE_AND_EDGE_CONTENT_VISIBLE_TO_ALL_THREE_METHODS; CE_DIFFERENT_ENCODER_NOT_PURE_GRAPH_ABLATION',
      'training_gate':'MULTIPLE_TRAIN_DISPUTES_WITH_POSITIVE_AND_NEGATIVE_VALID_LABELS; NO_LEAKAGE; COMMON_INPUT_VALID',
      'stage_reservations':{'P':86400,'final':43200},'retries':0}
 from legal_bench.proof_carrying.local_runtime_v18_recovery import SETTINGS
 cfg['runtime_settings']=dict(SETTINGS);cfg['local_model']={**old['local_model'],'P_max_tokens':16384,'final_max_tokens':8192,'context_tokens':65536,'timeout_seconds':3600};cfg['web_slots']=plan['web_plan']
 cfg['label_contract']=read(OUT/'freeze/annotation-contract.json');cfg['resource_support']=read(OUT/'engineering/resource-support.json')
 cfg['display_policy']=pipe.DISPLAY_POLICY;cfg['cross_rule_contract_inventory']=read(OUT/'engineering/rule-contract-inventory.json');cfg['engineering_gate']=read(OUT/'engineering/integration-acceptance.json')
 if cfg['engineering_gate']['status']!='PASS':raise ValueError('ACTUAL_ENTRY_GATE_FAILED')
 cfg['prepared_input_hashes']={str(p.relative_to(ROOT)):sha(p) for p in (PREP/'inputs').rglob('*') if p.is_file()}
 save(OUT/'freeze/protocol.json',cfg);save(OUT/'freeze/evaluation-contract.json',old['evaluation']);save(OUT/'freeze/final-schema.json',pipe.FINAL_SCHEMA)
 # Reuse the full frozen reference; preserve old High provenance and all amendments.
 ref=[]
 for cid in old['DEV']:
  path=OLD/'private/frozen-references'/cid/'checklist.json';v=read(path)
  save(OUT/'private/frozen-references'/cid/'checklist.json',{**v,'V18_reuse_provenance':{'path':str(path.relative_to(ROOT)),'sha256':sha(path),'original_web_setting':'High; NOT_EXTRA_HIGH','content_unchanged':True}})
  ref.append({'case_id':cid,'path':str(path.relative_to(ROOT)),'source_sha256':sha(path),'key_items':len(v['key_items']),'original_setting':'High'})
 save(OUT/'freeze/reference-checklists-manifest.json',ref)
 return cfg

def consolidate(cid,closed=False):
 f=fixture(cid);slots=[s for s in protocol()['local_generation_slots'] if s['role']=='P' and s['case_id']==cid];parts=[]
 for s in slots:
  d=OUT/s['dest']
  if not (d/'run.json').exists():
   if not closed:return
   parts.append((s['part']['id'],None));continue
  parts.append((s['part']['id'],read(d/'parsed.json') if read(d/'run.json')['run_status']=='OK' else None))
 if not any(v is not None for _,v in parts):save(OUT/'local'/cid/'P/merged.json',{'answer':None,'status':'ALL_PARTS_TECHNICAL_FAILURE'});return
 p,ledger=pipe.merge_parts(parts);save(OUT/'local'/cid/'P/merged.json',{'answer':p,'status':'COMPLETE' if all(v is not None for _,v in parts) else 'PARTIAL','part_ledger':ledger})
 audit=pipe.apply_connection_decisions(f['case'],f['rules'],p);save(OUT/'local'/cid/'P/offline-audit.json',audit)
 from legal_bench.proof_carrying.local_checker_v18 import check
 save(OUT/'local'/cid/'P/independent-check.json',check(f['rules'],audit))
 save(OUT/'inputs'/cid/'learner-inputs.json',pipe.learner_inputs(f['case'],f['rules'],p));annotation_task(cid)

def run_local(phase):
 cfg=assert_frozen()
 from legal_bench.proof_carrying.local_runtime_v18_recovery import Runner,SETTINGS
 if cfg['runtime_settings']!=SETTINGS:raise ValueError('FROZEN_RUNTIME_SETTINGS_MISMATCH')
 runner=Runner((ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),SETTINGS)
 slots=[s for s in cfg['local_generation_slots'] if (s['role']=='P')==(phase=='P')]
 def perform(s,d):
  cid=s['case_id'];f=fixture(cid);role=s['role'];used=sum(read(p).get('elapsed_seconds',0) or 0 for p in (OUT/'local').glob('*/*/run.json') if (p.parent.name.startswith('P'))==(phase=='P'))
  remaining=cfg['P_seconds_cap' if phase=='P' else 'final_seconds_cap']-used
  if remaining<=0:save(d/'run.json',{'run_status':'STAGE_BUDGET_EXHAUSTED','answer':None});save(d/'formal-answer.json',{'answer':None,'status':'STAGE_BUDGET_EXHAUSTED'});return {'run_status':'STAGE_BUDGET_EXHAUSTED'}
  if role=='P':prompt=(PREP/'inputs'/cid/(s['part']['id']+'-prompt.txt')).read_text();sc=read(PREP/'inputs'/cid/(s['part']['id']+'-schema.json'))
  else:
   intermediate={};sc=pipe.FINAL_SCHEMA
   if role=='B':
    a=OUT/'local'/cid/'A/formal-answer.json'
    if not a.exists() or read(a)['answer'] is None:save(d/'run.json',{'run_status':'SKIPPED_A_DEPENDENCY','answer':None});save(d/'formal-answer.json',{'answer':None,'status':'SKIPPED_A_DEPENDENCY'});return {'run_status':'SKIPPED_A_DEPENDENCY'}
    intermediate={'previous_direct_answer_model_proposed':read(a)['answer']}
   elif role!='A':
    path=OUT/'local'/cid/'P/merged.json';m=read(path) if path.exists() else {'answer':None}
    if m['answer'] is None:save(d/'run.json',{'run_status':'SKIPPED_P_DEPENDENCY','answer':None});save(d/'formal-answer.json',{'answer':None,'status':'SKIPPED_P_DEPENDENCY'});return {'run_status':'SKIPPED_P_DEPENDENCY'}
    p=m['answer'];intermediate={'proposal':p,'proposal_coverage':m['status']}
    if role!='C':
     decisions=None
     if role in 'EFG':
      model={'E':'Flat','F':'CrossEncoder','G':'RGCN'}[role];pr=OUT/'training'/model/'all-candidate-predictions.json'
      if not pr.exists():save(d/'run.json',{'run_status':'SKIPPED_MODEL_FAILURE','answer':None});save(d/'formal-answer.json',{'answer':None,'status':'SKIPPED_MODEL_FAILURE'});return {'run_status':'SKIPPED_MODEL_FAILURE'}
      decisions={x['key'].split('::')[-1]:LABELS[max(range(3),key=lambda j:x['probabilities'][j])] for x in read(pr) if x['key'].startswith(cid+'::')}
     audit=pipe.apply_connection_decisions(f['case'],f['rules'],p,decisions);save(d/'offline-audit.json',audit)
     from legal_bench.proof_carrying.local_checker_v18 import check
     save(d/'independent-check.json',check(f['rules'],audit));intermediate['program_checks']=pipe.compact_checks(audit)
     save(d/'prediction-transfer.json',[{'connection':x['connection_id'],'P':x['P_label'],'applied':x['applied_label'],'effect':x['disposition']} for x in audit['checks']])
   intermediate,display_receipt=pipe.display_material(intermediate);save(d/'display-receipt.json',display_receipt)
   prompt=pipe.final_prompt(f['case'],f['rules'],intermediate)
  result=runner.run(prompt,sc,d,s['max_tokens'],min(cfg['per_call_seconds_cap'],remaining),'FIXED')
  save(d/'formal-answer.json',{'answer':read(d/'parsed.json') if result['run_status']=='OK' else None,'status':result['run_status']})
  if phase=='P':consolidate(cid)
  return result
 result=schedule(OUT,slots,perform)
 if phase=='P':
  for cid in cfg['TRAIN']+cfg['DEV']:consolidate(cid,closed=True)
 save(OUT/('phase-'+phase+'-status.json'),{'status':result,'at':utc()});return result

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
  matches=[r for r in read(path)['connections'] if r['connection_id']==base['use_id']]
  if len(matches)!=1:excluded.append({**base,'reason':'LABEL_ADDRESS_MISSING_OR_DUPLICATE'});continue
  label=matches[0];f=fixture(cid);location=pipe.source_match(label,pipe.sources(f['case']));data=read(OUT/'inputs'/cid/'learner-inputs.json');pkg=data['materials'][base['use_id']]
  visible={s['id'] for packet in data['materials'].values() for s in packet['actual_restored_source']['segments']}
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
 from legal_bench.proof_carrying.local_fit_v18 import fit_graph,fit_ce
 data=read(OUT/'freeze/training-rows.json');inf=[r for r in read(OUT/'encoding/inference-rows.json') if r['split']=='DEV'];dest=OUT/'training'/kind
 if dest.exists():raise ValueError('NO_FIT_RESTART')
 deadline=time.monotonic()+cfg['models'][kind]['max_seconds']
 if kind=='CrossEncoder':return fit_ce(SEED,read(OUT/'encoding/pairs.json'),data,dest,deadline,inference_rows=inf)
 import numpy as np,mlx.core as mx
 from legal_bench.proof_carrying.semantic_model_inputs_v13 import graph_arrays
 vectors=np.load(OUT/'encoding/vectors.npz');graphs=read(OUT/'encoding/graphs.json');plans=read(OUT/'encoding/plans.json')
 allgraphs={fixture(cid)['case']['dispute_id']:graph_arrays(g,plans[cid],vectors) for cid,g in graphs.items()}
 for g in allgraphs.values():
  for k in ('x','adj','edges'):g[k]=mx.array(g[k])
 return fit_graph(kind,SEED,allgraphs,data,dest,deadline,inference_rows=inf)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['capacity','freeze','P','final','encoding','rows','fit']);parser.add_argument('--kind',choices=['Flat','RGCN','CrossEncoder']);args=parser.parse_args();os.chdir(ROOT)
 if args.phase=='capacity':print(json.dumps({k:v for k,v in capacity().items() if k not in ('cases','P_slots','final_slots')},indent=2))
 elif args.phase=='freeze':freeze()
 elif args.phase in ('P','final'):run_local(args.phase)
 elif args.phase=='encoding':encoding()
 elif args.phase=='rows':rows()
 elif args.phase=='fit':fit(args.kind)
if __name__=='__main__':main()
