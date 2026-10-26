"""Frozen, sequential whole-document comparison. No execution without scoped approval."""
import argparse
import copy
import fcntl
import json
import os
import time
from pathlib import Path
import environment as env
import source_v10 as v10
import source_v9 as v9
import latentweaver_v10 as lw
from prepare import load, sha, wire
from source_v8 import save, digest


def verify():
    manifest=load(env.HERE/'freeze.json')
    changed=[p for p,h in manifest['files'].items() if sha(p)!=h]
    if changed:raise RuntimeError('FROZEN_INPUT_OR_CODE_CHANGED:'+str(changed))
    return digest(manifest)


def preflight():
    cfg=load(env.HERE/'protocol.json')
    review=load(env.HERE/'private/offline-whole-document-review/report.json')
    if review['status']!='PASS_OFFLINE_WHOLE_DOCUMENT_INTERFACE_ONLY':raise RuntimeError('OFFLINE_REVIEW_PENDING')
    if review['new_model_calls']!=0:raise RuntimeError('REVIEW_EVIDENCE_MISMATCH')
    if review.get('replay_context_warnings'):raise RuntimeError('KNOWN_CONTEXT_OVERFLOW_NOT_RESOLVED')
    lw.modules()['config'].load_config(lw.EXTERNAL/'prompt2_v2/config.yaml')
    from role_api_provider import APIProvider
    rows=[]
    for cid in cfg['cases']:
        inp=load(env.HERE/'private/preparation/inputs'/f'{cid}.json')
        if digest(inp['sources'])!=inp['manifest']['source_map_hash']:raise RuntimeError('SOURCE_HASH_MISMATCH')
        catalog=v10.prepare_units(inp['sources'])
        for i,focus in enumerate(catalog['groups']):
            for role,independent in [('primary',False),('independent',True)]:
                request=v10.reading_request(inp['sources'],catalog,focus,independent)
                saved=load(env.HERE/'private/preparation/requests'/cid/f'{i:03d}-{role}.json')
                if saved!=wire(request,cfg):raise RuntimeError('FIRST_CALL_PREVIEW_MISMATCH')
        rows.append({'case_id':cid,'sources':len(inp['sources']),
            'V9_calls':2*len(v9.plan(inp['sources'])),
            'V10_calls':2*len(v10.prepare_units(inp['sources'])['groups'])+
                        2*len(v10.review_groups(v10.prepare_units(inp['sources']))),'LW_max_calls':4})
    return {'status':'READY_FOR_SCOPED_AUTHORIZATION','new_model_calls':0,'cases':rows,
            'semantic_quality':None,'baseline_or_full_C_enabled':False}


def authorization(path, frozen, cfg):
    auth=load(path)
    if not (auth.get('approved') is True and auth.get('freeze_hash')==frozen
            and auth.get('cases')==cfg['cases'] and auth.get('arms')==cfg['arms']):
        raise RuntimeError('SCOPED_APPROVAL_MISSING_OR_MISMATCHED')
    for name in ['maximum_new_usd','prior_conservative_usd']:
        if type(auth.get(name)) not in (int,float) or auth[name]<0:
            raise RuntimeError('EXPLICIT_FINITE_ACCOUNTING_REQUIRED:'+name)
        if not __import__('math').isfinite(auth[name]):raise RuntimeError('NONFINITE_ACCOUNTING')
    if not auth['maximum_new_usd'] or not auth.get('user_authorization_evidence'):
        raise RuntimeError('ACTUAL_NEW_EXPERIMENT_AUTHORIZATION_REQUIRED')
    if auth.get('retain_previous_unknown_reserves') is not True:
        raise RuntimeError('PREVIOUS_ACCOUNTING_RESERVES_MUST_BE_RETAINED')
    runtime=copy.deepcopy(cfg)
    runtime.update(execution_enabled=True,paid_api_enabled=True,
        maximum_new_usd=auth['maximum_new_usd'],prior_conservative_usd=auth['prior_conservative_usd'],
        allow_unknown_usage_reserve_continuation=auth.get('allow_new_unknown_usage_reserve_continuation') is True)
    return auth,runtime


