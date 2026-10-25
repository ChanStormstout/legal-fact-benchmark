# Rules and request assessment V1: implementation, experiments, stopping

Date: October 1, 2026. Historical status: **implementation authorized; two-case resource/format checks failed; stopped at P1 under section 3.1.** Actual code/configuration/results: [stage report](../../../outputs/rules-verdict-v1/report-zh.txt). Uncompleted modules below remain plans; versioned outputs define actual run configuration. See the [pipeline](PIPELINE.md) for semantics. This historical authorization does not authorize new runs or publication now.

## 1. Initial delivery and scope

First complete permitted facts → explicit rules → bindings → authorities/request conclusions on at most five existing development cases, then examine at most ten new cases unused in method development. Freeze the method for new cases and retain failures, without replacing difficult cases to manufacture positives or advantage. Report actual compatible-source availability; do not automatically expand to 100.

Start with a specific eviction issue. Follow existing source order, checking regime, jurisdiction, version, and stage. Choose the first compatible group with at least three complete development sources, taking at most five; retain uncertain-relatedness flags. Three is an engineering group-selection threshold, not evidence of adequate induction sample size. If unavailable, extract explicit rules/check interfaces on the first complete development case and disclose insufficient cross-case material.

Subletting eviction is the first candidate because relation diagnostics supply objects. Incompatible regimes/procedures cannot be combined into one rule. Sources determine provisions, temporal criteria, and substantive conclusions; no invented universal Indian-law standard.

Deliver task/split/source manifests, definitions/rules, extraction/execution code, authority indexes, freeze, raw outputs, condition/decision traces, per-question evaluation, a report, and a GitHub review package. Explicit rules, descriptive patterns, and inductive hypotheses remain separate. The original delivery plan requested a Chinese report; repository documentation is now maintained in English.

## 2. Preserve existing work; independent components

The historical working branch is `research/rules-and-verdict`; preserve old main/experiments. Record parent commit, pre-existing modifications, and source hashes. Save actual source snapshots, not only a commit with uncommitted changes. `legal_bench/local_chunk_v11.py` is an unfinished old draft, neither a dependency assumption nor a modification target.

Proposed namespace: `legal_bench/rules_verdict_v1/`. File interfaces never execute model-generated SQL, Python, or arbitrary code.

| Module | Responsibility | Constraint |
|---|---|---|
| `contracts.py` | Task/assertion/relation/rule/trace/result schemas, enums/versions | Field-local unknowns; technical null; explicit old-object adapters |
| `source_views.py` | Locations, permitted/protected views, source/split manifests | Read-only sources; actual downstream passages/content hashes |
| `runtime.py` | Parameterized MLX, schema masks, token/time/memory/failure/resume | Reuse V3 mechanics without fixed old output paths |
| `extract.py` | Ordered chunks, typed assertions/mentions, one consolidation | New format; no inherited 20-item cap/no-time assumption |
| `normalize.py` | Definitions, original/abstract views, families, aliases | Sourced merges; unclassified/disputed items allowed |
| `authority_index.py` | Units/parents, versions, dependencies, FTS5/vectors | Full law retained; fragments do not replace context |
| `rule_cards.py` | Explicit extraction, source review, source nature/scope | Natural-language first; stored text differs from execution |
| `rule_induction.py` | Three candidates, six neighbors, one sourced revision | Optional; record why not executed |
| `pattern_adapter.py` | Two-event candidates, canonical deduplication, support/witnesses | Patterns are not law; no whole-old-batch remine |
| `retrieve.py` | Raw/structured queries, BM25/vectors/RRF/reranking/dependencies | Save rankings, scope exclusions, budget stops |
| `compile_rules.py` | Restricted condition trees, variables/types/scope | Never silently omit unsupported parts or repair semantics |
| `apply_rules.py` | Sourced binding tables, AND/OR, counterproof, exceptions/unknowns | Adapt existing functions; add composition without changing old semantics |
| `decide.py` | Same 9B reads tables/sources for per-request results | Predictions separate from program-supported effects |
| `evaluate.py` | Authorities, conditions, bindings, outcomes, failures, cost | Match count/less UNKNOWN are not accuracy |

