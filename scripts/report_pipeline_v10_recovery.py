"""One concentrated decisive-source review of the recovered 69305 final pair."""
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import digest, write_new

ROOT = Path('outputs/rules-verdict-v10-constraint-recovery')
read = lambda p: json.loads(p.read_text())
results = read(ROOT / 'results.json')
source = read(ROOT / 'sources/69305.json')
law = read(ROOT / 'prepared/69305/law-package.json')
case_map = {x['id']: x['text'] for x in source['segments']}
law_map = {x['id']: x['text'] for x in law['law_segments']}
answers = {}
restored = {}
rows = []
for method in ['A', 'B']:
    meta = read(ROOT / 'runs' / method / 'run.json')
    intermediate_meta_path = Path('outputs/rules-verdict-v8-paired/runs') / method / 'stage1/run.json'
    stage = read(intermediate_meta_path)
    if meta['run_status'] == 'OK':
        answer = answers[method] = read(ROOT / 'runs' / method / 'parsed.json')
        restored[method] = []
        for index, ground in enumerate(answer['grounds']):
            restored[method].append({
                'ground': index + 1, 'point': ground['point'],
                'case_sources': [{'id': ref, 'text': case_map[ref]} for ref in ground['case_refs']],
                'law_sources': [{'id': ref, 'text': law_map[ref]} for ref in ground['law_refs']],
                'address_validity_not_semantic_support': True})
    else:
        answers[method] = None
    rows.append({
        'case': '69305', 'method': method, 'run_status': meta['run_status'],
        'outcome': answers[method]['outcome'] if answers[method] else None,
        'final_generation_role': 'NEW' if method == 'A' else 'REUSED_COMPATIBLE_FIXED_CALL',
        'final_input_tokens': meta['prompt_tokens'], 'final_output_token_ids': meta['output_tokens'],
        'final_seconds': round(meta['elapsed_seconds'], 3),
        'intermediate_origin': str(intermediate_meta_path),
        'intermediate_input_tokens': stage['prompt_tokens'],
        'intermediate_output_tokens': stage['output_tokens'],
        'intermediate_seconds': round(stage['elapsed_seconds'], 3),
        'recorded_two_stage_seconds': round(stage['elapsed_seconds'] + meta['elapsed_seconds'], 3),
        'cost_note': 'Historical intermediate plus recovered final ledger, not simultaneous benchmark',
        'source_review': 'DECISIVE_ERRORS_REMAIN_NO_LEGAL_ACCURACY_SCORE'})
write_new(ROOT / 'restored-final-sources.json', restored)
write_new(ROOT / 'comparison-table.json', rows)
with (ROOT / 'comparison-table.csv').open('x') as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
assert all(answers.values()), 'No complete pairing: report failure instead of legal comparison'

