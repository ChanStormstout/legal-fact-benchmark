"""Immutable per-attempt slots; pause check before and after every saved task."""
import json
from pathlib import Path
import datetime

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
        result=perform(slot,dest)
        # perform must save its results before returning; no new dispatch otherwise.
        if not (dest/'run.json').exists():raise RuntimeError('RESULT_NOT_SAVED_BEFORE_NEXT_TASK')
        append(root,{'event':'SAVED','slot':slot,'status':result['run_status']})
        if result['run_status'] in ('OUT_OF_MEMORY','UNSUPPORTED','INTERRUPTED_BY_USER_PAUSE'):
            append(root,{'event':'RESOURCE_OR_INTERRUPTION_STOP','slot':slot});return 'STOPPED'
        if paused(root):append(root,{'event':'PAUSED_AFTER_CURRENT_SAVED','slot':slot});return 'PAUSED'
    return 'FINISHED'
