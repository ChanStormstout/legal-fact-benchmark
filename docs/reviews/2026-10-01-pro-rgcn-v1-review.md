# Review of the GPT Pro dual-R-GCN proposal and implementation sequence

Date: 2026-10-01. This is a design review and proposed implementation, not a frozen method or new experimental result. Code baseline: `31d9813649b67b1796afd26518845ba6b82848d5`, branch `research/rules-and-verdict`. Reviewed user attachment SHA-256: `13c90c254319c14853659ec2e4bdf61f7582d3be57b524acd7675acc62080cbc`.

R2 revises the reasoning and implementation recommendations following the user's account of GPT Pro's comments. [Original R1](2026-10-01-pro-rgcn-v1-review-r1.md) retains its original review text and SHA-256 `992913c45d496836bfb400122d212b9b64f9bea0324b07d00dd35020a80a554a`. Revision is not implementation or experimental validation. This English rendering preserves the historical proposal; comparator recommendations here do not override the current requirement for an ordinary single-call baseline without added mechanisms unless explicitly approved. Linked literature and product specifications are historical references, not newly reverified claims.

## Assessment

The proposal aligns with the objective: connect case facts, issues, legal conditions, and authorities, evaluating legal retrieval separately from claim-level decisions. Retain provenance, object binding, statement status, unknown handling, source versions, candidate-recall failures, out-of-fold retrieval, and same-information controls. It specifies inputs, supervision, and losses for both graph models; it is more than two unnamed GNN boxes.

Do not implement the whole design simultaneously as V1. Rule provenance/admission are unclear; existing relation-diagnosis data lack supervision for both legal tasks; task interfaces/comparable controls are unfinished;35B/vLLM migration is unverified locally. First complete a reviewable chain: explicit statutory/judicial rule extraction → retrieval → application with full bindings → claim conclusion. Add cross-case induction only when material supports it. Insufficient supervision/comparison conditions justify postponing dual-GNN training from scratch; extraction errors do not prove GNN ineffectiveness. Pretrained graph-retrieval transfer remains a candidate.

This review changed no algorithm, model configuration, labels, or historical results, and launched/downloaded/trained no models. Unfinished `local_chunk_v11.py` was excluded from this design/publication.

## What existing code and evidence support

`field_pipeline_v2.py` has sourced known fields, field-level restrictions, type-first filtering, binding witnesses, and unknown candidates. `typed_relations.py` supports directed `part_of`/`member_of`; missing edges stay unknown and identity cannot substitute for either relation. `scoped_mining.py` implements budgeted two-event pattern search. These are reusable, but not a legal engine supporting arbitrary AND/OR, quantifiers, exception priorities, burdens, or amounts.

The latest complete same-configuration A/B development comparison at that time was v3: eight cases,13 questions, all five reference-positive questions missed, including one truncated B generation. v10 was an additional two-case diagnosis: one of two MATCH results was source-supported and one was not. In123036, landlord personal-use need became subletting during extraction. Even correct edges can then match incorrect facts. Semantic extraction and group representation both cause problems; errors can propagate to executors, LLMs, or GNNs. This does not rank those approaches or estimate an overall error rate from two cases. See [v3](../../outputs/local-qwen-pattern-eval-v3/report-zh.txt) and [v10](../../outputs/local-qwen-pattern-eval-v10/report-zh.txt).

## Component assessment

