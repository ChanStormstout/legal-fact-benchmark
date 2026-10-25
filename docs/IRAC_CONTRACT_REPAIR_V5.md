# IRAC V5: contract repair and two-case end-to-end acceptance

Round complete: engineering E passed; factual organization M and full answering L did
not. Two cases/eight local calls produced two proposals/six complete answers in19.31
minutes, with no retries, web calls, new training, or publication.

[Report](../outputs/irac-contract-repair-v5/continuation-01/report-zh.txt),
[Answers](../outputs/irac-contract-repair-v5/continuation-01/answers.md),
[Source review](../outputs/irac-contract-repair-v5/continuation-01/final-source-review.json),
and [E/M/L acceptance](../outputs/irac-contract-repair-v5/continuation-01/acceptance.json)
are separate. Original V5 engineering checkpoint and V4 outputs/failures are unchanged.

contract_v5.py reuses legal condition addresses, scoped limits, and source ordering,
separating evidence storage from computational eligibility. Every record retains position
and value. Missing bindings, invalid uses, and source-address problems affect dependent
computation without deleting original text or other valid uses. Empty readable proposals
can continue to source-based answering; technical failures stay null. Structural checks
do not prove proposal meaning.

`scripts/irac_contract_v5_run.py` is the freeze/run entry, using execute_slot →
finish_attempt → process. Twenty-two tests passed; fifteen real-tokenizer examples/five
constraint regressions reused unchanged schemas/constraints/materials. Eight actual
input-delivery checks passed; all thirteen records retained, one cross-binding limitation
isolated. B/C share the same unchanged new proposal; C additionally receives deterministic
checks.

M still splits one arrangement by legal issue/finding and misaligns source records/use
direction; all six uses in188721101 point to the time condition. B locally corrects some
errors but retains/adds unsupported inferences; C has no reliable extra net benefit.
All six answers predict rejection, which is not correctness. No GNN training occurred;
these results do not refute all graph methods.

Actual code is continuation-01/freeze/code; parent engineering/snapshot is an earlier
checkpoint and cannot be substituted. Completed freeze refuses overwrite; run only
reuses compatible saved results and does not retry partial output. No next-round
authorization is implied. Relevant checks are tests.test_irac_contract_v5,
tests.test_irac_contract_v5_run, and `scripts/irac_contract_v5_run.py preserved`.

One model-assisted source review, not human gold. Sources, outputs, checks, and gaps
remain traceable. All2,426 old files and generation/schema/source/authority hashes match.
