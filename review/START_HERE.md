# ChatGPT 审阅入口

内容快照：`6d08d45186566376bb2a7ff2ac4ab123fbace635bcd7d782fea12bdc38a3979d`

仓库分支：https://github.com/ChanStormstout/legal-fact-benchmark/tree/research/rules-and-verdict

当前实验：V22 已完成，V23 普通租约开发准备检查点

V22完成候选与检索诊断，未运行法律答案。随后已决定将两份普通租约另设开发组；V23第一批S01六项描述结构可读但语义未复核，统一索引未生成，S02/S03及两案最终回答未启动。本次按用户要求发布当前代码、V11至V22历史结果和V23准备快照，供整体科研审阅。详见[完整审阅prompt](../docs/reviews/2026-10-03-pro-research-design-review.md)。旧报告的待选择/未推送表述保留为当轮结束状态。

先读[项目说明](../README.md)、[本轮报告](../outputs/rules-verdict-v22-scope-preparation/report-zh.txt)、[逐案表](../outputs/rules-verdict-v22-scope-preparation/comparison-table.csv)、[最终回答位置](../outputs/rules-verdict-v22-scope-preparation/final-answer-slots.md)。

原始输出、最终prompt及程序轨迹位于 `outputs/rules-verdict-v22-scope-preparation/runs/`；允许来源在 `sources/`，共同法律包在 `prepared/<case>/law-package.json`。冻结协议与逐次元数据均在同目录。[当前状态](../docs/PROJECT_STATE.json)和[实验索引](../docs/EXPERIMENT_INDEX.md)保留历次边界。

[代码全文](CODE.md)、[文件清单与raw链接](MANIFEST.json)、[审阅请求](REVIEW_REQUEST.md)。本地prepare/verify不会推送；GitHub是否包含本快照须核对实际提交，不能因这里生成了链接就认为已经发布。

历史关系基线：[13题结果](RESULTS.md)、[报告](../outputs/local-qwen-pattern-eval-v3/report-zh.txt)。SOURCES_01–04仍属于该历史基线，不是当前实验来源；不得混用。

raw入口：https://raw.githubusercontent.com/ChanStormstout/legal-fact-benchmark/research/rules-and-verdict/review/START_HERE.md
