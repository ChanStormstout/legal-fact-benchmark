# 报告评价与修订机制调查 v1

已完成：V38只读数据流追查；21项原始文献的聚焦调查与阅读记录；固定20项开发rubric；对现有A0、C候选及实际交付的来源核对标签和可复算计分；检查后处理的内容保留分析；替代机制及后续完整比较方案。

主要阅读入口：

- [调查与机制选择](survey.md)
- [评分协议](evaluation-protocol.md)
- [本案评分解释](case-score-report.md)
- [逐项评分表](case1251841/keypoint-scorecard.csv)
- [程序处理导致内容损失的证据](processing-loss-trace.md)
- [文献证据表](literature-evidence.csv)

边界：没有修改V38或任何旧源码、旧标注、缓存和结果；没有新API或GPT网页调用，没有新实验、GPU、Agent、训练或推送。新增脚本只下载公共论文、保存允许来源及已有报告副本、记录明确开发标签和计算分数。新修订机制仍是设计，不能声称已接通或已超过A0。

所有当前分数都是输出暴露以后制定的rubric下、Codex非盲来源复核的开发参考，不是独立专家判断或人工金标准。原始评分清单和判断均保留，可按同样标签复算，也可对某项语义判断提出并保留分歧。不能把程序复算一致说成标签已被独立验证。

复算：在本目录运行 `python3 -B score_existing.py`。该脚本不导入被测pipeline，不联网，不调用模型。逐点及断言标签在case1251841/*-labels.json，原始报告哈希与来源路径在case1251841/manifest.json。它只计算标注的分数和内容变化，不自动判断语义。

论文的下载失败和备用来源保留在paper-downloads.json与paper-fallbacks.json；完整文件保存不代表全文逐页阅读，实际阅读范围在literature-evidence.json中记录。
