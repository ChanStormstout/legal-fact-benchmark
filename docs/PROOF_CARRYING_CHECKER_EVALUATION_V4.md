# V4: checking the same proposals and local revision

The main batch uses thirteen original requests from three v2 cases and v3's source-review
policy. Before/after views share one snapshot; maintainer-revised Sopan Q5 is not substituted
for the original. References come from earlier independent browser-source tasks; current
mapping/review is not blind and is not human gold.

`scripts/proof_checker_evaluation_v4.py prepare/run` freezes/runs diagnosis; completed
directories cannot be overwritten. V3 checker bytes remain unchanged.
reconstruction_view_v4.py separates unverified request prose from research-rule conditional
conclusions.

Complete-step hashes rejected semantically equivalent named-input orders/explanation
changes, while free request text escaped type checks. `scripts/proof_checker_patch_v4.py
prepare/validate` migrates semantic addresses in separate repair-01 without changing
rules/premises. The v4 checker reads that version. Execution-relevant fields remain fixed;
explanatory prose does not become trusted automatically.

Thirteen original requests,nine manually constructed controls,seven unit tests,six repair-
entry checks are saved separately, not combined into legal accuracy. The checker cannot
automatically understand sources; semantic acceptance already established by source
review is not its own semantic-error detection.

[Report](../outputs/proof-carrying-checker-evaluation-v4/report-zh.txt),
[Request comparison](../outputs/proof-carrying-checker-evaluation-v4/natural-comparison.csv),
[Source review](../outputs/proof-carrying-checker-evaluation-v4/source-review.json),
[Controls](../outputs/proof-carrying-checker-evaluation-v4/controlled-review.json),
[Repair validation](../outputs/proof-carrying-checker-evaluation-v4/repair-01/validation.json).
Retain checking/source review and proceed to planned calibration preparation, without
graph-model expansion.
