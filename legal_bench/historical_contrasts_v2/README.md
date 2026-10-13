# Historical contrasts V2: source-reviewed training

This is an isolated, authorized historical case-route retrieval experiment. It
does not switch the active entry, resume a parent generation queue, or approve a
legal answer. V1 source and acceptance bytes are retained unchanged.

## Data and supervision

The initial 22-query cohort was expanded before any fitting or ranking inspection
to 28 exposed development queries: 17 TRAIN, 3 VALIDATION, 8 DEVELOPMENT_HOLDOUT.
Ten disjoint historical cases form a common fixed candidate pool. Known duplicate
125596702 is excluded. Unrelated eviction grounds are not added to pad the sample.
No old SEALED/TEST body is opened. Dispute identity beyond checked document IDs and
known duplicates remains unconfirmed, so this is not an independent final test.

GPT-6 High receives the original allowed passages and independently labels each
query/candidate POSITIVE, NEGATIVE, UNKNOWN or DISPUTED, with exact source quotes.
The user authorized these labels as the operational ground truth for this round;
their origin remains model-generated source review, not human gold. Old evidence
use/authority classification labels are not reused as this task's answers.

Historical route outcomes are reviewed against full original judgments, stored in
a sidecar and excluded from features. Input visibility reviews may remove an entire
original source unit; original text and exclusions remain saved. Source addresses,
quote spans, source-view hashes and split/group joins are checked. A citation to a
masked passage rejects that label; it is not automatically relabeled as negative.
UNKNOWN/DISPUTED and invalid annotations never enter pairwise loss.

## Model interfaces and computation

The model text uses complete admitted source passages plus the common fixed issue.
The graph contains CASE, ISSUE, ROUTE and SOURCE nodes, source attribution and case
membership edges and reverse message edges. **It is a source grouping graph, not
the complete entity/condition/proof graph proposed for the final system.** No
unreviewed semantic bindings or entailment edges are fabricated to obtain training.
All methods see the same source information and the same ten candidate cases.

Pinned E5 is frozen. Full BPE tokenization precedes bounded windows and normalized
pooling. Text batching across all views only computes independent frozen text
embeddings; it creates no cross-query message or supervision edges. Every actual
GNN graph contains references plus exactly one query. IDs, split, annotation
reason, utility and target outcome are not numeric or textual model features.

PyG GraphSAGE uses the existing V1 Ranker: two mean-aggregation layers, width 128,
fanouts [15,10], CPU execution. Sampling is fixed independently of model seeds.
AdamW updates parameters on softplus(negative score - positive score), with gradient
clipping. Explicit source-reviewed negatives only; each query's pair loss is averaged
so many within-query pairs do not make that query an independent larger sample.
Validation NDCG@3 selects the earliest best epoch; holdout labels never enter loss.
Weights are saved as tensor-only checkpoints and reloaded with weights_only=True.

Official operator documentation: [PyG SAGEConv](https://pytorch-geometric.readthedocs.io/en/latest/generated/torch_geometric.nn.conv.SAGEConv.html).
Architecture background: [GraphSAGE paper](https://arxiv.org/abs/1706.02216).

## Frozen comparison and adequacy

The complete plan has seeds 13,37,71,101,137, 60 epochs, lr .001 and weight decay
.0001, with no architecture or hyperparameter search. Baselines are lexical cosine,
frozen E5 cosine, their RRF fusion, a Flat MLP, random ordering and a training-only
candidate frequency prior. GraphSAGE without edges retains the architecture and
features but removes messages. This separates structure effects from simply fitting
a neural scoring function and from memorizing generally popular candidates.

Nested training subsets of 5 and 11 trainable queries are compared with the full
trainable set. A TRAIN query with no reviewed positive-negative pair is counted in
data composition but contributes no optimization step. Independent case count,
pair count and accepted reference count are reported separately.

All selected checkpoints, including learning curves, freeze before any holdout
metric is computed. Report per-seed means/SD and paired query-group bootstrap
intervals. Metrics use judged-only rankings, filtering UNKNOWN/DISPUTED/invalid
labels rather than calling them false positives. Their frequency in the actual
top three is reported separately. Also report the subset of queries containing
both positive and negative candidates, since all-positive queries cannot distinguish
ranking methods. Opposite-outcome relevant-pair coverage is an exploratory metric;
it does not validate same-route distinctions or downstream legal benefits.

## Execution and current checkpoint

```sh
PYTHONDONTWRITEBYTECODE=1 .runtime/proof-semantic-v12/bin/python3 -B scripts/historical_contrasts_v2.py assemble
PYTHONDONTWRITEBYTECODE=1 .runtime/proof-semantic-v12/bin/python3 -B scripts/historical_contrasts_v2.py train
```

`assemble` rejects incomplete review coverage. Private dependencies are loaded only
in this process. Data, model weights, task prompts, raw responses, source views and
per-case details remain in private subdirectories, excluded from publication.
The complete comparison is finished: all 28 query reviews were exported and audited,
25 selected checkpoints (15 full-cohort plus 10 nested-size fits) were replayed,
and the result report is outputs/historical-contrasts-v2/report-zh.md. Four invalid
source citations are excluded, and five unknown labels are not negatives. Sixteen
TRAIN queries contribute pairwise loss. All five-seed models and the training-only
frequency baseline have holdout NDCG@3=1, so no graph-specific gain is established.

The original training call stopped at its final preservation audit because three
shared entry documents changed concurrently. Frozen data/code/checkpoints and the
remaining 576 protected source/module files matched. An isolated no-training
finalizer verifies them, replays checkpoints and records the metadata differences.
It never reverts the other work or bypasses source checks. Its script is deliberately
bound to the completed frozen run and is not a new tuning/training entry point.

The earlier three-fit technical pilot is retained unchanged and is excluded from
the 25 formal fits. Raw replies, per-task identities, multipart merge receipts,
exact citations and original technical failures remain in private directories.
