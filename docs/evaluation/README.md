# RAPIDO report evaluation

Protocol version: **RAPIDO-EVAL-2.0**, 2026-10-27. This is the maintained evaluation
specification for subsequent development. It does not retroactively preregister
already observed results, change a frozen experiment, or authorize another model run.

The task is to answer the user's legal question from the **permitted source view**:
identify the relevant people, property, events and procedural stage; explain the
competing positions and their support; distinguish previous findings from current
legal analysis; and state the remaining limits. A correct, explained uncertainty can
be part of a good answer. A report consisting only of UNKNOWN cannot recover known
content.

The principal score is **important-content coverage, R**: the fraction of a frozen,
source-grounded list of important answer requirements that the report satisfies
correctly. It is accompanied by **source-support precision, P**, **serious errors**,
and **main-answer adequacy**. This combination distinguishes a complete but wrong
answer, a short answer that hides omissions, and a useful supported answer. The
dashboard's harmonic score H is auxiliary, not an official legal-quality metric or
a substitute for the component scores.

| Read | Purpose |
| --- | --- |
| [Protocol and formulas](PROTOCOL.md) | Task, units, numerators, denominators, missingness, comparisons and statistics |
| [Reference and annotation manual](ANNOTATION_MANUAL.md) | How GPT Web creates the source reference, grades anonymous reports, and records disagreements |
| [Metric rationale and related work](RATIONALE.md) | Why these measurements address observed failures; what the literature does and does not establish |
| [Data contract](DATA_CONTRACT.md) | Files, identities, hashes, status values, publication and leakage boundaries |
| [Improvement and decision rules](IMPROVEMENT_LOOP.md) | How to change the system in response to scores without optimizing for acceptance counts |
| [Machine-readable defaults](protocol.json) | The versioned defaults; a run must still freeze its own cases, views, models and budget |
| [Annotation prompts](prompts/) | Source-only reference construction and blind grading templates |
| [Current evidence](../../outputs/rapido-evaluation-framework-2026-10-27-v2/README.md) | Preserved development scores, new web-annotation status, and actual limitations |

**Reference status:** GPT Web annotations followed by explicit source adjudication
are **source-grounded model references**, not human gold, independent lawyer
validation, or the truth of the real-world dispute. Repeated model agreement does
not eliminate common errors. Unresolved annotation questions remain visible.

**Baseline boundary:** A0 is the permitted raw case materials, fixed legal materials
and question followed by **one ordinary LLM call**. Do not add retrieval, agents,
decomposition, review, self-check, revision, or a second call without the user's
approval. A0 is graded by semantic content, not C's internal JSON or citation format.
Older enhanced comparators retain their historical names and definitions.

**Evaluation boundary:** final delivered reports are the main endpoints. A candidate
report is a separate diagnostic endpoint; it cannot replace a failed delivery. A
score, internal ACCEPT, or successful program run alone does not prove the system
is legally correct, better than A0, or ready for use.
