#!/usr/bin/env python3
"""V19 actual integration acceptance, encoding audit, baseline and blinded evaluation.
No generator call or training in acceptance. Tested raw source is really encoded.
"""
import argparse,copy,json,os,subprocess,sys,collections,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.proof_local_comparison_v19 import OUT,BASE,PREP,OLD,read,save,text,sha,fixture,protocol,assert_frozen
from legal_bench.proof_carrying import local_pipeline_v19 as pipe
from legal_bench.proof_carrying import local_reporting_v18 as report

def acceptance():
 from tests.test_local_pipeline_v19 import fixture
 from legal_bench.proof_carrying.local_runtime_v19 import Runner,SETTINGS
 from legal_bench.mlx_json_constraint import tokenizer_data
 from legal_bench.mlx_json_constraint_v2 import SchemaMask
 from scripts import proof_local_comparison_v19 as entry
 from unittest.mock import patch
 import tempfile,types,importlib,collections
 from legal_bench.proof_carrying.local_annotation_v18_recovery import CONTRACT
 c,r,raw=fixture();tok=entry.tokenizer();ids=tok.encode(pipe.compact_json(raw),add_special_tokens=False)
 data=tokenizer_data(tok,getattr(tok,'eos_token_ids',tok.eos_token_id));mask=SchemaMask(data,pipe.schema(r));prefix=[]
 for token in ids:
  allowed=mask.enforcer.get_allowed_tokens(prefix).allowed_tokens
  if token not in allowed:raise ValueError('ACTUAL_TOKENIZER_SCHEMA_REPLAY_FAILED:'+str(len(prefix)))
  prefix.append(token)
 end=mask.enforcer.get_allowed_tokens(prefix).allowed_tokens
 eos=getattr(tok,'eos_token_ids',tok.eos_token_id);eos=[eos] if isinstance(eos,int) else eos
 if not any(i in end for i in eos):raise ValueError('JSON_CANNOT_END')
 save(OUT/'engineering/real-tokenizer.json',{'status':'PASS','tokens':len(ids),'eos_allowed':True,'schema_sha256':pipe.hash_value(pipe.schema(r)),'model_generation':False})
 runner=Runner.__new__(Runner);runner.settings=dict(SETTINGS);runner.tokenizer=tok;runner.constraint_data=data
 runner.loaded_seconds=0;runner.versions={'engineering_mock_stream':True};runner.model_config_hash='fixture_not_model_run';runner.model=types.SimpleNamespace();runner.processor=tok;runner.render=lambda s:entry.render(tok,s)
 def stream(*args,**kwargs):
  assert kwargs['max_tokens']==16384 and kwargs['enable_thinking'] is False
  yield types.SimpleNamespace(text=pipe.compact_json(raw),token_ids=ids,token=None,generation_tokens=len(ids),prompt_tokens=24,finish_reason='stop')
 module=importlib.import_module('mlx_vlm.generate')
 # Invoke the real scheduling/generation/consolidation entry in an isolated engineering root.
 with tempfile.TemporaryDirectory() as temp:
  root=Path(temp);prep=root/'preparation';cfg={'code_hashes':{},'prepared_input_hashes':{},'runtime_settings':SETTINGS,'first_DEV':'SYN','TRAIN':[],'DEV':['SYN'],'P_seconds_cap':86400,'final_seconds_cap':43200,'per_call_seconds_cap':3600,
  'local_generation_slots':[{'role':'P','case_id':'SYN','dest':'local/SYN/P01','part':{'id':'P01','rule_ids':['R1'],'source_ids':[s['id'] for s in c['segments']]},'max_tokens':16384},{'role':'P','case_id':'SYN','dest':'local/SYN/P02','part':{'id':'P02','rule_ids':['R1'],'source_ids':[s['id'] for s in c['segments']]},'max_tokens':16384}]}
  for slot in cfg['local_generation_slots']:
   text(prep/'inputs/SYN'/(slot['part']['id']+'-prompt.txt'),'Engineering fixture only.');save(prep/'inputs/SYN'/(slot['part']['id']+'-schema.json'),pipe.schema(r))
  real_run=runner.run;counter=[]
  def one(*args,**kwargs):
   result=real_run(*args,**kwargs);counter.append(1)
   if len(counter)==1:(root/'PAUSE_REQUESTED.json').write_text('{}')
   return result
  runner.run=one
  with patch.object(entry,'OUT',root),patch.object(entry,'PREP',prep),patch.object(entry,'protocol',lambda:cfg),patch.object(entry,'fixture',lambda cid:{'case':c,'rules':r}),patch.object(entry,'annotation_task',lambda cid:None),patch.object(module,'stream_generate',stream):
   assert entry.run_local('P',runner)=='PAUSED'
   assert not (root/'local/SYN/P02/run.json').exists();assert not (root/'local/SYN/P/merged.json').exists()
   (root/'PAUSE_REQUESTED.json').unlink();assert entry.run_local('P',runner)=='FINISHED'
   assert entry.read(root/'local/SYN/P/merged.json')['answer'] is not None
   checkpoints=list((root/'checkpoints/SYN-P').glob('v*.json'));assert len(checkpoints)==2
   receipt={'status':'PASS','first_pause':'AFTER_SAVED_SINGLE','second_task_after_resume':True,'versioned_merge_count':len(checkpoints),'real_entry':'run_local -> Runner.run -> schedule -> consolidate -> source/binding/dependency independent check','stream':'MOCKED; zero model calls', 'actual_settings':SETTINGS}
   save(OUT/'engineering/actual-entry.json',receipt)
 # Actual existing E5 encoder and CE tokenizer verify newly shared block representation.
 p,_=pipe.merge_parts([('P01',raw)]);visible=pipe.learner_inputs(c,r,p);out=OUT/'engineering/actual-encoding';texts={};plan=[]
 for node in visible['graph']['nodes']:
  h=pipe.hash_value(node['text']);texts[h]=node['text'];plan.append({'node':node['id'],'part_sha256':[h]})
 save(out/'texts.json',texts);save(out/'input.json',visible);save(out/'graph-plan.json',{'graph':plan})
 if not (out/'encoding.json').exists():
  result=subprocess.run([str(ROOT/'.runtime/irac-e5-v1/bin/python'),str(ROOT/'scripts/proof_semantic_encode_v13.py'),str(out)],cwd=ROOT,capture_output=True,text=True);text(out/'encoder-log.txt',result.stdout+result.stderr)
  if result.returncode:raise ValueError('ACTUAL_E5_ENCODER_FAILED')
 result=subprocess.run([str(ROOT/'.runtime/proof-semantic-v12/bin/python'),str(__file__),'encoding-audit','--input',str(out)],cwd=ROOT,capture_output=True,text=True);text(out/'input-audit-log.txt',result.stdout+result.stderr)
 if result.returncode:raise ValueError('ACTUAL_INPUT_ENCODING_AUDIT_FAILED:'+result.stderr)
 save(OUT/'freeze/annotation-contract.json',CONTRACT)
 inv=collections.Counter();count=0;dependencies=[]
 for path in (PREP/'inputs').glob('*/fixture.json'):
  f=read(path)
  for rule in f['rules']:
   count+=1;inv[rule['operator']]+=1
   for key in ('dependencies','rule_dependencies','derived_from','depends_on'):
    if rule.get(key):dependencies.append({'rule':rule['id'],'contract':rule[key]})
 save(OUT/'engineering/rule-contract-inventory.json',{'rules':count,'operators':dict(inv),'explicit_dependencies':dependencies,'scope':'Only existing explicit per-rule compositions; OPEN_TEXT and missing cross-rule dependencies not invented.'})
 save(OUT/'engineering/integration-acceptance.json',{'status':'PASS','tests':'tests.test_local_pipeline_v19','actual_entry':receipt,'real_tokenizer_replay':True,'actual_E5_and_CE_inputs':True,'new_LLM_calls':0,'new_training':0,'legal_semantics_proved':False})
 print('V19_ACTUAL_ENTRY_PASS')

