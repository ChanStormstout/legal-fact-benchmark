# V13: common interfaces, DEV recovery, and conditional training

The task reviews evidence uses proposed by P and reconstructs bounded reasoning adopted
in a judgment. P's self-assessed labels/explanations remain inputs. USABLE includes
valid opposing evidence and does not mean that a proposition is true. Existing TRAIN
labels/raw materials are unchanged; TEST/SEALED bodies and features are not read.

The versioned entry is `scripts/proof_semantic_run_v13.py`, independent checker
`check_semantic_v13.py`, and use-prediction adapter `proof_semantic_apply_v13.py`.
role_types stores type declarations. Only explicit same-role variable addresses or
declared symbolic correspondences convert. Objects remain model proposals; exact
string equality is not semantic approval. Graph mentions are separate for each fact
record/role, without same-name merging. Unknown correspondence affects only its slot.
Evidence combinations may supply different roles; explicit conflicts remain visible.

Source restoration uses citation IDs and one adjacent same-document fragment in original
order, preserving each complete passage with reversible 3,000-character segmentation.
Fixed E5 encodes all tokens in chunks. CrossEncoder windows retain the complete left-hand
proposition and all right-hand material, averaging logits equally. Negation and opposing
evidence are not dropped. Only cited passages/fixed context are restored, not every
possible omission in the full document.

Relations come from P's explicit bounded sign/type/relation or existing fact IDs in
uses.opposition. Free text and unknown endpoints remain unencoded records; references
do not manufacture positive/negative edges. Flat/R-GCN share nodes, all text, and triples;
CE reads the same complete proposals, rules, relations, and restored sources. Message
passing is the method difference, not semantic information. Rule dependencies require
exact propositions and explicit correspondence; missing relations are not invented.

OPEN_TEXT remains unexecuted. ALL/ANY/exceptions combine P's separately proposed whole-
premise states/provenance. Usability cannot supply missing truth values; court assessments
are not program proofs. Actual traces depend on model semantics and have no formal
legal approval.

`scripts/proof_semantic_fit_v13.py` checks frozen data/resource gates before loading
weights and reuses V12 architecture/optimization. New features are incompatible with
old weights, which must not be described as trained on V13 sources/relations. Unmet gates
produce repairs/diagnosis without loading or fitting. The existing V12 CrossEncoder
may finish its current run; other seeds stay paused.

DEV follows the frozen queue with byte-identical V12 P tasks. Compatible old independent
references are reused; new use reviews hide P's self-labels, use defenses, and whole-
premise states. P-visible old references and new blind use references are registered
separately; neither is human gold. Failures remain null, without fabrication or retries.
See the report and final-audit-03/data-task-audit.json: ten DEV inputs/eight disputes,
195 valid uses, original P173/195. Replacing references for86 uses left every diagnostic
unresolved; the real complete-path gate failed, so V13 performed zero fits.
