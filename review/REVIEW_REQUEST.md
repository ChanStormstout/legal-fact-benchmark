请审阅公开仓库 https://github.com/ChanStormstout/legal-fact-benchmark 。先读取 https://raw.githubusercontent.com/ChanStormstout/legal-fact-benchmark/main/review/START_HERE.md
和MANIFEST.json，复述内容快照 03e7626c2f3c0cff1ce65b05c60cc7eaf216ae5950c542dc8f65de5472b0a69c 及实际读取的文件。若GitHub访问不可用或只读取部分
文件，请说明访问限制，改读用户上传的同版本Markdown分卷，不能假装已读取。

我们的目标是法律事实抽象与跨案件匹配benchmark，目前只完成开发验证。固定三题的
题意、陈述状态、关系方向和范围见 outputs/local-qwen-pattern-eval-v3/tasks.json。事实与参考是模型生成／来源复核，
不是人工金标准；没有人类标注者。请使用已有完整来源判断具体主张是否成立。

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
