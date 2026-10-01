# Legal AI 方向 A：文献检索与阅读登记

研究基准日：2026-09-29。近期窗口：2024-09-29 至该日；经典论文另列。

本文件登记本轮实际定位和阅读的核心来源，不是“所有相关论文”目录，也不是自动导出的完整搜索日志。没有运行作者代码或复现实验。用户提供的项目与数据事实不来自本登记中的论文。

## 阅读状态

- **M**：原论文正文主要方法与实验已读，并检查相关评估定义或局限；不表示所有附录逐页阅读，也不表示复现。
- **P**：部分全文已读，逐项说明范围；没有把打开链接当作深读。
- **A**：仅元数据/摘要，或全文访问失败。
- **A+**：正文未得，但另有出版社实质注释或作者方法说明，明确区别。
- **S**：标准中相关规范已读，不计为实验论文。

## 范围与筛选

优先：法律事实/事件/角色/认识状态表示，factor/dimension-based reasoning，本体/schema归纳，开放KG规范化，实体匹配的任务差异，聚类视角和粒度，以及相邻评价方法。以论文全文、作者材料、正式论文集和标准为主。仅泛泛提高法律问答分数而没有表示机制的论文不进A核心方法集；B/C相关工作只作接口或反证。

实际使用的来源包括 ACL Anthology、arXiv、NeurIPS 官方论文集、OpenReview检索、ACM、Springer、Elsevier、CEUR、作者/机构仓库、W3C/OASIS。英文和中文检索；实读论文主要为英文，应用覆盖多国语料。不声称系统遍历了Scopus、Web of Science或中文付费数据库。

纳入预印本，但单列正式发表状态。按标题、arXiv ID、DOI去重；EDC、KGGen、AutoSchemaKG、ATOM等预印本与会议版按同一工作记录。Ontogenia与OntoExtend、iText2KG与ATOM作为相关谱系，不视作独立外部验证。会议页眉的未来日期不构成正式发表已完成的证明。

## 实际使用的代表性查询

- `"legal facts" canonicalization ontology`
- `"factor ascription"`
- `"factor extraction"`
- `"ascribing factors"`
- `ICAIL 2025 factor ascription`
- `"open knowledge graph" canonicalization 2025`
- `"ontology induction" 2026`
- `"text clustering" "2026" "granularity"`
- `法律 事实 表示 事件 角色 本体 大模型 2025 2026`
- `"Doing Things with Factors"`
- `"Semantic uncertainty"`
- `"AnyMatch" "entity matching"`

另对登记中的最近核心论文使用了标题/acronym精确检索和版本/官方会议页核查。宽泛年份词查询出现噪声，随后改为精确标题和引文追踪。

## 定向引文追踪

EDC → CESI；CATO/2026分层论证评价 → 1995/2003 CATO与SMILE；Ontogenia → OntoExtend；French legal ontology → 增量KG/ATOM与法律IE综述；UMR → factuality/FactBank；法律IE综述 → LEVEN和U-CREAT。这里的“向前追踪”是后续相关论文/精确引用检索，不是完整数据库cited-by枚举。

## 逐项登记

### 01. EDC — M

**Extract, Define, Canonicalize: An LLM-based Framework for Knowledge Graph Construction**

版本/发表：2024; arXiv 2404.03868; EMNLP 2024。

原始来源：https://aclanthology.org/2024.emnlp-main.548/

实际阅读：正文抽取、定义、两种规范化模式；实验设置、结果和局限；相关表格截图。

与本项目的区别/限制：开放关系词规范化；不是带法律模态、论元绑定的完整命题等价。

论文关联代码、资源或作者说明：https://github.com/clear-nus/edc

（链接不表示已执行代码；作者说明也不等于论文正文。）

### 02. OLLM — M

**End-to-End Ontology Learning with Large Language Models**

版本/发表：2024; arXiv 2410.23584v1; NeurIPS 2024。

原始来源：https://arxiv.org/abs/2410.23584

实际阅读：正文训练、子图生成与聚合；数据划分、实验、指标；首页会议标注核验。

与本项目的区别/限制：有监督 taxonomy 学习；需要文档—本体子图配对，不是从零成本法律语料学习所有关系。

论文关联代码、资源或作者说明：https://github.com/andylolu2/ollm

（链接不表示已执行代码；作者说明也不等于论文正文。）

### 03. COMEM — M

**Match, Compare, or Select? An Investigation of Large Language Models for Entity Matching**

版本/发表：COLING 2025。

原始来源：https://aclanthology.org/2025.coling-main.8/

