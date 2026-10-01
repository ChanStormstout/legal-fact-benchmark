"""Resumable sequential v5 development pilot; no labels supplied to the model."""
import argparse,json,sys,time,resource,traceback,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read,digest,write_new
from legal_bench.chunked_extraction_v4 import chunks,route_prompt,route_schema,routed_source
from legal_bench.registry_extraction_v5 import object_prompt,object_schema,objects,fact_prompt,fact_schema,convert
from legal_bench.compact_output_v3 import validate_shape
from legal_bench.model_output import parse_one
from legal_bench.mlx_json_constraint import SchemaMask,tokenizer_data
from legal_bench.field_pipeline_v2 import import_declared,execute_declared
from legal_bench.typed_relations import import_edges
ROOT=Path('outputs/local-qwen-pattern-eval-v5');OLD=Path('outputs/local-qwen-pattern-eval-v3')

def write(p,v):write_new(p,v)

def prepare():
 if (ROOT/'config.json').exists():return
 c=copy.deepcopy(read(OLD/'config.json'));c.update(format_version='fixed-object-registry-task-extraction-v5',object_max_tokens=1536,chunk_max_chars=6000,neighbor_context=1,route_max_tokens=700,extract_max_tokens=3072)
 write(ROOT/'config.json',c);write(ROOT/'tasks.json',read(OLD/'tasks.json'))
 write(ROOT/'plan.json',{'role':'EXPOSED_CASE_DEVELOPMENT','cases':['148738','123036'],'selection':'Same two previously source-reviewed failures; fixed before v4 generation. All three questions evaluated per case, no answer-based replacement.','reference_use':'Not sent to model; reused only after outputs for analysis.','stage_order':['All full-source chunks routed once','Neighbor context added with no text changes','Object registry generated first; later references schema-constrained to supplied object IDs','Each fixed question extracted separately','Unchanged converter, importer, directed-edge registry and executor'],'positive_gate':'A claimed match needs assertions, correct state, two distinct objects, direction and exact original-source support. More matches alone does not pass.','limits':'One generation per job; failures retained; no model switch. Every source segment routed, no silent truncation.','next_check':'Only after development evidence, freeze and use unused cases in the same existing 20-source queue; report all categories and failure costs.'})
 for cid in read(ROOT/'plan.json')['cases']:write(ROOT/'sources'/(cid+'.json'),read(OLD/'sources'/(cid+'.json')))
 code=['legal_bench/registry_extraction_v5.py','legal_bench/chunked_extraction_v4.py','scripts/local_qwen_registry_v5.py','legal_bench/compact_output_v3.py','legal_bench/field_pipeline_v2.py','legal_bench/typed_relations.py','legal_bench/mlx_json_constraint.py','legal_bench/model_output.py']
 for f in code:
  p=ROOT/'method-snapshot'/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(Path(f).read_bytes())
 write(ROOT/'development-freeze.json',{'method_hashes':{f:digest(Path(f).read_bytes()) for f in code},'config_hash':digest(c),'tasks_hash':digest(read(ROOT/'tasks.json')),'no_current_correct_bindings_in_prompts':True})

