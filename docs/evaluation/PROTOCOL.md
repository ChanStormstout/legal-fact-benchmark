# RAPIDO-EVAL-2.0: source-bounded report quality

## 1. The estimand and its limits

The primary question is: **For the registered question and permitted materials,
does the delivered C report correctly recover more important content than the
one-call A0 report, and what happens to errors, omissions, delivery and cost?**

The statistical unit is an independent dispute. One question and one primary source
view per dispute are selected before a prospective comparison. Multiple views,
retries, candidate reports, stages and seeds do not create additional independent
cases. Same-case appeals, duplicates and related proceedings share a split group.
All currently exposed development cases, including 1251841 and the earlier twelve,
remain development cases. Reconstructing a record that retains judicial reasoning
is not pre-judgment prediction. Missing target reasons or outcomes must not be
recovered from case memory, related cases, repeated quotations or evaluator labels.

The reference is conditional on the allowed view and question. It distinguishes
what the source records, what a party alleges, what a named earlier court found,
what a legal inference can support, and what remains genuinely open. Source support
does not mean a party's allegation is true or a lower court's holding is legally
correct. Rule-conformant computation does not certify the rule or its premises.

## 2. What is frozen before the next result

Each prospective run freezes the dispute groups and inclusion log; primary question;
full CASE/LAW/HISTORY access and supplied-source manifests; redactions and leakage
checks; source hashes and locations; reference items and acceptable alternatives;
annotation instructions and severity definitions; system and A0 versions; model,
provider and available version metadata; decoding settings; resource and retry
limits; endpoint selection; metrics and comparison rules; and analysis code.

A0 makes one ordinary call from its registered raw dossier. No evaluator-generated
reference or corrected intermediate state enters either method. C can use its
registered retrieval/reasoning/revision mechanisms; their calls and reading costs
count. If C accesses a historical corpus not supplied to A0, disclose the difference:
the comparison estimates the complete system's effect, including information access
and compute, not an isolated reasoning mechanism or same-information advantage.
Do not silently give A0 a retrieval or self-check pipeline to address this difference.
A separate same-information or cost-matched comparator requires user approval.

The current 1251841 analysis is retrospective. A new source-only web session can
reduce direct output anchoring, but cannot undo the project's earlier exposure.
Its new reference and scores must be reported alongside, not in place of, the old
Codex posthoc twenty-item assessment.

The saved V38 C continuation and the unchanged older A0 output are a comparison of
existing texts, **not a newly run same-configuration frozen batch**. Cache reuse,
earlier version changes and C's internal rule/history resources must remain visible.
Do not use this re-evaluation to claim a controlled module effect or silently describe
the old outputs as experiments under RAPIDO-EVAL-2.0.

Select new disputes independently of which method currently covers their law.
Register all screened inclusions/exclusions and group same-dispute appeals before
splitting source/rule discovery, development and held-out evaluation. Natural-distribution
and targeted challenge cases are separate strata with separate results; do not pool
them as population performance without predeclared sampling weights. Hidden labels,
outcomes and rule-discovery references stay outside runner access. Model/service
metadata are saved as actually exposed; an unverified immutable weight revision
remains unverified, even if the model's marketing name is unchanged.

## 3. Reference requirements and full-credit matching

For case i, the reference contains M_i nonoverlapping **important content units**.
Each unit has an ID, one assessable criterion, mandatory bindings/qualifications,
category, importance reason, and exact supporting source spans. Categories cover
issue/scope; parties/property; material sequence; competing positions; prior
findings; legal analysis and controlling objections/gates; and justified open issues.
Not every category or every date must appear in every case.

Units are selected for their effect on the requested reasoning, not to reward a
long chronology or a particular writing style. A list of irrelevant case facts is
not a reference. Split independently assessable requirements before seeing outputs;
do not split one favorable point into many after a method answers it. Near duplicates
are merged. Every item has weight 1 in the primary analysis. Alternative importance
weights, if studied, are separately frozen sensitivity analyses; they cannot decide
the main winner after results are known.

