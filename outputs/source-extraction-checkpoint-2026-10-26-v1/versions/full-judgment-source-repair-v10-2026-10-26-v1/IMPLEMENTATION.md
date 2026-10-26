# Implementation and review

## Observations motivating the change

The preserved V9 complete-judgment run returned 24 complete Qwen responses. It still
misread an open issue as an affirmative position, inverted a mortgage role, failed
to preserve some time/amount/condition relationships, and left unchanged replacement
requests. Many batch candidates described passages outside their assigned focus.
These observations do not establish that every error has one cause. They do show
that valid JSON, available source text and repeated agreement are insufficient.

## Actual computation

1. `prepare.py` takes the complete cached judgment region from the court heading to
   the start of website-related tags. It retains headnotes, reasoning and disposition.
   It excludes website controls, not selected unfavorable reasoning. Existing anchor
   source maps must match byte-for-byte. Complete rendering is not a certified court
   copy, a full litigation record or a pre-judgment prediction setting.
2. `prepare_units` joins likely wrapped lines without rewriting them. Every original
   source entry has one owner unit. Owner units have stable source IDs; mechanical
   punctuation boundaries are not asserted to be gold sentence boundaries. A reader
   may cite continuation/context elsewhere while owning its assertion locally.
3. Primary and independent-reader requests are constructed before either response.
   Both receive the same full original and owner groups. The second reader receives
   no primary notes, candidate IDs, labels or reviews. It is the same Qwen model, so
   its errors can remain correlated. Role prompts do not establish independence of
   knowledge or improve accuracy by themselves.
4. Model-authored records distinguish speaker, participant roles and source-backed
   names; event and statement time; court and procedure; question/allegation/denial/
   finding; positive/negative/mixed embedded propositions; property and qualifications.
   A denial of P is not encoded as a denial of not-P. Genuine nested negation remains
   expressible. No string rule decides legal truth or resolves a pronoun.
5. Structural checks enforce source ownership and declared references. Invalid
   candidates are quarantined with their raw responses; they do not become accepted
   because another model agrees. The final source-coverage pass can identify content
   missing from the surviving candidates.
6. Reconciliation handles each primary target exactly once. Target groups comprise
   three consecutive reading batches, with the complete original in every request.
   It includes the relevant independent reading and observations sharing assertion
   sources. All groups use one immutable initial snapshot, so the program does not
   feed earlier reconciliation decisions into later groups as new truth.
7. KEEP, REPLACE, WITHDRAW and UNRESOLVED have separate contracts. A replacement must
   name the mistaken aspect, cite sources and contain a complete new record. An
   unchanged replacement is explicitly recorded, never counted as improvement.
   Original records, retirements, additions, exact duplicate aliases and snapshot
   hashes remain inspectable. No fuzzy semantic merging occurs.
8. A final pass reviews every current record and every source unit against the full
   original. It sees content but no earlier verdict or rationale, and cannot edit.
   Its SUPPORTED result is a model source assessment, not independent legal approval.
   A final unresolved or rejected record stays so; no extra pass forces acceptance.
9. Whole-document output retains sources, records, coverage gaps, retired versions,
   quarantined candidates and actual call evidence. Downstream rule execution and
   report generation are disabled in this extraction experiment.

## Data contracts and ownership

`owner_unit_id` identifies where an assertion is made. `primary_source_ids` must
belong to that unit. `source_ids` can include the surrounding context needed to
resolve an antecedent or condition. Each interpreted witness has `value` and source
IDs. An entity receiving land and the speaker alleging that transfer occupy different
fields. Null means unresolved identification, not proof that the person does not exist.

Program-owned record IDs and hashes bind a review to the exact proposed content.
The model selects existing target IDs; it does not mint them. Model-assessed fields
are never filled with source-derived correct answers by the runner. The source-only
reference annotations and prior diagnostic labels are not model inputs.

The input serializer shares identical witness objects and source-ID lists in lookup
tables. It verifies exact expansion back to the original candidate collections.
This avoids repeating a court/date/source set in every field. Tables are solely an
input encoding; they do not accept or reject an interpretation. New model output
still uses original source IDs and the same typed record contract.

## Necessary limits versus arbitrary exclusions

Removed: the local comparator's 6,000-word refusal. Kept: the configured model context
and output capacity, the user's approved fee scope, and transport guards for missing
termination, whitespace loops and repeated output. These guards preserve partial
responses and failure reasons. They never manufacture a completed JSON object.

The 2,400-character reading group is a work assignment, not an input cutoff. An
oversized indivisible source unit is retained whole. All original sources remain in
each V10 request. Likewise, review target groups partition work; they do not discard
records or stop the document after a set number of groups.

The historical transport uses a 180-second network read timeout and a 2,400-second
call watchdog, alongside content-progress guards. These are still disclosed technical
failure conditions, not semantic failures. We have not proved the origin of earlier
service timeouts. The shared aggregate ceilings cover the largest planned complete
case plus one identical technical retry per call; no stage receives a small bespoke
token cap. Format or semantic failures do not trigger iterative prompt changes.

## Whole-document offline review

The initial monolithic reconciliation request, using the complete cached V9 records,
was approximately 230,577 local tokens before reserving output. That exposed a real
context-capacity risk before any paid run. Lossless dictionaries alone reduced it to
about 140,018 tokens. Grouping review targets then reduced the largest reconciliation
request in this complete-case replay to approximately 60,934 tokens, while retaining
the full original in each request. Small prompt edits can change these estimates;
the final exact measurements are in the review artifacts.

All six complete inputs were checked through actual first-call builders. The longest
document contains approximately 12,890 source words; the local comparator's initial
requests are about 33,500 tokens. A 6,000-word exclusion therefore had no demonstrated
capacity justification for those calls. Later comparator inputs depend on future
model output and have not yet been experimentally verified for the long documents.

The cached-record replay never inserts SUPPORTED or ACCEPT. It mechanically projects
old content, leaves unknown fields unknown and returns UNRESOLVED reviews. The same
cached records stand in for both readers in this engineering replay; this is explicitly
not evidence of independent reading or extraction improvement. It does not establish
that Qwen will understand the table format, produce correct bindings, avoid duplicates
or fit all future outputs into the advertised context.

## Remaining risks

- The same model can repeat the same source error across different roles.
- Mechanical ownership can be imperfect at quotes, abbreviations or wrapped headings.
- Review is a complete grouped pass, not joint optimization over every candidate in
  one model call. Cross-group consistency remains a measured risk.
- Structural source references can be valid while the interpretation is wrong.
- This is not a complete entity-resolution system, cross-document ontology alignment,
  or proof of legal applicability. No new legal rule is inferred from a judgment.
- More detailed records may cost more and still omit important relationships.
- Long-document comparator and V10 model behavior remain untested. Server weight and
  tokenizer immutability are not confirmed; context overflow must be reported, not
  silently repaired by truncating sources.

## Research connection, without overstating transfer

The design borrows role-explicit extraction from [Code4Struct](https://aclanthology.org/2023.acl-long.202/),
source-relative status distinctions from [FactBank documentation](https://catalog.ldc.upenn.edu/docs/LDC2009T23/readme.pdf),
and unconditioned checking from [Chain-of-Verification](https://aclanthology.org/2024.findings-acl.212/).
These works do not establish improvement for this legal corpus or Qwen 9B. They
motivate mechanisms to test. The [self-correction survey](https://aclanthology.org/2024.tacl-1.78/)
is a reason to preserve failures and distinguish new evidence from repeated agreement.
