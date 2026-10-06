# ChatGPT 审阅入口

内容快照：`5f7e6f89a76a4922e46125c8d0efb5f30a5b0f01efa7dbfc40fd6fab51e6e9cb`

V10集中修复完成：六案180个DEV位置均有状态（176可评价、4隔离），统一类别、可逆空白定位、材料视图和构图。TRAIN746项弱监督候选；抽查发现两案重复用途口径错配，按预定规则停止六次新拟合。旧36项排名已重评；8 SEALED未读取，未生成法律答案或提交推送。

先读[本轮报告](../outputs/rgcn-dev-contract-repair-10/report-zh.txt)、[就绪决定](../outputs/rgcn-dev-contract-repair-10/readiness-final.json)、[历史排名重评](../outputs/rgcn-dev-contract-repair-10/saved-ranking-reevaluation.json)、[实际数据清单](../outputs/rgcn-dev-contract-repair-10/cohort-status-final.json)。

本轮22次普通High数据准备，重试0。已完成同一30项池的全部DEV对齐、粗用途参考与独立来源复核；未知和隔离不作负例。旧排名重评区分旧指标、历史参考修正和扩展参考，未重拟合或用新图声称新模型表现。有限TRAIN抽查出现重复“同一法体系即BACKGROUND”的用途边界问题，训练门槛关闭；不自动改写标签至通过。保留27 TRAIN／6 DEVELOPMENT／8 SEALED，封存正文、图与标签未读。参考不是人工金标准；仅本地交付。

tasks/保存完整提交；web/保存原始回复与对话记录；sources/、labels/、graph-inputs/、graphs/保存允许来源、版本化参考及图。参考是模型生成并依据来源复核，不是人工金标准；SEALED正文与特征没有读取。

[代码](CODE.md)、[文件哈希](MANIFEST.json)、[项目状态](../docs/PROJECT_STATE.json)。仅本地prepare/verify；未提交推送，远端不能假设含有本快照。
