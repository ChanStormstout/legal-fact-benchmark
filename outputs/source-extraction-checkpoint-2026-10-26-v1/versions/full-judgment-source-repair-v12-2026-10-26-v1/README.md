# V12: source extraction repair and one-document verification

V11's first two calls produced actual records, but its third call repeatedly emitted
the same source ID inside one array despite the transmitted `uniqueItems: true`.
The request was stopped and retained as USER_INTERRUPTED. V11 is a failed development
attempt, not a successful comparison. Its confirmed cost is $0.01121597 plus an
unknown-usage reserve of $0.04980736. Nothing from that run is overwritten.

V12 additionally bounds every reference set by the number of supplied choices and
detects repeated references within the same streaming array. A set over N IDs cannot
legitimately contain more than N IDs: this does not remove sources or cap substantive
prose. Reusing a citation in different records remains allowed. The frozen saved-stream
replay covers both complete V11 responses and the complete received failure prefix.

The V10 six-document run was stopped at the user's request. Preserve its completed
V9 extraction, failed local LatentWeaver adaptation, all V10 partial outputs, and
the interrupted transport. The predecessor summary calls interrupted V10 unrun;
`private/predecessor-stop.json` records the interruption without changing that file.

## Confirmed defects and unresolved causes

1. Prompt schema factoring treated a field-name map containing `type` as a schema
   node. The displayed schema could contain `properties: {"$ref": ...}` even though
   the hosted decoder received a valid, different structure. Round-trip equality
   had missed this defect. It is a confirmed implementation defect, not proof that
   it alone caused empty model answers. Validate both actual representations.
2. V10 allowed `records: []` with `MATERIAL_CAPTURED` coverage. It also asked the
   model to connect independently enumerated unit and source identifiers. Actual
   replies omitted known events, claimed supplied units were absent, and cited
   judge-name lines for unrelated propositions. Originals were present in the wire.
3. Coverage explanations became a competing output channel for facts. A technically
   valid response was mistakenly easy to obtain without useful extraction.
4. Exact repetition and repeated target identifiers were not sufficiently prevented.
   Source agreement, an existing citation, and JSON validity still do not prove truth.

## Changes

- Factor only actual JSON Schema positions; preserve property-name maps literally.
- Present each original passage beside its stable identifier, grouped into ordered
  source units. All source characters remain in every call, once; no hidden answers.
- Return records inside program-owned unit keys. Main citations are restricted to
  that unit. Component support can use the complete source for antecedents/context.
- `MATERIAL_CAPTURED` requires records; layout-only rows have none. Partial unresolved
  records remain possible. Narrative, metadata and headnote content are extractable.
- Derive only ownership and the union of MODEL-SELECTED citations in Python. No
  semantic value, corrected identity, legal answer or ACCEPT is filled by code.
- Preserve raw duplicate outputs but compute exact-identical records once. Distinct
  opposing claims remain separate. Semantic paraphrases require model review.
- Key reconciliation and final-review decisions by immutable target IDs. Readings
  stay independent; reconciliation and final review use originals and direct records.
- Preserve accounting for a keyboard interruption. SIGTERM or `private/STOP` requests
  stopping between calls after saving the current response.

## Staged experiment and limits

Run V12 once on full rendered judgment 1251841 with the same Qwen 9B service and
parameters. Reuse the already completed same-input V9 and LatentWeaver artifacts
for descriptive comparison; do not pay to recreate them or modify the comparator.
This is extraction only, not full C or A0, not independent generalization evidence,
and not a native LatentWeaver reproduction. No training, git commit or push.

The previous approved $6 envelope covers this repair continuation. V10 accounted
$0.21896736 and V11 accounted $0.06102333, each including its interrupted request's
$0.04980736 reserve; never add those reserves twice. At most $5.72000931 remains.
Only the first case is enabled. Expansion is gated on whole-document review.

Inspect actual records, source attribution, participant relationships, denial,
court/procedure, legal conditions, duplicates, omissions and unresolved coverage.
Compare recovery of important source content as well as serious errors; an empty
packet cannot pass by avoiding assertions. Do not call same-model support human gold.
If empty or mismapped readings persist, stop expansion and retain the negative result.
Do not repeat this frozen case until it passes or edit this version after dispatch.

Offline acceptance replays a complete previous extraction without corrected legal
answers or semantic acceptances. It establishes interface compatibility only.
The first real run must decide whether the changes improve source extraction.
