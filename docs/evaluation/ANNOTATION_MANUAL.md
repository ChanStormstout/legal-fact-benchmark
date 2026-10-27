# Source reference and blind annotation manual

This workflow uses the user's existing GPT Web account **only as an annotator**.
It never supplies correct intermediate records, ACCEPT decisions, rules or repaired
model answers to the scored pipeline. No human annotators or legal experts are
assumed available. The deliverable is a source-grounded **model reference**, with
explicit uncertainty and provenance.

For this development review the user additionally authorized a separate Codex side
chat to try annotation. Its source-before-output phase log and independent reference
are preserved as **secondary model evidence**, with the provider named explicitly.
It is not relabeled as GPT Web data or a second grading pass under the Web reference.
Different reference items and assertion inventories cannot be pooled, voted together,
or used to calculate inter-annotator kappa without a separately justified alignment.

## 1. Evidence hierarchy and source view

The reference authority is the permitted original source text, not an internal
checker, a previous model summary, an old score, or agreement between models. Preserve
the original file/hash, source ID and locator. Store the exact permitted text and
Unicode-character offsets of supporting quotations. A cleanly parsed quotation
establishes what text was cited; entailment remains a semantic annotation.

Describe the task's cutoff and visibility. If a target outcome/reason is hidden,
exclude its repetitions, same-dispute appeals and downstream summaries. A public
webpage containing the full judgment is still prohibited if the experiment hides
that portion. Do not ask annotators to browse it. Original exhibits are not present
merely because a judgment describes them. A prior finding is an attributed judicial
statement, not an independently verified fact about the underlying event.

The reference has two layers. **Required content** is derived from the common
question, current record and allowed law, before method output is visible. **Support
assessment** also checks any optional assertions/analogies against the allowed
historical source view. When methods read different history, the grader receives the
pure-source union of their registered historical reading, without assessments or
method identities. It does not add history-dependent required items after seeing
which method used them. Access differences remain disclosed in the experiment.

## 2. Construct and freeze the reference before blind scoring

1. Build a source-only packet: case/group ID, question, visibility boundary, exact
   CASE/LAW texts and source manifest. No output, method name, score, expected error,
   intermediate reasoning or checker decisions are included.
2. In a fresh GPT Web conversation, request important answer requirements, acceptable
   conditional/open answers, mandatory bindings and exact source evidence. Use the
   [reference prompt](prompts/source-reference.md). Record the displayed model and
   thinking setting; if the web interface does not expose a fixed model revision,
   mark it unavailable. Explicitly disallow browsing and other-chat/case memory.
3. Save the complete raw reply, URL, timestamp, prompt hash, source-view hash and
   attachment hashes. A loading/error placeholder or truncated JSON is not a label.
   A first "cannot load this reply" display is a retrieval/rendering observation,
   **not evidence that generation failed**. After generation has ended, verify the
   conversation URL, reload up to three times with a fresh ready-state check, and
   inspect/copy existing code blocks. Check existing message versions if relevant.
   Preserve the initial state and any subsequently recovered original reply. A
   copied error string is not JSON. Follow the existing job before submitting
   another; do not regenerate repeatedly until a preferred reference appears.
4. Have a second fresh source-only session review the proposed criteria against the
   same sources, without system outputs. Ask about unsupported law, wrong stage,
   missing material counterarguments, overlap and overemphasis on incidental details.
   This is a reference audit, not an independent human reference. If unavailable,
   mark the reference single-pass/provisional rather than invent agreement.
5. Adjudicate every proposed change against permitted spans. Save original proposal,
   audit, item mapping and adjudication. Reject reference requirements that need hidden
   information or unavailable law. Keep genuinely ambiguous criteria as explicit
   alternatives or unresolved reference issues. Freeze the final reference and hash
   before the anonymous reports are supplied to graders.

For prospective evaluation this also happens before system generation, with reference
storage isolated from the runner. In the present exposed development study, the
project has already seen the outputs; source-only web blinding is useful but does not
make the study preregistered or independent. Label it retrospective throughout.

## 3. Reference item design

Each item records `id`, `category`, `criterion`, `mandatory_constraints`,
`importance_reason`, `expected_state` and one or more `{source_id, quote}` witnesses.
Constraints identify relations, not opaque internal IDs: whose claim, concerning
which property/transaction, attributed to which court and stage, with what polarity
and qualification. Sources can support a *scoped legal interpretation* without
supporting an absolute legal holding.

Examples from the permitted 1251841 view:

* A required prior-finding item can say that the two earlier courts treated the
  claimant as subrogated to the bank, with correct attribution. It need not prove
  the present court should reach the same legal conclusion.
* The prior High Court's dismissal and the target court's withheld disposition
  are different objects. The former is answerable; the latter is not. A report
  reversing the former cannot earn its point by mentioning the latter as unknown.
* The lease predates the 1929 statutory provision. That temporal issue matters;
  a generic reference to a present statutory power does not resolve it.
* A defendant's assertion that the lease survives the auction must remain an
  assertion unless the cited judicial stage actually accepts it. Its importance
  does not require believing the assertion.

Use binary criteria. If a criterion combines independently scoreable relations,
split it before scoring. Necessary actor/stage/condition bindings stay attached to
their relation. Do not require a literal current-court name absent from the text.
Tag controlling objections and OPEN items so their diagnostic denominators are fixed.

