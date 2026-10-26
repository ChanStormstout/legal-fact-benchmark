# V10 whole-document source extraction

This is an isolated implementation, not a completed model experiment. It preserves V8,
V9, their failures and the main project entry point. It does not run the full RAPIDO
reasoning/report pipeline or change the ordinary single-call A0 baseline.

The new method assigns each source assertion to a reversible passage group, runs a
primary reader and a second reader that cannot see the primary output, reconciles the
readings against the original, and reviews the resulting extraction. The ontology
separates a speaker from event participants, occurrence from legal effect, an open
question from an assertion, and current-case content from quoted cases and headnotes.
These are typed source records, not an OWL reasoner or verified legal knowledge.

The entire rendered judgment remains available in every V10 model request. Review
targets are grouped across the document to avoid repeating every intermediate record
in one oversized request. This is one pass over all records, not repeated attempts
until a case passes. Source-reference dictionaries are lossless; they do not decide
what a source means. Only future model calls may propose interpretations or verdicts.

## Current status

- Implemented: source ownership, blind second reading, explicit scoped negation,
  source-backed role/time/court fields, version-bound reconciliation, final source
  review, unresolved coverage, immutable results, cohort runner and annotation export.
- Offline interface evidence: the complete 1251841 source and preserved V9 outputs
  traverse the new interfaces. All projected interpretations remain UNRESOLVED. This
  is not independent reading or evidence of better extraction.
- Prepared: six complete rendered source documents, original locators and hashes,
  deterministic selection record, actual first-call previews, and source-only
  annotation packets. Reference annotations are still pending.
- Not performed: new Qwen calls, six-case quality comparison, full C execution,
  training, default-entry changes, commits or pushes.

## Comparator word limit correction

The prior local adapter rejected inputs at 6,000 words with
`UPSTREAM_MULTI_CHUNK_ADAPTER_NOT_IMPLEMENTED_NO_TRUNCATION`. This was a limitation
of our adapter, not a Qwen limit or an upstream rejection rule. The pinned upstream
`land_dispute_pipeline/Python/new_pipeline.py` uses overlapping chunks of 6,000–8,000
words. The new `latentweaver_v10.py` removes the local refusal and passes the full
document through the existing local same-Qwen adaptation. No original text is deleted.

This remains a **full-document local adaptation**, not the original upstream model
or its native chunk schedule. Existing local prompt guidance and constrained candidate
format remain disclosed. It is not a plain one-call baseline. The native repository
commit is `156a0c32275682421bc0746678749e20a318debf`.

## Files and commands

- `IMPLEMENTATION.md`: mechanism, interfaces, review findings and remaining risks.
- `EXPERIMENT_PROTOCOL.md`: cohort, fairness, labels, whole-document metrics and stops.
- `COST_ESTIMATE.json`: receipt-grounded planning estimates; not fee authorization.
- `private/preparation/cohort.json`: inclusion, exclusions and source manifests.
- `private/preparation/requests/`: actual first-reading wire previews.
- `private/offline-whole-document-review/`: complete cached-record interface replay.
- `freeze.json`: exact code, source, prompt and dependency hashes.

Use the existing `.runtime/qwen35-v1/bin/python` interpreter with `-B`. Tokenizer
inspection reads only tokenizer assets, never model weights. From this directory:

```sh
python -B execute_cohort.py
python -B execute_cohort.py --run --authorization private/approved-authorization.json
python -B evaluate.py export private/experiment-v1 private/evaluation-v1
```

The second command requires a real new approval bound to the freeze hash, cases,
arms, fee cap and prior accounting. No approved authorization file is supplied here.
Existing paid trials do not authorize this new six-case experiment.
