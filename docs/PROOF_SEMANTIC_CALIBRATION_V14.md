# V14: evidence-use calibration and real-path interfaces

Local calibration only: no model calls, training, or TEST/SEALED access. Two existing
DEV paths retain original V13 P, its replay under explicit V14 contracts, and a separate
source-calibrated version. Sources and old grouping are unchanged.

`legal_bench/proof_carrying/use_contract_v14.py` separates use eligibility, direction,
whole-premise truth, and legal consequence. Background, partial support/opposition,
and reported allegations cannot individually establish a complete premise. Ambiguous
old uses stay ambiguous rather than being inferred from old labels.

`semantic_calibration_v14.apply_overlay` accepts only explicit versioned overlays:
role addresses, source-display corrections, and external premise-review receipts. It
checks the original snapshot hash and preserves P, evidence, use labels, rule propositions,
operators, and counterarguments. Source-review records establish role correspondence
and complete coverage; the program does not approve by name or similarity.

`scripts/proof_semantic_run_v14.py` saves the full snapshot, path, and acceptance policy,
then starts independent `check_semantic_v14.py`. The checker does not import overlay
assembly, references, or learned models. It checks citations, objects/stages/versions,
and component witnesses, then reuses explicit ALL/ANY/exception computation. External
premise truth comes from the declared research review policy; code does not re-prove
court judgments. OPEN_TEXT remains unexecuted; formal legal approval remains absent.

Case-specific roles and external premises are data, not case-ID code branches.
396336's F08 null quotation was not guessed; source calibration created a separate
court-assessment receipt. 594273's R5@1 semantic version was unchanged; a quotation's
initial-letter correction has an overlay, original value, and new hash, with frozen
rules intact. Hypothetical L125 rule background was not used to prove a real event.

`scripts/proof_semantic_calibrate_v14.py` verifies frozen code/material hashes and reuses
completed work without regenerating P or legal answers. Paths are in
`outputs/proof-semantic-calibration-v14/paths/`; use-flip dependency controls are in
`controls/` and do not count as naturally occurring corrections. The initial changelog
misread P's basis field; calibration-ledger-reviewed.json records actual fields and
the correction. Old logs/execution/receipts were not changed or rerun.

The twelve directly related test methods are in tests.test_proof_semantic_v14 and
tests.test_proof_semantic_v13. Engineering success does not prove legal correctness.
See [Report](../outputs/proof-semantic-calibration-v14/report-zh.md),
[Use contract](../outputs/proof-semantic-calibration-v14/freeze/use-contract.json),
[Calibration summary](../outputs/proof-semantic-calibration-v14/supervision-calibration-summary.json),
[Path comparison](../outputs/proof-semantic-calibration-v14/path-comparison.json), and
[Learning decision](../outputs/proof-semantic-calibration-v14/learning-decision.json).
Full sources/path snapshots/raw records remain local and excluded from publication.
No commit or push in this round.

These two paths do not justify an additional learned component or new use-classification
objective. Retain original P, shared checking interfaces, and historical GNN/CrossEncoder
implementations. Use eligibility has local value, but recovery here came from role/source
calibration, not demonstrated use correction. Two cases cannot estimate generalization.
