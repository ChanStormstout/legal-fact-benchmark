# 同一提议检查前后与局部修订 v4

主批直接使用v2三案13项原始请求及v3来源复核政策。检查前后共享同一快照，不用v3维护者改写后的Sopan Q5代替原始提议。参考来自此前独立网页来源任务，当前映射与审阅不是盲评，不称人工gold。

`scripts/proof_checker_evaluation_v4.py prepare/run`冻结并运行主诊断；已完成目录不能覆盖重跑。v3检查器保持原字节。新`reconstruction_view_v4.py`分开未核验的请求文字与根据研究规则生成的条件性结论。

诊断发现完整步骤哈希会拒绝语义等价的具名输入顺序或解释句变化；自由请求文字则不受类型检查约束。`scripts/proof_checker_patch_v4.py prepare/validate`在独立repair-01版本迁移语义地址，不修改规则或前提；新v4检查入口读取这个版本。所有影响执行的字段继续固定，解释文字不自动获得可信地位。

验收分别保存13项原始请求、9项人工控制改动、7项单元测试和6项修订入口检查。它们不可混为法律准确率。检查器没有自动理解来源的能力；源文审阅先确定的语义接受决定不计入程序的语义错误发现能力。

见[完整报告](../outputs/proof-carrying-checker-evaluation-v4/report-zh.txt)、[逐请求对照](../outputs/proof-carrying-checker-evaluation-v4/natural-comparison.csv)、[来源审阅](../outputs/proof-carrying-checker-evaluation-v4/source-review.json)、[控制诊断](../outputs/proof-carrying-checker-evaluation-v4/controlled-review.json)及[修订入口验收](../outputs/proof-carrying-checker-evaluation-v4/repair-01/validation.json)。当前投入决定是保留检查与来源审阅流程，进入既定校准准备，不扩大图模型。
