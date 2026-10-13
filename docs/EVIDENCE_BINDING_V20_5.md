# V20.5：非空证据与对象绑定验收

这是支线中授权实施的独立修复版本。它复用 V20.4 的局部编号约束，
没有替换主线程的当前实验入口，也没有恢复原批次。

原文、原 SRC 编号、旧提议、标签、失败记录及冻结源码保留。
原文仍完整保存并进入准备好的模型输入，供模型和人工读取；
空白行仅从生成时的可选证据引用中排除，编号不重新排列。
旧错误答案不删除引用、不改编号、不补猜对象。

生成 Schema 的来源选项排除空白文本。每个角色的编号仍限于本单元
实际声明的对象；明确的对象类型冲突会在生成时拦截。
类型依据为已有规则类型，或 original_variable_descriptions 中的完整、
精确通用类型描述。新增五个有限描述别名见代码 TYPE_ALIASES；
不按角色名称、人物名称、子串或相似度推断类型。
类型不明确时保留未决，UNMAPPED 始终可用于尚未建立的角色绑定。

生成后的独立检查重新计算局部编号范围、来源是否非空、
必需证据的原文定位、类型冲突和绑定核对状态。
编号存在、类型相容都不建立身份对应关系。
每个实际绑定需要单独的来源核对，覆盖用途和判断中的角色。
核对记录带提议、完整来源和规则哈希，以及对应绑定的内容哈希；
过期、重复、缺少依据或内容不符的记录不开放自动计算。

审核状态分别报告：

- REJECTED_EVIDENCE_OR_BINDING：引用或类型有确定错误；
- NO_ANALYZED_UNITS：目录完整，但没有已分析单元；
- BINDING_REVIEW_REJECTED：来源核对明确不支持绑定，不改写原提议；
- BINDING_REVIEW_PENDING：存在尚未完成来源核对的绑定；
- READY_FOR_CONDITIONAL_PROCESSING：具备进入条件性处理的工程条件。

新入口 gate.process_saved 只对最后一种状态调用原转换、合并和独立检查。
其他状态保留原始候选供人工查看，formal_answer 为 null，条件计算未运行。
这不是把技术失败写成 UNKNOWN。进入原入口之后，用途的有效、无效、
模型拒绝和未决数量又单独报告，处理完成不等于用途有效。
所有结果仍为模型提议或模型来源核对，不授予法律批准。

现有 Q 来源核验可通过 reviews_from_q 转成绑定审核记录。
调用者必须传入实际冻结记录中的 original_P_sha256、source_sha256、
rule_sha256 和 run_status=OK；输入不一致或调用未完成时不接受。
该适配器只读已存在的核验结果，不调用模型。
直接传入 reviews 时，格式如下；路径索引从 0 开始：

    {
      "payload_sha256": "...",
      "source_sha256": "...",
      "rule_sha256": "...",
      "verdicts": [{
        "path": ["analyses", "R1.P1", "uses", 0, "role_objects", "tenant"],
        "claim_sha256": "...",
        "label": "SUPPORTED",
        "refs": ["SRC:1"],
        "reason": "来源核对理由"
      }]
    }

claim_sha256 来自 binding_claim；另外三个哈希来自当前完整数据。
SUPPORTED 和 UNSUPPORTED 需要非空、允许且非空白的来源地址；
UNRESOLVED 可以没有来源，但不能被当作支持。审核依然是外部、
可错的语义判断，不是程序证明或独立人工金标准。

准备好的四项任务位于 outputs/proof-evidence-binding-v20-5/preparation-02。
完整来源尾部与旧提示词逐字相同。旧“解码器不保证编号存在”说明被替换；
示例改为两个都有内容的分析单元，显示 EV/OBJ/USE 局部编号重启。
新运行适配器为 local_runtime_v20_5.Runner。技术生成结果还必须交给
evidence_binding_gate_v20_5.accept_saved；它把验收结果保存到另外的目录，
不会改生成目录。

命令入口：

    .runtime/qwen35-v1/bin/python3 -B scripts/proof_evidence_binding_v20_5.py verify
    .runtime/qwen35-v1/bin/python3 -B scripts/proof_evidence_binding_v20_5.py accept --case-id CASE --part PART --input-dir DIRECTORY --reviews REVIEW_JSON

命令没有生成或恢复队列的选项。本轮没有真实模型重跑、训练、Q 调用、
网页提交、commit 或 push。真实新输出的对象匹配和法律语义改善尚未验证。
