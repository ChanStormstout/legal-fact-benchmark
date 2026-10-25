# Rule extraction and complete legal answers: debugging and change plan

Status at creation: plan prepared; application code not implemented; model experiment not run. Date: October 3, 2026, America/Phoenix. This document does not authorize automatic generation, commit, or push.

## 1. Question and scope

On the same permitted facts, legal package, and three original authorities for 1134266, does adding V16's nine actual extracted cards improve fidelity/completeness or introduce summary omissions/scope-transfer errors? This exposed development case guides investment only, not independent testing/generalization.

V15 added researcher-selected summaries/passages; V16 extracted rules in three independent website tasks. V15 improvement does not establish V16 usefulness. Actual V16 cards must enter complete answers; counts, valid provenance, and ranks cannot substitute for final benefit.

The shared legal package already contains three historical cards from 69305/661475. Correct comparison: “shared material” versus “shared material + nine V16 candidates,” not no-cards versus cards. Keep all common cards/limitations rather than deleting them for a cleaner experiment name.

Round one changes only task assembly, material comparison, citation recovery, and recording. Do not alter V16 semantics, re-extract, repair BM25, add law, or relabel facts before learning what existing components contribute.

## 2. Evidence and unconfirmed explanations

| Area | Evidence | Assessment | First-round handling |
|---|---|---|---|
| Extraction | `rule_transfer_v16.schema` caps three cards/source; General Radio response prioritizes other rules | Coverage loss, not proven code bug | Keep cards; give both arms complete existing sources |
| Omission | General Radio P10 describes Delhi provisions not excluding involuntary sale; nine cards omit the full distinction | Source-to-summary omission, not citation-address failure | Evaluation clue only, never tested prompt |
| Retrieval | `authority_index.search` uses OR terms/BM25; Delhi diagnostic ranks Telesound's tentative view first | Lexical relevance is not applicability; no confirmed BM25 bug | No top-k pruning; fixed three-source order |
| Scope | AP/Bombay/Delhi contexts differ; HP has special legislation; Telesound reserves the final question | Interpret scope rather than uniformly transplant/delete | Preserve scope/source_kind/exceptions/limits; reread originals |
| Context | General Radio 10 pages, HP 16; Telesound part of paragraph 12 and paragraph 16 | Telesound is an excerpt | Mark coverage, no new full text/guessed metadata |
| Metadata | V16 chiefly records retrieval addresses/hashes, not full court/date/statute fields | Structured metadata deficit, not omission of already supplied fields | Read available text; no URL/card-based guesses |
| Citation checks | `inspect_reply` checks structure/card/evidence IDs and restores text | Engineering, not proposition support | Keep `semantic_certification=false` |
| Final synthesis | V15 omits landlord's alternative capital-reduction argument, with attribution/date precision issues | Final integration defect, not automatically extractor fault | Review decisive content, including uncited passages |
| New cases | No two matching merger cases confirmed among 62 complete unused candidates; three keyword hits concern other settings | Prepared-material limitation, not corpus-wide absence | Use old-case diagnosis; no new-case prerequisite |

An earlier masked JSON termination token has separate repair evidence. This round uses website High without local token constraints; do not rerun that diagnosis or attribute legal misreading to its recurrence. Prompt/order/card caps remain hypotheses, not confirmed root causes.

## 3. Fixed complete flow

```text
Existing 1134266 facts: 19 passages, 40 excluded IDs
+ shared package: six original passages, three historical cards
+ V16 original authorities: ten pages, sixteen pages, two excerpts
                      ↓
            Assembly, IDs, hashes
              ↙                 ↘
A: shared material          B: identical shared material
empty intermediate block    + nine actual V16 cards
one new ordinary High chat  one new ordinary High chat
              ↘                 ↙
        Complete answers; structure/source recovery
                      ↓
       One consolidated source/cost review
                      ↓
       Retain cards / prefer originals / inconclusive
```

Programs ensure material consistency, address recovery, and records, not adjudication. The model interprets supplied law, connects facts, considers opposition, and gives experimental issue analysis. Valid source IDs cannot prevent misreading. No rule induction, automatic legal compilation, or retrieval-effectiveness experiment occurs here.

Cards might reduce the burden of locating conditions/effects/scope/exceptions in long authorities while originals allow correction. They might also emphasize inapplicable views, omit restrictions, or divert attention from counterarguments. Both directions require source evidence; do not assume structured input is superior.

## 4. Input preparation and leakage

Use actual saved V14 `prompt.txt`, `schema.json`, `source.json`, `law-package.json`, and `retrieval.json` under `outputs/rules-verdict-v14-web-direct/tasks/1134266/`, not a current-code approximation. The prompt already includes facts, common law, two fictional examples, and the fixed question.

