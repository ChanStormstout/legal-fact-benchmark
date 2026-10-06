# V09主训练审阅入口

27 TRAIN、730项暂定用途监督、30法源，两个种子共6次S/B/C训练完成。DEV核心送达S8/11、B7/11、C4/11与9/11；无稳定条件化收益，暂停扩大图。8 SEALED未用；未生成法律回答或推送。

[中文报告](../outputs/rgcn-data-expansion-09/main-training-01/report-zh.txt)、[逐案比较](../outputs/rgcn-data-expansion-09/main-training-01/case-comparison.md)、[汇总](../outputs/rgcn-data-expansion-09/main-training-01/aggregate.json)、[材料取舍](../outputs/rgcn-data-expansion-09/main-training-01/material-changes.json)、[冻结配置](../outputs/rgcn-data-expansion-09/main-training-01/training-freeze.json)、[实际参数](../outputs/rgcn-data-expansion-09/main-training-01/protocol.json)。

runs/保留六次拟合日志及全部开发排名、概率、原文选择；权重仅本地保存。8个封存案例没有运行。本轮参考为不完整模型标签，新增16项缺少开发对齐与用途，不能当完整30法源评价。先检查B是否超过S，再检查C是否稳定超过B，不挑选有利种子。没有新完整法律回答。

[源码](CODE.md)、[发布清单](PUBLICATION.json)、[项目状态](../docs/PROJECT_STATE.json)。仅本地更新，未提交推送。
