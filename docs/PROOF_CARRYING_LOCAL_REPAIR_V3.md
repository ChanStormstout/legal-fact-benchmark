# 真实判决重建的本地修复 v3

本版本复用v2三案、全部原始提议及来源，零模型调用。原v2冻结、失败和审阅保持不变。

运行入口为`scripts/proof_realcase_repair_v3.py prepare`和`run`。前者生成两条轨道及源码、材料冻结，后者调用独立的`scripts/check_realcase_certificate_v3.py`。已完成目录不可直接重复运行；新修订另存版本。来源原件引用现有v2路径，迁移时必须保持仓库及路径或另建可追踪manifest，不能改写已冻结快照。

`engine-only`保持三个原模型推导逐字内容相同，只更新地址检查与执行状态；`reviewed-reconstruction`另外使用明确的法院判断记录和局部角色映射，Sopan R6@2/S6/Q5有保存的维护者修订。这两条轨道不合并成模型比较成绩。

法院判断记录位于可信研究快照，不由提议凭据自行声明为可信。检查器核验来源地址、版本、接受记录、命题、对象、阶段及依赖条件，**不核验来源的自然语言含义，也不独立重做法院的开放评价**。相应语义假设ID传播到请求输出，状态为CONDITIONAL_RECONSTRUCTION；正式法律批准仍待定。未实现的开放评价保持INCOMPLETE_EXECUTION及null答案，明确区别于事实UNKNOWN和错误凭据INVALID。

两条原先只因渲染空格被暂停的规则恢复研究接受，依赖旧两份语义复核已经接受这一事实。新的引文定位保留原字符范围，绝不以定位成功代替语义接受。角色映射仅为明确槽位上的角色置换，不能补身份、跨事件合并或升级陈述状态。

全部结果与限制见[中文报告](../outputs/proof-carrying-local-repair-v3/report-zh.txt)、[逐项比较](../outputs/proof-carrying-local-repair-v3/comparison.csv)及[冻结配置](../outputs/proof-carrying-local-repair-v3/freeze/config.json)。这次已解决本地可修复的接口问题；正式批准与自然错误条件下的净收益评价仍独立保留，不作为暂停工程实现的借口。
