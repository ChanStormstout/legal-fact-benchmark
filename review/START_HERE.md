# ChatGPT 审阅入口

内容快照：`b4fd3f80f37d4cc84f249de7055f07ac3c7593bae2155af93ac9ece34192e2fb`

GNN-IRAC finite repair 02: NO_GO, blind bindings frozen before targets

GNN-IRAC第二轮有限修复完成：固定8个旧TRAIN、13次普通High、语义重试0。阶段许可覆盖711项，五案132条input-only候选绑定先于target冻结；1106992的目标关系和来源隔离。最终来源审阅2案语义READY、3案REFERENCE_ONLY、3案GAP；冻结准入0/8 READY，NO_GO。14项不连续拼接引文、范围错配、目标阶段和悬空对象/跳过绑定仍保留。组内真实canonical NOT_AVAILABLE；未训练、启封SEALED、生成完整法律回答、提交或推送。

先读[报告](../outputs/gnn-irac-feasibility-02/report-zh.txt)、[八案表](../outputs/gnn-irac-feasibility-02/feasibility-table.csv)、[最终来源审阅](../outputs/gnn-irac-feasibility-02/final-source-review.json)、[泄漏审计](../outputs/gnn-irac-feasibility-02/leakage-audit.json)、[状态](../outputs/gnn-irac-feasibility-02/readiness.json)。

[实际冻结版本](../outputs/gnn-irac-feasibility-02/active-prebinding-version.json)区分初始地址检查与首个盲任务前的PDF页段地址修正。规则和条件不作语义修改，旧冻结保留。stage-partition中的admitted_inventory是准入输入；盲任务不含目标或审阅结论。blind-binding-freeze完成后才构造targets，后者只用于监督。

[盲绑定比较](../outputs/gnn-irac-feasibility-02/blind-vs-postaware-comparison.json)、[组内真实产物审计](../outputs/gnn-irac-feasibility-02/real-canonical-adapter-audit.json)、[成本](../outputs/gnn-irac-feasibility-02/cost.json)。原始网页JSON与元数据见web；实际提示见tasks。无训练、SEALED、法律回答、提交或推送；本地材料不能假装已经在GitHub。

[代码](CODE.md)、[清单](MANIFEST.json)、[审阅请求](REVIEW_REQUEST.md)、[项目状态](../docs/PROJECT_STATE.json)。来源审阅为模型辅助评价，不是人工金标准。S/B/C保持收尾，不重新打开。
