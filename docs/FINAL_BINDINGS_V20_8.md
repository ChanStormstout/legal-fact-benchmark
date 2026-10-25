# Final-answer sources and actor repair: V20.8 → V20.9.2

This implementation is independent of `legal_bench/historical_contrasts_v1/` and its tests. It did not change retrieval/GNN modules, old binding gates, the main experiment entry, shared index, or publication bridge, and did not train, commit, or push. Shared registration/entry wiring was left to integration to avoid concurrent side-chat writes. Local entries/results are in `outputs/proof-final-bindings-v20-8`; see its `report-zh.md` and `results.json`.

## Causes and repairs

The earlier 480-character truncation came from adding a limit to a shared text-schema object. Summaries/bodies must not inherit an auxiliary-field limit. V20.7's fix remains; literal rendering also avoids summary slicing, with length and original sentences checked separately. The old 1954254 free-generation service response ended prematurely for a separate, still-unconfirmed server-side reason. These failures must not be conflated.

Actor mismatches involve both interfaces and semantic review. Local OBJ:1 can identify different objects in different premises; merged-array positions are not identities. Earlier final inputs omitted full identity definitions. A claim's reporting/adopting court level was conflated with the final acting court's level. Old 569555/1187427 JSON already bound judicial decisions to landlords; parsing preserved those IDs rather than corrupting them.

`final_bindings_v20_8.build_bridge` assigns addresses including case, source snapshot, partition, premise, and original ID, with separate merged-position maps. Object-count/order/content/local-reference mismatches are rejected, not merged by name. Complete sources, claims, dependencies, old blockers, and rule states remain. Claim `reporting_court_level` differs from actor `court_level`; parties/governments have no court level.

New people, courts, government, property, events, and old-object identity links form independent candidates reviewed against complete sources. Judicial actors differ from affected parties; hearing courts differ from courts reporting the event. Government notice and retirement have separate event categories. New entities require new source reviews; renaming cannot promote blocked claims to accepted premises.

An accurate actor/event table does not constrain free text. In the first real V20.8 writing attempt, the table was correct but the summary attributed a lower-court finding to the High Court. That failure remains. Later old-claim selection exposed incomplete claim libraries and identity definitions. The current entry therefore uses V20.9's complete typed statement pack.

## Final writing and acceptance

`final_statement_pack_v20_9.py` stores each original statement sentence, actor, property, event, sources, role, adoption status, stage, and section. Sections cover summary, grounds, opposing views, and disposition scope/unresolved issues. Pack/event frame bind source/content hashes. Every statement must receive supported source review before entering the final task.

Qwen emits only statement IDs in order, with every statement exactly once and no new factual text. The program renders all sentences and the reviewed event table verbatim, preserving prior findings, party assertions, Supreme Court majority/dissent, and conditional UNKNOWN. Summary sentences retain attribution/stage. The final model cannot rebind actors, add assumptions, or silently omit reviewed statements.

`final_statement_review_v20_9_1.py` sends actual old-object definitions and old-address-to-source-line maps to whole-answer review. Machine IDs do not prove identity and need not appear in source text; reviewers compare definitions, sources, and new objects. Identity sources, every field, and all 11 coverage checks must pass before a formal answer. Missing review, wrong hashes, unresolved judgments, or technical failure leave null. Acceptance was not relaxed.

Re-review of 1187427 found retirement date and government-housing occupancy had been overcombined. A revision separates date from occupancy scope and rechecks the event frame, retaining all 26 original statements and API order. Whole-answer review of 569555 identified two missing disposition reservations and the joint judgment's effect on the original tenant Association. A new snapshot retains the original 22 statements, adds source-reviewed S23/S24, and corrects E03's affected parties.

`proof_final_statement_completion_v20_9_2.py` transparently replays those two additions from cache. The old 22 statements and model-order prefix must stay identical; additions must be reviewed disposition-scope statements and event changes must exactly match documented edits. The receipt states there was no new API call. This is not a generation rerun; whole-answer review must still be repeated.

All source judgments for 1954254 were supported, but review copied one hash character incorrectly. The program first rejected it. The website review session then extracted the binding from the original schema in Python and merged the unchanged review. Local checks confirmed that all 177 field assessments, 11 coverage checks, and reasons were identical; only the binding changed. Old rejection and corrected acceptance remain separate.

## Experimental boundaries and information flow

Seven real Qwen API calls ran: one free-writing attempt, three old-statement selections, and three typed-pack ordering tasks. Failed outputs, requests, service returns, frozen code, reviews, and cache replay remain. Free writing and ID ordering are different tasks; short ID output does not prove improved long-form truncation behavior.

All 85 engineering checks passed. Injected labels test software, not semantic accuracy. Cache comparison confirmed retention of full sources, 338 local claims, 171 global object positions, 509 accepted claims, 102 blocked claims, and dependencies. Statement packs include development model proposals and source-reviewed additions. Whole-answer review evaluates current-question coverage; information retained in cache is not necessarily displayed in the final answer.

Bridge files retain original claims/dependencies. Qwen ordering reads full sources, reviewed actor/event frames, and the current statement pack. Detailed old-object definitions serve identity and whole-answer review separately. Rule computation states remain in task/acceptance context. Source support does not change UNKNOWN to TRUE; case reconstruction is not an executable legal proof.

The original API cap remains $0.50. Isolated transport `provider_token_budget_v20_9.py` counts actual token-ID sequences rather than tokenizer dictionary fields. Inputs remain complete; failures fall back to conservative UTF-8 byte estimates. The current 1.5× margin plus 4,096 policy passed checks on seven observed requests, not every possible future input. Earlier 2× calibration remains; final calibration is separate. API cost excludes ChatGPT Web subscription use for source review.

These are engineering and model-source regressions on exposed development cases, not human gold, automatic extraction accuracy, unseen-test performance, paper-mechanism/GNN benefit, or lawyer approval. The unique server-side cause of 1954254's early termination remains unknown. ID generation and verbatim rendering now avoid regenerating long factual prose. The main experiment entry was not switched.
