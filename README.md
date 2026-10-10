# 当前交付：局部接受与来源恢复 V16

完成四案缓存回归及六个固定DEV请求的来源对齐、独立审阅和D/P/R比较。实际11次普通High生成，五份完整提议、四份完整审阅；136109文件不可取得、885778审阅为空，正式结果保留null。停滞页面的其他回复从原任务取回，未重新生成。907531的限定不适用判断经共同引文修复恢复；新六案根规则均为OPEN_TEXT，尚未形成可执行的完整法律推导。

**保留局部对齐与分范围审阅，暂不恢复用途三分类训练。** 新角色范围错误只隔离对应绑定，独立判断、反论与其他用途保留；结构检查、条件性计算、研究接受与正式批准分别记录。25项相关工程测试通过，旧227项V15文件保持。见[中文报告](outputs/proof-source-alignment-v16/report-zh.md)、[最终三视图](outputs/proof-source-alignment-v16/three-views-final.json)、[来源链](outputs/proof-source-alignment-v16/walkthrough.md)及[投入决定](outputs/proof-source-alignment-v16/learning-decision.json)。未读取TEST／SEALED、训练、提交或推送。

# 历史交付：自动来源对齐与条件性推导 V15

完成四个固定DEV请求、四份自动提议、四份独立来源审阅及D/P/R视图。原P加共同确定性修复均未决；自动提议恢复396336与594273两条限定链，审阅接受后保留。121775准确区分普通期满与特殊提前终止，但未证制度主体对应使整项被拒；907531的前提获接受，既有规则引文断词仍阻止执行。见[中文报告](outputs/proof-source-alignment-v15/report-zh.md)、[来源到推导轨迹](outputs/proof-source-alignment-v15/walkthrough.md)、[投入决定](outputs/proof-source-alignment-v15/learning-decision.json)及[实现边界](docs/PROOF_SOURCE_ALIGNMENT_V15.md)。

**保留带独立审阅的来源对齐作为开发候选，不启动新训练。** 结构检查、假设下推导、模型辅助研究接受和正式法律批准分别保存；本轮不证明法律认证、泛化或GNN收益。八次普通High，重试0、新训练0，未读取TEST／SEALED，不提交推送。旧V12当前CrossEncoder种子仍按原暂停安排运行与保存，其余种子不启动。

# 历史交付：用途语义校准与两条真实推理链 V14

完成20条有限监督核对：13条合同一致、3条不同语义、3条用途不明、1条解释争议，旧标签不改。396336／594273各一条路径保留原P及来源校准版本；原P的四个用途及前提判断已为USABLE／TRUE，恢复来自角色映射、引文与外部前提接受，不能算学习模型收益。

**本轮不新增学习组件，不启动训练。** 两条限定组合在研究接受政策下可执行，正式法律批准仍缺失。四项用途翻转仅验证依赖；0新模型调用、0新拟合、未读取TEST／SEALED，不提交或推送。见[中文报告](outputs/proof-semantic-calibration-v14/report-zh.md)、[学习决定](outputs/proof-semantic-calibration-v14/learning-decision.json)、[实现接口](docs/PROOF_SEMANTIC_CALIBRATION_V14.md)。旧V12当前CrossEncoder种子仍按原安排继续保存，其余种子保持暂停。

# 历史交付：共同接口修复与DEV恢复 V13

V13完成类型／变量分离、多证据局部处理、引用原文恢复、同信息关系编码和真实入口验收；原30TRAIN及722条标签保留。冻结10DEV输入中8纠纷有195条有效用途参考，四类机制均有覆盖，但授权与阶段各仅一纠纷。13次普通High生成，无重试；两份用途审阅为空，保留null。

