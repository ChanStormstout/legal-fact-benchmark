请忽略上一条已经被用户暂停的短请求，改为回答本条完整请求。上一条没有向你提供完整独立方案，却让你裁决其细节，信息不充分。本条自包含项目背景、原始文档全文、独立方案全文、文献阅读范围和需要解决的设计缺口。不要假定能够读取任何本地路径；所有需要你读的内容都已直接附在下面。

你的任务：作为共同设计者，先理解整个项目和已有备选方案，复核近期相关论文的方法，再批判性地评审我们的独立方案，最后给出一套前后一致、足够具体可以开始实现的 A/B/C 推荐算法。不要只回复四个零散问题，不要只添加更多论文或列一堆可选方法。回答没有 2000–3000 字上限，以讲完整算法所必需的篇幅为准。用户要在 meeting 中解释“要解决什么、为什么这样设计、实际怎么执行、为什么预期有用、比文档备选改善在哪、还缺什么证据”。

## 1. 项目背景、范围与材料地位

这是一个尚无已完成代码的 Legal AI 研究项目。目标是从判决中的事实描述形成跨案件可比较、可追溯的规范事实，再发现有意义的事实组合，进一步连接法源、法律因素、要件与论证。我们现有的是判决语料，不是完整庭审证据库。法院认定、当事人主张、争议事实及引用规则必须分开。

团队完整流程是：Evidence → Canonical Facts → Fact Patterns → Subtests/Factors → Elements → Claims/Defenses → Issues → Conclusion；另一条 Authorities → Rules/Tests 定义法律要件的判断标准。这个图表达项目目标，不表示每条箭头已有算法，更不表示模式自动具有法律效力。

团队任务包括：原子事实抽取、角色替换和谓词论元表示；保守聚类与语义漂移控制；模式挖掘；评价；抓取法院推理实际引用的 authorities。团队建议可先用约 1000 份案件材料开发各阶段基础逻辑。A/B/C 是我们为实现方便采用的分解：A=可靠事实规范化与类别维护，B=关系模式/派生描述概念发现，C=有法源的法律连接及论证重建。A 可直接供 C 使用，不能要求所有法律事实先通过 B 的高频或压缩筛选。白板及手写截图不作为这次设计依据。

我们不能声称原始 PDF 没有算法。它已经给出抽取、角色规范、上下文 blocking、embedding 检索、LLM 六类关系判断、保守合并、定义/medoid/边界检查、命名和来源保存的具体流程。需要补足或改进的是执行细节、误判修复、可持续类别定义、模式的获取与筛选，以及事实到法律条件的连接。PDF 全文在最后附录，优先准确区分“原文已有”与“我们的建议”。

## 2. 已实际核查的数据和当前可做任务

本地 land 1.jsonl 审计：6954 条记录、6954 个不同 doc_id；6418 条 status=ok，497 empty，39 error；5424 条 facts 非空、6179 条 issues 非空、6111 条 conclusion 非空。这是结构计数，不是正确性评估。20 条固定随机样本显示主题混杂，包含土地/租赁之外的刑事、税务、野生动物保护等。部分事实放进 issues，部分 facts 开头实际是规范命题。因此不能把文件名当统一案由，也不能把现成字段当可靠的事实/理由/结论分段。不同 doc_id 不能证明纠纷相互独立。

我们没有经核验的：同一纠纷文书家族、局部实体/事件身份、等价标注、事实原文逐字段对应、稳定法律规则库或 claim-stage outcome 标签。不能虚构这些监督已存在，也不能让模型生成后自评代替独立依据。

默认首版任务是回顾性知识发现和有来源的法律论证重建。原 PDF 要求的 outcome-conditioned pattern mining 保留为明确模块，在完成“谁、何项请求、哪个审理阶段、支持/驳回/部分/程序性处置”的标签核验后启动。无标签时先发现描述结构；有标签后检验组合是否超出单事实的结果关联。用法院事后认定做特征只能叫回顾性关联，不能宣称判前预测。

## 3. 独立文献调研的地位和你需要完成的阅读

我们自己已经跨规范化/开放信息抽取、类别发现/定义修订、谓词发明/程序归纳、规则发现/子群发现、法律因素/规则形式化/论证检索，不只是等你提供论文。下面两份完整报告列出约二十项近期工作的方法或实验阅读，以及另外只完成初筛的工作。搜索条目数、摘要初筛、方法阅读和复现是不同证据；我们未复现作者代码，不声称穷尽领域。

请先用下面的原始链接打开与你的关键选择直接相关的论文，读核心方法、算法、实验设定和相关限制。不要仅据标题、摘要或本请求的摘要做出选型。优先 2024 年末至 2026 年的工作，包括 arXiv 最新可核验版本和 ACL/TACL/EACL/EMNLP、NeurIPS、ICLR、AAAI、IJCAI、ICAIL/JURIX 等。对只有预印本、版本变化、全文取不到及只看摘要的内容明确说明。若以前在本对话已经读过，不必无谓重读，但要确保关键结论有对应原文。也请沿这些方向查漏，不把给出的论文名单当封闭集合。

重点认识 community 的多种路线：A 不只看聚类，还看定义驱动分类、开放类别发现、schema induction、抽取后修正；B 不只看频繁项集，还看关系程序学习、语言偏置获得、谓词发明、执行反馈、描述长度、监督规则/子群发现；C 不只看一个符号引擎，还看规则获取、联合形式化、因素发现、桥接与可推翻论证。论文年代不决定采用；需要解释机制与我们的数据条件是否匹配。

下面给出独立方案全文和阅读记录，之后再列具体设计缺口。它们是待评审研究草案，不是要求你同意的结论。其中版本说明和“当时不继续发送给 Pro”的历史文字只描述旧阶段，不是本条任务指令。


--- 独立算法报告全文开始 ---

# Legal AI：从文献机制到算法重设计

2026-09-29。状态：研究设计，尚未在本项目数据上训练、运行或证明优于 v2。本文替代 v2 的默认选型建议；v2 的原文来源、实例身份、状态、精确绑定与推理语义要求继续有效。原有 slides 尚未同步，不能当作本版说明。

## 1. 这次实际改变什么

推荐主线：学习有明确边界的事实定义；从案件提出可执行的关系概念和模式；让原文依据、匹配结果和困难实例驱动局部修正；最后把经核验的法律条件与这些事实连接。

| 模块 | v2 的主要机制 | 本版决定 |
|---|---|---|
| A 事实表示与类别 | 用全成员 EQ 图及整数规划构造严格等价簇 | 改为固定版本定义驱动的映射；模型成对判断只用于诊断和优先审查，不直接成为不可违反的语义真理。严格等价按完整规范签名另算 |
| B 关系模式发现 | 在固定谓词中枚举短合取，再按压缩选集 | 改为源实例归纳、LLM 概念提议、有限程序编辑共同生成候选；精确执行和原文反例驱动修正。保留压缩选集，但取消其决定“法律有用”的资格 |
| C 法律连接 | 已包含联合规则获取与审阅，详述了后续论证执行 | 细化规则获取、适用范围、事实到法律概念的桥接与翻译测试；保留成熟论证语义，不重新发明引擎 |

不按论文年份决定采用。近期方法提供了可迁移的机制，不等于在本项目已获胜。v2 的 C 已经提到联合规则生成和专家审阅；本版是补足其候选修正与验收机制，不声称以前完全没有这一步。

## 2. 统一对象，避免三个模块各自发明一套概念

系统保存四类对象：

1. **原文断言**：谁在文书中说了什么，指向哪个合同、请求或事件，极性、日期、陈述状态和原文位置是什么。
2. **基础事实类型**：同一种动作或关系的明确解释和参数槽，例如“支付”，参数包括付款人、收款人、合同、金额、日期。实例金额不因共享类型而消失。
3. **派生描述关系**：用基础事实和已审核算子计算，例如两件事的时间间隔、同一合同的付款与通知组合。每次计算保存输入事实和对象绑定。
4. **法律因素或规则条件**：例如“有效通知”“实质违约”。这类概念需要法律依据和解释；不能因为模式反复出现就成为可计算的法律真理。

所谓 cluster 必须说明是哪一类：基础类型的实例集合允许参数不同；严格等价簇要求在预先声明的抽象政策下完整规范签名相同。family 只保存有依据的上位/相关类型组织，不授权合并。

