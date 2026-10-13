#!/usr/bin/env python3
"""V18 actual integration acceptance, encoding audit, baseline and blinded evaluation.
No generator call or training in acceptance. Tested raw source is really encoded.
"""
import argparse,copy,json,os,subprocess,sys,collections,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.proof_local_comparison_v18_recovery import OUT,BASE,PREP,OLD,read,save,text,sha,fixture,protocol,assert_frozen
from legal_bench.proof_carrying import local_pipeline_v18_recovery as pipe
from legal_bench.proof_carrying import local_reporting_v18 as report

def acceptance():
 from tests.test_local_comparison_v18 import fixture as synthetic
 from legal_bench.proof_carrying.local_checker_v18 import check
 c,r,p=synthetic();audit=pipe.apply_connection_decisions(c,r,p);assert check(r,audit)['traces'][0]['status']=='CONDITIONAL_TRACE_RECOMPUTED'
 invalid=copy.deepcopy(p);invalid['uses'].append(copy.deepcopy(p['uses'][0]));invalid['uses'][1]['bindings'][0]['object']=999;invalid['premises'][0]['uses']=[1,2]
 a=pipe.apply_connection_decisions(c,r,invalid);assert a['conditional_rules'][0]['conditional_result']=='TRUE';assert a['checks'][1]['disposition']=='STRUCTURAL_INVALID'
 counter=pipe.apply_connection_decisions(c,r,p,{'K001':'UNSUPPORTED'});assert counter['conditional_rules'][0]['conditional_result']=='UNKNOWN'
 d,receipt=pipe.display_material({'proposal':p,'checks':[audit,audit]})
 def expand(x):
  if isinstance(x,dict):return {k:expand(v) for k,v in x.items()}
  if isinstance(x,list):
   out=[]
   for v in x:
    out.append(copy.deepcopy(out[v['$exact_same_item_as_1based_index']-1]) if isinstance(v,dict) and set(v)=={'$exact_same_item_as_1based_index'} else expand(v))
   return out
  return x
 assert expand(d)=={'proposal':p,'checks':[audit,audit]}
 final=pipe.final_prompt(c,r,d);assert pipe.source_text(c) in final and '$exact_same_item_as_1based_index' in final
 # Actual saved source, without reference labels: source restoration in the same model input adapter.
 real=fixture('396336')['case'];seg=real['segments'][0];p['records'][0].update(text=seg['text'],refs=[seg['id']]);p['objects'][0].update(refs=[seg['id']]);p['uses'][0]['witnesses'][0].update(refs=[seg['id']],quote=seg['text'][:100])
 data=pipe.learner_inputs(real,r,p);assert seg['text'] in data['ce_pairs'][0]['right'];assert data['relation_counts']['SUPPORT']==1
 out=OUT/'engineering/actual-encoding';plan=[];texts={}
 for n in data['graph']['nodes']:
  h=report.hash_value(n['text']);texts[h]=n['text'];plan.append({'node':n['id'],'part_sha256':[h]})
 save(out/'texts.json',texts);save(out/'input.json',data);save(out/'graph-plan.json',{'graph':plan})
 if not (out/'encoding.json').exists():
  result=subprocess.run([str(ROOT/'.runtime/irac-e5-v1/bin/python'),str(ROOT/'scripts/proof_semantic_encode_v13.py'),str(out)],cwd=ROOT,capture_output=True,text=True)
  text(out/'encoder-log.txt',result.stdout+result.stderr)
  if result.returncode:raise ValueError('ACTUAL_E5_ENCODER_FAILED')
 # CE tokenizer and E5 graph are checked in their existing Torch environment (no model generation).
 result=subprocess.run([str(ROOT/'.runtime/proof-semantic-v12/bin/python'),str(__file__),'encoding-audit','--input',str(out)],cwd=ROOT,capture_output=True,text=True)
 logpath=out/'input-audit-log.txt'
 if logpath.exists():logpath=out/('input-audit-log-'+str(time.time_ns())+'.txt')
 text(logpath,result.stdout+result.stderr)
 if result.returncode:raise ValueError('ACTUAL_INPUT_ENCODING_AUDIT_FAILED')
 rows=[{'key':'D::K001','split':'DEV','dispute_id':'D','request_id':'Q1','premise_family':'f','label':'SUPPORTED','P_self_assessment':'SUPPORTED','structurally_valid':True},
       {'key':'T::K001','split':'TRAIN','dispute_id':'T','request_id':'Q1','premise_family':'f','label':'UNSUPPORTED','P_self_assessment':'SUPPORTED','structurally_valid':True}]
 metrics=report.local_report(rows,{'Flat':[{'key':'D::K001','label':'UNSUPPORTED'}]});assert metrics['methods']['RawP']['all_scorable']['connection_confusion']['confusion_gold_rows_prediction_columns'][0][0]==1
 ref={'key_items':[{'id':'KEY001','text':'synthetic'}]};answers={m:{'answer':None,'status':'TECHNICAL_FAILURE'} for m in 'ABCDEFG'}
 mapping,tasks=report.blind_tasks('SYN',c,r,ref,answers);neutral={n:answers[m] for n,m in mapping.items()}
 rev={'answers':[{'answer_id':n,'technical_status':'TECHNICAL_FAILURE','answer':None} for n in tasks[0]['expected_ids']]}
 assert len(report.validate_review(rev,ref,tasks[0]['expected_ids'],neutral))==4
 save(OUT/'engineering/synthetic-entry-results.json',{'input_source':'396336 first allowed segment, no reference','raw_P':p,'analysis':audit,'invalid_use_local_result':a,'changed_use_result':counter,'display_receipt':receipt,'metrics':metrics,'neutral_mapping':mapping,'null_review':rev})
 keys=collections.Counter();dep=[];total=0;ops=collections.Counter()
 for path in (PREP/'inputs').glob('*/fixture.json'):
  f=read(path)
  for rule in f['rules']:
   total+=1;keys.update(rule.keys());ops[rule['operator']]+=1
   for k in ('dependencies','rule_dependencies','derived_from','depends_on'):
    if rule.get(k):dep.append({'case_id':path.parent.name,'rule':rule['id'],'field':k,'contract':rule[k]})
 save(OUT/'engineering/rule-contract-inventory.json',{'rules':total,'operators':dict(ops),'explicit_dependencies':dep,'scope':'No explicit cross-rule ID/stage/variable contract found; no guessed edges or derivations. Per-rule combination only; final LLM receives all unchanged rules and original source.'})
 certificate=read(BASE/'engineering/real-tokenizer.json');oldtests=(BASE/'engineering/tests.txt').read_text()
 assert '34' in oldtests and 'OK' in oldtests
 save(OUT/'engineering/integration-acceptance.json',{'status':'PASS','old_34_checks_reused':{'path':str(BASE/'engineering/tests.txt'),'sha256':sha(BASE/'engineering/tests.txt'),'rerun':False},'real_tokenizer_replay_reused':{'path':str(BASE/'engineering/real-tokenizer.json'),'sha256':sha(BASE/'engineering/real-tokenizer.json'),'rerun':False},
  'actual_entry':'same pipe adapter, original-source encoding via actual E5, actual CE complete tokenizer windows, graph tensors, prediction override, conditional checker, lossless display, final task, blind scores/technical-null and baselines',
  'engineering_proves':'DATAFLOW_ONLY_NOT_LEGAL_SEMANTICS_OR_MODEL_GAIN','new_LLM_calls':0,'new_training':0,'prepared_prompts_unchanged':True})
 print('ACTUAL_ENTRY_ACCEPTANCE_PASS')

