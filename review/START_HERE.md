# ChatGPT 审阅入口

内容快照：`a91e48f92a338837b8e2bd3cb929d0cf49555f964d44809d0191e6d7722eae59`

仓库分支：https://github.com/ChanStormstout/legal-fact-benchmark/tree/research/rules-and-verdict

当前实验：V10：约束修复后的69305完整同案比较

仅补跑A一次，B复用相同配置的FIXED结果，V8两份中间结果不重抽。A/B均完整生成、均UNDETERMINED；A丢失可见下级可采性认定，B转移方式与原文及自身解释冲突。未见完整答案的可靠结构化增益，本案暂优先文本流程，但A也未验证正确；867个旧输出保持原字节。新调用1、复用最终1、网页0、重试0，本次按用户明确要求发布，原报告保留实验结束时的未推送状态。

先读[项目说明](../README.md)、[本轮报告](../outputs/rules-verdict-v10-constraint-recovery/report-zh.txt)、[逐案表](../outputs/rules-verdict-v10-constraint-recovery/comparison-table.csv)、[最终回答位置](../outputs/rules-verdict-v10-constraint-recovery/final-answer-slots.md)。

原始输出、最终prompt及程序轨迹位于 `outputs/rules-verdict-v10-constraint-recovery/runs/`；允许来源在 `sources/`，共同法律包在 `prepared/<case>/law-package.json`。冻结协议与逐次元数据均在同目录。[当前状态](../docs/PROJECT_STATE.json)和[实验索引](../docs/EXPERIMENT_INDEX.md)保留历次边界。

[代码全文](CODE.md)、[文件清单与raw链接](MANIFEST.json)、[审阅请求](REVIEW_REQUEST.md)。本地prepare/verify不会推送；GitHub是否包含本快照须核对实际提交，不能因这里生成了链接就认为已经发布。

历史关系基线：[13题结果](RESULTS.md)、[报告](../outputs/local-qwen-pattern-eval-v3/report-zh.txt)。SOURCES_01–04仍属于该历史基线，不是当前实验来源；不得混用。

raw入口：https://raw.githubusercontent.com/ChanStormstout/legal-fact-benchmark/research/rules-and-verdict/review/START_HERE.md
