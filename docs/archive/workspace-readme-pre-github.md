# Legal AI benchmark pilot

This workspace contains historical research material and a local Legal AI benchmark pilot.
The latest completed diagnostic is `outputs/unknown-two-case-study-v1`. It studied exactly
1982777 and the first shared-UNKNOWN new case, 500624; it introduced one explicit
source-reviewed type-only projection mechanism for six implicated records. All original
scope/status/polarity/object/time blocks survive. One rerun of the existing 30 questions
changed five B UNKNOWN results to NOT_FOUND; B now has 16 UNKNOWN and 14 NOT_FOUND,
with zero matches. The other eight cases and every direct answer remain unchanged.
This includes local source-review intervention and is not an automatic-method accuracy gain.
See its `report-zh.txt`, `case-traces.json`, `summary.json` and `related-tests.txt`
(51 related tests passed). No new web task or whole-case extraction was performed.

The completed original exploratory run is `outputs/new-10-pattern-matching-v1`: 10 new full-source judgments,
three unchanged prior queries, independent direct web answers and single-pass structured extraction.
Both methods returned zero full matches. The executor returned 21 UNKNOWN and nine NOT_FOUND;
type cooccurrence returned 16 candidates at the case/question level. Three fixed sampled
bindings from two cases received one bounded source review; the review supported rejecting
identity as proper group membership. No overall accuracy or positive transfer claim is established.
See `runs/first-run/report-zh.txt`, `report-detail-zh.txt`, `results.json` and
`status-complete-v1.json` under that directory. This round stopped without modifying the method.

The preceding completed run is `outputs/development-20-typed-relations-v2`: the same 20 full-source
judgments and 277 primary-request records, with source-supported direct `part_of` and `member_of`
relations added separately. It executes cooccurrence, exact identity and typed-relation searches,
with all candidates and traces preserved. The fixed six-binding model source audit is complete;
138 program tests passed. These are development results, not independent test accuracy or human gold.
See `runs/first-run/report-zh.txt` and `status-complete-v1.json` under that output directory.

The preceding single-pass run remains unchanged at `outputs/development-20-single-pass-v1`.
Older five-case A/B experiments and 100-case source/screening work remain saved under
`outputs/benchmark-pilot*`. No formal check set has been frozen. The new exploratory orchestration is in
`scripts/run_new10_exploration.py`; the prior development commands are in
`scripts/run_typed_development.py`. Older commands below retain their original schemas.

## Completed new-case exploratory run

The sample, tasks, protocol, source copies, prompts and core code hashes were saved before
new answers. Associations not already resolved remain marked; these are new documents,
not proven independent disputes. Six ordinary High web tasks were submitted, with no Pro,
paid API, format repair or repeated model request. The interface did not expose an exact model
identifier. All raw JSON downloads, task packages, conversation URLs, times and screenshots
are retained. Unknowns and unsupported results are not negatives; the cooccurrence diagnostic
does not answer the full relationship question. References are model judgments with source
review, not human gold.

The original exploratory command was:

```sh
python3 scripts/run_new10_exploration.py run
```

Its frozen-code guard now intentionally refuses the amended current core; the original method
is retained in that run's `method-snapshot/` and the completed original results are unchanged.
The completed diagnostic script `scripts/run_two_case_unknown_study.py` reuses its completion
record rather than issuing a second run.

`prepare` reuses the existing freeze; imports accept saved downloads; `prepare-audit` reuses
the bounded selection. No operation in these scripts sends a web request. The report is a
completed delivery artifact; the report generator writes a new timestamp and should not
overwrite its immutable completion record. No additional test round was run with unchanged
core code. The deliverable retains every candidate binding and failure/unknown trace.

## Run locally

Python 3.9+; the core uses only the standard library. No model API, browser scraping backend,
paid service, or neural model dependency is installed or called by this package.

