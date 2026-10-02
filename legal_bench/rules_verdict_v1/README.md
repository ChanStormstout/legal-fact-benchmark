# Rules and verdict V1 — implementation status

This package is an incomplete first implementation, separated from the historical
three-pattern experiments. See `outputs/rules-verdict-v1/report-zh.txt` for the
bounded development check. No end-to-end legal decision result is established.

Implemented: immutable source views and model attempts; source-preserving windows;
pinned text-only MLX generation with JSON Schema masks; field-dependent unknowns;
local record isolation; existential AND/OR queries with shared object bindings;
`part_of`/`member_of` evidence; SQLite FTS5 BM25, reciprocal-rank fusion, and explicit
authority dependency expansion. Retrieval primitives have fixture tests and a three-judgment historical development index, not a complete legal-corpus evaluation. `apply_rules.py` currently executes factual
queries; its name does not imply it can apply complete legal rules.

Not implemented: cross-window identity consolidation, definition-card normalization,
cross-case rule induction, historical legal-version verification, a complete rule compiler,
necessary/sufficient conditions and exceptions, temporal/numeric comparisons,
burden of proof, stage-sensitive resolution of competing court findings, dense
retrieval/reranking, final decision synthesis, and reference-based legal evaluation.
Unsupported query operators are rejected; they are not silently omitted.

From the repository root:

```sh
python3 -m unittest tests.test_rules_verdict_v1 tests.test_rules_verdict_retrieval_v1
# The prepared version is immutable. These commands reuse completed attempts.
.runtime/qwen35-v1/bin/python scripts/rules_verdict_v1.py check-dev --case 661475
.runtime/qwen35-v1/bin/python scripts/rules_verdict_v1.py check-dev --case 1134266
```

The local runtime/model path is inherited from the existing project environment;
a public clone does not include it. Never use `check-dev` to launch additional cases
without a new protocol. It is a low-level runner, not enforcement of all experimental
budgets. Runtime `OK` means generation parsed and satisfied the schema; the subsequent
import and source/semantic checks can still fail. A model-written `known` declaration
is not independent proof that the field is true. Imported evidence expands an explicit
segment ID to its exact supplied text; this verifies location, not entailment.

A complete original judgment is referenced by content hash. The appeal-input view
intentionally excludes the target court's reasons/disposition under the saved task
boundary. It is not a silent context truncation, nor proof that the resulting task is
citation-blind or a genuine prospectively collected appeal dataset.

## V2 development status

See `outputs/rules-verdict-v2/report-zh.txt`. The two-case objects-then-facts interface now imports records. Historical judgment retrieval and local explicit-rule extraction have run. A one-case A1/A2/A3 development comparison is preserved, including an invalid original condition translation and one corrected A3 replay. The translation gate requires source-backed approval for executable fragments; a model predicate hint alone is insufficient. Complete rule execution remains UNSUPPORTED. Format validity and exact quotation location do not establish legal accuracy. The ordinary High reference cards are separate from model inputs. No new-case evaluation or automatic publication is implied.

## V3 object-condition diagnostic

`conditions_v3.py` implements DOCUMENT.registration, separate PERMISSION form,
specificity and grantor/target links, actor roles and explicit court findings on
TRANSFER objects. The nine questions are predefined condition probes on the same
three exposed allowed-input views. They are not newly discovered rules, chronological
prediction tests or complete legal-rule applications. Each accepted atom retains its
source status and exact quotation. An existing tenancy does not manufacture a deed;
a generic clause does not prove global absence of specific permission. Same-case and
same-permission/event joins are enforced. Stage precedence is not inferred.

The original six-call budget and code are frozen under `outputs/rules-verdict-v3`.
A narrowly versioned format recovery converts bare Python boolean spelling outside
quoted strings to JSON spelling; original raw outputs and FORMAT_ERROR metadata
remain untouched. Recovery does not repair missing evidence or wrong object types.
Reference-witness execution is a separately labelled developer transcription of
model references; it is never substituted for B's local-model facts.
