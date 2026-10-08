"""Single frozen repair experiment, no retry; deterministic audit and actual local runner."""
import argparse,json,hashlib,copy,shutil,time,sys,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.irac_application.pipeline_v4 import process,display,compact,digest,catalogue
from legal_bench.irac_application.pipeline_v4_tasks import prompt,schema
from legal_bench.irac_application.aligned_v2_runtime import atomic_json as save
R=Path('outputs/irac-pipeline-repair-v4');V=Path('outputs/irac-hybrid-decision-v3')
ALL=['1114159','112400','188721101','52547606','55384096','68065690'];CASES=['112400','188721101','55384096','52547606']
read=lambda p:json.loads(Path(p).read_text());hf=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
CODE=['scripts/irac_pipeline_v4_tokenizer.py','scripts/irac_pipeline_v4.py','legal_bench/irac_application/pipeline_v4.py','legal_bench/irac_application/pipeline_v4_tasks.py','legal_bench/irac_application/hybrid_v3.py','legal_bench/irac_application/hybrid_v3_tasks.py','legal_bench/irac_application/aligned_logic.py','legal_bench/irac_application/aligned_v2_runtime.py','legal_bench/rules_verdict_v1/runtime_constraint_diag_v1.py','legal_bench/mlx_json_constraint.py','legal_bench/mlx_json_constraint_v2.py','legal_bench/rules_verdict_v1/repetition_v9.py','legal_bench/rules_verdict_v1/contracts.py','legal_bench/rules_verdict_v1/source_views.py','tests/test_irac_pipeline_v4.py']

def inputs(cid,stage=None):
 m=read(R/'sources'/f'{cid}.json');t=read(R/'templates'/f"{m['family']}.json");law=read(R/'sources'/f"{m['family']}-law.json")
 if stage in ['D-short','D-full']:
  tid='DRC_BONA_FIDE-C06';t=copy.deepcopy(t);t['tests']=[x for x in t['tests'] if x['id']==tid];t['elements']=[];t['claims']=[]
  if stage=='D-short':m['sources']={k:v for k,v in m['sources'].items() if k in ['IK-112400:L124:restored-v2','IK-112400:L137:context-v4','IK-112400:L138:context-v4','IK-112400:L139:restored-v2','IK-112400:L140:restored-v2']}
 return m,t,law