**V13没有启动新训练。** 原P与参考一致173/195，但参考用途替换后86项请求／规则分析仍全部未决，没有发现用途复核能影响完整链的真实路径；旧、新参考的用途口径也尚未充分认证。保留数据与接口，不把局部分类或工程通过解释为法律分析改善。见[中文报告](outputs/proof-semantic-interface-v13/report-zh.md)、[训练决定](outputs/proof-semantic-interface-v13/training-decision.json)、[实现边界](docs/PROOF_SEMANTIC_INTERFACE_V13.md)及[最终数据诊断](outputs/proof-semantic-interface-v13/final-audit-03/data-task-audit.json)。本地交付，未读取TEST／SEALED，不提交或推送。

旧V12尚未结束的CrossEncoder种子允许正常完成，保存监控继续记录；其余种子暂停。旧六次Flat／R-GCN拟合保留，仅属于旧输入下局部用途分类，不能充当V13结果。见[旧暂停诊断](outputs/proof-semantic-search-v12/continuation-02/pause-diagnostic-01/report-zh.md)。

# 历史交付：请求及当前状态条件化排序 V11

完成八案请求/状态条件化排序开发比较及12次实际拟合。Flat三种子为13/13/15项限定重建，R-GCN为12/13/13；新Simple退化至7项，不能作为强基线。全池有界检查17项约1.48秒。保留接口修复，暂不扩大GNN；无新生成调用、案件或推送。

[中文报告](outputs/proof-carrying-state-search-v11/report-zh.md)、[八案比较](outputs/proof-carrying-state-search-v11/index.html)及[监督覆盖](outputs/proof-carrying-state-search-v11/supervision/coverage.json)。每折仅两个纠纷贡献成对损失，不称独立泛化或法律认证。

# 历史交付：共同规则接口与排序空间诊断 V10

八案缓存重放：23项限定请求由8项变为15项（恢复9、撤回覆盖不足2）；仅1418721存在预算内额外1项排序见证。零模型调用、训练或权重加载，暂不扩大GNN。研究审阅政策下结果，不是法律认证。

[中文报告](outputs/proof-carrying-selection-readiness-v10/report-zh.txt)、[逐案工作台](outputs/proof-carrying-selection-readiness-v10/index.html)及[请求诊断](outputs/proof-carrying-selection-readiness-v10/request-diagnosis.json)。规则读取通用化，但新规则的映射仍须审阅；旧结果原字节保留。本地交付，不提交推送。

# 历史交付：Proof-Carrying接口与依赖修复 V9

八案缓存重放完成，零模型调用、零训练。原顺序接口修复使23项请求中的限定重建从5项增至8项；固定六候选预算的依赖选择仍为8项，无额外完整收益。保留旧结果，不推送。

[中文报告](outputs/proof-carrying-dependency-repair-v9/report-zh.txt)与[八案重放工作台](outputs/proof-carrying-dependency-repair-v9/index.html)。三项恢复有明确原文依据；依赖选择及旧宏观覆盖仍有限制，不宣称完整法律验收通过。

# 历史交付：Proof-Carrying完整流程与GNN接入 V8

完成8案16次普通High任务、12次实际拟合及64份下游交付。R-GCN已实际接入候选选择、推导和独立检查，但未显示超过简单排序的稳定完整分析收益。共同瓶颈包括角色绑定过严、引用/接受政策及预算依赖缺失；正式法律批准待定。

见[完整流程工作台](outputs/proof-carrying-graph-integration-v8/index.html)、[中文报告](outputs/proof-carrying-graph-integration-v8/report-zh.txt)、[实现对应表](docs/PROOF_CARRYING_GRAPH_V8.md)。本轮只作本地交付，不提交或推送。

# 历史交付：完整推理重建流程 V7

来源、英文模型任务、原始回复导入、研究审阅政策、类型化图及队列、推导凭据、独立检查、可追溯分析与版本修正已接入同一入口。复用8案23项旧请求完成整批集成；零新模型调用、零组件收益实验。模型和审阅通过明确的外部输入接入，正式法律批准及开放法律判断的自动计算没有被冒充为完成。

