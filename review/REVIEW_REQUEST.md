请审阅 https://github.com/ChanStormstout/legal-fact-benchmark/tree/research/rules-and-verdict 的指定快照 a232a8d6134da9dace569632f5461261a622f2817912416543ff62148f8a9d4f。先读 https://raw.githubusercontent.com/ChanStormstout/legal-fact-benchmark/research/rules-and-verdict/review/START_HERE.md 与 MANIFEST.json；若远端还没有该快照，请说明并使用用户上传的本地文件，不能声称已读取。

本轮是 V7：结构化中间分析是否改善完整法律回答。三旧案回顾性开发比较：9次本地调用、2份完整最终回答、4个方法截断失败，没有同案完整配对。决定本批无法判断；B2漏掉下级法院认定并传播到最终理由，A2仍混淆部分法律与事实缺口。网页0、重试0。用户已追加本轮及后续完成轮次的推送授权；远端状态须核对提交。

读取 outputs/rules-verdict-v7-intermediate/report-zh.txt、outputs/rules-verdict-v7-intermediate/comparison-table.json、final-source-review.json及runs中的原始输出，回到同目录sources和prepared中的允许输入与法律包。不要将历史SOURCES分卷当作本轮来源。

重点审查：局部缺失是否只影响相应事实或连接；来源地址是否被误当语义认证；两阶段最终模板是否相同；技术失败是否与实质未知分开；原文已有下级认定是否被漏掉；法律覆盖不足与程序未实现是否混淆。

没有同案两份完整答案，不能比较优胜者，也不能将不同案件上的两个UNDETERMINED当准确率。来源审阅是模型辅助开发评价，不是人工金标准。请对重要意见提供具体原文、文件和机制。

本次仅审阅，不授权新模型调用、重标注、增加字段或择优重跑。保留失败和全部历史结果。
