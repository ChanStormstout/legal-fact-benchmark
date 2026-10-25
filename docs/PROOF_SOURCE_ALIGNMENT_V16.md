# V16: scoped acceptance and reversible source-layout recovery

Judgment-reasoning reconstruction continues. Four V15 cases receive cache regression
only. The remaining six DEV disputes follow the saved queue; each request selects the
first existing dependency candidate by stable ID, including OPEN_TEXT. Sources, P,
rule meaning, and grouping remain unchanged. No local model calls, training,
TEST/SEALED access, or publication.

## Quotation alignment

`quote_locator_v16.py` first applies exact reversible matching. It may join a letter-
internal hyphen plus whitespace only when the full word also occurs in the permitted
document and neither broken fragment occurs independently. It returns original/normalized
text, a character-position map, and explicit edits. Multiple matches stay ambiguous.
Non-layout word changes, omitted negation, nulls, cross-document references, and wrong
addresses are not repaired. Rule quotation-display corrections are separate revision
records, not edits to old rules. The policy intentionally does not solve all OCR errors
or approve meaning.

## Four review scopes

Review records share addresses and explicitly specify ALIGNMENT, BINDING(role),
USE(one-based use number), or WHOLE_PREMISE. Old unscoped records remain whole-item;
a whole-item REJECT grants no local acceptance. Conflicting/duplicate scopes stay
unresolved. Whole-premise claims state use dependencies. Required execution roles
come from fixed rules and cannot be removed by the model.

Code separately records conditional premise judgments, binding checks, use checks,
dependency-propagated execution states, actual reviewer acceptance, and formal approval.
Bad binding does not delete independent evidence/judgments, but the rule still requires
valid binding. Negation applies only to the fixed proposition; FALSE does not globally
bypass object requirements. Partial/background/usable evidence cannot generate a whole
premise.

Model-assisted review may accept a narrow court assessment while rejecting entity
correspondence. This is not legal approval. OPEN_TEXT remains unexecuted while allowing
source-grounded external court assessments/conditional records to be displayed; it is
not forced into AND.

## Actual entry

`scripts/proof_source_alignment_v16.py prepare|freeze|import|run` saves complete tasks
and materials. `scripts/check_semantic_v16.py` independently loads frozen sources/contracts
without importing proposal/reference generators. Technical failure is null with dependent
steps skipped. Cache regression, repair effects, new proposals, and review costs are
reported separately.

Twenty-five engineering tests include fifteen V16 and ten V15 regressions; four-case
caches replay through a real independent process. These do not validate legal semantics.
Central source review after six cases informs development investment, not estimates
of generalization or legal certification.
