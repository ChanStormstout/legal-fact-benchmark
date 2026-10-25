# V19_6 shared-contract repair

This round repairs interfaces and replays caches only. Generation, web tasks, and
training remain paused. New artifacts are in `outputs/proof-contract-integrity-v19-6/`;
old V19/Together inputs, schemas, raw outputs, and failures are unchanged.

The shared entry is `scripts/proof_contract_integrity_v19_6.py prepare|replay|freeze`.
`legal_bench/proof_carrying/local_runtime_v19_6.py` validates the complete new schema,
constrains unique string arrays, and applies second-occurrence source-repetition
protection. Saved output enters the common `accept_saved_output` importer for coverage,
independent checking, and common-information learning-input preparation. The CLI has
no generation/training command; old entry points must not bypass the checks.

The contract represents analyses as an object with fixed rule-premise IDs, each allowing
NOT_ANALYZED. role_objects supplies OBJ addresses or UNMAPPED for the premise's rule
roles. Conversion constructs role addresses without inferring identity. Import checks
dynamic EV/OBJ/USE existence. A witness selects one permitted source address; code
restores its original text. SRC addresses appear next to unchanged source/rule content.

The validator rejects duplicate arrays, duplicate JSON keys, and unknown schema keywords.
Decoding prevents repeated values in schema-declared unique string arrays, but does not
guarantee dynamic references or semantics. Natural termination, contract validity,
analysis coverage, and legal support are recorded separately. Independent checking
compares all relevant list counts before individual items, retaining attribution,
status, and stage.

Old caches use their original production contracts and are not relabeled as new
outputs. New common inputs receive new hashes and PREPARED_NOT_YET_ENCODED status;
old weights are not represented as trained under the new configuration. Legal approval
remains absent, OPEN_TEXT is not forced into execution, and local structural usability
does not establish a premise.

[Report](../outputs/proof-contract-integrity-v19-6/report-zh.md),
[Protocol](../outputs/proof-contract-integrity-v19-6/freeze/protocol.json),
[Engineering acceptance](../outputs/proof-contract-integrity-v19-6/engineering-acceptance.json).
No commit or push in this round.