def encoding_audit(out):
 import numpy as np
 from transformers import AutoTokenizer
 from legal_bench.proof_carrying.semantic_model_inputs_v19 import graph_arrays,window_plan,ce_windows
 data=read(out/'input.json');vectors=np.load(out/'vectors.npz');g=graph_arrays(data['graph'],read(out/'graph-plan.json'),vectors)
 tok=AutoTokenizer.from_pretrained(ROOT/'.runtime/proof-semantic-v12-model',local_files_only=True);audit=[]
 for pair in data['ce_pairs']:
  left,plans,receipt=window_plan(tok,pair);windows=ce_windows(tok,pair)
  assert len(windows)==len(plans)
  assert sum(len(w['right_ids']) for w in plans)==receipt['right_tokens']
  for x,w in zip(windows,plans):assert x['input_ids'][0].tolist()==tok.build_inputs_with_special_tokens(left,w['right_ids'])
  audit.append(receipt)
 save(out/'coverage-audit.json',{'status':'PASS','E5_vectors':len(vectors.files),'x_shape':list(g['x'].shape),'CE':audit,'relation_counts':data['relation_counts'],'not_semantic_proof':True})
 print('COMPLETE_INPUT_COVERAGE_PASS')

def encode():
 from scripts.proof_local_comparison_v19 import encoding
 encoding();out=OUT/'encoding'
 if not (out/'encoding.json').exists():
  rc=subprocess.run([str(ROOT/'.runtime/irac-e5-v1/bin/python'),str(ROOT/'scripts/proof_semantic_encode_v13.py'),str(out)],cwd=ROOT)
  if rc.returncode:raise ValueError('ENCODING_FAILED')
 # Complete actual source map encoded into hashed node texts, all chunks retained.
 receipt=read(out/'encoding.json');texts=read(out/'texts.json');assert {x['sha256'] for x in receipt['audit']}==set(texts)
 save(out/'complete-input-audit.json',{'status':'PASS','encoded_texts':len(texts),'encoding_sha256':sha(out/'encoding.json'),'all_chunks':True,'reference_used':False})

