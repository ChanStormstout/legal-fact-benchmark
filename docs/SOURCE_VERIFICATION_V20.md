# V20: source verification and complete-answer implementation boundaries

This version implements the [source-semantic verification plan](SOURCE_GROUNDED_VERIFICATION_PLAN.md). The [V20.1 continuation report](../outputs/proof-source-verification-v20/continuation-01/report-zh.md) and [protocol](../outputs/proof-source-verification-v20/continuation-01/freeze/protocol.json) establish the old generation batch's status. The [original V20 report](../outputs/proof-source-verification-v20/report-zh.md) preserves its pause reason. Connected interfaces do not mean every stage ran or legal analysis improved.

V20.2 later completed ten authorized code repairs and cache engineering acceptance; see its [implementation boundaries](SOURCE_VERIFICATION_V20_2.md) and [five-case report](../outputs/proof-source-verification-repair-v20-2/report-zh.md). The original batch remains paused, with no new training/final answers. The V20 research protocol below is historical; repairs did not change its sources, rules, budgets, or split.

## Original sources to final answers

P is the fixed local LLM's initial structured proposal. Q is the same model's source review/local supplementation after reading all permitted sources, fixed rules, and original P. P remains unchanged. Q has separate evidence/object/use/premise-judgment records, distinct addresses, and producer versions. Claiming verification does not grant research or legal approval.

Shared candidates represent four reviewable claims: evidence attribution, object binding, concrete evidence use, and whole-premise basis. Classifiers predict source support for the exact claim as SUPPORTED, UNSUPPORTED, or UNRESOLVED. Supporting “evidence opposes p” does not establish p; rejecting a premise basis does not make that premise FALSE.

| Stage | Automatic computation | Remaining limitation |
|---|---|---|
| P/Q generation | Fixed source catalog/proposition addresses; proposed semantic links | Missed text, wrong objects, or court-stage confusion |
| Candidate assembly | Addresses for P/supplements; isolation of invalid/duplicate/unreferenceable review | No guessed people or rewritten records based on labels |
| Shared input | Cited sources, Q witnesses/opposition, neighboring same-document passages, full relations | Learners review this evidence package, not every omission in the full judgment |
| Learned judgment | Flat, CrossEncoder, R-GCN predict the same candidates' support states | No new candidates, rules, or approvals |
| Local application | Restricts failed bindings, uses, or premise bases; retains independent content | Supporting edges do not establish whole premises |
| Derivation/checking | Recomputes explicit contracts; checks conversion, application, conclusion scope | Missing shared-variable contracts/OPEN_TEXT remain limitations |
| Final answer | Same local LLM reads full sources, rules, and method-specific intermediate view | Program checks cannot replace final source review |

The verification LLM reads complete permitted sources. The three learned models share deterministic evidence packages and relations: Flat uses their encodings, CrossEncoder aggregates fixed windows, and R-GCN propagates typed relations. Sources, recovered evidence, encoding segments, and actual inputs are saved separately. Q self-labels/reasons are not classifier features; the claim's own proposition state remains task content.

## Rule and object contracts

Rules with explicit variable maps reuse original hashes. Others retain complete premises without identity inference from names, types, or role-name equality. Treating one whole premise as one component does not claim semantic decomposition. Missing cross-premise shared-variable declarations are explicitly unmapped; affected routes cannot be reported checked and established.

Separate evidence may provide different roles, but computation uses explicit existing connections only. Unknown objects are not incorrect objects; matching types are not matching people. Whole-premise assessments, external court assessments, rule combinations, and legal approvals remain separate. Final answers may discuss open questions in supplied rules, clearly indicating those interpretations were not independently proved by the program.

## Historical training/evaluation protocol

Use 30 TRAIN and ten exposed DEV cases, without TEST/SEALED access. Supervision concerns actual current candidates; old USABLE labels are not globally converted. Dispute hashes define validation groups inside TRAIN; official DEV does not drive early stopping. All candidates may enter inference; unlabeled ones are excluded only from supervision loss.

New website references record visible Extra High, submission hashes, settings, raw replies, and times. Clear negatives are not disputes merely because they disagree with P. Only unresolved reasonable disagreement about the reference itself is `dispute`. Labels requiring model-invisible sources do not enter supervision, and references cannot supply missing correct passages to tested inputs.

The historical A–G design was: A direct answer; B reviews its own A; C reads original P; D uses Q/common processing; E/F/G replace judgment sources with three learned models on identical candidates/programs. D adds a source-review call over C and is not equal-compute. D versus E/F/G isolates candidate judgment sources. These historical comparators do not authorize mechanisms in the user's current minimal baseline.

Final answers use a common source checklist frozen before generation, with hidden method labels and fixed randomized order. Report critical-item coverage, unsupported substantive judgments, major errors, completeness, and cost without selecting a winner through an improvised weighted score. Disputes have equal weight; local links are not independent cases. Attribute interface recovery, model corrections, and final-answer changes separately.

## Reproduction and stopping

Original entry: `scripts/proof_source_verification_v20.py`; continuation: `scripts/proof_source_verification_v20_1.py`. Production and independent application checking remain `source_verification_v20.py` and `source_verification_check_v20.py`. V20.1 separately saves prefix-completability repair and failed prefixes without changing legal prompts/schema. Successful old P is reused after exact token replay; failures are not retried. Order: prepare, accept, freeze, P, Q, shared inputs, reference import, encoding, three fixed fits, A–G answers, consolidated scoring. Every dispatch checks frozen code/material hashes; dynamic Q/final inputs save before calls. Started but uncertain tasks are not resent; old results are not overwritten.

Generation budget is 36 hours, reserving 12 each for P, Q, and final answers; training limit is 24 hours. The 77 P/80 Q/70 final slots are planned positions, not successes. Two consecutive same-kind P repetition/truncation failures stop dispatch. Individual technical failures remain null; independent work may continue by dependency. UNKNOWN cannot fill failures, and semantic outcomes cannot trigger same-batch contract changes or regeneration.

The 32 engineering checks and real-tokenizer replay establish tested behavior only. Final acceptance still requires actual training, source-support evaluation across four claim types, and common-source review of complete answers. Weights, private/browser records, and bulk raw tasks remain local. No commit or push in this round.