实际阅读：正文任务、三类交互、组合方法、数据与主要结果；第3–8页截图。

与本项目的区别/限制：同一现实实体的一对一记录匹配；不是跨案命题类型和多视图概念归属。

### 04. Ontogenia — M

**Ontology Generation Using Large Language Models**

版本/发表：2025; arXiv 2503.05388; ESWC 2025。

原始来源：https://arxiv.org/abs/2503.05388

实际阅读：正文 competency questions、设计模式和生成方案；基准、评估定义及结果。

与本项目的区别/限制：能力问题引导本体生成；CQ可表达不等于所有公理正确。

论文关联代码、资源或作者说明：https://github.com/dersuchendee/Onto-Generation

（链接不表示已执行代码；作者说明也不等于论文正文。）

### 05. KGGen — M

**KGGen: Extracting Knowledge Graphs from Plain Text with Language Models**

版本/发表：2025; arXiv 2502.09956; NeurIPS 2025。

原始来源：https://papers.neurips.cc/paper_files/paper/2025/hash/2b368455e832d2b1a60bcad8c4c6481f-Abstract-Conference.html

实际阅读：预印本方法、实验；正式论文主要方法、MINE评估及结果截图核对。

与本项目的区别/限制：实体/关系归并与检索效用；不是独立法律重要差异保留测试。

论文关联代码、资源或作者说明：https://github.com/stair-lab/kg-gen

（链接不表示已执行代码；作者说明也不等于论文正文。）

### 06. AutoSchemaKG — M

**AutoSchemaKG: Autonomous Knowledge Graph Construction through Dynamic Schema Induction from Web-Scale Corpora**

版本/发表：arXiv 2505.23628（2025，阅读v3）；ACL 2026。

原始来源：https://aclanthology.org/2026.acl-long.942/

实际阅读：正文实体/事件图、概念生成；schema评估与下游实验；Table 8截图。

与本项目的区别/限制：实例可以关联多个概念；标签不自动具有严格is-a或法律等价含义。

论文关联代码、资源或作者说明：https://github.com/hkust-knowcomp/autoschemakg

（链接不表示已执行代码；作者说明也不等于论文正文。）

### 07. ATOM — M

**ATOM: AdapTive and OptiMized dynamic temporal knowledge graph construction using LLMs**

版本/发表：arXiv 2510.22590（2025）；Findings EACL 2026。

原始来源：https://aclanthology.org/2026.findings-eacl.49/

实际阅读：正文方法、指标、实验、局限；正式PDF首页与实验表截图。

与本项目的区别/限制：原子化、双时间、并行合并；重复运行稳定不等于法律语义正确或长期概念稳定。

论文关联代码、资源或作者说明：https://github.com/AuvaLab/itext2kg

（链接不表示已执行代码；作者说明也不等于论文正文。）

### 08. Hierarchical legal reasoning — M

**Thinking Longer, Not Always Smarter: Evaluating LLM Capabilities in Hierarchical Legal Reasoning**

版本/发表：arXiv 2510.08710（2025），阅读v2（2026-01）；CSLAW 2026。

原始来源：https://arxiv.org/abs/2510.08710

实际阅读：正文CATO形式化任务、合成基准、实验结果与局限。

与本项目的区别/限制：输入已给定factor；支持论证图不是事实同义词树。

### 09. AAM-CBR — M

**Argumentative Reasoning with Language Models on Non-factorized Case Bases**

版本/发表：arXiv 2512.12656v1（2025-12）；公开预印本。

原始来源：https://arxiv.org/abs/2512.12656

实际阅读：正文按需factor抽取和AA-CBR；合成数据、筛选程序、实验与边界。

与本项目的区别/限制：新案例预先factor化；不证明真实判决上可以无条件省略全局表示。

### 10. Detention factors KG — M

**Factor extraction from pretrial detention decisions by Italian and Brazilian Supreme Courts: A knowledge graph perspective**

版本/发表：Computer Law & Security Review 61 (2026), 106280。

原始来源：https://cris.unibo.it/handle/11585/1054471

实际阅读：机构开放PDF正文：factor来源、摘要和KG流程、评价及实验表。

与本项目的区别/限制：预定义factor且部分选择依赖outcome；不是无标签事实概念归纳。

### 11. OntoExtend — M

**OntoExtend: A Framework for Requirement-driven and Scalable Ontology Extension with LLMs**

版本/发表：arXiv 2607.17963v1（2026-07）；公开预印本。

原始来源：https://arxiv.org/abs/2607.17963

实际阅读：正文CQ检索、只读原本体/扩展片段、验证；实验、专家评价和局限。

