# Legal AI Research Design and Pro Discussion Records

Completed September 29, 2026. This package records research discussion and design synthesis, not implementation or experimental execution.

## Reading order

1. [Literature map and design choices](文献地图与方案取舍.md): research landscape, nearest work and selection.
2. [Algorithm research proposal](算法研究方案.md): A/B/C interfaces, steps, pseudocode, hypotheses, historical comparators, experiments and rejection conditions.
3. [Independent literature verification](独立文献核查.md): 43 primary sources and actual reading scope, without claiming exhaustive or uniformly deep reading.
4. [Pro A literature registry](Pro-A文献登记.md): 38 self-reported reading records, retained as received, partly overlapping independent verification.

The historical selection prioritizes A's legal-fact abstraction and reliable reuse, treats B's robust pattern selection as an experimental branch, and uses C's bounded rule application to test practical value. The original PDF already contains an implementation workflow; this package adds semantic definitions, comparisons, experimental interfaces and possible algorithm extensions.

## Web conversations

Four GPT 6 Pro conversations and one Extra High technical conversation produced six Pro replies and six Extra High replies. Original text preserves intermediate assumptions and later corrections. The synthesized documents, rather than every intermediate suggestion, define this historical proposal.

| Discussion | Conversation | Saved replies |
|---|---|---|
| Strategy, broad reading and final positioning | [Pro strategy](https://chatgpt.com/c/6abb7c18-28dc-83e8-b682-9f5afd501314) | [First](01-strategy-round1.txt), [follow-up](10-strategy-round2.txt) |
| A: representation, normalization, hierarchy and evaluation | [Pro A](https://chatgpt.com/c/6abb7c61-7944-83e8-b720-09ea73fc9fa2) | [Reply](02-representation-round1.txt) |
| B: patterns, relational structures, set selection and nearest work | [Pro B](https://chatgpt.com/c/6abb7c74-4210-83e8-b744-be3526a254dc) | [First](03-patterns-round1.txt), [follow-up](08-patterns-round2.txt) |
| C: sources, rules, exceptions, arguments and downstream tasks | [Pro C](https://chatgpt.com/c/6abb7c86-f3c4-83e8-b524-21db329fa567) | [Reply](04-rules-round1.txt) |
| Technical checks: identity/type, unknown/negative, support bounds, optimization and review | [Extra High](https://chatgpt.com/c/6abb7f4f-5800-83e8-b5fb-a0c864cde126) | [1](05-extra-high-round1.txt), [2](06-extra-high-round2.txt), [3](07-extra-high-design.txt), [4](09-extra-high-final-audit.txt), [5](11-extra-high-set-design.txt), [6: corrections](12-extra-high-corrections.txt) |

`.txt` files export visible replies; later replies include earlier context. `-dom.txt` files preserve visible structure and citation links. Formulas may contain both Unicode and formatted duplicates; use the synthesized design for reading algorithms. Submitted prompts remain in adjacent prompt files.

## Corrections from independent review

Predicate-type equivalence differs from real-event identity; original instances, within-case bindings and provenance remain necessary. Missing witnesses do not imply false facts, and invalid candidate explanations do not reduce to ordinary unknown. Support bounds under globally consistent interpretations differ from sums of per-case extrema and hold only within explicit candidate sets. In robust optimization, the scenario master gives an upper bound while complete worst-case evaluation bounds the current feasible solution below; ordinary greedy guarantees do not transfer automatically. Downstream review, category revision and max-min set objectives have precedents and are not inherently novel.

The read-only local inventory contained 6,954 records. Filenames do not establish legal subdomain, and clean outcome labels were unverified. Original data were unchanged. The historical proposal was a small source audit and expert specification calibration followed by a staged pilot of approximately 90 dispute groups; sample size and budget required calibration against actual effort and data quality. This proposal is not current authorization.

![Completed Pro discussion](Pro最终研究讨论.png)
