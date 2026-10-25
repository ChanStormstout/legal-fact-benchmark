# Historical contrasts V2

Training/comparison completed; see the [report](../outputs/historical-contrasts-v2/report-zh.md)
and [component interfaces](../legal_bench/historical_contrasts_v2/README.md).
Twenty-eight queries/ten historical candidates, split17 train/3 validation/8 development
holdout; sixteen training disputes produced307 ranking pairs. GPT-6 High labels served
as operational references, not human gold:280 requested,276 passed interface/citation
checks, four invalid references excluded, five unknowns not treated as negatives.
Historical results stored separately, eight source passages masked, all217,580 text
tokens encoded.

Fifteen main five-seed fits plus ten nested-data-size fits yielded25 fits/19,200 updates;
three earlier technical trials were preserved separately. GNN, ordinary neural network,
no-edge GNN, and training-candidate-frequency ranker all reached held-out NDCG@3=1.0.
No added graph-structure benefit. The query-free frequency ranker also saturated the
metric; GNN top-three sets were identical across eight queries/five seeds. The same
conclusion held for six holdout queries with positive and negative candidates. Sixteen
training disputes, ten candidates, and85.9% positive holdout prevalence limit task
difficulty; low seed variance cannot establish sufficient data.

The graph has source/case/issue/path membership only, not complete entity/event/condition/
legal-derivation structure. Independent tests, whole legal-answer benefit, and human
certification were not evaluated. Model selection froze before holdout scoring; no
relabeling or tuning to improve results.

Acceptance reloaded25 weights and exactly replayed420 model scores,80 learning-curve
holdout scores,700 simple-method scores, and1,120 metric records. Twenty-one new interface
tests/two summary-protection tests plus prior45 component/46 original-gate checks total114.
Concurrent changes to three shared entry documents stopped the final summary check;
the failure/original preservation manifest remain. Other576 old modules/sources matched.
Independent summary completion added no training or rollback of shared entries. Main
queue paused; no publication or default-entry switch by this experiment.