The match for an item is **CORRECT**, **NOT_SATISFIED**, or
**ANNOTATION_UNRESOLVED**. Full credit requires the asserted relation, necessary
actor/property, source attribution, stage, polarity and material conditions. A
topic mention, a copied source without answering the requirement, or correct dates
attached to the wrong actor does not earn that relation's point. Fluent wording and
literal reference wording are irrelevant. Each item earns at most one point.

Do not propagate one mistake to unrelated units: a wrong bank identity can invalidate
the transaction relation requiring that identity, but not an independent correctly
stated statutory date. Conversely, separate true fragments must not earn a complete
relation when their combined meaning is wrong. An unqualified contradiction of the
same item elsewhere in the report defeats its credit; distinct stages, party views,
alternatives and explicitly corrected statements are not contradictions.

An OPEN criterion earns credit for a useful bounded answer with the actual reason
for uncertainty. Withheld outcome, absent applicable law, conflicting permitted
evidence and technical failure are different reasons. Technical failure is never
evidence that a clear source fact is unknown. Do not require a definite answer when
the source view cannot support one. Do not reward UNKNOWN for a source-established
item. No partial 0.5 credit is used in the primary binary matching scheme.

## 4. Main metric: important-content coverage R

For a completely annotated case:

```text
R_i = correctly satisfied reference items / M_i
R_macro = sum(R_i over all registered disputes) / N
```

Report each numerator and denominator, percentage and category breakdown. Macro
averaging gives a dispute with a long rubric the same weight as one with a shorter
rubric. Also publish the pooled item fraction as a diagnostic, clearly labeled.
R measures **correctly answered important content**, not factual mention recall,
word overlap, number of citations, number of checks, or internal acceptance.

For u unresolved matches, retain denominator M_i and report
`R_lower = c/M_i`, `R_upper = (c+u)/M_i`. Do not remove disputed items to inflate R.
A technical/empty delivery has R=0 in the registered system evaluation; missing
annotation for an existing report is null/unresolved, not R=0. M_i=0 is an invalid
reference that blocks scoring, not a perfect answer.

## 5. Source-support precision P

Annotate all distinct substantive assertions in the report, including assertions
outside the reference. An assertion preserves necessary attribution, entities,
property, time, procedural stage, modality, negation and conditions. Separate
independent propositions, not individual names or words. Repeated paraphrases have
one assertion identity. A lengthy supported quotation must not be split into many
trivial assertions to dilute an unsupported legal conclusion.

Labels are **SUPPORTED**, **CONTRADICTED**, **UNSUPPORTED**, or
**ANNOTATION_UNRESOLVED**. CONTRADICTED conflicts with the allowed evidence;
UNSUPPORTED is not established by it, without implying real-world falsity. A
conditional legal analysis must have supported premises, appropriately scoped
authority and justified inference; adding "if" does not make arbitrary law supported.
A clearly marked question/hypothesis is not a factual assertion, but any embedded
claim remains assessable. Unsupported advice cannot evade assessment by changing tense.

```text
P_i = supported distinct substantive assertions / all distinct substantive assertions
```

With s supported, n total, and u unresolved: `P_lower=s/n`,
`P_upper=(s+u)/n`. Contradicted and unsupported remain in the denominator. If the
assertion inventory itself is incomplete, P is **not scoreable**; a subset of selected
errors is not a precision estimate. Save the full inventory and its completeness
declaration. A grader's complete flag is a claim to audit, not program proof.

An empty/technical-only report has no substantive assertions and P=null, not 100%.
Show substantive-report P conditional on delivery, its number of cases, and all-case
R/delivery beside it. For a separately labeled all-case **effective support** summary,
assign empty/failed cases 0 and average P over the registered N; do not call that
summary ordinary precision. Missing annotations are intervals, not failures. Report
unsupported and contradicted assertion counts as well as rates to expose denominator
gaming and verbose hallucination.

## 6. Auxiliary harmonic score H

```text
H_i = 100 * 2*R_i*P_i/(R_i+P_i)
```