| Component | Rationale | V1 requirements and treatment |
| --- | --- | --- |
| Case + claim + stage | Avoid compressing multiple claims/appeals into one win/loss | Fix the disposition for the current claim. Separate merits, procedure, remand, and partial relief. Do not force three classes on binary issues. Evaluate historical agreement separately from legal correctness. |
| Input isolation | Target reasons, outcomes, and final citations must not leak | Check derived summaries, adoption status, node text, filenames, and embeddings. Complete historical training reasoning may be usable; target reasoning is not. Retrospectively curated facts support conditional application, not predecision prediction. |
| Fixed LLM + structural constraints | Separate extraction/prediction; JSON Schema makes outputs readable | Initially retain9B/MLX to control changes. Claims apply to that configuration. Repeat key controls on a different capability/architecture before cross-model claims. Valid structure does not establish semantics; allow OTHER, emptiness, and unknowns. |
| Chunked extraction + local review | Bounded calls can cover full texts |4,000/400-token windows do not solve cross-chunk identity. Add case-local registries, sourced aliases, overlap deduplication, and unresolved coreference. Shared roles do not merge identities; overlapping text is not a new event. Retrieve relevant context, not answer-bearing summaries. |
| DefinitionCard mapping | More controllable than corpus-wide pairwise merging; retains instances | Definitions do not prove completeness. Save ambiguities, unmapped facts, and mandatory qualifications. Definitions revised using training answers are learned artifacts subject to splits. |
| Relation-pattern search | Reusable variable joins; original facts/rare exceptions remain available | Keep patterns descriptive, not legal rules. Start with two events. Before2–4-atom search, specify operators, global budget, expansion order, and unexplored space. Count verified dispute groups. Unknown relations do not establish independence; unknown matches cannot justify unsafe pruning. |
| Authority library + RuleCard | Correct distinctions among versions, jurisdictions, definitions, exceptions, necessity/sufficiency | Separate statutory text, express judicial rules, and cross-case hypotheses. Record adopted/distinguished/rejected/quoted status. Express language is not universally binding. Store originals separately from machine interpretations and source-review status. |
| BM25 + vectors + RRF + text reranking | Parallel original/structured queries may mitigate extraction omissions; historically proposed as an enhanced comparator | Fix corpus/version/encoder/reranker inputs. Track known-relevant retention at200→40→8.20/20 quotas/top8 are development budgets, not legal completeness. Necessary dependencies exceeding budget remain incomplete. |
| LawRanker | Relation types and issue conditioning have a research basis | Train from scratch once supervision exists and ranking is a located bottleneck; separately test pretrained transfer when data are sparse. Compare text reranking, no-graph MLP, and graphs on identical inputs; distinguish transfer/local training. |
| Condition execution + semantic assessment | Makes binding, status, and exceptions operational | Combine conditions within full compatible bindings/assumptions, retaining witnesses. Two-event mining limits do not cap legal-rule conditions. Separate unknown evidence, unsupported execution, no match, and legal consequences. |
| VerdictNet | Separate training helps locate errors; retain raw predictions | Not a mandatory V1 decision maker. First compare fixed LLM/simple classifier/applicable executor on the same condition table, then test message-passing gains. Post hoc GNN explanations are not necessarily faithful. |
| Bounded feedback | Distinguishes missing law/facts/interpretive disputes with stop budgets | Start with no feedback, then one explicit gap investigation. Retrieve support and opposition, recording changed conditions/results instead of only supporting the initial verdict. |
| Supervision, out-of-fold retrieval, evaluation | Unknowns are not negatives; candidate misses count as failures; noisy inputs and same-information ablations matter | Learned rules, definitions, patterns, and thresholds must also be learned within folds. Five folds/three seeds require sufficient disputes/labels, not mechanical application. Unjudged candidates cannot silently count as irrelevant. |

## Separate explicit extraction, cross-case induction, and descriptive patterns

R1's blanket prerequisite of “real case-rule induction” was too strong. Express judicial standards can be extracted directly. What must be explicit is origin, transformation, and permitted use. When generalization data are insufficient, reliable extraction/reuse is a valid bounded target.

| Artifact | Suggested provenance | Supported claim |
| --- | --- | --- |
| Express source rule | RuleCard `origin_kind=EXPLICIT_STATUTE` or `EXPLICIT_JUDICIAL` | Legal analysis after checking adoption, context, scope, and authority; demonstrates extraction/reuse, not discovery of a new principle. |
| Cross-case candidate | RuleCard `origin_kind=CROSS_CASE_HYPOTHESIS` | Preserve generalization steps, support, counterexamples, and limits as a hypothesis. Frequency confers no legal force. |
| Descriptive relational pattern | Separate PatternCard, `origin_kind=DESCRIPTIVE_PATTERN` | Organizes/retrieves/compares facts without assigning legal consequences. |

These field names are proposals, not schema changes. Every RuleCard should retain issue, jurisdiction/time/stage, variables/conditions, necessity/sufficiency/factor status, effects, exceptions, evidence, and open interpretation. Provenance is distinct from semantic verification and authority. Outcome associations remain empirical associations, not legal rules.

“Same lease” also needs provenance: an express judicial requirement, a condition's parameter constraint, or a technical guard against invalid joins. The latter two are not automatically newly discovered legal rules. Arrears under K1 and notice under K2 invalidate that notice's binding, not every possible notice; other notices must be checked.