Proposed output root: `outputs/rules-verdict-v1/`, registered in `docs/repository-artifacts.json` before initial experiment files. At the original design-only checkpoint this directory had not been created. Every run uses a new `run_id`; existing immutable sources can be hash-referenced without copying datasets.

```text
outputs/rules-verdict-v1/
  protocol/       # Tasks, splits, permitted inputs, scoring, budgets
  sources/        # Manifests/new sources; references for existing originals
  definitions/    # Task categories and mappings
  authorities/    # Units, original text/versions, index documentation
  rules/          # Explicit rules, candidates, counterexamples, coverage
  prompts/        # Templates, complete examples, actual rendered inputs
  references/     # Model references, source evidence, unknowns/disputes
  freeze/         # Hashes, dependency locks, model revisions, source snapshots
  runs/<run_id>/  # Raw output, import, retrieval, execution, assessment, cost
```

Planned CLI: `prepare → extract-dev → build-authorities → build-rules → compile → check-dev → freeze → reference-new → run-new → evaluate → report`. This is not an assertion that these commands currently exist. Resume by input hash/success record without repeating completed tasks. Retain failures; protocol controls retries.

## 3. Prompts, formats, and configuration

### 3.1 Fixed generation and separately locked retrieval

| Setting | Initial choice | Before-freeze check |
|---|---|---|
| Generator | `mlx-community/Qwen3.5-9B-4bit` | Existing revision `8b2b98c00a6b4d291155e4890773ca8f769aee53` |
| Framework | Existing MLX-VLM 0.7.4 environment | Full dependency lock/effective parameters |
| Constraints | Existing logits hook + lm-format-enforcer 0.11.2 | Mask/termination on development examples; no silent disable |
| Sampling | Thinking off, temperature 0, top_p 1, top_k 0, min_p 0, repetition_penalty 1 | Verify actual support/values; seed 20261001 |
| Total context | Initially 32,768 input + reserved-output tokens | Exact chat-template count; not a hardware-capacity guarantee |
| Extraction output | 8,192 per chunk; 4,096 consolidation | Initial caps 32 assertions/64 mentions/32 relations; reaching caps flags possible omissions |
| Rule/final output | 4,096 explicit/inductive rule; 4,096 request answer | Structured fields, brief grounds/provenance; no long reasoning demand |
| Chunks | 4,000 source tokens, 400 overlap, sentence boundaries | Every permitted passage included; oversized single passages prechecked |
| Timeout | Initially 1,200 seconds/call | Retain partial output; technical answer null |
| Encoder | Qwen3-Embedding-0.6B, 1,024 dimensions | Resolve actual revision/tokenizer/dependencies, never invent SHA |
| Reranker | Qwen3-Reranker-0.6B | Fixed revision and yes/no scoring, not verbal confidence |
| Retrieval environment | Separate `.runtime/retrieval-v1`, local Transformers, CPU first | No CUDA/FlashAttention assumption; sequential loading/cache; version device/precision changes |

Load one large model/case at a time. At most two old examples each receive one new extraction and answer for schema/resources. Success means completion, parseability, valid citations, executability, not correct answers. Only semantics-preserving escaping/wrapper repairs are permitted and logged; no guessed fields. Token/item caps retain omission risk; truncated JSON is not completion.

After two resource/format failures, stop and deliver failures. Do not proceed to new cases or tune one case indefinitely. Development changes require a new version and explicit next-round implementation request. No automatic switch to 35B, vLLM, website experiment models, or paid APIs.

If retrieval models are unavailable, BM25 work may finish as BM25, not claimed hybrid retrieval. Freeze revisions/schema limits after development checks, never according to new-case answers.

### 3.2 Prompt content