review = {
    'review_type': 'ONE_CONCENTRATED_LOCAL_DECISIVE_SOURCE_REVIEW',
    'label': 'MODEL_ASSISTED_DEVELOPMENT_REVIEW_NOT_HUMAN_GOLD',
    'historical_final_judgment_not_used_as_expected_label': True,
    'source_findings': [
        {'id': 'S1', 'refs': ['p0003.s003', 'p0003.s004'],
         'finding': 'Conditional lease proviso exists: assignment or parting with possession to associate concerns without further consent. Its statutory effect for this occupant is not settled just by quoting it.'},
        {'id': 'S2', 'refs': ['p0004.s002'], 'quote': case_map['p0004.s002'],
         'finding': 'Allowed input explicitly reports the Rent Controller and appellate authority accepting reliance on the clause and ordering eviction on induction as sub-lessee. These are lower-court findings, not a withheld Supreme Court final endorsement.'},
        {'id': 'S3', 'refs': ['p0004.s001', 'p0004.s003', 'p0004.s004'],
         'finding': 'Authorized-dealer/associate status and collateral admissibility arguments remain party submissions; detailed final resolution of associate qualification is absent in the allowed material.'},
        {'id': 'S4', 'refs': ['LAW:1134266:p0004.s004', 'LAW:1134266:p0004.s005'],
         'finding': 'Law package supplies historical Section14(1)(b) transfer alternatives and written-consent requirement. It does not supply a source rule resolving Section49 collateral use or associate-concern interpretation for this tenant.'}],
    'decisive_checks': [
        {'method': 'A', 'ground': 1, 'finding': 'Allegation attributed to landlord correctly; SUPPORTED is proper for existence of allegation, not truth of every eviction element.'},
        {'method': 'A', 'ground': 2, 'reason_affected': True,
         'classification': 'AVAILABLE_LOWER_COURT_FINDING_MISREPORTED_AS_ABSENT',
         'source': 'p0004.s002',
         'finding': 'Claim that no judicial determination on admissibility is provided conflicts with explicit lower-court treatment. Legal completeness at the appeal stage can still be uncertain; the lower-court determination must be retained.'},
        {'method': 'A', 'ground': 3,
         'classification': 'QUALIFICATION_UNRESOLVED_IS_PLAUSIBLE_LABEL_BUT_POINT_ROLE_IMPRECISE',
         'finding': 'Absence of a supplied finding deciding associate qualification supports retaining this issue. However the proviso authorizes the original tenant to transfer to an associate, not United Automobiles to assign onward.'},
        {'method': 'B', 'ground': 1, 'classification': 'TEXTUAL_PROVISO_SUPPORTED_STATUTORY_EFFECT_NOT_ESTABLISHED',
         'finding': 'Proviso exists, but phrasing it as written consent for subletting imports a legal interpretation. No supplied rule conclusively resolves that interpretation; literal clause existence and statutory satisfaction should remain separate.'},
        {'method': 'B', 'ground': 2, 'classification': 'KEY_ASSOCIATE_QUALIFICATION_UNRESOLVED',
         'finding': 'Model retains actual dispute over associate qualification. This does not establish that every court-treated fact is missing.'},
        {'method': 'B', 'ground': 3, 'reason_affected': True,
         'classification': 'SOURCE_CONTRADICTED_POINT_AND_INTERNAL_INCONSISTENCY',
         'source': 'p0004.s002',
         'finding': 'Point asserts legally established parting with possession rather than subletting and marks SUPPORTED. Source reports induction as sub-lessee; explanation itself calls precise mode unverified. A general rule listing alternatives cannot establish which alternative happened.'}],
    'intermediate_trace': {
        'A': 'Final repeats the notes coverage claim that key court findings were omitted, despite full source being supplied.',
        'B': 'Proposal x2 classified court-reported sub-lessee induction as PART_WITH_POSSESSION; program gave local PROPOSED_SUPPORT, not semantic validation. Final point3 resembles this misclassification. This is a plausible propagation path, not proof of model attention or causal attribution.',
        'B_not_propagated': 'Corporate-amalgamation/US-versus-Indian identity contamination in old proposal did not appear in final answer; this is not evidence of B superiority because A did not make that error.',
        'program_checks': 'All54 old combinations remain UNRESOLVED; this expresses limits of supplied proposals/bindings, not absence of source court findings.'},
    'shared_limits': ['Both final outcomes UNDETERMINED can be defensible under restricted legal materials; same label is not proof of correctness.',
                      'Both use a conditional proviso without a supplied interpretation closing its statutory scope.',
                      'Missing target appellate reasoning differs from absent lower-court determination.',
                      'Neither identifies program-derived facts as the decisive source of an improved final answer.'],
    'decision': 'PRIORITIZE_TEXT_FOR_CURRENT_DEVELOPMENT_PAIR',
    'decision_basis': 'No source-verified overall B improvement; B introduces categorical mode misclassification and label inconsistency while using much more final input. A is also materially flawed. This is a resource choice for this old-case development configuration, not proof text reasoning is accurate or structured methods generally inferior.',
    'next_change_recommendation_only': 'Prioritize final judgement use of already supplied court findings and separation from unresolved legal scope. No new prompt or rerun in this round.',
    'accuracy_or_generalization_claim': False, 'new_annotations': 0, 'web_calls': 0}
write_new(ROOT / 'final-source-review.json', review)
write_new(ROOT / 'decision.json', {k: review[k] for k in ['decision', 'decision_basis', 'next_change_recommendation_only']})

start = read(ROOT / 'start-audit.json')
changed = [name for name, value in start['old_outputs'].items() if digest(Path(name).read_bytes()) != value]
assert not changed, changed
write_new(ROOT / 'preservation-check.json', {'old_files_checked': len(start['old_outputs']), 'changed_files': changed})
frozen = read(ROOT / 'freeze/config.json')
assert all(digest(Path(name).read_bytes()) == value for name, value in {**frozen['files'], **frozen['live_code']}.items())
(ROOT / 'final-answer-slots.md').write_text(
    '# Complete Recovered Answers for 69305\n\n[A: complete answer after text notes](runs/A/parsed.json)；'
    '[B: complete answer after partial facts and program checks](runs/B/parsed.json)。\n\n'
    'A is the only new call. B reuses the FIXED constraint-diagnostic result; neither V8 intermediate result was regenerated.'
    'Full raw outputs, source recovery, costs and one concentrated review are preserved. Development review is not human gold.\n', encoding='utf-8')
