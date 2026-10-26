"""Counted Together transport. No local model, implicit retries or oracle repair."""
import json,time,urllib.request,urllib.error,signal,hashlib
from pathlib import Path
from common import save,read,digest
from communication import request_wire,canonical_id_sets,ProgressWriter,BlankNoProgress,RepeatedTextNoProgress
from runner import ResourceStop,CallFailure
from contracts import validate,loads
from schema_contract import ContractError
from scripts.proof_together_diagnostic import credential


class StreamProtocolError(ValueError):
    pass


def consume_sse(lines, raw, content, reasoning, receipt):
    """Preserve every received byte and parse SSE frames, without completing JSON.

    DONE closes the stream; it does not certify that the model completed its
    answer. Usage-only frames and comments are legal and never discarded.
    """
    data=[];frame_type=None;events=0;byte_count=0;terminal=False
    started=time.monotonic();first=None;last=None;framing_hash=hashlib.sha256()
    def emit():
        nonlocal events,terminal,first,last
        if not data:return
        payload='\n'.join(data)
        events+=1;now=time.monotonic();first=now if first is None else first;last=now
        if terminal:raise StreamProtocolError('DATA_AFTER_DONE')
        if payload=='[DONE]':
            terminal=True;receipt['done_received']=True;return
        try:event=json.loads(payload)
        except json.JSONDecodeError as exc:raise StreamProtocolError('MALFORMED_SSE_JSON') from exc
        if not isinstance(event,dict):raise StreamProtocolError('NON_OBJECT_SSE_EVENT')
        if event.get('error') or frame_type=='error':
            receipt['provider_error']=event.get('error',event)
            raise StreamProtocolError('PROVIDER_STREAM_ERROR')
        for key in ('id','model'):
            if key in event and receipt.get(key) not in (None,event[key]):
                raise StreamProtocolError('STREAM_'+key.upper()+'_CHANGED')
        for key in ('id','model','created','system_fingerprint'):
            if key in event:receipt[key]=event[key]
        if event.get('usage') is not None:
            receipt['usage']=event['usage'];receipt['usage_event_count']=receipt.get('usage_event_count',0)+1
        if event.get('warnings'):receipt.setdefault('provider_warnings',[]).extend(event['warnings'])
        for choice in event.get('choices',[]):
            if choice.get('index',0)!=0:raise StreamProtocolError('UNEXPECTED_EXTRA_CHOICE')
            delta=choice.get('delta',choice.get('message',{})) or {}
            if delta.get('content'):
                if receipt.get('finish_reason') is not None:raise StreamProtocolError('CONTENT_AFTER_FINISH')
                content.write(delta['content']);content.flush()
            for key in ('reasoning','reasoning_content'):
                if delta.get(key):reasoning.write(delta[key]);reasoning.flush()
            finish=choice.get('finish_reason')
            if finish is not None:
                if receipt.get('finish_reason') not in (None,finish):raise StreamProtocolError('FINISH_REASON_CHANGED')
                receipt['finish_reason']=finish
                receipt['finish_event_count']=receipt.get('finish_event_count',0)+1
    try:
        for encoded in lines:
            if isinstance(encoded,str):encoded=encoded.encode('utf-8')
            raw.write(encoded);raw.flush();byte_count+=len(encoded);framing_hash.update(encoded)
            line=encoded.decode('utf-8').rstrip('\r\n')
            if not line:
                emit();data=[];frame_type=None
            elif line.startswith(':'):continue
            else:
                field,sep,value=line.partition(':')
                if value.startswith(' '):value=value[1:]
                if field=='data':data.append(value)
                elif field=='event':frame_type=value
        emit()
    finally:
        receipt['stream_evidence']={'event_count':events,'received_bytes':byte_count,
            'received_sha256':framing_hash.hexdigest(),'first_event_seconds':None if first is None else first-started,
            'last_event_seconds':None if last is None else last-started,
            'done_received':receipt.get('done_received',False),'finish_reason':receipt.get('finish_reason'),
            'usage_received':isinstance(receipt.get('usage'),dict),'raw_bytes_preserved':True}


def reported_usage(receipt):
    value=receipt.get('usage')
    if not isinstance(value,dict):return None
    # The reproduced decoder failure returned one prompt and one completion
    # token with a blank body and no finish reason. Preserve that service value
    # as evidence, but do not treat it as trustworthy billing reconciliation.
    if receipt.get('usage_anomaly'):
        return None
    keys=('prompt_tokens','completion_tokens')
    if any(type(value.get(k)) is not int or value[k]<0 for k in keys):return None
    if 'total_tokens' in value and (type(value['total_tokens']) is not int or value['total_tokens']<sum(value[k] for k in keys)):
        return None
    return {k:value[k] for k in keys}