与本项目的区别/限制：39个CQ的受控扩展；实验关闭增量重索引，不是长期漂移验证。

### 12. French legal ontology — M

**LLM-Assisted Ontology Engineering and Construction of a French Legal Knowledge Graph**

版本/发表：arXiv 2607.24551v1（2026-07）；文内注明SEMANTiCS 2026附属session，正式论文集未独立核实。

原始来源：https://arxiv.org/abs/2607.24551

实际阅读：正文本体核心、开放归纳、合并、封闭填充；评价、定性错误和局限。

与本项目的区别/限制：法规而非判决事实；有CQ示例，但无独立完整法律等价gold。

论文关联代码、资源或作者说明：https://github.com/gmontenegrou/LegiMaintLex

（链接不表示已执行代码；作者说明也不等于论文正文。）

### 13. GrOIL — M

**GrOIL: Graph-Grounded Domain Ontology Induction with Constrained LLM Mediation**

版本/发表：arXiv 2608.22135v1（2026-08）；页眉含未来CIKM 2026日期，不据此当作已召开正式会议。

原始来源：https://arxiv.org/abs/2608.22135

实际阅读：正文UDH图、概念/属性/限制归纳；合成保险数据、CQ和增长实验。

与本项目的区别/限制：图grounding和provenance已有；概念数平台不是语义稳定，数据规律不是规范法律规则。

论文关联代码、资源或作者说明：https://github.com/brains-group/GrOIL

（链接不表示已执行代码；作者说明也不等于论文正文。）

### 14. U-CREAT — M

**U-CREAT: Unsupervised Case Retrieval using Events extrAcTion**

版本/发表：ACL 2023（奠基/邻近）。

原始来源：https://aclanthology.org/2023.acl-long.777/

实际阅读：正文IL-PCR数据、依存事件抽取、检索与主要实验；数据/方法/结果/讨论截图。

与本项目的区别/限制：印度判决事件检索；引用关系gold不是完整相关性或法律等价gold。

### 15. Legal IE survey — P

**Survey on legal information extraction: current status and open challenges**

版本/发表：Knowledge and Information Systems 67 (2025); online 2025-10-10。

原始来源：https://link.springer.com/article/10.1007/s10115-025-02600-5

实际阅读：全文中检索方法、任务分类、事件抽取分支和开放问题已读；非全篇逐项文献深读。

与本项目的区别/限制：用于范围定位；不把其综述中的“尚无”外推到2026。正文纳入数81/结论83不一致，未沿用计数。

论文关联代码、资源或作者说明：https://github.com/DamithDR/legalinformationextraction

（链接不表示已执行代码；作者说明也不等于论文正文。）

### 16. Agents in law survey — P

**LLM Agents in Law: Taxonomy, Applications, and Challenges**

版本/发表：ACL 2026。

原始来源：https://aclanthology.org/2026.acl-long.718/

实际阅读：引言、任务分类和评价框架相关章节；非全部个案逐篇复核。

与本项目的区别/限制：系统层任务地图，不是事实表示正确性的直接证据。

### 17. LEGIT — P

**Evaluating Legal Reasoning Traces with Legal Issue Tree Rubrics**

版本/发表：arXiv 2512.01020（2025），阅读v2；ACL 2026。

原始来源：https://arxiv.org/abs/2512.01020

实际阅读：正文数据构造、法律争点树和评分设计相关章节；未完成全部实验逐表审计。

与本项目的区别/限制：法律推理评价；不能直接充当A的事实等价gold。

### 18. Argumentation schemes — P

**Using Argumentation Schemes to Model Legal Reasoning**

版本/发表：arXiv 2210.00315v1（2022）。

原始来源：https://arxiv.org/abs/2210.00315

实际阅读：理论全文的事实、factor ascription、论证链及相关章节已读；非实验论文。

与本项目的区别/限制：事实到factor含可推翻判断，不是改写或同义聚类。

### 19. LKIF Core — P

**The LKIF Core Ontology of Basic Legal Concepts**

版本/发表：LOAIT 2007, CEUR Vol.321。

原始来源：https://ceur-ws.org/Vol-321/paper3.pdf

实际阅读：核心本体、角色/表达/认识角色相关章节及图；非整篇逐页。

与本项目的区别/限制：上层概念模块借鉴；不预设该本体适配印度所有案件。

论文关联代码、资源或作者说明：https://github.com/RinkeHoekstra/lkif-core

（链接不表示已执行代码；作者说明也不等于论文正文。）

### 20. UMR — P

