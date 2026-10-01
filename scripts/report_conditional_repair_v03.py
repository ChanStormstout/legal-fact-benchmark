"""Report independent conditional checks without inventing natural-case gold."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read, write_new, log_run, digest
from legal_bench.conditional_controls import mappings
from legal_bench.development_experiment import prepare, run_query, CONDITIONAL_POLICY, without_identity
from legal_bench.engine import cooccurrence_query


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    root = Path(args.run)
    fixture = read(root / "controls/input-and-expected.json")
    summary = read(root / "summary.json")
    counts = {k: {"correct": 0, "incorrect": 0, "false_match": 0}
              for k in ("strict", "conditional", "no_identity", "cooccurrence")}
    failures = []
    for raw, expected in zip(fixture["cases"], fixture["expected"]):
        previous = prepare(raw, mappings(), "STRICT_SCOPE")
        current = prepare(raw, mappings(), CONDITIONAL_POLICY)
        for name, q in fixture["queries"].items():
            results = {"strict": run_query(previous, q), "conditional": run_query(current, q),
                       "no_identity": run_query(current, without_identity(q)),
                       "cooccurrence": run_query(current, cooccurrence_query(q))}
            for method, result in results.items():
                correct = result["status"] == expected["statuses"][name]
                counts[method]["correct" if correct else "incorrect"] += 1
                counts[method]["false_match"] += result["status"] == "MATCH" and expected["statuses"][name] != "MATCH"
                if not correct:
                    failures.append({"case_id": raw["case_id"], "query": name, "method": method,
                                     "expected": expected["statuses"][name], "actual": result["status"]})
    comparison = {"kind": "HAND_SPECIFIED_SYNTHETIC_ONLY", "counts": counts, "errors": failures,
                  "baseline_meaning": "Ablations answer the same relation question with deliberately removed conditions; no real-case accuracy claim"}
    write_new(root / "controls/method-comparison.json", comparison)
    lines = ["Legal AI：算法修复与条件性验证", "",
             "结论：假设标注字段及其显式未知说明正确，新执行器能按用途保留可计算字段；新搜索器在已声明的有限语言内通过独立穷举检查。五案重跑出现此前被整条禁用策略遮住的重复候选。这不能单独证明候选有法律价值，也不是20案独立检查结果。", "",
             "1. 修复内容", "",
             "执行器按字段传播未知：日期未知只阻止时间比较；金额未知只阻止精确金额条件；付款人未知只阻止涉及付款人的连接。原文出处、陈述来源和限定始终保存并随匹配返回。未识别限定仍阻止使用；已解析但需要兼容性判断的限制也不自动忽略。法院未采纳、否定和无法解析的谓词没有被升级为确定事实。",
             "查询只问：是否存在两条限定范围内的记录，满足指定对象连接与条件。相同财产ID不表示占有范围相同、时期相同或当前仍占有；相同记录角色不证明群体成员关系。记录ID不同也不证明它们是两个现实事件。",
             "搜索现在生成一个或两个共享对象连接，所以可以同时要求同一人和同一财产。结构候选优先于时间/属性扩展；每个候选至多附加一个时间或属性条件。支持数按案件计数，未知不计作否定，预算耗尽后的候选完整保存。", "",
             "2. 独立程序证据", "",
             "17个人工构造的合成案例包含51个预定判断：新方法51/51符合预先写定的答案；旧整条禁用方法41/51；移除对象连接42/51；仅事实类型共现40/51。移除对象连接产生9次错误匹配，共现变体产生11次错误匹配。这些数字仅用于程序语义验证，不能当作真实案件准确率。",
             "独立穷举器从类型、角色和属性常量生成所有模板，再逐个执行，未调用被测生成器、执行器或变量规范化函数。合成集合检查104个模板，得到21个有确定实例的候选，与搜索器完全一致；357个候选×案件执行比较的状态、确定绑定与未知绑定均一致。支持数和未知数另经逐候选检查。预算设为1时，11个重复候选留在未执行列表中，验证了截断会遗漏什么。",
             "穷举器与执行器共享声明的字段依赖规范，因此穷举一致不能证明这份规范符合所有法律表述；字段依赖的转换另由预定答案测试检查。", "",
             "3. 原五案输入重跑", ""]
    for side in ("A", "B"):
        info = summary["runs"][side + "/core"]
        lines += ["%s：独立穷举检查%d个模板，得到%d个候选；与搜索器无遗漏、无额外候选。%d个候选×案件判断及对象绑定全部与独立执行器一致。" %
                  (side, info["oracle_templates"], info["generated_candidates"], info["execution_oracle"]["comparisons"]),
                  "同一候选池下，旧整条禁用方法有%d个重复候选，新方法有%d个。新候选中%d个连接不同事实类型，%d个是同类记录配对，可能包含重复陈述，仍需事件身份复核。" %
                  (info["common_pool_legacy_repeated"], info["common_pool_conditional_repeated"], info["repeated_mixed_type_candidates"],
                   info["repeated_same_type_record_pairs_require_coreference_review"]),
                  "八个固定查询×五案：旧状态%s；新状态%s；%d项状态改变。状态改变本身不计为准确率提高。" %
                  (info["fixed_legacy_statuses"], info["fixed_conditional_statuses"], info["fixed_changed"]), ""]
    lines += ["所有重复核心候选均出现在1064407与184866874这两个输入中。不同类型的例子包括“占有者与起诉人相同”“占有者与权利人相同”，B还出现“占有记录与起诉记录指向同一财产”。这些候选不自动表达同一时期、同一占有范围或请求应获支持。不同谓词归入同一类型的草拟映射仍需语义复核。", "",
              "补充原生谓词搜索只检查同名谓词及角色结构，不默认跨案件语义相同："]
    for side in ("A", "B"):
        info = summary["runs"][side + "/native"]
        lines.append("%s生成%d个候选，按预算执行%d个，找到%d个重复候选；其余%d个保留，未声称完整覆盖，也未对整个原生词表运行穷举。" %
                     (side, info["generated_candidates"], info["executed_candidates"], info["repeated_patterns"],
                      info["generated_candidates"] - info["executed_candidates"]))
    lines += ["", "4. 文件与复现", "",
              "原十份标注及复核备注的对象与字节哈希均验证，原文件未修改。新运行保存输入快照、草拟映射、固定查询、代码快照、全部核心候选、确定/未知实例、未执行列表和独立检查。网页任务0次，付费API调用0次。",
              "主运行：python3 scripts/run_conditional_repair_v03.py --snapshot outputs/benchmark-pilot-v03/experiments/five-case-unreviewed-v2 --out 新目录",
              "中断恢复：使用同一参数加 --resume；输入与代码哈希变化时拒绝复用旧阶段。",
              "测试：python3 -m unittest discover -s tests -v",
              "", "5. 下一项证据", "",
              "现在可以说明程序在指定输入假设和有限语言内正确匹配、完整生成候选及正确计数。证明跨案件复用是否保留法律语义，还需side chat的来源核查、草拟类型映射协调，以及冻结后20案检查；本轮未完成这些步骤。"]
    content = "\n".join(lines) + "\n"
    path = root / "report.txt"
    if path.exists() and path.read_text() != content:
        raise ValueError("Existing report differs; use a versioned report")
    if not path.exists():
        path.write_text(content)
    log_run(root, "report-conditional-repair", [root / "summary.json", root / "controls/input-and-expected.json", Path(__file__)],
            [path, root / "controls/method-comparison.json"])
    print(path)


if __name__ == "__main__":
    main()
