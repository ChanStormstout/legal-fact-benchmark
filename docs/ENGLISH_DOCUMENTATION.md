# English Documentation and Evidence Preservation

Updated 2026-10-25 under the user's instruction to translate explanatory Chinese while preserving original experimental records.

## What changed

The root README is a short project entry with purpose, current evidence limits, workflow, navigation and safe local inspection. Maintained documentation, the experiment catalog's descriptive fields, research designs, implementation explanations, meeting scripts and report/navigation templates use English. Two existing PowerPoint decks have English speaker notes; all non-note archive entries, including visible slides and media, are unchanged.

The registered review can display an English explanation through `current_review.english_report`. Its original experiment/report selection is unchanged. The translation is explanatory material, not replacement evidence or a new run. Historical comparator proposals remain dated proposals; the ordinary baseline remains one direct LLM call unless additional mechanisms receive explicit approval.

## What remains in its original language

Original model prompts and replies, source quotations, annotations/adjudications, fixed query inputs, executed/frozen code copies, run receipts, failures, results and archived run reports retain their original bytes. This includes original Pro research conversations and embedded historical assessment dictionaries in legacy scripts. Rendering labels around those records are translated; record values are not rewritten.

Exact interface strings used to identify original browser messages, Unicode test fixtures, original authorization quotations and filename selectors also remain exact. Existing Chinese filenames and historical `-zh` paths remain identifiers so links and provenance addresses do not break. Their explanatory document contents may now be English. A Chinese filename therefore does not establish the language of its current content.

Versioned authored design/navigation documents translated in place are explicitly listed in the local migration verification record. Their new document hashes are distinct from the preserved historical design records. An old document hash is not asserted to match its translated explanation.

## Validation boundary

Validation covers Python syntax, JSON structure, documentation links, publication-manifest integrity and byte preservation of protected evidence. The repository-bridge checks exercise documentation/review packaging only. No model, API, GPU, training, annotation, experiment replay, commit or push was performed for this language cleanup. Report-generation scripts were not executed to overwrite old experiment results.

A local before/after inventory is retained under `.bridge/english-docs-20261025T062901Z/`. It is ignored operational bookkeeping, not a published experiment or an extra Chinese documentation edition. The verification record distinguishes intentional explanatory-file changes from protected evidence and records any discrepancy explicitly.

## Publication integration

The authorized documentation publication is based on remote revision `4292aa9e`, which already contains the V22 review. Its experiment selection, published evidence, original review prompt, and publication scope are retained. The English selected-report summary describes V22 rather than reverting the remote to the older local V20.9.2 selection. Unpublished implementation work in the original checkout is not included.