打开[完整流程工作台](outputs/proof-carrying-pipeline-v7/index.html)，查看[使用说明](docs/PROOF_CARRYING_PIPELINE_V7.md)、[中文报告](outputs/proof-carrying-pipeline-v7/report-zh.txt)和[逐案交付](outputs/proof-carrying-pipeline-v7/case-delivery.csv)。统一入口为 `scripts/proof_pipeline_v7.py`。历史结果原字节保留；本轮仅本地交付，不提交或推送。

# 历史交付：五案独立参考与条件性重建 v6

五案5次普通High独立参考完成；2份合同通过、3份31项超过30项上限而保留FORMAT_ERROR/null，完整文本作定性来源审阅。10项OPEN_TEXT请求在工程轨道未计算，在明确法院评价假设下形成10项条件性重建，均待正式批准。四项实际入口控制通过，1047项旧文件未变；不是法律认证或自动模型能力成绩。

见[报告](outputs/proof-carrying-calibration-v6/report-zh.txt)、[逐案推理链](outputs/proof-carrying-calibration-v6/walkthrough.md)及[实现边界](docs/PROOF_CARRYING_CALIBRATION_V6.md)。本轮完成研究性校准交付，正式法律批准仍待定；未提交推送。

# 历史交付：五案校准材料准备 v5

完成5案校准材料准备：按固定顺序核读9份完整判决，4份限定裁判链及1份分歧意见案，40项命题、10条OPEN_TEXT规则草案。5份英文独立参考任务保存但未提交；零模型调用、训练及正式批准。实际入口来源/合同/装配检查通过，940项旧文件保持；尚未产生本批凭据或法律验收结果。

见[中文报告](outputs/proof-carrying-calibration-v5/report-zh.txt)和[五案材料入口](outputs/proof-carrying-calibration-v5/walkthrough.md)。下一依赖是独立来源参考和接受政策；不因缺正式法律批准阻止已授权的材料整理。未提交推送。

# 历史交付：同一提议检查前后 v4

三案13项原始请求在同一来源政策下完成检查前后对照：12项条件性／显式轨迹保留，1项旧推导未完成；不能把来源审阅决定当作程序自动纠错。9项固定控制检查发现等价步骤哈希过严及自由文字展示边界，另存修订；7项测试和6项实际入口验收通过。零模型调用，旧记录保留，未提交推送。

见[中文报告](outputs/proof-carrying-checker-evaluation-v4/report-zh.txt)、[完整对照](outputs/proof-carrying-checker-evaluation-v4/walkthrough.md)及[实现边界](docs/PROOF_CARRYING_CHECKER_EVALUATION_V4.md)。保留检查与来源审阅流程，下一阶段准备既定5案校准；不扩大图算法，不将条件性轨迹作为法律认证。

# 历史交付：真实判决重建本地修复 v3

已完成三案缓存的版本化本地修复，零模型调用。工程轨道2项有效、9项计算未完成、2项无效；来源复核轨道11项条件性重建、2项显式组合，均未获正式法律批准。36项相关测试通过；不能把维护者语义修正或法院判断记录当作模型提升及独立法律证明。旧文件原字节保留，未提交推送。

见[报告](outputs/proof-carrying-local-repair-v3/report-zh.txt)、[逐项比较](outputs/proof-carrying-local-repair-v3/comparison.csv)及[实现边界](docs/PROOF_CARRYING_LOCAL_REPAIR_V3.md)。工程缺陷先修复，正式批准仅限制正式验收；条件性重建链不代替开放法律评价或检查净收益实验。

# 历史交付：真实判决推理重建 v2

三份Guide教学判决、15次普通High已完成。原始18步中5步、13项请求中2项取得研究假设下的有效轨迹；其余主要受开放性评价、引文呈现和角色映射限制，另发现Sopan规则范围错误。Rame另存S2修正；25项相关测试及17个变异场景通过，不代表法律能力。正式批准待定，检查净收益与图收益尚未建立，未训练、启封SEALED、提交或推送。

