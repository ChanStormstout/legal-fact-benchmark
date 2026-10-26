# Legal AI · RAPIDO

Research on source-grounded legal reasoning: analyze competing arguments in a case,
identify the evidence each argument needs, and produce a report whose claims can be
traced to the permitted sources.

**Status:** experimental research code. End-to-end runs have exposed source-reading,
entity-binding, legal-coverage, generation, and reporting failures. Engineering checks
and internal acceptance do not establish legal correctness or an advantage over a
plain LLM. See the [experiment index](docs/EXPERIMENT_INDEX.md) for version-specific evidence.

## How it works

```text
Permitted case materials + question + versioned legal sources
    → source assessment and evidence-use / entity / procedural-scope checks
    → retrieval of relevant case, law, and historical judgment passages
    → rule application, competing arguments, objections, and unresolved conditions
    → source-linked report and final checks
```

LLMs propose interpretations; Python enforces the declared contracts and computes
consequences under the registered rules. Historical case facts support comparisons,
not factual premises about the current case. Coverage and working stages vary by
version; this diagram is the research workflow, not a claim that every run succeeds.

Latest source-extraction checkpoint: [V15 / V16 and LW comparison](outputs/source-extraction-checkpoint-2026-10-26-v1/README.md). This is a captured partial-run status, not a live result or a success claim.

## Start here

| You want to… | Read |
| --- | --- |
| Understand the research question and evidence limits | [Research direction](docs/RESEARCH_DIRECTION.md) |
| Find implementation modules and versioned runs | [Project guide](docs/PROJECT_GUIDE.md) |
| Inspect results and failures | [Experiment index](docs/EXPERIMENT_INDEX.md) |
| Review a reproducible code-and-evidence snapshot | [Review entry](review/START_HERE.md) |
| Understand data availability and setup requirements | [Data and portability](docs/DATA_AND_PORTABILITY.md) |
| Browse documentation | [Documentation index](docs/README.md) |

## Repository layout

- `legal_bench/` — reusable source, contract, reasoning, and evaluation code.
- `scripts/` — version-specific runners, reporting tools, and review-package tooling.
- `tests/` — engineering checks; these are separate from legal-quality evaluation.
- `docs/` — research design, implementation notes, and the experiment catalog.
- `outputs/` — versioned methods, source records, responses, failures, and results.
  Only explicitly selected artifacts are published; a clone does not contain every local run.
- `review/` — generated review documents and file-hash manifests.

## Local inspection

The basic CLI and review tooling use Python's standard library:

```sh
python3 -m legal_bench --help
python3 scripts/repository_bridge.py verify
```

`verify` checks the existing review snapshot. After an authorized local change,
regenerate it with `python3 scripts/repository_bridge.py prepare`, then verify again.
Neither command starts a model or publishes changes. Model execution requires the
specific run's environment, model, inputs, and authorization; there is no universal
command that safely reproduces all historical experiments.

## Reading the results

Use the protocol and actual execution records from the same version. Missing reports,
technical failures, and unsupported legal scope remain visible in the results.
Source-reviewed model annotations are **model references, not human gold**. Exposed
development cases do not establish performance on unseen disputes.

The ordinary baseline is permitted raw materials and the question followed by one
LLM call. Added retrieval, review, decomposition, or revision requires explicit
approval. Older enhanced comparators retain their original definitions and results.

The registered review snapshot is the [V22 two-case comparison](outputs/rapido-v22-baseline-pro-review-2026-10-24-v1/README.md)
([English summary](docs/CURRENT_REVIEW_SUMMARY.md)):
the ordinary baseline delivered both reports; C delivered one report with errors and
timed out on the other case. Whole-case superiority is unproven. This is a retrospective
development review, not a twelve-case result or independent test. Original experimental
records retain their source language and exact bytes.
