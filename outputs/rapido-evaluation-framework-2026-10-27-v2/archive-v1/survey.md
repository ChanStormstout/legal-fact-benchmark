# 法律报告的评价与修订：让核验减少错误，同时保住有依据的内容

## 摘要

RAPIDO当前的主要问题不只是模型误读：生成、核验和交付采用的内容粒度不一致，导致一段中局部的错误引用或法院归属使正确历史内容也被删除，且模型修订并未改变正文。本调查结合1251841冻结V38的实际数据流，核对21项原始研究，比较内容单元评价、来源归属、局部事实修订和模型自纠的证据。已有文献支持把“正确重要内容覆盖”和“写出内容的来源支持”分开衡量，也支持尝试先定位错误关系再局部改写；它们并不保证同一Qwen能发现自己的错误。建议取消语义ACCEPT驱动的整段发布门槛，试验有来源的关系级修订，并把独立评价移出被测生成流程。本文交付可复算开发评分及下一版方案，不把调查或离线评分说成新方法已经有效。

## 1. 要回答的问题

RQ1：怎样比较两份仍有错误的报告，避免把二者全部判零，也避免删掉答案就获得高支持率？RQ2：本案哪些有依据的内容在实际调用链中丢失，原因是模型理解、核验判断还是发布处理？RQ3：固定原Qwen、不加Agent和训练时，有哪些替代机制，哪一种值得用完整案件比较？

评价的目标是让用户更准确地理解当前允许记录中的案件问题、竞争立场、此前认定、法律边界和未决事项。文件生成、引用存在、ACCEPT数量、推导是否跑完，都不是这个目标的替代指标。老师的应用目标可以保留，现有整段删除策略不必作为不可改变的实现要求。

## 2. 调查方法与证据边界

检索覆盖内容评价、归属生成、事实修订、支持自纠与批评自纠、近期评价器可靠性五类问题。使用网页检索定位原始发表页、arXiv和作者资源，下载21份论文，提取并阅读与本问题相关的方法、实验条件和局限；实际章节和阅读范围逐项保存在literature-evidence.csv/json，未把下载全文等同于读完全文。OpenReview的两次下载403保留记录，改读对应arXiv原始论文。遵守用户不加Agent的要求，各视角串行完成。

时间范围从2004年的内容单元评价到2026年的关系级事实定位及rubric可靠性研究。这是有明确问题的聚焦调查，不宣称穷尽或完成PRISMA式系统综述。只依赖原始论文和正式元数据；未确认的发表状态明确保留。外部论文没有在我们的Qwen、历史印度土地判决、规则版本和隐藏结局协议上证明效果。

本地证据来自V38实际请求、响应、报告、费用及冻结代码。只使用原有允许CASE/LAW来源，不访问目标隐藏理由和结局，不向实验模型提供参考答案；本轮没有新模型调用或实验费。1251841已暴露，新的评分属于非盲开发复核。

## 3. 把问题按发生位置分开

| 位置 | 实际问题 | 不能用什么替代解决 |
|---|---|---|
| 来源到表达 | 读错人物、法院或法律范围；财产成员混入银行和人 | 固定编号不能证明编号选对了 |
| 表达到核验 | 错误法院归属仍被判通过 | 多一次同模型ACCEPT不等于独立证据 |
| 核验到交付 | 局部问题使整段正确内容消失；修订未改文 | 引用数量和系统缺口提示不能算回答恢复 |
| 最终评价 | 没有固定连续分数，描述性比较容易变成整体印象 | 全部有错不等于无相对进步；只算支持率又奖励少写 |

后三类分别需要可靠反馈、内容保留策略和明确评价，不能混为增加一个核验角色。细节见processing-loss-trace.md。

## 4. 从“整体看起来更好”改为来源可追查的分数

