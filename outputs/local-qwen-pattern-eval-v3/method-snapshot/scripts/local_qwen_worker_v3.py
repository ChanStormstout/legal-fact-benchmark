"""Version 2 compact constrained JSON; sequential same-model A/B; no references."""
import sys,json,time,hashlib,traceback,resource,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read,canonical,digest
from legal_bench.fast_development import VOCABULARY
from legal_bench.model_output import parse_one
from legal_bench.compact_output_v3 import prompt as compact_prompt, schema as output_schema, convert
from legal_bench.mlx_json_constraint import tokenizer_data,SchemaMask
from legal_bench.field_pipeline_v2 import import_declared,execute_declared
from legal_bench.typed_relations import import_edges
from scripts.run_new10_exploration import SEMANTICS
ROOT=Path('outputs/local-qwen-pattern-eval-v3')
SETTINGS={'model':'mlx-community/Qwen3.5-9B-4bit','revision':'8b2b98c00a6b4d291155e4890773ca8f769aee53','mlx_vlm':'0.7.4','total_budget':32768,'A_max_tokens':4096,'B_max_tokens':8192,'temperature':0.0,'top_p':1.0,'top_k':0,'min_p':0.0,'repetition_penalty':1.0,'seed':20261001,'enable_thinking':False,'prefill_step_size':256,'timeout_seconds':1200,'media_input':False,'format_version':'compact-schema-v3-bounded','schema_enforcer':'lm-format-enforcer==0.11.2/MLX logits hook','sampling_note':'Greedy temperature=0; top_p=1/top_k=0/min_p=0 deactivate filtering. No KV quantization or sliding window.'}

def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2))

def prompt_for(source,method):
 return compact_prompt(source,method,read(ROOT/'tasks.json')['tasks'],SEMANTICS)

def scoreable_direct(data,source):
 if data.get('case_id')!=source['case_id']:raise ValueError('case id mismatch')
 cards=read(ROOT/'tasks.json')['tasks'];am={x['task_id']:x for x in data['answers']};sm={s['id']:s['text'] for s in source['segments']};rows=[]
 for c in cards:
  a=am.get(c['task_id']);errors=[]
  if not a or a.get('answer_status') not in ['MATCH','NOT_FOUND','UNKNOWN']:rows.append({'task_id':c['task_id'],'answer_status':None,'run_status':'FORMAT_ERROR','reason':'MISSING_OR_INVALID_ANSWER'});continue
  def walk(x):
   if isinstance(x,dict):
    if 'quote' in x and (not x.get('quote') or x['quote'] not in sm.get(x.get('segment_id'),'')):errors.append('UNLOCATED_QUOTE:'+str(x.get('segment_id')))
    for v in x.values():walk(v)
   elif isinstance(x,list):
    for v in x:walk(v)
  walk(a)
  if a['answer_status']=='MATCH' and not a.get('bindings'):errors.append('MATCH_WITHOUT_BINDING')
  rows.append(dict(a,run_status='OK',answer_status=a['answer_status'],raw_answer_status=a['answer_status'],automatic_errors=errors,source_anchor_valid=not errors,semantic_validity='NOT_ESTABLISHED'))
 return rows

def computed(data,source):
 v=import_declared(data,source)
 target={'parent_pairs':[{'left':e.get('left'),'right':e.get('right')} for e in data.get('edges',[]) if isinstance(e,dict) and e.get('op')=='part_of'],'group_ids':[o['id'] for o in v['objects'] if o.get('kind')=='GROUP']}
 reg=import_edges(v,source,data,target)
 for edge in reg['edges']:edge['origin']='LOCAL_MODEL_SOURCE_DECLARATION_NOT_HUMAN_GOLD'
 rows=[]
 for c in read(ROOT/'tasks.json')['tasks']:
  q=c['query'];co={'atoms':q['atoms'],'constraints':[x for x in q['constraints'] if x['op'] not in ['part_of','member_of']]}
  b=execute_declared(v,reg,q);base=execute_declared(v,reg,co)
  rows.append({'task_id':c['task_id'],'answer_status':b['status'] if b['status']!='UNSUPPORTED' else None,'run_status':'OK' if b['status']!='UNSUPPORTED' else 'UNSUPPORTED','trace':b,'cooccurrence':{'answer_status':base['status'],'run_status':'OK','trace':base}})
 return v,reg,rows

