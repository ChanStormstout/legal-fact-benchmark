# V20.2: ten code repairs and cache acceptance

This version consumes V20.1 originals through `scripts/proof_source_verification_v20_2.py`, saving results in `outputs/proof-source-verification-repair-v20-2`. Authorization covered consolidated F01–F10 repair and acceptance through caches/actual call chains. The old batch stays paused. No model generation, embedding inference, training, or website submission ran. Old code, proposals, failed outputs, budgets, and contracts remain byte-identical.

P is an initial structured proposal; Q is subsequent source review/local supplementation. SUPPORTED, UNSUPPORTED, and UNRESOLVED mean source support, lack of support, and semantic uncertainty. Unreviewed claims have null labels, not one of those three. Application may restrict them as UNRESOLVED while separately retaining original label and application state.

| Issue | Repair and evidence |
|---|---|
| F01: production dropped invalid local EV dependencies while the checker retained them, rejecting whole cases | Both independently inspect original invalid markers/out-of-range IDs and leave only affected uses unresolved. Two old cache rejections became zero across five cases; injected unauthorized transformations remain detected. |
| F02: ignored `counter_refs` | UNSUPPORTED can use valid primary/opposing sources; SUPPORTED still needs primary sources. Positive judgments with only counterevidence remain isolated with citations retained. |
| F03: website scores overwrote technical status | Local run records and formal answers jointly determine technical status. Empty/truncated answers cannot be scored completed or semantically successful, and imports cannot rewrite that status. |
| F04: missing scoring submission/input provenance | Each batch binds task, reply, receipt, rules/sources, checklist, fixed blind order, and answer hashes. Planned answer IDs must match; cross-batch duplicates are rejected. |
| F05: unreviewed/quarantined/technical failures conflated with semantic UNRESOLVED | Claims retain REVIEWED, NOT_REVIEWED, or QUARANTINED plus execution reasons; semantic labels may be null. Review coverage is not accuracy. |
| F06: extracting merged `answer` lost PARTIAL/partition failures | Candidate assembly, application, checks, and final material propagate P/Q statuses and combined snapshots. Final writing reads execution state; classifiers exclude Q self-labels/reasons/execution status. |
| F07: permanently reused old merged files | Partition run/output hashes define composition identity. New completions create new immutable snapshots; old ones remain. Global assembly awaits every Q terminal slot; explicit per-case cache acceptance may process partial results. |
| F08: incomplete dependency/config freeze | Recursive AST import discovery covers local, in-function, and relative imports; explicit entries add encoding subprocess/acceptance dependencies. Freeze includes 106 source files and three key configs with drift checks. |
| F09: pause guarded generation only | P, Q, final, fit, fit-one, and encode check pause before constructing executors. P consecutive-failure stopping persists on reentry. All six paused entries return PAUSED. |
| F10: missing/duplicate predictions still yielded formal metrics | Strict ID/probability/label validation; missing, empty, or null predictions make formal F1/error/NLL null. Completed-subset metrics are diagnostic only, not full-method comparisons. |

## Actual acceptance chain

`scripts/proof_source_verification_accept_v20_2.py` is the unified entry. All 36 existing and 18 new regression tests passed (54 total). Acceptance copies old caches, then uses the new real entry to combine P/Q, assemble candidates/shared inputs, apply Q judgments, run independent checks, and construct final material. The real local tokenizer counts final prompts without model weights. The same chain replays after freeze and verifies old hashes.

Cases: 277181, 280457, 444449, 569555, 923000. A/C/D use real sources/caches. E/F/G inject explicit synthetic SUPPORTED judgments solely for prediction-interface/application/final-material fidelity; they are untrained and cannot compare capabilities. B's real dispatch entry uses synthetic transport in unit tests; cache acceptance rejects missing real A by dependency. Synthetic records verify website-scoring provenance; no new website scoring occurred.

Hashes confirm preservation of 951 old batch files/frozen code and 631 copied cache files. New snapshots/final material stay in the new directory. Input/encoding/supervision hashes are checked around fitting. E/F/G final entries also match prediction files, fit inputs, and current material. The new output root is registered; raw tasks, caches, private records, weights, and frozen-code copies are excluded from publication.

## Research results not established

Across five cases, 748 claims await review. Formally usable old Q judgments increased from 73 to 80; all seven recovered judgments are UNSUPPORTED with valid opposing sources. Six SUPPORTED judgments with only opposing citations remain isolated. 80/748 is coverage, not accuracy. Wrong bindings, court-stage confusion, OPEN_TEXT, and missing shared-variable contracts still require source-level research.

D–G material for 277181, 569555, and 923000 exceeds the 65,536 context budget after reserving 8,192 output tokens and 256 template tokens. Interfaces construct/check material, but real generation must still reject it under existing capacity gates; sources cannot be truncated to claim resolution. Ten DEV cases still lack P. Final-answer/training comparisons have not run.

This round completed engineering repairs and local review preparation, not legal approval or demonstrated learned-model final-answer improvement. The old batch remains paused. Resume, training, generation, and website scoring require their corresponding authorization.
