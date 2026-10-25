# Meeting Brief: Why the Three Designs Might Help and How to Compare Them

2026-09-29. Discussion material only. Performance gains are hypotheses; no project experiment had been run. The comparator commitments below belong to this historical proposal, not current authorization to enhance a plain-LLM baseline.

## Opening

We retain the document's workflow: canonicalize facts, discover patterns, then examine their relation to legal conditions. The additions address three questions: does normalization preserve important information, do combined facts describe the same situation, and can rule application distinguish support, opposition and insufficient evidence?

These designs address specific failure mechanisms, but have not surpassed the document's alternatives. The original proposal calls for a complete implementation of those alternatives and matched information/budget comparisons. Every module need not introduce a new algorithm.

## A: Can the normalized representation still answer important questions?

PDF pages 2–6 already describe roles/predicate arguments, polarity/status/time, legal-context blocking, embedding retrieval, six-way LLM relation judgments, conservative merging, definitions/medoids/boundaries, provenance and change records. Page8 covers merge precision, stability and drift. Context, whole-cluster checks and provenance are therefore not new contributions.

The proposed addition is an executable abstraction/repair criterion. Experts define development questions about actors, objects, full payment, temporal order, allegations and findings, with source-backed references. The model cannot generate convenient answers to its own acceptance questions.

Run the original workflow to obtain types and instances. Types share only permissible abstractions; instances retain entities, amounts, events, time and status. Answer the questions through structured queries and compare with sources. Diagnose extraction omissions, wrong bindings, wrong type mappings and granularity errors; repair instances, remap, add necessary arguments or split types as appropriate. Recheck affected boundaries and freeze after development.

Programs check types, IDs and status consistency; models/experts interpret sources. Correct program checks do not rescue incorrectly extracted arguments. For example, alleged payment and found payment may share content, but losing instance status makes downstream reasoning treat an allegation as a finding. Query-level checks reveal this loss and localize repair. This is a measurement/repair design, not a proven new clustering algorithm. A complete PDF implementation may already preserve everything and leave no gain.

Historical comparisons include full PDF, adapted EDC, expert schema and source/local retrieval, all sharing sources, model, expert policy, definitions and budget. Calibrate on development queries; lock new cases and unseen query combinations. Separate structured-only answers from rereading, charging rereading cost. Require improved important-distinction recall or expert time at matched coverage/error, alongside merge precision, recall and reuse. All rejection/all singletons cannot win.

## B: Do frequent facts describe one relational situation?

PDF page7 names FP-Growth, gSpan and ANCO-HITS and introduces outcomes only after normalization. It does not define their encodings, edges, support units or objectives. They are not interchangeable: itemsets, subgraphs and signed bipartite grouping/ranking solve different problems.

The first design uses short connected queries over frozen facts, such as paid and overdue nondelivery under one contract. Every match returns participants, contract, assertions and sources. Fix case/claim/stage units; multiple witnesses do not inflate support. Missing witnesses remain unknown. Enumerate a bounded typed language, then use existing compact selection. Separate discovery, selection and confirmation. Study outcomes only after labels are defined/verified; frequency in two groups alone does not demonstrate discrimination.

K1 payment plus K2 nondelivery can fool an unbound case-level itemset, but a shared-contract matcher rejects that witness. This is conditional on correct extracted IDs. A pattern frequent among successful claims can be equally frequent among unsuccessful ones. Group comparisons, fixed units and independent confirmation are established statistical safeguards, not a new mining algorithm.

| Alternative | Fair implementation | Possible advantage | No-advantage condition |
|---|---|---|---|
| FP-Growth | Give identical relational-query features as well as binary facts; recheck shared bindings in combinations | Bindings reduce errors caused by information loss | Existing mining on the same relational features performs equally well |
| gSpan | Same reviewed/automatic graph with actors, objects, events and status | A short query language may reduce irrelevant search/review | gSpan finds the same valid structures at similar cost |
| ANCO-HITS | Define nodes, signed edges and ranking/grouping task; unknown is not negative | Queries may directly fit a discovery task | No superiority claim before a common task is defined |

Measure wrong bindings, source validity, independent recurrence, redundancy, important-pattern recall and total cost. Separate natural cases and constructed challenges. Reject complexity that only produces more patterns or abstentions. Joint interpretation bounds, robust selection and impact-guided review remain extensions until natural shared ambiguity is shown to change important outputs.

## C: Which legal conditions have support, and which lack evidence?

The PDF centers on canonicalization/mining and does not supply a complete C algorithm. The user's pipeline diagram connects facts/patterns, factors, elements and authorities. C is a supplementary design, not an already-surpassed PDF implementation.

Start with a small expert-reviewed issue-specific rule package recording authority, scope, conditions, exceptions and version. Bind A instances to premises, report supported/refuted/unresolved states, and execute declared semantics. Unknown exceptions follow sourced rule/burden arrangements, never a universal unknown=false policy. B retrieves situations and suggests conditions; it is not authority.

The first comparison supplies identical correct authorities/rules to all methods, isolating natural-language application from explicit execution; open retrieval comes later. Evaluate text-to-rule errors separately from inference guarantees.

If a conclusion needs A, B and C but sources support only A and B, absence of opposition to C cannot establish C. Explicit execution can reduce skipped conditions, mismatched objects and status confusion; it cannot correct legal interpretation automatically. Benefits are most plausible for clear conditions and exact object/time matching. Ambiguous norms, value balancing or expensive formalization may favor natural-language/expert analysis.

Compare same-information direct RAG/model analysis, structured checklists and bounded rules, with identical authorities, model and budget. Add a separate B-on/off comparison. Measure misapplication, missing premises/exceptions, citation applicability, unresolved coverage and expert time, not outcomes alone. If a checklist suffices, a complete logic engine is unnecessary.

## Historical experimental commitments

Implement the complete PDF process rather than weakened embedding-only clustering. Isolate B with reviewed representations and C with reviewed rules before introducing automatic A. Use independent source review and locked cases, recording expert information and total cost; without clean outcomes, begin with factual queries and case comparison. Claim superiority only when matched coverage/information/budget show fewer expected errors and better terminal tasks. Until then describe these as testable hypotheses grounded in failure mechanisms.

Sources: original PDF pages2–8; [full proposal](算法研究方案.md); [primary-source reading register](独立文献核查.md).