def run(source_path,out_path,config_path=None):
 source=read(Path(source_path));out=Path(out_path);out.mkdir(parents=True,exist_ok=True)
 if (out/'complete.json').exists():print('Already completed; retained',out,flush=True);return
 settings=read(Path(config_path)) if config_path else SETTINGS
 if config_path and (ROOT/'freeze.json').exists():
  freeze=read(ROOT/'freeze.json')
  for p,h in freeze['method_hashes'].items():
   if digest(Path(p).read_bytes())!=h:raise ValueError('Frozen code differs: '+p)
 import mlx.core as mx
 from mlx_vlm import load
 from mlx_vlm.generate import stream_generate
 from mlx_vlm.generate.types import GenerateKwargs
 from mlx_vlm.prompt_utils import apply_chat_template
 model_path=(ROOT/'environment/model-path.txt').read_text().strip();start=time.perf_counter()
 write(out/'start.json',{'case_id':source['case_id'],'source_hash':digest(source),'settings':settings,'started_at':time.time()})
 model,processor=load(model_path);tok=processor.tokenizer if hasattr(processor,'tokenizer') else processor
 constraint_data=tokenizer_data(tok,getattr(tok,'eos_token_ids',tok.eos_token_id))
 rendered={};tokens={};prepared={}
 for method in ['A','B']:
  prompt=prompt_for(source,method);(out/(method+'-input.txt')).write_text(prompt)
  chat=apply_chat_template(processor,model.config,prompt,enable_thinking=False,num_images=0,num_audios=0)
  rendered[method]=chat;ids=tok.encode(chat);tokens[method]=len(ids);prepared[method]={'input_hash':digest(prompt.encode()),'rendered_hash':digest(chat.encode()),'prompt_tokens':len(ids),'thinking_disabled_template_suffix':chat[-200:],'empty_think_closed':chat.rstrip().endswith('</think>'),'has_empty_think':('<think>\n\n</think>' in chat[-100:])}
  (out/(method+'-rendered.txt')).write_text(chat)
 write(out/'token-budget.json',{'source_tokens':len(tok.encode('\n'.join(s['text'] for s in source['segments']))),'methods':prepared,'total_budget':settings['total_budget'],'loaded_seconds':time.perf_counter()-start})
 too_long=any(tokens[m]+settings[m+'_max_tokens']>settings['total_budget'] for m in ['A','B'])
 for method in ['A','B']:
  f=out/method;f.mkdir(exist_ok=True)
  if (f/'run.json').exists():continue
  metadata={'case_id':source['case_id'],'method':method,'settings':settings,'sample_role':'DEVELOPMENT_FORMAT_REPAIR_VALIDATION',**prepared[method]}
  if too_long:
   write(f/'run.json',dict(metadata,run_status='INPUT_TOO_LONG',answer_status=None,reason='Full common source plus either method output reserve exceeds frozen total budget; neither method input truncated.'));continue
  mx.random.seed(settings['seed']);mx.clear_cache();mx.reset_peak_memory();t=time.perf_counter();raw='';last=None
  kw={k:settings[k] for k in ['temperature','top_p','top_k','min_p','repetition_penalty','enable_thinking','prefill_step_size']};kw['max_tokens']=settings[method+'_max_tokens']
  mask=SchemaMask(constraint_data,output_schema(source,method,read(ROOT/'tasks.json')['tasks']));kw['logits_processors']=[mask]
  unsupported=set(kw)-set(GenerateKwargs.__annotations__)
  if unsupported:raise ValueError('Unsupported parameters '+str(unsupported))
  print('START',source['case_id'],method,'input',tokens[method],flush=True)
  try:
   with (f/'raw-response.txt').open('w') as stream:
    for last in stream_generate(model,processor,rendered[method],image=None,audio=None,video=None,**kw):
     raw+=last.text;stream.write(last.text);stream.flush()
     if time.perf_counter()-t>settings['timeout_seconds']:raise TimeoutError('Generation wall-clock budget exceeded')
     if last.generation_tokens%256==0:print('PROGRESS',method,last.generation_tokens,round(time.perf_counter()-t,1),flush=True)
   if last is None:raise ValueError('No generation result')
   run_status='OUTPUT_TRUNCATED' if last.finish_reason!='stop' else 'OK'
   metadata.update(run_status=run_status,answer_status=None,finish_reason=last.finish_reason,prompt_tokens_actual=last.prompt_tokens,output_tokens=last.generation_tokens,elapsed_seconds=time.perf_counter()-t,peak_mlx_memory_gb=last.peak_memory,peak_rss_gb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e9,raw_hash=digest(raw.encode()),actual_parameters={k:v for k,v in kw.items() if k!='logits_processors'},schema_constraint={'adapter':'SchemaMask','library':'lm-format-enforcer==0.11.2','calls':mask.calls,'schema_hash':digest(output_schema(source,method,read(ROOT/'tasks.json')['tasks']))},seed_applied='mx.random.seed',thinking_output_present='<think>' in raw or '</think>' in raw)
   if metadata['thinking_output_present']:metadata['thinking_disable_verified']=False
   else:metadata['thinking_disable_verified']=prepared[method]['has_empty_think']
   if run_status=='OK':
    compact,repairs=parse_one(raw.encode());write(f/'compact.json',compact);data,operations=convert(compact,source,method,read(ROOT/'tasks.json')['tasks']);write(f/'parsed.json',data);metadata['format_repairs']=repairs;metadata['conversion_operations']=operations
    if method=='A':rows=scoreable_direct(data,source)
    else:
     v,reg,rows=computed(data,source);write(f/'view.json',v);write(f/'relations.json',reg)
    write(f/'answers.json',{'case_id':source['case_id'],'answers':rows})
   write(f/'run.json',metadata)
  except Exception as exc:
   err='TIMEOUT' if isinstance(exc,TimeoutError) else 'OUT_OF_MEMORY' if 'memory' in str(exc).lower() else 'FORMAT_ERROR' if isinstance(exc,(ValueError,KeyError,TypeError)) else 'UNSUPPORTED'
   write(f/'run.json',dict(metadata,run_status=err,answer_status=None,error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),elapsed_seconds=time.perf_counter()-t,peak_mlx_memory_gb=mx.get_peak_memory()/1e9,peak_rss_gb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e9));print('FAIL',method,err,str(exc),flush=True)
  print('END',method,read(f/'run.json')['run_status'],round(time.perf_counter()-t,1),flush=True)
 write(out/'complete.json',{'case_id':source['case_id'],'elapsed_seconds':time.perf_counter()-start,'methods':{m:read(out/m/'run.json')['run_status'] for m in ['A','B']}})

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True);p.add_argument('--config');a=p.parse_args();run(a.source,a.out,a.config)
