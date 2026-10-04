# ChatGPT 审阅入口

内容快照：`426855ddcbf6bf98a735b08ecc2a6e25041dac207c4fa9ab8d6f00ef17fcfe51`

六案完成38次准备、36次真实训练、20份法律回答。C/C0两种子材料均相同，未显示图传播额外收益；B有限依据覆盖较好但完整回答有得有失。保留简单关系候选，暂不扩大R-GCN。

先读[报告](../outputs/rgcn-ranking-development-06/report-zh.txt)、[逐案表](../outputs/rgcn-ranking-development-06/comparison-table.csv)、[答案入口](../outputs/rgcn-ranking-development-06/final-answer-slots.md)、[集中来源审阅](../outputs/rgcn-ranking-development-06/final-source-review.json)。

tasks/保存完整提交，raw/保存原始回复，parsed/保存解析；sources/保存允许案情和laws.json。graphs/与labels/隔离输入及监督；folds/保存真实训练及本地权重；selections/保存材料选择。training-freeze.json与freeze/code/固定实际方法。网页记录见web-ledger.json。

本轮36次训练、20份最终回答已完成。C与C0材料相同不证明消息传播有效；45/64有效条件及引文过滤损失须同时审阅。权重npz仅本地保存，哈希见local-weight-manifest.json。

[代码](CODE.md)、[文件清单](MANIFEST.json)、[审阅请求](REVIEW_REQUEST.md)、[项目状态](../docs/PROJECT_STATE.json)。本地包未提交或推送，GitHub不保证含当前版本；旧RESULTS及SOURCES不是本轮材料。
