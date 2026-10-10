# Proof-carrying teaching case v1

This implementation follows the Student Implementation Guide 4.0 teaching exercise, not a new legal accuracy experiment. The primary artifact is `outputs/proof-carrying-teaching-v1/walkthrough.md`. The internal guide and Teams retrieval record remain local; no PDF or chat transcript is included in the publication list.

## Task and evidence boundary

The sole case is the guide's fictional `DEMO_PERMISSION`. The exact dates 2026-10-12 and 2026-10-13 instantiate Monday and Tuesday. Three synthetic messages/records are authored fixtures, not actual exhibits or judgment extracts. `EXERCISE_SUPPLIED` means the exercise stipulates a premise; it is not a human annotation, legal approval, or certification of source authenticity. All production legal approvals are missing and production use is blocked.

The question is whether one specified authorization covers one specified entry. A negative result cannot establish that no authorization exists or that liability follows. Legal rules, burdens and exceptions are not inferred from this instructional rule.

## Implementation and reuse

`legal_bench/proof_carrying/contracts.py` reuses the strict JSON contract validator, the existing digest interface, and durable JSON writer. `engine.py` reuses `aligned_logic.evaluate` for proposal-side Boolean exercises. It never grants approval. The separately invoked `scripts/check_legal_certificate.py` loads a caller-selected manifest, snapshot, policy and rule registry; it does not import the proposal engine, old logical evaluator, a model or spectral calculations. Its bounded permission and expression tests are independently recomputed.

The old V1–V10 pipelines, prompts, annotations and frozen files are not modified. `scripts/repository_bridge.py` has only a metadata override for a run's reference label and sample role; historical defaults stay unchanged. This prevents a synthetic demonstration from being described as model-generated legal-reference evaluation.

## Trust and checks

The certificate gives IDs, exact snapshot/registry/policy content hashes, premise references, typed bindings, proposed results and scoped requests. It cannot supply `CHECKED` or its own trusted premise approval. The checker verifies immutable file bytes, document identity, exact substring/line locators, review-subject hashes, scope, premise attribution and types, rule eligibility, acyclicity, the requested conclusion's type, and recomputed results. A hash establishes identity only. The caller-controlled manifest and review process remain trust assumptions; this prototype has no cryptographic reviewer identity attestation.

`CHECKED` is qualified by `verification_scope=SYNTHETIC_TEACHING_POLICY_ONLY` and `legal_approved=false`. UNKNOWN and CONFLICTED stay distinct. The local expression policy permits a valid OR branch to suffice while retaining the unresolved branch in the trace. An explicitly required unresolved exception prevents completion. General burden shifts, open-ended evaluative tests and cross-rule derived-premise chains are explicitly unsupported rather than silently accepted.

## Correction and historical validity

S2 adds E3/P4, a separate Tuesday authorization. It preserves P1, P2 and the Monday evidence unchanged. The additive-patch validator checks parent/child hashes, unchanged scope and records, and the declared added premise. The dependency index records the new test and query. C1 can still be checked against S1; using C1 as an S2 result is rejected as stale. No actual person is represented as approving the synthetic patch.

## Graph boundary

The case graph preserves directed evidence, meaning and rule-dependency edges. Only explicitly selected support relations belong to the signed view. REQUIRES and INSTANTIATES are not automatically votes. No opposing party is fabricated for the permission case.

The separate numeric exercise implements the Guide's signed normalized Laplacian with P and N channels, P+N degrees/connectivity, per-component solves and unscored isolates. It reproduces the six-node examples and retains both +3 and -3 records. This is a spectral reference exercise, not ANCO-HITS, GNN training, legal scoring or evidence of improved answers.

## Run and replay

The independent checker requires only the Python standard library and existing repository code:

```sh
python3 scripts/check_legal_certificate.py \
  outputs/proof-carrying-teaching-v1/runs/S1-specific-mismatch/certificate.json \
  --trust-root outputs/proof-carrying-teaching-v1/trusted
```

A replay creates a new directory and refuses to overwrite existing output:

```sh
python3 scripts/proof_teaching_v1.py replay --output /tmp/proof-teaching-replay
```

For numeric examples, use an existing Python environment with NumPy. The recorded run used the Codex bundled Python with NumPy 2.3.5; no packages, models or dependencies were installed. Without NumPy, the checker still runs and the numeric exercise is explicitly marked unavailable.

## Remaining acceptance

The teaching engineering contract is implemented. No real judgment has completed the new approved-premise/approved-rule contract. The next real-case deliverable needs an explicitly accepted premise policy, actual source-based records and qualified legal approval. The 60-case cohort, three teaching judgments, Week 6 freeze and neural variants have not been launched by this task.