Read additional common law only from V16 `sources/{GENERAL_RADIO,HINDUSTAN_PETROLEUM,TELESOUND}.json`. All saved segments/text enter both arms in order, including headnotes/OCR/coverage. Mark Telesound as excerpts. Other historical cases' outcomes can belong to authority text; excluded target 1134266 outcomes/reasons remain different.

Insert the shared authority block once before `TARGET INTERMEDIATE MATERIAL (UNVERIFIED)`. A keeps its empty intermediate block. B receives actual V16 bundles: all nine cards, conditions, source nature, scope, exceptions, formalization limits, and response limitations. Exclude hand-authored V16 reviews, V15 summaries, and prior answers.

Fixed order: General Radio, Hindustan Petroleum, Telesound, independent of expected position/BM25. Preserve bundle/card order. Cards remain fallible proposals; addresses are not certification.

Use the same final schema/fields/caps, expanding only `law_refs` to 34 original law IDs (six old + 28 new). Facts remain the 19 old `case_refs`. Card IDs cannot be independent source evidence. Example IDs/excluded target IDs stay outside valid enums. Duplicate IDs stop preparation, never overwrite maps.

Prove that removing added common/card blocks restores the actual base. Facts, old package, added sources, question, examples, instructions, and schemas must match across arms; only intermediate cards differ. Whole prompts need not hash equally. Record the three existing common cards; A is not a rule-free baseline.

Tasks exclude V14/V16 reports/reviews, old A/B answers, reference labels, error lists, and target outcomes. Use an explicit allowlist, never the whole review ZIP. Historical-source people/dates/facts do not become target-case facts.

## 5. Necessary code only

Create a versioned entry, preserving frozen methods.

| Planned file | Responsibility | Exclusion |
|---|---|---|
| `legal_bench/rules_verdict_v1/rule_application_v17.py` | Shared view, paired assembly, equality checks, citation recovery | No card edits, viewpoint selection, guessed outcomes |
| `scripts/prepare_v17_rule_application.py` | Allowlist, tasks/schema, hashes/order/freeze | No model start or directory overwrite |
| `scripts/report_v17_rule_application.py` | Two raw replies/review to comparison/failure/cost report | No hardcoded historical correctness or result deletion |
| `tests/test_rule_application_v17.py` | Few equality/recovery/no-overwrite/format tests | No expected eviction conclusion or real model preview |

These are planned names at this checkpoint, not claims of existing programs. Register `outputs/rules-verdict-v17-rule-application/` before implementation outputs. Do not create empty results or completed-experiment entries for a plan.

Reuse `contracts.validate`, original ID recovery, and strict import. Strip only recognizable Markdown fences and standalone END. Local wrapper-order handling cannot repair sentences, fields, counterevidence, or truncated JSON. Parsed strings must match raw JSON. Incomplete structures fail; full nonconforming text can support separate qualitative review, not structural success.

Keep `rule_transfer_v16.py`, `authority_index.py`, `final_v9.py`, and runtime byte-identical in round one. Existing point/assessment/explanation/reason suffice: assessment concerns point; reason explains legal consequences. No new court table, ontology, or final fields.

## 6. Offline engineering acceptance

Run only necessary assembly/import tests, not historical legal experiments:

1. Identical shared facts/law/examples/question/schema; B adds only original nine cards. Single insertion and exact base recovery.
2. Preserve all cards, unknowns/conflicts/exceptions/source nature/limitations. Exact source recovery; excluded target IDs invalid.
3. Missing citations, card-as-law IDs, duplicate IDs, and duplicate preparation fail without guessing/overwrite.
4. Recognizable wrappers may be stripped; ambiguous tails, missing fields, and open JSON cannot be completed. Complete JSON with empty grounds means missing decisive analysis, not automatic legal correctness or technical crash.

Check prompts/schema/counts/hashes/manifests. This is not semantic testing. Character counts are exact; website tokens/internal reading coverage are usually unavailable. Do not invent context headroom from characters.

## 7. Freeze, website execution, failures

After implementation/checks and before submission, save HEAD/branch/pre-existing changes, actual code/input hashes, final tasks/schema, ordinary High setting, A-then-B order, evaluation/stops. Plan-time audit is not an experiment freeze of unimplemented code.

At most two new independent ordinary High chats: one A, one B. No Pro, paid API, local generation, additional extraction, or retry. No shared chat history. Use the same visible model/mode and record actual UI; undisplayed model is null. Website execution cannot be described as local greedy/seed/thinking-off/token-schema constraints.

Prefer self-contained task files. Record sent text, attachment hashes/bytes, and visible content/preview without truncation/substitution. This establishes transport, not internal reading. Both instructions prohibit external retrieval. Do not regenerate formatting failures or discuss the plan before re-answering.

