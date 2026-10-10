# Proof-carrying graph integration V8

本轮研究八个已暴露判决中的规则应用候选排序。不是判前预测，不训练裁判模型，不把图分数当作批准或法律真值。历史三个关系问题、固定9B、A/P/B和法源S/B/C实验只作历史背景，本轮不恢复这些实验。

| Guide要求 | V7实际状况 | V8接入位置 | 实际地位 |
|---|---|---|---|
| 来源身份、不同来源角色 | 仅目标文书 | workflow_v8.source_roles；共享法律材料调用既有retrieve.expand | 身份/地址计算；语义仍需审阅 |
| 请求覆盖 | 导入隔离后请求可能消失 | fixed_requests/import_derivation/complete_requests | 固定槽位；技术失败null；不可将DELIVERED当全部成功 |
| 历史重放 | 比较当前源码，旧版本升级后失败 | verify_history/replay_history | 冻结核心＋明确登记支持依赖；不是原运行环境完全复现 |
| 规范化 | 字符串谓词 | candidates_v8.catalogue/mapping_candidates | 固定E5最多5个候选；模型映射不自动合并对象 |
| 组合 | 主要沿给定推导 | generate | 法律槽位生成有界组合，未知/冲突保存 |
| 检验/要件/请求 | 未区分执行角色 | layout及REQUEST图节点 | OPEN_TEXT保留个案司法评价；不会改成AND |
| 图排序 | 谱图审阅队列 | ranker_v8 + proof_graph_v8 train/deliver | Flat与两层R-GCN同信息；标签另存 |
| 完整推导与独立检查 | 已有独立检查器 | delivery_v8.run_case | 分数选择候选；独立进程重算；审批仍外部输入 |
| 修正依赖 | 文件差异为主 | reverse_index/revision_impact | 影响闭包、审阅失效、旧记录保留 |

## 数据与计算边界

新模型事实提议不人工修正。候选图在标签前保存。参考不读取分数、排名或检查结果。监督只标注候选用途的可使用/明确不可使用；未决和未标项屏蔽。独立参考给出的前提接受和目标法院评价是共同的外部研究政策，不能归功于排序模型。无正式法律批准。

陈述状态、对象绑定、时间、来源角色、规则范围、冲突和缺失同时保存在JSON与模型输入中：离散项用固定数值字段；绑定值、阶段与完整限制文本进入固定E5表示。文本不截断，超长按现有分块编码器处理。请求、规则、事实、对象、来源与候选的关系三元组由Flat和R-GCN共同读取。

生成命题没有获批的谓词映射，不能仅凭相似度用于派生；检查器仍要求类型一致。文字举证政策和开放性判断进入模型但不成为未经实现的法律操作。OPEN_TEXT仅在有出处、绑定及版本一致的外部法院评价政策下条件性重建；报告明确区分这一外部贡献。

入口：`scripts/proof_graph_v8.py prepare|ingest|encode|build|freeze|gate|train|deliver`。编码在既有E5环境，训练及检查在既有项目MLX环境。不安装新依赖、不启封SEALED、不推送。

## 实际交付与验收

完成8案16次普通High任务、12次实际拟合及64份下游交付。R-GCN已实际接入候选选择、推导和独立检查，但未显示超过简单排序的稳定完整分析收益。共同瓶颈包括角色绑定过严、引用/接受政策及预算依赖缺失；正式法律批准待定。

初始冻结后发现槽位对应未编码，训练前另存`freeze/model-input-v2`修订，原始图与冻结保持。Simple采用兼容标记软惩罚，未实施前置硬过滤；共同下游仍可能过度统一角色或因引文呈现拒绝已存在的依据。不能宣布全部语义接口已正确。详见[集中报告](../outputs/proof-carrying-graph-integration-v8/report-zh.txt)及[逐案审阅](../outputs/proof-carrying-graph-integration-v8/final-source-review.json)。
