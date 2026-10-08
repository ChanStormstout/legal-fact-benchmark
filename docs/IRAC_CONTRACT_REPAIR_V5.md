# IRAC V5：工程契约修复与两案完整流程验收

本轮已经结束：E工程处理通过，M事实组织与L完整回答仍未通过。两案8次本地调用完成，2份提议和6份最终回答完整，生成总时间19.31分钟。没有重试、网页调用、新训练、提交或推送。

完整[中文报告](../outputs/irac-contract-repair-v5/continuation-01/report-zh.txt)、[答案入口](../outputs/irac-contract-repair-v5/continuation-01/answers.md)、[来源审阅](../outputs/irac-contract-repair-v5/continuation-01/final-source-review.json)与[E/M/L验收](../outputs/irac-contract-repair-v5/continuation-01/acceptance.json)分开保存。原V5初始工程检查点、V4原始结果和失败不改写。

`contract_v5.py`复用合法条件地址、限制范围和原文排序，补完证据账本与可计算用途分离。每条原始证据按位置和值独立保存；无绑定、无效用途和源地址问题按依赖限制计算，不擦除原文或其他有效用途。空的可读提议允许继续原文回答；技术失败仍为null。程序只检验已声明结构，不证明提议含义。

`scripts/irac_contract_v5_run.py`是真实冻结和运行入口，调用`execute_slot → finish_attempt → process`。22项相关测试通过；不变Schema、约束器和材料下复用15个真实tokenizer样例及5项修复回归。8个实际输入送达核验通过，13条证据全部保留，1条跨绑定限制局部隔离。B/C使用同一份未改写的新提议，C另读确定性检查。

M仍存在同一安排按法律问题或认定拆分、源记录与用途方向不一致；188721101的六条用途甚至全部指向时间条件。L中B有局部纠错，但保留或新增无依据推断；C没有可靠额外净收益。六份答案均预测拒绝，不等于判断正确。本轮没有训练GNN，不能由此否定整个图方法。

实际运行版本是`outputs/irac-contract-repair-v5/continuation-01/freeze/code`；父目录的`engineering/snapshot`是先前工程检查点，两者不可混用。已完成的`freeze`拒绝覆盖，`run`仅能兼容复用现有结果，不会重试半成品。没有开启下一轮的授权。

```sh
python3 -m unittest tests.test_irac_contract_v5 tests.test_irac_contract_v5_run -v
python3 scripts/irac_contract_v5_run.py preserved
```

报告使用一次模型辅助来源审阅，不是人工金标准。所有来源、模型输出、程序检查与缺口按原有位置可追溯。旧2,426项保留清单核验未变；生成代码、Schema、来源及法源冻结哈希保持一致。
