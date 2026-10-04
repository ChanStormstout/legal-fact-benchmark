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
当前发布包括[V22范围核对](outputs/rules-verdict-v22-scope-preparation/report-zh.txt)及V23准备检查点：两份普通租约已决定另设开发组，不并入原第14(1)(b)条实验。V23第一批S01的六项描述及原始回复已保存，结构可读、语义未复核，统一索引未生成，最终A/B回答均未运行。用户要求先发布当前代码及记录供整体科研审阅，详见[完整Pro审阅prompt](docs/reviews/2026-10-03-pro-research-design-review.md)。旧轮报告的“待范围选择”与“未推送”保留为历史状态；它们不代表此发布后的执行状态。

此前[V21检索实现与样本盘点](outputs/rules-verdict-v21-rule-retrieval/report-zh.txt)完成双路线检索、原文依赖恢复与软限制导入。7项相关测试通过，但限定盘点未确认合格未暴露新目标，**新案比较未运行，不能评价检索或完整回答收益**。当前已实现的数据流程见[实际pipeline](docs/plans/rule-retrieval-v21/PIPELINE.md)；它与前述历史设计建议分开。银行规则卡覆盖、历史版本与完整上下文预算仍有限制；本轮只在本地交付，不提交或推送。

此前[V20四案配对实验](outputs/rules-verdict-v20-four-case-pairs/report-zh.txt)在用户批准的小试范围内完成四案12次普通High回答，包括提前选定的两案重复。**基本配对B净改善2案、A/B接近1案、无法判断1案；没有确认B变差，但不能据此估计总体优势。** 12份文字保留、10份通过Schema，39942283两次A超出引用数组上限，正式答案为null。改善集中在历史规则的前提与范围，书面同意证据、下级观点遗漏和银行法覆盖问题仍在。公司合并重复方向保持；银行配对无法正式判断稳定性。见[比较表](outputs/rules-verdict-v20-four-case-pairs/comparison-table.csv)、[完整回答](outputs/rules-verdict-v20-four-case-pairs/final-answer-slots.md)、[集中来源审阅](outputs/rules-verdict-v20-four-case-pairs/final-source-review.json)及[重复记录](outputs/rules-verdict-v20-four-case-pairs/repeat-stability.json)。保留规则补充作为限定范围的候选，不增加强制卡或结构化阶段；非独立测试、非人工gold、不验证自动检索或归纳。本轮结束，仅本地更新审阅包，不提交、不推送。

此前[V19跨案件配对准备](outputs/rules-verdict-v19-historical-pairs/report-zh.txt)按固定窗口盘点24份候选（已有16份、新增8份），最多确认5份法条／争点范围相容候选，其中1份还受答案隔离限制。**少于预定6案启动门槛，本轮未运行A/B网页回答。** 没有收益分类、重复稳定性或成本比较结果，不据此评价规则方法有效与否。见[候选清单](outputs/rules-verdict-v19-historical-pairs/candidate-list.csv)、[逐案依据](outputs/rules-verdict-v19-historical-pairs/candidate-decisions.json)及[停止记录](outputs/rules-verdict-v19-historical-pairs/availability.json)。没有扩大筛选、改争点、新增规则或重答旧案；历史文件原字节保留，本地审阅包更新后结束，不提交、不推送。

此前[V18适用链开发检验](outputs/rules-verdict-v18-application-chain/report-zh.txt)先核对保存来源的生成方式、实际案情切片、规则引文与适用范围及代码职责，再以相同材料加通用适用链说明运行661475、1134266各一次普通High。**1134266的HP特别法区别更明确，661475没有清楚的实质净增益；暂保留简短要求，不增加强制结构化阶段。** 两案均保留真实同意缺口，法律范围桥接及反对理由仍不足。见[逐案比较](outputs/rules-verdict-v18-application-chain/comparison-table.csv)、[完整答案](outputs/rules-verdict-v18-application-chain/final-answer-slots.md)、[数据谱系](outputs/rules-verdict-v18-application-chain/data-lineage.json)及[集中来源审阅](outputs/rules-verdict-v18-application-chain/final-source-review.json)。对旧、新回答统一修正评价：下级裁判经过的遗漏不自动等于决定性错误。3项必要工程检查通过，5200个历史文件原字节不变；这些检查不认证法律正确。网页2次、重试0，旧案回顾性比较、精确网页模型不可得；本轮结束，只更新本地审阅包，不提交、不推送。

