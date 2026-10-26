"""One frozen full-document V12 extraction, followed by a mandatory review gate."""
import argparse
import copy
import fcntl
import hashlib
import json
import os
import signal
import sys
import time
from pathlib import Path
import environment as env
import source_v12 as method
from source_v8 import save, digest
from communication import request_wire

OLD=env.HERE.parent/'full-judgment-source-repair-v10-2026-10-26-v1'
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def transport_request(req,cfg):
    material={k:copy.deepcopy(v) for k,v in req.items() if k not in ('policy','task','schema','sources')}
    reconstructed={x['source_id']:x['text'] for unit in material['source_units'].values() for x in unit}
    if reconstructed!=req['sources'] or list(reconstructed)!=list(req['sources']):
        raise ValueError('FULL_SOURCE_ROUNDTRIP_FAILED')
    return {'policy':req['policy'],'task':req['task'],'schema':req['schema'],
            'material':material,'output_token_cap':cfg['parameters']['max_tokens']}

def wire(req,cfg):return request_wire(transport_request(req,cfg),cfg)

def prepare():
    if (env.HERE/'protocol.json').exists():raise ValueError('ALREADY_PREPARED')
    cfg=load(OLD/'protocol.json'); accounting=load(env.HERE/'private/predecessor-stop.json')
    cfg.update(version=method.VERSION,cases=['1251841'],arms=['V12'],execution_enabled=False,
               paid_api_enabled=False,prior_conservative_usd=accounting['prior_total_conservative_usd'],
               maximum_new_usd=accounting['remaining_original_six_case_authorization_usd'],
               allow_unknown_usage_reserve_continuation=True,
               arm_order_by_case={'1251841':['V12']},
               comparison_scope='One repaired method attempt; preserved same-input V9/LW are descriptive development comparators, not newly randomized concurrent arms.',
               expansion_gate='Stop after the first whole document for source-based review; do not automatically run remaining cases.',
               source_stage_only=True,no_semantic_reruns=True)
    for k in ['comparator_adapter','comparator_native_chunk_schedule','arm_order_reason']:cfg.pop(k,None)
    save(env.HERE/'protocol.json',cfg)
    save(env.HERE/'private/input.json',load(OLD/'private/preparation/inputs/1251841.json'))
    print(json.dumps({'prepared':True,'remaining_authorized_usd':cfg['maximum_new_usd']}))

def verify():
    f=load(env.HERE/'freeze.json')
    changed=[p for p,h in f['files'].items() if sha(p)!=h]
    if changed:raise ValueError('FROZEN_FILE_CHANGED:'+str(changed))
    return digest(f)

def freeze():
    if (env.HERE/'freeze.json').exists():raise ValueError('ALREADY_FROZEN')
    report=load(env.HERE/'private/offline/report.json')
    if report['status']!='PASS_OFFLINE_INTERFACES_ONLY':raise ValueError('OFFLINE_REVIEW_REQUIRED')
    files=set(env.HERE.glob('*.py'))|set(env.HERE.glob('*.md'))|{env.HERE/'protocol.json'}
    files.update((env.HERE/'private').rglob('*.json'))
    files.update(p for p in (env.HERE/'private/schema-validation-vendor').rglob('*')
                 if p.is_file() and p.suffix in ('.py','.so') and '__pycache__' not in p.parts)
    # Retain all dependency hashes from the predecessor freeze, including imported validators.
    inherited=load(OLD/'freeze.json')['files']
    inherited.update(load(env.HERE.parent/'full-judgment-source-repair-v11-2026-10-26-v1/freeze.json')['files'])
    manifest={'version':method.VERSION,'files':{**inherited,**{str(p):sha(p) for p in sorted(files)}},
              'model_weight_revision_verified':False,'scope':'One whole-document extraction only.'}
    changed=[p for p,h in inherited.items() if sha(p)!=h]
    if changed:raise ValueError('PREDECESSOR_FREEZE_CHANGED:'+str(changed))
    save(env.HERE/'freeze.json',manifest)
    print(json.dumps({'frozen_files':len(manifest['files']),'freeze_hash':digest(manifest)}))