def prepare():
 assert not (R/'freeze/config.json').exists()
 # Only pre-reviewed exact source-context recovery, no model summaries or target conclusions.
 plans={'112400':[(137,None,None,'Context for remand and the antecedent of The latter.'),(138,None,None,'Identifies Rent Control Tribunal as remand fact finder.')],
 '52547606':[(82,None,'could be made','Restore ARC attribution to existing contrary finding; exclude later text.'),(84,None,None,'Restore ARCT attribution and Mohan Lal antecedent to existing finding.')],
 '55384096':[(76,'RW-1 Sumitra Devi',None,'Recover witness identity only; preceding target approval expressly excluded.'),(77,None,None,'Recover attributed testimony around existing denials/admissions; no target evaluation.')],
 '68065690':[(174,None,None,'Recover source as reply to notice, not final acceptance.'),(176,None,'since 1975.','Recover speaker RW1/respondent and existing testimony; omit adjacent target reasoning.'),(181,None,'other business.','Recover speaker RW2 Kapil; retain only existing quotation extent.')]}
 for p in (V/'templates').glob('*.json'):dest=R/'templates'/p.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 for p in (V/'sources').glob('*-law.json'):dest=R/'sources'/p.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 audits=[]
 for cid in ALL:
  old=read(V/'sources'/f'{cid}.json');m=copy.deepcopy(old)
  rawp=Path(f'outputs/gnn-irac-native-data-01/sources/raw/single-{cid}-0.txt') if cid in ['1114159','112400'] else Path(f'outputs/rgcn-data-expansion-09/continuation-01/open-{cid}-0.txt')
  raw=rawp.read_text();line_map={int(mt.group(1)):(mt.group(2),mt.start(2),mt.end(2)) for mt in re.finditer(r'^L(\d+): ?(.*)$',raw,re.M)}
  additions=[]
  for n,start,end,reason in plans.get(cid,[]):
   text,a,b=line_map[n]
   if start:a+=text.index(start);text=text[text.index(start):]
   if end:text=text[:text.index(end)+len(end)]
   b=a+len(text);assert raw[a:b]==text
   sid=f'IK-{cid}:L{n}:context-v4';prov={'raw_path':str(rawp),'raw_sha256':hf(rawp),'raw_char_range':[a,b],'original_line':n,'document_id':cid,'url':f'https://indiankanoon.org/doc/{cid}/'}
   m['sources'][sid]={'text':text,'document_id':cid,'url':prov['url'],'semantic_stage':'PRIOR_COURT_FINDING' if cid=='52547606' else 'PRE_TARGET_RECORD','prospective_availability':'RETROSPECTIVELY_RECONSTRUCTED_PRE_TARGET','parent_source_id':f'IK-{cid}:L{n}','provenance':[prov]}
   additions.append({'source_id':sid,'reason':reason,'target_decisive_reasoning_included':False,**prov})
  source_map=[]
  for sid,s in m['sources'].items():
   assert str(s['document_id'])==cid
   hit=raw.find(s['text']);source_map.append({'source_id':sid,'document_id':cid,'url':s['url'],'raw_path':str(rawp),'raw_sha256':hf(rawp),'raw_char_range':[hit,hit+len(s['text'])] if hit>=0 else None,'text_exact_in_raw':hit>=0,'allowed_text_sha256':digest(s['text'])})
  assert all(x['text_exact_in_raw'] for x in source_map),[x for x in source_map if not x['text_exact_in_raw']]
  view,mapping=display(m);save(R/'sources'/f'{cid}.json',m);save(R/'input-audit'/f'{cid}.json',{'case_id':cid,'target_stage':m['target_stage'],'target_court':m['target_court'],'stage_scope':'Existing reconstructed task stage retained; original judgment may be from a later court. No historical prediction claim.','source_map':source_map,'additions':additions,'display_map':mapping,'display':view,'old_source_count':len(old['sources']),'new_source_count':len(m['sources']),'display_count':len(view['records']),'semantic_context_complete':False,'context_limits':'Context recovery confined to attribution for existing fragments. Whole case not restored; testimonial truth, missing law and excluded target reasoning remain unresolved.'})
  audits.append({'case_id':cid,'added_spans':len(additions),'display_records':len(view['records']),'old_records':len(old['sources']),'new_records':len(m['sources'])})
 save(R/'input-audit/summary.json',audits)
 order=['112400/D-short','112400/D-full']+[f'{c}/{s}' for c in CASES for s in ['A','P','B','C']]
 save(R/'protocol.json',{'cases':CASES,'audit_cases':ALL,'order':order,'max_calls':18,'max_tokens':{'diagnostic':1024,'proposal':4096,'final':3072},'context':32768,'generation_seconds_budget':3600,'seed':20261001,'web':0,'retries':0,'training':0,'diagnostic_short_sources':'Frozen selection of C06 claim identity and remand finding context; excludes other fact disputes; not pure length comparison.','comparison':'Exposed development; interface, display, condition contract and proposal budget jointly changed; not single-variable v3 comparison. A/B/C share exact law/case display.','evaluation':'One source review after all runs. No new gold or binary conversion. Inspect decisive opposition beyond cited paragraphs. No modifications after first generation.','failure':'Only dependent steps skipped; environment/resource/time failure stops rest. No retry or semantic repair.','stop':'After <=18 calls and one review; no further experiment, commit or push.'})
 for slot in order:
  cid,stage=slot.split('/')
  if stage in ['B','C']:continue
  m,t,l=inputs(cid,stage);kind='diagnostic' if stage.startswith('D-') else 'proposal' if stage=='P' else 'final';dest=R/'prepared'/cid/stage;dest.mkdir(parents=True,exist_ok=True);(dest/'prompt.txt').write_text(prompt(kind,m,t,l));save(dest/'schema.json',schema(kind,m,t,l))
 # One offline replay of every stored v3 proposal. Truncated JSON remains a failure.
 rows=[]
 for cid in ALL:
  m,t,l=inputs(cid);src=dict(m['sources']);src.update({x['source_id']:x for x in l});run=read(V/'runs'/cid/'proposal/run.json');raw=(V/'runs'/cid/'proposal/raw-response.txt').read_text()
  if run['run_status']!='OK':result={'status':run['run_status'],'usable':False,'raw_path':str(V/'runs'/cid/'proposal/raw-response.txt'),'answer':None}
  else:
   value=json.loads(raw);result,checks=process(value,t,src,cid)
   if checks:save(R/'replay'/cid/'checks.json',checks)
  save(R/'replay'/cid/'import.json',result);rows.append({'case_id':cid,'old_status':read(V/'runs'/cid/'proposal/result.json')['run_status'],'new_status':result['status'],'usable':result['usable'],'records':len(result.get('projection',{}).get('evidence',[])),'quarantine':len(result.get('quarantine',[])),'not_produced':len(result.get('missing',[]))})
 save(R/'replay/summary.json',rows)

