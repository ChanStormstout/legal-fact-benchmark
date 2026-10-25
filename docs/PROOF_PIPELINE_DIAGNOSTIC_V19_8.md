# V19.8: actual-entry diagnostics and version boundaries

This version processes only the two existing V19.7 P records, with zero generation or training. Sources, raw outputs, old references, and original rules remain unchanged. Semantic model proposals do not approve themselves.

`scripts/proof_pipeline_contract_v19_8.py` connects source/schema checks, import, merge, conditional computation, independent checking, and learning-input preparation. The new checker does not call production decision-core functions; it shares fixed format vocabulary and the source locator. Technical, structural, conditional-semantic, and source-review status are reported separately.

After freezing, deterministic tokenizer replay revealed that the capacity function counted BatchEncoding fields instead of tokens. The old freeze and erroneous observation remain. The actual final entry is `scripts/proof_pipeline_contract_v19_8_1.py` with `final_delivery_v19_8_1.py`, using the same V19.8 computation. Runner, tokenizer, and configuration must be explicit; this round used only a mock runner and does not automatically start a model. See `freeze/final-capacity-revision-01.json`. Old root capacity records are invalid; corrected results are in `capacity-correction-01/final-capacity.json`.

Rule contracts distinguish role types from shared variables: type does not establish identity. ALL routes with unconnected local object IDs remain IDENTITY_PENDING. Independent ANY branches need not share objects with unused branches. Unevaluated necessary exceptions remain unresolved. TRUE requires a declared complete premise and support for every necessary component; FALSE requires a complete judgment and opposition to at least one necessary component. Evidence usability does not establish premise truth. OPEN_TEXT is still not executed.

Final presentation stores identical repeated JSON values once and references restore original values exactly. Full sources and counterarguments remain. This is not a semantic model improvement. Capacity counts actual chat-template input tokens, 8,192 reserved output tokens, and a margin of 256. The 65,536 limit is operational, not a native limit. Over-limit inputs are not truncated; the formal answer is null.

Use the existing project runtime; do not install dependencies or download weights:

```bash
.runtime/qwen35-v1/bin/python3 -m unittest tests.test_pipeline_diagnostic_v19_8 tests.test_contract_integrity_v19_6 tests.test_reference_addresses_v19 tests.test_final_capacity_v19_8_1 -v
```

Do not overwrite old freezes or outputs. Register a new diagnostic output directory before reproducing saving scripts, or run read-only tests. Saving utilities reject incompatible overwrite.

This round establishes only the tested engineering behavior. Both cases still have clear source-semantic errors; both original P `object_links` arrays are empty, and 1187427 has two NOT_ANALYZED items. Final answers were neither generated nor scored. GNN/CrossEncoder training and evaluation did not run. See the report and `source-review.json` for evidence.