```sh
python3 -m unittest discover -s tests -v
python3 -m legal_bench --help
python3 -m legal_bench audit --input '/Users/victor/Downloads/land 1.jsonl' --out outputs/benchmark-pilot/data
python3 -m legal_bench prepare --source outputs/benchmark-pilot/sources/1064407.full.json --pass-name A --out outputs/benchmark-pilot/tasks
```

`audit` resumes only for identical input bytes. JSON outputs are immutable: an identical rerun
is allowed; changed outputs require a new path/version. Original JSONL and historical reports
are not modified. `runs.jsonl` records input hashes and command provenance.

## Web annotation workflow

Use **GPT-6 High, non-Pro** in a fresh ChatGPT web conversation for each A/B pass.
The source judgment and the exact generated task prompt must be supplied in full.
Pass B sees the same source/protocol but not A's answer. Code must not issue hidden ChatGPT requests.
Save the exact reply in a text file and observed metadata in JSON:

```json
{
  "conversation_url": "actual conversation URL",
  "model_display": "6",
  "effort_display": "High",
  "submitted_at": "actual ISO timestamp",
  "retrieved_at": "actual ISO timestamp",
  "prompt_sha256": "hash from the task JSON"
}
```

```sh
python3 -m legal_bench import --task TASK.json --source SOURCE.json --reply REPLY.txt --metadata METADATA.json --out IMPORTS
python3 -m legal_bench validate --annotation IMPORT.json --source SOURCE.json --out VALIDATION.json
python3 -m legal_bench compare --a IMPORT_A.json --b IMPORT_B.json --out DIFFERENCES.json
```

Import retains raw invalid replies and flags repair requirements. Only enclosing Markdown fences
are stripped; semantic content is never silently edited. Syntactically valid JSON still needs source
and field checks. Quotation support does not establish semantic correctness or completeness.
The current prompts/schema are in `legal_bench/tasks.py`; exported versions accompany each run.
Review uncited paragraphs as well as disagreements; allow at most two targeted semantic review
rounds per discrepancy, then retain uncertainty. References are model-generated, not human gold.

## Source and representation contracts

The existing dataset's segmented fields are candidate-discovery material, not a full-text gold source.
Source import preserves printed PDF page boundaries, text hash and provider URL. Connector text
exports and original PDF bytes have different hashes and must not be confused.
The source-completeness flag requires observed consecutive page footers and inspection of the
beginning and terminal disposition. Scanned/unparseable PDFs need a separate verified extraction.

Every event stores local unit/object IDs, source evidence, polarity, speaker, court status, optional
event date, attributes and unresolved modifiers. Role equality does not establish object identity.
Unknown identities are null. Different object IDs are only appropriate for separately resolved
objects; unresolved coreference must not be encoded as certain inequality.

`abstract` applies a versioned, model-reviewed, task-specific type/alias registry. It retains all
source events and source fields. Ambiguous and absent mappings remain explicitly UNMAPPED.
This first implementation does **not** generalize numeric values or discard fields.

## Query language

```json
{
  "atoms": [{"var": "n", "type": "NOTICE"}, {"var": "p", "type": "PAYMENT"}],
  "constraints": [{"op": "same", "left": "n.roles.property", "right": "p.roles.property"}]
}
```

Atoms default to COURT_FOUND/POSITIVE. `status`, `polarity`, and a specific `event_id` can be set.
Supported constraints are `same`, `different`, `before`, `equals`; references select `roles.KEY`,
`attributes.KEY`, `time`, `id`, `status`, or `polarity`. Unknown values do not compare equal.
Distinct variable names do not imply distinct events; mined two-event queries explicitly require
different event IDs. Exact ISO dates alone support time order. No arbitrary code execution,
sum, payment allocation, reversal state machine, legal sufficiency, or closed-world inference.