When data suffice, use four development-only induction steps:

1. Extract issue, adopted propositions/reasons, key facts, authorities, stage, and outcome, separating party claims, quotations, rejected propositions, and adoption.
2. Propose a few candidates within compatible statutory versions, stages, and interpretive scopes. Shared issue names alone are insufficient; patterns suggest candidates, not legal content.
3. Inspect similar-fact/different-outcome and same-outcome/different-reason neighbors. The latter challenge necessity only if a condition is demonstrably absent/negated; nonmention is not absence. Record support, true counterexamples, incompatible scope, and insufficient information separately.
4. Allow at most one sourced local revision of conditions/scope/exceptions/bindings. Prediction errors trigger review, not automatic semantic rewriting. Preserve unresolved counterexamples rather than querying until agreement. Freeze before checking other cases.

Support counts describe coverage, not authority. [LRI/SILVER §3](https://arxiv.org/html/2505.14104v2) uses strict-majority support and does not fully address complex defeasible rules; borrow its proposal/check/update workflow only. [RLJP §§3.4–3.5](https://arxiv.org/html/2505.21281v1) informs difficult-case selection, but its FOL rules are interpreted by an LLM with candidate labels, not deterministically executed legal proofs.

## Preserve complete bindings and the basis of legal consequences

Each rule execution should retain rule version, current claim/stage, allowed scope, assumption branch, full bindings, supporting/opposing condition evidence, source witnesses, coverage/gaps, execution capability, and the rule licensing the consequence. Independent yes/no checkboxes are insufficient.

For `exists k: arrears(t,k) AND notice(n,t,k)`, both facts must share a lease. K1 arrears and K2 notice cannot fill separate boxes. AND joins compatible bindings; OR retains distinct branches/witnesses without mixing exclusive assumptions. Failure of one binding does not refute others. Save full witnesses when a match exists; preserve unknown when unresolved combinations could still satisfy the rule.

Store source stage, current analysis stage, and event time separately. Appeals may use trial-stage notice/payment records if visible and still accepted. Vacated findings are not automatically current accepted facts. Historical facts must not be categorically forbidden.

“No witness found” is relative to materials/query scope. Refutation needs counterevidence or justified exhaustive checking over an explicitly complete domain. An empty query result does not prove that domain complete. Refuting notice N1 does not refute existence of another notice. Burden rules can connect proof status to consequences only with recorded legal authority, never a program default.

Implement expressiveness required by selected real rules. The target interface includes typed variables, AND/OR, explicit negation, date/number comparisons, and sourced exceptions; these are not all current capabilities. The first milestone implements only necessary operations while retaining the full condition tree. Negation is not database absence; numbers need units/values and dates need applicable computation rules. Unknown exceptions, complex quantifiers, balancing factors, or uncompiled conditions retain text/limits and go to explicit model assessment or unsupported-execution status. Do not drop conditions and claim complete success. Unsupported execution is not insufficient sources.

Two-event limits apply to pattern search only. A five-condition sourced rule retains/handles all five without first expanding open pattern mining to five events.

Authority records separately answer: relevance to the issue, compatible scope, evidence state under the binding, and licensed legal consequence. Failed necessary conditions may explain dismissal, so controlling law must not be removed simply because a condition fails. Compare retention/pruning to test this transfer risk empirically.

## Roles of the two R-GCNs

R-GCN propagates information over typed edges. Basis sharing is an established mechanism; issue gating weights relation types according to the issue. Three layers,256 dimensions,four bases are starting settings, not locally established optima. [Original R-GCN](https://arxiv.org/html/1703.06103v4).

`g_r(q)` applies one weight to the same relation type under an issue. It does not itself distinguish individual edges; node contents/aggregation must do that. A nearly fixed issue may produce nearly fixed gates, so it cannot establish cross-issue adaptation. Required depth depends on actual paths/readout; inspect key-condition path lengths before adding layers.

Connecting A,B,C does not encode `A AND (B OR C)` explicitly. Rule cards/execution records must retain logic and variable bindings. Graph scores do not replace necessary-condition checks. Repeating one assertion across source/fact/pattern nodes is not independent corroboration.

Separate training is reasonable; identical architectures are optional. Test LawRanker first because errors map to specific candidate authorities. VerdictNet learning curves require condition tables, claim labels, differing outcomes, and enough nonduplicate disputes. Neither6,954 raw records nor20 relation-extraction cases automatically supplies usable supervision. No untested sample threshold guarantees sufficiency.

[GFM-RAG §4.6](https://arxiv.org/html/2502.01113v3) studies pretrained retrieval transfer to new corpora. Sparse data primarily limit training from scratch, not all pretrained controls. Before transfer, check weights/runtime, graph adaptation, compute, and data exposure. Transfer is not legal validation or evidence for the proposed R-GCN's effectiveness. [UniLR, ACL2025 §3](https://aclanthology.org/2025.acl-long.584.pdf) offers a legal-element-supervision/graph-retrieval comparison; target label visibility must still be enforced.

## Runtime and extraction prerequisites

Existing `mlx-community/Qwen3.5-9B-4bit`, fixed revision, and the dedicated MLX environment initially isolate method changes, not semantic adequacy. Conclusions apply to that model/configuration. Broader paper claims require key controls on at least one different capability/architecture; two models still do not represent all modern LLMs. Browser reference review is not a second tested-model experiment. Check/freeze resources separately for new models without repeatedly changing configurations to pass checks. This review authorized/launched no migration.

The35B-A3B model card describes35B total/3B active parameters. Active count does not reduce stored weights to3B. Ideal4-bit storage for35B alone is17.5GB before quantization overhead, higher-precision parts, caches, runtime, and system memory. Long-context feasibility on24GB cannot be promised; this is an estimate, not measurement. [Official card](https://huggingface.co/Qwen/Qwen3.5-35B-A3B).

The cited vLLM documentation lists Apple Silicon via vLLM-Metal, so blanket Mac incompatibility is inaccurate. Plugin availability does not validate a specific model/quantization/structured-output combination. [Installation](https://docs.vllm.ai/en/latest/getting_started/installation/). [JSON Schema support](https://docs.vllm.ai/en/latest/features/structured_outputs/) is useful, but existing MLX constraints do not require migration for the same feature.

Qwen3-Embedding-0.6B supports up to1024 dimensions in the cited specification. Load/cache embedding and reranking separately to avoid memory competition with generation. Rerank complete bounded legal units and record lengths; do not copy example truncation that loses definitions/exceptions. [Embedding](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B), [reranker](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B).

## Proposed implementation and experiment sequence

Start with one sufficiently documented merits issue. Subletting is a candidate, but three existing object-relation questions do not automatically become sufficient grounds for eviction. Verify the statute, necessary conditions, and target stage. Use about five old development cases to connect the flow, not reextract every old case. Then select a fixed small new batch, for example at most ten, under predetermined rules without replacing method failures.

| Stage | Implementation/artifacts | Comparison and progression |
| --- | --- | --- |
|1 Task/sources | Visibility, claim outcomes, real authority/version, necessary conditions; reuse valid sources/records | Explain actual inputs/reference basis for each request. Procedural-only outcomes do not create merits labels. |
|2 Minimal end-to-end | Retrieval, explicit RuleCards, full condition trees/bindings, fixed LLM conclusion | Historically proposed direct-text, text-RAG, and structured application controls; retain failures. Do not wait for exhaustive review/GNN training or force induction. |
|3 Extraction versus induction | Compare original historical reasons with extracted rules; add separately labeled hypotheses only when supported | Report explicit reuse and cross-case generalization separately. Five cases supporting only extraction leave induction untested. Empirical gain does not confer authority. |
|4 Representation/pattern isolation | Same facts, authorities, condition records; retain/remove patterns; relation/co-occurrence controls | Preserve constituent facts when removing derived patterns. Source-review extra co-occurrence candidates rather than calling all erroneous. |
|5 Error-directed learning | Poor ranking motivates pretrained graph transfer or supervised LawRanker; poor outcome composition despite adequate conditions motivates VerdictNet | Separate fixed-pool reranking from retrieval. Match candidate information across text/MLP/graphs; compare VerdictNet to LLM/MLP/applicable executor on identical condition tables. |
|6 Investigation benefit | At most one gap-driven investigation on a working frozen version | The historical design allows a matched text-RAG control one extra retrieval. Record recovered content, corrections, and costs before adding rounds. |
|7 Model dependence | Repeat key comparisons on another tested model after stabilization | Report model-specific gains/failures; two models do not establish universal LLM effects. |

Proposed stage2 responsibilities are `prepare_legal_task`, `index_authorities`, `retrieve_authorities`, `build_rule_cards`, `assess_conditions`, `decide_claim`, and `evaluate_legal_task`; these names were not created by this review. Extraction can run first; `induce_case_rules` produces separately labeled hypotheses/counterexamples/versions only with sufficient material. Reuse relational execution and add full-binding condition composition, not sums of independent Booleans. Derive graph tensors from readable records without making graph frameworks a first-stage dependency.

Initial acceptance: one real complete rule stores provenance, every necessary condition, scope, and consequence; one case returns full compatible bindings, original witnesses, and key gaps; controlling law remains available to explain failed conditions. Add only necessary engineering tests, without changing old semantics. Passing does not require an expected verdict; rule semantics still require source review.

## Causal questions for evaluation

Control tested model, allowed materials, historical corpus, legal scope, and budget. Direct original-text answers measure base capability; text RAG tests supplied law; full bindings/explicit rules under the same law test structured application; separately labeled induced hypotheses test additional benefit later. Extraction and induction have separate outcomes, not a combined rule-learning success label. The historical proposal retains enhanced RAG, serialized-LLM, MLP, and no-pattern controls; running any enhanced baseline now requires explicit approval.

Two diagnostic inputs use source-reviewed key facts or applicable authorities to locate extraction versus retrieval/application errors. Keep them separate from automatic end-to-end scores. Diagnostic success is not automatic-system success.

At claim level, record known-relevant candidate/final-source retention, condition binding, historical/reference agreement, decisive-evidence validity, unknowns, technical failures, abstention coverage, and costs. Without complete independent relevance lists, report verified-source coverage/fixed audits, not exhaustive recall. Unreviewed candidates stay U, not negatives for favorable metrics.

Verdict agreement cannot substitute for sound reasons. Missing conditions do not always require abstention if an explicit applicable burden rule determines consequences of that proof state. Preserve such legal authority. Model abstention and historical labels remain separate; technical failure yields no substantive answer.

Split by verified dispute groups; unknown associations are separate. Historical evaluation respects authority/precedent availability dates. Out-of-fold generation covers all answer-informed rules/patterns/mappings. Fixed public statutes need not change semantic content per fold, but learned extraction/selection versions remain split-bound. Cases exposed during method changes become development material.

References remain ordinary High browser-model outputs checked against originals, not human gold; unavailable human annotators are not required. Small studies report item-level evidence, not multiple facts as independent cases. Fewer unknowns, more matches, or passing test counts do not establish accuracy.

## Related work and implications

These adjacent methods show that graph + LLM + legal retrieval alone is not a new contribution.

| Work/read scope | Mechanism | Project implication |
| --- | --- | --- |
| [LegalGraphRAG, ACL2026](https://aclanthology.org/2026.acl-long.1738.pdf), §4/AppendixB; [arXiv](https://arxiv.org/html/2605.28120v1) | Hierarchical legal graph, condition checks after retrieval, synthesized conclusions | In civil claims, pruning can remove reasons for dismissal. Compare retention/pruning rather than rejecting published results. Unsatisfied statutes may explain dismissal; unknown is not false. |
| [GLARE, ACL2026](https://aclanthology.org/2026.acl-long.600.pdf), §3 | Expand confusable offenses, distinguish precedents, retrieve missing knowledge | Borrow opposing-candidate comparison; Chinese criminal-offense results are not Indian civil-claim evidence. Start with one investigation. |
| [Capturing Legal Reasoning Paths, arXiv2025](https://arxiv.org/html/2508.17340v1), §2 | LegalApplication nodes connect facts, norms, and provisions | Application records can be standalone objects without first training dual GNNs. Court-reasoning reconstruction differs from target-case prediction. |
| [NyayaRAG, IJCNLP-AACL2025](https://aclanthology.org/2025.ijcnlp-long.92/), task description | Indian facts plus provisions/precedents assist judgment | Motivates an Indian-law text-RAG comparator, but input/label definitions were not established as directly reusable. |

This was a component-focused original-paper review, not an exhaustive survey. A plausible hypothesis is that explicit binding, statement status, applicability, and exceptions reduce specific condition misuse. Whether induced historical conditions improve new-case retrieval/decisions requires the proposed controls. Component evidence should determine whether graph learning is needed and whether it exceeds simpler methods.
