# Source-only reference prompt template

Replace placeholders from the frozen source manifest. Attach only the permitted
original material packet. Do not include experiment outputs or known error examples.

```text
You are constructing source-grounded model reference annotations, not an experimental
answer or legal certification. No system outputs or grades are supplied. The task is
to answer the specified legal question from the permitted record, explaining material
relationships, competing arguments, prior findings, legal/procedural limits and
justified uncertainty.

Case: {case_id}. Source-view SHA-256: {source_view_sha256}.
Read the entire attached source packet, its question and scope. Use only its original
CASE/LAW texts. No external lookup, remembered case outcome, saved memories or other
chats. A party allegation is not an established fact; a prior finding is not the
present court's endorsement. Respect all hidden-information and time boundaries.

Construct the minimum important answer requirements. Select each because its omission
would materially weaken/change the requested analysis, not to reward incidental
dates or long answers. Each criterion is one assessable relation/conclusion with
necessary actor, property, attribution, time/stage, polarity and conditions. Merge
duplicates. Do not force an item quota. Give full-credit criteria and exact source
IDs/quotes. Include justified open answers without requiring hidden information.
Do not require literal wording, JSON formatting, or a current-court name absent from
the permitted record. A contradictory or wrongly bound answer cannot earn that
relation's point. Keep legitimately unavailable questions separate.

Return complete JSON with case_id, source_view_sha256, annotation_role
SOURCE_ONLY_REFERENCE, reading_complete, question_interpretation,
allowed_answer_boundary; items [{id, category, criterion, mandatory_constraints,
importance_reason, expected_state, evidence:[{source_id,quote}]}];
known_critical_errors_to_check; unavailable_or_forbidden; reference_uncertainties;
reference_limitations. Use short exact evidence, not hidden chain of thought.
If anything cannot be read, set reading_complete:false and identify it.
```

## Source-only audit prompt

```text
Audit this proposed reference against the complete permitted original source packet.
No system report or score is supplied. Check source support, required attribution and
bindings, legal/temporal scope, hidden-information boundaries, missing material
objections, duplicate criteria and incidental-detail overemphasis. Do not browse or
use case memory/other chats. Do not optimize for any method. Return item-addressed
KEEP/CHANGE/MERGE/REMOVE proposals, any essential missing criterion, exact source
witnesses, reference uncertainty, and reading_complete. A proposed change is not an
automatic reference edit; it will receive explicit source adjudication.
```
