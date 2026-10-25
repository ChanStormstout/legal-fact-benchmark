# RAPIDO V22：两案实际结果、普通基线与 Pro 审阅包

本包用于独立质疑当前结论：C是否比一次普通LLM回答更好？为什么77次调用没有形成明显的整案优势？不预设C一定失败，也不把baseline当正确答案。新评价标准在观察输出后制定，属于回顾性开发审查。

|案号|A0|V22 C|当前边界|
|---|---|---|---|
|1251841|1次调用，17.46秒，$0.00183987，有最终报告|77次，1624.33秒，$0.4231378，有报告但内部未通过，修订正文未变|双方存在来源/推理错误；覆盖互有得失；未证明C整案胜出|
|1252014|1次调用，25.82秒，$0.00207092，有最终报告|43次，1563.20秒，核验中read timeout，无最终报告|C失败保留分母，语义质量null；A0也有需复核的程序/法源错误|

C两案已确认费用$0.62965455，另$0.04980736为未知用量保守预留，不是确认扣费。A0两案合计$0.00391079。无新模型调用、训练或重跑；原实验字节不变。本次仅复制证据、制定透明审阅标准并发布。其他十案A0结果另存为历史库存，不能当成V22十二案比较。

## 阅读顺序

1. [问题和评价标准](QUESTIONS_AND_RUBRIC.md)
2. 两案允许材料：[1251841](cases/1251841/ALLOWED_SOURCES.md)、[1252014](cases/1252014/ALLOWED_SOURCES.md)
3. 原报告：[1251841 A0](runs/A0/cases/1251841/final-report.txt)、[1251841 C](runs/C/cases/1251841/C/final-report.txt)、[1252014 A0](runs/A0/cases/1252014/final-report.txt)、[1252014 C失败](runs/C/cases/1252014/C/outcome.json)
4. [实际pipeline与输入审计](PIPELINE_AND_INPUT_AUDIT.md)、[调用索引](CALLS_INDEX.csv)、[输入逐段送达](ACTUAL_INPUT_COVERAGE.json)
5. [第一案原文评审](CASE_1251841_REVIEW.md)、[第二案原文评审](CASE_1252014_REVIEW.md)
6. [完整Pro审阅prompt](PRO_REVIEW_PROMPT.md)

code/C是V22原字节源码、提示词、schema、冻结规则、协议和冻结清单。code/dependencies保留冻结的项目依赖；code/A0保留实际baseline及运输/格式上下文。不能仅看保留的本地模型配置字段就说本轮用了本地权重：实际请求与回执明确是Together API。

runs/C/transport保存120次实际HTTP请求体和模型正文；runs/A0/transport保存两次直接回答请求。runs/C/cases保留中间对象、范围、用途、计算、选择、复核、修订和最终结果。cases/*/C-full-snapshot.json保留完整允许输入，包括HISTORY；简明CASE/LAW视图不替代该快照。EVIDENCE_MANIFEST记录原路径、字节哈希和导出映射；不发布HTTP认证头、凭据、浏览器截图、环境、模型权重或隐藏评分参考。成功SSE逐token帧只保留哈希，失败帧以gzip无损保存；实际请求和正文未删减。

这是审阅快照，不是自动可重跑发行版。原代码中的绝对路径和私有启动授权没有改写；若要复现实验，须另建运行目录并单独授权。文件里的旧状态是当时记录；当前事实以runs/*/outcome和summary为准。主仓库其他未提交工作未随本次推送。