Observe at most 15 minutes/arm, 30 total, measured from submission rather than exact generation time. Timeout retains state/URL, no continuation prompt. A's format/truncation/timeout does not cancel independent B; access/framework failure blocking B records SKIPPED. Downloading an existing completed response is not new generation. B's task cannot change after A.

Separate technical_status, format_status, and content evaluation. Technical formal answers are null. Legal UNDETERMINED is not TIMEOUT/INPUT_TOO_LONG/OUTPUT_INCOMPLETE. Complete free text remains FORMAT_ERROR with optional qualitative review. External-source/history contamination invalidates/limits comparison without silent rerun.

## 8. One consolidated evaluation

Review decisive grounds in both final answers, not all nine cards or all facts again. Seal shared criteria before execution; historical error clues belong only to evaluation files. Originals are evidence; old V15/V16 reviews only locate issues. Preserve wrong old reviews and apply identical corrected criteria to both arms.

Check facts, speakers/court levels/stages, transferred object/licensor/dates, unsupported cross-jurisdiction/special-law/tentative-view expansion, decisive opposition omissions, changed AND/OR/necessity/negation, reliable facts erased by unrelated gaps, distinction between fact gaps/law gaps/model omissions, and consistency of point/assessment/explanation/reason.

Review decisive uncited material too: valid citations do not establish completeness. Calling explicit source content missing is omission/misreading; party views cannot be demanded as judicial findings. True unresolved facts/effects may remain unresolved, without guessing excluded target outcomes.

Each finding records arm, ground, exact model wording, source ID/quote, category, inference impact, and genuine interpretation dispute. Categories include SOURCE_MISREAD, ATTRIBUTION_ERROR, SCOPE_ERROR, OMISSION, INTERNAL_CONTRADICTION, FACT_GAP, LAW_GAP, TECHNICAL_FAILURE. No program adjudicator exists here; unimplemented software is not a legal-material gap.

Where correct arguments occur in both sources/cards, observed differences concern the net added-card input, not a specific program mechanism. B can reread originals; correctness cannot automatically be credited to cards. Cards add length/attention demands. Compute is not equalized and the isolated causal effect of structured format is not identified.

Evaluation is model-assisted source review, not human gold. Lack of human annotators does not block this development diagnosis or make model agreement truth. One case supports no accuracy leaderboard, corpus prevalence estimate, or claim of effective automatic retrieval/induction.

## 9. Investment decisions

| Observation | Decision | Next direction |
|---|---|---|
| B has a material sourced improvement without an equally serious new error | Retain added cards as a development signal | Later same-family new cases, not immediate ontology expansion |
| Equal quality, or A more complete/cheaper | Prefer original-text workflow; pause mandatory cards | Cards may remain indexing/offline-review aids |
| B improves some content but adds decisive error | Report both, no winner | At most one source-supported minimal change |
| Both preserve known content but share a true material gap | Benefit inconclusive due to sources | Identify missing material, not format repairs for nonexistent evidence |
| Both omit/misstate the same clear source | Shared comprehension/integration bottleneck | Pause more complex retrieval/execution; do not assume card fixes suffice |
| No complete pair or contaminated material | Insufficient technical/comparison conditions | Deliver failures/limits, no superiority claim |

Serious errors change applicability, turn necessary gaps into facts, confuse decisive status, or materially alter inference. Wording differences do not offset them in a summed score; numerous small positives cannot conceal one larger harm.

## 10. Conditional later changes, not simultaneous first-round work

These require a separately selected, source-confirmed primary defect and new version. They do not start automatically after two replies, and exposed-case reruns are not independent tests.

### 10.1 Decisive summary loss

If B misses outside-card content used by A or changes judgment through wrong summaries, improve coverage reporting rather than unlimited card counts. Retain detailed cards plus a bounded source-point directory: short proposition, source address, adopted/quoted/tentative status, and whether expanded into a card. Unexpanded points still link to sources; this is not new law or exhaustive coverage.

Define finite directory budgets and mark cap-induced incompleteness. Support, restrictions, exceptions, contrary views, and important quotations can all occupy slots; do not prioritize only final adopted conclusions. No case-answer hints such as “extract P10.” First check source tracing/unexpanded retention/nonfabrication on unrelated fictional sources, then separately authorize one bounded extraction test.

Potential new `rule_transfer_v17.py`/schema; preserve V16 fields/outputs. Success requires important distinctions in final analysis, not more cards/full directories.

### 10.2 Retrieval mistaken for applicability

This round has no top-k application, so it cannot prove ranking caused final error. Future automatic selection retains BM25 recall and separate assessments of issue relevance, statute/geography/time/stage compatibility, adopted versus tentative/quoted status, and supported transfer reasoning.

