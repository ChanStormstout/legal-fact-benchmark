"""Bounded V20.7 real final attempts; no training, retries or old-queue resume."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from legal_bench.proof_carrying import final_source_guard_v20_7 as guard
from legal_bench.proof_carrying import source_repair_v20_6_6 as prior
from legal_bench.proof_carrying.artifact_state_v20_2 import immutable, byte_hash, freeze_files, verify_files
from legal_bench.proof_carrying.provider_runtime_v20_6_1 import Runner

OUT = ROOT/'outputs/proof-final-source-guard-v20-7/real-acceptance-01'
VALIDATED = OUT.parent/'validated-01'
PARENT = ROOT/'outputs/proof-source-repair-v20-6/completion-01'
OLD = ROOT/'outputs/proof-evidence-binding-rerun-v20-5'
CASES = ('1954254', '569555', '1187427')


def read(path):
    return guard.loads(Path(path).read_text())


def remaining():
    budget = read(OUT/'budget-before.json')
    return budget['maximum_total_cost_usd'] - budget['prior_cost_or_bound_usd']


def prepare_case(cid):
    dest = OUT/'cases'/cid
    if (VALIDATED/'cases'/cid/'task.json').exists():
        case = read(VALIDATED/'cases'/cid/'source.json')
        task = read(VALIDATED/'cases'/cid/'task.json')
    elif (OUT/'recovered-review'/cid/'parsed.json').exists():
        part = 'P01'
        original = read(PARENT/'preparation'/cid/part/'task.json')
        case = original['case']
        review = read(OUT/'recovered-review'/cid/'parsed.json')
        local = PARENT/'local'/cid/part
        applied = prior.apply_critique(case, original['rules'], read(local/'replacement.json'),
            read(local/'critique-task.json'), review['parts'][part])
        immutable(dest/'application.json', applied)
        full_rules, _ = prior.corrected_rules(read(OLD/'preparation'/cid/part/'fixture.json')['rules'])
        selected = {r['id'] for r in original['rules']}
        merged = prior.merge_applied(case, [r for r in full_rules if r['id'] in selected], [(part, applied)])
        immutable(dest/'recomputed.json', merged)
        task = guard.final_task(case, full_rules, merged, [(part, applied)])
    else:
        immutable(dest/'waiting-before-source-review.json', {
            'case_id': cid, 'status': 'WAITING_SAVED_SOURCE_REVIEW', 'dispatched': False})
        return False
    guard.verify_task(task, case)
    immutable(dest/'source.json', case)
    immutable(dest/'task.json', task)
    paths = [str(p.relative_to(ROOT)) for p in dest.glob('*.json') if p.name != 'waiting-before-source-review.json']
    manifest = freeze_files(ROOT, dest, ['scripts/proof_final_acceptance_v20_7.py'], paths)
    immutable(dest/'freeze/protocol.json', manifest)
    return True


def prepare():
    verify_files(ROOT, read(VALIDATED/'freeze/protocol.json'))
    client = Runner(out=OUT, maximum_cost_usd=remaining())
    provider = read(OUT/'provider-model.json')['model']
    budget = read(OUT/'budget-before.json')
    plan = {'version': 'V20_7_REAL_FINAL_ACCEPTANCE_01', 'cases': list(CASES),
            'generation_model': provider['id'], 'service_context_length': provider['context_length'],
            'final_tokens': 16384, 'seconds_per_call': 900, 'attempts_per_case': 1,
            'new_maximum_generations': 3, 'maximum_total_cost_usd': budget['maximum_total_cost_usd'],
            'prior_cost_or_bound_usd': budget['prior_cost_or_bound_usd'], 'remaining_budget_usd': remaining(),
            'source_reviewer': 'GPT-6 via ChatGPT Web; not human gold',
            'no_input_cuts': True, 'old_queue_stays_paused': True,
            'training': False, 'commit_or_push': False, 'failure_or_missing_review_is_not_success': True}
    immutable(OUT/'plan.json', plan)
    paths = [str((OUT/p).relative_to(ROOT)) for p in ('plan.json','budget-before.json','provider-model.json')]
    immutable(OUT/'freeze/protocol.json', freeze_files(ROOT, OUT, ['scripts/proof_final_acceptance_v20_7.py'], paths))
    ready = [cid for cid in CASES if prepare_case(cid)]
    print(json.dumps({'ready': ready, 'remaining_budget_usd': remaining(),
                      'live_service_context': provider['context_length'], 'generations': 0}))


def verify():
    verify_files(ROOT, read(OUT/'freeze/protocol.json'))
    for snapshot in [OUT/'preserved-before.json', OUT.parent/'preserved-before.json']:
        changed = [p for p,h in read(snapshot)['files'].items()
                   if not (ROOT/p).is_file() or byte_hash(ROOT/p) != h]
        if changed:
            raise ValueError('PROTECTED_FILES_CHANGED:' + ','.join(changed))


def generate(cid):
    verify()
    dest = OUT/'cases'/cid
    if not (dest/'task.json').exists():
        if not prepare_case(cid):
            print('WAITING_SAVED_SOURCE_REVIEW; NO_GENERATION')
            return
    verify_files(ROOT, read(dest/'freeze/protocol.json'))
    task, case = read(dest/'task.json'), read(dest/'source.json')
    guard.verify_task(task, case)
    plan = read(OUT/'plan.json')
    client = Runner(out=OUT, maximum_cost_usd=remaining())
    result = client.run(task['prompt'], task['schema'], dest/'generation',
                        plan['final_tokens'], plan['seconds_per_call'])
    raw_path = dest/'generation/raw-response.txt'
    accepted = guard.accept_final(task, raw_path.read_text() if raw_path.exists() else '',
                                  result['run_status'], case=case)
    immutable(dest/'pre-review-acceptance.json', accepted)
    if result['run_status'] == 'OK' and accepted.get('candidate_check', {}).get('status') == 'OK':
        packet = guard.review_task(task, guard.loads(raw_path.read_text()), case)
        immutable(dest/'whole-answer-review/task.json', packet)
    print(json.dumps({'case_id': cid, 'generation': result['run_status'],
                      'contract': accepted['contract_status'], 'answer_accepted': accepted['answer'] is not None,
                      'cost': result.get('listed_price_token_cost_usd')}, ensure_ascii=False))


def accept(cid, review_path):
    verify()
    dest = OUT/'cases'/cid
    verify_files(ROOT, read(dest/'freeze/protocol.json'))
    run = read(dest/'generation/run.json')
    review_raw = Path(review_path).read_text()
    immutable(dest/'whole-answer-review/parsed.json', guard.loads(review_raw))
    value = guard.accept_final(read(dest/'task.json'), (dest/'generation/raw-response.txt').read_text(),
                              run['run_status'], case=read(dest/'source.json'), review=review_raw)
    immutable(dest/'final-acceptance.json', value)
    print(value['contract_status'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'generate', 'accept', 'verify'))
    parser.add_argument('--case-id', choices=CASES)
    parser.add_argument('--review')
    args = parser.parse_args()
    if args.action == 'prepare': prepare()
    elif args.action == 'verify': verify(); print('VERIFIED')
    elif not args.case_id: parser.error('--case-id is required')
    elif args.action == 'generate': generate(args.case_id)
    elif not args.review: parser.error('--review is required')
    else: accept(args.case_id, args.review)