Results are MATCH, UNKNOWN, NOT_FOUND, MISMATCH (fully specified failing event pair), or UNSUPPORTED.
A MATCH is a qualifying witness in this record, not a legal conclusion. Conflicting/negative
assertions are separately returned for review. Unknown modifiers block that event's use
conservatively; another complete witness can still match. The legacy executor blocks an unresolved record conservatively. The opt-in v0.3
executor supports explicitly reviewed field projections, but their value is not
yet established by an independent benchmark. Unreviewed diagnostic runs do not
create or impersonate those review approvals.

## Experimental commands

`split` consumes reviewed eligible cases (case_id, dispute_group, eligibility_evidence, group_review),
five explicit dev IDs, and deterministically samples other groups with seed 20260930.
The CLI defaults to `--check-count 100`; `--check-count 20` reproduces the original plan.
`freeze` checks the manifest's explicit target counts and snapshots supplied config/protocol/query/code files.
`evaluate` on check data requires matching frozen query bytes and case assignments.

`mine` only accepts a development manifest. It generates two-event shared-object patterns plus
one optional time/attribute condition, canonicalizes variable permutations and logs the unexecuted
frontier after 1000 candidates. It counts primary analysis units, not mentions. It is a bounded
search, not a complete enumeration of legal patterns. Support >=2 marks repeated patterns.
Generation and execution are separated, but the current finite candidate generation still takes
quadratic event-pair work; the execution budget is not a total-runtime guarantee.

`evaluate` runs relational queries, type cooccurrence and three diagnostic ablations. `score`
reports macro case agreement with resolved model references, excluding disputed labels visibly;
missing runs are listed rather than silently scored as success. It does not claim human-gold accuracy.
Object-binding/semantic evidence comparison requires the saved source anchors and separate review;
the automated score currently covers status agreement only.

The real 6–10 query conditions and normalized registry must be developed from the five web-annotated
cases before freezing. Do not substitute the synthetic payment examples in the tests for this step.

## Five-case local diagnostics before reference review

The reviewed scoped executor, the legacy diagnostics and the conditional
accurate-input experiment are separate paths. None manufactures review
decisions. The legacy strict diagnostic blocks nonempty scopes and unresolved
records; the scope-blind variant remains an explicitly unsafe baseline.
`conditional_engine.py` instead checks dependencies of each field under an
explicit accurate-annotation assumption. It preserves scoped records and does
not claim global legal truth. Unregistered restrictions remain blocked.

```sh
python3 scripts/run_development_experiments_v03.py --out outputs/benchmark-pilot-v03/experiments/NEW
# Replay uses snapshot inputs and config, not mutable latest annotation paths.
python3 scripts/run_development_experiments_v03.py --snapshot outputs/benchmark-pilot-v03/experiments/five-case-unreviewed-v2 --out outputs/benchmark-pilot-v03/experiments/REPLAY-NEW
python3 scripts/run_native_pattern_diagnostic_v03.py --snapshot outputs/benchmark-pilot-v03/experiments/five-case-unreviewed-v2 --out outputs/benchmark-pilot-v03/experiments/NATIVE-NEW
```

The completed report is `outputs/benchmark-pilot-v03/experiments/five-case-unreviewed-v2/report.txt`.
The primary draft vocabulary and all native predicates are evaluated separately.
Matching native predicate/role names is only syntactic comparability, not proven
semantic equivalence. Candidate frontiers remain saved when the budget truncates
search. A/B versions are separate corpora, never additional independent cases.
That earlier run passed 67 program tests and reproduced 55 deterministic JSON
files. It remains preserved; reference scores are pending.

The current algorithm repair is documented in
`outputs/benchmark-pilot-v03/experiments/conditional-repair-v2/report.txt`.
It adds field-dependent uncertainty, one/two object joins and an independent
finite-language exhaustive oracle. Hand-expected synthetic checks are 51/51;
the previous whole-record baseline is 41/51 on those same controls. A/B are
separate five-case input versions. Core search candidates and case-level support
are checked independently; native syntax search remains bounded to 1,000
executed candidates and retains the frontier. These are conditional program
results, not natural-case accuracy or a frozen benchmark score. Distinct record
IDs do not establish distinct real-world events; same-type repeated pairs remain
explicit review candidates. That repair passed an 82-test suite under Python 3.9.6.

