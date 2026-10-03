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
| local-qwen-pattern-eval-v4 | exposed_development_diagnosis | [文件](../outputs/local-qwen-pattern-eval-v4/report-zh.txt) | 三题UNKNOWN；引用命名混淆。 |
| local-qwen-pattern-eval-v5 | exposed_development_diagnosis | [文件](../outputs/local-qwen-pattern-eval-v5/report-zh.txt) | 对象全null；零上限不被生成器可靠执行，停止于格式失败。 |
| local-qwen-pattern-eval-v6 | exposed_development_diagnosis | [文件](../outputs/local-qwen-pattern-eval-v6/report-zh.txt) | 两个MATCH的所有权主体或群体绑定不正确，均未计成功。 |
| local-qwen-pattern-eval-v7 | exposed_development_diagnosis | [文件](../outputs/local-qwen-pattern-eval-v7/report-zh.txt) | 路由漏掉关键段落；法律关系被错当房产。 |
| local-qwen-pattern-eval-v8 | exposed_development_diagnosis | [文件](../outputs/local-qwen-pattern-eval-v8/report-zh.txt) | 关键购买/转租抽取改善，但没有关系边；发现示例污染。 |
| local-qwen-pattern-eval-v9 | exposed_development_diagnosis | [文件](../outputs/local-qwen-pattern-eval-v9/report-zh.txt) | 目标类型强制重述其他事件；合并超20条失败，保留原结果。 |
| local-qwen-pattern-eval-v10 | exposed_development_diagnosis | [文件](../outputs/local-qwen-pattern-eval-v10/report-zh.txt) | 2案6题；2个MATCH中1个有来源支持、1个转租类型错误；4 UNKNOWN。 |
| local-qwen-semantic-probe-v1 | diagnostic | [文件](../outputs/local-qwen-semantic-probe-v1/report-zh.txt) | 两个原文短段有/无约束对照；非完整pipeline评分。 |
| local-qwen-split-assembly-v1 | diagnostic | [文件](../outputs/local-qwen-split-assembly-v1/report-zh.txt) | 同一v9输出的结构合并修复，无新生成；26记录进入导入/执行。 |
| local-qwen-type-gate-probe-v1 | diagnostic | [文件](../outputs/local-qwen-type-gate-probe-v1/report-zh.txt) | 类型核验分出转租/自用需要，状态核验误拒正例；未自动应用到事实。 |
| rules-verdict-v1-resource-format | development_resource_format_failed | [文件](../outputs/rules-verdict-v1/report-zh.txt) | 两旧案4次本地生成；JSON可解析，但多人角色／关系端点导致0可用断言，A理由触及字段上限；按计划停止P1，尚无法律端到端成绩。 |
| rules-verdict-v2-development | exposed_development_diagnosis | [文件](../outputs/rules-verdict-v2/report-zh.txt) | 两旧案格式通过；历史判决BM25、本地规则提取及一旧案三方法诊断。原A3错误编译保留，统一翻译门槛后仅重跑A3；仍UNDETERMINED。完整法律条件执行未完成，非独立测试。 |
| rules-verdict-v3-conditions | exposed_development_condition_diagnosis | [文件](../outputs/rules-verdict-v3/report-zh.txt) | 3案9条件，6次本地生成及1次High参考。A/B状态各5/9一致，不能称准确率；B漏一支持条件并过度否定两未知。三次原布尔格式失败统一本地恢复，原输出保留。完整法律规则执行未完成。 |
| rules-verdict-v4-attribution | targeted_old_case_diagnostic | [文件](../outputs/rules-verdict-v4-attribution/report-zh.txt) | 三旧案六目标，3次固定9B生成；分类6/6、采纳层级5/6一致，仍有法院和双方律师归属错误。未接入执行器，不是端到端能力证据。 |
| rules-verdict-v5-attribution-binding | exposed_development_diagnostic | [文件](../outputs/rules-verdict-v5-attribution-binding/report-zh.txt) | 六处分类/法院层级一致；结构准入4、隔离2，仍有身份语义错误通过。不能据此确认端到端改进。 |
| rules-verdict-v6-end-to-end | retrospective_exposed_development_full_path | [文件](../outputs/rules-verdict-v6-end-to-end/report-zh.txt) | 三案六次固定9B调用完成；B三案均无可用断言，A存在结论矛盾与不受来源支持的适用。共同提示含基础公式，全部按回顾性开发演示解释，不是预测验证。 |
| rules-verdict-v7-intermediate | retrospective_development_comparison | [文件](../outputs/rules-verdict-v7-intermediate/report-zh.txt) | 三旧案两阶段对照，9次本地调用、2份完整最终回答、4个方法截断失败，无同案完整配对，结果无法判断优劣。部分事实可进入下游，但遗漏下级认定仍传播；模型辅助来源审阅，不是金标准。网页0、重试0，旧轮保留。 |
| rules-verdict-v8-paired | bounded_same_case_recovery | [文件](../outputs/rules-verdict-v8-paired/report-zh.txt) | 69305；A/B第一阶段OK，A最终REPETITION_ABORT，B最终SKIPPED。3调用、无完整配对；只说明本冻结配置未完成。本轮不推送。 |
| rules-verdict-v9-final-examples | final_only_exposed_development_validation | [文件](../outputs/rules-verdict-v9-final-examples/report-zh.txt) | 69305复用V8中间结果；两个完整示例与短字段职责一起改；A/B各一次最终生成均point重复中止，2调用、无完整答案；不推送。 |
| json-constraint-diagnosis-v1 | same_input_constraint_debugging | [文件](../outputs/json-constraint-diagnosis-v1/report-zh.txt) | 69305 V9 B同输入：无约束/修复约束各一次，均OK、641 tokens且raw相同；第42个合法结束token被旧快速路径遗漏。默认入口已修复，5相关测试通过；不是法律正确性或A/B收益成绩，旧输出保留、本地不推送。 |
| rules-verdict-v10-constraint-recovery | retrospective_recovered_final_pair | [文件](../outputs/rules-verdict-v10-constraint-recovery/report-zh.txt) | 69305修复后完整配对：A新调用一次/B复用兼容FIXED输出；均UNDETERMINED，A遗漏已有下级认定、B模式定性及assessment矛盾。未发现整体结构化收益，本案暂优先文本；不是独立测试或全新两阶段运行。本地不推送。 |
