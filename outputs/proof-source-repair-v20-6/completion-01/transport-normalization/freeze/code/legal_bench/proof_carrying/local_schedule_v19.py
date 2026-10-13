"""Versioned checkpoints and safe saved-task boundaries; no retry of uncertain submission."""
import json,datetime,os,traceback
from pathlib import Path
from .local_schedule_v18 import append,paused

def state(dest):
    d=Path(dest)
    if (d/'run.json').exists():
        r=json.loads((d/'run.json').read_text());s=r['run_status']
        return 'COMPLETED' if s=='OK' else 'SKIPPED_DEPENDENCY' if s.startswith('SKIPPED') else 'PAUSED' if s=='PAUSED' else 'ACTUAL_TECHNICAL_FAILURE'
    return 'SUBMITTED_UNCERTAIN' if (d/'start.json').exists() else 'NOT_STARTED'

def checkpoint(root,name,value):
    d=Path(root)/'checkpoints'/name;d.mkdir(parents=True,exist_ok=True)
    body=json.dumps(value,sort_keys=True,ensure_ascii=False,indent=2)+'\n'
    paths=sorted(d.glob('v*.json'))
    if paths and paths[-1].read_text()==body:return paths[-1]
    p=d/('v%06d.json'%(len(paths)+1));p.write_text(body)
    latest=d/'latest.json';tmp=d/'latest.tmp';tmp.write_text(json.dumps({'path':p.name})+'\n');os.replace(tmp,latest)
    return p

def run(root,slots,perform,after=None):
    root=Path(root)
    for slot in slots:
        if paused(root):append(root,{'event':'PAUSED_BEFORE_NEXT_TASK','next_slot':slot});return 'PAUSED'
        dest=root/slot['dest'];ss=state(dest)
        if ss not in ('NOT_STARTED','SUBMITTED_UNCERTAIN'):continue
        if ss=='SUBMITTED_UNCERTAIN':append(root,{'event':'UNCERTAIN_NOT_RESUBMITTED','slot':slot});return 'SUBMITTED_UNCERTAIN'
        append(root,{'event':'DISPATCH','slot':slot})
        try:result=perform(slot,dest)
        except Exception as exc:
            dest.mkdir(parents=True,exist_ok=True);result={'run_status':'FRAMEWORK_ENTRY_FAILURE','answer':None,'error':repr(exc),'failure_stage':'ENTRY_OR_SAVE','traceback':traceback.format_exc()}
            if not (dest/'run.json').exists():(dest/'run.json').write_text(json.dumps(result,indent=2)+'\n')
            if not (dest/'formal-answer.json').exists():(dest/'formal-answer.json').write_text(json.dumps({'answer':None,'status':'FRAMEWORK_ENTRY_FAILURE'})+'\n')
            append(root,{'event':'ENTRY_FAILURE_STOP','slot':slot});return 'STOPPED'
        if not all((dest/k).exists() for k in ('run.json','formal-answer.json')):raise RuntimeError('RESULT_NOT_SAVED_BEFORE_NEXT_TASK')
        if (dest/'start.json').exists() and not all((dest/k).exists() for k in ('raw-response.txt','token-ids.json')) and result['run_status'] not in ('INPUT_TOO_LONG','UNSUPPORTED'):raise RuntimeError('RAW_OR_IDS_NOT_SAVED')
        append(root,{'event':'SAVED','slot':slot,'status':result['run_status']})
        if after and after(slot,result):return 'STOPPED_BY_FROZEN_RULE'
        if result['run_status'] in ('OUT_OF_MEMORY','UNSUPPORTED','INTERRUPTED_BY_USER_PAUSE','STAGE_BUDGET_EXHAUSTED'):return 'STOPPED'
        if paused(root):append(root,{'event':'PAUSED_AFTER_CURRENT_SAVED','slot':slot});return 'PAUSED'
    return 'FINISHED'
