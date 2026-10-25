# V20.3: shared source sets and four truncated-task reruns

This version changes source-reference representation for initial proposals P only. The authorized work implemented shared source sets, checked lossless cache conversion, and reran 569555/P01, 1187427/P01, 1954254/P01, and 1954254/P02. Old results remain intact and the original V20.1 batch stays paused. It does not run Q, training, website tasks, or complete answers, and does not commit or push.

## Generation and restoration

The model first generates `source_sets`: nonempty arrays of unique SRC IDs, named C1, C2, and so on by position. C0 represents only an originally permitted empty reference array and occupies no table entry. Each ordered source array is defined once and reused by short ID. C IDs identify source sets, not people, truth judgments, or legal approval.

Evidence, object, and judgment-limitation `refs` become `ref_set`. Use witnesses change `source` to `source_set`, retaining necessity attributes. Only adjacent witnesses with identical attributes are grouped; different attributes keep separate groups. The program restores each source ID and its original attributes, preserving reference/witness order. Restored data then enter the original schema, conversion, merge, independent check, and conditional computation.

Constraints require the source table first and allow only declared C IDs. SRC IDs retain the original catalog and uniqueness constraints. A repeated definition of the same ordered set cannot close normally. Independent validation rejects undefined sets, empty witness sets, duplicate sets, out-of-range sources, and restored data violating the original schema. Complete permitted sources and fixed legal rules are unchanged; only reference representation and its instructions change.

`shared_sources_v20_3.py` contains encoding/expansion. Independent restoration reconstructs expected values against the original schema without calling the production expander. Constraints and runtime are separately saved in `mlx_json_constraint_v20_3.py` and `local_runtime_v20_3.py`. Old source and frozen versions are unchanged.

## Cache acceptance

Eighteen complete P records round-trip exactly, including array order, judgments, object bindings, witness necessity, and limitations. Both representations pass through the real processing entry. Conversion, checks, conditional computation, and learning inputs match; serialization key order can still change raw-byte hashes. Four failed outputs contribute only fully written analysis units: missing units are not completed and old formal failures are not promoted to success.

All 63 relevant tests passed. The shared representation of the 1954254/P01 failure prefix passed token-by-token replay through the real tokenizer/constraint engine: all 5,872 tokens were permitted and EOS was available. No model weights were loaded. Length comparisons use identical compact serialization, so removing indentation is not counted as a shared-reference benefit.

## Interpretation of the four real reruns

Model, version, temperature, seed, 65,536-token context, and 16,384-token output limit retain the old settings. Each named task receives one new attempt, including retained failures. Limits are four hours total and one hour per attempt; previously consumed P budget remains recorded rather than reset. The original batch remains paused; this authorization covers only the four listed tasks.

Report technical status, normal termination, output length, source-set definition/reuse counts, and complete analysis-directory checks. Short output may still omit premises or contain wrong judgments; normal termination is not legal correctness. Old failures and new results remain separate. New results must not rewrite old proposals, training labels, or legal rules.