**Building a Broad Infrastructure for Uniform Meaning Representations**

版本/发表：LREC-COLING 2024（窗口前）。

原始来源：https://aclanthology.org/2024.lrec-main.229/

实际阅读：句子层、文档层和模态/时间/共指设计；未读全部资源实验。

与本项目的区别/限制：提供来源、作用域、跨句关系表达思想，不含完整法律materiality。

### 21. Re-Examining FactBank — P

**Re-Examining FactBank: Predicting the Author’s Presentation of Factuality**

版本/发表：COLING 2022。

原始来源：https://aclanthology.org/2022.coling-1.66/

实际阅读：来源视角、标签投射问题、数据修复和文档划分；未读全套模型实验。

与本项目的区别/限制：作者陈述与嵌套说话人信念不能混为一谈。

### 22. LEVEN — P

**LEVEN: A Large-Scale Chinese Legal Event Detection Dataset**

版本/发表：Findings ACL 2022。

原始来源：https://aclanthology.org/2022.findings-acl.17/

实际阅读：事件类型设计、数据与专家标注相关章节；未逐表深读模型实验。

与本项目的区别/限制：封闭事件类型/触发词标注，不是全命题规范化。

### 23. CESI — P

**CESI: Canonicalizing Open Knowledge Bases using Embeddings and Side Information**

版本/发表：WWW 2018; arXiv 1902.00172（2019公开稿）。

原始来源：https://arxiv.org/abs/1902.00172

实际阅读：方法中的侧信息、嵌入、聚类与数据/评估定义；非全部实验结果。

与本项目的区别/限制：NP实体身份与关系短语规范化需分开；不能直接换成法律命题等价。

论文关联代码、资源或作者说明：https://github.com/malllabiisc/cesi

（链接不表示已执行代码；作者说明也不等于论文正文。）

### 24. ClusterLLM — P

**ClusterLLM: Large Language Models as a Guide for Text Clustering**

版本/发表：EMNLP 2023。

原始来源：https://aclanthology.org/2023.emnlp-main.858/

实际阅读：perspective、triplet查询、granularity与层次切割方法；未完整审计所有实验。

与本项目的区别/限制：用户视角和粒度控制已存在；不提供法律全簇安全保证。

### 25. Plotkin — P

**A Note on Inductive Generalization**

版本/发表：Machine Intelligence 5 (1970)。

原始来源：https://homepages.inf.ed.ac.uk/gdp/publications/MI5_note_ind_gen.pdf

实际阅读：原始扫描件开篇的替换、泛化定义与例子；未读全部证明。

与本项目的区别/限制：anti-unification可借用变量绑定思想；并非法律规则有效性证明。

### 26. FCA tutorial — P

**Introduction to Formal Concept Analysis**

版本/发表：Radim Bělohlávek, 2008 作者教程；非新研究论文。

原始来源：https://phoenix.inf.upol.cz/esf/ucebni/formal.pdf

实际阅读：形式背景、extent/intent、闭包与概念偏序的定义。

与本项目的区别/限制：只在已核验属性上探索小格；属性缺失不能直接当否。

### 27. SMILE/IBP text classification — A+

**Automatically classifying case texts and predicting outcomes**

版本/发表：Artificial Intelligence and Law 17 (2009), 125–165。

原始来源：https://link.springer.com/article/10.1007/s10506-009-9077-9

实际阅读：摘要及出版社公开的实质性注释已读；正文全文未成功获得。

与本项目的区别/限制：公开注释确认角色替换/命题表示的早期来源，并说明该组实验人工角色替换；不声称深读完整实验。

### 28. HYPO — A

**A Case-based System for Trade Secrets Law**

版本/发表：ICAIL 1987; DOI 10.1145/41735.41743。

原始来源：https://doi.org/10.1145/41735.41743

实际阅读：原作元数据/摘要定位；未读全文。

与本项目的区别/限制：经典源头；具体论证机制依赖本轮已读的后续一手理论论文。

### 29. CATO — A

**Doing Things with Factors**

版本/发表：ICAIL 1995; DOI 10.1145/222092.222106。

原始来源：https://doi.org/10.1145/222092.222106

实际阅读：原作元数据定位；全文获取未成功。

与本项目的区别/限制：不将引用到它等同读过原文；本轮另读2026形式化评价论文。

### 30. CATO background knowledge — A

**Using background knowledge in case-based legal reasoning: A computational model and an intelligent learning environment**

版本/发表：Artificial Intelligence 150 (2003), 183–237。

原始来源：https://doi.org/10.1016/S0004-3702(03)00105-X