本批完成来源到独立检查的研究流程，尚未完成三案完整法律链验收。见[中文报告](outputs/proof-carrying-realcase-v2/report-zh.txt)、[可点击推理链](outputs/proof-carrying-realcase-v2/walkthrough.html)、[集中来源审阅](outputs/proof-carrying-realcase-v2/final-source-review.json)和[实现及边界](docs/PROOF_CARRYING_REALCASE_V2.md)。原始失败和冻结快照保留；5案校准与30/10/20试点尚未启动。

# 历史交付：Guide 4.0 可检查推理教学案例

已读Student Implementation Guide 4.0，完成DEMO_PERMISSION合成教学链：凭据、独立检查、错误拒绝、S1/S2版本修正及谱图数值复现。27入口场景符合预期，7项相关测试通过；真实法律批准缺失，不能作为真实判案验收。零模型调用、训练及SEALED访问；旧结果保留，不提交推送。 见[完整教学案例](outputs/proof-carrying-teaching-v1/walkthrough.md)、[中文报告](outputs/proof-carrying-teaching-v1/report-zh.txt)及[实现与边界](docs/PROOF_CARRYING_TEACHING_V1.md)。本轮先完成Guide中的合成案例，不声称已完成真实判决的经批准推理。

# 历史结果：V10 全英文四案A/P/B比较完成

V10全英文四案12次普通High全部完成，4份P、8份最终回答，零重试；E通过。集中来源审阅：B有净改善2案、接近1案、得失无法可靠比较1案。68065690新增重要反对证言遗漏，强制P门槛未通过，暂不选统一赢家，P保留可选。B流程输入约2.40倍、观察时间约2.15倍；非精确推理成本，非人工gold、非独立测试。旧结果保留，未提交推送。 见[中文报告](outputs/irac-web-english-v10/report-zh.txt)、[完整英文答案](outputs/irac-web-english-v10/answers.md)、[四份英文P](outputs/irac-web-english-v10/proposals.md)及[比较表](outputs/irac-web-english-v10/case-comparison.csv)。

# 历史检查点：IRAC V9 四案比较已提交8次，保存7份

四案已提交8/12次普通High任务，7份回答保存并导入；55384096 P页面完成但正文读取受阻，后续4个位置未提交。冻结方法和600项历史文件未变。集中来源审阅尚未开始，暂不评价P净收益；未提交推送。见[进度报告](outputs/irac-web-crosscase-v9/report-zh.txt)和[恢复记录](outputs/irac-web-crosscase-v9/resume-02.json)。

# 历史：IRAC V7 网页同接口A/B比较已完成

V7六次普通High独立临时对话完成，2份P与4份最终回答均可读，零重试。网页A/B明显减少V6来源误读及遗漏；112400 B接近A，188721101 B有逐安排组织收益但未确认重要额外净收益。优先网页A、P可选；一次模型辅助来源审阅，非人工gold，旧案开发诊断。未新增法源、执行器改动、本地推理或推送。 见[报告](outputs/irac-web-crossmodel-v7/report-zh.txt)、[完整回答](outputs/irac-web-crossmodel-v7/answers.md)、[逐案比较](outputs/irac-web-crossmodel-v7/case-comparison.csv)。

补充的[9B 4bit／8bit直接回答诊断](outputs/irac-quantization-v8/report-zh.txt)已完成：两次新生成，112400实质接近、188721101新增重要错误，没有清楚净改善。8bit增加约28%总生成耗时、62% MLX峰值内存，不能把旧问题主要归因于4bit。另已追踪[P到B的错误来源](outputs/irac-quantization-v8/diagnosis/report-zh.txt)；语义接口没有改写，P/B没有重跑。本地补充结果未提交或推送。

# 历史：IRAC V6 两案完整比较已完成