def scoring_tasks():
 cfg=assert_frozen()
 for cid in cfg['DEV']:
  answers={}
  for m in 'ABCDEFG':
   path=OUT/'local'/cid/m/'formal-answer.json';answers[m]=read(path) if path.exists() else {'status':'NOT_STARTED','answer':None}
  ref=read(OUT/'private/frozen-references'/cid/'checklist.json');mapping,tasks=report.blind_tasks(cid,fixture(cid)['case'],fixture(cid)['rules'],ref,answers)
  save(OUT/'private/blind-mapping'/cid/'mapping.json',mapping)
  for task in tasks:
   d=OUT/'web/tasks'/cid/('score-%02d'%task['part']);text(d/'task.txt',task['text']);save(d/'manifest.json',{k:v for k,v in task.items() if k!='text'})

def scoring_results():
 cfg=assert_frozen();methods={m:[] for m in 'ABCDEFG'};traces=[];issues=[]
 for cid in cfg['DEV']:
  mapping=read(OUT/'private/blind-mapping'/cid/'mapping.json');ref=read(OUT/'private/frozen-references'/cid/'checklist.json');answers={}
  for n,m in mapping.items():
   path=OUT/'local'/cid/m/'formal-answer.json';answers[n]=read(path) if path.exists() else {'status':'NOT_STARTED','answer':None}
  scored={};rawreviews={}
  for part in (1,2):
   path=OUT/'web/evaluation'/cid/('score-%02d'%part)/'parsed.json';manifest=read(OUT/'web/tasks'/cid/('score-%02d'%part)/'manifest.json')
   if path.exists():
    rev=read(path);scored.update(report.validate_review(rev,ref,manifest['expected_ids'],answers));rawreviews.update({x['answer_id']:x for x in rev['answers']})
    if rev.get('reference_disagreements'):issues.append({'case_id':cid,'part':part,'disagreements':rev['reference_disagreements']})
   elif manifest['has_evaluable_answer']:issues.append({'case_id':cid,'part':part,'status':'WEB_REVIEW_MISSING','semantics':None})
  for n,m in mapping.items():
   value=scored.get(n,{});methods[m].append({**value,'case_id':cid,'request_id':'Q1','dispute_id':fixture(cid)['case']['dispute_id'],'technical_status':answers[n]['status'],'semantic_review_present':n in scored})
   audit=OUT/'local'/cid/m/'offline-audit.json';baseline=OUT/'local'/cid/'P/offline-audit.json';pp=OUT/'local'/cid/'P/merged.json'
   if audit.exists() and baseline.exists() and pp.exists():traces+=report.transfer_trace(cid,m,read(pp)['answer'],read(audit),read(baseline),answers[n]['answer'],rawreviews.get(n))
 predictions={}
 for m in ('Flat','CrossEncoder','RGCN'):
  path=OUT/'training'/m/'all-candidate-predictions.json'
  if path.exists():predictions[m]=read(path)
 rowsfile=OUT/'freeze/training-rows.json';rows=read(rowsfile) if rowsfile.exists() else []
 save(OUT/'local-classification-metrics.json',report.local_report(rows,predictions));save(OUT/'prediction-to-answer-trace.json',traces)
 save(OUT/'full-answer-metrics.json',{'by_method':{m:report.equal_dispute_summary(rr,len(cfg['DEV'])) for m,rr in methods.items()},'per_request':methods,'reference_status':'MODEL_GENERATED_SOURCE_REVIEWED_NOT_HUMAN_GOLD','no_composite_score':True})
 pairs={}
 for left,right in [('C','A'),('D','C'),('E','D'),('F','D'),('G','D'),('G','E'),('E','A'),('F','A'),('G','A'),('E','B'),('F','B'),('G','B')]:
  paired=[]
  ix={x['case_id']:x for x in methods[left]}
  for row in methods[right]:
   a=ix[row['case_id']]
   if a['technical_status']=='OK' and row['technical_status']=='OK' and a.get('semantic_review_present') and row.get('semantic_review_present'):paired.append({'case_id':row['case_id'],'left':a,'right':row})
  pairs[left+'_vs_'+right]=paired
 save(OUT/'paired-completed-results.json',pairs)
 save(OUT/'evaluation-disagreements.json',issues)
 print('RESULTS_SAVED; decisive source review still separate')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['accept','encoding-audit','encode','score-tasks','score-results']);ap.add_argument('--input',type=Path);a=ap.parse_args();os.chdir(ROOT)
 if a.phase=='accept':acceptance()
 elif a.phase=='encoding-audit':encoding_audit(a.input)
 elif a.phase=='encode':encode()
 elif a.phase=='score-tasks':scoring_tasks()
 elif a.phase=='score-results':scoring_results()
if __name__=='__main__':main()
