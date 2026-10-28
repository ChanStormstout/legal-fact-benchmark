# V51: source planning, complete writing, and direct source editing

The completed ten-case development comparison shows higher average important-content coverage for F than for the ordinary one-call A0 baseline. It also includes a clear regression, unresolved labels, missing A0 assertion inventories, and unchanged edits. This is evidence of development improvement, not a demonstrated statistically significant advantage on independent disputes.

F produced ten reports; nine inherited a completed plan/draft chain. Case 236012 retained its old plan timeout without a rerun. Publication does not run a model, change the method, generate annotations, or alter the original experiment.

## Observed results

| Measure | A0 | F |
|---|---:|---:|
| Ten-case mean R | 57.8226–59.8746% | 70.1080–72.7137% |
| Ten-case mean H | Not observed: two A0 assertion inventories missing | 79.2550–82.3494 |
| Reports | 10 | 10 |
| Completed full chains | 10 | 9 |
| Logical method cost, ten cases | $0.02355802 | $0.11007232 |

R is the proportion of frozen important relations correctly addressed. P is the proportion of actual distinct substantive assertions supported by permitted sources. H is their harmonic mean, on a 0–100 scale. The method named P is separate from the metric P; both are labeled explicitly in the data.

The conservative difference in ten-case mean R is +10.2334 to+14.8911 percentage points. Eight cases have a definite positive R difference,1388066 has a definite negative difference, and 1489900 is unresolved in direction. The ranges reflect source-label ambiguity, not confidence intervals or significance tests. Cases are averaged equally; a longer reference does not automatically give its case more weight.

| Case | Important points | A0 correct | F correct | F minus A0, R percentage points |
|---|---:|---:|---:|---:|
| 1914817 | 59 | 31 to 32 / 59 | 42 to 45 / 59 | 16.95 to 23.73 |
| 406910 | 40 | 26 / 40 | 27 to 29 / 40 | 2.50 to 7.50 |
| 701211 | 74 | 38 / 74 | 50 to 52 / 74 | 16.22 to 18.92 |
| 152211 | 38 | 26 / 38 | 27 / 38 | 2.63 |
| 236012 | 46 | 22 to 24 / 46 | 38 to 40 / 46 | 30.43 to 39.13 |
| 1825635 | 47 | 17 to 18 / 47 | 32 / 47 | 29.79 to 31.91 |
| 1388066 | 40 | 29 to 30 / 40 | 20 to 22 / 40 | -25.00 to -17.50 |
| 89764 | 31 | 24 to 25 / 31 | 27 / 31 | 6.45 to 9.68 |
| 1230342 | 37 | 20 to 21 / 37 | 30 / 37 | 24.32 to 27.03 |
| 1489900 | 51 | 27 to 29 / 51 | 28 to 30 / 51 | -1.96 to 5.88 |

On the same eight cases with both observed H scores, A0 mean H is 65.9164–68.7056 and F is 81.7480–84.2729; the conservative difference is+13.0424 to+18.3565. Confirmed serious errors in those eight are 9 for A0 and 1 for F, with 21 and 13 additional unresolved-severity issues. These eight omit 1388066, the clear negative R case, and 406910; they are not a replacement for the full cohort. F has two confirmed serious errors in 1388066; the corresponding A0 inventory is missing. Do not compare incomplete A0 error counts against full F counts as if denominators were equal.

Mathematical missingness bounds for the full A0 H mean are 52.7331–71.4147 when the two unknown support rates may range from 0 to 1. F-minus-A0 bounds are 7.8403–29.6163. These are identification bounds, not observed scores, zero imputation, confidence intervals, a hypothesis test, or proof of independent superiority.

## Which component helped?

F is an actual source plan plus complete draft followed by one direct-source edit. In six cases the edit made no textual change:1914817,406910,701211,152211,89764,1230342. Their advantage over A0 already existed before the last editing call. The other four drafts changed; three have measurable coverage gains over their actual P drafts, while 1825635 still lacks the P coverage axis. No benefit is assigned to a proposed but mechanically rejected patch. See [component pairs](component-pairs.json).

The full F cost is approximately 4.672 times A0. The new ten editing calls cost$0.04149538; the actual inherited P cost is charged to F but not billed again. Across all compared branches there are 68 unique requests, with conservative cost$0.22147528: known usage$0.20238143 plus two unknown-usage reserves$0.01909385. This is a defined batch, not lifetime research spending.

## Inspect the complete evidence

- [All 50 endpoint slots, actual reports, errors and costs](comparison.html)
- [Full CSV](comparison.csv), [portable JSON](experiment-data.json), [original hashes and selected records](SNAPSHOT_MANIFEST.json)
- [Metrics and annotation validity](EVALUATION.md)
- [Executed method and ordinary-baseline boundary](METHOD.md)
- [Positive and negative case studies](CASE_STUDIES.md)
- [Missingness and descriptive bounds](descriptive-label-and-missingness-bounds.json), [same-eight summary](paired-eight-observed-summary.json)
- [Path mapping and portability](PORTABILITY.md)

## Limits and publication scope

These ten cases were exposed during method development. Four helped design F. The reused prefixes and new edits were served at different times; the Qwen/Qwen 3.8-Flash alias has no confirmed immutable weight revision. A0 has one ordinary call with the same allowed sources/question and no retrieval, planning, decomposition, review or revision. C0 is a separately named writing-instruction control, never a strengthened A0.

The evaluation uses source-grounded model references with preserved raw annotations and parent adjudication. It is not human or lawyer gold, and the parent was not fully method-blind. Two references have weaker design-review provenance, detailed in EVALUATION.md. Same-text endpoints reuse consistent units and labels. There is no confirmatory significance test or independent generalization result.

Only CASE plus the existing 23 LAW sources were supplied. This experiment does not validate HISTORY retrieval, executable legal rules, investigation planning, or lawyer approval, and is not full RAPIDO completion. No corpus-on/off control supports attributing the result specifically to RAG.

This snapshot includes selected completed-development code, allowed inputs, reports, requests/responses/receipts, model annotations and source-adjudicated labels. It excludes browser captures, account/chat URLs, credentials, model weights, third-party PDFs, raw SSE/reasoning streams, and all ongoing independent-source preparation. Original bytes and failures remain unchanged locally. The public navigation files are new derived views, not replacement experiment records.
