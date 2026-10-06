# GNN-IRAC 第二轮有限修复

固定八个旧 TRAIN，仅检查独立决定性法源、盲绑定和统一阶段门禁。无训练、SEALED、法源排名或完整法律回答。参考为模型辅助来源审阅，不能称人工金标准。

阶段原始提议与规则原文保持原值。`stage-partition` 是来源审阅后的输入准入；`admitted_inventory` 才是盲生成可读材料，原始禁用记录及审阅理由不进入其任务。允许的历史下级法院认定保留原法院与陈述状态。

`active-prebinding-version.json` 指向实际用于生成的地址修正版本。最初检查器没有识别 PDF 的 `segment_offsets`，1497837 的一个真实页段编号被误报；修正在任何盲任务提交前完成，只变更地址准入，不改规则、条件、事实或提议。原检查、初始冻结及错误记录全部保留。实际提示为 `tasks/B-*-address-v2.txt`；`blind-binding-tasks-address-v2` 保存输入。

`rule-package-address-v2` 保存规则、条件、独立审阅和不进入特征的 oracle 选择依据；`rule-condition-freeze-address-v2.json` 为实际规则冻结。`inference_payload` 明确剔除 oracle 字段，生成器没有 target 参数。存在决定性法源缺口的案件直接跳过绑定，无补标。

`blind-binding-freeze.json` 完成后才执行 `target-construction` 与 `targets`。后者仅为监督路径；任何目标标签变化不影响已冻结的盲输入及绑定。候选 SUPPORTS/DEFEATS 不是法院采纳，也不改变事实的 CLAIMED/REPORTED/FOUND 地位。

所有脚本使用标准库，分阶段且拒绝覆盖新产物。不要在完成目录重跑写入阶段。原始网页回复、下载 JSON、输入提示、版本哈希与技术异常均保留。浏览器界面记录为本地证据，不进入发布清单。真实组内 canonical 未发布时，本地链状态与组内接口状态分别报告。

历史来源大多由目标判决回顾重建，仅支持 retrospective rule application。文件中原机器路径保留以保证原字节，复用时应按仓库根解析相对入口；不能通过改写历史文件消除机器路径。

完整结果入口为 `report-zh.txt`、`feasibility-table.csv` 和 `readiness-explanation.json`。后者解释最终来源审阅建议与冻结接口准入的区别；不连续引文诊断不修复原字段，也不证明标签正确。正式NO_GO，本阶段结束，无训练或自动发布。
