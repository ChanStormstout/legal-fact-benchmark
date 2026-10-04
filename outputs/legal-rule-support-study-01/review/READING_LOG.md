# 固定版本审阅：阅读范围与验证边界

- 仓库：ChanStormstout/legal-fact-benchmark
- 所有仓库读取均指定提交：be0ec42b802c0ff701635e3421ff185699d94656
- 入口报告的内容 snapshot_id：6d08d45186566376bb2a7ff2ac4ab123fbace635bcd7d782fea12bdc38a3979d
- snapshot_id 没有被当作 Git commit；本次未重新计算完整快照哈希。
- 访问方式：GitHub 连接器逐文件读取。网页 raw 访问及容器整库下载未成功。
- 本次没有在本地执行仓库测试、MLX 推理或网页受测回答；测试通过数仅能作为仓库保存的报告内容。
- “全文”指读取了工具提供的完整文本，不表示已经逐字核对原始 PDF 或独立复算文件哈希。
- “片段”指只读了指定区间，或工具预算截断了响应；不据此声称全文审计。

## 一、全文读取的仓库文件

### 导航与研究界定
- review/START_HERE.md
- docs/RESEARCH_DIRECTION.md
- docs/plans/rule-retrieval-v21/PIPELINE.md

### 实现与测试
- legal_bench/mlx_json_constraint.py
- legal_bench/mlx_json_constraint_v2.py
- legal_bench/rules_verdict_v1/runtime_v9.py
- legal_bench/rules_verdict_v1/runtime_constraint_diag_v1.py
- legal_bench/rules_verdict_v1/final_v9.py
- legal_bench/rules_verdict_v1/authority_index.py
- legal_bench/rules_verdict_v1/retrieve.py
- legal_bench/rules_verdict_v1/rule_retrieval_v21.py
- legal_bench/rules_verdict_v1/rule_transfer_v16.py
- legal_bench/rules_verdict_v1/rule_application_v17.py
- legal_bench/rules_verdict_v1/application_chain_v18.py
- scripts/rule_retrieval_v21.py
- tests/test_rule_retrieval_v21.py

### 约束故障及 V11–V18
- outputs/json-constraint-diagnosis-v1/report-zh.txt
- outputs/json-constraint-diagnosis-v1/same-input-comparison.json
- outputs/json-constraint-diagnosis-v1/post-run-token-replay.json
- outputs/rules-verdict-v11-intermediate-ablation/report-zh.txt
- outputs/rules-verdict-v11-intermediate-ablation/sources/69305.json
- outputs/rules-verdict-v11-intermediate-ablation/runs/B-proposal/raw-response.txt
- outputs/rules-verdict-v11-intermediate-ablation/runs/B-P/raw-response.txt
- outputs/rules-verdict-v11-intermediate-ablation/runs/B-C/raw-response.txt
- outputs/rules-verdict-v12-thinking/report-zh.txt
- outputs/rules-verdict-v13-crosscase/final-answer-slots.md
- outputs/rules-verdict-v14-web-direct/final-answer-slots.md
- outputs/rules-verdict-v15-rule-supplement/report-zh.txt
- outputs/rules-verdict-v16-rule-transfer/report-zh.txt
- outputs/rules-verdict-v17-rule-application/report-zh.txt
- outputs/rules-verdict-v18-application-chain/report-zh.txt

### V19–V20
- outputs/rules-verdict-v19-historical-pairs/availability.json
- outputs/rules-verdict-v20-four-case-pairs/report-zh.txt
- outputs/rules-verdict-v20-four-case-pairs/protocol.json
- outputs/rules-verdict-v20-four-case-pairs/repeat-stability.json
- outputs/rules-verdict-v20-four-case-pairs/sources/1033921.json
- outputs/rules-verdict-v20-four-case-pairs/runs/R05/raw-response.txt
- outputs/rules-verdict-v20-four-case-pairs/runs/R05/format-check.json
- outputs/rules-verdict-v20-four-case-pairs/runs/R07/raw-response.txt
- outputs/rules-verdict-v20-four-case-pairs/runs/R08/raw-response.txt

### V21–V23
- outputs/rules-verdict-v21-rule-retrieval/library/coverage.json
- outputs/rules-verdict-v22-scope-preparation/engineering/summary.json
- outputs/rules-verdict-v23-uniform-retrieval/samples.json
- outputs/rules-verdict-v23-uniform-retrieval/scope-audit.json
- outputs/rules-verdict-v23-uniform-retrieval/description-instructions.txt
- outputs/rules-verdict-v23-uniform-retrieval/description-freeze.json
- outputs/rules-verdict-v23-uniform-retrieval/description-order.json
- outputs/rules-verdict-v23-uniform-retrieval/description-runs/S01/raw.txt
- outputs/rules-verdict-v23-uniform-retrieval/description-runs/S01/completion.json
- outputs/rules-verdict-v23-uniform-retrieval/publication-checkpoint.json
- outputs/rules-verdict-v23-uniform-retrieval/sources/157278563-allowed.json（两次区间读取覆盖全文）

## 二、片段读取；不能称全文

