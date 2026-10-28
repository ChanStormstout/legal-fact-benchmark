"""Count every actual Together call; preserve unknown costs; no implicit retry."""
import os,json,time,signal,urllib.request,urllib.error
from pathlib import Path
from common import ROOT,read,save,write,utc,digest
from stream_guard import ProgressWriter
from sse import consume_sse,reported_usage

class CallFailed(RuntimeError):
    def __init__(self,message,fatal=False): super().__init__(message);self.fatal=fatal

def credential():
    value=os.environ.get('TOGETHER_API_KEY')
    if value:return value
    p=Path.home()/'.config/legal-ai/together-api-key'
    if p.stat().st_mode&0o077:raise RuntimeError('CREDENTIAL_PERMISSIONS')
    return p.read_text().strip()

def service_metadata():
    key=credential();req=urllib.request.Request('https://api.together.ai/v1/models',headers={'Authorization':'Bearer '+key,'User-Agent':'legal-ai-research/1.0'})
    with urllib.request.urlopen(req,timeout=30) as response:d=json.load(response)
    rows=d if isinstance(d,list) else d.get('data',[])
    row=next(x for x in rows if x.get('id')=='Qwen/Qwen3.8-Flash')
    price=row.get('pricing',{})
    if price and (float(price.get('input',0))>.15 or float(price.get('output',0))>.47):raise RuntimeError('PRICE_CHANGED_REFREEZE_BEFORE_INFERENCE')
    return {'at':utc(),'model':row,'immutable_weight_revision_verified':False,'inference_call':False}

class Client:
    def __init__(self,cfg,dest):self.cfg=cfg;self.dest=Path(dest);self.halt=False
    def ledger(self):
        rows=[]
        for p in sorted((self.dest/'calls').glob('*/start.json')):
            rows.append(read(p.with_name('receipt.json')) if p.with_name('receipt.json').exists() else {'status':'INTERRUPTED_NO_RECEIPT','cost_usd':read(p)['reserved_usd']})
        return {'new_calls':len(rows),'new_conservative_usd':sum(x['cost_usd'] for x in rows),'calls':rows}
    def wire(self,system,material,cap):
        if system is None:
            import copy
            original=copy.deepcopy(material)
            original['model']=self.cfg['parameters']['model']
            return original
        return {**self.cfg['parameters'],'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps(material,ensure_ascii=False,separators=(',',':'))}],'max_tokens':cap}
    def preflight(self,system,material,cap):
        wire=self.wire(system,material,cap);body=json.dumps(wire,ensure_ascii=False,separators=(',',':')).encode()
        # Byte-tokenizer strings have at most one token per UTF-8 byte; extra 4096
        # bounds template/schema wrapper overhead. No original text is shortened.
        upper=len(body)+4096
        price=self.cfg['pricing']
        return wire,body,{'serialized_bytes':len(body),'input_token_upper':upper,'output_cap':cap,'fits':upper+cap<=self.cfg['context_length'],'reserved_usd':(upper*price['input_per_million_usd']+cap*price['output_per_million_usd'])/1e6}
    def call(self,tag,system,material,cap):
        if self.halt:raise CallFailed('SERVICE_HALTED',True)
        wire,body,pre=self.preflight(system,material,cap);ledger=self.ledger()
        if not pre['fits']:raise CallFailed('INPUT_TOO_LARGE_NO_TRUNCATION')
        if ledger['new_calls']>=self.cfg['max_calls'] or ledger['new_conservative_usd']+pre['reserved_usd']>self.cfg['max_new_usd']:raise CallFailed('FROZEN_RESOURCE_CAP')
        path=self.dest/'calls'/f'{len(ledger["calls"])+1:02d}-{tag}';path.mkdir(parents=True,exist_ok=False)
        save(path/'request.json',wire);save(path/'start.json',{'at':utc(),'tag':tag,'request_sha256':digest(wire),**pre})
        rc={'at':utc(),'tag':tag,'status':'INFLIGHT','cost_usd':pre['reserved_usd'],'source_truncated':False,'done_received':False,'weight_revision_verified':False,'request_hash':digest(wire)};key=credential();started=time.monotonic();guard=None
        def timeout(*args):raise TimeoutError('FROZEN_CALL_TIME_CAP')
        previous=signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,self.cfg['per_call_seconds'])
        print('START_API',tag,'reserved',pre['reserved_usd'],flush=True)
        try:
            req=urllib.request.Request(self.cfg['endpoint'],data=body,headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','Accept':'text/event-stream','User-Agent':'legal-ai-research/1.0'},method='POST')
            with urllib.request.urlopen(req,timeout=self.cfg['socket_idle_seconds']) as response:
                rc.update(http_status=response.status,request_id=response.headers.get('x-request-id'),service_date=response.headers.get('date'))
                with (path/'raw-sse.txt').open('xb') as raw,(path/'response.txt').open('x') as out,(path/'reasoning.txt').open('x') as reasoning:
                    guard=ProgressWriter(out,1024,1024,6,16384)
                    consume_sse(response,raw,guard,reasoning,rc)
            if not rc.get('done_received') or rc.get('finish_reason')!='stop':raise CallFailed('INCOMPLETE_STREAM')
            if (path/'reasoning.txt').stat().st_size or rc.get('model')!=self.cfg['parameters']['model']:raise CallFailed('MODEL_CONFIGURATION_MISMATCH',True)
            if system is None:
                value={'text':(path/'response.txt').read_text()}
                if not value['text'].strip():raise CallFailed('EMPTY_REPORT')
            else:
                value=json.loads((path/'response.txt').read_text())
                if not isinstance(value,dict):raise CallFailed('RESULT_NOT_OBJECT')
            save(path/'parsed.json',value);rc['status']='OK';return value
        except urllib.error.HTTPError as e:
            write(path/'http-error.txt',e.read().decode(errors='replace').replace(key,'[REDACTED]'))
            rc.update(status='HTTP_FAILURE',http_status=e.code,error=str(e));self.halt=e.code in (400,401,402,403,404,422,429)
            raise CallFailed('HTTP_'+str(e.code),self.halt) from e
        except Exception as e:
            rc.update(status=type(e).__name__,error=str(e).replace(key,'[REDACTED]'));self.halt=getattr(e,'fatal',False)
            raise CallFailed(rc['status']+':'+rc['error'],self.halt) from e
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)
            u=reported_usage(rc);rc['cost_basis']='SERVER_USAGE' if u is not None else 'UNKNOWN_USAGE_FULL_RESERVATION'
            if u is not None:rc['cost_usd']=(u['prompt_tokens']*self.cfg['pricing']['input_per_million_usd']+u['completion_tokens']*self.cfg['pricing']['output_per_million_usd'])/1e6
            rc['elapsed_seconds']=time.monotonic()-started;rc['progress_guard']=guard.diagnostic() if guard else None
            save(path/'receipt.json',rc);print('END_API',tag,rc['status'],rc['cost_usd'],flush=True)
