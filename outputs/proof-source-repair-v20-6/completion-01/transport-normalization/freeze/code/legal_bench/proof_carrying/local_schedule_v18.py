"""Immutable per-attempt slots; pause check before and after every saved task."""
import json
from pathlib import Path
import datetime,traceback

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def append(root,event):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    with (root/'call-ledger.jsonl').open('a') as f:f.write(json.dumps({'at':now(),**event})+'\n');f.flush()
def paused(root):return (Path(root)/'PAUSE_REQUESTED.json').exists()
def run(root,slots,perform):
    root=Path(root)
    for slot in slots:
        if paused(root):append(root,{'event':'PAUSED_BEFORE_NEXT_TASK','next_slot':slot});return 'PAUSED'
        dest=root/slot['dest']
        if (dest/'run.json').exists():continue
        if (dest/'start.json').exists():append(root,{'event':'INCOMPLETE_ATTEMPT_NOT_RETRIED','slot':slot});continue
        append(root,{'event':'DISPATCH','slot':slot})
        try:result=perform(slot,dest)
        except Exception as exc:
            dest.mkdir(parents=True,exist_ok=True)
            result={'run_status':'FRAMEWORK_ENTRY_FAILURE','answer':None,'error':repr(exc),'traceback':traceback.format_exc(),'stage':'ENTRY_OR_SAVE'}
            if not (dest/'run.json').exists():(dest/'run.json').write_text(json.dumps(result,indent=2)+'\n')
            if not (dest/'formal-answer.json').exists():(dest/'formal-answer.json').write_text(json.dumps({'answer':None,'status':'FRAMEWORK_ENTRY_FAILURE'})+'\n')
            append(root,{'event':'ENTRY_FAILURE_STOP','slot':slot,'error':repr(exc)})
            return 'STOPPED'
        # perform must save its results before returning; no new dispatch otherwise.
        if not (dest/'run.json').exists():raise RuntimeError('RESULT_NOT_SAVED_BEFORE_NEXT_TASK')
        append(root,{'event':'SAVED','slot':slot,'status':result['run_status']})
        if result['run_status'] in ('OUT_OF_MEMORY','UNSUPPORTED','INTERRUPTED_BY_USER_PAUSE'):
            append(root,{'event':'RESOURCE_OR_INTERRUPTION_STOP','slot':slot});return 'STOPPED'
        if paused(root):append(root,{'event':'PAUSED_AFTER_CURRENT_SAVED','slot':slot});return 'PAUSED'
    return 'FINISHED'
