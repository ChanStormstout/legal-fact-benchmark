"""Consolidated offline transport replay and full fictional-case execution.

No network, real credentials or experimental model. Recorded production streams
are read unchanged; fictional legal values come only from the existing fixtures.
"""
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'src'),str(REPO)]
from common import read,save,digest,prepare_sources
from whole_workflow import Provider as FictionalProvider,PACKET,LIB
from runner import run_arm,Session,CallFailure
from communication import ProgressWriter,request_wire
import api_provider as AP

WORK=ROOT/'private/transport-acceptance'/str(time.time_ns())
WORK.mkdir(parents=True)
checks=[]
def check(name,condition):
    if not condition:raise AssertionError(name)
    checks.append(name)


def replay_real():
    old=REPO/'outputs/rapido-source-recovery-v21-1-2026-10-24-v1/private/run/transport/1251841/C/calls'
    results=[]
    cfg=read(ROOT/'protocol.json')
    for folder in sorted(old.iterdir()):
        original=(folder/'raw-sse.txt').read_bytes();rc={'done_received':False}
        out=io.StringIO();raw=io.BytesIO();reason=io.StringIO()
        guard=ProgressWriter(out,cfg['blank_progress_limit_chars'],cfg['repetition_min_chars'],cfg['repetition_min_repeats'],cfg['repetition_window_chars'])
        AP.consume_sse(io.BytesIO(original),raw,guard,reason,rc)
        prior=read(folder/'receipt.json')
        check(folder.name+' body is byte-equivalent',out.getvalue()==(folder/'response.txt').read_text())
        check(folder.name+' raw evidence is unchanged',raw.getvalue()==original)
        check(folder.name+' terminal classification unchanged',AP.completion_status(rc)==prior['status'])
        check(folder.name+' usage preserved',rc.get('usage')==prior.get('usage'))
        results.append({'call':folder.name,'status':AP.completion_status(rc),'characters':len(out.getvalue()),'usage':AP.reported_usage(rc),
            'source_sha256':hashlib.sha256(original).hexdigest(),'stream_evidence':rc['stream_evidence']})
    save(WORK/'real-stream-replay.json',{'actual_calls':len(results),'new_model_calls':0,'cases':results,
        'conclusion':'Parser reproduces all 39 received answers; no evidence of lost local content. Last stream still fails, not repaired into success.'})


def frame(content,usage=True,finish=True,done=True,error=None):
    value={'id':'OFFLINE_REQUEST','model':'Qwen/Qwen3.5-9B','choices':[]}
    chunks=[]
    def add(event):chunks.append(('data: '+json.dumps(event)+'\n\n').encode())
    add({**value,'choices':[{'index':0,'delta':{'content':content},'finish_reason':None}]})
    if error:add({'error':error})
    if finish:add({**value,'choices':[{'index':0,'delta':{},'finish_reason':'stop'}]})
    if usage:add({**value,'usage':{'prompt_tokens':20,'completion_tokens':10,'total_tokens':30}})
    if done:chunks.append(b'data: [DONE]\n\n')
    return b''.join(chunks)


class FakeHTTP(io.BytesIO):
    status=200
    headers={'x-request-id':'OFFLINE_REQUEST','content-type':'text/event-stream'}
    def __enter__(self):return self
    def __exit__(self,*args):self.close()


class OfflineProvider(AP.APIProvider):
    kind='OFFLINE_HTTP_FIXTURE'
    def __init__(self,cfg,path,mode):
        super().__init__(cfg,path);self.mode=mode;self.fixture=FictionalProvider();self.wires=[];self.pending=None;self.first=True
    def call(self,cid,arm,tag,request,attempt=0):
        self.pending=(cid,arm,tag,request,attempt)
        return super().call(cid,arm,tag,request,attempt)
    def http(self,req,timeout):
        self.wires.append(json.loads(req.data));cid,arm,tag,request,attempt=self.pending
        if self.first and self.mode=='broken':
            self.first=False;return FakeHTTP(frame('{"observations": [',usage=False,finish=False))
        value,_=self.fixture.call(cid,arm,tag,request,attempt)
        if self.first and self.mode=='known_format_failure':
            self.first=False;return FakeHTTP(frame('{'))
        missing=self.first and self.mode=='usage_only_missing'
        self.first=False
        return FakeHTTP(frame(json.dumps(value),usage=not missing))


def test_save(path,value):
    if str(path).endswith('receipt.json'):
        value.update(offline_test_only=True,synthetic=True,api_dispatch=False,actual_provider='OFFLINE_HTTP_FIXTURE')
    elif str(path).endswith('start.json'):
        value.update(offline_test_only=True,api_dispatch_planned=False)
    save(path,value)


def packet(cid):
    p=copy.deepcopy(PACKET);p['case_id']=cid
    p['sources'][0]['text']+=' Dana formerly owned that parcel.'
    p['sources'][1]['text']+=' The Appeal Court considered the prior record.'
    p['sources'][2]['text']+=' The record is complete for possession.'
    p['sources'] += [{'source_id':'history:a','document_id':'other-a','document_role':'HISTORICAL','text':'In a separate historical possession proceeding Dana testimony was disputed.'},
        {'source_id':'history:b','document_id':'other-b','document_role':'HISTORICAL','text':'Another separate possession decision records disputed occupation and permission.'}]
    return prepare_sources(p,LIB)


