# Legal Facts, Rules and Decisions

研究目标是从历史案件的事实、请求和争点中取得有来源的法律规则，检验这些规则能否帮助新案件
找到适用法规、法律测试及先例，并形成有依据的逐项请求或争点结论。是否将benchmark作为主要
产出尚未确定；评测材料首先服务于验证方法。仓库URL沿用原名称。

[研究方向与实验影响](docs/RESEARCH_DIRECTION.md)记录2026-10-01的用户更正。
现有三个对象关系问题属于中间表示和匹配的诊断，早期结果不构成适用法源检索、法律规则归纳或判决预测的证据；新方向的开发进度见下文。

[GPT Pro双R-GCN方案评审R2](docs/reviews/2026-10-01-pro-rgcn-v1-review.md)逐项讨论组件、
近期方法依据、现有代码缺口及实施／实验顺序，并根据反馈区分规则提取与归纳、完整绑定与独立条件、
从零训练与预训练图模型迁移。初版原样保留；这些是待实施建议，没有更换模型或启动新实验。

据此制定的[完整pipeline设计](docs/plans/rules-and-verdict-v1/PIPELINE.md)说明历史案例到规则库、
新案到法源与请求结论的全部处理步骤；[实施与实验计划](docs/plans/rules-and-verdict-v1/IMPLEMENTATION_PLAN.md)
列出组件接口、模型与预算、最多5个开发案及10个新案的推进顺序、同信息对照和停止条件。
最新[V10恢复后的同案完整比较](outputs/rules-verdict-v10-constraint-recovery/report-zh.txt)仅补跑69305的A一次，B复用兼容的修复约束输出；两边均完整生成并回答`UNDETERMINED`。[比较表](outputs/rules-verdict-v10-constraint-recovery/comparison-table.csv)与[来源审阅](outputs/rules-verdict-v10-constraint-recovery/final-source-review.json)确认A遗漏可见下级认定，B转移方式定性与原文及自身解释冲突。**本案未显示可靠的整体结构化增益，暂优先文本流程继续开发，但A也未验证正确。** 两份旧中间结果没有重抽，这不是整套方法以新约束重新运行；仅是旧案最终阶段的开发配对。本轮新调用1、网页0、重试0。本次按用户明确要求发布，历史报告的未推送描述保留为实验结束时状态。

此前[JSON约束层诊断与修复](outputs/json-constraint-diagnosis-v1/report-zh.txt)已定位一个可复现错误：自由文本快速路径屏蔽合法的字符串结束token `.",`。固定V9 B同一输入，去掉自定义约束及使用修复约束均正常生成641 tokens，输出逐字相同；旧输出在第42个token处分叉后重复。默认入口已修复，5项相关测试通过，V1–V9原文件未改。这是同一B输入的技术诊断，**没有新增A/B法律质量比较，也不证明生成的结论正确**；本轮仅更新本地审阅包，不推送。

此前[V9最终生成开发验证](outputs/rules-verdict-v9-final-examples/report-zh.txt)复用69305的V8中间结果，加入两个完整虚构示例并合并重复字段职责。A、B各运行一次最终生成，均在首个`point`中重复止损，分别输出409和99 tokens；**没有完整法律答案，这组调整在本配置下仍未解决可用性问题**。[逐方法结果](outputs/rules-verdict-v9-final-examples/comparison-table.csv)保留两项技术失败，原始输出没有补写。2次本地调用、网页0、重试0；7项直接相关工程检查通过。有限来源对照不能代替未生成的完整判断，本轮未提交、未推送。

此前[V8同案恢复比较](outputs/rules-verdict-v8-paired/report-zh.txt)已按停止规则结束：仅69305，A/B第一阶段完整，A最终回答触发同字段重复止损，B最终未运行。3次本地调用、网页0、重试0；**这份冻结配置仍未完成同案配对，无法判断方法收益**，不能推论9B或结构化方法普遍不适用。[结果表](outputs/rules-verdict-v8-paired/comparison-table.csv)保留技术失败和跳过；raw、token IDs、完整／紧凑检查及停止证据均已保存。13项相关程序测试及8项桥接测试通过。**本轮按明确要求只更新本地文件，不提交、不推送。**

此前[V7两阶段中间分析实验](outputs/rules-verdict-v7-intermediate/report-zh.txt)已按固定范围结束：三旧案、9次本地调用，A2文本笔记与B2部分事实加程序检查均由相同最终模型回答。仅2份最终回答完成，4个方法结果截断，没有同案完整配对，**本批无法判断结构化是否改善完整法律回答**。来源审阅另确认B2漏掉69305的下级认定并将遗漏传播到最终理由；A2仍混淆部分事实与法律缺口。[六个方法结果](outputs/rules-verdict-v7-intermediate/comparison-table.csv)与[原始答案入口](outputs/rules-verdict-v7-intermediate/final-answer-slots.md)保留失败，不以未知减少或JSON完成认领法律正确性。全套248项程序测试通过，网页0次、重试0次。完成轮次按[同步约定](docs/DEVELOPMENT_BRANCH.md)提交到开发分支。

此前[V2法源诊断](outputs/rules-verdict-v2/report-zh.txt)、[V3条件实验](outputs/rules-verdict-v3/report-zh.txt)、[V4归属诊断](outputs/rules-verdict-v4-attribution/report-zh.txt)、[V5身份绑定](outputs/rules-verdict-v5-attribution-binding/report-zh.txt)及[V6完整流程](outputs/rules-verdict-v6-end-to-end/report-zh.txt)均保留。V7继承V6的回顾性范围限制，未新增案件、法源、规则归纳或完整法律引擎。