| Stage | Required input | Output/prohibition |
|---|---|---|
| Extraction | Task, statuses/fields, complete valid examples, source chunk/IDs | Assertions/mentions/relations/affected unknown fields; OTHER allowed, no invented legal outcomes |
| Consolidation | Extracted records, relevant mentions/source windows, IDs | Sourced aliases/relations; no unsupported identity merge/group-action assignment |
| Explicit rules | Complete provision/context or reasoning range, issue/stage | Natural rules, condition roles, exceptions/sources; adoption versus quotation/rejection |
| Induction | Compatible packages, source nature, budgets, counterexample types | Generalizations/support/counterexamples; no legal force from votes/scores |
| Request answer | Shared facts/question/authorities; method-specific tables | Outcomes, objects, evidence/gaps; necessary is not sufficient |
| Website reference | Full sources, allowed/protected lists, shared task/annotation instructions | Input-supported conditions, separate actual judgment, law roles, alternatives/gaps; no local outputs |

Use unrelated fictional people/objects in complete examples, not ellipses or option placeholders. Separate examples show positive, negative, reliable-type-only, and unknown-relation records. Never give the current correct combination. Schema fixes structure; field definitions constrain meaning; source evidence constrains content.

### 3.3 Fair inputs and long text

All primary methods receive identical permitted source scope, without judgment truncation or website-summary substitution. Stage-based exclusion of target reasoning belongs to task definition and records every exclusion; it does not depend on answer correctness.

Before viewing answers, count every complete prompt plus output reserve. For same-authority final-answer comparisons, any method exceeding 32,768 because of full sources/shared law makes the group input-budget-incompatible; retain all prechecks rather than shortening one method's input. Chunked extraction does not give direct answering unlimited context.

Shared authorities follow rank/complete units, not references. Any common-budget reduction applies identically and records excluded units/missing dependencies. Incomplete necessary context prevents deterministic rule conclusions. Never silently cut provisos.

Same information is not same calls. Report per-stage input/output tokens, wall time, peak memory, and reuse for extraction/consolidation/retrieval/final answer. Extra calls are explicit costs. Strict compute matching is a later separate experiment, not implied by one model.

## 4. Milestones and stopping

| Stage | Work/delivery | Stop or limitation |
|---|---|---|
| P0 Task/sources | Compatible issue; at most five old/ten new candidate order; time/labels/groups/corpus; task spec and permitted views | Unknown scope/source gaps reported, no incompatible regimes; new answers withheld from development |
| P1 Contracts/extraction | Schema/chunks/IDs/one consolidation/local unknowns; two old-example checks; recoverable traced records/configuration | Technical failure blocks new cases; retain semantic errors without endless repair |
| P2 Rules/retrieval | Remaining development cases; full law; at most five explicit cards; BM25/vector/reranking | Disclose coverage beyond five cards; never omit conditions yet claim complete relief assessment |
| P3 Application | Compile bindings/exceptions/states; old relation tasks/necessary synthetic counterexamples; executable traced tables | Unsupported real rules remain textual/UNSUPPORTED, never weakened |
| P4 Development/freeze | E0–E2, optional three induction candidates; all settings/tasks/scoring; follow-up disabled | Deliver incomplete-chain failures; no automatic expansion |
| P5 New references/one run | Seal references before E1–E3; at most ten cases, every method/failure | No reference injection/difficult-case replacement; source-missing substitutes follow preset order |
| P6 Results/decision | At most three high-risk disagreements; methods, conditions, law, cost, report/review package | End round; no automatic rule/model/GNN/feedback round |

The five-card cap controls development labor, not permission to omit required law. Covered-issue experiments may complete while whole-request assessment remains incomplete.

Tests target same/different contracts, incompatible hypothetical branches, known types/unknown dates, membership versus identity, explicit negation versus absence, conflict, failed versus successful alternatives, unknown exceptions, necessity/sufficiency confusion, one failed condition among five, technical nulls, and source/answer isolation. Run relevant tests per change and one integrated suite; no repeated old tests without changes.

## 5. Reference isolation

Old three relation tasks, V3/V10, and sources remain diagnostics, not new retrieval/outcome labels. Add only references needed for the target issue, not full reannotation of every judgment fact.

Ordinary High references read the full judgment plus allowed-input manifest and save two layers: input-only conditions/objects/relations/gaps; separately actual judicial authorities/reasons/outcome, possibly using protected answer text. The latter is not information available at prediction time. Save/hash both before local execution.

