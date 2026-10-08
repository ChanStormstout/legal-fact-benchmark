# 给定规则的条件适用接口

当前版本见`outputs/gnn-irac-application-development-01/`。研究对象是目标法院对一个条件的实体裁判状态，给定规则来自独立法源；不是自动检索、规则归纳或胜败预测。17包可构图，8包13条件进入弱监督分组开发比较，全部历史材料与冻结版本保留。

数据顺序是：已有完整来源→有限资格筛查与阶段子跨度→独立共同规则模板→只看允许跨度的输入提议→局部结构、引用与依赖闭包检查→输入图→独立目标提议与一次来源审阅→监督sidecar→固定E5缓存→分组划分、冻结→P/Flat/Graph比较。来源审阅可以否决不安全输入；不能根据目标类别补事实、挑边或决定条件节点有无。

`corpus_inventory`排除SEALED正文并记录暴露历史；`rule_templates`绑定独立来源及适用范围；`input_partition`保存可逆原文子跨度，局部隔离错误对象及依赖；`target_adapter`只决定哪些目标进入损失；`graph_builder`只接收输入；`text_cache`编码全部节点文字；`application_models`为Flat与Graph提供相同节点、状态及有向三元组；`train_eval`负责整纠纷组划分、局部mask、组均损失与评价。

图含Issue、Rule、Condition、Fact、Evidence、Entity。来源关系与程序候选连接分开；候选事实/证据—条件边没有支持或反对标签。模型复用同一ID或有关系边不等于法律证明。真实组内canonical尚未取得，当前只复用本地native输入合同，不称为组内上游完整集成。

SATISFIED/DEFEATED/UNRESOLVED分别表示目标条件被确立、没有确立、或法院明确分析后仍因证据无法确定。DEFEATED保留证明责任与相反事实等依据类型，不能等同现实事实为假。NOT_DECIDED、审阅不确定、输入缺关键文件或引文失败均为null+mask=false。当前没有UNRESOLVED监督，未观测类别的召回报告null。

引用定位只支持原文连续片段与唯一可逆空白映射。缓存中的已知citation显示包装可以映射到相同引用标签，原始范围及hash保留；不能删除页脚、重写法律字词或拼接不连续句子。原始任务/模型提议、审阅决策、派生mask和地址修复谱系分别保存。

运行入口为项目MLX环境执行`scripts/irac_application_study.py`：`prepare`、`prepare-inputs`、`import-inputs`、`prepare-targets`、`prepare-reviews`、`admit`、`encode`、`freeze`、`train`。网页工作已完成，不应仅因阅读本说明再次提交。E5编码在`.runtime/irac-e5-v1`独立环境；Flat/Graph训练在`.runtime/qwen35-v1`，不调用Qwen语言模型。`scripts/report_irac_application.py`仅从已保存结果生成报告，不重新训练。

训练固定三折、三种子、内部验证早停、18拟合。权重和向量缓存只在本地，冻结JSON保存其hash；仅靠公开审阅包不能字节复算缺失的私有缓存，但可以用固定encoder revision重新编码检查。开发数据及模型参考不是人工gold，纠纷关联未完全确认，SEALED不读。

结果见中文报告及training/summary.json：Flat三个种子全猜成立，Graph无额外收益，三个DEFEATED均漏检；反例集中于一折而该折拟合没有反例。此结果不支持扩大GNN，也未证明Flat具备案件条件化能力。下一阶段应由用户另行授权，优先研究真实相反条件监督与输入覆盖，不能自动调参或启封测试。
