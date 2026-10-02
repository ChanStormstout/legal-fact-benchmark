# ChatGPT 审阅入口

内容快照：`a232a8d6134da9dace569632f5461261a622f2817912416543ff62148f8a9d4f`

仓库分支：https://github.com/ChanStormstout/legal-fact-benchmark/tree/research/rules-and-verdict

当前实验：V7：结构化中间分析是否改善完整法律回答

三旧案回顾性开发比较：9次本地调用、2份完整最终回答、4个方法截断失败，没有同案完整配对。决定本批无法判断；B2漏掉下级法院认定并传播到最终理由，A2仍混淆部分法律与事实缺口。网页0、重试0。用户已追加本轮及后续完成轮次的推送授权；远端状态须核对提交。

先读[项目说明](../README.md)、[V7报告](../outputs/rules-verdict-v7-intermediate/report-zh.txt)、[逐案表](../outputs/rules-verdict-v7-intermediate/comparison-table.csv)、[六个方法位置](../outputs/rules-verdict-v7-intermediate/final-answer-slots.md)。

原始输出、最终prompt及程序轨迹位于 `outputs/rules-verdict-v7-intermediate/runs/`；允许来源在 `sources/`，共同法律包在 `prepared/<case>/law-package.json`。冻结协议与逐次元数据均在同目录。[当前状态](../docs/PROJECT_STATE.json)和[实验索引](../docs/EXPERIMENT_INDEX.md)保留历次边界。

[代码全文](CODE.md)、[文件清单与raw链接](MANIFEST.json)、[审阅请求](REVIEW_REQUEST.md)。本地prepare/verify不会推送；GitHub是否包含本快照须核对实际提交，不能因这里生成了链接就认为已经发布。

历史关系基线：[13题结果](RESULTS.md)、[报告](../outputs/local-qwen-pattern-eval-v3/report-zh.txt)。SOURCES_01–04仍属于该历史基线，不是V7三案来源；不得混用。

raw入口：https://raw.githubusercontent.com/ChanStormstout/legal-fact-benchmark/research/rules-and-verdict/review/START_HERE.md
