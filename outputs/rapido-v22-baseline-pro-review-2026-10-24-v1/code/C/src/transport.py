"""Versioned Unicode configuration repair in the same local MLX transport; no network."""
import os
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
import json,time,signal,hashlib,importlib.metadata,resource,socket,copy
from pathlib import Path
from legacy_adapter import digest,loads
from state import write
from communication import compact_schema,expand_schema
import base_schemas as S
ROOT=Path(__file__).resolve().parent

# Adapter-local correction to LMFE0.11.2: it pushes a first-item parser even
# when maxItems=0. Enforce that exact declared bound before sampling; never
# remove items from a completed model response or relax the consumer schema.
from legal_bench.mlx_json_constraint_v20_1 import ViableUniqueEnumParser,SchemaMask as FrozenSchemaMask
from legal_bench.mlx_json_constraint_v2 import CompositeQuoteEnforcer
from lmformatenforcer import JsonSchemaParser
from lmformatenforcer.characterlevelparser import CharacterLevelParserConfig,ForceStopParser
class DeclaredEmptyArrayParser(ViableUniqueEnumParser):
 def in_declared_empty_array(self):
  return self.string is None and bool(self.stack)and self.stack[-1]['kind']=='['and self.spec(self.stack[-1]['path']).get('maxItems')==0
 def get_allowed_characters(self):
  chars=super().get_allowed_characters()
  return ''.join(c for c in chars if c in '] \t\r\n')if self.in_declared_empty_array()else chars
 def shortcut_key(self):
  return None if self.in_declared_empty_array()else super().shortcut_key()
class StrictCompositeQuoteEnforcer(CompositeQuoteEnforcer):
 def __init__(self,data,parser,schema):
  self.schema=schema
  super().__init__(data,parser)
 def require_complete_contract(self,token_sequence):
  text=self.decoder(list(token_sequence))
  eos=self.eos_token_id if isinstance(self.eos_token_id,list)else[self.eos_token_id]
  if token_sequence and token_sequence[-1]in eos:
   suffix=self.decoder([token_sequence[-1]])
   if suffix and text.endswith(suffix):text=text[:-len(suffix)]
  try:
   value=json.loads(text)
   S.validate_stage(value,self.schema)
  except Exception as exc:
   raise RuntimeError('INTERNAL_CONSTRAINT_STOP_WITHOUT_VALID_COMPLETE_JSON')from exc
 def get_allowed_tokens(self,token_sequence):
  allowed=super().get_allowed_tokens(token_sequence)
  state=self.prefix_states[tuple(token_sequence)]
  eos=self.eos_token_id if isinstance(self.eos_token_id,list)else[self.eos_token_id]
  if any(t in allowed.allowed_tokens for t in eos)and not state.parser.can_end():
   self.require_complete_contract(token_sequence)
  return allowed
 def _apply_new_characters(self,state,token_sequence):
  new=super()._apply_new_characters(state,token_sequence)
  if isinstance(new.parser,ForceStopParser):
   # Some upstream parser transitions terminate after the contract is already
   # complete. Accept only an actual, unmodified, schema-valid token prefix;
   # never add delimiters or reinterpret an incomplete string as completion.
   self.require_complete_contract(token_sequence)
  return new
class ScopeSchemaMask(FrozenSchemaMask):
 def __init__(self,data,schema):
  # The wrapper configuration setter does not update the delegate or its
  # cached alphabet. Construct both with the same tokenizer alphabet first.
  # This admits schema-legal Unicode, never a repaired model judgment.
  config=CharacterLevelParserConfig(alphabet=data.tokenizer_alphabet)
  delegate=JsonSchemaParser(schema,config=config)
  parser=DeclaredEmptyArrayParser(schema,delegate=delegate,config=config)
  self.enforcer=StrictCompositeQuoteEnforcer(data,parser,schema);self.calls=0;self.prefix_length=None;self.history=[]
class ResourceStop(RuntimeError):pass

def no_network(*args,**kwargs):raise RuntimeError('LOCAL_ATTEMPT_NETWORK_DISABLED')
socket.socket.connect=no_network

