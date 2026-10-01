"""Summarize source-reviewed development results and trace prior changes."""
import argparse
import copy
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read, write_new, digest, log_run
from legal_bench.scoped_mining import mine


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True)
    parser.add_argument('--prior', default='outputs/benchmark-pilot-v03/experiments/conditional-repair-v2')
    args = parser.parse_args()
    root, prior = Path(args.run), Path(args.prior)
    summary = read(root / 'summary.json')
    traces = {}
    for side in ['A', 'B']:
        views = read(root / side / 'CORE/views.json')
        by_case = {v['case_id']: v for v in views}
        old = read(prior / side / 'core/mining.json')
        # Exactly the prior executed candidate set, with legal states retained
        # in this diagnostic only, isolates updated permissions and input view.
        candidates = [json.dumps(p['query'], ensure_ascii=False, sort_keys=True, separators=(',', ':')) for p in old['patterns']]
        result = mine(views, candidates=candidates)
        write_new(root / side / 'CORE/review-only-prior-candidates.json', result)
        updated = {p['id']: p for p in result['patterns']}
        entries = []
        for pattern in old['patterns']:
            if not pattern['repeated']:
                continue
            new = next(p for p in result['patterns'] if {k: v for k, v in p['query'].items() if k != 'mode'} == pattern['query'])
            lost = []
            for item in new['results']:
                original = next(x for x in pattern['results'] if x['case_id'] == item['case_id'])
                if original['relation']['status'] == 'MATCH' and item['relation']['status'] != 'MATCH':
                    lost.append({'case_id': item['case_id'], 'previous_witnesses': original['relation']['witnesses'],
                                 'reviewed_status': item['relation']['status'],
                                 'reviewed_uncertain_bindings': item['relation']['uncertain_bindings'],
                                 'reviewed_rejected_bindings': item['relation']['rejected_bindings'],
                                 'answer_boundary': 'This is not evidence the original real-world pattern is absent'})
            entries.append({'query': pattern['query'], 'previous_support': pattern['support'], 'reviewed_support': new['support'],
                            'reviewed_unknown_cases': new['unknown'], 'lost_matches': lost})
        traces[side] = {'previous_repeated': sum(p['repeated'] for p in old['patterns']),
                        'reviewed_repeated_on_exact_prior_candidates': sum(p['repeated'] for p in result['patterns']),
                        'pattern_changes': entries, 'scope': 'All CORE profile records including legal-state diagnostics; no new candidates'}
    write_new(root / 'previous-pattern-change-trace.json', traces)
    atlas_a, atlas_b = (read(root / side / 'ATLAS/repeated-with-evidence.json') for side in ['A', 'B'])
    a_ids, b_ids = {p['id'] for p in atlas_a}, {p['id'] for p in atlas_b}
    agreement = {'common_repeated_candidate_ids': sorted(a_ids & b_ids), 'A_only': sorted(a_ids - b_ids), 'B_only': sorted(b_ids - a_ids),
                 'interpretation': 'Independent extraction/reference-process diagnostic; not accuracy or independent cases'}
    write_new(root / 'AB-pattern-overlap.json', agreement)
    lines = ['Legal AI：五案来源核查接入与开发实验', '',
             '结论：核查清单已接入，类型与角色按明确的任务定义统一，五案查询和模式搜索已完成。较窄的占有／租赁核心词表没有达到两案重复门槛；扩展词表出现重复候选，但大部分只是诉讼程序结构。程序通过独立有限语言检查，这批结果尚不证明发现了有法律价值的事实规律。', '',
             '1. 核查结果怎样进入计算', '',
             '原401条事实／程序记录都保留核查结论；其中212条获准限定使用，12条只批准命题核心，没有批准对象连接。程序逐案校验原始文件、段落内容哈希和核查版本，十份输入与side chat快照一致。保留未知及排除决定，没有自动应用核查模型建议的改写，也没有重做标注。',
             '原字段值仍保存供追溯；只有approved_fields中的字段进入执行器和候选生成。角色改名时批准和未知原因一起改名，不能借统一角色重新批准某个对象。精确时间与金额没有获批，因此原JSON中即使有日期或金额，也不进入这些比较。',
             '例如755721 B的起诉记录a6虽然保存property=o5，但审核只批准事件核心，归入SUIT_FILING_RECORD后仍不能用o5连接财产。184866874 B的a35明确是A.S.上诉，归入APPEAL_FILING_RECORD；a3/a31才是O.S.起诉记录，行政请求没有被归为起诉。', '',
             '2. 类型统一与搜索边界', '',
             'type-cards.json和逐案registry.json保存14个任务类型及原始定义、角色映射、使用边界和输入哈希。LEASE_PROPERTY、EXECUTE_LEASE、LET_PROPERTY归为较弱的租赁记录类型；并不声称它们严格等价或属于同一个事件。经营活动三个名称也按来源定义统一。租金数额不归为实际支付，收到通知不归为回复，原审法院不改成受理上诉法院。',
             'CORE用于原占有／租赁查询；ATLAS在事先声明的类型清单中加入经营与程序行为；NATIVE保留原生谓词／角色集合，仅作语法对照。CORE固定查询保留法律状态记录，CORE／ATLAS的可观察事件搜索将法律状态另行排除；NATIVE保留原生类型作对照，不将其全部认定为物理事件。ATLAS不是根据表现挑出来的模式集合，全部候选均保存。',
             '搜索两个不同记录、一个或两个共享对象连接，至多附加一个获准时间／属性条件。本次没有获准时间／属性，因此搜索只生成结构条件。支持数按案件，不按记录数或匹配数；A/B分别运行，不能合并成十个案件。记录ID不同不能证明现实事件不同，同类配对和仅法院连接另列。', '',
             '3. 固定开发查询', '']
    for side in ['A', 'B']:
        info = summary['runs'][side + '/CORE']
        lines += ['%s：八个查询×五案，共40项，状态%s；相对“输入字段准确”的旧运行，有%d项状态改变。' %
                  (side, info['fixed_statuses'], info['changed_after_source_review'])]
    lines += ['Q1/Q2分别检查付租与租赁是否指向同一财产，以及租客是否就是付款人；Q3检查占有与租赁财产；Q4/Q5涉及权利状态与占有；Q6检查占有与起诉财产；Q7检查失去占有与占有财产；Q8还需要租赁早于起诉的时间比较。全部问题保持原自然语言含义，没有为获得更多匹配修改定义。',
              'Q8在具有相关记录的输入中因时间未获批而保留未知。有些旧确定结果被撤回，有些原“未找到”改为未知，因为核查没有批准此前依赖的身份或状态。NOT_FOUND只表示当前可用记录范围没有匹配，不能解读为原文或现实中没有事实。fixed-query-statuses.csv和逐项JSON保存全部结果与证据。', '',
              '4. 模式搜索结果', '', '版本／范围 | 生成并执行候选 | 至少两案重复候选 | 包含事实记录的重复候选']
    for side in ['A', 'B']:
        for profile in ['CORE', 'ATLAS', 'NATIVE']:
            info = summary['runs'][side + '/' + profile]
            lines.append('%s %s | %d/%d | %d | %d' % (side, profile, info['generated'], info['executed'], info['repeated'], info['repeated_with_fact_witnesses']))
    lines += ['', '本次全部生成候选都在1000预算内执行，未发生截断。ATLAS的A/B重复候选为22/7；其中20/6仅含程序行为，另2/1包含事实与程序的组合，没有纯事实组合达到两案重复门槛。只连接法院的重复候选为4/2；A还有7个同类记录配对，可能反映重复表述或不同阶段，未认定现实事件不同。这些标签可以重叠，不能直接相减当成剩余有效模式数。',
              'A/B共同重复候选%d个；提取差异及字段批准范围仍会改变发现结果。' % len(a_ids & b_ids),
              '一个两份标注都出现的例子是：“存在占有记录及撤销判决记录，指向同一财产ID”，出现在1064407与184866874。它只说明这些限定记录连接到同一个对象，未连接到同一个请求或同一个时期，不能推出占有合法或某方应胜诉。A另有“租客与上诉人同一对象”的两案候选，仍主要反映参与程序的身份结构。',
              '原条件性运行A/B的6/3个核心重复候选，在相同旧候选集合上读取核查后的记录，重复数均为0；previous-pattern-change-trace.json列出每个旧实例为何不再得到确定匹配。不能把这解释成真实模式必定不存在，原因可能是记录被限制、对象连接未获批准、来源不确定或样本缺少可比事实。', '',
              '5. 程序验证及实验解释', '',
              '独立穷举程序为CORE A/B各检查827个模板，为ATLAS检查6527/5032个模板；有确定实例的候选与搜索器完全相同。全部范围的候选执行状态、确定绑定、未知绑定及支持数通过独立程序比较。NATIVE验证了全部已生成候选的执行，未声称穷举原生语言的所有模板。程序独立不等于来源核查独立，也不证明模式的法律用途。',
              '本地程序测试共91项通过。新增测试检查角色改名不提升权限、已知日期未获批仍不可计算、未知源角色随改名继续受限、双连接枚举、同案计数及输入不变。人工构造例子仅验证程序；这五案是真实开发数据，但不是20案独立检查集。',
              '关系与共现会得到不同状态；本次没有独立逐查询答案，因此没有把所有差异计作真实错误或报告准确率。来源审核是模型生成并经来源核查的参考材料，不是人类金标准。没有胜败标签训练、付费API或新的网页任务。', '',
              '6. 下一步', '',
              '现在已完成接入、任务类型统一及开发运行。冻结20案前需要固定具体请求类型与抽样单位；目前五案混合租赁、征地、信托及管理权，适合检查流程，但不能用这批程序重复模式证明事实抽象能够跨同类案件复用。下一批应按材料完整性和纠纷分组选同类案件，而不是按本轮预测正确率或是否出现模式选样本。',
              '仍需在冻结配置下完成模型直接阅读、模型结构化后回答与执行器的预定对照；本报告只完成本地程序实验。不要通过改写这五案或调整重复门槛来制造模式。对于已有清单指出的关键修正，只有预定查询确实需要时才制作有版本和证据的局部修订，不重新抽取所有记录。', '',
              '复现：python3 scripts/run_reviewed_development_v03.py --out 新目录',
              '中断恢复：同一参数加--resume，输入／代码哈希变化时拒绝复用。',
              '报告：python3 scripts/report_reviewed_development_v03.py --run 运行目录']
    content = '\n'.join(lines) + '\n'
    path = root / 'report-v2.txt'
    if path.exists() and path.read_text() != content:
        raise ValueError('Refuse to overwrite a changed report')
    if not path.exists():
        path.write_text(content)
    log_run(root, 'report-reviewed-development', [root / 'summary.json', Path(__file__)],
            [path, root / 'previous-pattern-change-trace.json', root / 'AB-pattern-overlap.json'])
    print(path)


if __name__ == '__main__':
    main()