“跨案等价”指在指定比较层次上表达同一种事实结构，不是两个案件发生了同一件事。原实例 ID 永远分开。比较签名可把姓名变成角色变量，但必须保留参数关系和声明应保留的区别；在同案计算时仍使用真实局部对象 ID，不用 BUYER 这样的角色词代替身份。保留全部金额的严格签名可能很少跨案重复，这不妨碍 B 把金额显式泛化为变量来发现模式。

一个买方可以在同案 K1、K2 下承担不同关系，身份和合同绑定都保留。ALLEGED 与 FOUND 始终单独保存。未写、未证明、明确否定是三种不同情况。

所有程序仅在有界、类型安全的查询语言中执行。LLM 产生的是语法树，不是可任意运行的 Python/Prolog 源码；由本地编译器生成查询。允许索引连接、显式否定的查找、数值/日期比较和登记的聚合；不允许文件、网络、任意递归或自动把缺失变成否定。

## 3. A：固定定义映射＋有针对性的定义修正

### 输入与输出

输入是带上下文的原文断言和一个可扩展的版本化类型注册表。输出是基础事实实例、类型归属、保留参数、未决归属、定义修订记录，以及各项的原文依据。原文与旧版本不覆盖。

每张定义卡包含：类型 ID、解释、论元槽及类型、必须保留的限定、排除项、已审阅的同义表达、正例、困难反例、语境、版本。定义卡不包含案例胜败。

### 没有类别时怎样启动

先在一种明确法律问题的开发样本上开放抽取，不要求模型套入预设类别。按动作/关系及论元类型检索相似断言，只把检索结果当定义候选的材料。LLM 从一小组原文实例起草定义卡，再寻找最相近但有关键区别的实例测试边界。首批定义须经原文审查确认；未完成审查的定义单独标为候选，可以研究运行，但不能与已审阅定义混报。原子事实的拆分也要保留量词、条件、共同事件和否定范围，不能把“没有人付款”拆成未经依据的单个人否定。

类别建立后才进入下面的固定版本映射。新实例确实无法被现有卡表达时走同一新卡流程；先补别名和参数，仍不能表达才新建类别。避免每遇到新措辞就创建一类，也避免为减少类别数量丢掉重要差异。

### 执行步骤

1. 来源约束抽取。保存原文锚点、角色证据、实例身份，逐字段核对。修正明确分成 KEEP（保留）、FIX（纠正抽取错误）、REWRITE（不改含义地规范表达）、EXCLUDE（原文不支持，移出可计算视图但保留原记录）。每次改动记录前后差异和来源；信息不足用 UNKNOWN，不能一律当错误删除。首版每项最多一次自动修正，仍不通过则待审。抽取错误不得通过改宽类别定义来掩盖。这借鉴 GraphRefine 的操作划分，不意味着已有其监督微调效果。
2. 检索定义。精确别名、BM25 和向量检索取并集；每个实例先看最多 20 张卡。相似度只排序，未知语境不作硬排除。
3. 填卡而非投票。模型把原文成分映射到卡的槽，并逐项返回有出处的支持、冲突、未知。明确极性、角色方向、主体或适用范围冲突直接阻止映射；不允许用更高总分抵消。
4. 信息保存检查。实例必须保留原文有意义但定义未要求的修饰信息。只有抽象后的完整签名相同，才能进入严格等价簇；同属 PAYMENT 类型并不使“部分支付”和“付清”可互换。无法结构化的限定保存在原文并把严格等价资格标为未决。
5. 归属。唯一叶级定义通过全部必要项且未遇排除项时，写入“模型接受”的映射；通过父、子卡时选择有完整依据的最具体子卡并保留父关系；通过两个无已审核包含关系的卡时，保留歧义，不按距离强行二选一。没有合适卡则生成候选新卡。
6. 审查选择。每批预算 B 中约 1/4 用于固定随机抽样，3/4 用于以下顺序：违反已审阅区别的冲突；两个定义同时通过；定义与困难成员的判断不一致；新措辞/新参数组合。每层按影响的不同案件家族数量降序，再用距离多样性避免反复审查同一种表达。这里的比例是实施初值，不是论文证明的最优值。
7. 局部修正。可执行操作只有：纠正一个实例的槽/状态；增加有证据的同义表达；把遗漏限定提升为必填参数；按一个有来源的区别拆分定义；合并经双向检查且不存在保留区别的定义。单纯“把定义改得更宽以容纳成员”不接受。
8. 接受新版本。新版本必须通过已有人工审阅的正例和反例回放，且至少修复一个已确认错误；任何原有已确认错误回归都拒绝。多个通过版本优先选改动范围最小者。不能用模型平均置信度提高代替这个条件。改动后重映射所有依赖该定义的实例，再发布版本。

```text
for assertion in source_assertions:
    cards = retrieve(assertion, registry)
    mappings = check_slots_qualifiers_and_exclusions(assertion, cards)
    commit_unique_compatible_mapping_or_keep_pending(mappings)

while review_budget_remains:
    item = next_conflict_boundary_or_random_audit()
    evidence = review_original_text(item)
    if evidence does not resolve the issue: keep_pending(); continue
    patches = allowed_local_edits(item, evidence)
    accept smallest patch that fixes an adjudicated error
        and passes every applicable reviewed regression case
    recompute dependent mappings and strict signatures
freeze_registry_version()
```

### 为什么比 v2 更合理

v2 的示例图只有 ab、ac、bd 为 EQ，却让优化器选两个边来提高目标。真正等价具有传递性，这种图首先是判断器或比较语境需要检查的信号；多保留一条 EQ 边不直接代表更正确的法律类别。

本版让共同定义成为跨案件复用的标准，局部实例直接对标准检查；成对比较集中到边界和冲突。主要预期收益是减少重复比较、将错误定位到具体语义条件，同时避免未问过的边自动造成碎片化。它不保证模型能正确理解定义；仍可能系统性误读同一条定义，因此保留随机审计和原文复核。

这里主动改变了 v2 的承诺：本版不再宣称每个模型接受类别的所有成员对都已获得 EQ 证书。严格等价由规范签名和已审阅改写规则定义，签名抽取的语义正确性仍需评估。若团队坚持全成员 EQ，完整检查可作为额外严格模式，不能隐藏其成本。

## 4. B：有来源的概念生成＋可执行关系模式搜索

### 核心选择

同时保留两个候选来源：程序从真实事实子图归纳，LLM 提出可能缺失的关系及有解释的组合。两路候选进入同一编译器、匹配器和选择器。这样既利用语言模型的概念能力，也不把发现覆盖完全交给语言模型。

这里不设置虚构的胜败目标。没有可靠标签时学习的是可复用、可解释的描述关系；法律方向或结果关联留在有对应依据的单独对象中。

### 第一步：从真实实例形成种子

在每个案件的合同/请求范围内抽取连通的 2–4 原子小片段。只有通过实际主体、合同、事件或有来源的关系连接，才算连通；公共 case_id 不够。按类型结构分桶，优先取不同案件家族的实例，避免长判决占据全部预算。

程序对两份类型兼容的小片段做最小泛化：把不同人物、合同和数值改为带类型变量，保留两边共有的谓词、论元对应、同一/不同对象约束和显式时间关系。不同事实状态不能悄悄抹掉；需要更宽状态范围时显式写在查询中。该操作本身是已有关系学习思想，不主张原创。

具体实现先按谓词和论元类型分桶，在桶内枚举原子对应关系；对每个对应进行带类型反统一，保留连通结果，按变量首次出现顺序重命名并排序原子以去重。不承诺任意图都有唯一的最小泛化。首版每个案件家族最多抽 50 个种子、每桶最多 100 对片段，固定随机种子并记录未搜索范围；优先多样性采样，而非只取高频模板。候选展开后初始上限为 6 个原子、6 个对象变量、2 层派生定义，禁止循环；这些是可调整的计算预算，不是理论最优值。

LLM 每次读一组来源实例和现有定义，最多提出 8 个候选。每个候选必须包含自然语言定义、参数签名、查询语法树、对应来源实例、预计能区分的困难近邻。已有结构能表达时复用；缺基本观察时请求回到原文补抽；缺可计算算子时登记算子需求；需要法律评价时转入 C 的桥接队列。

### 第二步：限定概念发明的含义

新概念分三类，接受条件不同：