Allow UNKNOWN/DISPUTED rather than one binary score. Programs check verified metadata; models propose sourced analogy/scope judgments. Tentative views can be relevant without controlling merely through rank; other jurisdictions may be informative. Unmet conditions may support denial and do not justify deleting law.

Avoid invented court weights/precedence hierarchies. First record explainable candidates/scopes/coverage and missed/wrong transfers, then decide on learning. Requires new authorization, not an extra third selection call in the two-call round.

### 10.3 Shared final-answer omissions

If final synthesis dominates, keep extraction/retrieval unchanged. Later revise only responsibilities for support, opposition, and critical gaps under the same four-field contract. No current answers, court tables, extra reviewer models, or repeated six-sentence prompt trials.

Use complete fictional examples distinguishing established facts/unresolved effects and opposing arguments/judicial findings. Proceed only if consolidated review confirms the defect, not merely because all outcomes are UNDETERMINED. Stop after one frozen evaluation.

### 10.4 Genuine source/metadata gaps

Save sourced gap records, never invented facts. Copy actual structured metadata or propose locatable title/date text with evidence; do not infer court/statute/date from URLs or handwritten cards. Conflicting OCR retains bytes/dispute flags.

If applicability is blocked, acquire only directly relevant gap material, with rationale, permitted scope, and temporal relevance, not a corpus recrawl. This is source expansion, separate from card-input effects. New-case acquisition also has preset counts/sources, not repeated sample replacement.

### 10.5 Engineering failure

Minimal repairs affect new assembly/import only and reproduce with synthetic data. Keep original failures, no semantic/JSON completion or website re-answering. Post-run repairs cannot invisibly backfill current results; separately recomputed output is a development rerun. Rule misinterpretation is not a formatting defect.

## 11. Execution and stops

| Stage | Work | Gate |
|---|---|---|
| P0 | HEAD/dirty state, V14 base, V16 cards/sources | Reuse compatible tasks; missing/conflicting originals or scope failure stops preparation, no new retrieval |
| P1 | Paired assembly/recovery/report entry | Necessary checks; resolve shared-material differences before submission |
| P2 | Protocol/tasks/schema/hashes/evaluation files | Freeze; no reference/error-list leakage |
| P3 | One fresh A chat then one B | At most two; independent failure does not cancel possible arm; access/budget stops |
| P4 | Raw/structure/text preservation; decisive-source review | One review; no re-extraction/continuation |
| P5 | Complete comparison, investment decision, cost/docs/local review | End; no automatic section-10 changes/new samples |

The original request was a plan, so it made no model calls/application experiment. Local preparation can be independent; website tasks require actual authorized execution and are not completed by committing a plan.

## 12. Delivery and preservation

Planned execution delivers both complete answers/raw replies, actual tasks/schema, freeze/starting state, shared sources/IDs, card citation recovery, transport/run metadata, one source review, comparison/report, and stop record. Separate technical completion, support, decisive omissions, scope errors, contradiction, real gaps, conclusions, and input/wait costs.

Visible thinking time differs from observed submission-to-completion. Unavailable exact tokens/generation time/peak memory stay null; character estimates are not exact tokens. Report B's extra input and V16's three prior extraction calls separately. Two new answers do not erase prior extraction cost.

Original experiment sources/cards/failures/reports/freezes remain as run evidence. Register new outputs before publication inclusion. Update changelog/actual experiment index/state only for completed work, not plans. Prepare the bridge, inspect PUBLICATION, verify, and export locally. Preparation/export is not GitHub publication. No automatic commit/push; preserve existing uncommitted work.

## 13. Evidence and code pointers

- [V16 source review](../../../outputs/rules-verdict-v16-rule-transfer/final-source-review.json): omissions, scope, retrieval diagnostics.
- [V16 original collection](../../../outputs/rules-verdict-v16-rule-transfer/rule-collection.json): all nine cards for B unchanged.
- [V15 report](../../../outputs/rules-verdict-v15-rule-supplement/report-zh.txt): hand-selected-rule benefit/limits, not V16 evidence.
- [Actual V14 base](../../../outputs/rules-verdict-v14-web-direct/tasks/1134266/prompt.txt): task assembly source.
- [Rule interface](../../../legal_bench/rules_verdict_v1/rule_transfer_v16.py): historical lines 11–22 schema, 37–43 prompt, 60–76 checks, 79–92 retrieval.
- [BM25 entry](../../../legal_bench/rules_verdict_v1/authority_index.py): historical search lines 41–54; lexical candidates only.
- [Final template](../../../legal_bench/rules_verdict_v1/final_v9.py): historical schema lines 8–10, prompt lines 32–43; actual saved prompt remains authoritative.
- [Proposed protocol](protocol-proposed.json) and [plan-time audit](audit-at-plan.json): verified versus unimplemented/unrun work.