两案6次本地调用全部完成，12.44分钟，2份P及4份最终回答，无重试、网页或C。23项相关测试、17个真实tokenizer样例通过；E通过，M/L仍未通过。112400 B新增择一分支及来源问题，188721101 B局部纠错但未形成可靠完整净收益。暂停给当前9B增加提示／字段及强制P；2595项历史文件和旧IRAC源码保留，未读SEALED、未提交推送。 见[中文报告](outputs/irac-semantic-interface-v6/report-zh.txt)、[逐案比较](outputs/irac-semantic-interface-v6/case-comparison.csv)、[完整回答](outputs/irac-semantic-interface-v6/answers.md)与[实现说明](docs/IRAC_SEMANTIC_INTERFACE_V6.md)。两案仍是开发材料，结果不代表法律准确率或整个图方法的有效性；下一轮仅提出同接口更强模型比较，尚未执行。

# 历史：IRAC V5 两案完整流程验收

两案8次本地调用完成，19.31分钟，2份提议、6份完整回答，无截断或重试。22项相关测试通过，E工程验收通过；M仍有安排拆分、错误用途，L仍有极性、来源归属与法律组合问题。B局部纠错但无完整验收，C无可靠额外收益。2426项旧文件未变；未读取SEALED、提交或推送。 见[中文报告](outputs/irac-contract-repair-v5/continuation-01/report-zh.txt)、[E/M/L验收](outputs/irac-contract-repair-v5/continuation-01/acceptance.json)、[完整回答](outputs/irac-contract-repair-v5/continuation-01/answers.md)和[逐案比较](outputs/irac-contract-repair-v5/continuation-01/case-comparison.csv)。这是旧案例开发验证，不是独立法律准确率测试。原[V5工程检查点](outputs/irac-contract-repair-v5/report-zh.txt)原样保留。

# 历史：IRAC 流程集中修复与有界恢复 v4

局部导入、分支目录和来源组织修复完成；16次本地调用、2409.5秒，10份最终回答与两诊断完整，112400提议截断致B/C跳过。52547606 B有局部收益，其他配对传播或新增错误，C无稳定净收益；保留工程修复，暂停增加字段与图组件。未读取SEALED、训练、提交或推送。 见[报告](outputs/irac-pipeline-repair-v4/report-zh.txt)、[比较表](outputs/irac-pipeline-repair-v4/case-comparison.csv)、[来源审阅](outputs/irac-pipeline-repair-v4/final-source-review.json)和[实现说明](docs/IRAC_PIPELINE_REPAIR_V4.md)。这是材料与接口共同修改后的开发验证，不是独立测试。

## 历史：IRAC 局部依赖与明确决策 v3

六案16次本地调用完成：10最终回答均预测拒绝，8位置依赖失败跳过。局部用途和OR修复接通，但两份提议因覆盖门槛失败、两份截断；两完整配对仍有极性／来源误读，188721101全部用途分支地址错误。暂不增加组件，不宣称完整分析已修好。 17包旧预测重放不修改概率；未读取SEALED、未新训GNN、未调用网页、未提交推送。见[报告](outputs/irac-hybrid-decision-v3/report-zh.txt)、[六案比较](outputs/irac-hybrid-decision-v3/case-comparison.csv)、[完整答案入口](outputs/irac-hybrid-decision-v3/final-answer-slots.md)和[实现说明](docs/IRAC_HYBRID_DECISION_V3.md)。这是已暴露材料上的开发验证，来源审阅为模型辅助判断。

## 历史：IRAC 对齐 v2

本轮已完成17包、16次普通High、24次真实拟合及六包集中来源审阅。绑定读出、保存入口、划分与法律元数据已修复；局部限制跨见证及择一分支仍有过度阻止，完整分析未验收为已修好。四种学习方法均未稳定超过条件先验，暂停扩大GNN，保留来源与绑定接口。见[本轮报告](outputs/gnn-irac-aligned-v2/report-zh.txt)、[逐案比较](outputs/gnn-irac-aligned-v2/case-comparison.csv)、[集中来源审阅](outputs/gnn-irac-aligned-v2/final-source-review.json)及[实现说明](docs/IRAC_ALIGNED_V2.md)。旧结果、SEALED和GitHub均未改动。