Authority labels: decisive, relevant, explicitly irrelevant, unjudged, with relevance/scope reasons. Judicial citations are only part of observed reference law; uncited does not imply irrelevant. Retain complete bindings, quotes, opposition, alternative checks, and uncertainty. Reasonable legal disputes retain acceptable interpretations rather than treating one model preference as unique legal truth.

At most five development tasks, ten new-case tasks, and one consolidated disagreement task, all ordinary High with actual model/settings/URL/times/prompts/downloaded JSON. Reuse fully compatible artifacts. Development tasks may review rules; new-case tasks cannot see local output. Prefer lossless local format handling, not repeated completeness follow-ups.

There is no human gold. Label references “model-generated and source-reviewed.” Matching historical outcomes does not prove adjudicative correctness. Semantic scoring relies on those references, with software validation/direct source evidence separate.

## 6. Experiments

**E0: software/format.** Necessary deterministic tests plus two resource/format examples. Executability is not factual correctness; expected answers cannot gate format admission.

**E1: structure for legal retrieval.** With fixed corpus/reranker, compare BM25, raw-query BM25+vectors, and raw+structured hybrid queries. Retain each channel/rank/dependency expansion. Share channel/total caps and disclose extra query costs. Evaluate relevance/scope separately; controlling law with unmet conditions may remain relevant. Report known-reference Recall@8/@24, missed decisive authority, wrong subsection/version, and top-eight relevant/irrelevant/unjudged counts. Incomplete reference sets support known-reference coverage only. Do not compute full precision/nDCG by treating unjudged as zero. Fully labeled small pools support pool-specific ranking, not exhaustive legal coverage.

**E2: same-law structure/execution.** Shared law comes from frozen raw hybrid retrieval, not reference selection.

| Method | Input | Question |
|---|---|---|
| A0 direct | Permitted raw facts/request/issue | Basic no-external-knowledge performance, not same-information RAG |
| A1 text RAG | A0 + shared original authorities/historical reasons | Direct LLM with identical external law |
| A2 structured text | A1 + local facts/relations and textual rule cards | Extraction/rule organization without condition execution |
| A3 execution | A2 + computed binding/evidence tables | Added program execution under identical extraction/interpretation |

A2/A3 share local extraction/cards; A3 cannot use website reference facts. A1 receives corresponding original authorities. Derived representations are the tested mechanism, not extra answers. These are explicitly named historical comparator mechanisms, not additions to the ordinary A0 baseline.

Two local diagnostics on fixed facts ignore object relations or treat unknown fields as negative. They are not complete legal methods; excess candidates are not automatically errors. Judge specific misbindings/overcertainty only with references. If extraction/execution remain inseparable, run one reference-fact-input diagnostic, separately from end-to-end scores.

**E3: full methods.** Compare A1 raw retrieval against A3 raw+structured retrieval. This tests the combination, not one module; E1/E2 explain changes. Reuse completed calls with exact input/config hashes rather than paying again for cost tables. Start with explicit rules only. If development supports induction, separately register added-candidate-rule comparison with hypothetical status/equal knowledge/budgets. Otherwise skip; descriptive patterns cannot be renamed induced rules.

End after E3. Follow-up, graph retrieval, or another model requires a new comparison, not post-error additions still called independent results.

### Scoring and bounded adjudication

Report cases, related-dispute status, and analysis units; multiple conditions are not independent samples. Initial results use numerators/denominators/per-case tables, not small-sample significance as universal proof. Separate authority, condition, binding, outcome, and explanation.

| Reference/result situation | Treatment |
|---|---|
| Established condition/rule, method unknown/not found | Miss/incompletion; trace extraction/binding/status/execution |
| No witness or material unknown in defined sources, method claims match | False positive; inspect identity/source |
| Truly insufficient/disputed evidence, unsupported certainty | Overclaim; distinguish grounded burden-of-proof consequences |
| Invalid binding/quote but matching result label | Not supported matching success |
| Technical failure/null | Separate failure retained in total denominator, not UNKNOWN |
| Same historical outcome with invalid reasons | Outcome agreement, unsupported reasoning, not legal correctness |

