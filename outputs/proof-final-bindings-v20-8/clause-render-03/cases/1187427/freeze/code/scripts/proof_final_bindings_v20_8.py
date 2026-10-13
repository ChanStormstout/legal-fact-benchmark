"""Isolated cache replay and bounded final-writing experiments, no training/push."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from legal_bench.proof_carrying import final_bindings_v20_8 as core
from legal_bench.proof_carrying import final_source_guard_v20_7 as previous
from legal_bench.proof_carrying.artifact_state_v20_2 import immutable, byte_hash, freeze_files, verify_files
from legal_bench.proof_carrying.provider_runtime_v20_6_1 import Runner

OUT = ROOT / 'outputs/proof-final-bindings-v20-8'
OLD = ROOT / 'outputs/proof-final-source-guard-v20-7'
CASES = ('1954254', '569555', '1187427')
FILES = ['legal_bench/proof_carrying/final_bindings_v20_8.py',
         'scripts/proof_final_bindings_v20_8.py',
         'legal_bench/proof_carrying/final_source_guard_v20_7.py',
         'legal_bench/proof_carrying/provider_runtime_v20_6_1.py',
         'legal_bench/proof_carrying/schema_contract_v19_6.py']


def read(path):
    return core.loads(Path(path).read_text())


def inputs(cid):
    old = OLD / 'real-acceptance-01/cases' / cid
    cached = OLD / 'validated-01/cases' / cid
    case, task = read(old / 'source.json'), read(old / 'task.json')
    if cid == '1187427':
        merged = read(old / 'recomputed.json')
        parts = [('P01', read(old / 'application.json'))]
    else:
        merged = read(cached / 'recomputed.json')
        parts = [(p.name, read(p / 'application.json')) for p in sorted((cached / 'parts').iterdir())]
    return case, task, merged, parts


def prepare():
    # Preserve completed outputs only; the separate retrieval chat owns its files.
    paths = [p for p in OLD.rglob('*') if p.is_file()]
    immutable(OUT / 'preserved-before.json', {str(p.relative_to(ROOT)): byte_hash(p) for p in paths})
    for cid in CASES:
        case, task, merged, parts = inputs(cid)
        bridge = core.build_bridge(case, parts, merged)
        dest = OUT / 'cases' / cid
        immutable(dest / 'source.json', case)
        immutable(dest / 'bridge.json', bridge)
        frame_path = dest / 'frame-proposal.json'
        if frame_path.exists():
            rt = core.frame_review_task(case, read(frame_path), bridge)
            immutable(dest / 'frame-review/task.json', rt)
            (dest / 'frame-review/prompt.txt').write_text(rt['prompt'])
        print(json.dumps({'case': cid, 'declarations': len(bridge['declarations']),
                          'objects': len(bridge['global_positions']),
                          'claims': len(bridge['normalized_claims']), 'identity_merges': 0}))


def prepare_review(cid):
    dest = OUT / 'cases' / cid
    case = read(dest / 'source.json')
    rt = core.frame_review_task(case, read(dest / 'frame-proposal.json'), read(dest / 'bridge.json'))
    immutable(dest / 'frame-review/task.json', rt)
    (dest / 'frame-review/prompt.txt').write_text(rt['prompt'])
    print(cid, 'SOURCE_REVIEW_READY', len(rt['prompt']), len(rt['units']))


def apply_frame_review(cid, path):
    dest = OUT / 'cases' / cid
    case, old_task, _, _ = inputs(cid)
    review = read(path)
    frame, bridge = read(dest / 'frame-proposal.json'), read(dest / 'bridge.json')
    task = core.final_task(case, old_task, bridge, frame, review)
    immutable(dest / 'frame-review/parsed.json', review)
    immutable(dest / 'task.json', task)
    prepared = [str((dest / p).relative_to(ROOT)) for p in
                ('source.json', 'bridge.json', 'frame-proposal.json', 'frame-review/parsed.json', 'task.json')]
    immutable(dest / 'freeze/protocol.json', freeze_files(ROOT, dest, FILES, prepared))
    print(cid, 'TASK_READY', len(task['prompt']))


def verify():
    changed = [p for p, h in read(OUT / 'preserved-before.json').items()
               if not (ROOT / p).is_file() or byte_hash(ROOT / p) != h]
    if changed:
        raise ValueError('HISTORICAL_OUTPUT_CHANGED:' + ','.join(changed))
    for cid in CASES:
        dest = OUT / 'cases' / cid
        if (dest / 'freeze/protocol.json').exists():
            verify_files(ROOT, read(dest / 'freeze/protocol.json'))
            core.verify_task(read(dest / 'task.json'), read(dest / 'source.json'))


def generate(cid):
    verify()
    dest = OUT / 'cases' / cid
    task, case = read(dest / 'task.json'), read(dest / 'source.json')
    budget = read(OUT / 'budget.json')
    runner = Runner(out=OUT, maximum_cost_usd=budget['remaining_budget_usd'])
    run = runner.run(task['prompt'], task['schema'], dest / 'generation', 16384, 900)
    path = dest / 'generation/raw-response.txt'
    result = core.accept_final(task, path.read_text() if path.exists() else '', run['run_status'], case=case)
    immutable(dest / 'pre-review-acceptance.json', result)
    if run['run_status'] == 'OK' and result['contract_status'] == 'PENDING_WHOLE_ANSWER_SOURCE_REVIEW':
        writer = read(path)
        rendered = core.render(task, writer, case)
        immutable(dest / 'rendered-candidate.json', rendered)
        rt = core.review_task(task, writer, case)
        immutable(dest / 'whole-answer-review/task.json', rt)
        (dest / 'whole-answer-review/prompt.txt').write_text(rt['prompt'])
    print(json.dumps({'case': cid, 'technical': run['run_status'], 'contract': result['contract_status'],
                      'candidate_check': result.get('candidate_check'),
                      'cost': run.get('listed_price_token_cost_usd')}))


def accept(cid, path):
    verify()
    dest = OUT / 'cases' / cid
    run = read(dest / 'generation/run.json')
    review = read(path)
    result = core.accept_final(read(dest / 'task.json'), (dest / 'generation/raw-response.txt').read_text(),
                              run['run_status'], case=read(dest / 'source.json'), review=review)
    immutable(dest / 'whole-answer-review/parsed.json', review)
    immutable(dest / 'final-acceptance.json', result)
    print(cid, result['contract_status'], result.get('source_review_issues'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'prepare-review', 'apply-frame-review', 'generate', 'accept', 'verify'))
    p.add_argument('--case-id', choices=CASES)
    p.add_argument('--review')
    a = p.parse_args()
    if a.action == 'prepare': prepare()
    elif a.action == 'verify': verify(); print('VERIFIED')
    elif not a.case_id: p.error('--case-id required')
    elif a.action == 'prepare-review': prepare_review(a.case_id)
    elif a.action == 'generate': generate(a.case_id)
    elif not a.review: p.error('--review required')
    elif a.action == 'apply-frame-review': apply_frame_review(a.case_id, a.review)
    else: accept(a.case_id, a.review)
