"""Freeze once, then run P and E on the same two exposed disputes."""
import sys,ast,json,io,os
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent;sys.path.insert(0,str(ROOT/'src'))
from common import read,save,write,filehash,utc
from transport import Client,service_metadata
from pipeline import execute
from local_edits import apply_local

def protect():
    for p,h in read(ROOT/'protected-inputs.json').items():assert filehash(p)==h,p

def offline():
    protect();cfg=read(ROOT/'protocol.json');rows=[]
    class Fixture:
        halt=False
        def call(self,tag,system,material,cap):
            if tag.endswith('-plan'):return {'items':[],'open_items':[]}
            if tag.endswith('-draft'):return {'report':'ENGINEERING_SOURCE_DESCRIPTION.\n\nENGINEERING_NEEDS_CORRECTION.'}
            if tag.endswith('-locate'):return {'findings':[{'id':'F1','target':'ENGINEERING_NEEDS_CORRECTION.','evidence':[]}]}
            return {'edits':[{'id':'E1','op':'REPLACE','old':'ENGINEERING_NEEDS_CORRECTION.','new':'ENGINEERING_REVISED_NOT_LEGAL_ANSWER.','source_ids':[]}],'not_changed':[]}
    for cid in cfg['case_ids']:
        dossier=read(ROOT/'inputs'/f'{cid}.json')
        for method in cfg['methods']:
            out=execute(Fixture(),dossier,method,ROOT/'private/offline-whole-flow-v1'/cid/method,cfg['stage_output_caps']);assert out['full_chain_completed'] and out['final_report_available']
            assert out['report_changed']==(method=='E')
            rows.append({'case_id':cid,'method':method,'actual_source_count':len(dossier['sources']),'full_engineering_flow_completed':True})
    # Same whole-flow engineering acceptance includes its failed-locator branch;
    # independent editing remains executable and the original content is retained.
    class FailureFixture(Fixture):
        def call(self,tag,system,material,cap):
            if tag.endswith('-locate'):raise TimeoutError('OFFLINE_FIXTURE_NO_MODEL')
            if tag.endswith('-edit'):return {'edits':[{'id':'E1','op':'REPLACE','old':'ENGINEERING_NEEDS_CORRECTION.','new':'ENGINEERING_NEEDS_CORRECTION.','source_ids':[]}]}
            return super().call(tag,system,material,cap)
    out=execute(FailureFixture(),read(ROOT/'inputs/1251841.json'),'E',ROOT/'private/offline-whole-flow-v1/failure-branch',cfg['stage_output_caps']);assert out['final_report_available'] and not out['full_chain_completed'] and not out['report_changed']
    sample='首句正确。\n\n第二句待修。\n\n结尾正确。';fixed,audit=apply_local(sample,{'edits':[{'id':'A','op':'REPLACE','old':'第二句待修。','new':'第二句已修。','source_ids':[]}]},{})
    assert fixed=='首句正确。\n\n第二句已修。\n\n结尾正确。' and audit['applied']==1
    from sse import consume_sse
    from stream_guard import ProgressWriter
    rc={};output=io.StringIO();raw=next((ROOT.parent/'rapido-ontology-specialist-review-v47-2026-10-27-v1/private/two-case-qwen38-development-v1/transport/calls').glob('*-draft/raw-sse.txt'))
    consume_sse(raw.read_bytes().splitlines(keepends=True),io.BytesIO(),ProgressWriter(output,1024),io.StringIO(),rc);assert rc['done_received'] and json.loads(output.getvalue())
    protect();save(ROOT/'offline-acceptance.json',{'at':utc(),'engineering_pass':True,'whole_flow':rows,'failed_diagnosis_keeps_report':True,'no_op_not_accepted_as_change':True,'unicode_untouched_spans_preserved':True,'real_Qwen38_cached_stream_parsed':True,'new_model_calls':0,'semantic_quality':None});print('WHOLE_FLOW_ENGINEERING_PASS',flush=True)

def freeze():
    protect();assert read(ROOT/'offline-acceptance.json')['engineering_pass']
    save(ROOT/'service-metadata-frozen.json',service_metadata())
    files=[ROOT/'run.py',*(ROOT/'src').glob('*.py'),ROOT/'protocol.json',ROOT/'protected-inputs.json',ROOT/'baseline-registry.json',ROOT/'service-metadata-frozen.json',ROOT/'offline-acceptance.json',*(ROOT/'inputs').glob('*.json')]
    for p in files:
        if p.suffix=='.py':ast.parse(p.read_text())
    save(ROOT/'freeze.json',{'at':utc(),'files':{str(p.relative_to(ROOT)):filehash(p) for p in files}});print('FROZEN',len(files),flush=True)

def run():
    protect();cfg=read(ROOT/'protocol.json')
    for p,h in read(ROOT/'freeze.json')['files'].items():assert filehash(ROOT/p)==h,p
    work=ROOT/'private/two-route-development-v1';work.mkdir(parents=True,exist_ok=False)
    save(work/'started.json',{'at':utc(),'pid':os.getpid(),'freeze_hash':filehash(ROOT/'freeze.json'),'A0_rerun':False});save(work/'service-metadata-at-start.json',service_metadata())
    client=Client(cfg,work/'transport');results=[]
    for cid in cfg['case_ids']:
        d=read(ROOT/'inputs'/f'{cid}.json')
        for method in cfg['methods']:
            if client.halt:results.append({'case_id':cid,'method':method,'status':'NOT_RUN_GLOBAL_SERVICE_HALT','quality':None});continue
            out=execute(client,d,method,work/'cases'/cid/method,cfg['stage_output_caps']);results.append(out);save(work/(cid+'-'+method+'-terminal.json'),out)
    save(work/'outcome.json',{'results':results,'resources':client.ledger(),'A0_new_calls':0,'R':None,'H':None,'goal_achieved':False});protect();save(work/'exit.json',{'at':utc(),'terminal':True});print('BATCH_FINISHED',flush=True)

if __name__=='__main__':{'offline':offline,'freeze':freeze,'run':run}[sys.argv[1]]()