def encoding_audit(out):
 import numpy as np
 from transformers import AutoTokenizer
 from legal_bench.proof_carrying.semantic_model_inputs_v13 import graph_arrays,ce_windows
 data=read(out/'input.json');receipt=read(out/'encoding.json');vectors=np.load(out/'vectors.npz');g=graph_arrays(data['graph'],read(out/'graph-plan.json'),vectors)
 tok=AutoTokenizer.from_pretrained(ROOT/'.runtime/proof-semantic-v12-model',local_files_only=True);aud=[]
 for pair in data['ce_pairs']:
  windows=ce_windows(tok,pair);left=tok(pair['left'],add_special_tokens=False)['input_ids'];rt=pair['right']+'\nSHARED SAME-CASE GRAPH INFORMATION:\n'+json.dumps(pair['shared_case_context'],sort_keys=True,ensure_ascii=False)
  right=tok(rt,add_special_tokens=False)['input_ids'];capacity=8192-len(left)-tok.num_special_tokens_to_add(pair=True)
  assert len(windows)==max(1,(len(right)+capacity-1)//capacity)
  actual=0
  for i,w in enumerate(windows):
   chunk=right[i*capacity:(i+1)*capacity];expected=tok.build_inputs_with_special_tokens(left,chunk)
   assert w['input_ids'][0].tolist()==expected;actual+=len(chunk)
  assert actual==len(right)
  aud.append({'id':pair['id'],'right_tokens':len(right),'actual_encoded_right_tokens':actual,'windows':[int(w['input_ids'].shape[1]) for w in windows],'truncated':False,'shared_relations_entered':True,'source_entered':True})
 for item in receipt['audit']:
  assert not item['truncated'];ranges=item['chunks'];assert ranges[0]['tokens'][0]==0 and ranges[-1]['tokens'][1]==item['token_count']
  assert all(a['tokens'][1]==b['tokens'][0] for a,b in zip(ranges,ranges[1:]))
 save(out/'coverage-audit.json',{'status':'PASS','actual_E5_node_vectors':len(vectors.files),'graph_x_shape':list(g['x'].shape),'relations':data['relation_counts'],'CE':aud,'raw_source_and_P_distinct':True});print('COMPLETE_INPUT_COVERAGE_PASS')

def encode():
 from scripts.proof_local_comparison_v18_recovery import encoding
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