```sh
python3 scripts/run_conditional_repair_v03.py --snapshot outputs/benchmark-pilot-v03/experiments/five-case-unreviewed-v2 --out outputs/benchmark-pilot-v03/experiments/CONDITIONAL-NEW
python3 scripts/report_conditional_repair_v03.py --run outputs/benchmark-pilot-v03/experiments/CONDITIONAL-NEW
# For an interrupted run only, repeat the first command with --resume.
```

The run checks input/code hashes before resuming, stores immutable input and
code snapshots, and saves independent candidate, binding and support checks.
That conditional run preceded the completed side-chat source audit. Its
accurate-input assumption is kept separate from the approved-field path below.

## Source-reviewed five-case development run

The side audit now covers all 401 FACT/PROCEDURAL_ACT records. Its ten hashed
views approve 212 scoped records, including 12 without object-role permission.
`reviewed_pipeline.py` builds 14 explicit task type cards, preserves original
definitions and source assertions, and transfers permissions and uncertainty
with role renames. It never promotes an unapproved role, date, amount, or status.
`scoped_mining.py` now uses the tested one/two object-join generator on reviewed
seed cells. The accurate-input path grants none of these permissions.

The current report is
`outputs/benchmark-pilot-v03/experiments/source-reviewed-five-case-v2/report-v2.txt`.
The original eight queries and all generated candidates were executed separately
for A/B. Core discovery has zero repeated candidates; the declared extended
business/procedural vocabulary has 22/7, predominantly procedural structures.
Same-type record pairs and court-only joins remain visibly flagged, and these
counts are not legal usefulness or benchmark accuracy. Legal states are kept for
explicit fixed queries but excluded from CORE/ATLAS observable-event discovery;
the native profile remains a syntactic control.

Core and extended candidate sets agree with independent finite-template
enumeration; all generated candidate bindings and support counts agree with an
independent interpreter. The development run passed the then-current 91-test suite under Python 3.9.6.
That run changed no source annotations or side-review files and made no new web tasks or
paid API calls. The subsequent expansion targets 100 new cases; model-answer baselines
and a frozen check evaluation remain future phases.

```sh
python3 scripts/run_reviewed_development_v03.py --out outputs/benchmark-pilot-v03/experiments/REVIEWED-NEW
python3 scripts/report_reviewed_development_v03.py --run outputs/benchmark-pilot-v03/experiments/REVIEWED-NEW
# For an interrupted run, repeat the first command with --resume.
```

## Current 20-case development run

The original five four-case extraction tasks returned through ordinary ChatGPT Web. All 20
cases imported, with 277 usable primary-request records; 96 companion or other-request records
remain outside this computation. Exact source quotations, isolation decisions and unresolved
dispute links are retained. The UI exposed ordinary High mode but no exact model identifier;
metadata preserve that limitation. Independence is not certified.

The v2 iteration keeps these records unchanged and adds a targeted web review of existing
objects: 8 supported direct physical part relations, 9 supported direct person/group membership
relations, and 2 unresolved part proposals. Missing relations remain UNKNOWN. Relations are
directional, do not imply identity, and do not propagate group acts or whole-building properties.
No original unknown field or restriction is overridden.

Support remains at least 2 documents and the budget is 1,000 canonical candidates per pool.
All 212 cooccurrence, 450 identity and 65 new typed candidates were executed; respectively
113, 205 and 3 repeat in at least two documents. All 318 previous repeated-query support counts
replay unchanged. The 205 identity variants form 96 display groups by types, states and operator;
role variants remain distinct queries. These display groups are not semantic fact clusters.