- README.md：导航及多轮结果说明，响应截断。
- docs/PROJECT_STATE.json：多个历史状态及检索准备记录，响应截断。
- docs/EXPERIMENT_INDEX.md：历史实验导航，响应截断。
- docs/EXPERIMENTS.json：原文件 1–100 行。
- docs/repository-artifacts.json：读到 artifact_roots 包含 V23 及发布/代码登记信息；响应截断。
- docs/CHANGELOG.md：发布检查点、V21、V19、V18 至 V12 的部分记录，响应截断。
- docs/plans/rules-and-verdict-v1/PIPELINE.md：研究目标、历史组件选择、数据流、对象与来源约束；响应截断。
- docs/plans/rules-and-verdict-v1/IMPLEMENTATION_PLAN.md：实施、运行限制及停止设计；响应截断。
- scripts/pipeline_v11_ablation.py：前 170 行请求范围内的准备、共享提议与条件组装路径。
- outputs/rules-verdict-v11-intermediate-ablation/runs/B-C/prompt.txt：任务头、部分法律包/程序检查以及关键允许原文；直接核实 p0004.s002 的 not inadmissible 已送入实际 prompt，大型 JSON 载荷未读全。
- scripts/historical_pairs_v20.py：准备/组装主体和后段运行导入；中间小段及截断部分未完整重读。
- outputs/rules-verdict-v13-crosscase/sources/1134266.json：19 个允许片段已读；尾部元数据响应截断。
- outputs/rules-verdict-v19-historical-pairs/candidate-decisions.json：前段及原文件 255–430 行，未完整读取尾部。
- outputs/rules-verdict-v20-four-case-pairs/final-source-review.json：原文件 1–200 行，涵盖首次 R01–R07 的相当部分。
- outputs/rules-verdict-v20-four-case-pairs/cost-records.json：原文件 1–130 行，R01–R06。
- outputs/rules-verdict-v20-four-case-pairs/tasks/1033921/B/task.txt：任务头、基础法条、三张旧卡及关键新增原文；全部允许案情和全部后续要求/Schema。嵌入的大型法源 JSON 一行有截断，故不标全文。
- outputs/rules-verdict-v22-scope-preparation/engineering/157278563-retrieval-diagnostic.json：分次读取查询、配置、候选排序、关键原文、A/B 依赖与预算排除。部分重复原文及末尾截断，未把整份载荷标为全文。
- outputs/rules-verdict-v22-scope-preparation/engineering/34625760-retrieval-diagnostic.json：原文件 1–225 行及 660–末尾，覆盖两路原始排名、旧卡排名、融合前列、B 全部选择/排除结果；中间原文载荷与 A 详细决策未逐项读完。
- outputs/rules-verdict-v23-uniform-retrieval/library/original-units.json：GR 三单元、HP/TS 相关内容、44A 及部分 45；若干响应截断，未读全 10 单元载荷。
- outputs/rules-verdict-v23-uniform-retrieval/sources/34625760-allowed.json：原文件 1–155 行，法院层级、两物业/租约、收购更名、两项争点、条款 10.5 开头；后续完整条款条件及往来函件没有逐项读完。

## 三、未能获取与未读取的区别

### 未能获取完整正文
- review/MANIFEST.json：raw 请求失败；连接器文件读取返回空正文。未完成全清单与文件 SHA256 独立核验。
- 整库归档：容器下载未成功，未在容器取得完整固定提交；因此没有复跑测试或批量重算。

### 已知未逐项读取，不声称访问失败
- docs/reviews/2026-10-03-pro-research-design-review.md 的独立备份；本次请求全文已在用户消息中提供。
- 早期 8 案 13 题全部原始输出和完整参考；本轮只按登记和导航确定其历史性质，没有重评分。
- V11 其余实际 prompt/schema/run.json、V12 原始日志及全部原始回答、V13/V14 每份实际上传回执。
- V15/V16 全部来源 PDF、九张原始规则卡与完整语义复核链；相关结论中明确区分报告转述与本次直接核验。
- V17/V18 所有逐次 raw、冻结清单、引用回放及来源审阅条目。
- V20 全部 12 份 raw、所有目标完整判决、全部冻结/顺序/比较表与所有后续重复审阅。
- V22 全部候选筛选记录、两个诊断的所有重复原文载荷。
- V23 S01–S03 完整实际任务、全部来源文件、S01 submission/proposal/import-status；未把未运行的 S02/S03 或最终回答推定为已有成果。

这些未读项限制的是全仓库认证与全部评分复算；本次主要判断依赖已实际读到的决定性运行链路，并在正文区分原因证据强度。

## 四、论文阅读范围

- LR²: A Legal RAG for Legal Reasoning over Cases（2025，DOI 10.3233/FAIA251614）：出版方短文主体全文，方法与结果；其公开主体很短，不能据此认证所有实现细节。
- NyayaRAG（IJCNLP-AACL 2025，2025.ijcnlp-long.92）：原 PDF 的任务、数据构造、摘要 prompt、方法及实验相关部分；查看了相关页截图。未逐项读取全部 18 页附录。
- Legal Rule Induction: Towards Generalizable Principle Discovery from Analogous Judicial Precedents（arXiv:2505.14104v2）：原文任务、语料分组、结构化、规则提取/过滤、SILVER、评价、主要实验及限制；附录部分读取，未标全文附录。
- De Jure: Iterative LLM Self-Refinement for Structured Extraction of Regulatory Rules（arXiv:2604.02276v1，2026）：原文方法、三阶段 judge、best-of 修复、主要实验、下游 QA、消融及算法相关附录；未逐项读所有模板/附表。
- 另浏览 AQgR（2508.04710）与 LRAGE（2504.01840）的相关方法/评价段落；未把摘要浏览当成方法选择依据。若某篇仅搜索到标题/摘要，则没有在正式结论中援引其具体效果。
