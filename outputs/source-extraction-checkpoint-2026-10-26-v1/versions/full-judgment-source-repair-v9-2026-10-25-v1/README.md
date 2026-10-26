# Source-interface repair V9: prepared, not model-validated

This isolated version follows the preserved V8 development experiment. It changes source extraction interfaces, not the RAPIDO default entrypoint, rule library, model, or baseline. Case 1251841 remains the only scope; the original 139 rendered entries are supplied in every call. No model call has been made from V9.

## Concrete changes

- Extract each proposition once per source batch instead of filling one record container per physical line. Source-ID lists preserve all contributing fragments. The deterministic grouping and complete original input are unchanged from V8.
- Models select existing source IDs. The program attaches the exact corresponding original text, without model-retyped quotes, guessed offsets, or invented content. This establishes identity of the referenced text; it does not establish semantic support.
- Reviews have one action and its explanation. KEEP has no issue or replacement; REPLACE requires an identified issue and new records; WITHDRAW and UNRESOLVED require an identified issue. A second six-way pass/fail vector is removed. The output schema and consumer enforce the same branch contract.
- The immutable target snapshot, original records, retired records, corrections, pending gaps and original sources remain saved. Corrections and additions are not independently accepted. Unchanged replacements stay unresolved.
- Unary propositions may use null objects instead of inventing the string "null". Unknown times remain null. Allegation, denial, open question, occurrence, legal effect, scope and qualifications remain distinct in the representation.

These changes address observed communication/representation failures. They do not guarantee correct speakers, legal conditions, precedent treatment or complete reading. The experiment must evaluate those separately. No case-specific correct intermediate record is supplied to the tested model.

## Offline acceptance and experimental status

The complete synthetic reading/review consumer chain passed, as did original-text transport, declared source selection, revision application, unchanged-revision rejection, conditional records, null objects, schema factoring, and stale-snapshot rejection. This is engineering evidence only. The first generated request is 52,277 serialized bytes, compared with V8's first request of over 600 KB; source bytes are unchanged. This measures request structure, not expected quality or billed-token reduction.

V8 received a stream timeout with unknown usage. Its $0.04980736 reserve remains included once in prior accounting. The $0.60 grant has $0.43592787 unspent after both full-text attempts and the reserve. V9's launcher requires private/continuation-approval.json acknowledging that request before dispatch. Newly unknown usage will still pause further calls. No new grant is implied.

A proposed V9 run would execute only our repaired source reader once (24 logical calls before any authorized identical technical retry). The already completed, separately labelled V8 repaired LatentWeaver output is the comparison reference; it will not be rerun. This is sequential development on one exposed case, not a new independent benchmark or a clean one-factor ablation. All observed failures remain in the record.
