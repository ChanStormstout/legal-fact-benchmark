"""One frozen repaired source comparison; original results remain unchanged."""
import argparse
import copy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PREP = HERE.parent/'full-judgment-extraction-comparison-preparation-2026-10-25-v1'
REPO = Path('/Users/victor/Documents/Codex/2026-09-28/files-mentioned-by-the-user-canonicalizing')
V7 = REPO/'outputs/rapido-role-extraction-experiment-v7-2026-10-25'
V25 = REPO/'outputs/rapido-ontology-source-v25-2026-10-25-v1'
sys.path[:0] = [str(HERE), str(V7), str(V25/'src'), str(REPO)]
from source_v8 import run as run_ours, plan as source_plan, reading_request
from common import read, save, digest
from latentweaver_repaired import run_case as run_lw, modules, case_text, first_messages
from communication import request_wire


def verify():
    manifest = read(HERE/'freeze.json')
    for filename, expected in manifest['files'].items():
        if hashlib.sha256(Path(filename).read_bytes()).hexdigest() != expected:
            raise RuntimeError('FROZEN_INPUT_OR_CODE_CHANGED:' + filename)
    return digest(manifest)


def preflight():
    cfg = read(HERE/'protocol.json')
    sources = read(PREP/'private/inputs/1251841.json')['sources']
    snapshot = {'directory': {sid: {'domain': 'CASE', 'text': text}
                              for sid, text in sources.items()}}
    text = case_text(snapshot)
    assert all('[' + sid + ']\n' + value in text for sid, value in sources.items())
    groups = source_plan(sources)
    req = reading_request(sources, groups[0])
    transport = {'policy': req['policy'], 'task': req['task'], 'schema': req['schema'],
                 'material': {k: v for k, v in req.items() if k not in ('policy','task','schema')},
                 'output_token_cap': cfg['diagnostic_output_tokens']}
    wire = request_wire(transport, cfg, 0)
    assert json.loads(wire['messages'][1]['content'])['sources'] == sources
    assert wire['max_tokens'] == 65536 and len(text.split()) < 6000
    for kind in ('a','b'):
        assert text in first_messages(kind, text)[1]['content']
    m = modules()
    m['config'].load_config(V25/'private/external/latentweaver/source/prompt2_v2/config.yaml')
    from role_api_provider import APIProvider
    return {'status': 'READY_NO_MODEL_CALL', 'case_id': '1251841',
            'source_paragraphs': len(sources), 'source_hash': digest(sources),
            'method_order': cfg['arms'], 'our_semantic_calls_if_complete': 2*len(groups),
            'lw_semantic_calls_if_complete': 4, 'maximum_new_usd': cfg['maximum_new_usd'],
            'source_equivalence_checked': True, 'method_quality_not_checked': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    checked = preflight()
    if not args.run:
        print(json.dumps(checked)); return
    frozen = verify()
    cfg = read(HERE/'protocol.json'); auth = read(HERE/'authorization.json')
    if not (auth['approved'] is True and auth['maximum_new_usd'] == cfg['maximum_new_usd'] == .57934014
            and auth['cases'] == cfg['cases'] == ['1251841']
            and auth['arms'] == cfg['arms'] == ['LW','ROLE']):
        raise RuntimeError('AUTHORIZATION_SCOPE_MISMATCH')
    dest = HERE/'private/run-v1'
    if dest.exists(): raise RuntimeError('EXISTING_RUN_NOT_REPEATED')
    with (REPO/'.runtime/rapido-proof-task-api.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        save(dest/'preflight.json', checked)
        save(dest/'authorization.json', auth)
        save(dest/'start.json', {'pid':os.getpid(), 'epoch':time.time(), 'freeze_hash':frozen})
        from role_api_provider import APIProvider
        provider = APIProvider(cfg, dest/'transport')
        sources = read(PREP/'private/inputs/1251841.json')['sources']
        snap = {'directory': {sid: {'domain':'CASE','text':value} for sid,value in sources.items()}}
        outcomes=[]; started=time.monotonic()
        try:
            for arm in cfg['arms']:
                verify(); slot = dest/'cases/1251841'/arm
                if provider.dispatch_stop: break
                try:
                    if arm == 'LW':
                        result = run_lw(provider,'1251841',snap,cfg,slot)
                    else:
                        plan=[f'{stage}-{i:03d}' for i in range(len(source_plan(sources)))
                              for stage in ('reading','review')]
                        attempted=[]
                        def ask(tag, req):
                            if len(attempted)>=len(plan) or tag!=plan[len(attempted)]:
                                raise RuntimeError('UNPLANNED_OR_REPEATED_STAGE')
                            if req['sources']!=sources: raise RuntimeError('SOURCE_CHANGED')
                            attempted.append(tag)
                            request={'policy':req['policy'],'task':req['task'],'schema':req['schema'],
                                'material':{k:copy.deepcopy(v) for k,v in req.items()
                                            if k not in ('policy','task','schema')},
                                'output_token_cap':cfg['diagnostic_output_tokens']}
                            for attempt in range(cfg['max_technical_retries']+1):
                                try: return provider.call('1251841','ROLE',tag,request,attempt)[0]
                                except Exception as exc:
                                    receipts=getattr(exc,'receipts',[]); last=receipts[-1] if receipts else {}
                                    if (provider.dispatch_stop or last.get('no_retry') or
                                        last.get('status') not in ('FORMAT_ERROR','STREAM_INCOMPLETE',
                                            'STREAM_PROTOCOL_ERROR','CALL_TIMEOUT','TECHNICAL_FAILURE') or
                                        attempt>=cfg['max_technical_retries']): raise
                        run_ours(sources,ask,slot)
                        result=read(slot/'outcome.json')
                except Exception as exc:
                    result=read(slot/'outcome.json') if (slot/'outcome.json').exists() else {
                        'technical_complete':False,'error':type(exc).__name__+':'+str(exc),
                        'answer':None,'semantic_quality':None}
                    if not (slot/'outcome.json').exists(): save(slot/'outcome.json',result)
                outcomes.append({'arm':arm,**result})
                save(dest/'progress'/f'{len(outcomes):02d}.json',{'outcomes':outcomes,
                    'new_accounted_usd':provider.spent,'dispatch_stop':provider.dispatch_stop})
                print('ARM_FINISHED',arm,json.dumps(result),flush=True)
        finally:
            save(dest/'summary.json',{'case_id':'1251841','outcomes':outcomes,
                'unrun_arms':[a for a in cfg['arms'] if a not in [o['arm'] for o in outcomes]],
                'new_accounted_usd':provider.spent,'paid_calls':len(provider.receipts),
                'unknown_usage_reserves':provider.unknown_requests,
                'prior_conservative_usd':cfg['prior_conservative_usd'],
                'cumulative_accounted_usd':cfg['prior_conservative_usd']+provider.spent,
                'elapsed_seconds':time.monotonic()-started,'semantic_quality':None,
                'full_C_run':False,'no_semantic_reruns':True})
            verify()


if __name__ == '__main__': main()