def finish_attempt(run,out,stage,m,t,law):
 result={'case_id':m['case_id'],'method':stage,'run_status':run['run_status'],'prediction':None};src=dict(m['sources']);src.update({x['source_id']:x for x in law})
 if run['run_status']=='OK' or (stage=='P' and run['run_status']=='FORMAT_ERROR' and run.get('framework_finish_reason')=='stop'):
  try:value=json.loads((out/'raw-response.txt').read_text())
  except (ValueError,OSError):value=None
  if value is not None and run.get('schema_mask_calls',0)>0:
   if stage=='P':
    imp,checks=process(value,t,src,m['case_id']);save(out/'import.json',imp)
    if imp['usable']:
     result.update(run_status='OK',prediction=value,import_status=imp['status']);save(out/'checks-full.json',checks);save(out/'checks-compact.json',compact(checks))
    else:result.update(run_status='FORMAT_ERROR',reason=imp['status'])
   else:
    try:
     from legal_bench.rules_verdict_v1.contracts import validate
     validate(value,read(out/'schema.json'))
     if not stage.startswith('D-'):
      expected={c['id'] for c in t['claims'] if c['expression']['op']!='UNSUPPORTED'}
      assert {a['claim_id'] for a in value['answers']}==expected
     result['prediction']=value
    except (AssertionError,ValueError,KeyError,TypeError) as e:result.update(run_status='FORMAT_ERROR',reason=repr(e))
  elif run['run_status']=='OK':result.update(run_status='FORMAT_ERROR',reason='UNREADABLE_OR_MASK_NOT_EFFECTIVE')
 save(out/'result.json',result);return result

def complete_slot(runner,cid,stage,text,contract,remaining,out):
 m,t,l=inputs(cid,stage);budget=1024 if stage.startswith('D-') else 4096 if stage=='P' else 3072
 # Save exact rendered input BEFORE generation; compare saved runner input afterwards.
 out.mkdir(parents=True,exist_ok=True);rendered=runner.render(text);save(out/'input-before-generation.json',{'prompt_sha256':digest(text),'rendered_sha256':digest(rendered),'input_tokens':len(runner.tokenizer.encode(rendered)),'max_tokens':budget,'material_sha256':digest(json.dumps(display(m)[0],ensure_ascii=False)),'law_sha256':digest(json.dumps(l,ensure_ascii=False))});(out/'rendered-before-generation.txt').write_text(rendered)
 view,aliases=display(m);spans=[]
 for row in view['records']:
  encoded=json.dumps(row['text'],ensure_ascii=False);pos=text.index(encoded);rpos=rendered.index(encoded)
  spans.append({'display_id':row['source_id'],'prompt_char_range':[pos,pos+len(encoded)],'rendered_char_range':[rpos,rpos+len(encoded)],'aliases':row['aliases'],'text_sha256':digest(row['text']),'encoding':'JSON string including quotes; decoding exactly recovers source text'})
 save(out/'source-to-input.json',{'display_spans':spans,'alias_map':aliases,'law_in_prompt':all(json.dumps(s['text'],ensure_ascii=False) in text for s in l),'template_scope_in_prompt':json.dumps(t,ensure_ascii=False) in text})
 run=runner.run(text,contract,out,max_tokens=budget,remaining_seconds=remaining,constraint_mode='FIXED')
 assert (out/'prompt.txt').read_text()==text and (out/'rendered.txt').read_text()==rendered,'ACTUAL_INPUT_MISMATCH'
 save(out/'input-delivery.json',{'prompt_matches':True,'rendered_matches':True,'model_prompt_tokens_reported':run.get('prompt_tokens_actual'),'counted_tokens':run.get('prompt_tokens'),'text_not_truncated':not run.get('source_input_truncated',False)})
 return finish_attempt(run,out,stage,m,t,l),run

def freeze():
 assert not (R/'freeze/config.json').exists();log=(R/'engineering/tests.txt').read_text();assert '\nOK' in log and 'skipped=' not in log
 assert read(R/'engineering/real-tokenizer.json')['passed']
 settings=read(V/'freeze/config.json')['settings'];files={str(p):hf(p) for folder in ['sources','templates','prepared','input-audit','replay','engineering'] for p in (R/folder).rglob('*') if p.is_file()};files[str(R/'protocol.json')]=hf(R/'protocol.json')
 for p in CODE:
  dest=R/'freeze/code'/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);files[str(dest)]=hf(dest)
 save(R/'freeze/config.json',{'time':time.time(),'settings':settings,'files':files,'live_code':{p:hf(p) for p in CODE},'constraint_mode':'FIXED','max_tokens':read(R/'protocol.json')['max_tokens'],'evaluation':read(R/'protocol.json')['evaluation']})
