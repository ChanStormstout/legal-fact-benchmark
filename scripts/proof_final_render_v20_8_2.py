"""Isolated reviewed-clause final experiment; preserves the failed free writer."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.proof_final_bindings_v20_8 import OUT as BASE, inputs, read, verify as verify_base
from legal_bench.proof_carrying import final_render_v20_8_2 as core
from legal_bench.proof_carrying.artifact_state_v20_2 import immutable, freeze_files, verify_files
from legal_bench.proof_carrying.provider_runtime_v20_6_1 import Runner

OUT = BASE / 'clause-render-03'
FILES = ['legal_bench/proof_carrying/final_render_v20_8_2.py',
         'scripts/proof_final_render_v20_8_2.py',
         'legal_bench/proof_carrying/final_bindings_v20_8.py',
         'legal_bench/proof_carrying/final_source_guard_v20_7.py',
         'legal_bench/proof_carrying/provider_runtime_v20_6_1.py',
         'legal_bench/proof_carrying/schema_contract_v19_6.py']


def prepare(cid):
    verify_base()
    case, old, _, _ = inputs(cid)
    previous = BASE / 'cases' / cid
    task = core.final_task(case, old, read(previous/'bridge.json'),
                           read(previous/'frame-proposal.json'), read(previous/'frame-review/parsed.json'))
    dest = OUT/'cases'/cid
    immutable(dest/'source.json', case)
    immutable(dest/'task.json', task)
    paths = [str((dest/p).relative_to(ROOT)) for p in ('source.json','task.json')]
    immutable(dest/'freeze/protocol.json', freeze_files(ROOT, dest, FILES, paths))
    print(cid, 'PREPARED', len(task['clauses']), 'CLAUSES', len(task['prompt']), 'INPUT_CHARS')


def verify(cid):
    verify_base()
    dest = OUT/'cases'/cid
    verify_files(ROOT, read(dest/'freeze/protocol.json'))
    core.verify_task(read(dest/'task.json'), read(dest/'source.json'))


def generate(cid):
    verify(cid)
    dest = OUT/'cases'/cid
    task, case = read(dest/'task.json'), read(dest/'source.json')
    runner = Runner(out=BASE, maximum_cost_usd=read(BASE/'budget.json')['remaining_budget_usd'])
    run = runner.run(task['prompt'], task['schema'], dest/'generation', 16384, 900)
    raw_path = dest/'generation/raw-response.txt'
    result = core.accept_final(task, raw_path.read_text() if raw_path.exists() else '', run['run_status'], case=case)
    immutable(dest/'pre-review-acceptance.json', result)
    if result['contract_status'] == 'PENDING_WHOLE_ANSWER_SOURCE_REVIEW':
        plan = read(raw_path)
        immutable(dest/'rendered-candidate.json', core.render(task, plan, case))
        rt = core.review_task(task, plan, case)
        immutable(dest/'whole-answer-review/task.json', rt)
        (dest/'whole-answer-review/prompt.txt').write_text(rt['prompt'])
    print(json.dumps({'case':cid,'technical':run['run_status'],'contract':result['contract_status'],
                      'cost':run.get('listed_price_token_cost_usd'),'check':result.get('candidate_check')}))


def accept(cid, path):
    verify(cid)
    dest = OUT/'cases'/cid
    review = read(path)
    result = core.accept_final(read(dest/'task.json'), (dest/'generation/raw-response.txt').read_text(),
                              read(dest/'generation/run.json')['run_status'], case=read(dest/'source.json'), review=review)
    immutable(dest/'whole-answer-review/parsed.json', review)
    immutable(dest/'final-acceptance.json', result)
    print(cid, result['contract_status'], result.get('source_review_issues'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare','generate','accept','verify'))
    p.add_argument('--case-id', choices=('1954254','569555','1187427'), required=True)
    p.add_argument('--review')
    a=p.parse_args()
    if a.action=='prepare':prepare(a.case_id)
    elif a.action=='generate':generate(a.case_id)
    elif a.action=='verify':verify(a.case_id);print('VERIFIED')
    elif a.review:accept(a.case_id,a.review)
    else:p.error('--review required')