Use H=0 for no substantive delivery or R=P=0. H is the project's **coverage-support
harmonic score**, not classical set F1: R and P use different inventories. It is not
the official formula of FineSurE, FActScore or ALCE. Its monotonicity permits bounds
from the component bounds. Average per-case H, not the harmonic mean of macro R/P.
H helps scan tradeoffs but cannot offset a critical error or select a winner against
the declared primary metric. Keep the historical v1 field named F unchanged and
document this terminology change; do not rewrite old scores.

## 7. Serious errors and main-answer adequacy

An error is **serious** if it materially changes the answer, the availability of a
remedy/path, whose rights are analyzed, or which court/stage made the controlling
decision. Record its exact output span, expected scoped relation, sources, category
and materiality reason. Categories include outcome/polarity reversal; consequential
party/property/court binding; assertion of hidden target reasons/outcome; invented or
inapplicable controlling law; a missed controlling procedural gate; or internally
contradictory guidance with a materially wrong branch presented as established.
Minor typos and legally immaterial dates are not automatically serious.

Pure absence of a required argument/gate is an **important omission**, separately
counted in R and objection coverage. It is additionally a serious error only if the
report asserts the resulting conclusion/remedy as available despite that gate. This
distinction prevents arbitrary error-count inflation. Unsupported current-tribunal
naming is unsupported; severity depends on what legal effect it asserts, not merely
that a name is wrong. Record uncertain severity rather than silently resolve it.

Repeated forms of the same false legal relation constitute one distinct error event.
Record multiplicity separately. Report (a) fraction of registered disputes with at
least one serious error, (b) distinct serious errors per case, (c) categories, and
(d) critical hidden-outcome violations. Failure and non-delivery have no observed
assertion error, but cannot be called a safe successful answer. Always show R,
delivery and error rates together, including a failure-or-serious-error fraction.

Main-answer adequacy is **SUPPORTED_ANSWER**, **PARTIAL**, **WRONG_OR_OVERREACH**,
**NO_SUBSTANTIVE_ANSWER**, or **ANNOTATION_UNRESOLVED**. SUPPORTED_ANSWER can be
a reasoned limited/conditional answer when the source view is genuinely open. A
correct main conclusion with missing required objections is PARTIAL. The grader
must give the decision-bearing source and explanation; no impressionistic 1–10 scale.

The strict **complete supported report rate** is a secondary endpoint: all important
reference requirements satisfied, P=1, no serious error, SUPPORTED_ANSWER and actual
delivery. Report it as a separate all-or-nothing criterion; it is intentionally
difficult and does not replace informative partial scores. With unresolved labels,
provide success bounds. This is source-reference-conditioned success, not legal safety.

## 8. Diagnostics that identify what to change

| Measurement | Definition and denominator | Use |
| --- | --- | --- |
| Important-objection coverage | Correct objection/gate reference items / all such reference items | Detect a report that tells only one side; NA if none |
| Binding/stage errors | Distinct assertion errors by actor/property/time/stage and counts of assessed applicable relations | Separate wrong relationships from missing content; publish counts and denominator |
| Citation entailment | Citation-assertion links that actually support that assertion / all links | Separate real evidence from valid addresses |
| Citation coverage | Assertions requiring evidence with sufficient correct citations / all such assertions | Diagnostic only when citations were requested comparably |
| Source-role fidelity | Correct attribution and claim/evidence/finding/analysis status on annotated applicable assertions / all applicable assertions | Distinguish a lower finding from a present holding |
| Justified uncertainty | Correct reference OPEN items / all OPEN items, plus known items incorrectly replaced by unknown | Avoid both fabricated certainty and all-UNKNOWN |
| Delivery/technical failure | Actual substantive delivery and failure counts / all registered slots | Separate program execution from useful reports |
| Cost and latency | All calls, input/output tokens, retries, caches, unknown-usage reservations, elapsed/active seconds | Explain quality-cost tradeoffs without free checks |

An existing source ID is not citation entailment. A0 must not lose main quality
points because it lacks C's structured citation convention. Both are checked against
the same evaluable permitted sources. Citation results are separate and show any
difference in instructions. No report is required to cite irrelevant history.

