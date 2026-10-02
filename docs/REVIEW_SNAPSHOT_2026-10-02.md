# 本次网页审阅快照

本次发布同步规则与判决方向的设计、代码及已完成的V1–V5结果。V6正在主session串行运行，不是已完成实验；本次不发布其动态输出目录。V6代码作为开发中实现一并发布，不能据此声称实验成功或克隆后已有完整输入与结果。

先读README与docs/PROJECT_STATE.json中的research_objective，再读outputs/rules-verdict-v3/report-zh.txt、outputs/rules-verdict-v4-attribution/report-zh.txt和outputs/rules-verdict-v5-attribution-binding/report-zh.txt。PROJECT_STATE顶层latest_run仍保留早期完整关系A/B基线，不等于最新方向的实验。

V3九道法律条件题A/B各5/9状态一致；V4/V5是六处已暴露语句的归属诊断，不是独立测试。V5分类及层级一致，但缺失或错误身份仍存在。所有参考均非人工金标准，程序测试不是法律能力成绩。

发布时在docs/repository-artifacts.json的exclude_globs临时添加outputs/rules-verdict-v6-end-to-end/*，防止推送仍在变化的原始响应。V6完成、报告定稿后，主session应删除这一项，再执行prepare、verify及经授权的sync。该排除不影响本地推理，不修改V6配置、源数据或输出。未发布的local_chunk_v11.py保持不变。
