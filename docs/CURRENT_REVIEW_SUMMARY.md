# Selected review: RAPIDO V22 versus the ordinary baseline

This English navigation summary describes the published two-case development review.
The [original evidence package](../outputs/rapido-v22-baseline-pro-review-2026-10-24-v1/README.md)
retains its original records. Evaluation criteria were written after observing outputs;
this is a retrospective review, not an independent test.

| Case | Ordinary baseline A0 | Project method C | Evidence boundary |
| --- | --- | --- | --- |
| 1251841 | One call; 17.46 seconds; $0.00183987; final report delivered | 77 calls; 1,624.33 seconds; $0.4231378; report delivered, internal check failed, revision left the body unchanged | Both have source or reasoning errors; coverage has tradeoffs; whole-case superiority is unproven |
| 1252014 | One call; 25.82 seconds; $0.00207092; final report delivered | 43 calls; 1,563.20 seconds; read timeout during verification; no final report | C remains a technical failure in the denominator, with null semantic quality; A0 also needs review of procedural and legal-source errors |

Confirmed C cost across the two cases was $0.62965455, with a further $0.04980736
reserved conservatively for unknown usage. That reserve is not a confirmed charge.
A0 cost $0.00391079 in total. The other ten A0 results are historical inventory and
do not make this a twelve-case V22 comparison.

A0 is permitted raw materials, law, and the question followed by one ordinary Together
Qwen/Qwen3.5-9B call. C additionally uses history, rules, and computation. These extra
resources must remain explicit. Neither an internal PASS nor a source-reviewed model
reference establishes legal correctness. Independent Pro review is still pending in
this published snapshot.

Read the [questions and rubric](../outputs/rapido-v22-baseline-pro-review-2026-10-24-v1/QUESTIONS_AND_RUBRIC.md),
then the allowed sources and actual final reports before consulting the retrospective
assessments. The package includes actual requests, responses, frozen implementations,
source locations, and failures. It is a review snapshot rather than an automatically
runnable release. Translating this navigation does not run or alter the experiments.
