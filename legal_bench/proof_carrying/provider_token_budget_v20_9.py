"""Existing Together transport, bounded cost, no retries or client source cuts.

The service FP8 deployment differs from the local 4-bit snapshot. Server schema
enforcement plus local completed-schema/reference checks replace the local mask.
Credentials are read by the existing private helper and never saved or printed.
"""
import json
import signal
import time
import urllib.error
import urllib.request
from pathlib import Path
from scripts.proof_together_diagnostic import credential, request_body, stream_event
from .artifact_state_v20_2 import immutable, digest, byte_hash
from .schema_contract_v19_6 import loads, validate
from .repetition_v20_6 import StringGuard, RepetitionAbort, duplicates

MODEL = 'Qwen/Qwen3.5-9B'
ENDPOINT = 'https://api.together.xyz/v1/chat/completions'


class Runner:
    def __init__(self, ignored_local_path=None, *, out, maximum_cost_usd=0.50):
        self.out=Path(out)
        self.maximum_cost_usd=maximum_cost_usd
        self.key=credential()
        path=self.out/'provider-model.json'
        if path.exists():
            model=json.loads(path.read_text())['model']
        else:
            request=urllib.request.Request('https://api.together.xyz/v1/models',headers={
                'Authorization':'Bearer '+self.key,'User-Agent':'legal-ai-source-repair/1.0'})
            with urllib.request.urlopen(request,timeout=30) as response:
                rows=json.load(response)
            model=next(row for row in rows if row['id']==MODEL)
            immutable(path,{'model':model,'queried_at_epoch':time.time(),
                'source':'Authenticated official model-list API','exact_weight_revision':'UNAVAILABLE',
                'different_from_local_4bit_snapshot':True})
        self.pricing=model['pricing']
        self.usage=[]
        for path in self.out.glob('**/run.json'):
            value=json.loads(path.read_text())
            if value.get('runtime') in ('TOGETHER_V20_6_1','TOGETHER_V20_9_TOKEN_BUDGET'):self.usage.append(value)

    def used(self):
        return sum(row.get('listed_price_token_cost_usd',row.get('reserved_cost_upper_bound_usd',0))
                   for row in self.usage)

    def run(self,prompt,schema,out,max_tokens,remaining_seconds=1800,constraint_mode='FIXED'):
        out=Path(out)
        body=request_body(prompt,schema)
        body['max_tokens']=max_tokens
        body['response_format']['json_schema']['name']='v20_6_1_source_repair'
        identity={'prompt_sha256':digest(prompt),'schema_sha256':digest(schema),
            'request_sha256':digest(body),'model':MODEL,'endpoint':ENDPOINT}
        if (out/'run.json').exists():
            previous=json.loads((out/'run.json').read_text())
            if previous['identity']!=identity:raise ValueError('INCOMPATIBLE_API_REUSE')
            return previous
        if (out/'start.json').exists():raise ValueError('UNCERTAIN_SUBMISSION_NO_RETRY')
        # UTF-8 bytes bound token count conservatively; include the whole schema
        # and generous server wrapper overhead, rather than assuming a template.
        byte_upper=len(prompt.encode())+len(json.dumps(schema).encode())+4096
        input_upper=byte_upper
        token_preflight={'policy':'UTF8_BYTE_FALLBACK','byte_upper_bound':byte_upper}
        try:
            from transformers import AutoTokenizer
            root=Path(__file__).resolve().parents[2]
            model_path=(root/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip()
            tok=AutoTokenizer.from_pretrained(model_path,local_files_only=True)
            data=tok.apply_chat_template(body['messages'],tokenize=True,add_generation_prompt=True,enable_thinking=False)
            ids=data['input_ids'] if hasattr(data,'keys') else data
            if ids and isinstance(ids[0],list):
                if len(ids)!=1:raise ValueError('TOKEN_BUDGET_BATCH_SHAPE')
                ids=ids[0]
            if not ids or not all(type(i) is int for i in ids):raise ValueError('TOKEN_BUDGET_IDS_SHAPE')
            schema_tokens=len(tok.encode(json.dumps(body['response_format']),add_special_tokens=False))
            token_upper=(3*(len(ids)+schema_tokens)+1)//2+4096
            input_upper=min(byte_upper,token_upper)
            token_preflight={'policy':'PINNED_TOKENIZER_1_5X_PLUS_4096','client_prompt_tokens':len(ids),'schema_tokens':schema_tokens,'input_token_upper_bound':input_upper,'byte_upper_bound':byte_upper,'tokenizer_path':model_path,'service_tokenizer_revision':'UNAVAILABLE','calibration':'engineering/token-budget-calibration-v2.json'}
        except Exception as exc:
            token_preflight['fallback_reason']=type(exc).__name__
        reserved=(input_upper*self.pricing['input']+max_tokens*self.pricing['output'])/1000000
        meta={'runtime':'TOGETHER_V20_9_TOKEN_BUDGET','identity':identity,'requested_model':MODEL,
            'run_status':None,'source_input_truncated':False,'reserved_output_tokens':max_tokens,
            'reserved_cost_upper_bound_usd':reserved,'pricing_usd_per_million':self.pricing,
            'maximum_total_cost_usd':self.maximum_cost_usd,'token_budget_preflight':token_preflight,'local_mask_enforcement':False,
            'server_schema_requested':True,'exact_model_revision':'UNAVAILABLE',
            'service_quantization':'FP8','local_comparison_quantization':'4bit',
            'done_received':False,'actual_parameters':{k:v for k,v in body.items()
                if k not in ('messages','response_format')}}
        out.mkdir(parents=True,exist_ok=True)
        if self.used()+reserved>self.maximum_cost_usd:
            meta.update(run_status='COST_CAP_NOT_DISPATCHED',submitted=False)
            immutable(out/'run.json',meta);return meta
        immutable(out/'request.json',body)
        immutable(out/'schema.json',schema)
        (out/'prompt.txt').write_text(prompt)
        immutable(out/'start.json',{'identity':identity,'started_at_epoch':time.time(),'dispatch_count':1})
        req=urllib.request.Request(ENDPOINT,data=json.dumps(body).encode(),headers={
            'Authorization':'Bearer '+self.key,'Content-Type':'application/json',
            'Accept':'text/event-stream','User-Agent':'legal-ai-source-repair/1.0'},method='POST')
        guard=StringGuard();start=time.monotonic()
        def timeout(signum,frame):raise TimeoutError('BOUNDED_API_CALL_TIME_USED')
        previous_handler=signal.signal(signal.SIGALRM,timeout)
        signal.setitimer(signal.ITIMER_REAL,max(0.001,remaining_seconds))
        print('API_START',out.parent.name,out.name,flush=True)
        class CheckedContent:
            def __init__(self,handle):self.handle=handle
            def write(self,value):
                self.handle.write(value);self.handle.flush();guard.feed(value)
            def flush(self):self.handle.flush()
        try:
            with urllib.request.urlopen(req,timeout=300) as response:
                meta['http_status']=response.status
                with (out/'raw-sse.txt').open('x') as events, (out/'raw-response.txt').open('x') as content, (out/'reasoning.txt').open('x') as reasoning:
                    checked=CheckedContent(content);lines=[]
                    for binary in response:
                        line=binary.decode();events.write(line);events.flush()
                        if line.strip():
                            if line.startswith('data:'):lines.append(line[5:].lstrip().rstrip('\r\n'))
                        elif lines:
                            stream_event('\n'.join(lines),checked,reasoning,meta);lines=[]
                    if lines:stream_event('\n'.join(lines),checked,reasoning,meta)
            raw=(out/'raw-response.txt').read_text()
            if meta.get('model')!=MODEL:meta['run_status']='RETURNED_MODEL_MISMATCH'
            elif meta.get('finish_reason')=='length':meta['run_status']='OUTPUT_TRUNCATED'
            elif not meta['done_received']:meta['run_status']='STREAM_INCOMPLETE'
            elif (out/'reasoning.txt').stat().st_size:meta['run_status']='THINKING_CONFIGURATION_MISMATCH'
            else:
                value=loads(raw);validate(value,schema)
                if duplicates(value):raise RepetitionAbort('Completed explanatory-array duplicate')
                immutable(out/'parsed.json',value);meta['run_status']='OK'
        except urllib.error.HTTPError as exc:
            meta.update(run_status='HTTP_FAILURE',http_status=exc.code)
            (out/'http-error.txt').write_text(exc.read().decode(errors='replace').replace(self.key,'[REDACTED]'))
        except KeyboardInterrupt:
            meta.update(run_status='INTERRUPTED',interruption_actor='CALLER')
        except Exception as exc:
            meta.update(run_status='REPETITION_ABORT' if isinstance(exc,RepetitionAbort) else
                'TIMEOUT' if isinstance(exc,TimeoutError) else 'FORMAT_OR_TRANSPORT_FAILURE',
                error_type=type(exc).__name__,error=str(exc).replace(self.key,'[REDACTED]'))
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous_handler)
        usage=meta.get('usage') or {}
        if 'prompt_tokens' in usage and 'completion_tokens' in usage:
            meta['listed_price_token_cost_usd']=(usage['prompt_tokens']*self.pricing['input']
                +usage['completion_tokens']*self.pricing['output'])/1000000
        meta.update(elapsed_seconds=time.monotonic()-start,output_tokens=usage.get('completion_tokens'),
            prompt_tokens=usage.get('prompt_tokens'),repetition_guard=guard.hit,
            raw_sha256=byte_hash(out/'raw-response.txt') if (out/'raw-response.txt').exists() else None)
        immutable(out/'run.json',meta);self.usage.append(meta)
        print('API_END',out.parent.name,out.name,meta['run_status'],round(meta['elapsed_seconds'],1),
            'cost',meta.get('listed_price_token_cost_usd'),flush=True)
        return meta
