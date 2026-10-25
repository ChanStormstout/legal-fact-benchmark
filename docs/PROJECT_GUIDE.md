# Project guide

## Research workflow

RAPIDO studies whether explicit evidence uses, entity bindings, procedural scope,
and rule dependencies help produce a complete, source-grounded legal report.
An evidence use records what a passage is being used to establish. A binding records
which person, property, time, and proceeding that statement concerns. These must
be checked separately from whether the requested legal conclusion follows.

The intended workflow reads permitted sources, assesses these uses and bindings,
retrieves relevant authorities and historical comparisons, applies registered rules,
identifies competing arguments and gaps, and generates a checked report.
The presence of an interface does not establish that a particular run completed it.
Inspect the run's actual requests, responses, and final artifacts.

## Code map

| Location | Purpose |
| --- | --- |
| `legal_bench/core.py` | Source records, validation, and common data utilities |
| `legal_bench/engine.py` | Structured relation execution and pattern operations |
| `legal_bench/tasks.py` | Task preparation and reply import |
| `legal_bench/experiment.py` | Manifests, splits, freezes, scoring, and ablations |
| `legal_bench/rules_verdict_v1/` | Early rule-and-verdict interfaces |
| `legal_bench/research_diagnostic_e2e_v1/` | Local-only bounded diagnostic reasoning and report replay |
| `legal_bench/rapido_offline_v1/` | Local-only adapters, event replay, and saved-result verification |
| `scripts/` | Explicitly versioned experiment and delivery entry points |
| `outputs/` | Frozen run-specific implementations, inputs, execution records, and results |

This is a map of responsibilities, not a claim that the modules form one current
production entry point. Several later experiments freeze independent adapters under
`outputs/`. Read the selected version's README and protocol before choosing a runner.
The offline pilot uses prepared assessments and cannot establish automatic source
understanding by itself.

## Finding a result

Start with [EXPERIMENT_INDEX.md](EXPERIMENT_INDEX.md). For the selected version, read
its report, protocol, execution status, actual final reports, and source adjudication.
Do not combine scores across versions, substitute internal acceptance for independent
quality assessment, or interpret an unrun slot as a successful answer.

`PROJECT_STATE.json` and `review/START_HERE.md` describe the review snapshot selected
in `repository-artifacts.json`. That selection may be older than local development;
it is not evidence that a process is currently running. The catalog and individual
run records preserve their own dates and scope.

## What the comparisons can establish

The ordinary baseline is a single LLM call on the permitted raw materials and question.
Additional mechanisms are separate methods and require explicit approval. Historical
multi-stage comparators retain their historical labels and are not retroactively
redefined as the ordinary baseline.

Distinguish four questions: did execution finish, did internal checks pass, was the
whole report supported and complete, and did it improve on the comparator? A positive
answer to one does not imply the others. Retrieval hits, accepted bindings, or rule
matches are intermediate observations, not final quality scores.

The current research includes exposed development cases and model-reference labels.
It does not by itself establish generalization, lawyer approval, or a publishable
method advantage. Case comparisons must preserve source scope, failures, and costs.
