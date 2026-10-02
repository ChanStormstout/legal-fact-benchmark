# V7: intermediate analysis and complete legal answers

This is a retrospective, exposed three-case development comparison. It is not rule induction, independent prediction or a retrieval comparison. Every source, law package and retrieval result is copied byte-for-byte from V6; inherited-scope-audit.json retains V6's limitations.

- A2: full allowed case + law package → sourced prose notes → same full inputs + notes → final model.
- B2: same full inputs → partial model-proposed facts → deterministic source-address recovery and candidate joins → same full inputs + proposals + checks → the same final model.

Both use the identical final prompt template and output schema, fixed 9B revision and generation settings. Four calls per case maximum, 2048 output tokens each; no retries, web calls or extra warmup generation. A stage-one technical failure prevents that method's stage two. The 14000-token intermediate reserve is a preflight safety bound, not permission to truncate. Inherited runtime settings contain legacy direct/extract defaults, but the frozen V7 runner explicitly passes 2048 for every actual call; actual_parameters records the effective limit.

`freeze/config.json` freezes code, prompts, schemas, source/law bytes, settings and evaluation protocol before inference. `freeze/token-preflight.json` records non-generative counting and runtime versions. Each final-input-derivation.json records dynamic material hashes and exact final prompt lengths; the template, derivation algorithm and bounds were frozen beforehand.

Partial tenancy facts do not require a recipient or transfer date. Roles use source-addressed literal mentions, not a mandatory global object table. Local unknowns restrict dependent fields. Nulls, role labels, shared paragraphs or model IDs are not identity evidence. An identical unique source mention or an explicitly source-addressed model coreference is only a proposed connection, never a certified semantic identity. Proposed statement status and threshold classifications are not independently verified. Missing facts or failed combinations do not establish whole-case absence.

Program checks do not cover document admissibility, corporate succession, all exceptions or historical law versions. No RuleCard identifier gates final generation. The final model sees the original source and can reject intermediate material. Correct final answers therefore cannot automatically be attributed to program checks.

`runs/<case>/<A2|B2>/stage1` and `stage2` retain prompts, raw outputs, schemas, parsed JSON and runtime metadata. B2 additionally saves `restored-sources.json` and `program-checks.json`. Final source review assesses only decisive grounds, once, as model-assisted development evaluation rather than human gold. Technical validity and source-address validity are not legal accuracy.

No changes to frozen methods after the first call, no post-result semantic reruns, no new cases, and no automatic GitHub push are permitted for this round.
