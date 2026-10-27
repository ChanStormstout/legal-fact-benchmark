# Why these measurements

## The insight from the actual failure

The current system can lose content at three distinct places: source reading can
create a wrong relation; review can falsely accept it; and post-review processing
can remove a whole mixed paragraph, including its correct content. A final report
can therefore contain fewer false statements while answering less of the question.
Acceptance counts and citation-address validity cannot distinguish these cases.

The existing 1251841 development record illustrates the measurement requirement.
Under its **old posthoc Codex twenty-item rubric**, correct content changed from
6/20 in the C candidate to 3/20 in the delivered C report, while supported-assertion
precision rose from 16/33 to 8/12. Three correct requirements disappeared and the
repair object did not change. Those are retrospective model-adjudicated observations,
not independently validated legal gold or results under the new web reference.
They justify measuring content preservation separately from error removal.

The A0 answer covered more of that old list but also reversed a prior High Court
disposition. This is why a coverage score alone must not be presented as legal
reliability, and why one serious error does not automatically erase all other
measurable quality differences. The evaluation makes the tradeoff inspectable.

## Design choices and closest evaluation work

| Choice | Primary source and actual borrowing | Necessary change for this task |
| --- | --- | --- |
| Frozen important semantic units rather than word overlap | [RoSE / Atomic Content Units, Liu et al., ACL 2023](https://aclanthology.org/2023.acl-long.228/) studies fine-grained content matching and robust summarization evaluation | Our units answer a legal question and retain parties, property, stage and modality; the absence of human reference writers is explicit |
| Separate factual support, completeness and concision | [FineSurE, Song et al., ACL 2024](https://aclanthology.org/2024.acl-long.51/) evaluates distinct summarization dimensions using LLM judgments | We adopt the separation, not its task validity or an invented official harmonic formula; legal implications and source statuses require additional annotation |
| Inspect every asserted proposition, not just required facts | [FActScore, Min et al., EMNLP 2023](https://aclanthology.org/2023.emnlp-main.741/) decomposes generations and checks factual precision against sources | Our allowed source view may be incomplete; UNSUPPORTED is not real-world false, and allegation/finding/analysis have different entailment targets |
| Keep relation-level bindings and whole-report consistency | [D-FActScore, Chiang and Lee, Findings of ACL 2024](https://aclanthology.org/2024.findings-acl.160/) addresses entity-confounded factual evaluation | Correct isolated fragments must not hide a wrong plaintiff, court or procedural attribution; credit requires the necessary relationship and no unresolved reversal |
| Separate correctness from citation support/coverage | [ALCE, Gao et al., EMNLP 2023](https://aclanthology.org/2023.emnlp-main.398/) evaluates cited generation | No citation-style bonus in A0/C main quality; legal scope and authority entailment are checked, not merely presence of a source ID |
| Measure preservation as well as revision | [RARR, Gao et al., ACL 2023](https://aclanthology.org/2023.acl-long.910/) investigates evidence-based revision while retaining content | Our preservation unit is a source-correct legal requirement, not textual similarity; deletion, correct rewrite and new error are separate events |
| Use structured questions to locate omitted/wrong relations | [QAEval, Deutsch et al., TACL 2021](https://aclanthology.org/2021.tacl-1.47/) evaluates content through question answering | A question's premise and reference answer must themselves be source-supported; forcing a hidden judicial outcome is invalid |
| Keep exact error location and qualification | [QASemConsistency, TACL 2026](https://aclanthology.org/2026.tacl-1.6/) studies fine-grained semantic consistency | We borrow the diagnostic relation perspective, not its trained parser or reported performance on another task |

The full earlier survey and reading-scope evidence table are preserved in the versioned
evaluation artifact. The works above motivate measurement components. They do not
validate this new legal rubric, establish GPT Web as a gold annotator, or demonstrate
that a particular RAPIDO repair will work.

## Why not use only one familiar number

ROUGE or a similarity score can reward overlapping names and wording despite a
reversed court outcome. A free-form "which answer is better" judgment can hide
the weighting of completeness, false claims and legal severity. Required-question
accuracy alone ignores hallucinated extra content. Factual precision alone can be
increased by deleting almost everything. Strict whole-report success alone often
gives all development reports zero and conceals partial progress. Citation metrics
alone can reward valid source IDs attached to unsupported conclusions.

R, P and serious-error events cover these different failure modes. The auxiliary H
makes the coverage/precision tradeoff easier to scan but introduces an explicit design
choice about their balance. It has no universal legal interpretation. A severe
outcome inversion is still displayed even if H rises. Improvement decisions use the
registered components and guardrails, not whichever number looks favorable.

## What the proposed ground truth can establish

The current reference supports statements such as: "Under this frozen allowed view,
these source-grounded model annotations consider this relationship correct, missing
or unsupported." Exact evidence and preserved disagreement allow another reviewer
to challenge the judgment. Blind report IDs reduce known-method preference; a
source-only reference reduces direct output anchoring. Neither removes pretraining
case memory, model-family correlation, salience choices or subtle legal errors.

Repeated GPT agreement is not a substitute for an external gold standard. No expert
resources are assumed in the base study. If lawyers later review a stratified sample
including both successes and failures, freeze that extension, record inter-reviewer
disagreement, and estimate how model-reference conclusions change. Do not backdate
that future review to the current experiment or silently replace its labels.

## What is still a research hypothesis

Statistical bounds are also explicit design choices. The protocol's conservative
safety bound combines marginal exact binomial bounds; it does not pretend to exploit
the pairing. Clopper-Pearson is documented in the [SciPy statistical reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats._result_classes.BinomTestResult.proportion_ci.html).
The nominal sampling coverage assumes independent disputes and fixed labels; source
reference errors require separate disagreement/sensitivity reporting.

Keeping a complete draft, localizing a wrong binding, and repairing the relation
instead of rejecting a whole paragraph might improve supported coverage. It might
also preserve more hallucinations or introduce new dependencies. The current traces
support the existence of a preservation problem. They do not establish superiority
of the proposed replacement. Only a frozen end-to-end comparison, scored with the
same reference and retaining all failures/costs, can evaluate that hypothesis.