def run():
    fingerprint=verify();cfg=load(env.HERE/'protocol.json');cfg.update(execution_enabled=True,paid_api_enabled=True)
    dest=env.HERE/'private/run-v1'
    if dest.exists():raise ValueError('EXISTING_ATTEMPT_NOT_REPEATED')
    if (env.HERE/'private/STOP').exists():raise ValueError('USER_STOP_REQUEST_PRESENT')
    sources=load(env.HERE/'private/input.json')['sources'];cat=method.prepare_units(sources)
    plan=[f'{s}-{i:03d}' for i in range(len(cat['groups'])) for s in ['reading','independent']]
    plan += [f'{s}-{i:03d}' for s in ['whole-document-reconcile','whole-document-final-review']
             for i in range(len(method.review_groups(cat)))]
    with (env.REPO/'.runtime/rapido-proof-task-api.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        save(dest/'start.json',{'pid':os.getpid(),'epoch':time.time(),'freeze_hash':fingerprint,
             'authorization':'User requested stop, repair and continue experiments under the unused portion of the approved six-case $6 envelope.',
             'case_id':'1251841','reuse_comparator_calls':True,'no_automatic_expansion':True})
        from role_api_provider import APIProvider
        provider=APIProvider(cfg,dest/'transport');attempted=[];start=time.monotonic();stop={'requested':False}
        def halt(*args):stop['requested']=True
        signal.signal(signal.SIGTERM,halt)
        def ask(tag,req):
            if stop['requested'] or (env.HERE/'private/STOP').exists():raise RuntimeError('USER_STOP_BETWEEN_CALLS')
            verify()
            if len(attempted)>=len(plan) or tag!=plan[len(attempted)]:raise ValueError('UNPLANNED_STAGE')
            if req['sources']!=sources:raise ValueError('SOURCE_CHANGED')
            attempted.append(tag);request=transport_request(req,cfg)
            for attempt in range(cfg['max_technical_retries']+1):
                try:return provider.call('1251841','V12',tag,request,attempt)[0]
                except Exception as exc:
                    receipts=getattr(exc,'receipts',[]);last=receipts[-1] if receipts else {}
                    if (stop['requested'] or provider.dispatch_stop or last.get('no_retry') or
                        last.get('status') not in ['STREAM_INCOMPLETE','STREAM_PROTOCOL_ERROR','CALL_TIMEOUT','TECHNICAL_FAILURE'] or
                        attempt>=cfg['max_technical_retries']):raise
        result=None;error=None
        try:result=method.run(sources,ask,dest/'case')
        except Exception as exc:error=type(exc).__name__+':'+str(exc)
        finally:
            outcome=load(dest/'case/outcome.json') if (dest/'case/outcome.json').exists() else result
            save(dest/'summary.json',{'outcome':outcome,'error':error,'attempted_stages':attempted,
                 'physical_calls':len(provider.receipts),'confirmed_usd':sum(r.get('known_cost_usd',0) or 0 for r in provider.receipts),
                 'accounted_usd':provider.spent,'unknown_usage_reserves':provider.unknown_requests,
                 'elapsed_seconds':time.monotonic()-start,'prior_conservative_usd':cfg['prior_conservative_usd'],
                 'remaining_original_six_case_envelope_usd':cfg['maximum_new_usd']-provider.spent,
                 'semantic_quality':None,'full_C_run':False,'next_case_started':False})
            verify()
        print(json.dumps({'outcome':result,'error':error,'accounted_usd':provider.spent}),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','freeze','verify','run'])
    action=ap.parse_args().action
    if action=='prepare':prepare()
    elif action=='freeze':freeze()
    elif action=='verify':print(verify())
    else:run()
