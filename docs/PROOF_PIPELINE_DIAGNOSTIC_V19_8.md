# V19_8实际入口诊断与版本边界

本版本只处理既有两份V19_7 P，零生成、零训练。来源、原始输出、旧参考和原规则不改；模型语义提议不自行获得批准。

主入口为`scripts/proof_pipeline_contract_v19_8.py`，负责来源/Schema、导入、合并、条件性计算、独立检查和学习输入准备。新检查器不调用生产核心判定函数；共享固定格式词表与来源定位器。结果分别标明技术、结构、条件性语义与来源审阅状态。

冻结后确定性tokenizer回放发现容量函数误把BatchEncoding字段数当token数，旧冻结和错误观察保留。实际最终入口改用`scripts/proof_pipeline_contract_v19_8_1.py`与`final_delivery_v19_8_1.py`，计算入口仍为同一V19_8。它要求显式runner、tokenizer和配置，本轮只用mock runner，不自动启动模型。有效配置/源码补充见`freeze/final-capacity-revision-01.json`。旧根目录容量记录无效，正确结果在`capacity-correction-01/final-capacity.json`。

规则合同明确区分角色类型与共享变量，类型不证明身份。不同局部对象ID没有连接时，ALL路线保持IDENTITY_PENDING；ANY的独立分支不要求与未使用分支共享相同对象。必要例外未判断仍未决。TRUE需声明完整前提及各必要部分支持依据；FALSE需声明完整判断及至少一个必要部分反对依据。证据可用不自动成为命题真值。OPEN_TEXT继续不执行。

最终展示将完全相同的重复JSON值保存一次，引用只恢复原始值，逐值往返一致；完整原文和反论保留。不得把该变换称为模型语义改善。最终容量包含真实chat-template输入tokens、8192输出预留和256余量；65,536是操作预算，不是原生极限。超限不截断，正式答案为null。

复现使用已存在的项目运行时，不安装依赖、不下载权重：

```bash
.runtime/qwen35-v1/bin/python3 -m unittest tests.test_pipeline_diagnostic_v19_8 tests.test_contract_integrity_v19_6 tests.test_reference_addresses_v19 tests.test_final_capacity_v19_8_1 -v
```

历史冻结与输出不能直接重写。若需复现保存型脚本，先登记新的诊断输出目录，或仅运行只读测试；已有文件的保存工具会拒绝不相容覆盖。

本轮只证明所测工程行为。两案来源语义仍有明确错误，原P两个object_links均为空，1187427两项NOT_ANALYZED；完整回答未生成、未评分，GNN/CrossEncoder未训练或评价。详细证据见本轮报告和source-review.json。
