# Historical contrasts v1

An isolated, local retrieval component for source-bound historical case/issue/route
comparisons. It does not replace the active experiment or authorize training.

`adapter.packet` retains the complete legacy case, rules, part, P, schema and saved
binding reviews. Multiple targets require an explicit `query_id`; TEST/SEALED
inputs are rejected. Source identifiers are qualified by dataset, case and material
snapshot. Record identifiers additionally include proposal snapshot, part and exact
local address. Material and proposal snapshots are distinct: two parts share the
same source nodes without merging their evidence uses or entities.

`contracts.py` is the single schema registry. Every envelope has a kind, version,
body and canonical-JSON SHA-256. Original file checksums use file bytes. Text/view
hashes in these interfaces hash the canonical JSON representation of the string;
they are not interchangeable with original-file or legacy plain-text hashes.
Validators reject extra fields, duplicate JSON keys, NaN/Inf, undeclared references,
source/span changes, missing records, mismatched object dependencies, changed query
selection, and attempts to promote technical or gate states. Opaque original data
is preserved but is not a feature whitelist.

Interfaces: `CasePacket`, `GraphRelease`, `CandidatePool`, `RankRequest`,
`RankResult`, `ContrastBundle`; `ContrastReview` and `RelevanceLabel` are separate
source-bound review inputs. RankRequest.query_id is the global ISSUE node UID;
CasePacket.query_id retains the original target address, e.g. Q1.

`graph.build` creates CASE/ISSUE/ROUTE/SOURCE and proposal nodes. Binding metadata
is represented as nodes. Support, opposition and context have separate relation
types; reverse edges are message edges, not reverse legal entailments. Graph nodes
and edges are checked against their original packets, and typed tensor indices are
derived from sorted UID maps, never used as business identifiers. Case material and
proposal edges make case facts reachable from the query within two hops.

`encoder.encode` uses the already cached, pinned E5 checkpoint offline. ISSUE uses
`query: `; other nodes use `passage: `. Full BPE tokenization precedes bounded
windows, token-weighted chunk pooling and L2 normalization. All token IDs, offsets
and windows are recorded and independently replayed. Complete token consumption
does not guarantee preservation of every cross-window semantic relationship.
`graph.hashed_features` is a clearly marked alternative for contract smoke tests.

Candidate discovery combines global issue discovery, lexical cosine, pinned E5
cosine and signed proposal-structure/count signatures through reciprocal-rank
fusion (k=60, equal weights). Missing signatures remain unavailable rather than
negative labels. Scope description differences remain pending; explicit conflicting
canonical stage/URN values are excluded. Capacity is 200 and default top-k is 10.
All scorers receive exactly the same frozen pool. Historical route equivalence and
outcomes need source-bound review; whole-case win/loss is not a route label.

`model.Ranker` uses real PyG HeteroConv/SAGEConv, two layers, hidden size 128, mean
aggregation and a pair scoring head. The Python neighbor sampler records two-hop,
per-relation budgets [15,10], seeds and exact sampled edges; it requires no optional
compiled sampling extension. Inference uses a private reference-plus-one-query
graph and frozen parameters. Random smoke checkpoints cannot be reported as a
trained method. The current extracted judgment views are explicitly exposed and
not outcome blind: production SAGE requests and TRAIN labels are rejected until
the required source visibility review is present. The v1 CLI has no fit mode.

`contrasts.form` accepts reviewed, source-bound route/outcome/distinction receipts,
checks scope and source ownership, and otherwise reports pending candidates. It
does not invent distinctions or turn retrieved historical facts into query facts.
`training_pairs` keeps UNKNOWN/DISPUTED out of negative supervision, checks
dispute groups/exposure and separates TRAIN/DEV. Legacy use-classification labels
cannot be imported under the new task identifier. References are not human gold.

`adapter.handoff` rechecks the existing binding gate independently of rankings.
NOT_ANALYZED units containing records/objects/uses/judgments are preserved but
blocked before computation. Technical failure remains null; conditional processing
does not confer semantic or legal approval. Existing whole-part gating is preserved;
dependency-local isolation is a separate future integration, not silently enabled.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 .runtime/proof-semantic-v12/bin/python3 -B scripts/historical_contrasts_v1.py verify --neural-smoke --semantic-encoder
```

PyG dependencies are isolated at `.runtime/historical-contrasts-v1/site`; the
script adds this path only to its own process. Existing environments and weights
are not modified. The E5 encoder is read from the existing pinned local cache.
Outputs are immutable, versioned by code/configuration under the explicitly
registered `outputs/historical-contrasts-v1`. Full packet/graph/feature artifacts
stay under private subdirectories; tensor-only sage_graph.pt roundtrips with
weights_only=True. No cloud generation, annotation, optimizer, push or queue resume
is performed. The synthetic normal-path test is distinct from real blocked-case
acceptance and from model effectiveness.

Training/data readiness still requires reviewed relevance labels, source-bound
same-route contrasts and outcomes, and a query view that excludes hidden outcomes
and their textual proxies. No retrieval or legal-quality improvement is claimed.