| 候选 | 例子 | 接受条件 |
|---|---|---|
| 已有事实的组合缩写 | 同一合同付款后发出通知 | 展开后是有效的带绑定查询，保存展开定义；它不增加逻辑表达能力，只增加可复用结构 |
| 新描述算子 | 通知日期减去获知日期 | 输入类型和单位明确，确定性算子经测试，原文有两个同事件日期；缺失则不计算 |
| 法律评价 | 合理期限内通知 | 必须有适用规则、解释范围和桥接依据；不能当作普通描述算子直接发布 |

金额求和、次数和“所有”容易把缺失记录当完整集合。首版只允许“记录中至少存在两次不同事件”这样的存在性表达；对总额/全部履行的计算要求单独的完整性依据，否则保留未知。时间阈值来自有出处的合同/法律条件，或标为纯描述统计分段；后者不能命名成“及时/违法”。

### 第三步：执行并收集可解释的失败

每个候选用统一索引连接执行，返回 `(unit, binding, source_assertion_ids)`。unit 默认是一个案件中的请求与审理阶段；同一纠纷的不同文书作为关联家族处理。每个 unit 支持计数至多一次，全部绑定见证另外保存。

执行结果分开记录：找到无冲突见证；原文存在明确相反条件；关键身份/参数未知；没有记录见证。最后一种不等于现实中模式为假。存在性模式的一个失败绑定也不能证明所有绑定失败。

困难近邻优先从只差一个原子、对象绑定或时间关系的真实案件取得。候选与近邻是否匹配由程序算；自然语言定义是否允许匹配由独立的原文审查判定。模型审查只能形成待复核标注，不能与专家标注混报。没有足够语义依据时只发布“查询候选”，不宣称法律概念已确认。

开发期允许构造最小变化样例检查程序：把 K1 换成 K2、交换先后时间、把 FOUND 换成 ALLEGED、删除日期、加入明确延期。它们只检查编码行为，不计入真实支持度，也不自动证明法律意义。

### 第四步：通过具体编辑修正候选

允许编辑：统一或分开变量；添加有来源的同一/不同约束；增加/删除一个描述原子；保留缺失限定参数；用登记算子替换展开表达；拆成两个定义；纠正状态范围。禁止根据最终胜败把某条事实重写成更有利的含义。

查询执行器为每个连接和比较节点保存中间绑定。失败时先确定是事实缺失、类型错误、跨对象连接，还是定义本身错误，再编辑相关节点；找不到有依据的局部修复时退出该分支。这个分解式反馈借鉴 RHDA，但我们的反馈来自查询见证和原文审阅，而非任务答案已知的代码输入输出。长依赖链仍可能难以正确生成，因此同时限制展开深度，不能只数表面谓词数。

每轮每个父候选最多 8 个子候选；保留最多 12 个不同结构；每个候选最多 3 轮修正。参数均为可调整的运行预算，不是准确性保证。预算结束仍失败就保存失败原因，不把它强行修成“通过”。

候选排序采用有解释的顺序：

1. 类型/来源/范围及已审核反例测试不通过，拒绝。
2. 在当前发现期审阅样例中，先减少定义与实际匹配不一致的个数；正例与困难反例各单独报告，不使用未知作负例。
3. 不增加已确认语义错误的前提下，优先扩大到不同案件家族的有效见证。
4. 同等证据下选展开结构较短、重复较少的候选。

如果新增语义标签改变了排名，重算全部现存候选；不把早期评分当永久事实。已有审核语义测试不能被后续新名称绕过。

### 第五步：选取模式库

默认保留 v2 的可解码描述长度目标，对通过上述检查的描述模式去冗余：总成本包括定义、每次调用的主体绑定、常量参数和剩余事实。派生概念的展开定义与算子成本也要计入，不能靠把长查询起一个短名字获得虚假压缩收益。

固定被描述的数据 D 为 A 的基础事实记录，最小化 `L(定义库) + L(调用及绑定) + L(未覆盖基础事实)`。原文、来源 ID 和状态始终保留；不能把派生结果反复加入 D 来人为增加压缩收益。确定性算子可重算，算子名称、定义及必要输入必须编码。首版选择器按净节省量贪心加入，再做一次单个加入/删除替换，直到无正收益或预算耗尽；它是可实现的近似，不宣称全局最优。

选择器可多次使用一个模式，但每次用不同实际见证绑定；相同绑定重复调用不增加覆盖收益。这替代 v2 的“每模式每单元最多一次调用”，因为同案可能有多个真实合同实例需要描述。支持计数仍按 unit 去重，两件事不能混为一谈。

该库回答“哪些描述结构值得复用”。有明确法律依据但少见的例外单独登记在 C 的规则/因素库中，不要求它能压缩很多案件才能保留。压缩未选中的候选与原事实仍保存可查，不意味着不重要。

### B 的完整过程

```text
registry = frozen_base_types + reviewed_descriptive_operators
pool = generalize_real_connected_fragments(discovery_cases)
pool += propose_concepts_from_source_packets(registry)

for round in 1..3:
    for candidate in pool:
        compile_typed_bounded_query(candidate)
        execute_and_store_all_bindings_and_sources(candidate)
        separate_witness_absence_unknown_and_explicit_conflict()
        challenge = choose_real_near_misses_and_reviewed_test_cases()
        diagnose_definition_vs_binding_errors(challenge)
    archive accepted definitions and all unresolved failures
    if no candidate can improve within allowed edits: break
    pool = bounded_edits_and_top_structurally_distinct_candidates()

S = select_decodable_dictionary(validated_descriptive_candidates)
freeze_definitions_queries_and_selection_policy()
run_frozen_queries_on_confirmation_cases_without_repair()
```

这一设计比纯 WARMR 枚举增加的是候选概念与表达的获得机制，并非替换关系连接的数学语义。它可能遗漏不符合 LLM 先验的模式，所以程序种子路线持续保留。没有可靠目标标签时，不照搬 ADVENT 的正负目标覆盖或 LRI 的多数支持当接受标准。

### 第六步：标签核验后，才学习结果关联

完整项目仍应回答“哪些组合与结果有关”。但需先确定结果的主体、请求、阶段，保存支持、驳回、部分支持与程序性处置，不能把整案直接压成胜败。第一版选择一种明确请求与阶段的二分类任务，其余不硬编码为失败。

固定 A 的定义。B 可在训练部分的已核验标签上搜索短关系组合，用按案件家族分组的交叉验证比较：只有单事实的模型，与增加组合后复杂度受罚的逻辑回归模型。候选组合的加入依据是验证集对数损失的改善，而非训练支持度或 LLM 判断。正则强度、长度和数量在训练内层确定；最终确认集不参与选择。这样可以检验一个组合是否比组成它的单事实额外有用，而不是重复计算同一信息。

特征表示的是“文书中存在指定状态的绑定见证”；不存在见证不解释为现实中为假，缺失与来源覆盖指标另存。搜索只允许正的见证条件或有明确来源的否定条件，不允许用没有记载推导现实否定。保留相近效果但不同事实构成的候选，让法律审阅判断意义差异；这借鉴受约束子群发现对简短、替代描述的处理。NRI 等零样本规则模型可作为后续候选生成器，但其布尔标签、表达空间和域外表现不足以支持直接替换本项目主算法。

若输入包含判决后的法院事实认定，这一结果只能叫回顾性结果关联；要做判前预测，必须另建只含决策前可用材料的数据版本。关联本身既不是因果效应，也不赋予模式法律效力。

## 5. C：带法源的规则提取、桥接与编译

### 两种来源，明确分开

法规和判例中明确表达的规则，形成带原文依据的候选规则卡。从一组类案归纳出的隐含原则，形成候选原则卡，另存支持与反对案件。两者可以共同用于研究，但统计多数不能给候选原则自动赋予法源地位。

规则卡包含：前提、结论、模态、例外、适用辖区/时间/程序阶段、来源片段、交叉引用、优先关系、桥接定义、未解决解释和审阅状态。机器无法查明时留下缺项，不能用本案结论补齐。

### 规则获得与修正

