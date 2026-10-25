# Given-rule condition-application interfaces

Version: `outputs/gnn-irac-application-development-01/`. The target is a court's merits
assessment of one condition under independently sourced given rules, not retrieval,
rule induction, or whole-case prediction. Seventeen packets form graphs; eight packets/
thirteen conditions enter weakly supervised grouped development comparison. Historical
materials/freezes remain intact.

Data order: existing full sources → bounded eligibility/stage subspans → independent
shared rule templates → input proposals restricted to allowed spans → local structural,
citation, and dependency checks → input graphs → independent target proposals/one source
review → supervision sidecars → fixed E5 cache → grouped split/freeze → P/Flat/Graph.
Review may reject unsafe input; target labels must not determine facts, edges, or whether
condition nodes exist.

corpus_inventory excludes SEALED bodies and records exposure. rule_templates binds
independent sources/scope. input_partition stores reversible subspans and locally isolates
bad objects/dependencies. target_adapter selects loss targets only. graph_builder takes
inputs only. text_cache encodes all node text. application_models gives Flat/Graph the
same nodes/status/directed triples. train_eval handles whole-dispute splits, local masks,
group-mean loss, and evaluation.

Graphs contain Issue,Rule,Condition,Fact,Evidence,Entity. Source relations and program
candidate links are separate; candidate fact/evidence–condition edges have no support/
opposition labels. Shared IDs or relation edges are not legal proofs. True group-level
canonical outputs are unavailable; this reuses a local native-input contract only.

SATISFIED means established, DEFEATED not established, UNRESOLVED explicitly analyzed
but unresolved on the evidence. DEFEATED retains reasons such as burden failure or
opposite facts and is not equivalent to factual falsity. NOT_DECIDED, uncertain review,
missing decisive input, and failed quotations are null with mask=false. No UNRESOLVED
supervision exists; recall for unobserved classes is null.

Citations require contiguous original spans or unique reversible whitespace mapping.
Known display wrappers can map to the same citation label while preserving spans/hashes.
No footer deletion, legal-word rewriting, or discontinuous sentence stitching. Raw
tasks/proposals, review decisions, masks, and address-repair lineage are separate.

`scripts/irac_application_study.py` stages are prepare,prepare-inputs,import-inputs,
prepare-targets,prepare-reviews,admit,encode,freeze,train. Completed web work is not a
reason to resubmit. E5 uses `.runtime/irac-e5-v1`; Flat/Graph uses `.runtime/qwen35-v1`
without invoking the Qwen language model. `scripts/report_irac_application.py` reports
saved results without retraining.

Three folds/three seeds with inner-validation early stopping yield eighteen fits.
Weights/vectors remain local, hashes frozen. A public package cannot exactly replay
missing private caches, though the fixed encoder revision permits re-encoding. References
are not human gold; dispute relationships remain partly unconfirmed; SEALED unread.

Results in report-zh.txt and training/summary.json: Flat predicted all established;
Graph added no benefit and missed all three DEFEATED conditions. Negatives concentrate
in one fold whose training set lacks negatives. This supports neither GNN expansion
nor Flat case-conditioning ability. Further work requires separate authorization, with
opposing-condition supervision/input coverage prioritized over automatic tuning/test access.