当前开发分支为 [`research/rules-and-verdict`](https://github.com/ChanStormstout/legal-fact-benchmark/tree/research/rules-and-verdict)。
规则与判决方向的代码、文档及新实验在该分支更新；`main`保留已有发布版本。
[分支与同步说明](docs/DEVELOPMENT_BRANCH.md)记录开发起点及审阅方式。

**当前状态：开发验证，整体可靠性尚未验证。** 此前关系任务的完整A/B比较使用固定的 Qwen3.5-9B-4bit，在8案、13道预定题上
比较直接回答与“抽取后执行”。A全部完成，B一案输出截断；相对模型参考答案，5道正例
均未识别。格式约束已让大部分输出可执行，但事实抽取仍有遗漏、状态与对象混淆。
现已完成上述V10同案最终阶段比较：完整生成已恢复，决定性语义错误仍存在；没有独立测试准确率或可靠预测结论。

后续[v10开发诊断](outputs/local-qwen-pattern-eval-v10/report-zh.txt)把完整来源按事实类型拆开抽取，再逐对象对判断关系：
2案6题，两个MATCH经原文检查有1个得到支持、1个转租类型错误，另4题UNKNOWN。
已得到第一个有来源支持的本地端到端匹配；不能据此声称整套方法有效。失败版本与修改均保留，
详见实验索引。v10使用额外调用，不是同预算比较或独立新测试。

从 [ChatGPT审阅入口](review/START_HERE.md) 开始；
[当前状态](docs/PROJECT_STATE.json)、[实验索引](docs/EXPERIMENT_INDEX.md)、
[早期关系任务中文报告](outputs/local-qwen-pattern-eval-v3/report-zh.txt)、
[全部13题结果](outputs/local-qwen-pattern-eval-v3/scoring/results-table.csv)
提供可追踪的当前信息。旧README保存在 [archive](docs/archive/workspace-readme-pre-github.md)。

## 方法与边界

固定三个问题：法院认定的转租部分是否属于文书记载拥有的整处房产；另案提起人是否
属于腾退被请求人群体；个人或机构租户是否属于该群体。对象身份、角色、陈述状态和
方向分别保存。未知只阻止依赖相应字段的计算；不相关的已知事件类型可先被排除。
个体身份相等不能替代群体成员关系，集体行为不能自动分配给个人。

A：同一模型直接读完整判决并回答。B：同一模型抽取结构化事实和关系，再由声明式
执行器回答。JSON生成约束只保证格式，引用能定位不代表事实正确。参考答案由普通
High网页模型读取原文生成并经来源复核，不是人工金标准。技术失败的答案为null，
UNKNOWN是实质信息不足。NOT_FOUND仅指给定材料/记录中未找到，不证明现实中不存在。

## 代码与数据

| 位置 | 内容 |
| --- | --- |
| `legal_bench/` | 表示、字段依赖、关系执行、抽取格式与校验 |
| `scripts/` | 版本化实验入口、分析与仓库同步 |
| `tests/` | 确定性程序语义及格式测试 |
| `outputs/local-qwen-pattern-eval-v3/` | 冻结配置、来源、参考、原始输出、执行轨迹与报告 |
| `outputs/` 中其他已登记目录 | 先前开发、诊断和算法设计文档 |
| `review/` | 同步生成的网页审阅入口、代码/结果/完整来源分卷及哈希 |

核心使用Python3.9+标准库。MLX依赖仅在生成阶段需要，普通测试和阅读结果不加载模型。

```sh
git clone --branch research/rules-and-verdict https://github.com/ChanStormstout/legal-fact-benchmark.git
cd legal-fact-benchmark
python3 -m unittest discover -s tests -v
python3 scripts/repository_bridge.py verify
python3 -m legal_bench --help
```

模型固定为 `mlx-community/Qwen3.5-9B-4bit`，revision
`8b2b98c00a6b4d291155e4890773ca8f769aee53`，MLX-VLM0.7.4。
参数及资源结果见最新报告；完整预算边界未经过验证。
[数据与运行前提](docs/DATA_AND_PORTABILITY.md) 说明克隆后包含哪些数据、缺少哪些环境、
哪些历史脚本保留机器专用路径。已完成的实验不得直接覆盖重跑。

## 与 ChatGPT 网页版协作

把 [review/START_HERE.md](https://github.com/ChanStormstout/legal-fact-benchmark/blob/research/rules-and-verdict/review/START_HERE.md)
和 [审阅请求](review/REVIEW_REQUEST.md) 给网页对话。连接GitHub后按需读取，未连接或链接
读取不完整时，下载review目录中的Markdown分卷并上传。每次让审阅者注明内容快照编号，
避免拿旧结果评当前代码。[协作说明](docs/CHATGPT_REVIEW.md) 包含读取与反馈路径。

```sh
# 生成最新文档、审阅分卷和文件哈希，不提交、不推送。
python3 scripts/repository_bridge.py prepare
python3 scripts/repository_bridge.py verify
# 生成本地ZIP，不启动模型。
python3 scripts/repository_bridge.py export
# 明确发布已授权的更新：生成、核验、按白名单提交并推送。
python3 scripts/repository_bridge.py sync --message "Describe the concrete change"
```

历史来源、标注、失败输出、配置与快照保留原字节。数GB中间轨迹、模型权重/环境、
第三方论文副本和浏览器界面文件留在本地；新增输出目录先登记再同步。
公开仓库本身不会自动把网页聊天或本地修改同步回来。
