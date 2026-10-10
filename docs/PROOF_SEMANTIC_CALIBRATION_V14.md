# V14 用途语义校准与真实路径接口

本轮只做本地校准，不调用模型或训练，不启封TEST／SEALED。两条既有DEV路径分别保留原V13 P、V14显式合同下的原P重放，以及来源校准版本。源文件和旧分组不变。

`legal_bench/proof_carrying/use_contract_v14.py`定义具体用途合同，分开作用资格、方向、完整前提真值与法律后果。背景、部分支持、部分反对及记录主张不能单独推动整个前提成立。未明确的旧用途继续保留歧义，不从原标签猜测。

`semantic_calibration_v14.apply_overlay`只接受显式、版本化的数据覆盖层：角色地址、来源呈现更正及外部前提审阅凭据。它校验原快照哈希，保留原P、证据、用途标签、规则命题与操作符、反论。角色对应与完整覆盖由来源审阅记录承担，不是程序按姓名或相似度批准。

`scripts/proof_semantic_run_v14.py`使用既有依赖搜索，把完整快照、路径与接受政策保存后，启动独立的`check_semantic_v14.py`进程。检查器不导入覆盖层装配函数、参考或学习模型；它复核引文、对象／阶段／版本、组成内容见证，再复用明确的ALL／ANY／例外计算。外部前提真值来自明示研究审阅政策，程序不重新证明法院语义判断。OPEN_TEXT保持未执行；正式法律批准始终另列为缺失。

两案具体角色和外部前提都在数据文件，而非案件ID代码分支中。396336的F08 null引文没有猜补；来源校准另建法院判断接受凭据。594273的R5@1语义版本未改，来源quote首字母修订由V14覆盖层、原值和新内容哈希记录，旧冻结规则原字节保留。作为规则背景的假设性L125没有被用于证明具体事件发生。

真实执行：`python3 scripts/proof_semantic_calibrate_v14.py`。它先核对冻结源码和材料哈希，已经完成时直接复用；不重新生成P或法律答案。路径输出保存于`outputs/proof-semantic-calibration-v14/paths/`，用途翻转的依赖控制保存于`controls/`。控制不算自然错误纠正。初版变更日志误读原P basis字段，修订的本地`calibration-ledger-reviewed.json`保存实际原字段与记录勘误；旧日志、执行和凭据未改，也未重跑。

直接相关验收：`python3 -m unittest tests.test_proof_semantic_v14 tests.test_proof_semantic_v13 -v`。本轮集中执行12项测试方法，工程通过不证明法律正确。

[中文报告](../outputs/proof-semantic-calibration-v14/report-zh.md)、[用途合同](../outputs/proof-semantic-calibration-v14/freeze/use-contract.json)、[有限校准摘要](../outputs/proof-semantic-calibration-v14/supervision-calibration-summary.json)、[路径比较](../outputs/proof-semantic-calibration-v14/path-comparison.json)、[学习决定](../outputs/proof-semantic-calibration-v14/learning-decision.json)。完整来源、路径快照与原始记录只在本地保存，发布清单排除这部分数据；本轮没有提交或推送。

决定：当前两条路径没有新增学习组件的证据，不启动用途分类训练或另立新学习目标。保留原P基线、共同检查接口和历史GNN／CrossEncoder实现。用途资格有局部价值，但此轮恢复来自角色及来源校准，未展示真实用途纠错；两个案例不用于估计泛化。
