# Documentation

## Start here

- [Project guide](PROJECT_GUIDE.md): workflow, code map, and how to inspect a run.
- [Research direction](RESEARCH_DIRECTION.md): research objective and original design boundaries.
- [Experiment index](EXPERIMENT_INDEX.md): version-specific reports and limitations.
- [Evaluation standard](evaluation/README.md): important-content scores, source support,
  serious errors, report preservation, source-grounded GPT Web references, and change rules.
- [Data and portability](DATA_AND_PORTABILITY.md): published data and environment requirements.
- [Registered historical review in English](CURRENT_REVIEW_SUMMARY.md): translated explanation with unchanged original evidence.
- [Review workflow](CHATGPT_REVIEW.md): preparing and reviewing a traceable snapshot.
- [Development branch](DEVELOPMENT_BRANCH.md): branch history and publication workflow.
- [English documentation scope](ENGLISH_DOCUMENTATION.md): translations and preserved original records.
- [Changelog](CHANGELOG.md): dated changes and historical delivery records.

## Machine-readable records

`EXPERIMENTS.json` is the experiment catalog. `repository-artifacts.json` selects
publishable artifacts and the registered review snapshot. `PROJECT_STATE.json` is
generated from that selection; it is not a live process monitor.

## Historical designs and implementation notes

Versioned documents in this directory describe the implementation and evidence at
their recorded dates. `plans/` contains proposals, not completed results. `reviews/`
contains review material whose suggestions are not automatically accepted findings.
Actual experiment inputs, outputs, failures, and source records are under `outputs/`.

Explanatory documentation is maintained in English. Original prompts, model replies,
judgment quotations, and annotations retain their source language so that experimental
evidence remains traceable. Historical filenames are retained to avoid breaking links.