实际阅读：元数据/摘要；作者PDF访问失败。

与本项目的区别/限制：背景知识与案例论证的重要经典线索，未做原文方法实验背书。

### 31. FactBank — A

**FactBank: a corpus annotated with event factuality**

版本/发表：Language Resources and Evaluation 43 (2009)。

原始来源：https://doi.org/10.1007/s10579-009-9089-9

实际阅读：摘要与资源元数据；正文未深读。

与本项目的区别/限制：经典factuality来源；本轮实读的是2022重新审查论文的相关章节。

### 32. Semantic uncertainty — A

**Semantic Uncertainty: Linguistic Invariances for Uncertainty Estimation in Natural Language Generation**

版本/发表：ICLR 2023; arXiv 2302.09664。

原始来源：https://arxiv.org/abs/2302.09664

实际阅读：论文摘要；未读正文方法实验。

与本项目的区别/限制：不能把一般语义等价自动当法律上下文等价。

### 33. Semantic entropy — A+

**Detecting hallucinations in large language models using semantic entropy**

版本/发表：Nature 2024（6月，窗口前）。

原始来源：https://www.nature.com/articles/s41586-024-07421-0

实际阅读：论文摘要及作者方法说明全文；论文正文访问失败/验证码。

与本项目的区别/限制：作者明确的系统性错误边界；不把采样一致性当法律真值。

论文关联代码、资源或作者说明：https://oatml.cs.ox.ac.uk/blog/2024/06/19/detecting_hallucinations_2024.html

（链接不表示已执行代码；作者说明也不等于论文正文。）

### 34. MAGLJP — P

**A multi-agent framework with legal event logic graph for multi-defendant legal judgment prediction**

版本/发表：Information Processing & Management 63(1) (2026), 104319。

原始来源：https://doi.org/10.1016/j.ipm.2025.104319

实际阅读：出版社摘要/引言部分；未完成正文方法实验阅读。

与本项目的区别/限制：属于C的事件图预测邻近方向，不能用作A规范化方法已深读证据。

### 35. OntoClean — A

**Evaluating ontological decisions with OntoClean**

版本/发表：Communications of the ACM 45(2) (2002)。

原始来源：https://doi.org/10.1145/503124.503150

实际阅读：元数据线索；未读正文。

与本项目的区别/限制：本体评价经典边界，尚需专门原文追踪。

### 36. SKOS — S

**SKOS Simple Knowledge Organization System Reference**

版本/发表：W3C Recommendation 2009；标准非论文。

原始来源：https://www.w3.org/TR/skos-reference/

实际阅读：broader、broaderTransitive、related、closeMatch、exactMatch相关规范。

与本项目的区别/限制：知识组织匹配关系与法律逻辑等价不可混用。

### 37. PROV-O — S

**PROV-O: The PROV Ontology**

版本/发表：W3C Recommendation 2013；标准非论文。

原始来源：https://www.w3.org/TR/prov-o/

实际阅读：entity/activity/agent、derivation、source与bundle相关规范。

与本项目的区别/限制：记录来源和变换，不保证内容正确。

### 38. LegalRuleML — A

**LegalRuleML Core Specification Version 1.0**

版本/发表：OASIS Standard 2021；标准非论文。

原始来源：https://www.oasis-open.org/standard/legalruleml-core-specification-version-1-0-oasis-standard/

实际阅读：官方发布元数据；未阅读完整规范。

与本项目的区别/限制：作为A到C接口候选，不能声称已完成规范兼容设计。

## 尚未补齐的覆盖

经典HYPO/CATO/SMILE原始全文并非全部可得；OntoClean等本体评价源头仍只有元数据。印度各具体法律领域、程序阶段和法条版本适用性尚无本项目专家确认。2026年新稿索引有延迟，JURIX/ICAIL专题、本体工程共享任务和非英文文献未穷尽。B的MDL/关系模式挖掘/多重检验与C的规范规则归纳、ILP/统计关系学习不构成本轮完整综述。

对搜索中版本/日期疑点未解决的条目，不据此断言不存在，也不用于新颖性主张。

## 本轮能支持的判断

已有工作覆盖角色抽象、抽取—定义—规范化、受需求驱动本体扩展、多概念事件图、增量时态KG及来源追踪。法律专用混合流水线本身不是足够的新颖性证据。可研究的增量应当围绕：明确法律语境与粒度，在可用概念复用和人工成本受控时，保留有法律后果的区别、来源立场、论元关系，并以独立专家标注和任务问题验证。该方向目前是待验证研究假设，不是已取得的结果。
