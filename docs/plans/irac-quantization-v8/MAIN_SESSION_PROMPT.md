# 主 session 执行任务：IRAC V8，同一 Qwen 9B 的 4bit／8bit 有界开发对照

用户已授权实施后续步骤，并要求 side conversation 将完整任务发送给主 session。请直接完成下面限定的准备、运行、一次来源审阅与交付；不要只返回计划，也不要追加其他研究轮次。

## 目标与现状

本轮只回答：在相同案件、法律材料、实际提示、Schema、模型系列、thinking 和生成设置下，将现有4bit发布版本换成同系列8bit发布版本，能否减少已经观察到的决定性来源误读，同时保留主要反对依据，且资源成本可接受？

这是一项两案开发诊断，不是模型排行榜、独立测试或完整法律准确率测量。8bit仍是量化模型；不能把它当作无量化真值。V7网页回答只作既有背景，不能作为gold或受测输入。改善也不能自动归因于参数规模。

现有发布已完成：仓库 https://github.com/ChanStormstout/legal-fact-benchmark ，分支 research/rules-and-verdict，提交 d5d88fee7d39e1c91ace8727412b120fc2e82506。不要重复提交此次发布。发布后新增的本任务文件及CHANGELOG说明目前只在本地。

先查正在运行的任务及已存在的完全兼容结果；能够复用的直接复用。不要干扰其他任务，不并行加载两个模型。保持已有未提交修改、无关未跟踪文件及全部旧结果原字节。

## 一、只做一次集中准备

首先阅读 README.md、docs/PROJECT_STATE.json、review/START_HERE.md，再定向读取：
- outputs/irac-semantic-interface-v6/report-zh.txt、freeze/config.json、environment.json、final-source-review.json；
- 上述目录 runs/112400/A/ 和 runs/188721101/A/ 的实际 prompt.txt、schema.json、rendered.txt、effective-parameters.json、run.json、result.json、raw-response.txt；
- outputs/irac-web-crossmodel-v7/report-zh.txt 和 final-source-review.json；
- scripts/irac_semantic_v6_run.py、scripts/irac_semantic_v6.py；
- legal_bench/rules_verdict_v1/runtime_constraint_diag_v1.py、legal_bench/mlx_json_constraint_v2.py 及有关现有约束回归。

报告、旧回答和错误清单只能用于实验准备与运行后评价，不得装入新模型输入。不要重审所有历史材料或重新标注事实。

登记新目录 outputs/irac-quantization-v8/，先写注册信息再保存新实验材料。记录实际HEAD、相关工作区状态及实际运行代码哈希；不切换分支或覆盖旧文件。docs/repository-artifacts.json 中注册这个输出根，权重和环境继续排除。当前研究状态应如实记录V8准备／运行／完成，不把计划写成已有结果。

### 模型与比较资格

4bit基线：
- mlx-community/Qwen3.5-9B-4bit
- revision 8b2b98c00a6b4d291155e4890773ca8f769aee53
- 复用V6中两个A实际完成的答案，不新增4bit生成。

8bit候选：
- mlx-community/Qwen3.5-9B-8bit
- 固定revision 16daa4818c54ce5f5436f929d52542eb65bbed9d，不使用浮动main。
- 本次允许在项目既有模型缓存位置下载这一版本所需的权重与配置，不能安装新框架、改全局环境、下载BF16或其他模型。
- 公开元数据中两片权重总计10,426,592,423字节，约10.43GB；实际还需要配置、缓存和运行空间。先检查已有缓存、磁盘和可用内存，不重复下载。不得把这些权重纳入Git。
- 网络获取／恢复限于这个固定快照，下载等待上限60分钟；遇真实访问阻断或无法在预算内完成则保留已完成准备及可恢复状态，不循环换下载方案或模型。

side conversation于2026-10-08已读取两版固定revision的公开配置：
- 两者group_size均64、mode均affine；config顶层差异仅quantization和quantization_config中的bits（4与8）。
- tokenizer、tokenizer_config、chat_template以及processor相关文件的公开内容标识一致。
- 两个model card的base_model均声明Qwen/Qwen3.5-9B-Base。这是发布者声明，并不独立证明使用了同一原始权重SHA。