Six fixed selected typed bindings were supported by a fresh web source review. This is a small
same-model diagnostic, not an accuracy estimate. The three earlier extra cooccurrence examples
still fail exact identity but have supported member/part connections. Different operators answer
different questions; additional matches alone do not establish superiority.

All 727 candidates and 14,540 query/document traces are saved. The compact trace references
resolve to immutable input copies; failures and unknowns are retained alongside matches.
`runs/first-run/summary.json` is the pre-audit computational snapshot; the later
`status-complete-v1.json` and `runs/first-run/completion-summary-v1.json` record audit completion.
The report corrects an earlier description of 76 combinations: that older count omitted state.

```sh
python3 scripts/run_typed_development.py run --out REPLAY-NEW
python3 -m unittest discover -s tests -v
```

Use a new output path; the existing run is preserved. Full findings are in
`outputs/development-20-typed-relations-v2/runs/first-run/report-zh.txt`, all query strings in
`all-patterns.txt`, and structured candidates, witnesses and sources in the adjacent JSON files.
The 100-case work remains separate and is not a prerequisite for this development run.

## Recovery and limitations

The 100-case expansion is saved separately under
`outputs/benchmark-pilot-v04/sampling-v1`, preserving the original five-case results.
Its fixed random order contains 1,006 summary-keyword tenancy-possession candidates after
excluding the five development IDs. The first 150 source texts and all 15 full-context screening replies are now saved.
At `status-v5.json`, all 15 replies have passed structural and exact-source-anchor
checks; after the earlier request-family review, there are 113 eligible, 34 ineligible
and 3 uncertain model references. These counts are not selected independent disputes.
The cross-document reply for 120 candidates plus five development documents is saved,
with 28 full-source-review flags. Its import was refused: the prompt had not explicitly
required a primary entry in `associated_disputes`, and the reply lists companions only;
two companion proposals also lack source quotations. Bounded repair tasks are prepared,
not submitted. The other 30 candidate records still require cross-document coverage.
No final check sample, method freeze, new fact annotations or new check experiments
have been completed. See `progress-v5.txt` for the actual remaining steps. That historical checkpoint had 108 passing tests; the current suite has 138. Sources retain an
initial pending terminal-content review flag;
consecutive printed PDF pages alone do not certify a complete judgment. Native Chrome
submissions have per-task URLs, screenshots and hashes; prepared tasks are not submitted
tasks. Eligibility screening produces neither fact annotations nor experiment answers.
Accepted cases require source-supported eligibility and separate cross-case dispute
review, including links to the five development disputes. Sampling is random within
the keyword candidate pool, not across all Indian Supreme Court cases.

```sh
PYTHONPATH=. python3 scripts/prepare_hundred_case_screen.py
PYTHONPATH=. python3 scripts/import_screening_sources.py
python3 scripts/import_screening_reply.py --batch screen-001 --reply /absolute/path/to/download.json
python3 scripts/extend_screening_sources.py --first-rank 131 --last-rank 140
python3 scripts/import_grouping_reply.py --batch group-review-v1 --reply /absolute/path/to/group-review.json
python3 scripts/checkpoint_hundred_case_screen.py --version a-new-checkpoint-name
```

Existing versions are preserved, changed inputs are refused, and model replies are
not silently rewritten. Source-anchored screening still needs grouping review before
selection. Reference labels remain model-generated, not human gold.

No real model annotation or accuracy result exists until a saved web reply and provenance has been
imported and checked. PREPARED does not mean SUBMITTED. Source/connection failures are recorded in
the status report. Do not replace unavailable GPT-6 annotations with Codex-generated labels.
After reconnection, reuse the existing source and pending tasks; do not repeat successful downloads.

For the new check sample, further work includes final dispute grouping, method and sample
freeze, two independent annotations, query reference answers and the predeclared comparisons.
The five-case development registry and local experiments remain available separately;
they are not results on the new check set.
Cross-model generalization, prospective prediction and downstream legal tasks are outside this pilot.
