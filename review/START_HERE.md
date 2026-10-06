# ChatGPT 审阅入口

内容快照：`3844700a0515d9491a017565ab6e58fdf924ec00fec0c8dc1c86ed78d5c6ad85`

当前实验：GNN-IRAC data feasibility and canonical adapter: NO_GO, no training

GNN-IRAC数据可行性完成：固定8个旧TRAIN，8次提议＋2次独立High来源审阅，无语义重试。1案有较完整回顾性链，7案缺决定性测试、证据内容或阶段明确的target；1106992发现目标FOUND关系残留。通用关系guard离线隔离两条，不覆盖冻结输入。真实组内canonical仅有合成接口检查，没有八案上游产物；NO_GO，未训练、未启封SEALED、未生成法律回答或发布。保留S并暂停扩大排序R-GCN。

先读[报告](../outputs/gnn-irac-feasibility-01/report-zh.txt)、[八案可行性表](../outputs/gnn-irac-feasibility-01/feasibility-table.csv)、[来源审阅](../outputs/gnn-irac-feasibility-01/source-review.json)、[泄漏审计](../outputs/gnn-irac-feasibility-01/leakage-audit.json)、[组内接口审计](../outputs/gnn-irac-feasibility-01/group-schema-audit.md)、[映射表](../outputs/gnn-irac-feasibility-01/canonical-to-irac-crosswalk.csv)。

inputs及input-graphs仅保存冻结输入；target-construction及targets仅为监督构造。bindings和task-layer-candidates是有目标访问的研究提议，未经许可不能当成推断时可取得的图特征。web保留原始JSON和调用元数据，tasks-readable是实际完整任务。真正组内canonical只测了合成fixture；八案用的是既有本地弱事实，不声称上游复现。

[代码](CODE.md)、[清单](MANIFEST.json)、[审阅要求](REVIEW_REQUEST.md)、[项目状态](../docs/PROJECT_STATE.json)。本轮无训练、无新法律回答、未启封SEALED、未提交或推送；旧S/B/C保持，S保留，暂停扩大排序R-GCN。远端未包含本地快照时须使用本地审阅包。
