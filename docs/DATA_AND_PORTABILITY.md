# Data and reproducibility

The repository makes selected code, research documents, judgment texts, model-reference
answers, and experimental outputs available for method review. Judgment records retain
provider URLs, paragraph identifiers, original wording, and names as published in the
judgments. The project does not claim copyright in third-party sources or relicense
them. No separate license was selected for the code and original research material in
the publication described here; public access is not unrestricted redistribution permission.

## Published and local-only files

`repository-artifacts.json` explicitly selects publication files. See
`review/PUBLICATION.json` for inclusion and exclusion records and `review/MANIFEST.json`
for hashes. Model environments and weights, the full 6,954-record JSONL, third-party
paper copies, browser captures and UI state, hardware information, download logs, and
multi-gigabyte expanded traces remain local. References in an old report do not imply
that all referenced files are present in a clone. Local source files are not deleted
by the publication tool.

Original experimental sources, annotations, requests, responses, failures, and frozen
method snapshots retain their bytes. Older JSON, logs, and scripts may contain
machine-specific absolute paths; use the manifest's relative paths to locate published
files. Documentation translations do not change experimental inputs or outcomes.

## Execution requirements

The basic CLI, review tooling, and standard-library-only checks do not require MLX.
Some experiment scripts and tests need additional dependencies. Local MLX generation
requires Apple Silicon and the experiment's isolated environment. Register a new
version before execution; do not overwrite a completed run.

The historical local model is `mlx-community/Qwen3.5-9B-4bit`, revision
`8b2b98c00a6b4d291155e4890773ca8f769aee53`. Its framework and parameter records belong
to the relevant experiment directory. Later API runs have separate provider and
model metadata; do not treat their weights as identical to the local snapshot.

To reconstruct a historical local environment, use that run's
`environment/requirements.lock.txt`, obtain its exact model revision, and set the
ignored `environment/model-path.txt` to the local location. These are prerequisites,
not authorization to start a model. A repository clone is not a ready-to-run model installation.