此前[V16法源规则提取](outputs/rules-verdict-v16-rule-transfer/report-zh.txt)完成三个独立普通High任务，得到9张有出处的候选卡，并运行导入、原文恢复和既有BM25候选检索。**新案A/B应用比较未运行：现有完整候选未确认两件同类公司合并案。** 规则提取仍漏掉General Radio转述的Delhi非自愿转移规则，关键词排序将Telesound暂定意见置首；不能把可读取的卡或排名当成正确法律选择。见[完整规则卡](outputs/rules-verdict-v16-rule-transfer/rule-collection.json)、[来源审阅](outputs/rules-verdict-v16-rule-transfer/final-source-review.json)和[样本不足记录](outputs/rules-verdict-v16-rule-transfer/sample-availability.json)。三次网页调用、重试0，旧文件不改；没有跨案应用成绩，不提交、不推送。

此前[V17同材料规则卡应用比较](outputs/rules-verdict-v17-rule-application/report-zh.txt)已按[debug方案](docs/plans/rule-card-debug-v17/DEBUG_AND_CHANGE_PLAN.md)完成1134266的两个独立普通High回答：A读取共同原文，B额外加入V16九张原样候选卡，两边均保留原法律包三张历史卡。**额外卡未显示明确的完整答案净改善，暂不将其设为强制前置，优先共同原文读取与法源适用整合。** 两边保留登记租约、方案转归及判例范围限制，但共同遗漏已提供的下级法院结果；A将RBI指令的证据地位写得过实，B仅增加有限专门法区别。两份UNDETERMINED不等于法律正确。见[完整答案](outputs/rules-verdict-v17-rule-application/final-answer-slots.md)、[比较表](outputs/rules-verdict-v17-rule-application/comparison-table.csv)和[集中来源审阅](outputs/rules-verdict-v17-rule-application/final-source-review.json)。四项直接相关工程测试通过，旧文件原字节核验通过；它们不证明法律能力。两次网页调用、重试0，本轮结束，不启动后续修复、不提交或推送。

此前[V15补充规则比较](outputs/rules-verdict-v15-rule-supplement/report-zh.txt)仅在1134266增加三份有出处和适用范围的早期判例，复用V14原案情、法律包、问题和示例，新开普通High对话回答一次。**补充规则带来具体法律分析增益，保留规则提取与应用方向；完整回答仍有关键遗漏。** 答案区分合并权利转归与租赁法后果、Telesound保留的腾退问题、Hindustan Petroleum依赖的专门法保护；仍未充分处理房东“降低股本可有其他路径”的反驳，书面同意未定，结论继续为UNDETERMINED。没有确认同等严重新增来源反写，但适用范围迁移和事实归属仍需限定。见[完整回答](outputs/rules-verdict-v15-rule-supplement/final-answer-slots.md)、[规则包](outputs/rules-verdict-v15-rule-supplement/rule-package.md)及[比较表](outputs/rules-verdict-v15-rule-supplement/comparison-table.csv)。这是旧案、研究者选取规则包、单次模型辅助来源审阅，不验证自动检索、跨案归纳或裁判可靠性。一次网页回答、重试0、本地生成0；本轮结束，只更新本地审阅包，不提交、不推送。

此前[V14同材料网页直接回答对照](outputs/rules-verdict-v14-web-direct/report-zh.txt)在661475、1134266各新开一个普通High对话，完整复用V13 D实际任务、Schema和各案法源，没有旧答案、参考事实或纠错提示。**网页High在两案减少明确基础来源误读，当前暂缓给9B流程增加复杂组件。** 661475正确区分起诉日期与转移日期、租户父亲与房东许可；1134266正确保留已登记租约、法院批准及ARC/Tribunal/High Court层级，未把无同意指控升级为事实。1134266仍遗漏法定强制与自愿合并的具体对抗理由；两份UNDETERMINED不等于完整正确。网页只显示ChatGPT/High，具体型号、tokens和精确生成耗时不可得，且没有本地逐token约束，不能把改善全部归因模型大小。见[完整答案](outputs/rules-verdict-v14-web-direct/final-answer-slots.md)、[逐案比较](outputs/rules-verdict-v14-web-direct/comparison-table.csv)及[集中来源审阅](outputs/rules-verdict-v14-web-direct/final-source-review.json)。两次网页回答、重试0、本地生成0；只更新本地文件，不提交、不推送。