class APIProvider:
    kind='TOGETHER_QWEN_NEW_MODEL_EXECUTION'
    def __init__(self,cfg,work):
        if not (cfg.get('execution_enabled') and cfg.get('paid_api_enabled')):
            raise RuntimeError('MODEL_EXECUTION_NOT_AUTHORIZED_IN_SIDE_REPAIR')
        if cfg.get('capacity_diagnostic') and cfg.get('billing_authorization_mode')!='ROLE_SOURCE_TWO_CASE_APPROVAL':
            raise RuntimeError('EXPLICIT_ROLE_SCOPED_BILLING_AUTHORIZATION_REQUIRED')
        if type(cfg.get('prior_conservative_usd')) not in (int,float) or cfg['prior_conservative_usd']<0:
            raise RuntimeError('PRIOR_ACCOUNTING_REQUIRED_BEFORE_PROVIDER_CONSTRUCTION')
        self.cfg=cfg;self.work=Path(work);self.spent=0.;self.counts={};self.usage={};self.arm_started={};self.receipts=[];self.charges=[];self.halt=False;self.cache={};self.credit_retry_pending={}
        self.billing_hold=False;self.blocked_cases=set();self.wire_hashes={};self.unknown_requests=[]
        self.reserve_continuation=(cfg.get('unknown_usage_policy')=='RESERVE_AND_ISOLATE_FAILED_CASE'
            and cfg.get('allow_unknown_usage_reserve_continuation') is True)
        self.client=self  # Same accounting interface used by the frozen orchestrator.
        save(self.work/'protocol.json',cfg)
    @property
    def dispatch_stop(self):
        return self.halt or self.billing_hold
    def charge_shared(self,cid,arm,receipts):
        key=(cid,arm);u=self.usage.setdefault(key,{'prompt_tokens':0,'completion_tokens':0});seconds=0
        for rc in receipts:
            charge=rc.get('resource_charge',rc.get('usage',{}))
            for field in u:u[field]+=charge.get(field,0)
            seconds+=rc.get('elapsed_seconds',0)
        self.counts[key]=self.counts.get(key,0)+sum(not r.get('not_new_model_call',False) for r in receipts)
        self.arm_started[key]=time.monotonic()-seconds
        self.charges.append({'case_id':cid,'arm':arm,'shared_receipt_hashes':[digest(r) for r in receipts],
            'resource_charge':dict(u),'elapsed_monotonic_seconds':seconds,'not_new_model_calls':True,
            'resource_equivalent_usd':self.cost(u),'new_bill_usd':0})
    def cost(self,u):return (u['prompt_tokens']*self.cfg['prices']['input']+u['completion_tokens']*self.cfg['prices']['output'])/1e6
    def call(self,cid,arm,tag,request,attempt=0):
        diagnostic=self.cfg.get('capacity_diagnostic',False)
        if diagnostic and (cid not in self.cfg['diagnostic_case_limit'] or arm not in self.cfg['diagnostic_arm_limit']):
            raise ResourceStop('OUTSIDE_AUTHORIZED_TWO_CASE_DIAGNOSTIC')
        key=(cid,arm);reqhash=digest(request)
        retry_key=(cid,arm,tag,reqhash)
        recovery_wait_seconds=0.0
        same_wire_retry=self.credit_retry_pending.pop(retry_key,None)
        if same_wire_retry is not None:
            if attempt!=1:raise ResourceStop('CREDIT_RETRY_ATTEMPT_MISMATCH')
            delay=self.cfg['credit_retry_backoff_seconds']
            print('CREDIT_RECOVERY_WAIT',cid,arm,tag,delay,flush=True)
            wait_start=time.monotonic();time.sleep(delay)
            recovery_wait_seconds=time.monotonic()-wait_start
        cached=self.cache.get((cid,arm,reqhash))
        if cached and attempt==0:
            value,rc=cached
            return value,{**rc,'not_new_model_call':True,'api_dispatch':False,'accounted_usd':0,'elapsed_seconds':0,
                'usage':{'prompt_tokens':0,'completion_tokens':0},'resource_charge':{'prompt_tokens':0,'completion_tokens':0},'cache_receipt':rc['receipt_path']}
        u=self.usage.setdefault(key,{'prompt_tokens':0,'completion_tokens':0});self.arm_started.setdefault(key,time.monotonic())
        output_cap=request.get('output_token_cap',self.cfg['parameters']['max_tokens'])
        reserve={'prompt_tokens':self.cfg['context_length']-output_cap,'completion_tokens':output_cap}
        # Explicit output capacity avoids relying on the observed 2048 default.
        # Full provider context reservation bounds unknown-usage failures without
        # pretending the local tokenizer is an exact hosted billing tokenizer.
        if self.halt:raise CallFailure('API_SERVICE_HALTED','REVIEW_LAST_RECEIPT_BEFORE_FURTHER_DISPATCH',True)
        if self.billing_hold:raise CallFailure('BILLING_RECONCILIATION_REQUIRED','UNKNOWN_USAGE_POLICY_HOLD',False)
        if key in self.blocked_cases:raise CallFailure('CASE_ATTEMPT_ALREADY_FAILED','FAILED_CASE_NOT_REPEATED',False)
        if not diagnostic and self.counts.get(key,0)>=self.cfg['max_calls_per_arm']:raise ResourceStop('API_CALL_CAP')
        if not diagnostic and any(u[k]+reserve[k]>self.cfg['max_'+('input' if k=='prompt_tokens' else 'output')+'_tokens_per_arm'] for k in u):
            save(self.work/cid/arm/'resource-stops'/f'{tag}-attempt{attempt}.json',{
                'reason':'API_TOKEN_RESERVATION_CAP_NO_DISPATCH','usage_accounted':dict(u),'next_call_worst_case_reserve':reserve,
                'caps':{'prompt_tokens':self.cfg['max_input_tokens_per_arm'],'completion_tokens':self.cfg['max_output_tokens_per_arm']},
                'api_dispatched':False,'actual_tokens_exhausted':any(u[k]>=self.cfg['max_'+('input' if k=='prompt_tokens' else 'output')+'_tokens_per_arm'] for k in u),
                'reason_not_exact_request_cost':'Hosted tokenizer/template revision unverified; strict caps keep the context bound. Request-size estimates are not a certified reservation.'})
            raise ResourceStop('API_TOKEN_RESERVATION_CAP_NO_DISPATCH')
        seconds=self.cfg['local_per_call_seconds'] if diagnostic else self.cfg['local_total_seconds']-(time.monotonic()-self.arm_started[key])
        if seconds<=0:raise ResourceStop('API_ARM_TIME_CAP')
        upper=self.cost(reserve)
        if (not diagnostic or self.cfg.get('enforce_scoped_dollar_cap')) and self.spent+upper>self.cfg['maximum_new_usd']+1e-10:raise ResourceStop('CUMULATIVE_USD_CAP_NO_DISPATCH')
        token=credential()  # Existing authorized credential; never saved/logged.
        plain=(arm in ('A0','LW') and 'plain_wire' in request)
        wire=request['plain_wire'] if plain else request_wire(request,self.cfg,0)
        if diagnostic:
            if wire.get('max_tokens')!=self.cfg['diagnostic_output_tokens'] or wire['max_tokens']!=output_cap:
                raise ResourceStop('DIAGNOSTIC_WIRE_CAPACITY_MISMATCH')
        elif wire['max_tokens']!=output_cap:raise ResourceStop('RESERVATION_WIRE_OUTPUT_CAP_MISMATCH')
        number=self.counts.get(key,0);dest=self.work/cid/arm/'calls'/f'{number:03d}-{tag}-attempt{attempt}'
        if dest.exists():raise ResourceStop('EXISTING_DISPATCH_NOT_REPEATED')
        if same_wire_retry is not None and digest(wire)!=same_wire_retry:
            raise ResourceStop('CREDIT_RETRY_WIRE_CHANGED')
        logical=(cid,arm,tag,reqhash)
        if attempt:
            if attempt>self.cfg['max_technical_retries'] or self.wire_hashes.get(logical)!=digest(wire):
                raise ResourceStop('TECHNICAL_RETRY_WIRE_MISMATCH_OR_LIMIT')
        else:self.wire_hashes[logical]=digest(wire)
        save(dest/'request.json',wire)
        if not plain:
            save(dest/'decoder-contract.json',{'normalization':'SELF_CONTAINED_ANYOF_V1',
                'semantic_schema_hash':digest(request['schema']),
                'decoder_schema_hash':digest(wire['response_format']['json_schema']['schema']),
                'original_semantic_schema':request['schema'],'model_values_modified':False})
        save(dest/'start.json',{'pipeline_request_hash':reqhash,'wire_hash':digest(wire),'reserved_usd':upper,'reserved_usage':reserve,'started_epoch':time.time(),'api_dispatch_planned':True})
        self.spent+=upper;self.counts[key]=number+1
        for field in u:u[field]+=reserve[field]
        rc={'case_id':cid,'arm':arm,'tag':tag,'attempt':attempt,'pipeline_request_hash':reqhash,'wire_hash':digest(wire),
            'actual_provider':'TOGETHER_API','api_dispatch':True,'server_weight_revision_verified':False,'done_received':False,'source_input_truncated':False,'reserved_usd':upper,'receipt_path':str(dest/'receipt.json'),
            'retry_wire_identical':bool(attempt),'unknown_usage_policy':self.cfg.get('unknown_usage_policy'),
            'reserve_continuation_authorized':self.reserve_continuation}
        start=time.monotonic();value=None;guard=None
        def timeout(*args):raise TimeoutError('FROZEN_API_CALL_OR_ARM_TIME_CAP')
        previous=signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,min(seconds,self.cfg['local_per_call_seconds']))
        print('START_API',cid,arm,tag,'reserved_usd',upper,flush=True)
        try:
            req=urllib.request.Request(self.cfg['endpoint'],data=json.dumps(wire).encode(),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','Accept':'text/event-stream','User-Agent':'legal-ai-research/1.0'},method='POST')
            with urllib.request.urlopen(req,timeout=180) as response:
                rc.update(http_status=response.status,request_id=response.headers.get('x-request-id'),service_date=response.headers.get('date'))
                rc['response_headers']={k:response.headers.get(k) for k in ('content-type','x-request-id','date','server','retry-after') if response.headers.get(k) is not None}
                with (dest/'raw-sse.txt').open('xb') as raw,(dest/'response.txt').open('x') as out,(dest/'reasoning.txt').open('x') as reason:
                    guard=ProgressWriter(out,self.cfg['blank_progress_limit_chars'],
                        self.cfg['repetition_min_chars'],self.cfg['repetition_min_repeats'],self.cfg['repetition_window_chars'])
                    consume_sse(response,raw,guard,reason,rc)
            rc['status']=completion_status(rc)
            if (dest/'reasoning.txt').stat().st_size or rc.get('model')!=self.cfg['api_model']:
                rc['status']='MODEL_CONFIGURATION_MISMATCH';self.halt=True
            if rc['status']=='OK' and plain:
                value=(dest/'response.txt').read_text()
                if not value.strip():rc['status']='EMPTY_REPORT'
            elif rc['status']=='OK':
                raw_value=loads((dest/'response.txt').read_text())
                value,changes=canonical_id_sets(raw_value,request['schema'])
                rc['id_set_canonicalization_count']=len(changes)
                save(dest/'id-set-canonicalization.json',{'changes':changes,'raw_response_preserved':True,'semantic_judgment_changes':False})
                validate(value,request['schema'])
                validate(value,wire['response_format']['json_schema']['schema'])
                rc['semantic_and_decoder_contracts_valid']=True
        except KeyboardInterrupt:
            rc.update(status='USER_INTERRUPTED',error='USER_REQUESTED_STOP',no_retry=True)
            self.halt=True
        except BlankNoProgress as exc:
            rc.update(status='BLANK_NO_PROGRESS',error=str(exc),no_retry=True,
                whitespace_limit=self.cfg['blank_progress_limit_chars'],no_json_completion=True)
        except RepeatedTextNoProgress as exc:
            rc.update(status='REPEATED_TEXT_NO_PROGRESS',error=str(exc),no_retry=True,no_json_completion=True)
        except StreamProtocolError as exc:
            rc.update(status='STREAM_PROTOCOL_ERROR',error=str(exc))
        except (ContractError,json.JSONDecodeError) as exc:
            rc.update(status='FORMAT_ERROR',error=str(exc))
        except TimeoutError as exc:
            rc.update(status='CALL_TIMEOUT',error=str(exc))
        except urllib.error.HTTPError as exc:
            rc.update(status='HTTP_FAILURE',http_status=exc.code)
            (dest/'http-error.txt').write_text(exc.read().decode(errors='replace').replace(token,'[REDACTED]'))
            if exc.code in (400,401,402,403,404,422,429):self.halt=True
        except Exception as exc:
            rc.update(status='TECHNICAL_FAILURE',error=type(exc).__name__+':'+str(exc).replace(token,'[REDACTED]'))
        finally:
            signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)
        if (rc.get('usage',{}).get('prompt_tokens')==1
                and rc.get('usage',{}).get('completion_tokens')==1
                and rc.get('finish_reason') is None
                and (dest/'response.txt').is_file()
                and not (dest/'response.txt').read_text().strip()):
            rc['usage_anomaly']='BLANK_NO_FINISH_WITH_ONE_PLUS_ONE_TOKEN_USAGE'
        actual=reported_usage(rc);known=actual is not None
        charged=actual if known else reserve
        actual_cost=self.cost(charged);self.spent+=actual_cost-upper
        # Reserve and actual usage remain separate. A schema/repetition fix does
        # not authorize a different billing policy or declare the reserve paid.
        if not known:
            self.unknown_requests.append({'request_id':rc.get('request_id'),'receipt_path':rc['receipt_path'],'reserve_usd':upper})
            self.billing_hold=not self.reserve_continuation
            rc.update(billing_state='USAGE_UNKNOWN_RESERVED',billing_hold=self.billing_hold,
                halt_reason='USAGE_RECONCILIATION_REQUIRED' if self.billing_hold else None)
            # Unknown-cost failures are never retried. With explicit reserve
            # policy, the failed case is isolated; independent authorized cases
            # may proceed with the full reserve still charged to the ledger.
            if rc['status']!='OK':self.blocked_cases.add(key);rc['no_retry']=True
        else:rc['billing_state']='USAGE_REPORTED_NOT_INVOICE_VERIFIED'
        rc['content_status']=rc['status']
        if not known and self.billing_hold and rc['status']=='OK':rc['status']='USAGE_UNRESOLVED'
        for field in u:u[field]+=charged[field]-reserve[field]
        if any(charged[k]>reserve[k] for k in reserve):rc['status']='SERVICE_RESERVATION_EXCEEDED';self.halt=True
        rc.update(accounted_usd=actual_cost,known_cost_usd=actual_cost if known else None,resource_charge=charged,
            elapsed_seconds=time.monotonic()-start,cumulative_accounted_usd=self.cfg['prior_conservative_usd']+self.spent,usage_missing_reserved=not known,
            raw_response_path=str(dest/'response.txt'))
        if same_wire_retry is not None:
            rc['request_elapsed_seconds']=rc['elapsed_seconds']
            rc['elapsed_seconds']+=recovery_wait_seconds
            rc.update(credit_transport_retry=True,credit_retry_backoff_seconds=self.cfg['credit_retry_backoff_seconds'],retry_wire_identical=True)
        recoverable_credit=(known and arm!='A0' and rc.get('http_status')==402 and attempt==0 and self.cfg.get('credit_balance_verified_positive')
            and (diagnostic or self.spent+upper<=self.cfg['maximum_new_usd']+1e-10))
        if recoverable_credit:rc['one_credit_transport_retry_permitted']=True
        if guard is not None:rc['stream_progress']=guard.diagnostic()
        rc['free_text_hard_length_limit']=False
        rc.update(manual_output_token_limit_omitted=False,explicit_output_token_capacity=wire['max_tokens'],
            resource_budget_enforced=not diagnostic,aggregate_resource_budget_enforced=not diagnostic)
        rc.update(service_halted=self.halt,billing_hold=self.billing_hold,case_blocked=key in self.blocked_cases,
            dispatch_stop=self.dispatch_stop,unknown_usage_is_not_confirmed_charge=not known)
        save(dest/'receipt.json',rc);self.receipts.append(rc)
        print('END_API',cid,arm,tag,rc['status'],'usd',actual_cost,flush=True)
        if rc['status']!='OK':
            if recoverable_credit:
                self.halt=False
                self.credit_retry_pending[retry_key]=digest(wire)
                err=RuntimeError('API:HTTP402_ONE_BOUNDED_TRANSPORT_RETRY');err.receipts=[rc];raise err
            err=CallFailure(rc['status'],rc.get('halt_reason'),self.halt) if self.dispatch_stop or rc.get('no_retry') else RuntimeError('API:'+rc['status']);err.receipts=[rc];raise err
        self.cache[(cid,arm,reqhash)]=(value,rc)
        return value,rc


def completion_status(receipt):
    if receipt.get('finish_reason')=='length':return 'OUTPUT_TRUNCATED'
    if receipt.get('finish_reason') is None:return 'STREAM_INCOMPLETE'
    if not receipt.get('done_received'):return 'STREAM_INCOMPLETE'
    if receipt.get('finish_reason')!='stop':return 'PROVIDER_FINISH_FAILURE'
    return 'OK'