历史[老师方案对齐版报告](outputs/gnn-irac-aligned-v1/report-zh.txt)：17包、58次普通High、96/117项材料参考；36拟合已保存预测但权重/训练日志导出失败，原失败保留，未重训。该轮未显示Flat/R-GCN及ANCO超过条件先验；请求级门槛及训练覆盖问题限制了结论，不能视为充分的图方法有效性检验。保留来源接口，暂停扩大图。非独立测试、非人工gold，SEALED未读，未提交推送。 [逐案审阅](outputs/gnn-irac-aligned-v1/case-comparison.csv)与[实现对应](docs/IRAC_ALIGNED_V1.md)。

历史[给定规则的条件适用开发报告](outputs/gnn-irac-application-development-01/report-zh.txt)：完成17个真实问题图、8组13项条件弱监督和18次Flat/R-GCN拟合。Flat三个种子全猜成立，Graph未识别三个不成立，概率损失明显差于条件先验；本轮没有图传播额外收益证据。保留接口，暂停扩大图。监督覆盖13/102，第三类无样本，反例集中于同一折；不宣称法律准确率或独立泛化。34次普通High，SEALED未读，未提交推送。

历史[IRAC-native候选发现与图接口报告](outputs/gnn-irac-native-data-01/report-zh.txt)：固定16个新候选、4次普通High筛查完成：1 SUITABLE、3模型认可BORDERLINE、12 REJECT。即使全部暂计边界案也只有4案，未达到六案construction门槛，IRAC_NATIVE_DISCOVERY_NO_GO。新input schema及target-free图builder实现，33相关测试通过；真实链/图/READY均0，未训练、未启封SEALED、未提交推送。

历史[GNN-IRAC第二轮有限修复报告](outputs/gnn-irac-feasibility-02/report-zh.txt)：GNN-IRAC第二轮有限修复完成：固定8个旧TRAIN、13次普通High、语义重试0。阶段许可覆盖711项，五案132条input-only候选绑定先于target冻结；1106992的目标关系和来源隔离。最终来源审阅2案语义READY、3案REFERENCE_ONLY、3案GAP；冻结准入0/8 READY，NO_GO。14项不连续拼接引文、范围错配、目标阶段和悬空对象/跳过绑定仍保留。组内真实canonical NOT_AVAILABLE；未训练、启封SEALED、生成完整法律回答、提交或推送。

历史[GNN-IRAC数据可行性报告](outputs/gnn-irac-feasibility-01/report-zh.txt)：GNN-IRAC数据可行性完成：固定8个旧TRAIN，8次提议＋2次独立High来源审阅，无语义重试。1案有较完整回顾性链，7案缺决定性测试、证据内容或阶段明确的target；1106992发现目标FOUND关系残留。通用关系guard离线隔离两条，不覆盖冻结输入。真实组内canonical仅有合成接口检查，没有八案上游产物；NO_GO，未训练、未启封SEALED、未生成法律回答或发布。保留S并暂停扩大排序R-GCN。

历史[V11 S/B/C收尾报告](outputs/rgcn-sbc-finalization-11/report-zh.txt)：V11正式收尾：四项法源的132个位置完成独立L/G复核，12次普通High无语义重试；27 TRAIN／6 DEV／8 SEALED、30法源保持。757项弱监督进入损失，两个种子六次固定S/B/C拟合全部完成。已知非强制CORE送达S16/35两次、B14/35与15/35、C13/35与15/35。B只有单案明确收益，其他案件损失关键限制或反论；C无稳定额外净收益。保留S，暂停扩大当前R-GCN；未启封SEALED、未生成法律回答、未提交推送。

历史[V10集中修复报告](outputs/rgcn-dev-contract-repair-10/report-zh.txt)：V10集中修复完成：六案180个DEV位置均有状态（176可评价、4隔离），统一类别、可逆空白定位、材料视图和构图。TRAIN746项弱监督候选；抽查发现两案重复用途口径错配，按预定规则停止六次新拟合。旧36项排名已重评；8 SEALED未读取，未生成法律答案或提交推送。

