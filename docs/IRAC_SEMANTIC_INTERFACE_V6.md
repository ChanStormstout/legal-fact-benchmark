# V6: two-case comparison after semantic-interface repair

Compare direct A with original proposal P plus complete sources B on exposed cases
112400/188721101. V5 sources,legal templates,scope unchanged. No C,web calls,reference
annotation,GNN training,new authorities. Outputs: `outputs/irac-semantic-interface-v6/`.

## Computational changes

P separates records,arrangements,condition analyses,local limitations. Records reference
array positions and receive program IDs, without a unique parent arrangement. One record
can serve different uses. Speaker/court stage remain in text/status and do not force
new transactions; model arrangement errors require subsequent evaluation.

Each analysis references an arrangement,a full legal proposition,and evidence uses.
SUPPORT/OPPOSE are proposed directions summarized in evidence_use_summary. Counts,
one-sided support,or absent opposition do not create truth. Model assessment/reasons
remain separate. Explicit judgments with legal addresses/relevant declared links can
enter Boolean combination as model premises; code does not prove their legal meaning
or sufficiency. Conflicts,unknowns,local blocks remain. Wrong model premises can yield
wrong conditional claim results; checks are offline audit only.

Frozen source containers determine roles. Case sources belong to the target document;
authority-package entries are legal sources. Uses relying only on authorities for
current-case facts are isolated, preserving records/other legal uses. Address validity
is not semantic review; embedded quotations still need interpretation/source review.

Legal templates supply one readable condition catalog with full propositions for original
IDs/subbranch IDs. Models no longer maintain separate ADDR/test/branch fields or generate
internal graph edges/dependencies. AND/OR/NOT and authority status remain unchanged.
Explicit model premises combine; one failed arrangement does not imply no other instance.

Limits address arrangement,condition,use. Record-specific limits preserve other records/
arrangements. Whole-proposition limits retain pending-review scope even if their citations
fail. Unlocatable limits become coverage gaps, not whole-case negation. Generic gaps
notes do not automatically block every combination.

Final answers retain fields and must answer each fixed request exactly once with at
least one decisive analysis. Empty answers,missing/duplicate requests,empty reasons
fail technical completion and yield null. Final prediction is binary; reasons/gaps
must distinguish known support,application gaps,assumptions,without treating all unknowns
as negatives.

## Inputs and acceptance

A/B share final prompt,schema,complete permitted sources/legal package. B adds only raw
new P, not import results/program checks. Raw P,evidence ledger,use isolation,condition
premises,full checks are separately saved. V5 source ordering/reversible display add
or remove no permitted content.

Real-tokenizer checks found numeric-position enums wrongly declared as strings; corrected
to integers before the first model call. Model,constraints,settings unchanged; no model
call consumed. Tests exercised actual completion,saving,import,assembly. Old replay
checks addresses/use mappings without rewriting answers or filling new judgments.

E measures implementation; M arrangement/fact/condition organization; L source/legal
fidelity of final answers. E success implies neither M nor L. JSON completeness,state
changes,binary predictions are not legal correctness. Results/costs/decision are in
the version's report.

## Freeze and stopping

Qwen3.5-9B-4bit revision `8b2b98c00a6b4d291155e4890773ca8f769aee53`,MLX-VLM0.7.4,
LMFE0.11.2,repaired constraint,greedy,seed20261001,repetition_penalty1,thinking off.
P4,096/final3,072 output,total32,768 context. Fixed112400 A/P/B then188721101 A/P/B,
at most six calls/1,800 generation seconds/no retries. Individual failure blocks dependents;
resource/time exhaustion stops the round.

freeze/config.json fixes code,prompts,schemas,materials,parameters,evaluation before
generation. Old A is incompatible with changed final contracts/prompts and is not reused.
One centralized model-assisted source review, not human gold. No automatic semantic
repair,rerun,expansion,commit,push after completion.
