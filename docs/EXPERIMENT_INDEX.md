# 实验索引

历史版本按实际角色区分；源码和结果在同一次提交中同步。

| 版本 | 角色 | 报告 | 解释 |
| --- | --- | --- | --- |
| development-20-single-pass-v1 | development | [文件](../outputs/development-20-single-pass-v1/runs/first-run/report-zh.txt) | 保留来源、事实视图、汇总和抽查选择；3.7GB展开轨迹及123MB压缩轨迹只在本地保存。 |
| development-20-typed-relations-v2 | development | [文件](../outputs/development-20-typed-relations-v2/runs/first-run/report-zh.txt) | 20案277条记录；增加有来源的part_of/member_of，不能据此声称整体准确率提高。 |
| new-10-pattern-matching-v1 | exploratory | [文件](../outputs/new-10-pattern-matching-v1/runs/first-run/report-zh.txt) | 10案30题，原版本执行器21 UNKNOWN/9 NOT_FOUND，无完整匹配。 |
| unknown-two-case-study-v1 | diagnostic | [文件](../outputs/unknown-two-case-study-v1/report-zh.txt) | 仅研究两个案例；来源复核介入不能当作自动方法优势。 |
| local-qwen-pattern-eval-v1 | interrupted_development | [文件](../outputs/local-qwen-pattern-eval-v1/scoring/results-partial-v1.json) | 保存原格式失败与截断；因用户要求暂停，不是完整成功运行。 |
| local-qwen-pattern-eval-v2 | format_development | [文件](../outputs/local-qwen-pattern-eval-v2/development/444449/B/run.json) | 首次约束生成开发检查；B仍在无界字符串中截断。 |
| local-qwen-pattern-eval-v3 | development_validation_after_observed_failures | [文件](../outputs/local-qwen-pattern-eval-v3/report-zh.txt) | 同8案13题统一重跑；非独立新测试。相对模型参考正例，A0/5，B0/5并含一技术失败。 |
