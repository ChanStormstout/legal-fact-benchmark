"""Actual local Qwen transport and exact-request replay. No paid endpoint."""
import importlib.util
import json
import sys
import time
from pathlib import Path
from common import REPO, ROOT, digest, read, save
from runner import ResourceStop

class LocalProvider:
    kind='LOCAL_QWEN_NEW_MODEL_EXECUTION'
    def __init__(self,cfg,work):
        parent=REPO/'outputs/rapido-side-scope-acceptance-local-v1'
        # Reuse the fixed tokenizer/constraint transport without executing its old run.py.
        # ROOT is rebound before constructing Client; no writes reach the frozen parent.
        sys.path.insert(0,str(parent))
        spec=importlib.util.spec_from_file_location('rapido_proof_task_transport',ROOT/'src/transport.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.module=module;self.work=Path(work);self.cfg=cfg
        module.ROOT=self.work
        transport={**cfg,'local_execution_enabled':True,'endpoint':None,'exact_raw_cache':{}}
        save(self.work/'protocol.json',transport)
        self.client=module.Client();self.receipts=[];self.charges=[]
    def call(self,cid,arm,tag,request,attempt=0):
        identity={'run_id':digest({'snapshot':request['snapshot_id'],'arm':arm,'config':self.cfg}),'provider':'LOCAL_ONLY'}
        save(self.work/'private/runs'/cid/arm/'identity.json',identity)
        body=request['policy']+'\n'+request['task']+'\n'+json.dumps(request['material'],ensure_ascii=False,separators=(',',':'))
        if attempt:body+='\nTransport retry '+str(attempt)+': same task and sources, no semantic correction.'
        # Reserve final generation, checking and the single revision/recheck from early stages.
        if not tag.removeprefix('repair-').startswith(('report','final-review','coverage-final')) and self.client.counts.get((cid,arm),0)>=self.cfg['max_calls_per_arm']-4:
            raise ResourceStop('FINAL_REPORT_CALL_RESERVE')
        folder=self.work/'private/runs'/cid/arm/'calls'
        before=set(folder.glob('*/receipt.json'))
        try:value,receipt=self.client.call(cid,arm,tag,body,request['schema'])
        except Exception as exc:
            receipts=[read(p) for p in set(folder.glob('*/receipt.json'))-before]
            self.receipts.extend(receipts)
            error=ResourceStop(str(exc)) if isinstance(exc,self.module.ResourceStop) else RuntimeError(str(exc))
            error.receipts=receipts
            raise error from exc
        self.receipts.append(receipt)
        return value,{**receipt,'pipeline_request_hash':digest(request),'actual_provider':'LOCAL_MLX','attempt':attempt}
    def charge_shared(self,cid,arm,receipts):
        """Shared actual B/C judgments are charged once to EACH method, not free."""
        key=(cid,arm);usage=self.client.usage.setdefault(key,{'prompt_tokens':0,'completion_tokens':0})
        seconds=0
        for rc in receipts:
            charge=rc.get('resource_charge',rc.get('usage',{}))
            for field in usage:usage[field]+=charge.get(field,0)
            seconds+=rc.get('elapsed_seconds',0)
        self.client.counts[key]=self.client.counts.get(key,0)+sum(not r.get('not_new_model_call',False) for r in receipts)
        self.client.arm_started[key]=time.monotonic()-seconds
        self.charges.append({'case_id':cid,'arm':arm,'shared_receipt_hashes':[digest(r) for r in receipts],
            'resource_charge':dict(usage),'elapsed_monotonic_seconds':seconds,'not_new_model_calls':True})

class ExactReplayProvider:
    kind='EXACT_REQUEST_CACHE_REPLAY_NOT_NEW_MODEL_EFFECT'
    def __init__(self,cache_root):
        self.cache={}
        for path in Path(cache_root).rglob('responses/*.json'):
            row=read(path);key=row['request_hash']
            if row['receipt'].get('synthetic') or row['receipt'].get('actual_provider')!='LOCAL_MLX':continue
            if key in self.cache and self.cache[key]['raw_model_value']!=row['raw_model_value']:raise ValueError('AMBIGUOUS_REPLAY')
            self.cache[key]=row
    def call(self,cid,arm,tag,request,attempt=0):
        key=digest(request)
        if key not in self.cache:raise ResourceStop('EXACT_REQUEST_CACHE_MISS_NO_MODEL_FALLBACK')
        row=self.cache[key]
        return row['raw_model_value'],{**row['receipt'],'exact_request_replayed':True,'paid_api_dispatch':False}
