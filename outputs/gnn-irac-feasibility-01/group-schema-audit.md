# 组内实际接口审计

读取 main `88ff082cce05b948119fcd54f6ef8fe8540baedb`，完整文件与哈希见 group-read-manifest.json。当前本仓库远端 research/rules-and-verdict 为 `6ac6de5...`；本地V11完成但尚未发布，不能假称远端已包含V11。

实际 config.yaml → prompts/prompt2_v5_2_rich_canonical.md → src/run_case.py。production prompt 行为v5.3.2，候选/最终Schema标识仍v5.2；README仍写v5.2。兼容标识与行为版本必须分别记录。候选由 llm_candidate_schema 接收，canonicalizer 再生成最终九类型Schema，不直接输出IRAC图。source_validator验证源span；semantic_admission/semantic_audit处理语义诊断；production_guardrails限制修复。我们没有运行这些昂贵上游步骤或其ASU API。

实际类型为Case/Court/Party/Claim/Fact/Evidence/LegalIssue/Precedent/Conclusion。没有Rule/Element/Application节点；Prompt1A有rule_and_authority及elements、Prompt1B有elements_analyzed，不意味着这些内容以独立结构进入canonical。

canonicalizer `_prune_orphan_claims`要求Claim有Fact SUPPORTS/DEFEATS/CONTESTS实质边；孤立Claim会被剪去。没有Claim不能解释为没有请求。`_add_mechanical_edges_and_evidence`可按Fact出处生成source-passage Evidence；它是文字来源锚，不是第二份实物证据。生产prompt明确区分当前法院采纳与下级法院事实经过，但Schema本身没有typed court-level/stage、property、event或rule-condition槽位；这部分需要有出处的下游sidecar，不能按名字猜测。

全判决canonical保留court_status与Conclusion，适合来源分析，直接进入预测图会泄漏。adapter要求逐节点、逐字段pre-outcome许可，排除目标Conclusion/接受拒绝处理及悬空边，不复制全判决proof_chains。两个空ID、同角色、同引文均不创建新身份边。

组内main未发现任何这8案的canonical JSON产物。本轮真正canonical adapter用完整合成合法fixture验证，8案数据验证复用现有local weak inventory，来源身份明确，不声称上游复现或真实canonical数据端到端通过。实际canonical数据验收是后续接入前置条件；可以在不修改组内production schema的情况下添加任务层，但缺失信息不能由adapter自动补造。

评价代码EVALUATOR_LOGIC.md依原文双lane生成自动参考，再做关系匹配。其精度/召回依赖模型参考，不是人工gold；没有以其自动得分替代本轮逐链核查。