def workflow(mode,allow=True):
    cfg=read(ROOT/'protocol.json');cfg.update(execution_enabled=True,paid_api_enabled=True,
        billing_authorization_mode='V22_SCOPED_ACTUAL_USAGE_APPROVAL',diagnostic_case_limit=['OFFLINE_A','OFFLINE_B'],
        allow_unknown_usage_reserve_continuation=allow)
    provider=OfflineProvider(cfg,WORK/mode/str(allow)/'transport',mode)
    with patch.object(AP,'credential',lambda:'OFFLINE_NO_CREDENTIAL'),patch.object(AP.urllib.request,'urlopen',provider.http),patch.object(AP,'save',test_save):
        first=run_arm(provider,packet('OFFLINE_A'),cfg,WORK/mode/str(allow)/'cases/OFFLINE_A/C','C')
        if mode=='broken':
            check('incomplete first case remains failure '+str(allow),not first['complete_chain'] and first['stop_reason']=='STREAM_INCOMPLETE')
            check('unknown reserve retained '+str(allow),len(provider.receipts)==1 and provider.spent==provider.receipts[0]['reserved_usd'])
            before=len(provider.wires)
            if allow:
                check('failure isolated without service halt',not provider.dispatch_stop and ('OFFLINE_A','C') in provider.blocked_cases)
                second=run_arm(provider,packet('OFFLINE_B'),cfg,WORK/mode/str(allow)/'cases/OFFLINE_B/C','C')
                check('independent second case reaches final check',second['complete_chain'] and second['internal_pass'])
                check('failed first case never retried',sum(r['case_id']=='OFFLINE_A' for r in provider.receipts)==1)
            else:
                check('reserve continuation cannot bypass approval',provider.billing_hold and provider.dispatch_stop and not provider.halt)
                second=run_arm(provider,packet('OFFLINE_B'),cfg,WORK/mode/str(allow)/'cases/OFFLINE_B/C','C')
                check('unapproved continuation dispatches no network',len(provider.wires)==before and not second['complete_chain'])
        else:
            check(mode+' reaches actual final checker',first['complete_chain'] and first['internal_pass'])
            if mode=='known_format_failure':
                check('bounded technical retry has byte-identical body',provider.wires[0]==provider.wires[1])
                check('first format failure preserved',provider.receipts[0]['status']=='FORMAT_ERROR' and provider.receipts[1]['status']=='OK')
            if mode=='usage_only_missing':
                check('complete answer not mislabeled truncated',provider.receipts[0]['content_status']=='OK' and provider.receipts[0]['status']=='OK')
                check('unknown usage never charged zero',provider.receipts[0]['known_cost_usd'] is None and provider.receipts[0]['accounted_usd']>0)
        save(WORK/mode/str(allow)/'scenario.json',{'offline_fictional_only':True,'new_model_calls':0,'simulated_http_requests':len(provider.wires),
             'first_outcome':first,'second_outcome':locals().get('second'),'fees_are_simulated_not_real':True})


def framing_checks():
    # One captured-compatible framing scenario, with comments, multiline JSON,
    # CRLF, a separate usage frame and EOF without a final blank line.
    stream=b': heartbeat\r\n\r\n'+frame('{}').replace(b'data: {"id":',b'data: {\n' + b'data: "id":').replace(b'\n',b'\r\n').rstrip(b'\r\n')
    rc={};out=io.StringIO();AP.consume_sse(io.BytesIO(stream),io.BytesIO(),out,io.StringIO(),rc)
    check('SSE comment multiline CRLF and terminal EOF retained',out.getvalue()=='{}' and AP.completion_status(rc)=='OK' and AP.reported_usage(rc)['completion_tokens']==10)
    rc={}
    try:AP.consume_sse(io.BytesIO(frame('{}',error={'code':'engine_error','message':'fictional upstream failure'})),io.BytesIO(),io.StringIO(),io.StringIO(),rc)
    except AP.StreamProtocolError:pass
    else:raise AssertionError('upstream stream error ignored')
    check('provider error detail preserved',rc['provider_error']['code']=='engine_error')
    check('boolean fake usage is not a measured token count',AP.reported_usage({'usage':{'prompt_tokens':True,'completion_tokens':0}}) is None)


if __name__=='__main__':
    with patch('socket.create_connection',side_effect=AssertionError('NETWORK_FORBIDDEN_IN_OFFLINE_ACCEPTANCE')):
        replay_real();framing_checks()
        workflow('broken',True);workflow('broken',False)
        workflow('known_format_failure',True);workflow('usage_only_missing',True)
    save(WORK/'summary.json',{'status':'PASS','scope':'RECORDED_TRANSPORT_REPLAY_AND_FICTIONAL_END_TO_END',
        'checks':checks,'new_model_calls':0,'actual_new_cost_usd':0,'real_quality_improvement':None,
        'remote_stream_root_cause':'UNRESOLVED'})
    print('ACCEPTANCE_DIRECTORY',WORK)
