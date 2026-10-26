# Frozen whole-document extraction comparison

## Scope and cohort

Compare V9, the disclosed local LatentWeaver same-Qwen adaptation, and V10 on the
same complete rendered judgments. This does not compare the whole RAPIDO system
against A0. A0 remains a plain one-call baseline and is not modified or run here.

The two fixed anchors are 1251841 and 1252014. Four additional documents are selected
by a frozen hash ordering from complete locally available sources outside the prior
twelve-case cohort, with one document per recorded local dispute group: 696952,
1997407, 45759 and 1801104. Selection does not use experimental outcomes. Admission
and exclusion records are in `private/preparation/cohort.json`.

The extra four were already exposed in source screening/design work. They are not
sealed tests, and prompt-development exposure has not been ruled out. Local dispute
grouping is provisional rather than an exhaustive litigation-registry search.

## Shared inputs, model and execution

Each arm receives the same original source content, source IDs and full outcome.
The experiment measures source extraction, not pre-judgment prediction. No hidden
law, answer key or corrected intermediate output enters any model request. Each arm
uses Together `Qwen/Qwen3.5-9B`, seed 20261001, temperature 0, top_p 1, reasoning off,
streaming, and the inherited 65,536-token output / 262,144-token context configuration.
Hosted weight revisions and exact hosted tokenizer/template are not immutable here.

V9 keeps its original reader and review implementation. The comparator preserves its
existing native prompts/ontology/builders/validators plus the previously disclosed
local guidance and candidate-schema adapter. The only new comparator behavior is
removing our arbitrary 6,000-word refusal and using full-document input. It therefore
does not measure the upstream original large model or native overlapping-chunk schedule.

The planned logical calls are V9 204, comparator at most 24, V10 258, total at most
486. A comparator with no semantic-admission items may use fewer calls. Calls run
serially, with arm order rotated by case before any result is seen. All calls,
technical failures and at most one identical technical retry are charged. No model
format repair, semantic retry, case replacement or tuning between cases is permitted.

The user-approved new fee cap must cover the scope actually run. A conservative
unknown-usage reservation is not an invoice. Existing reserves remain in prior
accounting. A newly unknown usage event pauses dispatch unless a new scoped approval
expressly allows reserve-and-isolate continuation. Service refusal, depleted fee
authorization or actual context overflow is preserved as a failure/blocker.

Every arm receives the same generous aggregate resource ceiling derived from the
largest full plan plus technical retry allowance. This is not an equal-realized-cost
comparison: V10 intentionally uses more calls. Actual cost must be reported alongside
quality. A future matched-cost study would be needed for an efficiency claim.

## Reference and annotation protocol

Prepare important source relationships from the full original without method output.
A reference unit includes its speaker, proposition/event participants, assertion
status, current-versus-quoted case, relevant time/procedure/property, attached
conditions or exceptions, and exact source locators. A long judgment need not be
reduced to one unit per printed line. Importance concerns material source meaning,
not whether an item benefits a particular method.

References and annotations remain source-grounded model references unless an actual
human review is separately documented. They are not human gold or legal advice.
Freeze reference files before inspecting new method outputs when possible. If this
cannot be achieved, mark the evaluation retrospective and retain that limitation.

`evaluate.py export` creates anonymous complete-case artifacts and keeps the method
mapping in a separate private file. Do not send that mapping, internal reviews or
prior error diagnoses to the annotator. Output-format blinding is imperfect and must
be disclosed. A source-based adjudicator checks disagreements and keeps both initial
and adjudicated labels with source, reference and artifact hashes.

## Outcomes and scoring

Primary descriptive outcomes are (1) important-relationship recovery and (2) serious
source errors. A relationship is recovered only when the required attribution,
participants, proposition, status and material qualifications are all correctly
present somewhere in the delivered extraction. A bare quotation or vague unresolved
placeholder cannot recover a determinate relationship. Correctly preserving a source's
own uncertainty is valid. Do not demand legal certainty where the original is unresolved.

Serious errors include changing the relevant speaker or court, reversing debtor/
creditor or transfer roles, converting an issue or rejected argument to an adopted
holding, treating execution as binding force, and dropping a condition that changes
the extracted legal proposition. Minor transcription/format defects are separate.
Use exact source evidence; do not count a disagreement about external law as a source
extraction error without checking what the judgment actually states.

Whole-document success requires all predeclared important relationships recovered
and no serious error. Technical failures count as zero delivered recovery and zero
whole-document success; their semantic-error scores remain null. Unrun or unlabelled
cases are pending, not fabricated zeros. Report all six slots per arm and withhold a
complete-cohort mean while any required result or annotation is pending.

Secondary diagnostics: wrong attribution/binding, missed qualifications, false
acceptance, unresolved supported content, duplicates, review-introduced errors,
corrected versus unchanged revisions, source alignment, output completeness, calls,
tokens, elapsed time and cost. Coverage claims made by the model are not quality labels.

Use paired per-document differences, with each provisional independent dispute
group receiving equal weight. Six exposed documents do not establish generalization
or statistical superiority. Do not equate a higher record count with better recovery,
or silently relabel a technical failure as an invalid case.

## Decision and stops

Continue development if V10 improves material relationship recovery on the paired
documents without hiding regressions or relying on more abstention. If it primarily
increases output volume, cost or erroneous acceptance, retain the negative result and
reconsider the mechanism. Any added field or check must explain a measured source
failure; it is not a research contribution by default.

No per-field intervention, planted correct answer or repeated single-case adjustment
belongs to this run. Necessary pre-run interface review uses the complete cached
document and preserved outputs, not synthetic legal micro-tests. A substantive method
change after freezing requires a separate version; do not pool its scores into this
cohort. Full RAPIDO/A0 experiments require a later explicit scope and fee approval.
