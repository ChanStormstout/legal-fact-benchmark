# ChatGPT 审阅入口

内容快照：`beb8a2eade0ee91d72281104234684ba3a4d035ffd36df9c5fb25880faa0da4a`

仓库：https://github.com/ChanStormstout/legal-fact-benchmark
当前实验：outputs/local-qwen-pattern-eval-v3（开发验证；已观察过格式问题，非独立新测试）。

先读[项目说明](../README.md)、[当前状态](../docs/PROJECT_STATE.json)和
[最新中文报告](../outputs/local-qwen-pattern-eval-v3/report-zh.txt)。然后按需读取[代码全文](CODE.md)、
[全部13题结果与轨迹](RESULTS.md)，以及[SOURCES_01](SOURCES_01.md)、
[SOURCES_02](SOURCES_02.md)、[SOURCES_03](SOURCES_03.md)、[SOURCES_04](SOURCES_04.md)。
这些来源分卷包含当前8案完整提供材料，引用相同段落编号。

相对模型参考答案，5正例：A0识别／5漏检；B0识别／4漏检／1输出截断。
6参考未找到：A/B均返回未找到；2参考未知：A/B均返回未找到。
不能把“全返回未找到”中的一致部分解释为算法准确。全文依据与参考均可质疑，
但不能只因程序输出与参考不同就认定程序或参考正确。

[MANIFEST.json](MANIFEST.json)列出所有公开文件、哈希和raw链接，
[PUBLICATION.json](PUBLICATION.json)说明本地保留内容，[审阅请求](REVIEW_REQUEST.md)
给出要检查的问题。所有main链接会随下一次同步更新；需要固定版本时，在GitHub
将URL中的main换为正在审阅的提交SHA。内容快照用于核验文件组合，不冒充Git提交SHA。

公开raw入口：https://raw.githubusercontent.com/ChanStormstout/legal-fact-benchmark/main/review/START_HERE.md
原始完整结果：https://raw.githubusercontent.com/ChanStormstout/legal-fact-benchmark/main/outputs/local-qwen-pattern-eval-v3/scoring/results-v1.json

每次更新：prepare生成文件，verify核验，sync明确提交并推送。不是后台自动同步。
不要只读取本入口就声称已经阅读全部代码或全文判决。
