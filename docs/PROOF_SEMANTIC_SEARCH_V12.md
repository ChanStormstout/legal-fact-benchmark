# V12: sourced evidence-use matching and complete dependency search

The task is judgment-reasoning reconstruction. Original proposals, independent references, and use evaluations are separate. References cannot enter automatic-check acceptance policy. Use judgments differ from whole-premise states; programs check addresses, explicit role maps, rule versions, and logic without approving legal meanings.

## Entries

- `scripts/proof_semantic_import_v12.py CASE proposal|reference|review RAW`: retains raw text, strips only outer JSON fences, isolates local rule/use errors. Proposal import saves the input graph, candidates, independent checks, and full original proposal without reading the independent reference.
- `scripts/proof_semantic_run_v12.py`: complete dependency search with independent-process recomputation; saves snapshots, search traces, checks, and bounded analysis. Limit: 10,000 expansions or ten seconds per request; no default six-candidate cap.
- `scripts/proof_semantic_supervision_v12.py --out NEW_DIR`: builds separate supervision from TRAIN/DEV proposals and use evaluations only. It does not open existing TEST directories. Missing labels are masked; missing QC keeps training disabled.
- `scripts/proof_semantic_train_batch_v12.py --rows ROWS --qc QC --out NEW_DIR`: after frozen gates pass, encodes, saves a training freeze, and runs at most three methods × three seeds. It does not run by default or generate TEST legal answers.
- `scripts/proof_semantic_fit_v12.py`: one fixed fit, saving logs/DEV predictions before weight export; reloaded weights generate DEV predictions.
- `scripts/proof_semantic_apply_v12.py`: feeds reloaded use probabilities into the same search/check entry without changing evidence, original whole-premise states, or approvals.

## Data and versions

Eligibility decisions cover 95 candidate judgments, allocated as 40 TRAIN/10 DEV/20 TEST. These are source-preparation counts, not valid-label counts. Known duplicate disputes are grouped; incomplete related-litigation verification is disclosed. The old eight cases are separate regression material; existing SEALED contents remain unread. New sources, full tasks, TEST preparation records, and browser material stay local and outside publication.

Proposal contracts/data tasks are frozen. Outputs cannot be repaired from references. Interface integration may finish before the formal training freeze; every actual run retains its code hash. Unaccepted functionality must not be reported as validated.

## Computation

Evidence combinations retain separately checked citations rather than fabricated continuous quotes. Role mappings come from proposed rule contracts; empty objects are not wildcards. Cross-rule links require explicit exact proposition correspondence, not semantic approval by similarity. Unformalized exceptions remain OPEN_TEXT and cannot be removed to enable execution.

Flat/R-GCN reuse two 64-dimensional layers and four relation bases, replacing scalar output with three use classes. E5 retains its fixed revision and encodes all long text in traceable token chunks. CrossEncoder uses the authorized fixed ModernBERT revision; input above 8,192 tokens records coverage failure without truncation. Weight reload, formal training, and downstream quality still require acceptance once actual training conditions are met.

## Verified scope

The old eight-case full-entry regression ran once in approximately 1.36 seconds, without budget termination. This automatic track did not load old reference approvals and cannot be combined with V11 conditional acceptance counts. Synthetic checks establish local isolation, source/status/time checks, evidence combination, logic, and failure-recording behavior only.

CrossEncoder completed one authorized synthetic load/forward/backward/save check, without optimizer steps or a real-case preview. This does not validate formal training, use quality, or GNN benefit.