def verify():
 f=read(R/'freeze/config.json')
 for p,h in {**f['files'],**f['live_code']}.items():assert hf(p)==h,p
 return f

def run():
 from legal_bench.rules_verdict_v1.runtime_constraint_diag_v1 import Runner
 f=verify();assert not (R/'run-ledger.json').exists(),'already started; no duplicate call'
 specs=read(R/'protocol.json')['order'];save(R/'run-ledger.json',{'status':'STARTING','order':specs})
 try:r=Runner(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),f['settings'])
 except Exception as e:save(R/'run-ledger.json',{'status':'ENVIRONMENT_BLOCKED','error':repr(e)});return
 pre=[]
 for s in specs:
  c,st=s.split('/');p=R/'prepared'/c/st
  if not p.exists():continue
  txt=(p/'prompt.txt').read_text();ren=r.render(txt);(p/'rendered-preflight.txt').write_text(ren);n=len(r.tokenizer.encode(ren));b=1024 if st.startswith('D-') else 4096 if st=='P' else 3072;pre.append({'slot':s,'input_tokens':n,'max_tokens':b,'within_budget':n+b<=32768,'thinking_off':'<think>\n\n</think>' in ren[-150:]})
 save(R/'freeze/token-preflight.json',{'rows':pre,'versions':r.versions,'load_seconds':r.loaded_seconds,'model_config_hash':r.model_config_hash,'dynamic_B_C':'Count full rendered input immediately before each call, never truncate.'})
 rows=[];spent=0;stop=None;props={}
 for slot in specs:
  verify();cid,stage=slot.split('/');out=R/'runs'/cid/stage
  if stop or (stage in ['B','C'] and cid not in props):
   result={'case_id':cid,'method':stage,'run_status':'SKIPPED','prediction':None,'reason':stop or 'NO_READABLE_USABLE_PROPOSAL'};save(out/'result.json',result);rows.append(result);continue
  m,t,l=inputs(cid,stage)
  if stage in ['B','C']:
   inter={'proposal':props[cid],'import_coverage':{k:v for k,v in read(R/'runs'/cid/'P/import.json').items() if k in ['missing','quarantine','status']}}
   if stage=='C':inter['program_checks']=read(R/'runs'/cid/'P/checks-compact.json')
   text=prompt('final',m,t,l,inter);contract=schema('final',m,t,l);dest=R/'prepared'/cid/stage;dest.mkdir(parents=True,exist_ok=True);(dest/'prompt.txt').write_text(text);save(dest/'schema.json',contract);save(dest/'intermediate.json',inter)
  else:dest=R/'prepared'/cid/stage;text=(dest/'prompt.txt').read_text();contract=read(dest/'schema.json')
  remaining=3600-spent
  if remaining<=0:stop='TOTAL_TIME_BUDGET';save(out/'result.json',{'run_status':'SKIPPED','prediction':None,'reason':stop});continue
  try:result,meta=complete_slot(r,cid,stage,text,contract,remaining,out)
  except Exception as e:result={'case_id':cid,'method':stage,'run_status':'FRAMEWORK_OR_RECORDING_ERROR','prediction':None,'error':repr(e)};save(out/'result.json',result);meta={};stop='FRAMEWORK_OR_RECORDING_ERROR'
  spent+=meta.get('elapsed_seconds',0)
  if stage=='P' and result['run_status']=='OK':props[cid]=result['prediction']
  if meta.get('run_status') in ['OUT_OF_MEMORY','UNSUPPORTED','TIMEOUT']:stop=meta['run_status']
  rows.append({'slot':slot,'run_status':result['run_status'],'seconds':meta.get('elapsed_seconds'),'output_tokens':meta.get('output_tokens'),'input_tokens':meta.get('prompt_tokens')});save(R/'run-ledger.json',{'status':'RUNNING','rows':rows,'seconds':spent,'stop':stop})
 save(R/'run-ledger.json',{'status':'COMPLETE' if not stop else 'STOPPED','rows':rows,'seconds':spent,'stop':stop,'calls':len(list((R/'runs').glob('*/*/start.json'))),'no_retry':True})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','freeze','verify','run']);globals()[p.parse_args().command]()