def run(cid):
 config=read(ROOT/'config.json');freeze=read(ROOT/'development-freeze.json')
 assert all(digest(Path(p).read_bytes())==h for p,h in freeze['method_hashes'].items())
 source=read(ROOT/'sources'/(cid+'.json'));out=ROOT/'development'/cid;out.mkdir(parents=True,exist_ok=True)
 if (out/'complete.json').exists():print('Completed case retained',cid);return
 import mlx.core as mx
 from mlx_vlm import load
 from mlx_vlm.generate import stream_generate
 from mlx_vlm.generate.types import GenerateKwargs
 from mlx_vlm.prompt_utils import apply_chat_template
 model_path=(OLD/'environment/model-path.txt').read_text().strip();model,processor=load(model_path);tok=processor.tokenizer if hasattr(processor,'tokenizer') else processor
 td=tokenizer_data(tok,getattr(tok,'eos_token_ids',tok.eos_token_id))
 def job(name,prompt,sc,limit):
  folder=out/name;folder.mkdir(parents=True,exist_ok=True)
  if (folder/'run.json').exists():
   state=read(folder/'run.json')
   if state['run_status']!='OK':raise RuntimeError('Prior failed job retained: '+name)
   return read(folder/'data.json')
  (folder/'prompt.txt').write_text(prompt);write(folder/'schema.json',sc)
  chat=apply_chat_template(processor,model.config,prompt,enable_thinking=False,num_images=0,num_audios=0);nt=len(tok.encode(chat))
  if nt+limit>config['total_budget']:write(folder/'run.json',{'run_status':'INPUT_TOO_LONG','answer_status':None,'prompt_tokens':nt});raise RuntimeError('INPUT_TOO_LONG')
  mx.random.seed(config['seed']);mx.clear_cache();mx.reset_peak_memory();start=time.perf_counter();raw='';last=None
  kw={k:config[k] for k in ['temperature','top_p','top_k','min_p','repetition_penalty','enable_thinking','prefill_step_size']};kw['max_tokens']=limit;mask=SchemaMask(td,sc);kw['logits_processors']=[mask]
  assert not set(kw)-set(GenerateKwargs.__annotations__)
  print('START',cid,name,nt,flush=True)
  try:
   with (folder/'raw-response.txt').open('w') as f:
    for last in stream_generate(model,processor,chat,image=None,audio=None,video=None,**kw):
     raw+=last.text;f.write(last.text);f.flush()
     if time.perf_counter()-start>config['timeout_seconds']:raise TimeoutError('Generation timeout')
   if last is None:raise ValueError('No output')
   status='OK' if last.finish_reason=='stop' else 'OUTPUT_TRUNCATED'
   meta={'run_status':status,'answer_status':None,'prompt_tokens':nt,'output_tokens':last.generation_tokens,'elapsed_seconds':time.perf_counter()-start,'peak_mlx_memory_gb':last.peak_memory,'schema_hash':digest(sc),'prompt_hash':digest(prompt.encode()),'thinking_output_present':'<think>' in raw or '</think>' in raw,'thinking_closed_in_template':chat.rstrip().endswith('</think>'),'actual_parameters':{k:v for k,v in kw.items() if k!='logits_processors'}}
   if status!='OK':write(folder/'run.json',meta);raise RuntimeError(status)
   data,repairs=parse_one(raw.encode());validate_shape(data,sc);meta['format_repairs']=repairs;write(folder/'data.json',data);write(folder/'run.json',meta)
   print('END',cid,name,status,last.generation_tokens,flush=True);return data
  except Exception as exc:
   if not (folder/'run.json').exists():write(folder/'run.json',{'run_status':'TIMEOUT' if isinstance(exc,TimeoutError) else 'FORMAT_ERROR','answer_status':None,'error':str(exc),'elapsed_seconds':time.perf_counter()-start})
   raise
 try:
  groups=chunks(source,config['chunk_max_chars']);routes=[]
  write(out/'chunk-manifest.json',{'groups':[[s['id'] for s in g] for g in groups],'all_source_hash':digest(source),'all_segments_covered_once':True})
  prior=Path('outputs/local-qwen-pattern-eval-v4/development')/cid
  if (prior/'complete.json').exists():
   for i,g in enumerate(groups):
    f=prior/('route-%03d'%i);state=read(f/'run.json');assert state['run_status']=='OK' and state['prompt_hash']==digest(route_prompt(source,g).encode())
    routes.append(read(f/'data.json'))
   write(out/'reused-routing.json',{'origin':str(prior),'jobs_reused':len(groups),'reason':'Identical full source, chunks, prompt and schema; no duplicate model request'})
  else:
   for i,g in enumerate(groups):routes.append(job('route-%03d'%i,route_prompt(source,g),route_schema(g),config['route_max_tokens']))
  selected,selection=routed_source(source,routes,config['neighbor_context']);write(out/'routing.json',selection);write(out/'selected-source.json',selected)
  registry_data=job('objects',object_prompt(selected,read(ROOT/'tasks.json')['tasks'],read(ROOT/'tasks.json')['scope']),object_schema(selected),config['object_max_tokens'])
  registry_objects=objects(registry_data,selected)
  rows=[]
  for task in read(ROOT/'tasks.json')['tasks']:
   if not selected['segments']:rows.append({'task_id':task['task_id'],'answer_status':'NOT_FOUND','run_status':'OK','reason':'No relevant span selected after full-source routing; not a real-world negative'});continue
   compact=job('extract-'+task['task_id'],fact_prompt(selected,registry_objects,task,read(ROOT/'tasks.json')['scope']),fact_schema(selected,registry_objects,task),config['extract_max_tokens'])
   data,ops=convert(compact,registry_objects,selected,source,task);view=import_declared(data,source)
   registry=import_edges(view,source,data,{'parent_pairs':[{'left':e['left'],'right':e['right']} for e in data['edges'] if e['op']=='part_of'],'group_ids':[o['id'] for o in view['objects'] if o['kind']=='GROUP']})
   folder=out/('extract-'+task['task_id']);write(folder/'annotation.json',data);write(folder/'view.json',view);write(folder/'relations.json',registry);write(folder/'conversion.json',ops)
   ans=execute_declared(view,registry,task['query']);co=copy.deepcopy(task['query']);co['constraints']=[c for c in co['constraints'] if c['op'] not in ['part_of','member_of']]
   rows.append({'task_id':task['task_id'],'run_status':'OK','answer_status':ans['status'],'trace':ans,'cooccurrence':execute_declared(view,registry,co)})
  write(out/'answers.json',{'case_id':cid,'answers':rows});write(out/'complete.json',{'case_id':cid,'run_status':'OK','answers':[r['answer_status'] for r in rows],'jobs':len(groups)+len(rows)+1})
  print('CASE_DONE',cid,[r['answer_status'] for r in rows],flush=True)
 except Exception as exc:
  write(out/'failure.json',{'case_id':cid,'run_status':'PIPELINE_STOPPED_AT_FAILED_JOB','answer_status':None,'error':str(exc),'traceback':traceback.format_exc()});raise

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','run']);p.add_argument('--case');a=p.parse_args();prepare() if a.command=='prepare' else run(a.case)
