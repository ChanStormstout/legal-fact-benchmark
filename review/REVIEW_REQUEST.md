请审阅 https://github.com/ChanStormstout/legal-fact-benchmark/tree/research/rules-and-verdict 的指定快照 6d08d45186566376bb2a7ff2ac4ab123fbace635bcd7d782fea12bdc38a3979d。先读 https://raw.githubusercontent.com/ChanStormstout/legal-fact-benchmark/research/rules-and-verdict/review/START_HERE.md 与 MANIFEST.json；若远端还没有该快照，请说明并使用用户上传的本地文件，不能声称已读取。

本轮是 V22 已完成，V23 普通租约开发准备检查点。V22完成候选与检索诊断，未运行法律答案。随后已决定将两份普通租约另设开发组；V23第一批S01六项描述结构可读但语义未复核，统一索引未生成，S02/S03及两案最终回答未启动。本次按用户要求发布当前代码、V11至V22历史结果和V23准备快照，供整体科研审阅。详见[完整审阅prompt](../docs/reviews/2026-10-03-pro-research-design-review.md)。旧报告的待选择/未推送表述保留为当轮结束状态。

读取 outputs/rules-verdict-v22-scope-preparation/report-zh.txt、outputs/rules-verdict-v22-scope-preparation/comparison-table.json、final-source-review.json及runs中的原始输出，回到同目录sources和prepared中的允许输入与法律包。不要将历史SOURCES分卷当作本轮来源。

重点审查：局部缺失是否只影响相应事实或连接；来源地址是否被误当语义认证；两阶段最终模板是否相同；技术失败是否与实质未知分开；原文已有下级认定是否被漏掉；法律覆盖不足与程序未实现是否混淆。

只有同案两份完整答案才能进行配对内容比较；技术完成不等于法律正确，具体是否完成以本轮报告为准。来源审阅是模型辅助开发评价，不是人工金标准。请对重要意见提供具体原文、文件和机制。

本次仅审阅，不授权新模型调用、重标注、增加字段或择优重跑。保留失败和全部历史结果。
