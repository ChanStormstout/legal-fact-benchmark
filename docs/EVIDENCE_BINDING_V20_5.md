# V20.5: nonempty evidence and object-binding acceptance

This separately authorized repair reuses V20.4 local-ID constraints without replacing the main experiment entry or resuming its batch.

Original text, SRC IDs, proposals, labels, failures, and frozen source remain. Complete text is saved and enters prepared model input for model/human reading. Blank lines are excluded only from selectable generated evidence citations; IDs are not renumbered. Old wrong answers are not repaired by deleting citations, changing IDs, or guessing objects.

The generation schema excludes blank source text. Each role can select only locally declared objects; explicit type conflicts are blocked during generation. Types come from existing rule types or complete, exact generic descriptions in `original_variable_descriptions`. Five bounded aliases appear in `TYPE_ALIASES`. Types are not inferred from role/person names, substrings, or similarity. Unclear types stay unresolved; UNMAPPED remains available for unestablished bindings.

Independent post-generation checks recompute local ID bounds, source nonemptiness, required evidence locations, type conflicts, and binding-review status. ID existence/type compatibility do not establish identity. Every actual binding, including roles in uses and judgments, needs source review. Review records bind proposal/full-source/rule hashes plus each binding's content hash. Stale, duplicate, unsupported, or mismatched records do not unlock computation.

Statuses:

- REJECTED_EVIDENCE_OR_BINDING: definite citation/type error.
- NO_ANALYZED_UNITS: complete catalog but no analyzed unit.
- BINDING_REVIEW_REJECTED: source review rejects the binding; original proposal remains.
- BINDING_REVIEW_PENDING: source review remains incomplete.
- READY_FOR_CONDITIONAL_PROCESSING: engineering prerequisites for conditional processing hold.

`gate.process_saved` calls original conversion, merge, and independent checks only for the last status. Otherwise candidates remain available for inspection, `formal_answer` is null, and conditional computation has not run. Technical failure is not relabeled UNKNOWN. Once processing starts, valid/invalid/model-rejected/unresolved uses are counted separately; processing completion is not use validity. All outputs remain model proposals/source reviews, without legal approval.

`reviews_from_q` adapts existing Q source checks to binding reviews. Callers must supply the frozen `original_P_sha256`, `source_sha256`, `rule_sha256`, and `run_status=OK`. Mismatches/incomplete calls are rejected. The adapter reads existing checks without a model call. Direct reviews use zero-based path indices:

```json
{
  "payload_sha256": "...",
  "source_sha256": "...",
  "rule_sha256": "...",
  "verdicts": [{
    "path": ["analyses", "R1.P1", "uses", 0, "role_objects", "tenant"],
    "claim_sha256": "...",
    "label": "SUPPORTED",
    "refs": ["SRC:1"],
    "reason": "Reason grounded in source review"
  }]
}
```

`claim_sha256` comes from `binding_claim`; other hashes come from complete current data. SUPPORTED/UNSUPPORTED require nonempty, permitted, nonblank source addresses. UNRESOLVED may lack sources but does not count as support. Review remains fallible external semantic judgment, not programmatic proof or independent human gold.

Four prepared tasks are under `outputs/proof-evidence-binding-v20-5/preparation-02`. Their complete source suffix is identical to the old prompt. The obsolete decoder-ID disclaimer was replaced; examples now contain two populated analysis units showing EV/OBJ/USE numbering restarting locally. New runtime: `local_runtime_v20_5.Runner`. Generated outputs must separately pass `evidence_binding_gate_v20_5.accept_saved`, which writes acceptance elsewhere without changing generation directories.

```sh
.runtime/qwen35-v1/bin/python3 -B scripts/proof_evidence_binding_v20_5.py verify
.runtime/qwen35-v1/bin/python3 -B scripts/proof_evidence_binding_v20_5.py accept --case-id CASE --part PART --input-dir DIRECTORY --reviews REVIEW_JSON
```

These commands do not generate or resume a queue. This round made no real model rerun, training, Q call, website submission, commit, or push. Object matching and legal-semantic improvement in new real output remain unverified.