def run_structured(provider,cid,arm,sources,cfg,slot):
    module=v9 if arm=='V9' else v10
    count=len(v9.plan(sources)) if arm=='V9' else len(v10.prepare_units(sources)['groups'])
    plan=[f'{stage}-{i:03d}' for i in range(count)
          for stage in (('reading','review') if arm=='V9' else ('reading','independent'))]
    if arm=='V10':
        plan += [f'{stage}-{i:03d}' for stage in ['whole-document-reconcile','whole-document-final-review']
                 for i in range(len(v10.review_groups(v10.prepare_units(sources))))]
    attempted=[]
    def ask(tag,req):
        if len(attempted)>=len(plan) or tag!=plan[len(attempted)]:raise RuntimeError('UNPLANNED_OR_REPEATED_STAGE')
        if req['sources']!=sources:raise RuntimeError('SOURCE_CHANGED')
        attempted.append(tag)
        request={'policy':req['policy'],'task':req['task'],'schema':req['schema'],
                 'material':{k:copy.deepcopy(v) for k,v in req.items() if k not in ('policy','task','schema')},
                 'output_token_cap':cfg['parameters']['max_tokens']}
        for attempt in range(cfg['max_technical_retries']+1):
            try:return provider.call(cid,arm,tag,request,attempt)[0]
            except Exception as exc:
                receipts=getattr(exc,'receipts',[]);last=receipts[-1] if receipts else {}
                # No semantic retry, format repair, larger cap, changed prompt, or partial-answer completion.
                if (provider.dispatch_stop or last.get('no_retry') or
                    last.get('status') not in ('STREAM_INCOMPLETE','STREAM_PROTOCOL_ERROR','CALL_TIMEOUT','TECHNICAL_FAILURE')
                    or attempt>=cfg['max_technical_retries']):raise
    return module.run(sources,ask,slot)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',action='store_true');ap.add_argument('--authorization',type=Path)
    args=ap.parse_args();checked=preflight();frozen=verify()
    if not args.run:
        print(json.dumps({**checked,'freeze_hash':frozen}));return
    if not args.authorization:raise RuntimeError('SCOPED_AUTHORIZATION_FILE_REQUIRED')
    base=load(env.HERE/'protocol.json');auth,cfg=authorization(args.authorization,frozen,base)
    dest=env.HERE/'private/experiment-v1'
    if dest.exists():raise RuntimeError('EXISTING_EXPERIMENT_NOT_REPEATED')
    with (env.REPO/'.runtime/rapido-proof-task-api.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        save(dest/'preflight.json',checked);save(dest/'authorization.json',auth)
        save(dest/'start.json',{'pid':os.getpid(),'epoch':time.time(),'freeze_hash':frozen})
        from role_api_provider import APIProvider
        provider=APIProvider(cfg,dest/'transport');outcomes=[];start=time.monotonic()
        schedule=[(cid,arm) for cid in cfg['cases'] for arm in cfg['arm_order_by_case'][cid]]
        try:
            for cid,arm in schedule:
                if provider.dispatch_stop:break
                verify();sources=load(env.HERE/'private/preparation/inputs'/f'{cid}.json')['sources']
                slot=dest/'cases'/cid/arm
                try:
                    if arm=='LW':
                        snap={'directory':{sid:{'domain':'CASE','text':text} for sid,text in sources.items()}}
                        result=lw.run_case(provider,cid,snap,cfg,slot)
                    else:result=run_structured(provider,cid,arm,sources,cfg,slot)
                except Exception as exc:
                    result=load(slot/'outcome.json') if (slot/'outcome.json').exists() else {
                        'technical_complete':False,'error':type(exc).__name__+':'+str(exc),
                        'answer':None,'semantic_quality':None}
                    if not (slot/'outcome.json').exists():save(slot/'outcome.json',result)
                outcomes.append({'case_id':cid,'arm':arm,**result})
                save(dest/'progress'/f'{len(outcomes):02d}.json',{'outcomes':outcomes,
                    'accounted_new_usd':provider.spent,'dispatch_stop':provider.dispatch_stop})
                print('WHOLE_DOCUMENT_SLOT_FINISHED',cid,arm,json.dumps(result),flush=True)
        finally:
            done={(o['case_id'],o['arm']) for o in outcomes}
            save(dest/'summary.json',{'outcomes':outcomes,
                'unrun_slots':[{'case_id':c,'arm':a} for c,a in schedule if (c,a) not in done],
                'denominator_per_arm':len(cfg['cases']),'new_accounted_usd':provider.spent,
                'new_confirmed_usage_cost_usd':sum(r.get('known_cost_usd',0) or 0 for r in provider.receipts),
                'unknown_usage_reserves':provider.unknown_requests,'physical_calls':len(provider.receipts),
                'elapsed_seconds':time.monotonic()-start,'semantic_quality':None,
                'baseline_run':False,'full_C_run':False,'no_semantic_reruns':True})
            verify()


if __name__=='__main__':main()
