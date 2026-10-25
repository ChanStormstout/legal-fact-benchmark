"""Verify exact accepted artifacts and write the isolated local delivery report."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.proof_final_bindings_v20_8 import OUT, read, verify as verify_base
from legal_bench.proof_carrying import final_statement_review_v20_9_1 as core
from legal_bench.proof_carrying.artifact_state_v20_2 import immutable, digest, byte_hash, freeze_files, verify_files

CASES = [('1954254', 'statement-pack-01', 'final-acceptance-corrected.json',
          'whole-answer-review/web-response-corrected.json', 'generation/parsed.json'),
         ('569555', 'statement-pack-03', 'final-acceptance.json',
          'whole-answer-review/parsed.json', 'ordering-plan.json'),
         ('1187427', 'statement-pack-02', 'final-acceptance.json',
          'whole-answer-review/parsed.json', 'ordering-plan.json')]


def write_once(path, body):
    path = Path(path)
    if path.exists() and path.read_text() != body:
        raise ValueError('DELIVERY_TEXT_CHANGED:' + str(path))
    if not path.exists(): path.write_text(body)


def readable(cid, answer):
    parts = [f'# {cid} — case reconstruction accepted by this source review',
             'This is model source review of development cases, not human gold, lawyer approval, or executable legal conclusions. Old premise-computation states remain preserved.',
             '## Summary', answer['conclusion'], '## Parties, courts, and properties']
    for r in answer['case_frame']['actors']:
        parts.append(f"- {r['name']}: {', '.join(r['capacities'])}; {r['kind']}; ID {r['id']}.")
    for r in answer['case_frame']['properties']:
        parts.append(f"- Property: {r['description']}; ID {r['id']}.")
    parts.append('## Procedure and events')
    for r in answer['case_frame']['events']:
        parts.append(f"- {r['description']} (actor {r['actor_id']}; stage {r['stage']}; sources {', '.join(r['refs'])})")
    for label, key, textkey in [('Grounds', 'grounds', 'explanation'),
                                ('Opposing arguments and treatment', 'counterarguments', 'treatment')]:
        parts.append('## ' + label)
        for r in answer[key]:
            parts.extend([r['point'], r[textkey],
                          'Sources: ' + ', '.join(r.get('case_refs', r.get('refs', [])))])
    parts.append('## Unresolved matters and adjudicative scope')
    parts.extend(answer['gaps'])
    return '\n\n'.join(parts) + '\n'


def deliver():
    verify_base()
    rows = []
    for cid, root, result_file, review_file, plan_file in CASES:
        d = OUT / root / 'cases' / cid
        verify_files(ROOT, read(d / 'freeze/protocol.json'))
        task, case, plan, review = (read(d / f) for f in
                                   ('task.json', 'source.json', plan_file, review_file))
        result = read(d / result_file)
        recomputed = core.accept_final(task, json.dumps(plan), 'OK', case=case, review=review)
        if result != recomputed:
            raise ValueError('FINAL_RESULT_REPLAY_MISMATCH:' + cid)
        if result['contract_status'] != 'MODEL_SOURCE_REVIEW_ACCEPTED_NOT_LEGAL_SUCCESS' or result['answer'] is None:
            raise ValueError('FINAL_SOURCE_REVIEW_NOT_ACCEPTED:' + cid)
        if result['legal_approval']:
            raise ValueError('UNAUTHORIZED_LEGAL_SUCCESS_CLAIM')
        rt = read(d / 'whole-answer-review/task.json')
        if any(v['label'] != 'SUPPORTED' for group in ('verdicts', 'coverage')
               for v in review[group].values()):
            raise ValueError('SOURCE_REVIEW_NOT_ALL_SUPPORTED:' + cid)
        if digest(case['segments']) != read(OUT / 'cases' / cid / 'bridge.json')['source_sha256']:
            raise ValueError('SOURCE_CHANGED:' + cid)
        answer = result['answer']
        for record in task['pack']['records']:
            section = record['section']
            if section == 'SUMMARY': assert record['text'] in answer['conclusion']
            elif section == 'LIMITATION': assert record['text'] in answer['gaps']
            else:
                pool = answer['grounds'] if section == 'GROUND' else answer['counterarguments']
                row = next(x for x in pool if x['claim_ids'] == [record['id']])
                assert row.get('explanation', row.get('treatment')) == record['text']
                assert all(row[k] == record[k] for k in ('actor_ids', 'property_ids', 'event_ids'))
        assert answer['case_frame'] == task['frame']
        assert len(plan['record_order']) == len(set(plan['record_order'])) == len(task['pack']['records'])
        write_once(d / 'accepted-answer-zh-heading.md', readable(cid, answer))
        rows.append({'case_id': cid, 'accepted_result': str((d / result_file).relative_to(ROOT)),
                     'readable_answer': str((d / 'accepted-answer-zh-heading.md').relative_to(ROOT)),
                     'contract_status': result['contract_status'], 'legal_approval': False,
                     'summary_characters': len(answer['conclusion']), 'statement_records': len(task['pack']['records']),
                     'field_review_units': len(rt['units']), 'supported_field_units': len(review['verdicts']),
                     'coverage_checks': len(review['coverage']), 'all_source_checks_supported': True,
                     'source_sha256': digest(case['segments']), 'task_sha256': task['input_sha256'],
                     'answer_sha256': digest(answer), 'all_reviewed_statement_text_and_bindings_preserved': True,
                     'unreviewed_assumptions': len(answer['assumptions']),
                     'actual_new_ordering_call': str((OUT/'statement-pack-01/cases'/cid/'generation/run.json').relative_to(ROOT)),
                     'final_adjustment_is_cache_replay': cid in ('1187427','569555')})
    accounting = read(OUT / 'engineering/run-accounting-final.json')
    tests = read(OUT / 'engineering/tests-v20-9-2.json')
    assert tests['passed'] and accounting['total_api_cost_or_bound_usd'] <= accounting['maximum_total_cost_usd']
    results = {'version': 'V20_9_2_LOCAL_SOURCE_RECONSTRUCTION_DELIVERY', 'cases': rows,
               'accepted_cases': len(rows), 'total_cases': len(rows), 'tests': tests,
               'api_accounting': accounting,
               'scope': 'EXPOSED_DEVELOPMENT_CASE_ENGINEERING_AND_MODEL_SOURCE_REVIEW',
               'not_human_gold': True, 'not_automatic_extraction_accuracy': True,
               'not_paper_or_gnn_effectiveness_evaluation': True,
               'main_entry_switched': False, 'training_commit_push': False,
               'old_freewriting_server_truncation_unique_cause': 'UNKNOWN',
               'other_side_chat_and_shared_files_not_written': True}
    immutable(OUT / 'results.json', results)
    table = '\n'.join(f"| {r['case_id']} | {r['statement_records']} | {r['summary_characters']} | {r['supported_field_units']}/{r['field_review_units']} | {r['coverage_checks']}/11 |"
                      for r in rows)
    answers = '\n'.join(f"- [{r['case_id']} complete answer](/{ROOT}/{r['readable_answer']})".replace('//Users','/Users') for r in rows)
    report = f'''# Final-answer repair and experimental acceptance report

All three development cases passed final source-consistency and coverage checks; 85 engineering checks passed. Acceptance covers the reviewed statements' subjects, properties, procedural stages, conditions, opposing arguments, and adjudicative scope. It is not human gold, automatic-extraction accuracy, paper/GNN effectiveness, or legal approval. The main experiment entry has not switched.

| Case | Fixed statements | Summary characters | Supported fields / all fields | Supported coverage checks |
|---|---:|---:|---:|---:|
{table}

## Repairs and causes

The 480-character ceiling came from shared field rules applying the same cap to summaries and auxiliary explanations. The existing fix is retained: summaries render complete reviewed sentences without a 480-character slice. All three summaries exceed 480 characters and preserve every summary statement in full.

Subject mismatches included specific interface defects: local OBJ IDs meant different things across premises, but merged-array positions were treated as identity; the court recording a statement was confused with the court acting; final input lacked original object definitions. The new bridge preserves local domain addresses, global-position maps, definitions, and dependencies. Acting subjects, affected parties, hearing courts, and recording courts are separate; government notifications and retirement have separate categories. Old incorrect statements remain blocked, and new entities require source review.

After fixing the subject table, one actual free-writing call still attributed a lower-court finding to the High Court. Later old-statement selection omitted an explicit judicial reservation. These failures show that format/prompt repair alone is insufficient. The current interface lets Qwen order only IDs of source-reviewed typed statements. The program renders all statements and event tables verbatim; the model cannot add facts, rebind subjects, or introduce unreviewed assumptions. Summaries preserve attribution and adjudicative stage, and excluded facts cannot reenter through final writing.

Whole-case review further corrected 1187427's conflation of retirement date with occupation during employment. The revised frame was reviewed again; the original 26 statements and actual ordering result stayed unchanged. For 569555, additions retained the majority's rejection of a merely directory-proviso theory, Sarkar's reservation about other 1958 grounds, and the joint judgment's effect on the Association. The original 22 statements were unchanged. Two added reservations entered only after new source review; repeated whole-case review passed.

For 1954254, all initial 177 fields and 11 coverage checks were supported, but the review record omitted one character of the rule hash. The program first rejected it. In the browser review session, Python read the binding value from the original schema and merged the original record. Local checking confirmed unchanged source judgments, reasons, and coverage. The rejected result was retained and corrected acceptance stored separately; acceptance requirements were not relaxed.

## Experimental and cached evidence

Seven actual Qwen API calls comprised one free-writing call, three old-statement selections, and three complete typed-statement orderings. Each case had one real final ordering generation on complete, undeleted source input and ended normally. Later source corrections for 1187427 and 569555 used transparent cached replay, not purported new generation. The program appended 569555's two new statements to the original ordering prefix; the replay receipt records the additions and fresh source review. Only review-record binding fields changed for 1954254.

Cache checks preserved complete originals, 338 local statements, 171 global object positions, 509 previously accepted statements, 102 blocked statements, and dependencies. All 72 current reviewed statements retain complete sentences and bindings in final answers. Saving every original cache item does not mean displaying all of it in the answer; answer coverage was separately checked against 11 request requirements. Old premise computations remain UNKNOWN; historical court narration was not treated as satisfied legal proof.

The 85 engineering checks cover scoped IDs, invalid subject types, blank sources, dependencies, invalidation after statement changes, prohibited omissions/repeated IDs/new body text, identity-review material, source-supplement replay, and null technical failures. Label injection was used only for program checking. All 480 saved V20.7 file hashes were unchanged, and current case code/data dependencies also passed freeze checks.

New API cost or conservative bound was USD {accounting['new_api_cost_or_bound_usd']:.8f}; including earlier usage it was USD {accounting['total_api_cost_or_bound_usd']:.8f}, within the original USD0.50 cap. ChatGPT Web source-review subscription usage is separate from API token cost. Token counting was repaired in an isolated transport layer. Actual token-sequence lengths matched server counts for seven observed requests; the current margin covered those requests, without guaranteeing identical bounds for every future input.

## Remaining limits

Statement packs include development-stage model proposals, source inspection, and supplements. Automatic production of equally complete packs for unseen cases is unproven. Reviewers were separate ChatGPT Web sessions, not human gold, and exact browser-model revisions were unavailable. These three cases do not establish the paper mechanism or GNN superiority over retrieval.

The unique cause of the old 1954254 server-side early ending during free generation remains unknown. Generating IDs and rendering fixed text avoids regenerating long factual prose; it does not prove the old free-writing truncation fault is cured. Final-answer acceptance for these three cases cannot extend the earlier four analysis tasks' completeness findings to every task.

This work wrote only independent modules, its own documentation, and output directories. The other side chat's retrieval/GNN modules, tests, environment, and shared entry were untouched. No training, commit, or push occurred. Shared indexing/main-entry integration was left for consolidation to avoid concurrent writes. Replay entry: `scripts/proof_final_statement_completion_v20_9_2.py`. Local verification/reporting of accepted results: `scripts/proof_final_delivery_v20_9_2.py`, which makes no model calls.

## Complete results and verification material

{answers}

Summary: `results.json`. Cache/budget evidence: `engineering/cache-acceptance.json`, `engineering/run-accounting-final.json`, `engineering/token-budget-calibration-final.json`, `engineering/tests-v20-9-2.json`, and `engineering/preservation-final.json`. Each case retains complete sources, tasks, raw generations, statement packs, event frames, source reviews, and acceptance records. `replay-receipt.json` records replay differences. Browser-review provenance is in `engineering/reviewer-provenance.json`; visible evidence is in `engineering/review-1954254-proof.png`.
'''
    write_once(OUT / 'report-zh.md', report)
    prepared = [str((OUT / p).relative_to(ROOT)) for p in
                ('results.json', 'report-zh.md', 'ownership-v20-9-2.json',
                 'engineering/run-accounting-final.json', 'engineering/tests-v20-9-2.json',
                 'engineering/preservation-final.json', 'engineering/reviewer-provenance.json',
                 'engineering/token-budget-calibration-final.json')]
    for row in rows:
        prepared.extend([row['accepted_result'], row['readable_answer']])
    prepared.append('docs/FINAL_BINDINGS_V20_8.md')
    manifest = freeze_files(ROOT, OUT / 'delivery-01', ['scripts/proof_final_delivery_v20_9_2.py',
                             'scripts/proof_final_statement_completion_v20_9_2.py'], prepared)
    immutable(OUT / 'delivery-01/freeze/protocol.json', manifest)
    verify_files(ROOT, manifest)
    print(json.dumps({'accepted': len(rows), 'tests': tests['tests_run'],
                      'api_calls': accounting['actual_api_calls'],
                      'total_cost': accounting['total_api_cost_or_bound_usd']}))


if __name__ == '__main__': deliver()