Cost accounting separates actual new billing, logical inference resources for the
stages used in that method, and cumulative research/development expenditure. Cached
model work is not a free reasoning step in the logical comparison; record its
original usage once, without charging the same invoice twice. Failed or timed-out
calls without provider usage retain a conservative reservation, not zero cost.
Unattributable carried costs are reported unknown with an explanation. Web annotation
is evaluation expenditure/time, not experimental inference: record its model,
timestamps and subscription/usage visibility separately; unavailable token counts
remain unavailable. More review calls must not be hidden outside the C budget.

Historical-use diagnostics classify each assessed opportunity as not retrieved,
retrieved but unassessed, assessed incorrectly, understood but unused, or used
appropriately/inappropriately. A retrieval miss needs a registered known-relevant
source pool; absent that, only observed retrieval/use can be claimed. Raw hit counts
or accepted analogies do not establish RAG benefit. Without a same-version corpus
on/off comparison, old-versus-new differences cannot be attributed solely to RAG.

## 9. Candidate-to-delivery preservation and repair

Grade candidate and delivered texts independently with the same reference and source
view. Link them only after blind grading. The delivered endpoint decides C versus A0.

```text
correct-content retention = |correct candidate items ∩ correct delivered items|
                            / |correct candidate items|
new correct content        = |correct delivered items − correct candidate items|
lost correct content       = |correct candidate items − correct delivered items|
```

Retention is NA when the candidate has no correct items. Report the set of IDs and
source evidence, not just a ratio. Preserve unresolved matching as bounds.

For each distinct candidate error, annotate exactly one transition: corrected
substantively; removed without restoring the content; unchanged; or unresolved.
New errors in delivery are a separate list. **Correction rate** divides corrected
candidate errors by all candidate errors; **removal rate** divides removed errors
by that same inventory. Deleting a paragraph is removal, not successful rewriting.
If one error was partly changed but its false legal relation remains, it is unchanged.
One-to-many rewritten claims must be explicitly matched. An assertion-inventory change
requires semantic alignment; comparing raw assertion counts alone is not repair.
Text/object identity detects no-change, not correctness. These diagnoses cannot be
substituted for a final report-quality gain.

## 10. Missingness, adjudication and reliability

Keep distinct: system technical failure; empty report; legal-scope limitation;
annotation not submitted; annotation unreadable/incomplete; semantic disagreement;
and missing/ineligible source. Every registered system slot stays in the denominator.
An evaluated report outside rule coverage is still graded for whatever its source
view can answer; it is not silently excluded or automatically fully failed.

Unretrieved web replies and unadjudicated items have null scores/bounds. A failed
experiment may have R=0 without a web grader; an ungraded existing report may not.
Aggregate bound formulas average the case bounds over N, assigning fully ungraded
existing reports [0,1]. Never report a partially annotated cohort as all-cohort 0/N.

Two fresh annotation sessions reduce direct anchoring but share model-family errors.
Record coverage-label agreement on the same frozen items, complete label-confusion
tables, Cohen's kappa where defined, and unresolved counts. When annotations have
different assertion segmentations, align inventories before calculating agreement;
do not compare unrelated claim IDs. Kappa can be undefined or misleading with severe
prevalence imbalance; publish raw agreement and marginal counts. Disagreement is
resolved only by an explicit source-adjudication record, preserving both raw labels.
Agreement is reproducibility evidence, not accuracy against independent legal gold.

## 11. Comparisons, uncertainty and claims

For one or two development cases, show paired item tables, R/P/H differences, serious
error events, answer status, cost and content transitions. No significance or
generalization claim follows. A higher score need not mean error-free; fewer errors
need not mean better if important content was lost.

For a fixed larger cohort, the primary estimate is the macro mean paired difference
`mean(R_C − R_A0)` at dispute level. Report paired dispute-cluster bootstrap 95%
intervals (10,000 resamples, frozen seed), raw pairs and annotation-uncertainty bounds.
If multiple source views exist, aggregate within dispute first. The prospective
quality target is an increase of at least 5 percentage points in R; this is a
development target, not an inherited claim about the earlier B=4 investigation task.
Freeze the sample-size simulation using pilot paired distributions before opening
test results; twenty or twelve exposed cases do not establish sufficient power.