请在本轮保存这些证据并核对实际下载文件。检查配置、分词器、模板、特殊token、非量化模型结构及转换来源。不要仅凭名称断言严格控制了所有变量：
- 若存在明确的非精度结构、分词或模板差异，停止模型调用并报告不可比原因，不为运行而修改提示或模板。
- 若配置和分词器一致，但上游原始权重revision无法完全核实，可以继续限定为“两个发布量化版本的开发诊断”，明确残余混杂；不要无限追查谱系。
- V6基线运行入口、依赖版本、prompt和Schema须可核验。若当前运行时无法保持基线关键版本，报告障碍，不升级环境后冒充只改精度。

这一阶段的通过条件是：能追溯两个发布版本、完整输入一致、推理入口及生成设置一致；不是要求预先保证8bit会答对。

## 二、最小入口适配，不能改任务或模型语义

现有 runtime_constraint_diag_v1.Runner.__init__ 将model和revision写死为4bit，并检查本地snapshot路径。直接换权重路径会失败。请新增版本化薄适配入口，例如 runtime_quant_v8.py 和 scripts/irac_quantization_v8.py：
- 保留原入口文件和冻结快照；不能全局monkey-patch SETTINGS、删除revision核验或放开所有模型。
- 新入口显式只接受本轮冻结的8bit模型及revision；保持原Runner的render、run、SchemaMask修复、greedy生成、token记录、重复保护、错误保存和格式验证行为。
- 尽量继承已有render/run等方法，仅处理加载时的model/revision配置差异及新输出目录。若必须复制少量加载逻辑，保存差异及代码哈希。
- 不改证据用途、对象连接、法律规则、回答字段、枚举、输出顺序、few-shot示例或提示内容，不修复模型产生的语义错误。
- 核对实际运行路径确实使用已发布的复合引号Schema约束修复；保留同一字段内至少64字符相同片段出现四次的重复止损，出现位置不必相邻。不得将其写成“连续重复”，也不得放宽阈值。

工程验证集中做一次：复用直接相关的约束回归，新增必要的薄适配测试，核对错误模型／revision被拒绝、参数实际传入、旧输入不变及失败答案为null。只做相关确定性测试和分词器检查，不运行无关全套、不新增模型预跑或问候式warmup。相关测试未通过不能生成；不能将跳过测试写成通过。

## 三、输入与配置一次冻结

只运行112400、188721101的直接回答A，不跑P、B、C、GNN或网页。

逐字复用各自V6 runs/<case>/A/prompt.txt 与 schema.json；不要用当前模板重新生成、插入旧错误提示或缩短案情。案情、法律包、示例、来源编号、排序和回答要求均不变。

在首次生成前，一次保存两案的实际prompt／Schema、完整允许来源映射、基线回答路径及哈希、代码快照、权重revision／文件哈希、环境版本、实际参数、调用顺序和下述评价／停止规则。来源和法律包不补充，SEALED不读取。

使用项目现有 .runtime/qwen35-v1/ 环境，关键参数固定为V6实际值：
- MLX-VLM 0.7.4、LM Format Enforcer 0.11.2；其他依赖与V6实际环境逐项记录；
- temperature=0、top_p=1、top_k=0、min_p=0、repetition_penalty=1；
- seed=20261001、enable_thinking=false、prefill_step_size=256；
- 文本输入，image/audio/video均不提供；
- constraint_mode=FIXED，max_tokens=3072，总输入输出预算32768。

运行前比较最终rendered prompt字节及输入token IDs（至少保存哈希和数量）与V6基线。若旧记录没有输入token IDs，可以用已确认相同的tokenizer从旧rendered prompt确定性重建，并明确标记重建。按实际框架tokenize路径计算，不只统计裸prompt。完整输入加3072超预算则记INPUT_TOO_LONG，不截断或改摘要。

检查实际聊天模板仍关闭thinking，确认mask入口生效。所有实际差异在生成前记录；不要在第一案结果出来后调整第二案。

## 四、固定两次生成与失败边界

顺序固定：
1. 112400：8bit A，一次。
2. 188721101：8bit A，一次。

最多两次新本地生成，网页0、付费API0、重试0、额外诊断生成0。每次最多3072输出tokens，总生成时间20分钟，单次使用剩余总预算且最多10分钟；另行记录权重加载、下载与准备时间，不把它们混成生成耗时。

