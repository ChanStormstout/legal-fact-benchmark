# V19_6共同合同修复接口

本轮仅修复与缓存重放，生成、网页和训练保持暂停。新输出位于`outputs/proof-contract-integrity-v19-6/`。旧V19及Together的输入、Schema、原始输出和失败不改。

新共同入口是`scripts/proof_contract_integrity_v19_6.py prepare|replay|freeze`。新运行器是`legal_bench/proof_carrying/local_runtime_v19_6.py`；它读取完整新Schema校验、唯一字符串数组约束、第二次来源重复保护。运行后的保存输出通过共同`accept_saved_output`导入、核对覆盖、独立检查并准备同信息学习输入。当前CLI没有生成或训练命令，不应恢复旧入口绕过新检查。

新合同的analyses是由规则前提ID固定键的对象，每个条目允许明确NOT_ANALYZED。role_objects按该前提的规则角色填OBJ地址或UNMAPPED；转换器只构造角色地址，不猜测对象身份。EV、OBJ、USE动态存在性由导入检查。见证通过source选一个允许地址，由代码恢复原文。原文旁直接显示SRC地址，规则及允许来源保持原内容。

完整校验器拒绝重复数组、重复JSON键和未知Schema关键字。解码器针对Schema声明的唯一字符串数组阻止重复值；不能保证动态引用或语义正确。生成自然结束、合同有效、分析覆盖和法律支持性分开保存。独立检查在逐项比较前核对全部相关列表数量，保留归属、状态与阶段。

旧合同缓存按原生产版本读取；不会被改名成新生成结果。新共同输入另存哈希，标记PREPARED_NOT_YET_ENCODED；未使用旧权重冒充新配置。正式法律批准仍未授予，OPEN_TEXT不强制执行，局部结构可用不等于前提成立。

[中文报告](../outputs/proof-contract-integrity-v19-6/report-zh.md)、[冻结协议](../outputs/proof-contract-integrity-v19-6/freeze/protocol.json)、[工程验收](../outputs/proof-contract-integrity-v19-6/engineering-acceptance.json)。不提交或推送。
