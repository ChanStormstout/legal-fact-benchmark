# Timeout regression diagnosis and staged repair result

## Finding

The strongest evidence points to the hosted decoding constraints introduced in
V12, rather than a change to the judgment or model parameters. V11 returned its
first reading in 51.63 seconds. V12 added 792 maxItems constraints to that request's
hosted schema; its original attempt and two explicitly authorized retries all
timed out before an HTTP response at the unchanged 180-second socket timeout.

V13 kept the V12 prompt, sources and generation parameters identical, removing
only mathematically redundant maxItems=N constraints on unique arrays over N
distinct allowed strings from the hosted decoder. Its first two calls completed,
the first in 41.48 seconds. Its third call reproduced the old L111 reference loop
and was stopped by the unchanged streaming guard after 16.14 seconds.

V14 retains small unit-local assertion_source_ids bounds but omits the redundant
global-context bounds from the hosted schema. The first request has 96 maxItems
entries instead of V12's 816 total entries (which included 24 pre-existing bounds).
Prompt and local validation retain the complete original V12 contract. Source ID
enums, uniqueness declarations and streaming loop protection are retained.

This isolates a concrete implementation regression and an effective workaround
on the observed requests. Provider internal compilation or queueing traces are
unavailable. These sequential observations do not prove a particular grammar
compiler algorithm, eliminate time-varying service conditions, or establish that
every possible schema will respond within 180 seconds.

## Why the previous fix caused a new problem

The V11 failure repeated one source ID inside an array. V12 addressed repetition
by adding a finite-set bound to every source array. Logically, this is reasonable:
a set over N unique identifiers contains at most N items. Operationally, the rule
was expanded hundreds of times in a large self-contained hosted schema, including
global lists of 139 source choices. Correct JSON Schema and valid local checks did
not establish acceptable hosted-decoder latency. The prior offline acceptance did
not measure that service behavior. This was an unvalidated implementation change,
not evidence that the source document had become too long or the model suddenly
could not understand it.

Removing every hosted bound in V13 restored responses but also exposed the original
reference loop. V14 therefore keeps the small primary-citation bounds where the
observed loop occurred. The affected unit U0025 has two possible primary citations;
both V14 readers emitted L110 and L111 exactly once and then continued.

## Actual staged experiment

Complete judgment 1251841 was supplied on every request. The gate covered the first
two existing source groups, each with a primary and a blind independent reading.
No reference answers or corrected intermediate interpretations were supplied. No
reconciliation, final semantic review, full C report or further case was run.

| Call | Status | Seconds | Reported usage cost |
| --- | --- | ---: | ---: |
| reading-000 | OK, finish_reason=stop | 41.92 | $0.00553969 |
| independent-000 | OK, finish_reason=stop | 43.01 | $0.00569755 |
| reading-001 | OK, finish_reason=stop | 75.53 | $0.00456597 |
| independent-001 | OK, finish_reason=stop | 68.65 | $0.00467183 |

All four outputs parsed and passed both local semantic-schema and hosted-schema
validation. There were zero ID-set canonicalization operations, no timeout and no
repeated-reference interruption. Total elapsed time was 232.08 seconds. The gate
completed and the process exited; no other cases were started. Structural validity
is not a semantic acceptance.

Evidence: [summary](run-v1/summary.json), [transport receipts](run-v1/transport/1251841/V14/calls/),
[first group](run-v1/case/batches/000.json), [second group](run-v1/case/batches/001.json),
and [preflight](preflight.json). V13's failed loop remains in the adjacent
`full-judgment-source-decoder-v13-2026-10-26-v1` directory.

## Source-quality limits

Each first-group reader produced only one headnote record and classified all 23
preceding units as NON_SUBSTANTIVE, including metadata that the prompt requested.
Each second-group reader produced eight records. The original citation loop is
absent, but content classification and attribution still have errors:

- The primary reader labels the judgment-start marker as a PROCEDURE record.
- Counsel representation is labeled LEGAL_PROPOSITION rather than metadata.
- U0024's note describes a prior-case headnote while its case_context says CURRENT_CASE.
- The independent U0025 record cites L120 for Civil Appeal No. 73 of 1950, while that
  procedural history appears at L118 and L120 identifies appellant counsel.
- Long compound records combine distinct facts or legal conditions. Correctly
  finishing such a record is not proof that all relationships are properly separated.

These are preliminary source-based observations, not independent gold annotations
or whole-document scores. They justify withholding expansion and quality claims.
The result establishes recovery of the tested transport/loop behavior, not that
source extraction is now reliable or that C surpasses the comparator.

## Accounting and preservation

V13 reported $0.01127249 usage and retained a $0.04980736 reserve for its interrupted
third call. V14 reported $0.02047504 with no unknown usage. This turn therefore used
or reserved $0.08155489, of which $0.03174753 is usage-reported, not invoice-verified.
Remaining original six-case authorization is $5.48903234. Unknown reserves remain
included once; they are not represented as confirmed charges.

All 2,843 protected predecessor files and 1,024 frozen file entries verified
unchanged after the run. The cancelled long-wait experiment was never launched.
The socket timeout remained 180 seconds. There was no training, main-thread change,
default-entry switch, git commit or push.