历史[V09主训练报告](outputs/rgcn-data-expansion-09/main-training-01/report-zh.txt)：27 TRAIN、730项暂定用途监督、30法源，两个种子共6次S/B/C训练完成。DEV核心送达S8/11、B7/11、C4/11与9/11；无稳定条件化收益，暂停扩大图。8 SEALED未用；未生成法律回答或推送。

准备阶段[V09剩余任务报告](outputs/rgcn-data-expansion-09/continuation-03/report-zh.txt)：27 TRAIN／6 DEV／8 SEALED；27图、26标签、26案接口配对。补2项，125596702标签保留隔离；未训练或推送。 旧结果保持；接口完成不等于语义验收。

历史第08轮见[完成报告](outputs/rgcn-use-development-08/report-zh.txt)与[逐案比较](outputs/rgcn-use-development-08/comparison-table.csv)。十案80次用途监督训练、三案9次普通High回答完成；共享基线核心送达仍领先，R-GCN减少部分无关材料占用，但未显示稳定完整答案改善。冻结字节保留；非独立测试、非人工gold。

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
当前[关系图辅助法源排序开发实验06](outputs/rgcn-ranking-development-06/report-zh.txt)已完成。六案完成38次准备、36次真实训练、20份法律回答。C/C0两种子材料均相同，未显示图传播额外收益；B有限依据覆盖较好但完整回答有得有失。保留简单关系候选，暂不扩大R-GCN。 完整[逐案比较表](outputs/rgcn-ranking-development-06/comparison-table.csv)、[集中来源审阅](outputs/rgcn-ranking-development-06/final-source-review.json)和训练权重/日志均已保存。旧[可行性检查](outputs/rgcn-retrieval-feasibility-05/report-zh.txt)作为历史记录保留；本次另行补齐数据后完成真实训练。仅本地交付，未提交或推送。

此前[六案同材料分析提示对照](outputs/legal-analysis-study-04/report-zh.txt)已冻结12项任务，尚未提交模型任务；浏览器连接现已恢复，但按本次优先级暂缓。新增说明仍可在单独任务按冻结顺序比较，本地未提交或推送。

此前[六案本地诊断](outputs/legal-rule-support-diagnostic-03/report-zh.txt)：六案本地诊断确认：原文已找回全部14项，G/L改变排名但受描述覆盖、依赖恢复与预算影响，固定展示顺序消除多数剩余差异。一次范围优先重排找回四案DRC16，三案有限覆盖提高、一案交换重要依据、两案无确认覆盖增益；不能直接替换A。主要主张归属及反论遗漏发生在已送达内容的使用阶段。0模型调用，旧文件不改；后续同材料比较已获授权并完成准备，当前访问受阻。

上一轮已完成[来源修复与六案A/G/L比较](outputs/legal-rule-support-study-02/report-zh.txt)。来源边界修复后，按Delhi14(1)(b)定位详审8份、纳入6案，完成28次普通High调用（参考6、描述4、最终10、集中审阅6、独立复核2），重试0。5案A/G/L最终输入相同，6案G/L相同；1908519唯一不同材料配对接近，重复存在覆盖变化。暂优先原文检索，G/L收益未建立；非人工gold、非独立预测。本轮仅本地交付，不提交或推送。完整[逐案表](outputs/legal-rule-support-study-02/comparison-table.csv)、[答案及对话入口](outputs/legal-rule-support-study-02/final-answer-slots.md)、[来源修复证据](outputs/legal-rule-support-study-02/audit/source-trace.json)和[集中审阅](outputs/legal-rule-support-study-02/final-source-review.json)均已保存。上一轮零合格反映候选定位不足，不再据此推断数据里没有适用案件；旧报告与失败原样保留。

最近已发布的状态仍是[V22范围核对](outputs/rules-verdict-v22-scope-preparation/report-zh.txt)及V23的S01准备检查点。其[完整Pro审阅prompt](docs/reviews/2026-10-03-pro-research-design-review.md)与后续完整审阅档案保存在新研究目录review/。旧报告“待范围选择”“未推送”和原冻结源码按当时状态保留，不倒改为本轮状态。

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