1. 检索引用原条文及相关例外、定义和交叉引用。形成完整来源包；只取得片段时标记来源不完整。
2. 使用共享事实类型注册表，联合生成前提、结论、例外及槽位绑定。避免先独立造一大套原子、再让第二模型硬拼规则。
3. 将每一个规则成分映射回原文。事实类型无法表达“有效通知”等条件时，明确提出桥接规则需求，禁止用 NOTIFY 自动替换 VALID_NOTICE。
4. 编译器检查变量范围、类型、日期/单位、正负号、模态和支持链有限性。这里通过只代表形式上可执行。
5. 对照原文形成行为测试：全部条件满足；删除一个必要条件；例外成立；同样事实发生在不同合同；规则时间/辖区不适用；显式否定与未记载。测试预期必须由原文及独立解释支持；含糊项提交法律审阅，不能由生成模型自问自答后宣布正确。
6. 对每个失败给出最小差异：丢了哪个条件、哪条引用未展开、哪个绑定错误或例外方向错误。只允许按这些证据增删条件、修复绑定、展开引用或拆分规则。每卡最多 3 个版本；仍有解释分歧保留不同解读，状态未决。
7. 新规范性规则、解释性桥接及优先关系须经过项目法律审阅后进入正式规则库；自动候选可在明确标记的研究模式执行，不冒充审阅通过。

保留 v2 的受限 ASPIC+、显式攻击与 grounded 标记，用审核后的规则实际推理。例外未知按该规则审核过的默认方式处理，不统一假设未知即无例外。C 直接读取 A 的全部适格事实；B 只帮助定位可能相关的关系和案件，不能代替必要前提或重复增加证据权重。

### 实际怎样产生结论

每项请求建立独立的有限论证图：节点是“原文事实经过哪些规则推出什么”的完整支持链，边表示一个论证反驳另一个论证的前提、结论或规则适用性。明确规则区分不可推翻的演绎规则与可被例外推翻的规则。来源层级、时间或具体规则的优先关系只按已审核规则使用，模型不能凭语气决定优先。

把攻击及已审核优先关系转换为有效反驳关系。先接受没有有效反驳者的论证，拒绝被已接受论证有效反驳的论证，再接受所有反驳者已被拒绝的论证，重复到状态不变；剩余标为未决。这是 grounded 标记的有限图计算。优先关系如何作用于支持链沿用明确的 last-link 方式，即按冲突结论所依赖的最后可推翻规则比较；未定义优先则保留冲突。

例外卡必须写清是“只有证明例外才阻止默认规则”，还是“必须证明例外不存在才允许规则”。两种方式在例外未知时会产生不同结果，不能由程序偷偷选择。最终逐项输出已接受的支持、已接受的反对、未决争议、缺失前提及来源链；无支持论证不是相反结论成立。规则无法完整形式化时，只显示来源与待解释条件，不自动生成结论。

并非所有法律因素都是必要条件。一项因素若仅支持或削弱一方，保存其方向、强度描述、适用请求和依据，不改写成“该因素成立就必然胜诉”。类案比较先列共同因素与重要区别，再由有来源的论证规则连接到支持/反对；缺少这样的规则时只输出可检查的类比候选。来源只给定性强弱时不捏造数值权重；多个因素也不默认相加。缺失事实可以成为待查问题，不能通过溯因猜测后回写成已知事实。

### 为什么有必要

若规则把“通知”误写成“有效通知”，再严密的推理引擎也只会稳定地算出错误结论。本版把算法预算从增加引擎复杂性转向规则与桥接翻译的具体错误，并给出能定位错误的修正操作。它仍无法仅靠程序证明法律解释正确。

## 6. 贯穿实例：日期差怎样成为可复用概念

以下全部是构造的解释材料，规则也是虚构的，不是任何真实法域的法律意见。

| 文书记载 | A 保存 |
|---|---|
| 法院认定买方于 5 月 1 日付清 K1 价款 | FOUND paid_full(buyer, seller, K1, May1) |
| 法院认定 K1 的交付期限为 5 月 10 日，至 5 月 12 日仍未交付 | FOUND due(K1, May10)；FOUND not_delivered(K1, May12) |
| 法院认定买方 5 月 11 日就 K2 发出通知 | FOUND notify(buyer, seller, K2, May11) |
| 买方称 5 月 11 日也就 K1 发出了通知，法院未解决 | ALLEGED notify(buyer, seller, K1, May11) |

B 的一个错误候选只写“已付款 AND 逾期未交付 AND 已通知”，丢掉共享合同变量。程序会给出 K1 的付款和 K2 的通知。来源审查指出该绑定不符合“针对同一合同催告”的定义；修正操作是统一三个合同变量。修正后，这个案件在 FOUND 通道没有完整见证，不能把 ALLEGED 通知补成 FOUND。

另一些案件确有同合同的通知和到期日期。系统提出 `notice_offset(K, Δ)`，定义为通知日期减到期日期并要求同 K、同一通知事件范围和明确日期。Δ=1 只表示晚一天，不自行推出通知有效。定义通过参数与绑定测试后，可供其他模式复用。

给定一条虚构规则：“在指定适用范围内，交付到期且未交付，并经有效通知，满足要件 E；经认可的延期构成例外。”C 会要求 due、not_delivered、valid_notice 及例外语义。它可以通过 B 找到候选通知，但仍须取得“有效”的桥接依据。上述 K1 缺少认定通知，更缺少有效性依据，因此输出缺失前提，不输出要件成立。

这段例子的收益不在于生成一个好听的 factor 名称，而是同一条定义的候选、绑定错误、修正和规则前提都能逐项检查。

## 7. 三个模块怎样反馈，怎样停止

开发和发现期：B/C 发现“已有类型无法表达某项有原文依据的区别”，可提交定义或算子需求给 A；A 只能依据原文与已批准的抽象政策修改，不能为提高模式胜败关联而改写事实。C 的法源可以提示应检查哪些条件，但本案结果不能成为 A 的输入。

每轮发布固定版本。定义、实例绑定或规则改变后，重算所有依赖项，包括之前未匹配或被剪枝的候选。首版对限定领域全量重算，避免伪装有完整增量算法。

进入独立确认集后，类型、模式定义、选择政策及规则包冻结。确认集只运行和计错，不用于修复；需要修复时另起版本，旧确认集降为已见数据。

全局停止条件是声明的调用/审阅预算或迭代上限耗尽，以及一轮没有通过接受条件的编辑。停止不是全部问题已解决；未决项以原文、候选和缺失条件交付。

## 8. 文献实际怎样改变设计

本次复核的是下面的方法、实验及相关消融段落；未运行作者代码，不声称穷尽近两年所有论文。先前更广文献清单保存在 v2，不能把清单数目当作深读数量。

