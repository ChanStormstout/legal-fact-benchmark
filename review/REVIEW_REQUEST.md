请审阅公开仓库的指定分支 https://github.com/ChanStormstout/legal-fact-benchmark/tree/research/rules-and-verdict 。先读取 https://raw.githubusercontent.com/ChanStormstout/legal-fact-benchmark/research/rules-and-verdict/review/START_HERE.md
和MANIFEST.json，复述内容快照 1c520c22bb65abee2d346bdaab6738396758a5b770d2f4526159613938f66f92 及实际读取的文件。若GitHub访问不可用或只读取部分
文件，请说明访问限制，改读用户上传的同版本Markdown分卷，不能假装已读取。

我们的目标是从案件事实与争点取得有来源的规则，帮助新案件找到适用法源并形成有依据的请求结果。
是否将benchmark作为主要产出尚未决定；请先读docs/RESEARCH_DIRECTION.md。
目前只完成事实表示与关系匹配的开发诊断，尚未完成规则归纳、法源检索或判决预测实验。固定三题的
题意、陈述状态、关系方向和范围见 outputs/local-qwen-pattern-eval-v3/tasks.json。事实与参考是模型生成／来源复核，
不是人工金标准；没有人类标注者。请使用已有完整来源判断具体主张是否成立。

先区分中间关系匹配与最终法律任务，评价现有方法怎样支持规则获取、适用法源检索和逐要件应用，
指出尚缺的环节。事实模式频率不产生法律效力；研究性判决预测与已有判决的事后重建须分开。

优先检查：1. 字段未知是否只影响依赖该字段的判断；2. 类型、法院认定、诉讼阶段、
个体／群体、房产部分／整体是否在抽取转换时被混淆；3. 固定关系执行器的候选生成、
绑定、状态汇总是否有错误；4. JSON约束是否只修格式，是否有事实补造或错误确定化；
5. 分母、技术失败、未知、语义核查和开发／独立测试区分是否准确。

阅读CODE.md、RESULTS.md及相关SOURCES分卷，并沿原文→模型原始输出→结构化记录→轨迹
提出具体意见。两道既有来源核查可作线索，不能把它们当作全案金标准。不要只因匹配
数量减少便认定错误减少，也不要据这批题宣称开放发现能力或总体准确率。

每项建议写明文件与行号、关键原文／轨迹、问题机制、最小修复、应验证的测试及证据
不足之处。区分必须修复与下一轮研究建议；不要生成替代事实或建议覆盖旧结果。
可以按review/feedback/schema.json输出JSON反馈，snapshot_id使用上述内容快照。
本次只是review，不授权新实验、模型更换、重标注或冻结方法后的同题择优重算。
