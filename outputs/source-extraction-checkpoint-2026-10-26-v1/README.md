# Source extraction checkpoint: atomic records and specialist readers

This is an immutable publication checkpoint, not a declaration of a successful
experiment. See [snapshot manifest](SNAPSHOT_MANIFEST.json) for capture time, original
and published hashes, exact file selection and per-version status. The working
experiments were not stopped, edited or copied as active mutable directories.

## State at capture

- V15: 22 reading calls and four reconciliation calls had completed. Final source
  review was still running; no complete final source result or quality score existed
  in this snapshot. Its code, prompts, configuration and completed calls are included.
- V16: three specialist readers were implemented, offline interface replayed and
  frozen. The process was queued behind V15. No V16 model result existed at capture.
- V14: four initial reading calls completed without the earlier citation loop or
  socket timeout. This demonstrated technical delivery on these calls, not improved
  whole-document extraction.
- Earlier failed V8-V13 attempts, including the V12 retries, remain represented by
  saved execution artifacts. Missing output is not a semantic score.
- The saved LW comparison is a same-Qwen full-document adaptation of
  LatentWeaver/legal-ai at 156a0c32275682421bc0746678749e20a318debf, not native upstream
  model performance. Its 25-node/48-edge graph failed one structural relation check.

## Research question and concrete observations

We are testing whether structured, source-grounded reading actually improves
extraction over the teammate adapter, rather than merely increasing calls and
fields. The input is the complete rendered judgment 1251841, including its outcome.
This is an exposed development extraction case, not pre-judgment prediction.

V15 raw readings sometimes separated the 1931 decree, 1935 auction purchase and
1936 possession delivery into distinct records. Both first readers still copied a
compound legal headnote into one proposition. One reader treated a dissented-from
authority as approved; some event records were classified as obligations and a
denial as a burden. These are raw-reading defects, not an adjudication of the
not-yet-finished final packet. More records do not establish more correct content.

The LW adapter already separated several central events and extracted the permanent
lease and ordinary-management issues. It also incorrectly described Chohan Ram as
Wazir Narain Singh's son; the source identifies Hiraman Ram as his father. Its own
citation validation did not establish semantic correctness. Current evidence does
not establish a V15 or V16 advantage over LW.

## Method changes

V15 adds explicit assertion types, one-core-assertion instructions and source-based
granularity assessment in reconciliation/final review. Conditions remain attached
to the propositions they qualify. Composite or uncertain granularity cannot be
counted as model-supported by the final program gate. The model can still misjudge
both content and granularity; the gate is not a legal correctness guarantee.

V16 changes the blind reading assignments to facts/entities, procedure/court scope,
and law/conditions/burdens. All role records receive equal-status reconciliation
against original text. There is no vote and no inserted correct intermediate answer.
Its planned 41 calls exceed V15's 30, so any observed improvement cannot isolate role
specialization from extra computation. See the V16 comparison plan in versions/.

Both preserve the same model parameters, full source, 180-second socket timeout and
cost guard. V16 deducts V15's final accounted spending before dispatch. Publication
does not authorize extra cases or change the experiment budget.

## How to inspect the evidence

- `versions/`: exact versioned code, embedded prompts, protocols, preparation checks,
  completed responses, and completed-call transport evidence. Raw requests and SSE
  traces are losslessly gzip-compressed; decompress to inspect full model input.
- `source/1251841-input.json`: exact common source input.
- `comparators/LW/`: adaptation declaration, outputs, validation and available inputs.
- `dependencies/`: selected imported local source helpers.
- `SNAPSHOT_MANIFEST.json`: byte provenance and explicit incomplete-run status.

Model source support and offline tests are not human legal gold. Final quality must
be checked against original text, counting errors and omissions together. No final
comparison score is invented here.

## Portability and exclusions

Frozen code and configuration retain their original absolute local paths and freeze
references. This is an inspectable evidence snapshot, not a portable one-command
execution package. Local runtime packages, model weights, secure credentials and
all historical transitive artifacts are not included. Do not execute a saved runner
without adapting paths in a new version and obtaining appropriate run authorization.

Completed calls were copied only after their receipts existed and each selected
file was unchanged across two reads. Active streams, mutable launch logs, browser
captures, credentials, bulk corpora and offline replay bulk traces were excluded.
All newly published content is English; original artifacts were not translated or
rewritten. Partial results remain partial even if the live experiment later finishes.