a, b = rows
report = f'''V10: same-case final-answer comparison for 69305 after constraint repair

The within-case pair recovered: A and B both completed and answered UNDETERMINED, but both have errors in decisive reasoning. Text remains provisionally preferred for development on this case. B has no verifiable overall complete-answer gain, adds an unjustified definite transfer characterization and contradictory explanation, and increases input burden. A is not a reliable legal method either. This is an investment decision for one exposed case, not a generalization or accuracy ranking.

Actual execution
A reused V8 text notes with the original V9 final prompt and repaired constraints, in one new call. B reused the completed FIXED diagnosis result after verbatim compatibility checks of prompts, schema, shared case/legal sources, settings, and repaired mask; B was not regenerated. Both intermediate artifacts came from completed V8 proposals under old constraints. This compares recovered final stages, not complete two-stage reruns under new constraints.

Qwen3.5-9B-4bit revision8b2b98c00a6b4d291155e4890773ca8f769aee53, MLX-VLM0.7.4, greedy, repetition_penalty1, thinking off, and schema constraints are unchanged. Final output cap3072, total context32768, with no original-text truncation. A input {a['final_input_tokens']}, output IDs {a['final_output_token_ids']}, time {a['final_seconds']} seconds; B input {b['final_input_tokens']}, output IDs {b['final_output_token_ids']}, time {b['final_seconds']} seconds. Both ended stop without repetition, format repair, or retries. Saved-ID output counts include the end token. One new call, one reused final call, no browser calls/retries.

Historical first-stage times were A {a['intermediate_seconds']} and B {b['intermediate_seconds']} seconds. Recorded two-stage totals including recovered finals are A {a['recorded_two_stage_seconds']} and B {b['recorded_two_stage_seconds']} seconds, excluding historical failures/extra diagnosis. Runs occurred at different times and are not a synchronized performance benchmark.

Supported content and actual errors
1. A distinguishes the landlord's allegation of unauthorized subletting from its truth. But ground2/reason claim no judicial admissibility finding. Source p0004.s002 explicitly states that the Rent Controller/appellate authority found the lease term “was not inadmissible,” allowed reliance, and ordered eviction because United Automobiles entered as sub-lessee. A loses visible lower-court findings; withholding the Supreme Court's reasoning does not remove them.
2. B ground2 retains the unresolved associate-concern issue. Ground3 nevertheless declares the transfer legally established as parting with possession rather than subletting, marks SUPPORTED, and says its precise mode is unverified. The source records a lower-court sub-lessee finding. Old proposal x2 similarly records PART_WITH_POSSESSION; local PROPOSED_SUPPORT is based only on that proposal. This suggests possible propagation, not proof that the model relied on the program.
3. Both must distinguish a conditional associate exception in the lease from whether it constitutes statutory written consent for this transaction under Section14(1)(b). Shared authorities supply transfer/consent/date conditions, not full Section49 collateral-purpose or associate-definition interpretation. B's description of the clause as written consent for subletting is not semantically verified by valid source IDs. A ground3 also makes the original tenant's permission to transfer to an associate sound like permission for United Automobiles to assign onward, misexpressing roles.

Structured-material contribution and limits
B retains some lower-court history and does not copy American/Indian merger identities contaminating the old proposal. A lacks that identity error too, so B's self-correction is not superiority over A. B does not correct transfer characterization. All 54 program combinations being UNRESOLVED provides no clear reliable final-judgment benefit. Both UNDETERMINED labels may be cautious, but equal labels do not establish correct reasons. The model was not required to reconstruct the excluded historical final judgment.

Three distinct gaps
Lower-court admissibility/sub-lessee findings are present, not missing facts. Complete associate-eligibility adjudication details are absent from allowed input and require scope qualification. Missing contract/registration-law interpretation is a legal-coverage gap. Unimplemented open legal interpretation is a program-coverage gap, not missing source text. Both final models read full originals, so omissions cannot all be blamed on extraction fields.

Scope, delivery, and stopping
Only repeatedly exposed case69305 was used, with existing retrieval, allowed sources, authorities, and intermediate outputs. Lower-court information and later authorities make this retrospective development material. V1–V9/constraint-diagnosis outputs remain unchanged. Before A generation, current sources, prompts, schema, settings, source hashes, calls, and review rules were frozen. One consolidated decisive-source review covered both final answers, without complete intermediate relabeling, browser recheck, new gold, or extra calls. Complete answers, raw text, comparison tables, recovered citations, B traces, and compatibility audits are saved.

The next proposed focus is preserving supplied court findings and distinguishing unresolved facts from legal interpretation. That recommendation was not implemented through prompt edits or regeneration here. This round ends without case expansion, automatic continuation, commit, or push.
'''
(ROOT / 'report-zh.txt').write_text(report, encoding='utf-8')
print(json.dumps({'new_calls': results['new_model_calls'], 'complete_final_answers': 2,
                  'decision': review['decision'], 'preserved_files': len(start['old_outputs'])}, indent=2))
