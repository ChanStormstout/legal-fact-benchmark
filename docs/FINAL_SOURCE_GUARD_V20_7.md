# V20.7: final-answer source and completeness constraints

This side-branch version repairs summary length, connects reviewed claims to final writing, checks person/event attribution, and provides source review for a specific final answer. Code: `legal_bench/proof_carrying/final_source_guard_v20_7.py`; entry: `scripts/proof_final_source_guard_v20_7.py`. The main entry, registered review version, and old-batch pause are unchanged.

## Length limits

The old schema shared string objects between body and auxiliary fields. Setting a 480-character auxiliary limit also limited the body; ordinary `deepcopy` preserved this aliasing. The new version copies each occurrence separately and limits only auxiliary arrays such as gaps, including item count/length. Summaries, arguments, and explanations no longer inherit 480 characters. Original schemas and failed answers remain.

Removing a field limit does not ensure completion within total output budget. Final review must still inspect unfinished sentences, omissions, and conclusion scope. Budget exhaustion/transport failure remains technical failure with a null answer.

## Reviewed claims and writing

Preparation reuses saved source reviews, invokes original local application/merge/independent checking, and constructs selectable claims. Eligibility requires REVIEWED, SUPPORTED, nonempty valid citations, and the same conditions for every dependency. Excluded/unresolved records remain complete in application/raw-review files; writing materials show only their IDs/status.

Each C001-style ID has `origin_declaration_id` linking to the original partition and EV/USE/ROLE/J address. `declaration_aliases` restores old addresses; content is unchanged and dependencies round-trip. Source/claim enums share `$defs` to avoid repeated full lists. `source.json` preserves full text, which enters both writing and final review. Blank passages are not evidence options; original paragraphs/SRC numbering remain.

Each J:n uses its own audit status/errors, rather than inheriting the first judgment's status. SUPPORTED means a sourced claim, not a TRUE legal premise. UNKNOWN, CONFLICTED, and OPEN_TEXT still constrain conclusions.

Actual-case reconstruction requires empty `assumptions`. Unsupported facts remain gaps, not assumed grounds for conclusions. Hypothetical scenarios need a separate task; that workflow is not implemented here. Newly noticed facts cannot bypass claim review into arguments/events/conclusions: they need new review records and a new prepared task.

## People, property, and procedural acts

`case_frame` records parties/identities, property descriptions, event actors, acting courts, court levels, and stages. Arguments, rebuttals, and events must link to selectable claims. Checks require at least two parties, one property, unique IDs, matching citations, and compatible party/court action categories. A court cannot apply as a PARTY_APPLICATION party; a private party cannot issue COURT_REMAND; the remanding court actor must match court context.

These checks detect structure and explicit category conflicts. Swapped court IDs, misread names/dates, and whether a claim was adopted still require source review of the actual answer. Field presence does not prove correctness.

## Final-answer acceptance

After format/link checks, `review_task` creates units for every text field: summary, arguments, rebuttals, explanation, gaps, treatment reasons, names, event descriptions, and stage classifications. Review receives the specific answer, full sources, fixed request, rules, per-premise computation state, and claim table. Task/answer/source/rule/table hashes are saved.

Eleven whole-case checks additionally cover people, property, event attribution, court/stage, adopted reasoning, decisive rebuttals, uncertainty, conclusion scope, resurfacing excluded facts, text/claim agreement, and narrative completeness. Direct source support does not replace missing intermediate-claim review. Conditional payments cannot become actual payments; disputed dates cannot become certain dates.

Without review, `accept_final` returns PENDING_WHOLE_ANSWER_SOURCE_REVIEW with null answer. Unsupported/unresolved/missing review, missing citations, duplicate JSON keys, or any hash mismatch also rejects acceptance. Original candidates/reviews remain separately saved. Correctly expressed unknowns can pass as faithful reconstruction; unresolved review itself does not unlock acceptance.

Full acceptance is MODEL_SOURCE_REVIEW_ACCEPTED_NOT_LEGAL_SUCCESS, explicitly model-based/non-human reference with `legal_approval=false`. Fallible external review labels are not programmatic proof of semantic correctness.

## Execution and handoff

Validated material is in `outputs/proof-final-source-guard-v20-7/validated-01`. Initial root preparation/freeze remain as engineering history; that first preparation made no model calls. Use `validated-01/freeze/protocol.json` for the implementation.

These entries only prepare/check/accept locally; they do not generate answers, submit website reviews, train, or resume queues:

```sh
python3 -B scripts/proof_final_source_guard_v20_7.py prepare
python3 -B scripts/proof_final_source_guard_v20_7.py verify
python3 -B scripts/proof_final_source_guard_v20_7.py review-task --case-id 1954254 --candidate /absolute/candidate.json --output-dir /absolute/separate-review-directory
python3 -B scripts/proof_final_source_guard_v20_7.py accept --case-id 1954254 --candidate /absolute/candidate.json --review /absolute/review.json --output-dir /absolute/separate-acceptance-directory
```

Outputs must be separate from candidate directories. `review-task` saves unsent material; `accept` reads existing review. Schema-valid generation must still use this entry, never old `local_pipeline_v19_8.accept_final`.

Initial `validated-01` applied reviews for 1954254/569555, yielding 219/153 selectable claims. Missing 1187427 review was not fabricated. Subsequent authorized real acceptance is in `real-acceptance-01`: 111 old reviews for 1187427 were recovered/applied, yielding 137 selectable claims. One actual generation per case produced **0/3 complete acceptances**. 1954254 ended midway through references; both other complete JSON responses failed actor-relation checks. Old material/validated-01 remain. See the [real acceptance report](../outputs/proof-final-source-guard-v20-7/real-acceptance-01/report-zh.md).

Initial local-tokenizer input estimates were 92,764/86,878 tokens plus 16,384 output reserve, exceeding the local 65,536 budget. Real acceptance later confirmed a service context of 262,144 and made three calls without removing sources. 1954254 returned no usage; the other inputs were 86,878/80,729 tokens. Completed service calls do not imply acceptance or compatibility with the old local budget.
