# IRAC-native 数据与输入图 V1

本阶段从现有案件数据库重新发现候选，不继续修复旧八案。范围仍是 Delhi Rent Control Act §14(1)(b)，规则作为给定信息，不评价规则检索。数据库的历史裁判字段只服务候选发现；不能直接复制为未来模型输入。

## 数据顺序与边界

先固定最多16个候选，再独立筛查。至少六个符合条件的候选才启动最多八案的构建。构建按独立规则拆解、阶段划分、盲绑定、目标构建、独立来源审阅的顺序执行。规则拆解任务只看争点和独立法源；盲绑定只看冻结的规则、条件及获准的来源记录。目标只能在全部盲绑定冻结后单独构建。每一步另存原始回复和冻结哈希，不用审阅意见反复修订直到通过。

`inputs/<case>.json`、`targets/<case>.json` 和 audit 文件分开。来源引用使用多个独立 `{source_id, quote}` 对象，每项引文单独连续。定位只允许空白等价，不修正OCR、否定或引文含义。

## 可执行接口

`legal_bench.rules_verdict_v1.irac_native_schema_v1.load_input(path)` 读取并校验 input；错误抛出 `ContractError`。`input_from_case` 是显式拆分接口，只读取 envelope 中的 `input`，不修改 input 内部字段，也不读取 target。`validate_targets` 是独立监督审计入口，不能用于图特征。

`legal_bench.rules_verdict_v1.irac_graph_builder_v1.build_input_graph(input_record)` 只接受 input。节点包含 Issue、Rule、Condition、Fact、Evidence、Entity；边只使用有来源的明示关系和冻结的模型候选绑定。图中保留 CLAIMED、PRIOR_FOUND、UNKNOWN 等状态。候选 SUPPORTS 表示“该记录如成立，其方向支持此条件”，不代表法院采纳或条件满足。

所有来源和记录执行同一阶段许可。允许 PRE_TARGET_RECORD、PRIOR_COURT_FINDING、TARGET_STAGE_PARTY_ARGUMENT；禁止 TARGET_COURT_REASONING、TARGET_DISPOSITION、AMBIGUOUS。下级法院认定保留法院层级，不提升为目标法院认可。排除对象后，依赖对象的记录递归排除，原记录与原因保存在 audit。缺失对象不会被补造。

input 根对象字段固定，target/audit 字段禁止进入；阶段 sidecar 只保存 policy_version，其余阶段信息保存在具体记录。节点只使用阶段、陈述状态、对象类型、当事人角色、法院层级、极性、可获得性、来源标记和文本。未实现编码、训练、梯度或模型评测。

## 验证的含义

相关单元测试覆盖 target 隔离、改变 target 不改变图哈希、阶段许可、级联端点排除、绑定状态及来源不变、独立规则来源、分段引文、UNKNOWN 保留、举证失败与事实为假的区别。合成 fixture 只用于接口验证，不能计为真实案例或组内 canonical 产物。

来源定位和程序测试不验证法律含义。真实案例仍需要独立来源审阅及完整链准入；图构建成功不自动成为 READY。本轮不训练模型、不启封 SEALED、不提交或推送。
