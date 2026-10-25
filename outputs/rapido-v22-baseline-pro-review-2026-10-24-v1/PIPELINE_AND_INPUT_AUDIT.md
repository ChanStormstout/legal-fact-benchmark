# 实际调用链、代码与模型收到的信息

这是一份代码和缓存审计，不是新模型实验。真实输入以 runs/*/transport/*/*/request.json 为准，而不是依据README推测。所有请求是实际发送的messages和参数；response.txt为实际返回正文。输入可见不意味着模型理解或正确使用。

## A0

系统提示只有“Answer the question using the supplied materials. Cite the supplied source IDs where relevant.” 用户消息包含原始问题、材料范围和完整允许CASE＋LAW。一次普通文本输出，无JSON限制、RAG、拆解、复核、自检或修订。具体见code/A0/baseline.py和两案000-direct-answer-attempt0/request.json。

## C

source-original-read（分批原文阅读）→objects/identity→scopes/scope-review→source-records/source-record-review/coverage→tasks-inventory/tasks/rule-screen/merge/task-review→retrieval-queries→逐历史案例reading/compare/review→use-allocation/uses/use-review→bundles/bundle-review→applications/application-review→paths/path-review→burdens→requests/request-review→report选择→Python编译报告→final-review→一次依赖顺序修订→最终报告及检查。

1251841完整经历77次，1252014在use-review-5停止。调用顺序、状态、费用及原文件链接见CALLS_INDEX.csv。ACTUAL_INPUT_COVERAGE.json逐次区分：完整CASE片段确实在消息中、仅提到ID、没有该完整片段。该检查只验证字面送达，不判断是否充分、是否被注意或语义正确。代码中保存的目录、材料进入提示、实际进入计算和最后展示四件事必须分开。

## 对答案能力有直接影响的合同

code/C/src/report_control.py:catalog/selection_schema/compile_report以及runner.py的report调用是关键。最终调用输出的是已有record_ids、coverage、omission_reason及历史比较disposition；没有自由撰写最终论证的正文位置。程序把选中的来源记录、可用计算结果或缺口拼成正文。上游解释错误可能因此原样进入报告；正确来源都在请求里，也不意味着模型能在此步骤直接改写它们。

1251841初始report和repair-report给多个不同报告任务选择相同的12条来源记录。catalog中的来源记录task_id为None；compile_report寻找直接归属失败后按选择顺序分配共享记录，摘要先取得这些记录，其余部分转成also_covered_by。最终render_text把它们显示为Shared material。该过程在代码和实际selection中可复核。不能把“程序消除重复”当成“形成了各段论证”，也不能单纯要求模型写得更好而忽视输出结构限制。

来源记录、法律规则、历史比较和当前事实仍是不同对象。代码有用途资格/规则范围检查；检查运行不代表得到可执行、正确的法律结论。原始与修订computation都记录scope_supported=false，须逐条读规则理由，不能从这一布尔值推断所有法源都缺失。

## 修订

修订确实运行，revision-effect记录正文未变。repair-plan的record_ids与objects_ids为空，source_omissions只有律师出庭段S3b50d90b2024，另有一项scope修订及任务/用途/规则映射重算。已知法院与主张归属问题是否成功转换成针对这些错误对象的反馈，要检查revision-feedback、repair-plan、实际repair-*请求和响应。它支持“反馈到纠错对象的路由可能失效”的假说，不能仅凭修订没改善就认定模型无能力。

## 历史RAG

1251841确实取回并逐篇阅读3个历史案例，随后比较和复核；初始与修订的最终comparison都未选USED。报告检查还拒绝其省略理由。应沿retrieval-plan→history-reading→compare→review→accepted.analogies→selection逐层确认：没取回关键来源、取回但不适用、被误读、资格被错拒、或允许使用却未选。无引文不自动算失败；关键是是否失去了有用且合法的论证内容。历史资料不能变成当前事实，也不能被自动提升为新执行规则。

## 可确认与尚不能确认

已确认：存在法院/主张归属误读；最终报告接口限制为记录选择；相同选择与去重生成共享摘要；修订正文未变；部分原文包含正确归属线索；C比A0使用更多材料与计算。

待验证：上述接口限制对完整报告质量的因果贡献、结构化中间内容是否诱导复核重复犯错、上下文冗余是否降低注意力、9B模型能力是否主瓶颈、哪种RAG资格判断不合理。不能凭提示长度或模型大小直接定位。

API网络/服务超时与语义质量应分开。失败原始SSE以gzip保存，断流根因仍未知。不得为分析启动新模型、扩大预算或把修正后的中间答案替换进原运行。