For a confirmatory claim, require both a point increase of at least 0.05 in macro R
and a lower endpoint above zero for its paired 95% bootstrap interval. For serious
errors retain the earlier planning non-inferiority margin of +0.02 in case rate.
The default conservative safety calculation is a 97.5% one-sided exact binomial
upper bound on C's rate minus a 97.5% one-sided exact binomial lower bound on A0's
rate. Their difference is a simultaneous at-least-95% upper bound on the rate
difference (Bonferroni); require it to be at most 0.02. This valid conservative
bound does not exploit within-pair correlation. Publish the paired 2x2 event table
and a paired bootstrap interval additionally, without replacing the preselected
safety decision. Each binomial bound is Clopper-Pearson; for zero successes the lower
bound is 0, and for N successes the upper bound is 1. A pre-frozen alternative paired
method is allowed only in a new protocol before test access, with its simulation
and justification. Do not swap methods after an unfavorable bound.

Before confirmatory evaluation, simulate the joint paired R differences and serious
error outcomes from the development pilot (resampling whole disputes). Use 10,000
simulated cohorts per planned N with seed 20261027; choose the smallest N within
the authorized resource ceiling giving at least 80% estimated probability of
passing both criteria under the declared effect assumptions. Publish the pilot
distribution, assumptions and the power curve, including negative/zero-effect
conditions. Bootstrap planning from a tiny pilot is unstable: vary paired R variance,
event prevalence and discordance in a declared sensitivity grid. If power is
insufficient or resources are unavailable, do not open an underpowered test and
call its failure conclusive; stay at a descriptive development study. Safety power
may require far more cases than quality power. No confirmatory cohort or adequate
sample size has been established by this document. Any additional confirmatory
comparisons need an explicit multiplicity plan, such as Holm; do not silently inherit
the old two-comparator A/B/C protocol when the current comparison is A0/C.

The power calculation must include the **point-estimate** 0.05 hurdle as well as
the interval and safety hurdles. Under a true effect exactly at 0.05, increasing N
does not generally make the probability of a point estimate above 0.05 reach 80%.
Show alternatives at 0, 0.03, 0.05, 0.08 and 0.10 where feasible; do not report a
sample-size claim based only on detecting a difference from zero. Feasible paired
binary safety scenarios must respect both marginal error rates and their discordance.
With annotation disagreement, report score/risk bounds and how the decision changes;
sampling intervals alone do not quantify model-reference error.

A **Pareto observed quality improvement** requires no lower macro R, no lower all-case
effective support (with conditional P and its denominator also shown), no higher
serious-error case rate, no lower SUPPORTED_ANSWER fraction, and no lower delivery
fraction, with at least one of these dimensions strictly better. Equal coverage
with fewer errors can therefore be a real improvement. The primary research target
still requires an increase in R; a precision-only gain does not meet that target.
Display the main-answer category distribution
and pairs as well; do not turn its category names into an arbitrary numeric scale. If
metrics trade off, report exactly which improved and which worsened. H can describe
the tradeoff; it cannot erase it. A confirmatory advantage additionally needs the
frozen inference and safety conditions above; a point increase alone is not proof.
Costs remain a separate axis. More C calls do not establish same-cost superiority.

## 12. Change control

Freeze the reference, prompts, scoring version, adjudication policy and evaluation
manifest. Store raw annotations separately from source adjudications and calculated
scores. Correct a demonstrated reference error only in a new reference version with
a source-based rationale, before/after item mapping and complete regrading of all
methods; retain old scores. A reference bug discovered after unblinding is disclosed,
not hidden by calling the revised reference preregistered. No evaluator artifact may
be supplied as a model input in the scored comparison. New method versions receive
new runs; successful old calls and new calls cannot be repackaged as one frozen run.
