"""One bounded repair/criticism per old part and one complete final per judgment.

No training, reference leakage, retries, resume of the old queue or publication.
First execute the most affected judgment, then the other two development cases.
"""
import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from legal_bench.proof_carrying import source_repair_v20_6 as repair
from legal_bench.proof_carrying import shared_sources_v20_3 as shared
from legal_bench.proof_carrying import local_pipeline_v19_8 as core
from legal_bench.proof_carrying import evidence_binding_gate_v20_5 as binding
from legal_bench.proof_carrying import declared_references_v20_4 as references
from legal_bench.proof_carrying.repetition_v20_6 import duplicates
from legal_bench.proof_carrying.local_runtime_v20_6 import Runner, SETTINGS
from legal_bench.proof_carrying.artifact_state_v20_2 import immutable, byte_hash, freeze_files, verify_files

OLD = ROOT/'outputs/proof-evidence-binding-rerun-v20-5'
OUT = ROOT/'outputs/proof-source-repair-v20-6'


def read(path):
    return json.loads(Path(path).read_text())


def text(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() != value:
        raise ValueError('IMMUTABLE_TEXT_CHANGED:'+str(path))
    if not path.exists():
        path.write_text(value)


def model_path():
    return (ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip()


def preserve():
    roots = [ROOT/'outputs/proof-evidence-binding-rerun-v20-5',
             ROOT/'outputs/proof-evidence-binding-v20-5',
             ROOT/'outputs/proof-evidence-binding-acceptance-v20-5-1',
             ROOT/'outputs/proof-source-verification-v20/continuation-01']
    files = [p for root in roots for p in root.rglob('*') if p.is_file()]
    immutable(OUT/'preserved-input-files.json', {
        p.relative_to(ROOT).as_posix(): byte_hash(p) for p in sorted(files)})


def prepare():
    preserve()
    old_plan = read(OLD/'plan.json')
    order = [('1954254','P02'), ('1954254','P01'), ('569555','P01'), ('1187427','P01')]
    plan = {'version': repair.VERSION, 'cases': ['1954254','569555','1187427'],
        'tasks': [], 'max_repair_tokens': 16384, 'max_critique_tokens': 16384,
        'max_final_tokens': 8192, 'per_call_seconds': 3600,
        'total_generation_seconds': 10800, 'attempts_per_task': 1,
        'maximum_calls': 11, 'old_queue_stays_paused': True,
        'reference_used': False, 'training': False, 'commit_or_push': False,
        'purpose': 'Exposed development repair and complete-answer verification, not a research comparison.'}
    prepared = []
    for cid, pid in order:
        slot = next(x for x in old_plan['tasks'] if x['case_id'] == cid and x['part']['id'] == pid)
        original_fixture = read(OLD/'preparation'/cid/pid/'fixture.json')
        rules, changes = repair.corrected_rules(original_fixture['rules'])
        previous = read(OLD/'local'/cid/pid/'expanded.json')
        task = repair.repair_task(original_fixture['case'], rules, slot['part'], previous)
        dest = OUT/'preparation'/cid/pid
        immutable(dest/'task.json', task)
        immutable(dest/'rule-category-corrections.json', changes)
        text(dest/'prompt.txt', task['prompt'])
        immutable(dest/'schema.json', task['schema'])
        prepared += [p.relative_to(ROOT).as_posix() for p in dest.iterdir() if p.is_file()]
        plan['tasks'].append({'case_id': cid, 'part': slot['part']})
    immutable(OUT/'plan.json', plan)
    prepared.append((OUT/'plan.json').relative_to(ROOT).as_posix())
    frozen = freeze_files(ROOT, OUT,
        ['scripts/proof_source_repair_v20_6.py','legal_bench/proof_carrying/local_runtime_v20_6.py'], prepared)
    immutable(OUT/'freeze/protocol.json', frozen)
    print('PREPARED', len(plan['tasks']), 'repair parts; max 11 calls, no retries', flush=True)


def remaining(beginning, plan):
    seconds = plan['total_generation_seconds']-(time.monotonic()-beginning)
    if seconds <= 0:
        raise TimeoutError('BOUNDED_GENERATION_TIME_USED')
    if (OUT/'PAUSE_REQUESTED.json').exists():
        raise KeyboardInterrupt('OWN_REPAIR_PAUSE_REQUESTED')
    return min(plan['per_call_seconds'], seconds)


def run():
    plan = read(OUT/'plan.json')
    verify_files(ROOT, read(OUT/'freeze/protocol.json'))
    runner = Runner(model_path())
    beginning = time.monotonic()
    statuses = []
    for cid in plan['cases']:
        slots = [x for x in plan['tasks'] if x['case_id'] == cid]
        applied = []
        case = None
        full_rules = None
        for slot in slots:
            part = slot['part']['id']
            task = read(OUT/'preparation'/cid/part/'task.json')
            print('REPAIR_TASK', cid, part, flush=True)
            meta = runner.run(task['prompt'], task['schema'], OUT/'local'/cid/part/'repair',
                plan['max_repair_tokens'], remaining(beginning, plan), 'FIXED')
            if meta['run_status'] != 'OK':
                statuses.append({'case_id':cid,'part':part,'stage':'REPAIR','status':meta['run_status']})
                continue
            packed = read(OUT/'local'/cid/part/'repair/parsed.json')
            raw = shared.expand(packed)
            expansion = shared.check_expansion(packed, raw, task['original_schema'])
            ref_check = references.audit(packed, task['schema'])
            repeated = duplicates(packed)
            if ref_check['violations'] or repeated:
                raise ValueError('REPAIRED_OUTPUT_STRUCTURAL_REJECTION')
            immutable(OUT/'local'/cid/part/'replacement.json',raw)
            immutable(OUT/'local'/cid/part/'transport-check.json', {
                'expansion': expansion, 'references': ref_check, 'duplicates': repeated})
            critique = repair.critique_task(task['case'],task['rules'],raw)
            immutable(OUT/'local'/cid/part/'critique-task.json',critique)
            print('CRITIQUE_TASK',cid,part,len(critique['claims']),flush=True)
            review = runner.run(critique['prompt'],critique['schema'], OUT/'local'/cid/part/'critique',
                plan['max_critique_tokens'], remaining(beginning, plan), 'FIXED')
            if review['run_status'] != 'OK':
                statuses.append({'case_id':cid,'part':part,'stage':'CRITIQUE','status':review['run_status']})
                continue
            result = repair.apply_critique(task['case'],task['rules'],raw,critique,
                read(OUT/'local'/cid/part/'critique/parsed.json'))
            immutable(OUT/'local'/cid/part/'application.json',result)
            applied.append((part,result))
            case = task['case']
            fixture = read(OLD/'preparation'/cid/part/'fixture.json')
            full_rules,_ = repair.corrected_rules(fixture['rules'])
            immutable(OUT/'local'/cid/part/'part-summary.json', {
                'analysis': {k:u['analysis_status'] for k,u in raw['analyses'].items()},
                'decisions':result['decision_counts'], 'changes':len(result['application_ledger']),
                'independent_check':result['independent']['status'],
                'original_replacement_preserved':True, 'semantic_approval':False})
            print('PART_APPLIED',cid,part,compact_summary(result),flush=True)
        if len(applied) != len(slots):
            statuses.append({'case_id':cid,'stage':'FINAL','status':'DEPENDENCY_FAILED','answer':None})
            continue
        selected_ids={r for slot in slots for r in slot['part']['rule_ids']}
        rules=[r for r in full_rules if r['id'] in selected_ids]
        merged=repair.merge_applied(case,rules,applied)
        immutable(OUT/'final'/cid/'recomputed.json',merged)
        final=repair.final_task(case,full_rules,merged,applied)
        immutable(OUT/'final'/cid/'task.json',final)
        print('FINAL_TASK',cid,flush=True)
        meta=runner.run(final['prompt'],final['schema'],OUT/'final'/cid/'generation',
            plan['max_final_tokens'],remaining(beginning,plan),'FIXED')
        raw_text=(OUT/'final'/cid/'generation/raw-response.txt').read_text() if (OUT/'final'/cid/'generation/raw-response.txt').exists() else ''
        accepted=core.accept_final(final,raw_text,meta['run_status'])
        if accepted.get('answer') is not None and duplicates(accepted['answer']):
            accepted.update(answer=None,contract_status='FINAL_REPETITION_REJECTED')
        immutable(OUT/'final'/cid/'formal-answer.json',accepted)
        statuses.append({'case_id':cid,'stage':'FINAL','status':accepted.get('contract_status',meta['run_status']),
            'output_tokens':meta.get('output_tokens'), 'answer_available':accepted.get('answer') is not None})
        print('CASE_FINISHED',cid,statuses[-1],flush=True)
        immutable(OUT/'final'/cid/'case-run-status.json',statuses[-1])
    immutable(OUT/'run-summary.json',{'version':repair.VERSION,'statuses':statuses,
        'elapsed_seconds':time.monotonic()-beginning,'source_review':'NOT_YET_ASSISTANT_AUDITED',
        'training':False,'old_queue_stays_paused':True})
    print('BOUNDED_REPAIR_BATCH_FINISHED',flush=True)


def compact_summary(result):
    return json.dumps({'decisions':result['decision_counts'],
        'verification':result['pool']['verification_coverage'],
        'independent':result['independent']['status']},separators=(',',':'))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','run'])
    args=parser.parse_args()
    (prepare if args.action=='prepare' else run)()


if __name__ == '__main__':
    main()