此前[V13固定方法跨案件开发检验](outputs/rules-verdict-v13-crosscase/report-zh.txt)运行661475与1134266，保持V11 no-thinking、完整来源、法源和输出合同；六次调用全部完成。**两案收益方向不同，暂不选赢家，也不强制结构化前置。** 661475的B-P新增虚构转移日期和择一条件矛盾；1134266的B-P保留D遗漏的法院批准，避免把已登记租约读成未登记，却增加无依据的默示同意抗辩。两边仍有来源整合问题及真实法律缺口，四份UNDETERMINED不代表正确。含抽取成本分别约182/226秒，D约64/65秒。[完整四份答案](outputs/rules-verdict-v13-crosscase/final-answer-slots.md)、[比较表](outputs/rules-verdict-v13-crosscase/comparison-table.csv)和[集中来源审阅](outputs/rules-verdict-v13-crosscase/final-source-review.json)保留具体依据、错误、遗漏和争议。两个旧开发案件不构成独立测试；网页0、重试0，全部原始文件保留，本轮仅本地更新，不提交、不推送。

此前[V12 thinking开关开发对照](outputs/rules-verdict-v12-thinking/report-zh.txt)仅运行69305的D与B-P最终回答，逐字复用V11提示和同一B提议。D完整生成后日志失败，正式答案为null，保留文本仅作诊断；B-P正常完成。B-P开始保留下级转租腾退认定，却在另一项理由中称没有法院定性，仍漏掉条款可依赖的下级认定；D保留文本减少过度判断但也仍漏认定。**暂不采用thinking作为当前流程默认配置。** B生成耗时约92→504秒，推理4098＋最终760 tokens；D精确计时和峰值内存缺失。[比较表](outputs/rules-verdict-v12-thinking/comparison-table.csv)与[来源审阅](outputs/rules-verdict-v12-thinking/final-source-review.json)保留这些限制。两次调用、网页0、重试0，无新抽取或程序检查；只更新本地文件，不提交、不推送。

此前[V11修复约束下的中间分析消融](outputs/rules-verdict-v11-intermediate-ablation/report-zh.txt)在69305上固定运行六次，D直接来源、A-clean文本笔记、B-P结构化提议、B-C同提议加程序检查四个最终条件全部完成。[完整答案](outputs/rules-verdict-v11-intermediate-ablation/final-answer-slots.md)、[比较表](outputs/rules-verdict-v11-intermediate-ablation/comparison-table.csv)和[集中来源审阅](outputs/rules-verdict-v11-intermediate-ablation/final-source-review.json)显示：A-clean/B-P减少了D部分过度判断，但共同遗漏可见下级认定；加入整个检查块后B-C新增了可采性反向与观点归属错误。**当前仅保留程序离线审计，不继续把整个检查块作为最终判断输入；没有一个条件验证为可靠完整法律回答。** 推理624.2秒、网页0、重试0，928个历史文件原字节未变。D只用一次调用，其他逻辑方法两阶段，不能声称等调用预算。此为单个旧案的回顾性开发比较，本轮仅本地更新，不提交、不推送。

此前[V10恢复后的同案完整比较](outputs/rules-verdict-v10-constraint-recovery/report-zh.txt)仅补跑69305的A一次，B复用兼容的修复约束输出；两边均完整生成并回答`UNDETERMINED`。[比较表](outputs/rules-verdict-v10-constraint-recovery/comparison-table.csv)与[来源审阅](outputs/rules-verdict-v10-constraint-recovery/final-source-review.json)确认A遗漏可见下级认定，B转移方式定性与原文及自身解释冲突。**本案未显示可靠的整体结构化增益，暂优先文本流程继续开发，但A也未验证正确。** 两份旧中间结果没有重抽，这不是整套方法以新约束重新运行；仅是旧案最终阶段的开发配对。本轮新调用1、网页0、重试0。本次按用户明确要求发布，历史报告的未推送描述保留为实验结束时状态。

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
现已完成V11四条件消融、V12 thinking对照、V13两案固定方法比较、V14同材料网页直接回答、V15补充规则比较、V16法源规则提取及V17同材料候选卡应用：整个检查块仅用于离线审计，thinking暂不默认采用；V13结构化收益随案件改变，V14网页配置减少基础误读，V15补充规则改善部分法律适用分析。V16新案应用因样本不足未运行；V17仅在旧案中隔离额外九张卡的作用，未显示清楚的完整答案收益。V18逐步核对材料与代码后新增通用适用链要求，只有有限的法律范围解释改进；真实事实缺口与法源范围桥接不足分开保留。当前保留有来源规则提取与应用方向，暂不强制额外卡，暂缓复杂化9B；网页答案不是金标准，没有独立测试准确率或可靠预测结论。

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
