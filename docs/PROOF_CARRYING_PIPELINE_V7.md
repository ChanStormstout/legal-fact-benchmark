# 完整推理重建流程 V7

本版交付统一的研究流程入口。它把已经实现但分散的来源、模型任务、回复导入、研究审阅政策、图、推导凭据、独立检查、解释与版本修正接在一起。没有新增组件收益实验、模型调用、案件、法源或训练；历史三份教学判决和五份校准材料用于整条流程的集成运行。

这是一条包含外部模型与明确审阅输入的工作流。网页模型通过自包含任务文件和原始回复导入接入，当前没有后台自动操纵 ChatGPT 的服务；来源语义和法律批准也不会由程序自动补齐。运行入口不会把这些人工或外部步骤伪装成自动完成。

## 一个入口及其数据流

入口为 `scripts/proof_pipeline_v7.py`，实现位于 `legal_bench/proof_carrying/workflow_v7.py`。独立检查仍调用原 `scripts/check_realcase_certificate_v4.py`，没有把检查逻辑复制到提议引擎中。

1. **来源导入。** `init` 接收 case spec，包含案件及阶段、固定问题、允许来源索引、原始来源路径和哈希。核对文书身份、原始段落、原文位置与文本一致性，复制来源并保存 source map。已有来源中的空白行原样保留。来源引用有效不等于语义正确。
2. **模型任务与原始记录。** 从相同完整来源生成规则、独立规则审阅、事实、独立参考和推导任务。依赖未满足的任务不装配；独立参考不接收事实、规则草案、推导或检查结果。每份实际任务保存来源到文本的映射与哈希。缓存复用必须记录来源，不新开同名任务冒充新结果。
3. **导入与局部保留。** `ingest` 接收原始回复及传输记录，核对提交任务哈希，只允许移除外层 Markdown 围栏。不猜补 JSON、不改事实、不自动重试。可以识别的完整记录独立保留，错误记录及原始全文另存；依赖缺失保留为缺失。新参考导入按记录处理，不因第31项抹去前30项，但旧版 FORMAT_ERROR/null 原样保留。
4. **研究接受政策。** 政策与提议分别保存，消费已有按内容哈希固定的审阅决定、范围和法院评价。没有审阅时不自动接受，没有批准时不改事实状态。审阅不能通过 policy 文件重写来源、前提或规则。
5. **图与队列。** 构建来源、实体、前提、规则、步骤和请求节点，以及出处、绑定、规则应用和依赖边。只有原提议明确保存、来源地址可用的正反关系进入谱投影。正反冲突并存；逻辑依赖不转成支持票。输出来源顺序、简单顺序和谱辅助队列。没有正反边时如实保留孤立节点，不补造冲突以使图看起来有效。
6. **凭据与独立检查。** 按已保存提议生成凭据，独立进程加载固定来源、政策和规则版本，检查对象、类型、时间、依赖及现有有限逻辑。开放法律判断不因图分数而成立。可重建的法院评价标记为条件性重建；未计算、无效和技术失败分别保存。
7. **完整分析页面。** 无新增模型调用，从检查结果生成请求分析、主要反论、具体缺口和图。点击请求可追踪到步骤、规则、前提及原始段落。原模型自由文字单列为未经语义检查的提议，不能借检查状态自动获得背书。
8. **版本化修正。** `revise` 要求新目录和明确修正理由，记录父版本、组件哈希和变更；不会覆盖旧批准、来源、提议或失败。修订仍须提供新的政策记录，不自动批准。

## 使用方式

使用已存在且包含 NumPy 的运行环境，不安装新依赖：

```sh
PY=/Users/victor/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3

# 已交付案例：核验或读取已完成状态，不重复生成。
$PY scripts/proof_pipeline_v7.py verify outputs/proof-carrying-pipeline-v7/cases/789051
$PY scripts/proof_pipeline_v7.py advance outputs/proof-carrying-pipeline-v7/cases/789051

# 新工作区先按仓库要求登记输出根。spec 中的相对路径以 spec 所在目录为基准。
$PY scripts/proof_pipeline_v7.py init --spec path/to/spec.json --out path/to/new-workspace

# 外部回复只有在对应任务已装配后才能导入；同一阶段不接收第二次回复。
$PY scripts/proof_pipeline_v7.py ingest path/to/new-workspace rules \
  --response path/to/raw-response.txt --metadata path/to/transport.json

# 研究政策是独立输入，不能用参考答案文件直接代替。
$PY scripts/proof_pipeline_v7.py ingest path/to/new-workspace policy \
  --response path/to/research-policy.json --metadata path/to/policy-origin.json

# 新版本重新构建；原版本保持不变。
$PY scripts/proof_pipeline_v7.py revise path/to/parent \
  --spec path/to/new-spec.json --out path/to/new-version --reason 'Explain the documented change'
```

真实可用的 spec 示例在 `outputs/proof-carrying-pipeline-v7/inputs/789051/spec.json`。将其中已有缓存路径保留，会复用这些文件；去掉某个缓存阶段会产生相应待执行任务，不会自动新增模型调用。不要把已审阅的旧案 spec 仅改案件编号后用于其他案件。

网页回复的 metadata 至少填写 `origin` 与 `submitted_task_sha256`，后者取对应 `task-manifest.json`。另外记录真实 URL、可见模型/模式、提交及观察完成时间；不可得字段为 null，不推测型号。研究政策 metadata 记录负责人或模型辅助审阅来源，不要求虚构网页提交。

阶段可以是待输入、待依赖、导入、部分可用或格式失败。最终 `DELIVERED` 只表示完整工作流产物已保存；应另看每项请求的 `draft_status`、`answer`、假设、错误和批准状态。缺少政策也可输出图及明确的未完成请求，不会因此批准前提。完成后不能原地导入新政策，须用 `revise` 建新版本。

## 本次完整集成交付

八案、23项已有请求进入统一入口，保存源文映射、提议、政策、图、审阅队列、凭据、独立检查和分析页面。20项条件性重建、2项研究假设下显式组合、1项计算未完成；这些是旧材料经统一入口恢复的状态，不是新增能力成绩。三份Guide案例保留旧模型推导；五案校准保留维护者组装推导，不能混称模型生成。

两次集成失败也保留：第一次因旧校验器不支持整数版本导致规则隔离；第二次误把同一规则不同版本视为重复。实际交付代码增加版本类型校验、按 `id@version` 识别规则，未改变法律规则或原始输出。它们属于实现错误修复，不是语义调参或组件实验。

三项完整入口检查覆盖缓存到交付、空工作区到任务和回复导入、不可变重开与修订、来源冲突，以及全部旧规则版本的无损导入。八案实际运行与历史文件核验完成；1205份旧记录字节未变。源码、失败尝试与实际交付分别保存。

## 仍需明确的人机边界

该实现不等于30/10/20试点已完成，不自动授予法律批准，也不计算尚未实现的开放法律评价。谱队列已接入，但本轮没有评价其法律任务收益。新的网页生成和真实法律审阅通过固定接口进入；本轮全部复用缓存，没有把人工组装改名为模型能力。后续工作可以围绕完整工作流推进，无需先证明每个组件胜出。

当前交付入口：`outputs/proof-carrying-pipeline-v7/index.html`；实际运行源码冻结：`freeze/implementation-03/config.json`。页面仅为本地文件，没有部署、提交或推送。