| 近期工作 | 本次检查与具体采用 | 没有照搬的部分 |
|---|---|---|
| [Cequel，2025 v2](https://arxiv.org/html/2504.15640v2) | §4–7：把有限查询用在信息量较大的比较，处理模型约束噪声。影响 A 的审查预算设计 | 文本主题/意图同类不等于法律事实等价；不直接套固定 k 聚类 |
| [LLM-generated constraints，AAAI 2026](https://arxiv.org/html/2601.11118v1) | §4–5：批量约束与噪声容忍说明“逐对全验＋硬约束”不是唯一选择 | 模型高置信不自动升为不可违反的法律约束；本文采用明确结构区别作为硬条件 |
| [ClassMATe，TACL 2025](https://aclanthology.org/2025.tacl-1.55.pdf) | §3.2–3.4、算法1及实验：定义驱动分类，困难样本反馈修改定义。影响 A 的主结构 | 不用平均模型不确定性下降接受新定义；改用已审阅实例和反例回放 |
| [LLM-Automated Language Bias for ILP，2025/2026 v2](https://arxiv.org/html/2505.21486v2) | 方法及 MAXSYNTH 附录：把谓词和搜索语言的获得视为算法部分 | 我们无已核验目标标签，不照搬监督误分类目标 |
| [ADVENT，2026 预印本](https://arxiv.org/html/2607.01585v1) | §III、表I及§V：可执行定义、具体执行反馈、概念复用。影响 B 的候选与修正 | 论文部分增益来自给基线补不等式/算术；不能假称对已有这些算子的 v2 同样增益。自定义描述发现接受条件 |
| [Argumentation and Judgement Factors，EACL 2026](https://aclanthology.org/2026.eacl-long.128.pdf) | §2、§3.5–3.7：法律概念生成、批评和修正应是发现过程的一部分 | 模型判断支持哪一方只是候选信息；真实绑定、来源与法律依据仍另验 |
| [LRI/SILVER，2026 v2 预印本](https://arxiv.org/html/2505.14104v2) | §3.3、§5.2及提示：检查已有原则覆盖后再补充。影响 C 的隐含原则候选队列 | 多数支持与 LLM 判定不产生法源地位；论文更复杂可推翻规范不在其当前设定中 |
| [Legal Text Formalization into DDL，2025 v3](https://arxiv.org/html/2506.08899v3) | §4.4–4.5、§5：联合形式化与后续修正、完整规则匹配和跨段引用困难。影响 C 的具体翻译流程 | 不把先抽原子、多模型或多阶段本身当优势；程序测试不能证明解释正确 |
| [AutoSchemaKG，ACL 2026](https://aclanthology.org/2026.acl-long.942.pdf) | 方法与 Appendix E：实例、事件和概念表示及消融。支持明确分层的必要性 | 同预算消融中并非每任务均明显改善；不给复杂概念图自动赋予价值 |
| [GrOIL，2026 预印本](https://arxiv.org/html/2608.22135v1) | §3–4：图证据、类型化生成、来源链及合成保险合同评价 | 不采用其后续完全不回看原文的限制；法律解释修复仍需原文 |

本设计属于已有机制的有理由组合与任务适配。潜在贡献要落在“如何发现并修正会影响法律比较的语义边界与关系定义”，不能仅用 LLM＋验证器＋法律数据宣称新范式。

后续补查已实际影响 A 的修正操作、B 的查询局部诊断及结果关联分支：GraphRefine、RHDA、DeLFGCD、KGGen、GraphJudge、UniPred、NRI、受约束子群发现，以及法律因素发现等工作的阅读范围与取舍另见[检索覆盖与独立选型](检索覆盖与独立选型.md)。该记录同时列出只完成初筛的论文，不能把所有条目都说成已精读。

## 9. 目前能支持的判断

本版明确修复三个设计缺口：A 不再以尽量保留模型 EQ 边作为主目标；B 能提出原有词表外的描述关系并执行、修正；C 将原有规则获取与审阅细化为可定位错误的翻译、桥接和修正流程。它比 v2 在研究问题与机制之间的对应更完整。

我们仍没有在真实法律数据上的优势结果。最重要的成本也很明确：需要一小部分独立原文审阅来判断语义修正是否正确；没有这些依据，自动反复修改只会得到更自洽的模型输出。自动候选生成和程序执行可以先实现，但不能用自评填补这项证据。

## 10. 相对项目文档备选方案的具体理由

这里给出机制上的选择理由，不是尚未做过的性能结论。

- **Embeddings＋LLM 合并**：继续用于找到候选和判断语义，但最终对明确、可复核的定义归类，避免 A≈B、B≈C 就链式合并。项目文档本来已有保守合并与边界检查；我们补的是启动、编辑、接受和重算机制。
- **DBSCAN 等距离聚类**：可做候选分组，不能直接定义法律等价，因为距离不能保证保留极性、角色、状态和对象范围。聚类质量不能只看轮廓系数。
- **FP-Growth**：适合已正确构造的离散项。但先把每案变成“有付款、有通知”的袋子会丢掉付款和通知是否属于同一合同。我们的执行器先保留变量绑定；如果输入项已经是经核验的绑定关系，FP-Growth 仍可作为高效枚举部件，无须否定。
- **gSpan**：可枚举图结构，但节点/边如何规范、时间和数值怎样表达、哪些组合值得解释仍需另解。真实子图种子可复用该类搜索思想；新设计增加概念提议与有依据的局部修正。
- **ANCO-HITS 等排序路线**：本文尚未核验文档所指的准确版本及其完整设定，因此不声称已证明替代算法更好。无论使用何种排序器，排名高也不能替代对象绑定、原文或法源证据。
- **让 LLM 直接解释结论**：可帮助起草候选和语言说明。正式计算保留显式前提、例外与反驳，是为了区分“缺前提”“有反证”“解释分歧”，而非只得到一个流畅答案。

## 11. 实施顺序与验证条件

先做一个领域内的小型端到端版本，不同时覆盖所有案由。已有文件名不能证明案件都属于同一领域。按同一纠纷的关联文书分组，排除空文书，核对 facts 字段与原文一致性，再划分开发、发现和独立确认数据；具体数量依可用样本与审阅预算确定，不把 6954 条文书等同于 6954 个独立案件。

第一批实现共享对象、来源索引、A 的开放抽取与定义注册表；第二批实现 B 的受限语法、精确匹配、程序种子和 LLM 候选；第三批加入错误定位与局部编辑；同时用少量经审阅法源贯通 C。优先贯通“付款—同一合同—通知—例外”的结构测试，然后换成真实领域的事实与规则。没有 outcome 标签时关闭结果关联模块，不用模型生成标签自证有效。

验证对应每个预期收益：

| 主张 | 必须观察的证据 | 失败后怎样处理 |
|---|---|---|
| A 能减少误合并和漂移 | 固定审阅预算下，原文支持的映射准确率、危险误合并、漏归并、未决比例和版本回归；另外核对抽取召回率 | 分开定位抽取、定义、检索错误；不以全部拒绝换取高精度 |
| B 新概念与局部修正有价值 | 同候选/调用预算下，有效新关系、真实跨案复现、错误绑定率；概念生成与局部编辑分别移除后是否变差 | 没有净收益就保留更简单的程序种子；不能靠增加 LLM 调用量归因 |
| B 组合有额外预测信息 | 标签核验后，在未参与发现的数据上改善单事实模型；按纠纷家族估计不确定性 | 无稳定改善则只称描述模式，不称预测因子 |
| C 翻译和推理忠实 | 独立法源审阅、必要条件/例外/绑定测试、支持链可回溯，以及未知时是否适当未决 | 翻译错误回到来源；不能靠修改引擎把答案调成法院结果 |

当前没有运行上述真实数据实验。开发期反复使用的审阅样本是训练与修正依据，不能再次作为独立正确性证据。交付时同时给出自动接受、人工确认和待审数量，避免把保留下来的原文记录误说成已进入正式推理。


--- 独立算法报告全文结束；阅读覆盖记录开始 ---

# 检索覆盖与独立选型

2026-09-29 的独立检索记录。现由用户重新授权，与 Pro 讨论完整方案；网页答复本身不作为论文结论的证据。

## 搜索范围与阅读边界

主时间窗为 2024 年末至 2026-09-29，同时保留直接相关的稍早基础工作。检索覆盖：开放信息抽取与规范化；主动聚类与新类别发现；定义修正与模式归纳；谓词发明与程序学习；受约束子群发现；法律因素、规则获取、非单调论证；法律知识图谱。使用论文原站、ACL Anthology、NeurIPS/ICLR/IJCAI/PMLR、arXiv、作者页面及论文参考文献追查。未用 Reddit 或二手摘要支持方法选型。

这是跨方向的定向文献调研，不是注册过检索协议的系统综述，也不声称搜全近两年所有相关论文。下面区分核读方法、初筛和采用；未复现任何作者代码。主方案第 8 节记录了此前十项近期工作的阅读与取舍，本文件记录补查及对选型的影响。

本轮具体搜索词组包括 `knowledge graph canonicalization`、`schema induction`、`active generalized category discovery`、`relational concept learning`、`predicate invention`、`logical rule induction`、`subgroup discovery`、`legal factors`、`legal rule extraction`、`legal abductive reasoning`，搭配 2025/2026；进一步追查 KGGen、GraphJudge、UniPred、NRI、ICAIL 2025 论文及作者列表。

## 核读了相关方法的补充工作

| 工作与原始来源 | 阅读范围 | 对本方案的实际决定 |
|---|---|---|
| [GraphRefine，ACL 2026](https://aclanthology.org/2026.acl-long.1353.pdf) | §4、操作定义、实验和操作消融 | A 明确区分保留、纠错、含义不变的改写及排除。不能把监督训练过的修正器成绩当作我们提示词版本的成绩 |
| [RHDA，ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/file/eeffa70bcbbd43f6bd067edebc6595e8-Paper-Conference.pdf) | 分解—执行—修正流程、实验消融、失败分析 | B 保存查询节点中间绑定，按错误位置局部修改。借鉴程序假设的分解与执行反馈，不声称迁移效果已成立 |
| [Expressivity-graded Logical Theory Induction，AAAI 2025](https://ojs.aaai.org/index.php/AAAI/article/view/34546/36701) | 方法、算法1、合成数据设定和实验设计 | 不只限制候选表面长度，也限制展开依赖深度；有标签的理论恢复与我们无标签的描述发现分开 |
| [KGGen，NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/file/2b368455e832d2b1a60bcad8c4c6481f-Paper-Conference.pdf) | §4 抽取、汇总、实体/关系解析与 §5 评价设定 | 混合检索及别名归并是可用部件；不能把更密的图或更好的检索自动视作法律事实等价正确 |
| [GraphJudge，EMNLP 2025](https://aclanthology.org/2025.emnlp-main.554.pdf) | 实体中心去噪、监督判断器、判断算法与相关分析 | 支持抽取后单独检查，但首版不依赖训练专用判断器；不先删掉可能承载例外的上下文，只做检索视图 |
| [DeLFGCD，EACL 2026](https://aclanthology.org/2026.eacl-long.358.pdf) | §3 实例/类别反馈与对比学习、反馈质量分析 | 定义卡与实例边界应共同检查。暂不微调检索编码器；若审阅后发现检索漏掉真实类别，再用已审阅正反对学习检索，不用模型相似标签直接决定最终类别 |
| [UniPred，2025 预印本](https://arxiv.org/html/2512.17992v1) | §IV-C 作用效果监督与双层学习、§V 结果和消融 | 有价值的是候选要受独立数据约束；本项目没有机器人状态转移，不能直接搬其损失函数。其反馈消融也不支持“多反馈必然更准” |
| [NRI，IJCAI 2026；核读 arXiv v1](https://arxiv.org/html/2605.04916v1) | §4 输入统计与子句生成、§5 域外/噪声/复杂度实验 | 可作为未来有标签的组合生成备选；当前依赖布尔输入和标签，不能解决我们的对象绑定与语义定义。论文域外表现也不足以支持直接替换 |
| [受约束子群发现，2025 扩展稿](https://arxiv.org/html/2406.01411v2)；[SIGMOD 正式记录](https://publikationen.bibliothek.kit.edu/1000182481) | 扩展稿问题定义、束搜索、特征数限制及替代描述；正式版机构摘要 | 在结果关联模块中控制组合大小并保留不同事实构成的替代解释。正式版全文本轮获取失败，不能声称逐页读完正式版 |
| [Using LLMs to Discover Legal Factors，JURIX 2024](https://arxiv.org/html/2410.07504v1) | §4–6，包括人工/LLM 修订及错误因素分析 | 法律因素候选应追查相关请求、阶段和法院实际理由；重复出现不等于法律因素。保留罕见但有理由支持的候选，避免全由频率筛选 |

原有重点论文仍包括 EDC、ClassMATe、Cequel、LLM-generated constraints、LLM-Automated Language Bias、ADVENT、EACL 2026 Argumentation and Judgement Factors、LRI/SILVER、DDL Formalization、AutoSchemaKG、GrOIL。它们不是孤立的论文名单；采用与不采用的机制见[主方案第 8 节](算法重设计.md)。

## 已找到并初筛，尚未据此采用新算法

| 工作 | 本轮覆盖及处理 |
|---|---|
| [Generating Legal Arguments with Automatically Identified Factor Magnitudes，ICAIL 2025](https://researchonline.stthomas.edu/esploro/outputs/conferenceProceeding/Generating-Legal-Arguments-with-Automatically-Identified/991015404088303691?institution=01CLIC_STTHOMAS) | 核对机构记录和摘要。不能把因素全部压为布尔值；目前不据摘要引入新的强度估计算法。作者页面的该标题链接实际指向另一篇旧论文，已区分 |
| [Neurosymbolic Methods for Rule Mining，2025 章节](https://arxiv.org/abs/2408.05773) | 摘要与方法分类；用于扩展搜索到路径泛化、优化及神经规则学习，不当作具体方法证据 |
| [Neuro-symbolic Predicate Invention，2025](https://journals.sagepub.com/doi/10.3233/NAI-240712) | 搜索条目及作者摘要层面；未据此宣称某套视觉谓词学习优于本项目方案 |
| [Description Logic Concept Learning using LLMs，NeSy 2025](https://proceedings.mlr.press/v284/barua25a.html) | 读官方摘要，PDF 工具读取失败。不是已深读采用工作 |
| [ACAL，Canadian AI 2026](https://proceedings.mlr.press/v318/cao26b.html) | 官方摘要；暂不增加多代理辩论组件，因没有核验其对规则翻译正确性的实际增益 |
| [LLMs for legal reasoning: A unified framework，2025](https://www.sciencedirect.com/science/article/pii/S2212473X25000380) | 官方摘要与框架说明，作者存档 PDF 403；确认需区分规则、类案与溯因，不声称本文方法已完整复核 |
| [Indonesian sentencing hybrid KG，2026](https://link.springer.com/article/10.1007/s10506-026-09507-8) | 读到方法与数据范围；没有检查全部实验，不引用其效果数值作为选型证据 |
| [CLaw，EMNLP Findings 2025](https://aclanthology.org/2025.findings-emnlp.646/) | 摘要与官方记录；属于法条知识和应用评价，不是直接替代 A/B 的发现算法 |
| [ANDRE，2026 预印本](https://arxiv.org/abs/2605.04193) | 搜索初筛；未读方法，不据此排除可微关系学习 |
| [Regulated procurement with Logic Tensor Networks，2026 预印本](https://arxiv.org/abs/2604.05539) | 搜索初筛；后续软真值规则研究候选，当前不采用其语义 |

## 独立选型后的结论

A 采用定义约束的开放类别归纳与版本修正；B 采用有来源的关系种子、受限概念提议和局部程序修正，并将描述发现与有标签的关联学习分开；C 采用法源规则卡、桥接需求、独立翻译测试和可追溯论证。保留精确关系执行，是因为对象绑定与计数需要确定语义，不是因为经典算法天然优于新方法。

新工作改变了候选从哪里来、错误怎样定位、类别怎样修正以及反馈如何使用。没有采用某套完整模型，可能是缺少它要求的监督或其输出不能直接表达本任务，不是因为“任务不同”就否定全部机制。首版不同时加入所有有趣模块；每个新增组件必须对应一个明确失败原因。


--- 阅读覆盖记录结束 ---


## 4. 在读完全文之后，请实质解决这些设计缺口

这些不是让你脱离项目回答的短问题；请把答案融入完整 A/B/C 方案，确保接口、状态、搜索目标与法律语义相互一致。

### A：定义驱动规范化是否真正比保守成对合并更合适

完整方案已给出冷启动、卡片内容、候选检索、槽位核查、同义/父子/兄弟区别、主动审阅、局部编辑、版本回归和重算。请检查它会不会只是把原来的 pairwise 错误变成定义的系统性错误。要保留什么独立原文审查和随机抽样，才能发现检索遗漏、错误卡片和自我强化？类型归属允许参数不同，严格等价要求声明抽象政策下签名相同；请明确这与原文 canonical predicate 的目标如何对应，哪些区别应留在类型中、哪些放参数、哪些成为 family，不能把“付款类型”当成全部付款事实可以合并。

v3 的一个具体不足是“未解析的限定先保存在原文、严格等价待定”还不够：B/C 可能继续用其他已解析槽位，实际忽略该限定。请给出可执行的依赖阻断规则。例如“已付款，但仅针对另一笔债务”不能因为 payment=true 就用于当前债务清偿。我们倾向把限定绑定到特定断言、字段、事件/债务；无法确定作用域时阻止依赖该断言的使用，而非封锁整案。查询需要声明读取的语义条件和字段。哪些使用可以安全继续、哪些必须 UNKNOWN、遇到其他独立见证如何处理，请具体说明。仅由 LLM 猜测“不相关”不应自动解除阻断。

同时分开来源陈述状态 FOUND/ALLEGED/…、机器映射状态、人工审阅状态。机器自动接受不是原文法院已认定，更不是专家审阅通过。输出保存和计算使用应分开。

### B：选定一个默认搜索过程，解释搜索空间、目标与反馈

我们现在倾向以真实连通子图的带类型泛化为主要种子，辅以受预算约束的 LLM 描述概念提议，用来源/程序执行失败做局部编辑。WARMR 风格穷举不作为主路线，但可以做小语言空间的召回基线或补充。请独立判断这个决定；如果你认为应反转，就解释何种条件使其更合理。不能两套都赞同而不决定。

需要写清：种子取样→对象对应/反统一→变量规范化去重→候选定义→编译→真实绑定执行→来源审查与困难近邻→局部编辑→排序→停止→冻结→独立确认。我们的预算初值是每家族50片段、每桶100片段对、候选展开最多6原子/6对象变量/2层、每父8补丁、beam12、3轮；这些是运行预算，允许更合理调整，不能假称论文证明最优。单纯按原子排序后首次出现重命名未必能对图结构完整去重；在6变量小范围内按类型枚举重命名取规范最小串是否足够可实现？

关键：候选的自然语言意图固定，修程序不能为扩大覆盖悄悄改意图；改意图算新候选、重做语义审核。真实查询未匹配≠现实反例；一个错误绑定≠一个案件不存在有效绑定。对象、合同、债务、通知/付款事件必须准确连接。同案共现和共享case_id不是关系证据。请说明无监督情况下怎样判断“有用”，哪些只说明描述复用、哪些需要法律来源或标签；避免把词义正确和压缩有效混成一个分数。

请明确分开两个库：G=通过语法/来源/语义检查、可执行的描述关系库，S=从G选择的压缩描述字典。S没选中不意味G关系无价值；C的罕见法定例外不能被MDL删除。

MDL（最小描述长度）必须是可实现的真实编码目标，不只是给模式和事实拍几个价格。固定D为A发布版本的基础事实，写清哪些数据在编码对象中，哪些公共来源表作为同样计费的头部，模式定义、常量、变量绑定、实例/出处ID、状态、限定和残余怎样编码，重叠模式怎样还原同一条事实而不重复增加证据。允许同模式多绑定，但支持度每unit一次。不能把派生关系再放入D人为增加收益。候选的首次加入应与一组实际使用联合算净收益，不能因为第一个token还未摊薄整个定义就错杀候选。请给最小可解码编码结构、贪心覆盖/选集的具体规则和停止条件，明确是近似、不是全局最优。若首版不值得实现复杂重叠编码，请直接选择更简单可验证方案并说明代价。

有真实outcome后，如何使模式选择与“比单事实更有额外信息”对应？我们暂定训练内按纠纷家族分组验证、正则逻辑回归比较单事实与增加组合，最终确认集不修正。请核对与PDF的胜败分别挖掘如何对应；不能简单取消PDF目标，也不能把所有胜败共现写成规则。

### C：法源解释、桥接及可推翻推理需要一致语义

C必须涵盖获取算法，而不只是拿到规则后调用引擎。法源包包含正文、定义、例外、引用、辖区、有效时间、适用阶段以及法院如何使用该来源。RuleCard与BridgeCard联合生成，每个前提/结论/例外都回指来源；桥接是“描述事实如何满足法律条件”，如寄出、实际收到、依法视为收到、有效通知必须分开。独立来源测试与解释审核后才发布规范性规则；模型自己生成测试又自己判通过不是独立验证。隐含原则只作为重建/归纳假设，不自动拥有法源效力。

你上一轮提到对未知例外设置gate，若全部如此会改变通常可推翻默认推理。我们的偏好是每条规则显式审核例外策略：一种是证实例外才形成攻击、未知仍可形成默认论证；另一种要求证实例外不存在才满足前提；没有法源/审阅依据确定策略时保留未决。请决定正式论证计算与谨慎报告的边界，不能计算时允许默认、展示时偷偷把它当确定无例外。存在相反论据时交给已声明的攻击/优先关系和grounded语义，不凭LLM信心决定胜负。哪些情况下可用受限ASPIC+、last-link，哪些需要人工解释而首版不支持，请写清。

不是每个factor都是必要或充分条件。对“只支持/削弱某一方”的因素，如何保存方向、适用争点、程度描述、来源以及与其他因素的关系？不能全转成足以推出胜诉的Horn规则，不能从频次自动学法律权重。无法形式化时应交付可审查的因素/论证候选，而不是伪造完整判定。

### 系统与研究贡献

请挑出最值得首版实现的核心机制，列出删除或延期的部分，防止所有论文各借一个组件造成无法归因的复杂系统。只选一个首要贡献假设，并说明与最接近工作的实质差异及怎样证伪。把“系统工程需要做的”“可能是论文贡献的”“已有标准机制”分开。

当B/C发现缺少债务归属、收到时间等原文已有字段时可以回A补抽；但不能因预测结果更好而改A语义。A改动后依赖的失败候选和负向/未匹配结果也需要重算，不只成功输出。小领域首版可以全量重算，别假装已经有复杂增量算法。探索集可修、确认集不可修；版本变化后的MDL比较也必须重新固定D。

## 5. 要贯穿执行的例子

用一个明确标为虚构的规则和几份构造材料，把A→B→C执行到输出，而非只画模块框。
例子至少覆盖：同一案件有K1/K2两份合同；同一合同有D1/D2两笔债务；通知寄出与收到日期不同或收到未知；一笔付款可能部分支付，也可能全额但用于D2；原文对款项撤销/有效延期的例外没有交代；有一个事实只是当事人主张；来源中的“有效通知”需要额外法律条件。
先展示错误候选会怎样误匹配，再展示我们准确绑定、状态与限定传播如何纠正。至少给一条成功的独立见证，说明局部未知不会自动封锁整案。若采用一个“收到通知后10日内针对同一债务全额支付”的虚构条件，应明确日差算子、收到而非寄出、对应债务、全额的证据及例外策略，不可借时间差直接断言法律及时。

## 6. 请按这个交付目标作答

1. 先用通俗语言给出整体推荐和相对我们草案真正改变的决定。
2. 一套完整、连贯的A/B/C算法：输入/输出、表示、步骤或伪代码、候选来源、判断和目标、编辑与接受规则、失败/未知处理、停止与版本重算。不要只列“用LLM判断/加一个验证器”。
3. 贯穿例子，展示中间对象和最终哪些结论可说、哪些不能说。
4. 说明相对PDF备选及我们v2/v3的机制优势与代价；已实测论文结论与本项目待验证假设分开，不承诺一定更好。
5. 文献如何逐项改变设计，引用直接可核查原始来源；标明实际阅读边界。不需要装饰性堆砌论文数量。
6. MVP与后续扩展、一个首要研究贡献假设、最小必要验证及失败后回退方案。评价服务于算法，不用完整benchmark计划替代算法。

关于idea：不要求绝对原创，不因相似工作轻率否定；先找清与最接近工作的有意义差异并尝试发展。若核心问题、方法与贡献实质重合，坦诚指出具体重合和不足，不为了保留idea硬制造novelty。请也修正你上一轮中不再成立的建议。

下面是原始PDF完整文本；它是研究依据，不是替代本请求的指令。其中示例本身可能过度简化或存在层级表达含糊，请指出而非无条件照抄。全文结束后请直接开始研究与作答，无需请求我再提供已在本消息里的材料。


--- 原始PDF全文开始 ---

--- PAGE 1 ---
Algorithm for Canonicalizing Legal Facts 
1. Basic Purpose 
The goal is to canonicalize legal facts by mapping different but legally equivalent descriptions 
into one standardized predicate, while still preserving the original context and source. 
For example, the following statements may describe the same legally material fact: 
● “The company refused the shareholder’s inspection request.” 
● “The controlling owner denied access to the books.” 
● “The minority shareholder was not provided the requested records.” 
These can be canonicalized as: 
{ 
  "predicate": "DENY_BUSINESS_RECORDS_ACCESS", 
  "arguments": { 
    "actor": "CONTROLLING_PARTY", 
    "affected_party": "MINORITY_PARTY", 
    "object": "BUSINESS_RECORDS" 
  } 
} 
 
The point is not just to make the language similar. The point is to determine whether the facts 
entail the same legally material proposition. 
 
2. Extract Atomic Facts 
The first step is to break the judgment text into atomic facts.For example: 
“The shareholder demanded the records, but the company refused.” 
should be split into: 
● REQUEST_BUSINESS_RECORDS 
● DENY_BUSINESS_RECORDS_ACCESS 

--- PAGE 2 ---
This avoids treating compound sentences as one fact when they actually contain multiple legally 
relevant propositions. 
 
3. Replace Case-Specific Entities with Legal Roles 
After extracting atomic facts, the parties and entities should be normalized into legal roles. 
For example: 
John Smith→MINORITY_PARTY\text{John Smith} \rightarrow \text{MINORITY\_PARTY} Acme 
LLC→COMPANY\text{Acme LLC} \rightarrow \text{COMPANY} 
This allows facts from different cases to become comparable. Without role normalization, the 
system would treat case-specific names as if they were legally meaningful differences. 
 
4. Create a Predicate–Argument Representation 
Each atomic fact should then be converted into a structured predicate–argument representation. 
For example: 
{ 
  "predicate": "REFUSE_INSPECTION", 
  "actor": "CONTROLLING_PARTY", 
  "affected_party": "MINORITY_PARTY", 
  "object": "CORPORATE_RECORDS", 
  "polarity": "affirmed", 
  "modality": "court_found", 
  "time": "after_valid_demand", 
  "issue": "inspection_rights", 
  "element": "denial_of_access", 
  "source": "case_17_paragraph_42" 
} 
 
This structure is important because facts should not be compared only by surface wording. The 
system also needs to know the issue, legal element, roles, object, polarity, modality, and 
source. 

--- PAGE 3 ---
Alleged facts, disputed facts, and court-found facts must be kept separate. A party allegation 
should not automatically be merged with a fact that the court actually found. 
 
5. Block Candidate Facts by Legal Context 
The system should not compare every fact with every other fact. Before using embeddings or 
the LLM, facts should be blocked by legal context. 
Only facts with compatible features should be compared, including: 
● issue 
● claim 
● legal element 
● argument roles 
● object type 
● polarity 
● modality, where relevant 
This is necessary because two facts may sound similar but belong to different legal issues or 
have different legal consequences. 
 
6. Use Embeddings to Suggest Candidate Merges 
After blocking, embeddings can be used to retrieve plausible candidate pairs for merging. 
The fact should be embedded together with its legal context: 
v(f)=Embed⁡(predicate,roles,issue,element,authority context)v(f)= \operatorname{Embed} 
(\text{predicate},\text{roles},\text{issue},\text{element},\text{authority context}) 
The similarity score can combine semantic similarity with structural and legal-context 
compatibility: 
S(fi,fj)=α embedding similarity+β role compatibility+γ legal-context compatibilityS(f_i,f_j)= 
\alpha\,\text{embedding similarity} +\beta\,\text{role compatibility} +\gamma\,\text{legal-context 
compatibility} 
Embeddings only suggest possible merges. They should not decide the merge by themselves. 
 

--- PAGE 4 ---
7. Use the LLM as the Merge Adjudicator 
The LLM should act as the expert for deciding whether candidate facts are legally compatible. 
For each candidate pair, the LLM should classify the relationship as: 
● EQUIVALENT 
● PARENT_CHILD 
● RELATED_SIBLINGS 
● CONTRADICTORY 
● UNRELATED 
● UNCERTAIN 
Only EQUIVALENT pairs should be merged. 
For example: 
● “refused inspection” 
● “denied access to the books” 
may be equivalent. 
But: 
● “delayed producing the records” 
● “denied producing the records” 
should probably be treated as related siblings, not equivalents, because delay and outright 
denial can have different legal consequences. 
The LLM should evaluate: 
predicate meaning+actor and affected-party roles+object+issue, claim and element+polarity and 
modality+temporal conditions+legally material qualifications\text{predicate meaning} +\text{actor 
and affected-party roles} +\text{object} +\text{issue, claim and element} +\text{polarity and 
modality} +\text{temporal conditions} +\text{legally material qualifications}
 
8. Cluster Conservatively 
The clustering should be conservative. False merges are more dangerous than missed merges 
because an incorrect merge can corrupt the ontology and later pattern mining. 
A simple bottom-up merge loop is: 

--- PAGE 5 ---
1. Start with one cluster per fact. 
2. Use embeddings to retrieve the nearest compatible candidate pairs. 
3. Ask the LLM to classify the relationship. 
4. Merge only if the pair is classified as EQUIVALENT. 
5. Create ontology edges for PARENT_CHILD and RELATED_SIBLINGS. 
6. Reject merges involving conflicting roles, polarity, modality, or legal consequences. 
7. Continue until no safe merge remains. 
The goal should be high merge precision. Ambiguous cases can remain separate or be sent for 
lawyer review. 
 
9. Prevent Chaining Errors and Semantic Drift 
The main risk is chaining error: 
A≈B,B≈C⇏A≈CA\approx B,\quad B\approx C \quad\not\Rightarrow\quad A\approx C 
A sequence of individually plausible merges can slowly create an incoherent cluster. 
To prevent this, the LLM should not compare a new fact only with its nearest neighbor. Before 
merging, the LLM should compare the candidate against: 
● the cluster medoid 
● the canonical definition 
● representative boundary examples 
● explicit exclusions 
● several existing cluster members 
A merge should occur only if the new fact is compatible with the cluster as a whole. 
 
10. Name Each Cluster 
Once a cluster is formed, choose the most representative fact as the medoid and assign a 
standardized predicate. 
For example: 
{ 
  "canonical_predicate": "DENY_BUSINESS_RECORDS_ACCESS", 
  "parent": "INFORMATION_RESTRICTION", 

--- PAGE 6 ---
  "members": ["fact_17", "fact_29", "fact_81"], 
  "medoid": "fact_29", 
  "confidence": 0.91 
} 
 
Closely related but legally distinct predicates should remain separate children under a broader 
parent category: 
INFORMATION_RESTRICTION 
├── DENY_ACCESS 
├── REFUSE_INSPECTION 
├── WITHHOLD_RECORDS 
├── DELAY_PRODUCTION 
└── PROVIDE_INCOMPLETE_RECORDS 
 
The canonical predicate should remain stable as new facts enter the system. 
 
11. Preserve Provenance 
The original fact should never be replaced. Every canonicalized fact must preserve the mapping 
back to its original source. 
The chain should be: 
Canonical fact→normalized instance→original passage→case and paragraph\text{Canonical fact} 
\rightarrow \text{normalized instance} \rightarrow \text{original passage} \rightarrow \text{case 
and paragraph} 
The system should also preserve every proposed pair, LLM decision, reason, confidence level, 
and cluster change. 
This makes the canonicalization auditable and repairable. 
 
12. Keep Outcomes Hidden During Canonicalization 
WIN/LOSE outcomes should not be used during canonicalization. 

--- PAGE 7 ---
If outcomes are used to decide which facts are equivalent, the ontology will leak the outcome 
into the features. This would make later pattern mining unreliable. 
The correct order is: 
1. Canonicalize facts independently of outcomes. 
2. Freeze or evaluate the canonical fact structure. 
3. Reintroduce WIN/LOSE labels afterward. 
4. Mine recurring fact or authority patterns separately for winners and losers. 
 
13. Mine Outcome-Dependent Patterns After 
Canonicalization 
After canonicalization, winning and losing cases should be split and mined separately. 
The purpose is to discover which canonical fact or authority patterns align with winning and 
losing outcomes. 
The professor mentioned using: 
● FP-Growth 
● gSpan 
● ANCO-HITS 
For graph-based recurring fact and authority patterns, gSpan can be used after the canonical 
facts have been created. The key point is that outcome-conditioned pattern mining comes after 
canonicalization, not before. 
 
14. Evaluation 
The decisive experiment is to test whether the LLM can make sound merge decisions while 
maintaining stable canonical predicates. 
The main things to measure are: 
1. Merge precision 
Are the merged facts truly legally equivalent? 
2. Predicate stability 
Does the canonical predicate remain consistent as new facts enter? 

--- PAGE 8 ---
3. Semantic-drift resistance 
Does iterative merging preserve the cluster’s original legal meaning? 
For the pilot, a few hundred expert-labeled pairs should include: 
● true equivalents 
● closely related siblings 
● parent–child relationships 
● polarity conflicts 
● legally material distinctions 
High-confidence merges can then be sent to lawyers for checking. Ambiguous or uncertain 
cases should not be forced into automatic merges. 
 
16. Summary 
The method is: 
Embedding retrieval→LLM compatibility judgment→cluster-consistency test→canonical 
predicate\text{Embedding retrieval} \rightarrow \text{LLM compatibility judgment} \rightarrow 
\text{cluster-consistency test} \rightarrow \text{canonical predicate} 
In words, we canonicalize facts by converting case-specific descriptions into role-based 
predicate–argument structures, using embeddings to suggest possible merges, using the LLM 
to decide legal equivalence, clustering conservatively under contextual constraints, and 
preserving every mapping back to the original case source. 
Only after this process should WIN/LOSE outcomes be introduced for FP-Growth, gSpan, or 
ANCO-HITS pattern mining. 
 

--- 原始PDF全文结束；完整请求结束 ---
