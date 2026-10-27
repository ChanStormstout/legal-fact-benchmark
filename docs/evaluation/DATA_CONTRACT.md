# Evaluation records and identities

No schema makes semantic labels true. These records make the observations,
judgments and arithmetic auditable and keep them out of experiment inputs.

## Required records

| Record | Required content |
| --- | --- |
| Run registration | protocol version/hash; cases and independent-dispute groups; task, source permissions, redactions, sample role, endpoint, method/model/settings/budget; frozen analysis and comparison rules |
| Source view | question and scope; source ID, domain, exact text, original file/document hash and locator, text hash, allowed state; history/current boundary; excluded/ambiguous materials and reasons |
| Reference | case/question/source-view identities; status and construction provenance; items with criteria, necessary bindings and source evidence; forbidden/unavailable information; alternatives and unresolved issues |
| Report manifest | case/group, random blind ID, relative report path, raw SHA-256, endpoint status, source-view and reference hashes; private mapping to method/run |
| Web job | prompt/attachment hashes, conversation URL, displayed model/settings, submission/read timestamps, output visibility, full raw response hash, extraction status |
| Labels | case, blind ID, report/reference/source-view hashes; every coverage item; full distinct assertion inventory and completeness; serious errors and completeness; main-answer category and evidence |
| Adjudication | raw-label hashes, changed item/assertion IDs, before/after label, exact source/output evidence, reason, assessor/date; unresolved issues retained |
| Scores | scorer version/hash; label/reference/report hashes; all numerators/denominators, bounds, per-case and macro values, missingness, cost and endpoint |
| Preservation | protected input/frozen-output hashes, newly created paths, experiment-started=false for evaluation-only work |

## Canonical label vocabulary

`coverage.status`: CORRECT / NOT_SATISFIED / ANNOTATION_UNRESOLVED.

`assertions.label`: SUPPORTED / CONTRADICTED / UNSUPPORTED /
ANNOTATION_UNRESOLVED. Each assertion has a stable local ID, exact report quote,
proposition retaining attribution/bindings, evidence and reason. IDs identify
annotation units, not experimental facts. Cross-report error/claim matching is a
separate semantic alignment.

`main_answer`: SUPPORTED_ANSWER / PARTIAL / WRONG_OR_OVERREACH /
NO_SUBSTANTIVE_ANSWER / ANNOTATION_UNRESOLVED.

`delivery_status`: SUBSTANTIVE_REPORT / TECHNICAL_FAILURE / EMPTY_REPORT /
NOT_RUN. A report with scope limitations is SUBSTANTIVE_REPORT if it provides a
substantive answer; coverage is scored normally and the limitation is recorded.
NOT_RUN remains in the registered denominator but is not counted as a completed
technical attempt. If the whole comparison was stopped before planned cases ran,
give both registered-slot and attempted-slot statistics; do not present it as a
completed batch.

`annotation_status`: NOT_SUBMITTED / SUBMITTED / IN_PROGRESS / RECEIVED /
INVALID / UNREADABLE / SOURCE_ADJUDICATED / UNRESOLVED.

Unknown legal state, unsupported assertion, uncertain annotation, missing reply,
and failed generation must never share a single UNKNOWN field.

## Hash and locator rules

Use SHA-256 of exact UTF-8 file bytes, retaining whitespace and newline endings.
Do not claim the web model computed a hash: the annotator copies the supplied
identity and the program checks it. Hash matches establish identity, not reading
completeness. Span offsets use half-open Unicode character positions in the saved
source text; original document locators remain alongside them. New text normalization
has a new hash and an explicit map to the original. Never normalize an old frozen
response in place.

The preserved example retains an upstream field named `text_hash`. In V38 that
field is SHA-256 of the canonical JSON **string value** (including JSON quoting),
not SHA-256 of raw text UTF-8 bytes. Its original meaning/bytes are retained.
`source-view-audit.json` separately supplies explicit raw `text_sha256` values and
checks the actual A0 text and reconstructed C witness passages. Do not interchange
these digest conventions. The v2 source-view file hash always identifies the exact
submitted file bytes, independently of inherited metadata fields.

Relative paths in published packages resolve under that package. Original private
absolute paths remain in local provenance when necessary, not as dependencies of
the public scorer. Raw provider/API headers, credentials, browser screenshots, UI
captures, unrelated personal data, third-party paper PDFs and model weights are not
published. Chat URLs stay in local provenance or a separately reviewed public job
record; a conversation link is not an immutable evidence archive.

## Reference/scorer compatibility

The small published arithmetic tool consumes `reference.json`, a report file and
a finalized `labels.json`. It verifies report/reference identities, source evidence,
all item IDs and label enums, then computes R/P/H bounds. It does not call a model,
change sources, declare semantic acceptance, calculate legal safety, or replace the
annotation/adjudication workflow. A complete statistical comparison additionally
needs the registered cohort, endpoint/method map, costs and paired analysis described
in the protocol. The arithmetic tool alone does not implement that whole workflow.

Version 1's twenty-point posthoc labels, original F field and scores are archived
unchanged. Version 2's stronger binding/contradiction rules and new web reference are
an additional evaluation, never a relabeling of the earlier numbers.
