"""Audited source-completion replay, preserving old generations and rejections."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.proof_final_bindings_v20_8 import OUT as BASE, inputs, read, verify as verify_base
from legal_bench.proof_carrying import final_statement_review_v20_9_1 as core
from legal_bench.proof_carrying import final_statement_pack_v20_9 as pack_core
from legal_bench.proof_carrying.artifact_state_v20_2 import immutable, freeze_files, verify_files, digest

OLD = BASE / 'statement-pack-01'
OUT = BASE / 'statement-pack-03'
FILES = ['scripts/proof_final_statement_completion_v20_9_2.py',
         'legal_bench/proof_carrying/final_statement_review_v20_9_1.py',
         'legal_bench/proof_carrying/final_statement_pack_v20_9.py']


def extend_order(old_pack, new_pack, old_plan):
    """Only append newly reviewed limitations; never relabel an old generation."""
    before, after = old_pack['records'], new_pack['records']
    if after[:len(before)] != before or len(after) <= len(before):
        raise ValueError('REPLAY_OLD_STATEMENTS_CHANGED_OR_NO_ADDITION')
    old_ids = [r['id'] for r in before]
    order = old_plan['record_order']
    if len(order) != len(old_ids) or set(order) != set(old_ids):
        raise ValueError('REPLAY_OLD_PLAN_NOT_COMPLETE_AND_UNIQUE')
    added = after[len(before):]
    if any(r['section'] != 'LIMITATION' for r in added):
        raise ValueError('REPLAY_ADDITIONS_MUST_BE_SOURCE_REVIEWED_LIMITATIONS')
    ids = old_ids + [r['id'] for r in added]
    if len(ids) != len(set(ids)):
        raise ValueError('REPLAY_ADDITION_ID_COLLISION')
    return {'record_order': order + [r['id'] for r in added]}


def replay_569():
    verify_base()
    cid = '569555'
    d = OUT / 'cases' / cid
    case, old, _, _ = inputs(cid)
    bridge = read(BASE / 'cases' / cid / 'bridge.json')
    frame, pack = read(d / 'frame-proposal.json'), read(d / 'proposal.json')
    reviews = read(d / 'combined-source-review.json')
    fr, pr = reviews['frame_review'], reviews['pack_review']
    # final_task validates both exact source-review schemas and every binding.
    task = core.final_task(case, old, bridge, frame, fr, pack, pr)
    previous = read(OLD / 'cases' / cid / 'task.json')
    original_plan = read(OLD / 'cases' / cid / 'generation/parsed.json')
    pack_core.render(previous, original_plan, case)
    plan = extend_order(previous['pack'], pack, original_plan)
    old_frame = previous['frame']
    expected_frame = json.loads(json.dumps(old_frame))
    expected_frame['events'][2]['affected_actor_ids'] = [a['id'] for a in frame['actors'][:3]]
    if 'IK-569555:L311' not in expected_frame['events'][2]['refs']:
        expected_frame['events'][2]['refs'].append('IK-569555:L311')
    if expected_frame != frame:
        raise ValueError('REPLAY_UNAUDITED_FRAME_CHANGE')
    receipt = {
        'actual_new_api_model_calls': 0,
        'method': 'DETERMINISTIC_SOURCE_COMPLETION_REPLAY_NOT_NEW_MODEL_GENERATION',
        'old_generation': str((OLD / 'cases' / cid / 'generation/run.json').relative_to(ROOT)),
        'original_model_plan_sha256': digest(original_plan),
        'all_original_22_statement_records_unchanged': True,
        'original_model_order_prefix_unchanged': True,
        'added_mandatory_source_reviewed_limitations': [r['id'] for r in pack['records'][22:]],
        'frame_delta': 'E03 affected actors now include Association; added source L311',
        'fresh_frame_review_sha256': digest(fr),
        'fresh_pack_review_sha256': digest(pr),
        'old_task_sha256': previous['input_sha256'],
        'new_task_sha256': task['input_sha256'],
        'source_input_unchanged': previous['source_sha256'] == task['source_sha256'],
    }
    for name, value in [('source.json', case), ('task.json', task), ('ordering-plan.json', plan),
                        ('frame-review/parsed.json', fr), ('source-review/parsed.json', pr),
                        ('replay-receipt.json', receipt),
                        ('rendered-candidate.json', core.render(task, plan, case))]:
        immutable(d / name, value)
    rt = core.review_task(task, plan, case)
    immutable(d / 'whole-answer-review/task.json', rt)
    prompt = d / 'whole-answer-review/prompt.txt'
    if prompt.exists() and prompt.read_text() != rt['prompt']:
        raise ValueError('REVIEW_PROMPT_CHANGED')
    if not prompt.exists():
        prompt.write_text(rt['prompt'])
    prepared = [str(p.relative_to(ROOT)) for p in d.rglob('*.json') if 'freeze' not in p.parts]
    prepared.append(str(prompt.relative_to(ROOT)))
    immutable(d / 'freeze/protocol.json', freeze_files(ROOT, d, FILES, prepared))
    print(cid, 'EXACT_REVIEW_READY', len(rt['units']), len(rt['prompt']))


def verify_569():
    verify_base()
    d = OUT / 'cases/569555'
    verify_files(ROOT, read(d / 'freeze/protocol.json'))
    core.verify_task(read(d / 'task.json'), read(d / 'source.json'))


def accept_569(path):
    verify_569()
    d = OUT / 'cases/569555'
    review = read(path)
    result = core.accept_final(read(d / 'task.json'), json.dumps(read(d / 'ordering-plan.json')),
                               'OK', case=read(d / 'source.json'), review=review)
    immutable(d / 'whole-answer-review/parsed.json', review)
    immutable(d / 'final-acceptance.json', result)
    print('569555', result['contract_status'], result.get('source_review_issues'))


def accept_corrected_195(path):
    """A reviewer-generated metadata correction cannot change source verdicts."""
    from scripts.proof_final_statement_pack_v20_9 import verify
    verify('1954254')
    d = OLD / 'cases/1954254'
    original = read(d / 'whole-answer-review/web-response.json')
    corrected = read(path)
    keys = ('version', 'task_sha256', 'candidate_sha256', 'source_sha256', 'registry_sha256', 'rule_sha256')
    if {k:v for k,v in original.items() if k not in keys} != {k:v for k,v in corrected.items() if k not in keys}:
        raise ValueError('METADATA_CORRECTION_CHANGED_SOURCE_VERDICTS')
    rt = read(d / 'whole-answer-review/task.json')
    if any(corrected.get(k) != rt['bindings'][k] for k in keys):
        raise ValueError('CORRECTED_REVIEW_BINDING_MISMATCH')
    immutable(d / 'whole-answer-review/web-response-corrected.json', corrected)
    immutable(d / 'whole-answer-review/metadata-correction-receipt.json', {
        'reviewer_used_python_to_merge_schema_enum_values': True,
        'source_verdicts_and_coverage_unchanged': True,
        'actual_new_api_model_calls': 0,
        'changed_fields': [k for k in keys if original[k] != corrected[k]],
        'original_review_sha256': digest(original), 'corrected_review_sha256': digest(corrected),
        'original_rejected_acceptance_preserved': True,
    })
    result = pack_core.accept_final(read(d / 'task.json'), (d / 'generation/raw-response.txt').read_text(),
                                   read(d / 'generation/run.json')['run_status'],
                                   case=read(d / 'source.json'), review=corrected)
    immutable(d / 'final-acceptance-corrected.json', result)
    print('1954254', result['contract_status'], result.get('source_review_issues'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('replay569', 'verify569', 'accept569', 'correct195'))
    p.add_argument('--review')
    a = p.parse_args()
    if a.action == 'replay569': replay_569()
    elif a.action == 'verify569': verify_569(); print('VERIFIED')
    elif not a.review: p.error('--review required')
    elif a.action == 'accept569': accept_569(a.review)
    else: accept_corrected_195(a.review)