class Client:
 def __init__(self):
  self.cfg=json.loads((ROOT/'protocol.json').read_text());self.spent=0;self.started=time.monotonic();self.counts={};self.reuse={};self.arm_started={};self.usage={}
  if not self.cfg.get('local_execution_enabled')or self.cfg.get('endpoint')is not None:raise RuntimeError('LOCAL_ONLY_CONFIGURATION_REQUIRED')
  from mlx_vlm import load
  import mlx.core as mx
  from legal_bench.mlx_json_constraint import tokenizer_data
  self.mx=mx;mx.set_memory_limit(14*1024**3);mx.set_cache_limit(512*1024**2)
  path=Path(self.cfg['local_model_path'])
  if path.name!=self.cfg['local_revision']:raise RuntimeError('LOCAL_SNAPSHOT_REVISION_MISMATCH')
  self.versions={x:importlib.metadata.version(x)for x in ['mlx','mlx-metal','mlx-vlm','transformers','lm-format-enforcer']}
  if self.versions['mlx-vlm']!='0.7.4'or self.versions['lm-format-enforcer']!='0.11.2':raise RuntimeError('PINNED_RUNTIME_MISMATCH')
  print('LOADING_LOCAL_SNAPSHOT',path.name,flush=True)
  self.model,self.processor=load(str(path));self.tok=getattr(self.processor,'tokenizer',self.processor)
  self.data=tokenizer_data(self.tok,getattr(self.tok,'eos_token_ids',self.tok.eos_token_id))
  self.loaded_seconds=time.monotonic()-self.started
  write(ROOT/'private/runtime'/('instance-'+str(os.getpid())+'-'+str(time.time_ns())+'.json'),{'model':self.cfg['local_model'],'snapshot':path.name,'versions':self.versions,'load_seconds':self.loaded_seconds,'memory_limit_gib':14,'cache_limit_mib':512,'network_disabled':True,'constraint_adapter':'V10_2_SHARED_UNICODE_SCHEMA_VALID_COMPLETION','quantization':'4bit affine group64','not_same_as_together_weights':True})
 def remaining(self,cid,arm):
  key=(cid,arm);started=self.arm_started.setdefault(key,time.monotonic());usage=self.usage.get(key,{'prompt_tokens':0,'completion_tokens':0})
  return 1 if time.monotonic()-started<self.cfg['local_total_seconds']and self.counts.get(key,0)<self.cfg['max_calls_per_arm']and usage['prompt_tokens']<self.cfg['max_input_tokens_per_arm']and usage['completion_tokens']+self.cfg['parameters']['max_tokens']<=self.cfg['max_output_tokens_per_arm']else 0
 def seconds_remaining(self,cid,arm):
  started=self.arm_started.setdefault((cid,arm),time.monotonic())
  return max(0,self.cfg['local_total_seconds']-(time.monotonic()-started))
 def call(self,cid,arm,tag,text,schema):
  if not self.remaining(cid,arm):raise ResourceStop('LOCAL_WALLTIME_OR_CALL_LIMIT')
  from mlx_vlm.generate import stream_generate
  from mlx_vlm.prompt_utils import apply_chat_template
  SchemaMask=ScopeSchemaMask
  mx=self.mx;display=compact_schema(schema)
  if expand_schema(display)!=schema:raise RuntimeError('PROMPT_SCHEMA_ROUNDTRIP_MISMATCH')
  schema_text=json.dumps(display,separators=(',',':'))
  prompt=text+'\nOUTPUT CONTRACT: Return one complete single-line compact JSON object following this schema. No indentation, markdown, padding or repeated explanations.\n'+schema_text
  rendered=apply_chat_template(self.processor,self.model.config,prompt,enable_thinking=False,num_images=0,num_audios=0)
  prompt_tokens=len(self.tok.encode(rendered,add_special_tokens=False));limit=self.cfg['parameters']['max_tokens']
  identity=json.loads((ROOT/'private/runs'/cid/arm/'identity.json').read_text())
  request={'model':self.cfg['local_model'],'snapshot':self.cfg['local_revision'],'prompt':prompt,'schema':schema,'parameters':self.cfg['parameters'],'provider':'LOCAL_MLX'}
  key=digest({'request':request,'run_id':identity['run_id']});dest=ROOT/'private/runs'/cid/arm/'calls'/key
  if (dest/'receipt.json').exists():
   rc=json.loads((dest/'receipt.json').read_text())
   if rc['status']!='OK':raise RuntimeError('PRESERVED_LOCAL_FAILURE:'+rc['status'])
   return loads((dest/'response.txt').read_text()),{**rc,'same_run_cache_reused':True,
      'original_receipt':str(dest/'receipt.json'),'elapsed_seconds':0,
      'usage':{'prompt_tokens':0,'completion_tokens':0},'resource_charge':{'prompt_tokens':0,'completion_tokens':0},
      'not_new_model_call':True}
  if (dest/'start.json').exists():raise RuntimeError('LOCAL_INCOMPLETE_ATTEMPT_NO_RESEND')
  cache=self.cfg.get('exact_raw_cache',{})
  if tag in cache.get('allowed_tags',[]):
   parent=Path(cache['root']);protected=json.loads((ROOT/cache['protection_map']).read_text())['files'];matches=[]
   for old_start in (parent/'private/runs'/cid/arm/'calls').glob('*/start.json'):
    if json.loads(old_start.read_text()).get('tag')!=tag:continue
    old=old_start.parent
    if not(old/'receipt.json').exists():continue
    old_receipt=json.loads((old/'receipt.json').read_text())
    if old_receipt.get('status')!='OK':continue
    if digest(json.loads((old/'request.json').read_text()))!=digest(request):continue
    for name in ('request.json','response.txt','receipt.json','rendered-prompt.txt'):
     rel=str((old/name).relative_to(parent))
     if hashlib.sha256((old/name).read_bytes()).hexdigest()!=protected.get(rel):raise RuntimeError('EXACT_CACHE_PROTECTED_BYTES_CHANGED:'+rel)
    matches.append((old,old_receipt))
   if len(matches)>1:raise RuntimeError('AMBIGUOUS_EXACT_REQUEST_CACHE')
   if not matches and cache.get('required'):raise RuntimeError('REQUIRED_EXACT_RAW_CACHE_MISS:'+tag)
   if matches:
    old,original=matches[0];raw=(old/'response.txt').read_text();parsed=loads(raw);S.validate_stage(parsed,schema)
    write(dest/'request.json',request);(dest/'response.txt').write_bytes((old/'response.txt').read_bytes());(dest/'rendered-prompt.txt').write_bytes((old/'rendered-prompt.txt').read_bytes());write(dest/'parsed.json',parsed)
    self.counts[(cid,arm)]=self.counts.get((cid,arm),0)+1
    charge={'prompt_tokens':original['usage']['prompt_tokens'],'completion_tokens':original['usage']['completion_tokens'],'elapsed_seconds':original['elapsed_seconds']}
    charged=self.usage.setdefault((cid,arm),{'prompt_tokens':0,'completion_tokens':0})
    for name in ('prompt_tokens','completion_tokens'):charged[name]+=charge[name]
    self.arm_started[(cid,arm)]-=charge['elapsed_seconds']
    rc={**copy.deepcopy(original),'run_id':identity['run_id'],'request_hash':key,'elapsed_seconds':0,'cache_reused':True,'cache_origin':str(old),'original_receipt':original,'usage':{'prompt_tokens':0,'completion_tokens':0},'resource_charge':charge,'status':'OK','cache_policy':'EXACT_REQUEST_MODEL_PARAMETERS_SCHEMA_PROMPT_AND_PROTECTED_RAW_BYTES_CHARGED_ORIGINAL_RESOURCES'}
    write(dest/'start.json',{'tag':tag,'run_id':identity['run_id'],'prompt_tokens':prompt_tokens,'max_output_tokens':limit,'cache_reused':True,'api_dispatch':False,'started_epoch':time.time()});write(dest/'receipt.json',rc)
    print('EXACT_RAW_CACHE',tag,'source',old.name,flush=True);return parsed,rc
  if prompt_tokens+limit+256>self.cfg['context_length']:raise ResourceStop('LOCAL_FULL_INPUT_CONTEXT_LIMIT')
  usage=self.usage.setdefault((cid,arm),{'prompt_tokens':0,'completion_tokens':0})
  if usage['prompt_tokens']+prompt_tokens>self.cfg['max_input_tokens_per_arm']:raise ResourceStop('LOCAL_INPUT_TOKEN_BUDGET')
  if '<think>\n\n</think>'not in rendered[-180:]:raise RuntimeError('THINKING_DISABLE_TEMPLATE_UNVERIFIED')
  write(dest/'request.json',request);write(dest/'start.json',{'tag':tag,'run_id':identity['run_id'],'prompt_tokens':prompt_tokens,'max_output_tokens':limit,'api_dispatch':False,'started_epoch':time.time()})
  (dest/'rendered-prompt.txt').write_text(rendered)
  self.counts[(cid,arm)]=self.counts.get((cid,arm),0)+1
  rc={'case_id':cid,'arm':arm,'tag':tag,'request_hash':key,'run_id':identity['run_id'],'model':self.cfg['local_model'],'snapshot':self.cfg['local_revision'],'api_dispatch':False,'accounted_usd':0,'known_cost_usd':0,'source_input_truncated':False,'prompt_tokens':prompt_tokens,'max_output_tokens':limit,'versions':self.versions}
  start=time.monotonic();raw='';last=None;mask=None;tokens=[]
  def timeout(*a):raise TimeoutError('LOCAL_FROZEN_WALLTIME_LIMIT')
  old_handler=signal.signal(signal.SIGALRM,timeout)
  call_seconds=min(self.cfg['local_per_call_seconds'],self.seconds_remaining(cid,arm));rc['walltime_limit_kind']='CASE_ARM_BUDGET'if call_seconds<self.cfg['local_per_call_seconds']else 'PER_CALL_LIMIT'
  signal.setitimer(signal.ITIMER_REAL,max(.001,call_seconds))
  print('START',cid,tag,'input',prompt_tokens,'max_output',limit,flush=True)
  try:
   mx.random.seed(self.cfg['parameters']['seed']);mx.clear_cache();mx.reset_peak_memory()
   mask=SchemaMask(self.data,schema)
   kwargs={k:self.cfg['parameters'][k]for k in ['temperature','top_p','top_k','min_p','repetition_penalty']}
   kwargs.update(max_tokens=limit,enable_thinking=False,prefill_step_size=256,logits_processors=[mask])
   with (dest/'response.txt').open('x')as out:
    for last in stream_generate(self.model,self.processor,rendered,image=None,audio=None,video=None,**kwargs):
     out.write(last.text);out.flush();raw+=last.text
     if last.token_ids is not None:tokens=list(last.token_ids)
     elif last.token is not None:tokens.append(int(last.token))
     if last.generation_tokens%256==0:
      write_progress={'tag':tag,'tokens':last.generation_tokens,'elapsed_seconds':round(time.monotonic()-start,1)}
      write_progress['streamed_characters']=len(raw)
      (dest/'progress.json').write_text(json.dumps(write_progress));(dest/'live-token-prefix.txt').write_text(self.tok.decode(tokens,skip_special_tokens=False));print('PROGRESS',json.dumps(write_progress),flush=True)
   if last is None:raise ValueError('EMPTY_LOCAL_GENERATION')
   rc['finish_reason']=last.finish_reason
   if last.finish_reason!='stop':raise RuntimeError('OUTPUT_TRUNCATED')
   if '<think>'in raw or '</think>'in raw:raise RuntimeError('THINKING_OUTPUT_DETECTED')
   parsed=loads(raw);S.validate_stage(parsed,schema);write(dest/'parsed.json',parsed);rc['status']='OK'
  except Exception as exc:
   rc.update(status='OUTPUT_TRUNCATED'if str(exc)=='OUTPUT_TRUNCATED'else 'TIMEOUT'if isinstance(exc,TimeoutError)else 'LOCAL_FAILURE',error=type(exc).__name__+':'+str(exc))
  finally:
   signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old_handler)
   rc.update(elapsed_seconds=time.monotonic()-start,usage={'prompt_tokens':prompt_tokens,'completion_tokens':getattr(last,'generation_tokens',len(tokens))},peak_mlx_memory_gb=mx.get_peak_memory()/1e9,peak_rss_gb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e9,mask_calls=getattr(mask,'calls',0),format_repair=False)
   write(dest/'receipt.json',rc);write(dest/'token-ids.json',tokens)
   usage['prompt_tokens']+=prompt_tokens;usage['completion_tokens']+=rc['usage']['completion_tokens']
   (dest/'token-decoded-audit.txt').write_text(self.tok.decode(tokens,skip_special_tokens=False))
   if hasattr(mask,'failed_generated_ids'):write(dest/'constraint-failure.json',{'generated_ids':mask.failed_generated_ids,'history_tail':mask.history[-10:]})
   mx.clear_cache()
  print('END',tag,rc['status'],round(rc['elapsed_seconds'],1),flush=True)
  if rc['status']=='TIMEOUT'and rc['walltime_limit_kind']=='CASE_ARM_BUDGET':raise ResourceStop('LOCAL_CASE_ARM_WALLTIME_BUDGET_EXHAUSTED')
  if rc['status']!='OK':raise RuntimeError('LOCAL:'+rc['status']+':'+rc.get('error',''))
  return parsed,rc
