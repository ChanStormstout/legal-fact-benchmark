# V20.4: references to declared local identifiers

EV, OBJ, and USE are one-based positions in an analysis unit's records, objects, and
uses arrays. The old schema constrained spelling/capacity but did not bind reference
ranges to actual lengths, allowing EV:1–EV:256 after declaring a single evidence record.

The new character constraint retains V20.3 shared sources and tracks completed declaration
arrays. Each unit generates analysis_status, records, objects, uses, judgments, and
limits in that order. Later references can address actual positions only after the
relevant array closes. Ranges are unit-local. When all IDs in a unique array are used,
a comma cannot begin another item and lead into a dead end.

Roles still allow UNMAPPED. Without evidence, uses is empty; without uses, components
is empty. Judgment uses/opposition_uses may be empty. object_links selects premise
before object at each endpoint, allowing only units containing objects. No available
endpoint means no new link item. These constraints never supply evidence, objects,
or uses on the model's behalf.

An independent post-generation JSON audit recomputes EV/OBJ/USE validity from actual
lengths, including nested combinations and cross-unit links. It does not call the
character constraint. Only after passing does source restoration feed the original
schema, conversion, independent processing checks, and conditional computation.
Technical failure retains a null formal answer rather than UNKNOWN.

Cache acceptance separately checks unchanged values/array order after restoring shared
representation/field order and correct acceptance/rejection of legal/illegal references.
Old illegal results stay unchanged; no guessed, deleted, or renumbered references.
Field order changes serialized text/hashes in some learning inputs. Compare decoded
JSON data and record byte identity separately. No training/feature encoding occurred;
data fidelity is not identical training behavior.

The scope was one exposed TRAIN task,569555/P01, rerun once with the same Qwen3.5-9B-4bit
snapshot, temperature, seed, full material, rules,65,536 context, and16,384 output limit.
Prior elapsed work counts against remaining resources; old queue stays paused. Tests,
legal references, and natural termination do not prove evidence meaning, identity,
source relevance, or legal correctness. No independent-test accuracy/learning claim.

Implementation: `legal_bench/mlx_json_constraint_v20_4.py`,
`legal_bench/proof_carrying/declared_references_v20_4.py`, and
`scripts/proof_declared_references_v20_4.py`. New output:
`outputs/proof-declared-references-v20-4`. Old V20.3/results retained; no training,
commit, or push.
