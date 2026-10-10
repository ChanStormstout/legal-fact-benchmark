"""Summarize saved records only; no generation, semantic repair or legal scoring."""
import csv
import datetime as dt
import io
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from legal_bench.proof_carrying.realcase_contracts import byte_hash, read_json, write_once
from legal_bench.proof_carrying.realcase_tasks_v2_2 import CASES, KINDS

OUT = ROOT / 'outputs/proof-carrying-realcase-v2'

def main():
    calls, comparison, cases = [], [], []
    for cid in CASES:
        for kind in KINDS:
            p = OUT / 'runs' / cid / kind
            sub, end = read_json(p/'submitted.json'), read_json(p/'completed.json')
            result = read_json(p/'result.json')
            recovery = read_json(p/'transport-recovery.json') if (p/'transport-recovery.json').exists() else None
            complete = end.get('observed_complete_at', end.get('observed_completed_at'))
            start = sub['submitted_at']
            elapsed = (dt.datetime.fromisoformat(complete.replace('Z','+00:00')) - dt.datetime.fromisoformat(start.replace('Z','+00:00'))).total_seconds()
            task_path = sub.get('task_path') or str(Path('tasks-interface-02' if kind=='reference' else 'tasks')/cid/kind/'task.txt')
            task = OUT / task_path
            calls.append({'case':cid, 'task':kind, 'submitted_at':start, 'observed_complete_at':complete,
                'observed_interval_seconds':elapsed, 'interval_is_exact_inference_cost':False,
                'mode':sub.get('visible_mode',sub.get('mode_visible',sub.get('mode'))), 'exact_model':None, 'tokens':None, 'inference_seconds':None,
                'url':end['url'], 'task_path':task_path, 'task_sha256':byte_hash(task),
                'task_bytes':task.stat().st_size, 'task_characters':len(task.read_text()),
                'submission_text_sha256':byte_hash(p/'submission-text.txt') if (p/'submission-text.txt').exists() else None,
                'raw_sha256':byte_hash(p/'raw-response.txt'), 'parsed_sha256':byte_hash(p/'parsed.json'),
                'original_import_status':result['status'],
                'effective_import_status':'OK_VISIBLE_SOURCE_RECOVERY' if recovery else result['status'],
                'transport_recovery_record':str((p/'transport-recovery.json').relative_to(OUT)) if recovery else None})
        facts = read_json(OUT/'runs'/cid/'facts/parsed.json')
        rules = read_json(OUT/'runs'/cid/'rules/parsed.json')
        ref = read_json(OUT/'runs'/cid/'reference/parsed.json')
        for version in ('S1','S2'):
            p = OUT/'cases'/cid/'runs'/version
            if not (p/'check.json').exists(): continue
            check, cert = read_json(p/'check.json'),read_json(p/'certificate.json')
            proposals = {q['id']:q for q in cert['proposal']['requests']}
            cases.append({'case':cid,'snapshot':version,'rules':len(rules['rules']),
                'premises':len(facts['premises']),'reference_propositions':len(ref['judgments']),
                'step_statuses':dict(Counter(s['status'] for s in check['steps'].values())),
                'request_statuses':dict(Counter(q['draft_status'] for q in check['requests'])),
                'formal_legal_approval':False,
                'is_original_model_proposal':version=='S1'})
            for q in check['requests']:
                comparison.append({'case':cid,'snapshot':version,'request':q['id'],
                    'proposal_state':proposals[q['id']]['proposed_state'],
                    'checked_trace_status':q['draft_status'],'checked_answer':q.get('answer'),
                    'predicate':q.get('predicate'),'errors':';'.join(q.get('errors',[])),
                    'gaps':';'.join(q.get('gaps',[])),'legal_status':q['formal_status'],
                    'not_a_legal_correctness_score':True})
    write_once(OUT/'run-index.json',{'calls':calls,'count':len(calls),'semantic_retries':0,
        'total_task_bytes':sum(c['task_bytes'] for c in calls),
        'sum_observed_intervals_seconds':sum(c['observed_interval_seconds'] for c in calls),
        'cost_limit':'Observed intervals include UI, queue and collection delay and overlap. They are not exact generation time or additive wall-clock work.'})
    write_once(OUT/'case-summary.json',cases)
    write_once(OUT/'before-after.json',{'interpretation':'Same cached proposal under same source/review policy. INVALID is a credential result, not necessarily a wrong legal conclusion. S2 is a separately marked maintainer correction.','requests':comparison})
    buf=io.StringIO();w=csv.DictWriter(buf,fieldnames=list(comparison[0]));w.writeheader();w.writerows(comparison)
    with (OUT/'before-after.csv').open('x') as f:f.write(buf.getvalue())
    print(json.dumps({'calls':len(calls),'case_versions':cases},indent=2))

if __name__=='__main__': main()
