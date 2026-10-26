# V9 full-judgment source extraction: real-run evaluation

V9 completed the single authorized case, 1251841, on the original Together Qwen/Qwen3.5-9B configuration. It delivered a complete source packet after 24 calls and 12 reading/review batches. This verifies technical completion of this extraction attempt. It does **not** establish reliable extraction, whole-C performance, or superiority to the teammate method.

## Execution and funding

- Elapsed: 1,187.71 seconds (19.80 minutes).
- Reported usage: 334,139 input tokens and 80,296 output tokens.
- New token-based cost: $0.07687763; all 24 calls reported usage and finish_reason=stop.
- No retry, new timeout, output-length stop, or new unknown-usage reserve occurred. Maximum completion was 7,701 tokens; the configured capacity was 65,536.
- The old V8 reserve of $0.04980736 remains included once in prior conservative spending, not added again and not represented as confirmed billing.
- Remaining in the original $0.60 scoped grant: $0.35905024. Conservative project accounting: $25.30310354, including historical exception authorizations and reserves; this is not an invoice reconciliation.
- All 1,538 protected hashes are unchanged. No second case, teammate rerun, training, default-entry switch, commit or push occurred.

## What improved and what remains broken

The source-ID interface works mechanically: every retained ID exists, and all program-attached source text matches the original exactly. The previous generated-quote mismatch cannot occur in this field. One review action replaces the redundant verdict vector, so the former all-components-supported/final-unresolved contradiction is absent by construction. These are narrow interface improvements, not semantic acceptance.

There are genuine localized content gains. B002.R0002 and B003.R0001 describe the lease grant as an occurrence, separate from its binding legal effect. B004.R0007 correctly attributes the partition allegation to Defendant 1. Review-004 withdrew two records that falsely attributed lower-court findings to the Supreme Court. Review-008 corrected a historical suit date from 24 December 1867 to the source-supported 12 March 1867, preserving the correction as a proposal.

However, the final packet fails content acceptance:

1. **The reader repeatedly ignores the assigned focus.** Of 169 initial records, 118 cite no focus entry. Every request contains the full original plus a focus list. The reader repeatedly summarizes other parts of the judgment; the program marks these records unresolved but still pays for review. The final packet retains six exact-content duplicate groups with eight excess copies, plus paraphrased repetition. Batch extraction removed the per-physical-line obligation but did not solve cross-batch repetition.
2. **Valid IDs still cite the wrong passage.** B003.R0005-R0007 cite L128 alone for defenses continued in L129. B004.R0017-R0018 cite L134 for validity and dismissal stated in L135. Review accepts them and even claims the selected line contains the missing wording. Program-resolved text is exact; model source alignment is wrong.
3. **Important semantic errors pass review.** B005.R0001 turns the question whether the mortgagor had permanent-leasing power into an affirmative legal argument. Its reviewer describes the question but keeps the assertion. B007.R0002 changes the mortgagee into the mortgagor inside a condition about taking security and allowing possession. Both have MODEL_REVIEW_SUPPORTED status. This status cannot be treated as correctness.
4. **Negation and qualifications are not consistently encoded.** B004.R0004-R0006 combine DENIAL with an already-negative embedded proposition, contrary to the prompt's positive-proposition convention. The same defense is represented with inconsistent polarity elsewhere. Examples and costs are labelled conditions, and some legal qualifications are incomplete. Downstream reasoning was disabled, so no actual downstream reversal is claimed.
5. **Full input does not yield complete extraction.** The interpretation records omit the original 1914 mortgage/Bank sequence, the conditional payment/cancellation and two amounts, the 1931 decree and 1936 delivery, and the unchallenged status of the lower-court findings. They also omit the general distinction between acquiring equity of redemption and having a lease binding on the mortgagee. Some originals remain embedded in source_text_by_id; saving those strings is not extracting the missing relations. D1's partition speaker is correct, but the supported partition record omits D2 as recipient; fuller versions remain unresolved elsewhere.
6. **Revision remains uneven.** It fixes a date and some attribution, but 17 replacement requests repeat the original unchanged. Other replacements add generic current-court attribution to facts from quoted historical litigation without preserving the originating-case identity. Changing a record is not necessarily improving it.

Final internal states: 44 MODEL_REVIEW_SUPPORTED, 9 REVISION_NOT_INDEPENDENTLY_REVIEWED and 102 UNRESOLVED, totaling 155 retained records. These are workflow states, not 44 correct versus 111 incorrect records. The source-grounded review identifies errors even among the 44. The packet remains downstream_enabled=false.

## Comparison with the existing teammate-method result

No teammate run was repeated. The comparator is the **V8 repaired local LatentWeaver adaptation**, using the same full allowed judgment and Qwen 9B; it is not an untouched upstream or native larger-model performance result. Both attempts are exposed development material, with unequal method call counts.

| Observed aspect | V9 | Existing repaired local LatentWeaver adaptation |
| --- | --- | --- |
| Technical artifact | Complete source packet | Complete canonical graph; semantic diagnostic reported valid=false |
| Actual lease grant | Correctly retained as occurrence | Narrative is correct but court_status=REJECTED conflates event and legal effect |
| D1 partition allegation | Speaker correct; supported record omits recipient, fuller records unresolved | Not represented in final graph |
| Original 1914 mortgage | Missing from extracted interpretations | Explicitly retained in node_fact_001 |
| Remaining legal question | One accepted positive assertion instead of question | node_legalissue_001 correctly remains a question |
| Final disposition | Correctly retained | Correctly retained |
| Other serious errors | Wrong source selection, accepted role inversion, inconsistent polarity | Unsupported deceased-mortgagor description; event/status conflation; source support issues |
| Calls / elapsed | 24 / 19.80 min | 4 / 3.52 min in summed call time |
| Token-based cost | $0.07687763 | $0.01731433 |

V9 has localized gains and losses. It costs about 4.44 times as much in this case and does not justify a claim of overall superiority. The 16-unit source reference is reviewed descriptively in unit-review.json; no composite accuracy or human-gold claim is fabricated.

## Cause and next decision

The experiment separates three limitations. (1) Focus is only requested in prose and checked after generation; out-of-focus records still enter review. (2) Source-ID validity and exact attachment establish traceability, not semantic alignment; the same model accepts interpretations based on nearby text and assigns the wrong ID. (3) Coverage, polarity and nested provenance remain incompletely represented or checked. No controlled experiment attributes these failures solely to model size, full-context length, or one specific prompt sentence.

The next repair should target focus ownership, source-supported assertion coverage, consistent polarity, and quoted-case provenance, with review directed at the exact candidate component and its selected original. It should not add more generic reviewers or quietly loosen acceptance. Preserve full original context but distinguish it from the text owned by each extraction batch. Verify on the source-extraction stage before spending on full C. Those changes were **not implemented or paid-tested in this V9 run**; the frozen method and outputs remain intact.

## Evidence

- [Run summary](private/run-v1/summary.json)
- [Complete source packet](private/run-v1/cases/1251841/ROLE/source-records.json)
- [Measurements and protected-file verification](private/evaluation-v1/measurements.json)
- [Source-grounded findings](private/evaluation-v1/findings.json)
- [All 16 reference-unit reviews](private/evaluation-v1/unit-review.json)
- [Readable record inventory](private/evaluation-v1/records-readable.jsonl)

The audit is a source-grounded Codex development assessment, not independent lawyer approval or human gold. This run used the complete supplied judgment, including its outcome; it is extraction, not hidden-outcome prediction. No full C report, RAG comparison, or baseline experiment was run here.
