#!/usr/bin/env python3
"""V18 bounded phases. No references in inference; safe pause at saved-task boundaries."""
import argparse,datetime,hashlib,json,math,os,random,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from legal_bench.proof_carrying import local_pipeline_v18 as pipe
from legal_bench.proof_carrying.local_evaluation_v17 import LABELS,CLAIM_RULE,hash_value,blind_order,local_metrics
from legal_bench.proof_carrying.local_schedule_v18 import run as schedule
OUT=ROOT/'outputs/proof-local-comparison-v18';OLD=ROOT/'outputs/proof-local-comparison-v17';SEED=20261001
PREP=OUT/'preparation-02'

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
 return p

def tokenizer():
 from transformers import AutoTokenizer
 path=(ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip()
 return AutoTokenizer.from_pretrained(path,local_files_only=True)
def count(tok,s):return len(tok.encode(s,add_special_tokens=False))
def render(tok,s):return tok.apply_chat_template([{'role':'user','content':s}],tokenize=False,add_generation_prompt=True,enable_thinking=False)

def capacity():
 if (PREP/'capacity-plan.json').exists():return read(PREP/'capacity-plan.json')
 old=read(OLD/'freeze/protocol.json');tok=tokenizer();slots=[];cases=[];issues=[]
 # Output estimate: 1000 tokens for shared records/objects, 300 per premise (use+whole judgement), 15% margin.
 maxprem=math.floor((6144*.85-1000)/300)
 for split in ('TRAIN','DEV'):
  for cid in old[split]:
   f=read(OLD/'inputs'/cid/'fixture.json');case=f['case'];rules=f['rules'];groups=[];current=[];n=0
   if any(s['source_document']!=cid for s in case['segments']):raise ValueError('DOCUMENT_IDENTITY_CONFLICT')
   if sha(ROOT/case['source_path'])!=case['source_sha256']:raise ValueError('SOURCE_CHANGED')
   for rule in rules:
    k=len(rule['premises'])
    if k>maxprem:issues.append({'case_id':cid,'reason':'SINGLE_RULE_OUTPUT_ESTIMATE_TOO_LARGE','rule':rule['id'],'premises':k})
    if current and n+k>maxprem:groups.append(current);current=[];n=0
    current.append(rule['id']);n+=k
   if current:groups.append(current)
   ordered=sorted(case['segments'],key=lambda s:(s['source_document'],pipe.position(s),s['id']))
   derived=[];parts=[]
   for gi,ids in enumerate(groups):
    allpart={'id':'P%02d'%(gi+1),'rule_ids':ids,'source_ids':[s['id'] for s in ordered],
             'cross_part_policy':'NO_AUTOMATIC_OBJECT_IDENTITY_ACROSS_PARTS','source_scope':'FULL_ALLOWED_RANGE'}
    prompt=pipe.proposal_prompt(case,rules,allpart);nt=count(tok,render(tok,prompt))
    if nt+6144<=32768:parts.append(allpart)
    else:
     # Fixed source windows; entire rule group reused, all allowed original segments covered.
     windows=[];cur=[]
     for seg in ordered:
      trial=cur+[seg];part={**allpart,'source_ids':[s['id'] for s in trial],'source_scope':'CONTIGUOUS_SOURCE_WINDOW'}
      vv={**case,'segments':trial};nn=count(tok,render(tok,pipe.proposal_prompt(vv,rules,part)))
      if nn+6144+256>32768 and cur:windows.append(cur);cur=[];trial=[seg]
      vv={**case,'segments':trial};part['source_ids']=[s['id'] for s in trial]
      nn=count(tok,render(tok,pipe.proposal_prompt(vv,rules,part)))
      if nn+6144+256>32768:
       issues.append({'case_id':cid,'reason':'SINGLE_SOURCE_SEGMENT_EXCEEDS_CONTEXT','source_id':seg['id'],'tokens':nn});cur=[]
      else:cur=trial
     if cur:windows.append(cur)
     for wi,window in enumerate(windows):parts.append({**allpart,'id':'P%02dW%02d'%(gi+1,wi+1),'source_ids':[s['id'] for s in window],
        'source_scope':'CONTIGUOUS_SOURCE_WINDOW','cross_window_limit':'IDENTITY_AND_COURT_CONTEXT_NOT_AUTOMATICALLY_ESTABLISHED'})
   for part in parts:
    prompt=pipe.proposal_prompt(case,rules,part);nt=count(tok,render(tok,prompt));nr=sum(len(r['premises']) for r in rules if r['id'] in part['rule_ids'])
    estimate=1000+nr*300
    if nt+6144>32768:issues.append({'case_id':cid,'reason':'INPUT_LIMIT','part':part['id'],'tokens':nt})
    slot={'case_id':cid,'split':split,'role':'P','part':part,'max_tokens':6144,'rendered_input_tokens':nt,'output_estimate_tokens':estimate,
          'dest':'local/'+cid+'/'+part['id']}
    slots.append(slot);text(PREP/'inputs'/cid/(part['id']+'-prompt.txt'),prompt);save(PREP/'inputs'/cid/(part['id']+'-schema.json'),pipe.schema([r for r in rules if r['id'] in part['rule_ids']]))
   save(PREP/'inputs'/cid/'fixture.json',f)
   final=pipe.final_prompt(case,rules,{})
   text(PREP/'inputs'/cid/'A-prompt.txt',final)
   cases.append({'case_id':cid,'split':split,'source_tokens':count(tok,pipe.source_text(case)),'source_segments':len(case['segments']),
                 'rule_count':len(rules),'premise_count':sum(len(r['premises']) for r in rules),'P_parts':len(parts),'A_input_tokens':count(tok,render(tok,final)),
                 'role_addresses':len(pipe.role_directory(rules)),'Q1_rule_mapping':'ALL_EXISTING_RULES_RETAINED; NO_REFERENCE_GUIDED_SCOPE_PRUNING'})
   # The union is checked independently for every rule group, not just global source coverage.
   for group in groups:
    selected={ref for part in parts if part['rule_ids']==group for ref in part['source_ids']}
    if selected!={s['id'] for s in ordered}:issues.append({'case_id':cid,'reason':'SOURCE_WINDOW_UNION_INCOMPLETE','rules':group})
 # Balanced interleaving: A for all cases, B later; each C-G offset rotates across cases.
 finals=[{'case_id':cid,'role':tag,'max_tokens':3072,'dest':'local/'+cid+'/'+tag} for tag in ('A','B') for cid in old['DEV']]
 for roundno in range(5):
  for i,cid in enumerate(old['DEV']):
   tag='CDEFG'[(roundno+i)%5];finals.append({'case_id':cid,'role':tag,'max_tokens':3072,'dest':'local/'+cid+'/'+tag})
 if len(slots)>80:issues.append({'reason':'P_CALL_CAPACITY_EXCEEDED','needed':len(slots),'cap':80})
 speeds=[read(p) for p in (OLD/'local').glob('*/*/run.json')];pp=[x for x in speeds if x.get('output_tokens') and x.get('elapsed_seconds')]
 tps=sum(x['output_tokens'] for x in pp)/sum(x['elapsed_seconds'] for x in pp)
 lower=sum(s['output_estimate_tokens']/tps for s in slots)+70*180;upper=len(slots)*1200+70*1200
 plan={'at':utc(),'cases':cases,'P_slots':slots,'final_slots':finals,'static_issues':issues,'launch_permitted':not issues,
       'output_estimate':{'fixed_overhead':1000,'per_premise':300,'margin':.15,'derived_max_premises_per_rule_group':maxprem,
         'not_guarantee':True,'one_premise_can_have_multiple_uses':True,'no_connection_count_quota':True},
       'source_windows':'WHOLE_ORIGINAL_SEGMENTS; ALL_ORIGINAL_IDS_PER_GROUP; NO_REFERENCE_FILTERING; NO_SILENT_TRUNCATION',
       'web_plan':{'connection_annotations':40,'reference_gap_patches_max':10,'blind_evaluation_max':20,'total_cap':70,
          'label_output_estimate':'300_tokens_per_declared_use + 500; checked against realized P before submission',
          'blind_evaluation_plan':'TWO_TASKS_PER_DEV; seed20261001_neutral_order_split_4_and_3_answers; same_full_reference_and_source'},
       'generation_seconds_cap':72000,'P_seconds_allocation':50400,'final_seconds_reserved':21600,'per_call_seconds_cap':1200,
       'historical_effective_output_tokens_per_second':tps,'estimated_generation_seconds':lower,'worst_case_unfunded_seconds':upper,
       'estimate_limit':'Estimate includes V17 actual input/prefill overhead indirectly; 6144 output budget and different interface may change speed. Worst-case max durations exceed total cap, stop at stage caps rather than overspend.'}
 save(PREP/'capacity-plan.json',plan);return plan

def freeze():
 plan=capacity()
 if not plan['launch_permitted']:raise ValueError('STATIC_CAPACITY_BLOCKED; no generation started')
 old=read(OLD/'freeze/protocol.json');files=['legal_bench/proof_carrying/local_pipeline_v18.py','legal_bench/proof_carrying/local_runtime_v18.py','legal_bench/proof_carrying/local_checker_v18.py','legal_bench/proof_carrying/local_schedule_v18.py','scripts/proof_local_comparison_v18.py','legal_bench/proof_carrying/local_fit_v17.py','legal_bench/proof_carrying/semantic_models_v12.py','legal_bench/proof_carrying/semantic_model_inputs_v13.py','legal_bench/proof_carrying/semantic_interface_v13.py','legal_bench/proof_carrying/quote_locator_v16.py','legal_bench/mlx_json_constraint_v2.py','scripts/proof_semantic_encode_v13.py']
 hashes={f:sha(ROOT/f) for f in files}
 for f in files:text(OUT/'freeze/code'/f,(ROOT/f).read_text())
 cfg={**old,'version':'V18','frozen_at':utc(),'code_hashes':hashes,'local_generation_slots':plan['P_slots']+plan['final_slots'],
      'local_slot_cap':150,'total_local_generation_seconds_cap':72000,'P_seconds_cap':50400,'final_seconds_cap':21600,
      'web_slot_cap':70,'web_mode':'GPT-6, Extra High (visible UI; user confirmed Ex High means Extra High)',
      'label_contract':{'unit':'ONE_DECLARED_USE_EXACT_SOURCE_OBJECT_STAGE_DIRECTION_SCOPE','classes':LABELS,
        'SUPPORTED_not_whole_TRUE':True,'valid_opposition_supported':True,'out_of_packet_labels_not_supervised':True,'wrong_quote_not_rescued':True},
      'context_policy':plan['source_windows'],'restore_policy':'ALL_RECORD_USE_WITNESS_OPPOSITION_OBJECT_REFS_PLUS_FIXED_ADJACENT_CONTEXT; NEIGHBOUR_CONTEXT_ONLY',
      'same_information':'ALL_NODE_AND_EDGE_CONTENT_VISIBLE_TO_ALL_THREE_METHODS; CE_DIFFERENT_ENCODER_NOT_PURE_GRAPH_ABLATION',
      'training_gate':'MULTIPLE_TRAIN_DISPUTES_WITH_POSITIVE_AND_NEGATIVE_VALID_LABELS; NO_LEAKAGE; COMMON_INPUT_VALID',
      'stage_reservations':{'P':50400,'final':21600},'retries':0}
 cfg['local_model']={**old['local_model'],'P_max_tokens':6144};cfg['web_slots']=plan['web_plan']
 save(OUT/'freeze/protocol.json',cfg);save(OUT/'freeze/evaluation-contract.json',old['evaluation']);save(OUT/'freeze/final-schema.json',pipe.FINAL_SCHEMA)
 # Reuse the full frozen reference; preserve old High provenance and all amendments.
 ref=[]
 for cid in old['DEV']:
  path=OLD/'private/frozen-references'/cid/'checklist.json';v=read(path)
  save(OUT/'private/frozen-references'/cid/'checklist.json',{**v,'V18_reuse_provenance':{'path':str(path.relative_to(ROOT)),'sha256':sha(path),'original_web_setting':'High; NOT_EXTRA_HIGH','content_unchanged':True}})
  ref.append({'case_id':cid,'path':str(path.relative_to(ROOT)),'source_sha256':sha(path),'key_items':len(v['key_items']),'original_setting':'High'})
 save(OUT/'freeze/reference-checklists-manifest.json',ref)
 return cfg

def consolidate(cid):
 f=fixture(cid);slots=[s for s in protocol()['local_generation_slots'] if s['role']=='P' and s['case_id']==cid];parts=[]
 for s in slots:
  d=OUT/s['dest']
  if not (d/'run.json').exists():return
  parts.append((s['part']['id'],read(d/'parsed.json') if read(d/'run.json')['run_status']=='OK' else None))
 if not any(v is not None for _,v in parts):save(OUT/'local'/cid/'P/merged.json',{'answer':None,'status':'ALL_PARTS_TECHNICAL_FAILURE'});return
 p,ledger=pipe.merge_parts(parts);save(OUT/'local'/cid/'P/merged.json',{'answer':p,'status':'COMPLETE' if all(v is not None for _,v in parts) else 'PARTIAL','part_ledger':ledger})
 audit=pipe.apply_connection_decisions(f['case'],f['rules'],p);save(OUT/'local'/cid/'P/offline-audit.json',audit)
 from legal_bench.proof_carrying.local_checker_v18 import check
 save(OUT/'local'/cid/'P/independent-check.json',check(f['rules'],audit))
 save(OUT/'inputs'/cid/'learner-inputs.json',pipe.learner_inputs(f['case'],f['rules'],p));annotation_task(cid)

def run_local(phase):
 cfg=assert_frozen()
 from legal_bench.proof_carrying.local_runtime_v18 import Runner,SETTINGS
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
   prompt=pipe.final_prompt(f['case'],f['rules'],intermediate)
  result=runner.run(prompt,sc,d,s['max_tokens'],min(1200,remaining),'FIXED')
  save(d/'formal-answer.json',{'answer':read(d/'parsed.json') if result['run_status']=='OK' else None,'status':result['run_status']})
  if phase=='P':consolidate(cid)
  return result
 return schedule(OUT,slots,perform)

ANNOTATION='''Assess the proposed evidentiary use exactly as stated. Keep source support, evidentiary direction, whole-premise truth and legal consequence separate. A correctly grounded opposition may be SUPPORTED. Use UNSUPPORTED for a demonstrable mismatch or unsupported upgrade, and UNRESOLVED when the supplied common packet cannot settle the use. Do not rescue a mis-cited use with a different passage. If a judgement requires information outside the learner-visible packet, mark the input-coverage limitation and identify that dependency. Do not rewrite the proposal or infer a label from the model's confidence. Read the complete allowed source for decisive limitations, but keep local packet support separate from full-source review. The learner-visible common input includes each use packet and the same-case union of all listed packets, raw records and rules. Dependencies elsewhere in that union are learner-visible, not outside-input. P self-ratings, whole-premise judgements and confidence are hidden from the annotation task only, while the learner retains them as fallible proposal information. Return complete English JSON in the response body, not only a file link. No external search or other conversations. One response only. Output {"connections":[{"connection_id":"K001","label":"SUPPORTED","basis":"source explanation","refs":["id"],"quote":"short exact source words","dispute":false,"input_coverage_limited":false,"outside_packet_dependencies":[]}],"limitations":[]}; exactly one row per declared use. Model-assisted source reference, not human gold.'''

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
  if label.get('input_coverage_limited') or label.get('outside_packet_dependencies') or not set(label.get('refs',[]))<=visible:
   excluded.append({**base,'reason':'INPUT_COVERAGE_LIMITED','raw':label});continue
  if location.get('error') or label.get('label') not in LABELS or not label.get('basis') or label.get('dispute'):
   excluded.append({**base,'reason':'SOURCE_OR_SEMANTIC_CONTRACT_UNCONFIRMED','raw':label,'location':location});continue
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
 return good

def fit(kind):
 cfg=assert_frozen();gate=read(OUT/'training-gate.json')
 if not gate['start_permitted']:raise ValueError('TRAINING_GATE_NOT_MET')
 from legal_bench.proof_carrying.local_fit_v17 import fit_graph,fit_ce
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
