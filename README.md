# Legal Facts, Rules and Decisions

研究目标是从历史案件的事实、请求和争点中取得有来源的法律规则，检验这些规则能否帮助新案件
找到适用法规、法律测试及先例，并形成有依据的逐项请求或争点结论。是否将benchmark作为主要
产出尚未确定；评测材料首先服务于验证方法。仓库URL沿用原名称。

[研究方向与实验影响](docs/RESEARCH_DIRECTION.md)记录2026-10-01的用户更正。
现有三个对象关系问题属于中间表示和匹配的诊断，尚未检验适用法源检索、法律规则归纳或判决预测。

**当前状态：开发验证，整体可靠性尚未验证。** 最新完成的完整A/B比较使用固定的 Qwen3.5-9B-4bit，在8案、13道预定题上
比较直接回答与“抽取后执行”。A全部完成，B一案输出截断；相对模型参考答案，5道正例
均未识别。格式约束已让大部分输出可执行，但事实抽取仍有遗漏、状态与对象混淆。
尚未完成法源检索与判决预测的端到端实验，也没有独立测试准确率结论。

后续[v10开发诊断](outputs/local-qwen-pattern-eval-v10/report-zh.txt)把完整来源按事实类型拆开抽取，再逐对象对判断关系：
2案6题，两个MATCH经原文检查有1个得到支持、1个转租类型错误，另4题UNKNOWN。
已得到第一个有来源支持的本地端到端匹配；不能据此声称整套方法有效。失败版本与修改均保留，
详见实验索引。v10使用额外调用，不是同预算比较或独立新测试。

从 [ChatGPT审阅入口](review/START_HERE.md) 开始；
[当前状态](docs/PROJECT_STATE.json)、[实验索引](docs/EXPERIMENT_INDEX.md)、
[最新中文报告](outputs/local-qwen-pattern-eval-v3/report-zh.txt)、
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
git clone https://github.com/ChanStormstout/legal-fact-benchmark.git
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

把 [review/START_HERE.md](https://github.com/ChanStormstout/legal-fact-benchmark/blob/main/review/START_HERE.md)
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
