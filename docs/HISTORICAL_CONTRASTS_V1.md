# Historical-contrast retrieval: interfaces and implementation V1

This independent historical-case retrieval component does not switch the V20.4 entry, resume the old batch, train, commit, or push. See the [module guide](../legal_bench/historical_contrasts_v1/README.md) and [acceptance report](../outputs/historical-contrasts-v1/report-zh.md).

Implementation order: old-cache adaptation/validation, graph and ID maps, full-text encoding, shared candidates, simple retrieval/GraphSAGE ranking, historical-contrast review, and handoff to existing gates. Ranking offers relevance signals. Data entering rule computation still require original gates. Historical facts do not become current-case facts.

| Interface | Required content | Invariant |
|---|---|---|
| CasePacket | Complete old material, shared sources, objects/evidence/uses/bindings, selected query, versions/status | Preserve values/order; local references resolve to declarations; sources/records are traceable |
| GraphRelease | Typed nodes/edges, global UIDs, node indices, sources/visibility | Correspond to original material; IDs are not features; supervision/review decisions are not message edges |
| CandidatePool | Case–issue–path, scope checks, retrieval channels/exclusions | Exclude the query dispute; unknown is not negative; methods share candidates |
| RankRequest | Query UID; graph/feature/candidate hashes; model role; sampling/budget | Match task/dependencies; random weights cannot be presented as trained |
| RankResult | Every candidate score, deterministic ranking, top k, actual coverage | No invented/missing IDs; finite values; scores do not change evidence/review states |
| ContrastBundle | Both paths, results/differences, sources/reviews | Unreviewed items stay pending; case-level winner is not a path result |

Material and proposal snapshots are separate. The former establishes source/case-node identity; the latter scopes local EV/OBJ/USE IDs and bindings. Original SRC:1-style IDs and order remain; global graph UIDs do not replace them. Text offsets use frozen Unicode character positions, with original-file character/byte ranges separately checked. Original rule versions remain complete; changes alter proposal/graph/cache identity. Unreviewed legal period, request type, and path equivalence are not inferred automatically.

Source files, frozen text, graphs, encoding, sampling, and inference are recorded separately. Encoders read every BPE token across windows; GNNs read sampled subgraphs; original reasoners read their complete required conditions. Full encoding does not prove relational understanding, and sample coverage is not full-material coverage.

State conflicts, out-of-range/misaligned references, stale versions, or changed sources reject computation while preserving originals/reasons. Semantic errors require source review. Training/legal approval remain incomplete. Existing gates block entire partitions; this version does not introduce dependency-local release.

The current source view uses exposed judgment material for engineering acceptance only. Production SAGE requests and TRAIN labels are blocked by incomplete outcome-masking review. New-task source-reviewed labels and same-path outcome comparisons are required; old use-classification labels cannot establish retrieval effectiveness.
