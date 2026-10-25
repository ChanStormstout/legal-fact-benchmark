# Complete reasoning-reconstruction workflow V7

This version provides one research entry connecting existing source handling, model tasks, response import, research-review policy, graphs, derivation certificates, independent checks, explanations, and versioned revision. It adds no component-benefit experiment, model call, case, legal source, or training. The three historical teaching judgments and five calibration cases supply whole-workflow integration material.

External model and explicit review inputs are part of the workflow. Website models connect through self-contained task files and raw-response import; there is no background ChatGPT automation service. Programs do not fill in source semantics or legal approvals, or present human/external steps as automatically completed.

## Entry and data flow

Entry: `scripts/proof_pipeline_v7.py`; implementation: `legal_bench/proof_carrying/workflow_v7.py`. Independent checking still invokes `scripts/check_realcase_certificate_v4.py`; checker logic is not copied into the proposal engine.

1. **Source import.** `init` receives a case spec with case/stage, fixed questions, permitted-source index, original paths, and hashes. It checks document identity, original paragraphs, locations, and text consistency, copies sources, and saves a source map. Existing blank lines remain. Valid references do not prove semantics.
2. **Model tasks and originals.** The same full sources produce rule, independent rule-review, fact, independent-reference, and derivation tasks. Unmet dependencies prevent assembly. Independent references receive no fact/rule drafts, derivations, or checker results. Every task saves source-to-text mappings and hashes. Cache reuse records provenance rather than masquerading as new generation.
3. **Import and local retention.** `ingest` accepts raw responses and transport records, verifies submitted-task hashes, and strips only outer Markdown fences. It does not repair JSON, change facts, or retry automatically. Identifiable complete records survive separately; erroneous records and full originals remain. Missing dependencies stay missing. New reference import handles records individually rather than erasing the first 30 because a 31st exists; old FORMAT_ERROR/null records remain unchanged.
4. **Research acceptance policy.** Policy is separate from proposals and consumes existing content-hash-bound review decisions, scopes, and court assessments. Missing review does not become automatic acceptance; missing approval does not change fact status. Policy files cannot rewrite sources, premises, or rules.
5. **Graphs and queues.** Source/entity/premise/rule/step/request nodes connect through provenance, binding, application, and dependency edges. Only explicit proposed positive/negative relations with valid source addresses enter spectral projection. Conflicting relations coexist; logical dependencies are not support votes. Source-order, simple, and spectral-assisted queues are emitted. Missing positive/negative edges leave isolated nodes rather than fabricated conflict.
6. **Certificates and independent checks.** Saved proposals generate certificates. An independent process loads fixed sources, policy, and rule versions, checking objects, types, time, dependencies, and existing finite logic. Graph scores cannot establish open legal judgments. Reconstructed court assessments are conditional; uncomputed, invalid, and technical failures remain distinct.
7. **Analysis page.** Without new model calls, checker results produce request analyses, major counterarguments, specific gaps, and graphs. Requests link through steps/rules/premises to original paragraphs. Model free text remains an unverified semantic proposal and receives no automatic endorsement from checker status.
8. **Versioned revision.** `revise` requires a new directory and explicit reason, retaining parent version, hashes, and changes. Old approvals, sources, proposals, and failures are not overwritten. New review policy remains required; revision does not auto-approve.

## Usage

Use the existing runtime with NumPy; no installation is required:

```sh
PY=/Users/victor/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3

# Verify/read a delivered case without generating it again.
$PY scripts/proof_pipeline_v7.py verify outputs/proof-carrying-pipeline-v7/cases/789051
$PY scripts/proof_pipeline_v7.py advance outputs/proof-carrying-pipeline-v7/cases/789051

# Register a new output root first. Relative spec paths resolve against its directory.
$PY scripts/proof_pipeline_v7.py init --spec path/to/spec.json --out path/to/new-workspace

# Import only after the matching task is assembled; no second response per stage.
$PY scripts/proof_pipeline_v7.py ingest path/to/new-workspace rules \
  --response path/to/raw-response.txt --metadata path/to/transport.json

# Policy is an independent input, not a reference-answer file.
$PY scripts/proof_pipeline_v7.py ingest path/to/new-workspace policy \
  --response path/to/research-policy.json --metadata path/to/policy-origin.json

# Rebuild a new version while preserving its parent.
$PY scripts/proof_pipeline_v7.py revise path/to/parent \
  --spec path/to/new-spec.json --out path/to/new-version --reason 'Explain the documented change'
```

A usable example is `outputs/proof-carrying-pipeline-v7/inputs/789051/spec.json`. Retained cache paths reuse existing records; removing one produces a pending task, not an automatic call. Do not reuse a reviewed old-case spec for another case merely by changing its ID.

Website metadata requires `origin` and `submitted_task_sha256` from `task-manifest.json`. Record actual URL, visible model/mode, submission and observed completion times; unavailable fields remain null. Policy metadata records the responsible reviewer or model-assisted review provenance, without fictional website submissions.

Stages can await input/dependencies, be imported/partly usable, or fail formatting. DELIVERED means workflow artifacts were saved, not that every request succeeded. Inspect each `draft_status`, `answer`, assumptions, errors, and approval. Missing policy can still produce graphs and explicit incomplete requests without accepting premises. After completion, new policy requires `revise`, not in-place import.

## Integration delivery

Eight cases and 23 existing requests passed through the unified entry, saving source maps, proposals, policies, graphs, queues, certificates, checks, and analysis pages. Results: 20 conditional reconstructions, two explicit combinations under research assumptions, and one incomplete computation. These restore old-material states through a unified entry; they are not new capability scores. The three Guide cases retain model derivations; the five calibration cases retain maintainer-assembled derivations.

Two integration failures remain: an old validator rejected integer versions, and another check treated different versions of the same rule as duplicates. Delivered code validates version types and identifies rules by `id@version`, without changing legal rules or raw output. These are implementation repairs, not semantic tuning/component experiments.

Three full-entry checks cover cache-to-delivery, empty-workspace task/import, immutable reopening/revision, source conflicts, and lossless import of all old rule versions. Actual eight-case runs and historical checks completed; 1,205 old records stayed byte-identical. Source, failed attempts, and delivery remain separate.

## Human/model boundaries

This is not a completed 30/10/20 pilot, automatic legal approval, or an implementation of all open legal assessments. The spectral queue is connected but its legal-task benefit was not evaluated. New website generation and legal review enter through fixed interfaces; this round reused caches only and did not relabel manual assembly as model capability. Future work can evaluate the whole workflow without first requiring every component to win.

Local entry: `outputs/proof-carrying-pipeline-v7/index.html`. Actual-code freeze: `freeze/implementation-03/config.json`. No deployment, commit, or push occurred.