[Pyramid](https://aclanthology.org/N04-1019/)与[RoSE的ACU协议](https://aclanthology.org/2023.acl-long.228/)都把内容评价拆成可重复使用的语义单元；前者用多参考间的共识赋权，后者强调更小的单元与一致匹配。我们没有多份律师参考，不能伪造Pyramid权重，但可以先根据问题和允许来源冻结要点，再给所有方法同一张卷子。[QAEval](https://aclanthology.org/2021.tacl-1.47/)进一步说明问答可以测信息是否存在；它仍依赖问题生成和问答正确性，不能只因主题词出现就给分。

[FActScore](https://aclanthology.org/2023.emnlp-main.741/)测的是写出断言的来源支持比例，作者明确指出少写可能提高分数，未解决recall；[ALCE](https://aclanthology.org/2023.emnlp-main.398/)把答案正确覆盖和引用质量分开，不能用引用覆盖替代任务回答。对我们的直接含义是：正确要点覆盖R必须作为任务分，断言支持率P和引用分另报。一个正确未知可以回答真正开放的问题，但不能覆盖原文明说的交易经过。

仅拆成小命题仍有风险：[D-FActScore](https://aclanthology.org/2024.findings-acl.160/)发现不同实体的分别正确事实可以拼成错误传记，而[FineSurE](https://aclanthology.org/2024.acl-long.51/)把句子事实性、keyfact完整性和简洁度显式分开。我们的指标需要保留是谁、何时、哪个法院和何种主张状态；日期正确不能把原告等同银行变成正确。当前开发计分允许正确的角色事件获得该内容点，同时在主体条件和错误清单中记录身份矛盾，故其组合分也不能充当整份叙事一致性的证明。

本轮定义二十个条件，每项一分；R=正确要点数/20。P=允许来源支持的去重实质断言数/全部已标注去重实质断言数。辅助组合分F=100×2PR/(P+R)，用于同时显示少写和无依据扩写的代价；它是本任务的开发组合分，不冒充原版FineSurE或经典集合F1。R为主要任务指标，P、严重错误、主问题回答和成本同步报告。将来如需改变主指标或法律重要性权重，必须在新输出生成前冻结，不能见到输赢再改。

[FACTS Grounding](https://arxiv.org/abs/2501.03200)同时要求完成用户请求和受给定文档支持，[FACTS后续套件](https://arxiv.org/abs/2512.10791)则进一步区分给定来源、参数知识、搜索等条件。这支持我们明确允许来源的边界，但其任务和评价设计不能直接当作复杂法律推导的验证；初版Grounding特意排除了复杂逻辑和专业知识要求。

有rubric并不等于标签自动客观。[MT-Bench裁判研究](https://proceedings.neurips.cc/paper_files/paper/2023/hash/91f18a1287b398d378ef22505bf41832-Abstract-Datasets_and_Benchmarks.html)显示顺序和长度等偏差；2026年的[rubric artifacts研究](https://arxiv.org/abs/2609.02942)又提示准则措辞可能关联评分，并用反转实验研究裁判是否追踪内容变化。后者仍是有条件、非因果的证据。因此，程序负责哈希和算术，语义标签需要来源依据、匿名复核和分歧记录，不能让C生成链自己的ACCEPT兼任金标准。

### 4.1 用现有输出实际计分

| 现有输出 | 正确要点 | R | P | 辅助F |
|---|---:|---:|---:|---:|
| A0一次普通调用 | 11/20 | 55.0% | 26/37=70.3% | 61.7 |
| C候选 | 6/20 | 30.0% | 16/33=48.5% | 37.1 |
| C实际交付 | 3/20 | 15.0% | 8/12=66.7% | 24.5 |

每个点和断言都有报告原句及来源ID，计算器为score_existing.py。不是根据篇幅推算，不因还有错误就归零。A0的裁判反转和身份混淆仍列为严重错误；候选C在高院实际结果这个点确有改善。当前等权评分下，改善不足以抵消C的其他无依据断言和遗漏。全部数字是非盲、事后制定rubric的开发参考，不是人类金标准，也不支持单案统计显著性。

候选到交付正确要点保留率为3/6=50%；八条来源支持断言被删除，十三条矛盾或无支持断言也被删除，四条无支持断言仍保留。检查使P上升，但R和辅助F下降。直接取消门槛返回现有候选会恢复正确内容，也带回错误；这只说明当前交付策略的取舍，不是新方法已成功。

## 5. 有哪些机制可替代整段阻断

### 5.1 先选证据再生成，减少事后补引用

[Attribute First, then Generate](https://aclanthology.org/2024.acl-long.182/)把来源片段选择、句子规划、生成分开，而[RARR](https://aclanthology.org/2023.acl-long.910/)保留原生成模型，之后根据证据修订。两者区别是证据在生成前还是之后约束内容。前者有利于局部归属，后者更容易保住完整初稿；但前者会受选段遗漏影响，后者依赖发现错误和可控编辑。Attribute First不同任务和变体的结果并不一致，不能只摘LFQA的有利结果；其逐句调用和截断实现也不适合直接照搬当前预算与完整来源要求。

对本案应保留“整份允许原文可读”，但生成时同时给出精确证据片段、说话者和阶段。选中的片段是注意力和归属依据，不是禁止读取其余原文的白名单。尤其不能让初始八个偏法律的问题决定全部报告内容，事实链和重要反论也必须进入通用报告任务。这个通用任务清单与评价参考要点、隐藏结局隔离，不能把已标好的答案再交给Qwen。

### 5.2 定位错误关系，再只改那一处

RARR在修订时兼顾来源归属和原文保留；[QASemConsistency](https://aclanthology.org/2026.tacl-1.6/)则把命题拆成“谁做了什么、涉及谁、何时发生”等更小的关系，定位哪部分不受支持。二者结合给出比整段ACCEPT/REJECT更直接的方向：关于“两级下级法院作出代位认定”的句子，法院名称可能错，代位事实及被认定的当事人仍可分别有依据。应改法院归属，保留得到支持的历史描述。

这种关系级定位不是已经解决的问题。QASem论文训练了专门解析器，也测试NLI和LLM，仍有误差；不能把它的名字贴在Qwen提示上就宣布有同样能力。当前只值得借其表示和评价协议，用同一Qwen在允许原文内提出短QA及精确来源，再实测是否比现有复核更可靠。

[FAVA](https://arxiv.org/abs/2401.06855)进一步区分实体、关系、句子和不可验证内容的处理；[PURR](https://arxiv.org/abs/2305.14908)则训练小型去噪编辑器以降低逐证据编辑成本。它们说明检测和修订是不同任务，也说明按事实数线性增加大模型调用并非唯一实现。其训练、额外模型及开放网络检索不在当前约束内，因此不直接采用其检查点。可借鉴的是编辑范围和输出合同：有依据的局部修复、仅删无依据的子句、真实未知的说明，以及保持其他内容不变。

### 5.3 独立读来源，比重复确认草稿更值得检验

[Self-Refine](https://proceedings.neurips.cc/paper_files/paper/2023/hash/91edff07232fb1b55a505a9e9f6c0ff3-Abstract-Conference.html)支持同模型反馈改写在其若干任务中有效；[不能内在自纠的研究](https://openreview.net/forum?id=IkmD3fKBPQ)和[批评性综述](https://aclanthology.org/2024.tacl-1.78/)则揭示oracle信息、初稿提示、任务与成本条件会改变结论。这些结果不能被平均为“自纠一定行”或“一定不行”。我们的任务有允许原文可查，不是纯无反馈推理，但同一Qwen的评语依旧可能错；外部文档存在不等于反馈可靠。

[DeFacto](https://aclanthology.org/2023.acl-long.844/)把来源证据、具体修改指令和实际改写分开，其零样本可控编辑局限与本次“反馈发送了、正文却没改”的现象有关；[CoVe](https://aclanthology.org/2024.findings-acl.212/)通过不看原答案的核验问答减少复制草稿错误。可试验中性问题加原文的独立读取，避免“请确认银行是原告”式带答案核验；但不能照搬无检索知识问答，也不能让每个QA都引出新的一串调用。

### 5.4 撤掉语义发布门槛，需要同时改变交付和评价

程序能够证明来源地址存在、片段没有越界、补丁针对哪个版本，以及预算是否耗尽；它没有独立能力判定两个法院是不是同一个、法条是否支持当前法律结论。当前设计把模型的语义判断转成硬门槛，再用整段渲染删除正文，扩大了错误判断的影响。取消这种门槛是可研究的选择，并不需要把老师所有模块原样保留。

但只把所有候选内容原封不动交付，也会保留错误。更合理的替代是让核验生成定位到原句和来源的修改建议，生成器据此进行有限局部修订；程序只管理文本事务和机械边界，独立评价随后判断修订是否真减少错误、是否丢内容。对未知和争议的标注也要成为正文的限定，不能把一段无依据断言加一个总警告就算修好了。

## 6. 建议选择的下一版机制

建议主方向为“完整初稿＋不看草稿的来源关系问答＋一次局部修订”，以“来源片段先行生成”为备选。核心变化是错误处理的对象从整段改成具体关系，语义检查从发布许可证改成有证据的修改输入。现有规则推导可以作为报告的条件性分析材料，不再决定有来源的历史描述能否出现。

第一步，Qwen基于完整允许材料生成完整初稿，必须涉及问题、交易与身份、双方立场、此前处理、法律边界和未决原因，不能由模型只列八个法律问题就结束。这是C内部生成步骤，不把A0或评价参考作为正确答案免费注入。

第二步，同一Qwen在新上下文中只看允许来源和中性的关系问题，不看初稿答案或ACCEPT。成批输出短答案、原句、来源位置、当事人/法院/阶段，以及原文未明确之处。历史材料必须单独标为历史，不能转成当前案事实；法源时效与适用仍需说明。

第三步，编辑调用收到初稿、这些来源读取结果和完整原文，输出有具体目标范围的修改、补充及完整报告。一个修改必须指向草稿中实际存在的字串/哈希，并说明涉及哪些来源和其他依赖关系。只修错误引用时不删除有依据正文；某项法律解释未知时，不删除此前法院已经作出何种认定的历史描述。错误可能影响后文结论时，要一起改依赖内容，不能机械地只替换一个名字。

程序不填ACCEPT、不填正确语义答案、不决定哪方胜诉。它只保证来源准入、引用定位、版本与非冲突补丁、预算及日志。语义判断仍可能错，必须通过独立终态评价验证。最多三次主要调用，必要技术修复可设一次硬上限；不加Agent、不按每个字段另开复核、不无限追求通过。具体token和费用上限在实际实施前按原材料核算，不能把本方案当成已获额外预算。

如果不能形成可靠改写，报告保留能够明确归属的原文描述，并准确说明哪个关系或法律判断尚不能确认；原始错误候选作为审计材料单独保留，不能重新标成有效报告。一个未知不能吞掉同段的已知历史事实。补丁不合法或模型返回同文都记为没有完成修复，不能把文字字段非空或检查结束计为恢复。

例如，本案可读的来源描述可以是：“原文记载，两级下级法院认定原告代位于原银行、第二被告已被充分代表，这两点在当前记录中未受挑战。高院另认为租约不受抵押执行影响，驳回了原告诉讼。现有片段提出的尚存问题是1929年前抵押人的出租权能否拘束原告；目标法院最终理由和结局未提供。”这只是本报告解释机制的原文阅读示例，不是新Qwen结果，也不得作为本案被测流程的正确中间答案。

## 7. 如何决定替代机制是否值得继续

先冻结评价协议和方法版本，再进行一次完整案件比较，不用单项字段替换实验代替最终报告。A0保持原一次普通调用；本案不重跑它。新增C与旧C候选/交付分别比较，来源权限、法源、历史可见性和C方案之间的总资源上限一致；所有新调用和失败计费。C比A0调用更多，报告的是完整系统效果，不能据此主张同成本或将差异单独归因于局部编辑。

需要同时观察：R是否提高；新增无依据断言、法院/角色错绑和裁判反转是否减少；正确内容保留率是否改善；实际正文是否改变；主问题与重要反论是否被正确恢复。新版本即使还有错误，也可以获得更高连续分；不能让“尚不完美”抹掉进步。反过来，只删掉大部分回答而提高P，不满足报告恢复目标。

本案可以检查错误位置和已知开发效果，但正式研究必须使用独立纠纷组、未暴露评价材料，固定要点与标签权限，并报告纠纷级成对差异。若局部编辑仍返回同文、反馈仍无法识别关系错误，应优先简化为来源片段先行的完整生成，而非再加核验角色。

## 8. 仍需面对的反对意见

第一，参考要点本身可能偏向更长、更像某一方法的回答。当前用原有十主题和等权条件、公开逐点来源，并报告权重敏感性；正式材料仍需在输出前固定，允许登记参考遗漏。第二，原子命题粒度会影响P，独立正确片段还可能拼成错误叙事；必须另查角色、法院、时间和条件的一致性，不能只看总比例。第三，局部改写可能传播旧错误或漏改依赖结论；应记录每次修改的依赖范围与新增错误，不能把小编辑距离当质量。第四，同一Qwen的来源QA仍可能错，法律知识覆盖也仍不足；需要来源支持和范围未决的真实评价，不能用角色命名弥补模型能力。第五，这套组合与RARR、Attribute First、QASem等工作接近，系统组装没有自动的新颖性；能否贡献新的来源/程序范围任务、有效机制或可靠负面发现，需要跨案实验证据。

## 9. 对三个研究问题的回答

RQ1已有可实施答案：固定来源支持的要点作为R，去重实质断言作为P，公开辅助组合分、严重错误和主问题回答。分数可以复算，标签仍须来源标注和可靠性审查。RQ2的发布损失原因已经定位：资格判定及渲染以整段为单位，局部引用或状态失败使正确内容连带删除；本案还同时存在模型误读、假通过与修订无变化，不能全归咎于程序删除。RQ3的优先候选是来源关系引导的局部修订，并撤去语义ACCEPT驱动的整段门槛；证据片段先行生成是值得保留的备选。两者都只是有文献与本案诊断支持的可检验方案，尚未在本项目验收为有效。

## 参考文献与复核材料

完整21项题名、作者、年份、发表状态、原始链接、实际阅读部分、机制、实验条件、局限与迁移要求见literature-evidence.csv/json；原始PDF和提取文本在papers/，下载哈希与失败记录在paper-downloads.json、paper-fallbacks.json。正文的论文链接均指向原始来源。

本案评分协议见evaluation-protocol.md；逐项标签、原句、来源和哈希在case1251841/；数据流原因见processing-loss-trace.md。没有修改V38或旧结果，没有启动新模型实验。

### 书目信息

[1] Ani Nenkova、Rebecca Passonneau. “Evaluating Content Selection in Summarization: The Pyramid Method.” HLT-NAACL published, 2004.

[2] Yixin Liu、Alex Fabbri、Pengfei Liu、et al.. “Revisiting the Gold Standard: Grounding Summarization Evaluation with Robust Human Evaluation.” ACL published, 2023.

[3] Daniel Deutsch、Tania Bedrax-Weiss、Dan Roth. “Towards Question-Answering as an Automatic Metric for Evaluating the Content Quality of a Summary.” TACL published, 2021.

[4] Sewon Min、Kalpesh Krishna、Xinxi Lyu、et al.. “FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation.” EMNLP published, 2023.

[5] Tianyu Gao、Howard Yen、Jiatong Yu、Danqi Chen. “Enabling Large Language Models to Generate Text with Citations.” EMNLP published, 2023.

[6] Cheng-Han Chiang、Hung-yi Lee. “Merging Facts, Crafting Fallacies: Evaluating the Contradictory Nature of Aggregated Factual Claims in Long-Form Generations.” Findings ACL published, 2024.

[7] Hwanjun Song、Hang Su、Igor Shalyminov、Jason Cai、Saab Mansour. “FineSurE: Fine-grained Summarization Evaluation using LLMs.” ACL published, 2024.

[8] Luyu Gao、Zhuyun Dai、Panupong Pasupat、et al.. “RARR: Researching and Revising What Language Models Say, Using Language Models.” ACL published, 2023.

[9] Aviv Slobodkin、Eran Hirsch、Arie Cattan、Tal Schuster、Ido Dagan. “Attribute First, then Generate: Locally-attributable Grounded Text Generation.” ACL published, 2024.

[10] Arie Cattan、Paul Roit、Shiyue Zhang、et al.. “Localizing Factual Inconsistencies in Attributable Text Generation.” TACL published January2026, 2026.

[11] Abhika Mishra、Akari Asai、Vidhisha Balachandran、et al.. “Fine-grained Hallucination Detection and Editing for Language Models.” COLM published; PDF/arXiv confirms, 2024.

[12] Anthony Chen、Panupong Pasupat、Sameer Singh、Hongrae Lee、Kelvin Guu. “PURR: Efficiently Editing Language Model Hallucinations by Denoising Language Model Corruptions.” arXiv preprint; no formal venue verified, 2023.

[13] Aman Madaan、Niket Tandon、Prakhar Gupta、et al.. “Self-Refine: Iterative Refinement with Self-Feedback.” NeurIPS published, 2023.

[14] Jie Huang、Xinyun Chen、Swaroop Mishra、et al.. “Large Language Models Cannot Self-Correct Reasoning Yet.” ICLR published, 2024.

[15] Ryo Kamoi、Yusen Zhang、Nan Zhang、Jiawei Han、Rui Zhang. “When Can LLMs Actually Correct Their Own Mistakes? A Critical Survey of Self-Correction of LLMs.” TACL published, 2024.

[16] Yixin Liu、Budhaditya Deb、Milagro Teruel、et al.. “On Improving Summarization Factual Consistency from Natural Language Feedback.” ACL published, 2023.

[17] Shehzaad Dhuliawala、Mojtaba Komeili、Jing Xu、et al.. “Chain-of-Verification Reduces Hallucination in Large Language Models.” Findings ACL published, 2024.

[18] Alon Jacovi、Andrew Wang、Chris Alberti、et al.. “The FACTS Grounding Leaderboard: Benchmarking LLMs Ability to Ground Responses to Long-Form Input.” arXiv technical report, 2025.

[19] Aileen Cheng、Alon Jacovi、Amir Globerson、et al.. “The FACTS Leaderboard: A Comprehensive Benchmark for Large Language Model Factuality.” arXiv technical report December2025, 2025.

[20] Lianmin Zheng、Wei-Lin Chiang、Ying Sheng、et al.. “Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.” NeurIPS Datasets and Benchmarks published, 2023.

[21] Anshul Bagaria、Sowmya S Sundaram、Gokul S Krishnan、Balaraman Ravindran. “Judging LLM-as-a-Judge: Concerning Rubric Artifacts in LLM-based Automated Text Generation Evaluation.” arXiv; authors state EMNLP2026 acceptance, proceedings not verified, 2026.

