# Real-judgment reasoning reconstruction V2

This stage reconstructs reasoning from the three teaching judgments in Student Implementation Guide 4.0. Models may read final reasons; final dispositions serve as comparators, never premises proving themselves. Results are not pre-decision prediction, independent legal testing, or legal certification.

## Interfaces and information flow

`prepare_sources()` reuses document-response boundary parsing to recover all three full texts. Every passage retains document ID, URL, original-response character/byte offsets, and line numbers; `tasks/*/delivery.json` maps text into actual tasks. Sources are public website presentations, not certified court copies. Underlying exhibits were not independently acquired. Cited precedents enter only through the target judgment's account.

Each case permits at most five ordinary High calls in separate temporary chats: rule draft, rule-source review, fact proposal, independent source reference, and derivation proposal. The reference sees full sources and the shared contract only, not drafts, proposals, checks, or old answers. The initial `freeze/config.json` remains. Scope-metadata and reference-isolation interfaces were revised before the first real certificate run, in `freeze/interface-01` and `freeze/interface-02`. Actual English contracts are in `realcase_tasks_v2_2.py`; entry is `scripts/proof_realcase_v2_2.py`. Only the reference task removed rule drafts potentially containing case analysis; compatible existing responses were reused without re-answering. Dynamic tasks record actual attachment hashes. No paid API, Pro, local inference, or semantic retry.

Rule drafts declare conclusion/input types, necessary roles, permitted statement status, time, stage, exceptions, and uncovered content. ALL/ANY express only sourced sufficient inferences. Failed antecedents do not imply false conclusions; negation requires a separately supported negative proposition/rule. Open legal assessments remain OPEN_TEXT, not automatically sufficient AND lists.

Premise truth and source status are separate. TRUE can establish the record “the court found ownership unproved,” without establishing that the party actually lacks ownership. Shared role names do not establish identity; actual bindings and required time scopes must agree. Premise-review decisions bind content hashes. Model references and maintainer source review remain model-assisted, not named legal approval.

Derivation slots explicitly reference original premises or previous steps. `realcase_engine.py` wraps original proposals without calling checker semantic decisions. Independent `scripts/check_realcase_certificate_v2_1.py` loads fixed snapshots/trust lists and checks source bytes, rule versions, proposition types, status, bindings, time, cycles, and finite combinations. Free-text jurisdiction/stage enters through separately saved content-hash-bound research scope review, not literal comparison with `India`. Each request retains its own result; incomplete dependencies do not block unrelated requests. Source existence/locatable quotation do not prove meaning.

Research states are VALID_UNDER_ASSUMPTIONS, INCOMPLETE, and INVALID; technical-failure answers are null. APPROVAL_PENDING is separate, does not alter known propositions, and is not counted as successful rejection of wrong derivations. This version produces no legally approved CHECKED result. Future approval requires a new record/snapshot, not retrospective alteration.

INVALID means incompatibility with this executable contract, not necessarily a false legal conclusion. A source-supported OPEN_TEXT assessment proposed as TRUE can fail result matching; this is execution coverage/state-interface failure, not identification of a false legal judgment. Quote location can also overreject punctuation/whitespace presentation. Original failures remain and corrections require new records.

Deterministic templates reconstruct final explanations without model supplementation. Free-text conclusions remain proposals; automated checks concern typed propositions/dependencies, not verified free-text meaning. Explanations show premises, counterarguments, limitations, sources, procedural results, and approval status.

## Evaluation

Evaluate source-to-certificate processing, before/after checking of the same cached proposals, and graph review ranking separately. First inspect decisive facts, attribution, rule translation, and scope; then valid-derivation retention, blocked errors, unsupported conclusions, and incompletion. Multiple derivations in one case are not independent cases. Synthetic and natural model errors are separate.

Graphs use proposed positive/negative relations with unit weights; dependencies are not support votes. Source order, simple unresolved-link/opposition-combination counts, and simple scores plus spectral local energy share nodes. Degree uses P+N; nonunique spectral axes/isolates fall back to simple ranking. Top-5/10 slots are allocated across components by node counts. Spectral scores change no facts, approvals, or certificates. Three cases establish interfaces, not review-efficiency gains or lawyer-hours saved.

## Stage gates

Complete three teaching cases and consolidated source review before deciding calibration preparation. Read at most 20 same-family candidates to select five calibration cases. A full 30 training (including those five)/10 development/20 sealed-test pilot remains planned. Old lease data do not automatically migrate; existing SEALED data remain closed. Four annotators, qualified legal reviewers, formal approvals, and sealed-test access are unavailable; multiple model sessions cannot substitute for those people.

Freeze once, run once, review once per batch. Semantic failures stay in results; do not tune individual prompts to success. Engineering changes require a separate version and affected-scope disclosure, not mixed frozen results. Preserve historical outputs, raw failures, and frozen bytes. This stage updates local documentation/review artifacts only, without commit/push.

Engineering acceptance uses real entries, 27 old scenarios, and new chained-dependency tests for source bytes, objects, time, status, local unknowns, AND/OR/exceptions, versions, empty requests, and no-overwrite behavior. Passing tests establishes only those behaviors.

## Reproduction

`proof_realcase_v2_2.py task|ingest|snapshot|run` refuses overwrite. Read delivered results rather than rerunning to update them. `scripts/proof_realcase_audit_v2.py` runs synthetic variants through the real independent checker. `scripts/proof_realcase_revision_v2.py` demonstrates explicit Rame Gowda S2 revision and historical S1 reopening. Neither calls a model.

`scripts/render_realcase_walkthrough.py` renders saved source-to-conclusion traces. `scripts/summarize_realcase_v2.py` aggregates submissions, cost, and before/after tables. Neither adds legal analysis. Exact website model versions, tokens, and internal reasoning times are unavailable. Records preserve High, separate temporary chats, and observation intervals, not precise inference cost.
