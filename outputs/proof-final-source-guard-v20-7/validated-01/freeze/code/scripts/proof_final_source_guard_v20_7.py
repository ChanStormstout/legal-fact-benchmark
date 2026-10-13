"""Offline preparation/replay and explicit candidate acceptance; no generation."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from legal_bench.proof_carrying import source_repair_v20_6_6 as previous
from legal_bench.proof_carrying import final_source_guard_v20_7 as guard
from legal_bench.proof_carrying.artifact_state_v20_2 import immutable, byte_hash, freeze_files, verify_files

BASE = ROOT/'outputs/proof-final-source-guard-v20-7'
OUT = BASE/'validated-01'
PARENT = ROOT/'outputs/proof-source-repair-v20-6/completion-01'
OLD = ROOT/'outputs/proof-evidence-binding-rerun-v20-5'
CASES = {'1954254': ['P01', 'P02'], '569555': ['P01'], '1187427': ['P01']}


def read(path):
    return guard.loads(Path(path).read_text())


def prepare():
    rows, prepared = [], []
    for cid, parts in CASES.items():
        review_path = PARENT/'web-review'/cid/'parsed.json'
        initial = read(PARENT/'preparation'/cid/parts[0]/'task.json')
        case = initial['case']
        immutable(OUT/'cases'/cid/'source.json', case)
        prepared.append(str((OUT/'cases'/cid/'source.json').relative_to(ROOT)))
        if not review_path.exists():
            row = {'case_id': cid, 'status': 'WAITING_SAVED_SOURCE_REVIEW',
                   'source_sha256': guard.digest(case['segments']), 'model_called': False}
            immutable(OUT/'cases'/cid/'preparation-status.json', row)
            prepared.append(str((OUT/'cases'/cid/'preparation-status.json').relative_to(ROOT)))
            rows.append(row)
            continue
        review = read(review_path)
        applied = []
        selected = set()
        for part in parts:
            t = read(PARENT/'preparation'/cid/part/'task.json')
            if guard.digest(t['case']['segments']) != guard.digest(case['segments']):
                raise ValueError('PART_SOURCE_VIEW_MISMATCH')
            local = PARENT/'local'/cid/part
            result = previous.apply_critique(case, t['rules'], read(local/'replacement.json'),
                read(local/'critique-task.json'), review['parts'][part])
            result['reviewer'] = 'Existing saved source review; model-generated, not human gold'
            immutable(OUT/'cases'/cid/'parts'/part/'application.json', result)
            prepared.append(str((OUT/'cases'/cid/'parts'/part/'application.json').relative_to(ROOT)))
            applied.append((part, result))
            selected.update(r['id'] for r in t['rules'])
        full_rules, _ = previous.corrected_rules(read(OLD/'preparation'/cid/parts[0]/'fixture.json')['rules'])
        merged = previous.merge_applied(case, [r for r in full_rules if r['id'] in selected], applied)
        immutable(OUT/'cases'/cid/'recomputed.json', merged)
        prepared.append(str((OUT/'cases'/cid/'recomputed.json').relative_to(ROOT)))
        task = guard.final_task(case, full_rules, merged, applied)
        immutable(OUT/'cases'/cid/'task.json', task)
        prepared.append(str((OUT/'cases'/cid/'task.json').relative_to(ROOT)))
        legacy_path = PARENT/'final'/cid/'formal-answer.json'
        legacy_result = None
        if legacy_path.exists():
            old = read(legacy_path)
            legacy_result = guard.accept_final(task, json.dumps(old['answer']), 'OK', case=case)
            immutable(OUT/'cases'/cid/'legacy-final-replay.json', {
                'original_path': str(legacy_path.relative_to(ROOT)),
                'original_sha256': byte_hash(legacy_path), 'result': legacy_result,
                'old_candidate_rewritten': False})
        row = {'case_id': cid, 'status': 'FINAL_TASK_READY_NOT_GENERATED',
               'reviewed_selectable_claims': len(task['claim_registry']['accepted']),
               'blocked_claims': len(task['claim_registry']['blocked']),
               'original_sources_complete': not task['source_input_truncated'],
               'source_review_reused': str(review_path.relative_to(ROOT)),
               'legacy_final_status': legacy_result['contract_status'] if legacy_result else 'NOT_AVAILABLE',
               'model_called': False, 'semantic_success': False}
        immutable(OUT/'cases'/cid/'preparation-status.json', row)
        prepared.append(str((OUT/'cases'/cid/'preparation-status.json').relative_to(ROOT)))
        rows.append(row)
    summary = {'version': guard.VERSION, 'cases': rows, 'model_calls': 0, 'training': False,
               'old_queue_stays_paused': True, 'main_entry_changed': False}
    immutable(OUT/'cache-replay.json', summary)
    prepared.append(str((OUT/'cache-replay.json').relative_to(ROOT)))
    manifest = freeze_files(ROOT, OUT, ['scripts/proof_final_source_guard_v20_7.py',
        'tests/test_final_source_guard_v20_7.py'], prepared)
    immutable(OUT/'freeze/protocol.json', manifest)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def verify():
    verify_files(ROOT, read(OUT/'freeze/protocol.json'))
    records = read(BASE/'preserved-before.json')['files']
    changed = [p for p, h in records.items() if not (ROOT/p).exists() or byte_hash(ROOT/p) != h]
    if changed:
        raise ValueError('PROTECTED_FILE_CHANGED:' + ','.join(changed))
    print(json.dumps({'status': 'PASS', 'protected_files': len(records), 'model_calls': 0}))


def candidate_action(args):
    verify_files(ROOT, read(OUT/'freeze/protocol.json'))
    task = read(OUT/'cases'/args.case_id/'task.json')
    case = read(OUT/'cases'/args.case_id/'source.json')
    source = Path(args.candidate).resolve()
    destination = Path(args.output_dir).resolve()
    if destination == source.parent or source.parent in destination.parents:
        raise ValueError('DO_NOT_WRITE_INTO_CANDIDATE_DIRECTORY')
    raw = source.read_text()
    def saved_text(name, value):
        path = destination/name
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_text() != value:
            raise ValueError('IMMUTABLE_CANDIDATE_CHANGED:' + str(path))
        if not path.exists():
            path.write_text(value)
    saved_text('raw-candidate.txt', raw)
    if args.action == 'review-task':
        value = guard.review_task(task, guard.loads(raw), case)
        immutable(destination/'review-task.json', value)
        print('REVIEW_TASK_READY_NOT_SUBMITTED')
    else:
        review = Path(args.review).read_text() if args.review else None
        if review is not None:
            saved_text('raw-review.txt', review)
        value = guard.accept_final(task, raw, args.technical_status, case=case, review=review)
        immutable(destination/'acceptance.json', value)
        immutable(destination/'candidate-provenance.json', {'path': str(source), 'sha256': byte_hash(source),
            'review_path': args.review, 'review_sha256': byte_hash(Path(args.review)) if args.review else None})
        print(value['contract_status'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'verify', 'review-task', 'accept'])
    parser.add_argument('--case-id', choices=list(CASES))
    parser.add_argument('--candidate')
    parser.add_argument('--review')
    parser.add_argument('--technical-status', default='OK')
    parser.add_argument('--output-dir')
    args = parser.parse_args()
    if args.action == 'prepare': prepare()
    elif args.action == 'verify': verify()
    elif not all([args.case_id, args.candidate, args.output_dir]): parser.error('case, candidate and output directory required')
    else: candidate_action(args)