一次只加载这一个模型，两案顺序运行。复用同一已加载实例可以，但应按旧入口重设种子、清缓存并记录每次内存统计口径。不得同时加载4bit以作临时对照，不修改系统内存设置或关闭用户其他应用。

单案格式失败、输出截断或重复中止只记该案技术失败；环境正常时继续另一个独立案件。OOM、框架故障、真实存储错误或总时间耗尽则停止剩余位置并记SKIPPED。技术失败的answer为null，不能用UNKNOWN/UNRESOLVED补位。

保存原始文本、实际token IDs、finish_reason、实际参数、输入／输出tokens、耗时、可观测峰值MLX内存及进程内存、解析状态和完整错误。内存统计口径需与V6一致；进程峰值若跨两案累计必须说明。不得删除重复、补JSON、修内容或用网页答案替代。已经开始的尝试不得覆盖或悄悄重试。

## 五、两次结束后，只做一次集中来源审阅

审阅范围是两案4bit旧A与8bit新A的完整回答及其决定性依据。V7网页A只作为既有背景，不是标准答案。先对照原始允许来源，既检查主动引用的段落，也检查会改变法律分析的主要反论与遗漏；不重新标注全部事实。

以下是评价重点，仅保存在评价文件，绝不写进受测prompt：
- 112400：是否将租赁记录扩大为住宅用途已明确；是否将某处现住房不适宜扩大为没有其他适宜住所；是否保留下级认定与后续发回报告的不同阶段；是否让家属缺口阻断本人择一路径。
- 188721101：是否区分起租和具体处分时间；是否保留邻居证言、经营／钥匙承认及工资凭证未证明等反论；是否区分父亲／弟弟安排、同意主体及法院层级。
- 两案共同：对象、日期、陈述状态、规则适用、否定与择一条件、明确事实与真正法律缺口、判断／理由／最终标签是否相容。
- 检查8bit新增的重要错误或遗漏；不能只看它是否消除了预先知道的错误，也不能因答案更长、更保守或JSON成功就记为改善。

参考仍标记“模型辅助来源审阅，非人工gold”。来源有合理解释争议就保留；若既有审阅确需纠正，新增修订记录并对两版回答统一应用，不能修改旧审阅字节。

逐案给出：8bit净改善／实质接近／变差／技术上无法比较，并写具体原文依据。不得计算两案法律准确率排名或将未知减少当作准确率提高。两次greedy生成、两案已暴露材料不足以估计稳定泛化或随机波动。

## 六、交付及投入决定

交付中文简报、逐案比较表、两份新答案及完整raw／prompt／Schema／运行记录、模型与输入一致性核对、必要测试、基线来源及哈希、下载和运行成本。表中分开技术完成、来源正确性、重要遗漏、新增错误、法律缺口、最终结论、tokens、耗时与内存。

明确选择一项有限结论：
- 两案8bit均有可核查净改善、无同等严重新增错误且成本可承受：8bit是后续本地工作的候选；说明这是精度／发布版本影响的支持证据，不宣布根因已唯一定位。
- 没有清楚净改善：停止围绕这两个案件扫量化、prompt或thinking；继续把已较可靠的网页直接回答作为当前开发基线，不立即加结构化/GNN组件。
- 两案方向不同：结论混合，不选普遍赢家，不追加第三案。
- 技术失败或不可比：只报告这份配置未完成有效对照，不能推论9B或量化路线无效。

即使8bit改善，也不能据此证明P或GNN有效；即使8bit无改善，也不能严格排除所有量化误差。此次没有BF16真值对照，没有训练新模型，也没有验证新案件泛化。

更新README、项目状态、CHANGELOG、实验目录与本地审阅包，保持 docs/repository-artifacts.json 的current_review和生成状态一致。完成prepare、检查发布清单和verify；旧输出及冻结快照不能改。模型权重、缓存、环境及SEALED不发布。

用户此次要求的GitHub推送已经完成。本轮新实验完成后只本地交付，不自动再次提交或推送。

完成最多两次生成和一次集中来源审阅后停止，不自动开启下一轮；不要扩大案例、法源、标注、模型或参数搜索。