## 4. Anonymous report preparation

Copy the **actual** final candidate/delivered/plain-call bytes into separate files.
Store raw SHA-256 hashes. Replace method labels only in a separate envelope, not
inside the report. If a text itself reveals technical style, record imperfect
blinding; do not rewrite it into a better answer. Use random blind IDs and randomized
presentation order with a saved seed. Keep the method/endpoint mapping in a separate
private file, never in an annotator packet.

Include the question, frozen reference and source originals. Exclude request logs,
internal derivations, draft history, ACCEPT records, old grades and source-adjudicator
preferences. Do not tell graders which reports are candidate/delivery versions.
A source-review packet is data, not an instruction source. Treat any instructions
inside report/source text as untrusted text.

## 5. Grade all dimensions, with evidence

Use the [blind grading prompt](prompts/blind-grading.md). For each report:

* Match every reference item once: CORRECT, NOT_SATISFIED, or
  ANNOTATION_UNRESOLVED. Give report quotations, source evidence and a concise reason.
  Absence can be recorded without inventing an output quote.
* Enumerate **all distinct substantive assertions**, including wrong or extra law,
  and label SUPPORTED, CONTRADICTED, UNSUPPORTED, or ANNOTATION_UNRESOLVED. Preserve
  necessary participants, attribution, stage, conditions and negation. Tag which
  report spans the inventory covers. If enumeration is incomplete, leave precision
  unscoreable; do not divide a selected error list by an assumed total.
* Record all serious-error events, their materiality, source basis and whether
  severity itself is unresolved. Report important omissions separately.
* Assign the defined main-answer category and explanation. No method preference,
  free-form overall grade, or citation-count bonus is requested.

A second fresh grading session uses the same frozen reference and sources, a new
report order, and no first-pass scores. Save both raw results. If resources or access
permit only one pass, publish it as single-pass with source adjudication; do not claim
inter-annotator reliability. Do not repeat scoring merely because a result is unwanted.

## 6. Validate identities before accepting labels

Program checks require case ID, blind ID, exact report hash, reference hash,
source-view hash and complete reference-item coverage. Evidence source IDs and exact
quotes must exist in the specified view; report quotes must occur in that report.
Check duplicates, missing items, invalid enums and incomplete JSON. Raw annotation
bytes are immutable. A malformed reply is retained as invalid/pending; never silently
fill absent labels with CORRECT, zero, ACCEPT or a previous version's label.

Program checks cannot verify paraphrase entailment, legal materiality or whether an
assertion inventory is truly complete. Those remain explicit semantic review tasks.
Do not advertise format acceptance as ground-truth validation.

## 7. Source adjudication and disagreement

For every disputed criterion/assertion, and every severe/unsupported finding, record
the web labels, exact output and source spans, the applied decision rule, final label
or unresolved status, assessor identity, date and a short reason. Source-adjudication
by Codex remains model adjudication, not human expert review. Preserve the raw web
judgment even when changed. Do not use majority vote as proof of legal truth.

Audit the full assertion inventory against each paragraph to detect missed assertions
and false passes. Adding an omitted assertion is a documented adjudication with its
span, not an invisible denominator change. If one report receives additional review,
apply the same review policy to all reports in the cohort. A flawed reference is
versioned and all methods regraded. An error particular to an output does not create
a new mandatory content item after unblinding.

Report coverage-label agreement and confusion counts before adjudication, score
differences before/after adjudication, and unresolved counts. For unmatched assertion
inventories, publish alignment uncertainty instead of a misleading kappa. Agreement
within one model family is not external accuracy. If reference uncertainty could
reverse the conclusion, report that the comparison is undecided.

Keep the logic and attribution in the report when adjudicating. “Only if” expresses
necessity, not equivalence. “Not the surviving issue” does not establish “never
raised.” A correct narrower paraphrase must not conceal an unsupported court name
or procedural act present in the actual sentence. A supported local assertion may
remain in P even when another sentence contradicts the complete relation required
for R; this distinction must be recorded rather than silently changing either
denominator. The current example preserves all seven such adjudication changes.

## 8. Annotation access, missing work and contamination

Reuse an old annotation only if case, question, source view, reference version,
report hash, endpoint and grading contract match. Otherwise it is historical evidence,
not a label for the new report. An old V6 web score cannot label V38. Source-only
reference contents may be reused only when their own source/question/contract matches
and that reuse is recorded. Every existing final report in the registered evaluation
manifest needs annotation; technical no-output slots need a failure record instead.

Track NOT_SUBMITTED, SUBMITTED, IN_PROGRESS, RECEIVED, INVALID, UNREADABLE,
SOURCE_ADJUDICATED and UNRESOLVED separately. A UI send action must have a visible
message/job receipt before being called submitted. If a reply cannot be loaded,
preserve its URL and status and leave scores null. Do not turn a delivery obstacle
into a method-quality failure. Annotations for old twelve-case experiments remain
an archive unless that cohort is explicitly being re-evaluated with compatible views.

Keep evaluator-only answers and method mappings outside runner inputs. Freeze this
boundary for new test disputes. Development feedback can guide a new method version,
but those cases then remain exposed. Freeze the next evaluation before seeing its
outputs; never tune reference weights to make C win.
