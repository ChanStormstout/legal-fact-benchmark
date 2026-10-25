# Research direction and experimental implications

On 2026-10-01, the user clarified that a benchmark had not been selected as the main
research output. The main question is whether rules grounded in a case's facts and
issues can help retrieve applicable authorities and support reasoned decisions in new
cases. The goals below were confirmed; the methods and experiments in this dated
note were proposals, not completed or frozen work.

## Objective and existing evidence

There are two objectives: identify statutory provisions, legal tests, and necessary
precedents applicable to the claim, issue, jurisdiction, time, and procedural stage;
and use facts and rules to explain whether requirements and defenses are established
and what claim-level or procedural consequence follows at that stage. Predicting an
outcome does not prove that the court's decision is the only legally correct answer.

The three early questions examine relationships between a sublet portion and the
whole property, between a separate action's initiator and the eviction respondents,
and between the tenant and that respondent group. These diagnose representation and
matching; they are not legal rules and do not demonstrate authority retrieval or
adjudication ability. Earlier experiments, failures, references, and configurations
remain separate evidence.

## Proposed method

Retain source assertions, identities and roles, statement status, qualifications,
field dependencies, and source traceability. Abstract facts for an explicit claim or
issue and check the abstraction against applicable legal conditions. Never change
source facts to obtain the desired prediction.

Distinguish descriptive fact patterns, source-checked rules expressly stated in
statutes or judgments, and candidate rules inferred across cases. Extracting an
express rule is not discovering a new principle. Cross-case candidates retain support,
counterexamples, and unresolved interpretations. Frequency and outcome correlations
do not automatically confer legal authority. Do not claim induction when the material
supports only extraction.

For development cases, link facts, issues, the court's applied rules, and their legal
sources. For a new case, propose candidate rules and authorities from the facts and
issues, then check the original provision, interpretation, effective period, and scope.
Combine conditions only within compatible complete entity bindings. Keep the source
stage separate from the current analytical stage. Permitted historical facts may inform
analysis, but overturned findings cannot simply remain accepted. Legal conditions may
identify missing evidence; they cannot manufacture facts. Open-ended reasonableness,
degree, and balancing judgments retain their model origin and disputed status.

Record authority relevance, scope compatibility, evidential status of conditions, and
legal consequences separately. A controlling authority can support rejecting a claim
when a necessary condition fails. Failure to retrieve evidence is not proof that a
condition is false. A two-event pattern-search limit does not limit the number of
conditions in a legal rule. See the [R2 design review](reviews/2026-10-01-pro-rgcn-v1-review.md),
[historical pipeline proposal](plans/rules-and-verdict-v1/PIPELINE.md), and
[implementation proposal](plans/rules-and-verdict-v1/IMPLEMENTATION_PLAN.md).

The legal-task workflow need not wait for global fact clustering or unrestricted
pattern search. Existing interpretable relations may serve as features and diagnostics;
rare but legally important exceptions must not be excluded for low frequency.

## Proposed evaluation

Separate historical development material from new-case inputs. Development may inspect
historical reasoning and outcomes to obtain candidate rules. New-case prediction may
use only facts, claims, issues, and materials available at the defined decision stage.
Exclude the target case's final outcome, decisive reasoning, and answer-revealing
citations. Precedent and statutory versions must also respect the designated time.
Existing judgments alone cannot establish real pre-decision evidence availability.

The original proposal distinguished authority retrieval, application of a given rule,
and the complete workflow to diagnose wrong authorities, rule translation, fact
extraction, entity binding, and application. Retrieval assessment checks provisions,
scope, and citation support; a court's citation list is not an exhaustive reference
set. Assess outcomes at the claim, issue, and procedural-stage level, separating merits,
procedural dismissal, remand, and partial relief.

The dated proposal included direct answering, answering with retrieved authorities,
and structured fact-and-rule application as distinct comparators, with cross-case
induction conditional on suitable data. These are historical proposals, not permission
to add mechanisms to the ordinary baseline. The current ordinary baseline is one LLM
call on permitted raw materials and the question; additional mechanisms require explicit
approval. Use the same tested model, information scope, and recorded resources within
each comparison. An initial 9B-model result cannot characterize all LLMs. Cross-model
claims require separate approved comparisons.

Limited supervision and incomplete interfaces motivated postponing GNN training from
scratch; transfer from pretrained graph models could be evaluated later. Check outcomes,
bindings, decisive conditions, and source-grounded reasons separately. More matches or
fewer UNKNOWN answers are not sufficient evidence of improvement.

Human annotators were unavailable. Browser-model references may be checked against the
sources but remain model references. Judgments supply historical outcomes, not proof
that every legal interpretation is uniquely correct. Report engineering tests, source
checks, reference agreement, and genuinely pre-decision ability separately.

## Historical next-step proposal and boundaries

The proposed starting point was one legally compatible eviction issue and at most five
existing development cases linking source facts, express rules, provisions, and condition
application. It proposed contracts and extraction formats, output/resource checks on at
most two development cases, followed by rule/authority storage and complete-binding
execution. After freezing, at most ten new cases would compare retrieval, application
under common authorities, and the full workflow. Cross-case induction depended on the
materials; GNNs and further-evidence feedback had separate entry conditions. Recording
these proposals did not start models, expand annotations, or change old experiments.

The professor's GlassBox material, page 12, discusses connecting patterns to authorities
and inducing element-based rules; page 13 discusses retrieving authorities and precedents
and predicting claim-level outcomes. This agrees with the objective but does not show
that the existing implementation completed every stage.

[Legal Rule Induction](https://arxiv.org/html/2505.14104v2) and
[NyayaRAG](https://aclanthology.org/2025.ijcnlp-long.92/) were cited as related work on rule
induction and externally supported legal decisions. They may inform comparisons; they
do not establish the effectiveness or novelty of this project's combination.
