# RAPIDO V22 transport recovery

独立本地修复，语义流程继承冻结 V21.1。见 [修复报告](report-zh.md)。

真实服务根因未定位；没有新 Qwen 调用、真实终稿或质量改善结论。execute.py 默认不执行，必须经过 V22 专属费用授权及未知用量处理。原 V21.1 与失败结果保留，主入口不变。

离线验收：tests/whole_workflow.py 为既有虚构整案；tests/transport_acceptance.py 回放 39 份真实流并用禁止网络的 HTTP 替身通过实际 APIProvider 执行整案。测试不生成真实模型答案。
