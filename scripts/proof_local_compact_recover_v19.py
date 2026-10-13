"""Explicit one-window recovery; saved boundaries and inherited guard state."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import proof_local_compact_v19 as entry
from legal_bench.proof_carrying.local_schedule_v19 import run as saved_schedule
from legal_bench.proof_carrying.local_checker_v19_refs import check

def observed():
    cfg=entry.protocol();reg=entry.read(entry.OUT/'startup/window-preregistration.json')['tasks']
    carried={x['dest'] for x in cfg['carried_cost']['calls']}
    order=reg+[s for s in cfg['local_generation_slots'] if s['role']=='P' and s['dest'] not in {x['dest'] for x in reg} and s['dest'] not in carried]
    completed=[]
    for slot in order:
        d=entry.OUT/slot['dest']
        if not (d/'run.json').exists():continue
        r=entry.read(d/'run.json');completed.append({'dest':slot['dest'],**{k:r.get(k) for k in ['run_status','output_tokens','elapsed_seconds','record_guard','repetition_guard']}})
    consecutive=0;trigger=None
    for row in completed:
        consecutive=consecutive+1 if row['run_status'] in ('OUTPUT_TRUNCATED','REPETITION_ABORT') else 0
        if consecutive>=2:trigger=row['dest'];break
    return {'new_calls':len(completed),'rows':completed,'rolling_stop':bool(trigger),'trigger':trigger,
            'P_seconds_used':cfg['carried_cost']['P_seconds']+sum(x['elapsed_seconds'] or 0 for x in completed),
            'historical_failures':6,'history_not_cleared':True}

def inspect_saved(slot,result):
    f=entry.fixture(slot['case_id']);d=entry.OUT/slot['dest']
    if result['run_status']=='OK':
        raw=entry.read(d/'parsed.json');view={**f['case'],'segments':[x for x in f['case']['segments'] if x['id'] in slot['part']['source_ids']]}
        p,ledger=entry.pipe.convert(raw,view,entry.pipe.VERSION)
        imported=entry.pipe.independent_import(raw,p,view,entry.pipe.VERSION)
        merged,_=entry.pipe.merge_parts([(slot['part']['id'],p)])
        audit=entry.pipe.apply_connection_decisions(f['case'],f['rules'],merged)
        checked=check(f['case'],f['rules'],merged,None,audit)
        entry.save(d/'saved-entry-audit.json',{'import':imported,'independent':checked,'checks':audit,
            'raw_records':sum(len(u['records']) for u in raw['analyses']),
            'raw_uses':sum(len(u['uses']) for u in raw['analyses']),
            'mapped_original_fragments':sum(len(r['restored_source']) for u in p['analyses'] for r in u['records'])})
        if imported['status']!='OK' or checked['status']!='OK':
            entry.save(entry.OUT/'PAUSE_REQUESTED.json',{'reason':'COMMON_ENTRY_MISMATCH','dest':slot['dest']});return True
    snapshot=observed();entry.checkpoint(entry.OUT,'recovery-monitor',snapshot)
    if snapshot['rolling_stop']:
        entry.save(entry.OUT/'PAUSE_REQUESTED.json',{'reason':'TWO_CONSECUTIVE_NEW_WINDOW_FLOW_FAILURES','dest':slot['dest'],'history_preserved':True});return True
    return False

def run(phase):
    entry.assert_frozen();tasks=entry.read(entry.OUT/'startup/window-preregistration.json')['tasks']
    if phase=='window':
        def window_schedule(root,slots,perform,after=None):return saved_schedule(root,tasks,perform,after=inspect_saved)
        entry.schedule=window_schedule
    elif phase=='P':
        review=entry.read(entry.OUT/'engineering/window-source-review.json')
        if not review['production_resume_permitted']:raise ValueError('WINDOW_SOURCE_GATE_NOT_PASSED')
        entry.schedule=lambda root,slots,perform,after=None:saved_schedule(root,slots,perform,after=inspect_saved)
    else:raise ValueError('Unknown phase')
    result=entry.run_local('P');snapshot=observed()
    entry.checkpoint(entry.OUT,'window-result' if phase=='window' else 'production-result',{'status':result,**snapshot})
    print(json.dumps({'phase':phase,'status':result,**snapshot},indent=2),flush=True)

if __name__=='__main__':run(sys.argv[1])