Separate technical failure from unsupported task language. Partial success cannot conceal an unexecutable critical condition. First-error locations: source missingness, extraction, identity/relation representation, rule interpretation/compilation, retrieval, execution, open legal judgment, or multiple causes. Downstream UNKNOWN alone does not identify a broken executor.

Review at most three new-case disagreements, prioritizing unsupported MATCH, missed clear positives, then unknown despite sufficient text, ties by preset sample order. One relevant-source/disagreement check each, optionally one consolidated High task. Reference corrections retain old versions and rescore all methods; method defects wait for a new round, not same-round repair relabeled unseen evaluation.

## 7. Later-component entry criteria

| Candidate | Trigger | Comparison |
|---|---|---|
| Bounded follow-up | Existing permitted evidence/law was missed | Zero versus one round/two gaps, same sources, no protected answers |
| Contrastive learning | Stable definitions and adequate reviewed same/different examples | Frozen 0.6B versus learned representation; confusion/binding, no evaluation leakage |
| Pretrained GFM-RAG | Faithful source/status graph and local feasibility; key chains still missed | Frozen checkpoint versus text, equal corpus/candidates, cost |
| R-GCN LawRanker | Positive/negative/unjudged relevance and valid dispute split | Same-feature linear/MLP versus R-GCN, initially separate from VerdictNet |
| VerdictNet | Stable request labels/upstream predictions and grouped cross-fitting | Same-information LLM/MLP versus graph; outcomes/reasons/calibration/cost |
| Second generator | Completed V1 chain; need model-specificity check | Separate resource check/freeze, same key tasks; no mixed-model results |

Use authors' public GFM-RAG implementation/checkpoint at a fixed revision. If extraction models, changed representations, or unsuitable local support are required, report adaptation costs rather than quietly substituting a different graph method. Document source/status mapping.

Possible later R-GCN starting configuration: three layers, hidden 256, four bases, dropout 0.1; AdamW 1e-3, weight decay 1e-4, at most 50 epochs, development patience five; seeds 20261001/20261002/20261003. These are starting values, not optima; tiny validation does not justify broad search. LawRanker uses pairwise adjudicated relevance, never unjudged negatives. VerdictNet class weights use training distribution only.

Split known disputes before training/validation and respect time. VerdictNet training features come from upstream predictions made without that group's labels. Insufficient groups defer training; same-case conditions cannot fabricate independent training cases. [UniLR](https://aclanthology.org/2025.acl-long.584/) is a historical task-relevant retrieval reference, not evidence that its label/corpus advantages transfer to this architecture.

## 8. Delivery sequence and collaboration

Reviewable implementation units, with schedule determined by measured resource checks:

1. Task contracts/input scope: namespace, schemas, source maps, manifests; reviewable without calls.
2. Extraction/import: MLX entry, compact format, chunks/consolidation, format/citation checks; at most two old-example checks.
3. Authorities/rules: units, BM25/vector/reranking, explicit cards, source review.
4. Application: compiler, full bindings, logic, unknowns/counterproof/exceptions, necessary tests; complete development chain.
5. Freeze/one comparison: reference isolation, code/config snapshot, E1–E3, bounded disagreements, full report.

Update `docs/CHANGELOG.md` per completed stage. Update experiment indexes/latest pointers only for actual experiments. Run `python3 scripts/repository_bridge.py prepare`, inspect `review/PUBLICATION.json`, then `verify`. Publication excludes environments, weights, credentials, browser screenshots, bulk third-party data. Prepare/verify are local only; `sync --message ...` commits/pushes solely with publication authorization.

Review packages state goal, actual hashes, allowed inputs, method, results/failures, and specific questions. ChatGPT comments are proposals, not direct rule/reference overwrites. Confirmed issues become separate edits/necessary tests and an authorized new version; website review must identify the snapshot actually read.

Begin with task contracts/development issue, then resource/format checks. After sources yield traceable bindings, add law/request assessment. Any failed stage delivers its complete result/reason rather than hiding failure through more cases, GNNs, or repeated website revision.
