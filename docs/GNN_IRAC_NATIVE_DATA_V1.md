# IRAC-native data and input graphs V1

This stage discovers new candidates in the existing database rather than continuing repairs to the old eight cases. Scope remains Delhi Rent Control Act section 14(1)(b). Rules are supplied; rule retrieval is not evaluated. Historical decision fields serve candidate discovery only and must not be copied directly into future model inputs.

## Data order and boundaries

Fix at most 16 candidates before independent screening. Construction starts only with at least six eligible candidates and covers at most eight cases. Order: independent rule decomposition, stage assignment, blind binding, target construction, independent source review. Rule decomposition sees only the issue and independent legal sources. Blind binding sees frozen rules, conditions, and permitted source records. Targets are constructed separately after all blind bindings freeze. Every step retains raw responses and freeze hashes; review feedback is not used for repeated revisions until success.

`inputs/<case>.json`, `targets/<case>.json`, and audit files are separate. Citations use separate `{source_id, quote}` objects, each a continuous passage. Location matching permits whitespace equivalence only; it does not repair OCR, negation, or meaning.

## Executable interfaces

`legal_bench.rules_verdict_v1.irac_native_schema_v1.load_input(path)` validates input or raises `ContractError`. `input_from_case` explicitly selects only envelope `input`, without changing its fields or reading target. `validate_targets` is a separate supervision-audit entry, never graph features.

`legal_bench.rules_verdict_v1.irac_graph_builder_v1.build_input_graph(input_record)` accepts input only. Nodes are Issue, Rule, Condition, Fact, Evidence, and Entity. Edges use sourced explicit relations and frozen proposed bindings. CLAIMED, PRIOR_FOUND, UNKNOWN, and other states remain. Candidate SUPPORTS means that the record, if established, supports a condition; it does not mean judicial acceptance or condition satisfaction.

All records/sources follow one stage policy. PRE_TARGET_RECORD, PRIOR_COURT_FINDING, and TARGET_STAGE_PARTY_ARGUMENT are permitted; TARGET_COURT_REASONING, TARGET_DISPOSITION, and AMBIGUOUS are prohibited. Prior findings retain court level rather than becoming target-court acceptance. Excluding an object recursively excludes dependent records, retaining originals/reasons in audit. Missing objects are not fabricated.

Input-root fields are fixed; target/audit fields are prohibited. The stage sidecar stores only `policy_version`; actual stage information belongs to records. Nodes use stage, statement status, object type, party role, court level, polarity, availability, source markers, and text. Encoding, training, gradients, and model evaluation are not implemented here.

## Meaning of validation

Tests cover target isolation, graph-hash invariance to target changes, stage permission, cascading endpoint exclusion, unchanged bindings/sources, independent rule sources, segmented quotations, UNKNOWN retention, and failure of proof versus factual falsity. Synthetic fixtures verify interfaces, not real cases or canonical within-group artifacts.

Source location and software checks do not establish legal meaning. Real cases still require independent source review and complete-chain admission; successful graph construction is not automatic READY. No training, SEALED access, commit, or push.
