#!/usr/bin/env python3
"""Output-only V15 reporting after the fixed batch; does not alter/run methods."""
import csv
import datetime as dt
import hashlib
import json
from collections import Counter
from pathlib import Path
from scripts.proof_source_alignment_v15 import ROOT, read, save, textsave, assert_frozen


def main():
    assert_frozen()
    observations = {
        '396336': {
            'finding': '自动建立Imrit与其余成员的角色对应，并另提明确见证；原F08的null引文保留。两个完整前提获得独立模型审阅接受，恢复无联合／无全部分离推定的限定规则。',
            'sources': ['L133', 'L139', 'L146', 'L147', 'L148', 'L150', 'L157', 'L159', 'L160', 'L161', 'L163', 'L164', 'L167', 'L169', 'L170', 'L173', 'L181', 'L185', 'L186'],
            'boundary': '缺全面分家契约、确切日期和后续共同交易均被保留；法院已采纳的历史分离评价作为外部语义前提。TRUE仅表示无推定规则适用，不表示本程序证明全部产权或整案胜败。',
            'natural_problem': '将法院解决反论的L186同时放在counterevidence中，功能分类不够清楚；审阅指出它是反论的处理，不是独立反证。对选定规则未造成决定性方向错误。',
            'V14_comparison': 'V14人工校准与V15自动提议／独立审阅均得到限定TRUE，但语义补充来源与成本不同；V14校准答案未进入任务。',
        },
        '594273': {
            'finding': '自动连接East Punjab与TPA及Ganeshi Lal／共同抵押／其他共抵押人；区分下级法院关于原抵押与个人赎回的认定和最高法院争点框定。两项前提均接受。',
            'sources': ['L103', 'L104', 'L105', 'L106', 'L107', 'L108', 'L110', 'L111', 'L112', 'L115', 'L116', 'L117', 'L120', 'L121', 'L122', 'L124', 'L125', 'L159', 'L160', 'L161', 'L174', 'L177'],
            'boundary': '只确认此历史争议采用衡平原则而非直接套用TPA条文；不决定当代法、92条溯及、各人最终份额或金额。否认、让与论与未决继承份额保留。',
            'natural_problem': 'other_debtors为既有集合名称，足以识别共同争议，不足以证明每名被告相同责任。提议及审阅明确保留这一限制，本地不升级为逐人责任判断。',
            'V14_comparison': '与V14限定TRUE方向相同；新对象对应和见证来自实际新提议，非旧overlay。共同确定性修复还恢复了一处唯一大小写引文，不能把该变化算作模型收益。',
        },
        '121775': {
            'finding': '提议正确区分条款11的六个月通知提前终止与Part III普通期满，条件性结果FALSE；审阅拒绝A01整体连接，接受A02明确不完整的用途说明。R因此UNKNOWN。',
            'sources': ['L54', 'L55', 'L58', 'L60', 'L62', 'L63', 'L71', 'L80', 'L86', 'L89', 'L113', 'L114', 'L115', 'L118', 'L119', 'L120'],
            'boundary': 'A01的否定判断有L118–119明确支持；拒绝针对terminating_lessor绑定，不能把拒绝解释为该否定判断错误。A02仅保留非移走主张及条款区别，程序不据此生成完整前提。',
            'natural_problem': 'A01将Province of Bengal绑定为合同Secretary of State角色，同时明示未确认两者对应，属于提议内部的绑定／限制不一致。独立审阅依严格身份合同拒绝；不存在事件的否定证明是否必须具备该正向角色是验收粒度争议，不能把本次阻止计为确定法律纠错。',
            'review_granularity_risk': 'R整项接受门槛也遮住了原文明确的否定分类；A02缺完整正向组成并不消除其合法反对／背景用途。原始内容继续保存，未人工修正，不在本批放宽覆盖规则。',
        },
        '907531': {
            'finding': '四个候选地址均结构通过、审阅接受：习惯存在为TRUE，诉讼时河道不再划分相关村界为FALSE。但两个替代路线均因既有R1引文QUOTE_NOT_LOCATED未执行。',
            'sources': ['L120', 'L123', 'L127', 'L129', 'L130', 'L131', 'L132', 'L133', 'L136', 'L137', 'L138', 'L139', 'L140', 'L142', 'L143', 'L146', 'L148', 'L149', 'L155', 'L156', 'L157', 'L158', 'L159', 'L160', 'L161', 'L162', 'L163', 'L164', 'L165'],
            'boundary': '区分历史习惯存在、突然变道适用范围和当前地理前提；保留原告主张、被告外村延伸主张及未来复活可能。两组地址是同一请求的替代材料，不是四个独立事件。',
            'natural_problem': '既有规则quote用established，L137原文为estab- lished。严格定位器不删除断词连字符，产生QUOTE_NOT_LOCATED；不是引文地址不存在、法源缺失或模型无法理解。冻结后未修复重放。',
        },
    }
    rows, costs, traces = [], [], []
    decisions = Counter()
    structure = Counter()
    for c in read(ROOT / 'selection.json')['cases']:
        cid = c['case_id']
        b = read(ROOT / 'inputs' / cid / 'bundle.json')
        p = read(ROOT / 'raw' / cid / 'proposal/import.json')['answer']
        rv = read(ROOT / 'raw' / cid / 'review/import.json')['answer']
        zs = {v: read(ROOT / 'runs' / cid / v / 'checked.json') for v in ['D', 'P', 'R']}
        row = {'case_id': cid, 'request_id': c['request_id'], 'deep_V14_development': c['deep_V14_development'],
               'technical_status': 'ALL_TASKS_COMPLETE_AND_STRUCTURED_RUNS_OK',
               'D': zs['D']['requests'][0]['answer'], 'P': zs['P']['requests'][0]['answer'],
               'R': zs['R']['requests'][0]['answer'], 'answer_meaning': b['requests'][0]['predicate'],
               'formal_legal_approval': False, **observations[cid]}
        row['program_obstacles'] = {v: [{'state': a['state'], 'errors': a['errors'], 'pending': a['pending']}
                                        for a in zs[v]['requests'][0]['alternatives']] for v in zs}
        rows.append(row)
        for a in zs['R']['structure_checks'].values():
            structure[a['structural_status']] += 1
            decisions[a['review']['submitted_decision']] += 1
        trace = {'case_id': cid, 'request': b['requests'][0], 'source_order': b['source_order'],
                 'old_P_unchanged': True, 'deterministic_repairs': b['deterministic_repairs'],
                 'slots': [{'directory': d,
                           'model_alignment': next(a for a in p['alignments'] if a['address'] == d['address']),
                           'review': next(a for a in rv['reviews'] if a['address'] == d['address']),
                           'checks': zs['R']['structure_checks'][d['address']]}
                          for d in b['directory']],
                 'views': {v: zs[v]['requests'] for v in zs},
                 'opposition_and_limits_preserved': True, 'formal_legal_approval': False,
                 'no_free_answer_generation_after_checks': True}
        save(ROOT / 'paths' / cid / 'trace.json', trace)
        traces.append({'case_id': cid, 'path': str(ROOT / 'paths' / cid / 'trace.json')})
        for role in ['proposal', 'review']:
            run = read(ROOT / 'raw' / cid / role / 'run.json')
            taskfile = ROOT / 'tasks' / cid / (role + '-task.txt')
            rawfile = ROOT / 'raw' / cid / role / 'assistant.txt'
            start = run.get('submitted_at')
            end = run.get('completed_observed_at') or run.get('observed_complete_at')
            interval = (dt.datetime.fromisoformat(end.replace('Z', '+00:00')) - dt.datetime.fromisoformat(start.replace('Z', '+00:00'))).total_seconds() if start and end else None
            costs.append({**run, 'task_file': str(taskfile), 'task_bytes': taskfile.stat().st_size,
                          'task_sha256': hashlib.sha256(taskfile.read_bytes()).hexdigest(),
                          'raw_file': str(rawfile), 'raw_bytes': rawfile.stat().st_size,
                          'raw_sha256': hashlib.sha256(rawfile.read_bytes()).hexdigest(),
                          'observed_submit_to_capture_seconds': interval,
                          'observation_is_not_exact_generation_time': True,
                          'input_tokens': None, 'output_tokens': None})
    save(ROOT / 'case-comparison.json', rows)
    save(ROOT / 'cost.json', {'web_calls': 8, 'new_local_model_calls': 0, 'new_fits': 0, 'retries': 0,
                              'web_legal_search': 0, 'model_visible': 'GPT-6', 'mode_visible': 'High',
                              'exact_model_revision': None, 'exact_generation_seconds': None,
                              'new_uploaded_task_bytes': sum(x['task_bytes'] for x in costs),
                              'raw_answer_bytes': sum(x['raw_bytes'] for x in costs),
                              'old_V12_active_fit_not_a_V15_fit': True, 'tasks': costs})
    save(ROOT / 'final-source-review.json', {
        'identity': 'ONE_CONCENTRATED_MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
        'performed_after_all_eight_web_tasks': True, 'reviewed_units': 'FOUR_FIXED_REQUESTS_AND_DECISIVE_ALIGNMENT_RECORDS',
        'not_full_P_reannotation': True, 'formal_legal_approval': False,
        'web_review_decisions': dict(decisions), 'structural_slot_counts': dict(structure),
        'counts_not_independent_cases_or_accuracy': True, 'cases': rows,
        'shared_limit': 'The checker validates addresses/declared coverage/bindings and explicit combination. It does not independently prove semantic completeness, object equivalence, court attribution or the law.'})
    save(ROOT / 'learning-decision.json', {
        'direction': 1, 'decision': 'RETAIN_SOURCE_ALIGNMENT_WITH_INDEPENDENT_REVIEW_FOR_BOUNDED_DEVELOPMENT_ONLY',
        'reason': 'The fixed process recovers two scoped paths with reviewed support and retains sourced negative classification and historical/temporal limits in the other requests. One explicit object-role inconsistency is caught by review; an old rule quotation independently blocks another request. Retain the step as a development candidate, without claiming stable autonomous operation on unseen cases.',
        'train_use_three_classes_next': False, 'start_training_now': False,
        'future_single_candidate_target': 'VERIFY_SOURCE_GROUNDED_ALIGNMENT_FOR_A_FIXED_PREMISE',
        'input': ['allowed original source and fixed rule scope', 'original P and proposed role/variable/object binding', 'specific function, statement stage and whole-premise coverage claim'],
        'output': 'ACCEPT/REJECT/UNRESOLVED for the explicitly scoped semantic alignment; retain limited valid functions separately from whole-premise sufficiency',
        'supervision': 'Versioned independent source-review decisions with exact witnesses and recorded disagreements, not automatic gold and not raw USABLE relabeling',
        'simplest_baseline': 'Current deterministic checker plus raw alignment proposal; compare actual natural errors and legitimate inference coverage before adding a learner',
        'why_program_insufficient': 'Present source checks can find a valid quotation without proving that it establishes equivalence of institutional roles or coverage of the whole legal proposition.',
        'GNN_CrossEncoder_position': 'If separately authorized and sufficiently supervised, verify this same alignment information; no graph propagation or architecture change established by this batch.',
        'natural_definite_training_errors_too_few': True, 'review_granularity_dispute_preserved': True,
        'no_generalization_or_legal_certification_claim': True, 'stop_after_delivery': True})
    with (ROOT / 'comparison.csv').open('x', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['case_id', 'request_id', 'D', 'P', 'R', 'technical_status', 'finding', 'natural_problem', 'boundary'])
        w.writeheader()
        for r in rows: w.writerow({k: r[k] for k in w.fieldnames})
    md = ['# V15 四个请求的来源到推导轨迹', '', '原P、自动提议、独立审阅分别保存。TRUE/FALSE指所选规则的限定适用结果；没有正式法律批准。', '']
    for r in rows:
        cid = r['case_id'];md += [f"## {cid} / {r['request_id']}", '', f"D={r['D']}；P={r['P']}；R={r['R']}。{r['finding']}", '', r['boundary'], '', r['natural_problem'], '',
             f"[完整逐步轨迹](paths/{cid}/trace.json) · [原始提议](raw/{cid}/proposal/assistant.txt) · [独立审阅](raw/{cid}/review/assistant.txt)", '',
             '来源 → 角色与用途 → 完整前提 → 固定规则 → 限定结果：', '']
        t = read(ROOT / 'paths' / cid / 'trace.json')
        for slot in t['slots']:
            d, a, ck = slot['directory'], slot['model_alignment'], slot['checks']
            refs = sorted({ref for comp in a['whole_premise']['components'] for wit in comp['witnesses'] for ref in wit['refs']})
            md += [f"- **{d['address']} / {d['premise_id']}**：{d['proposition']}", f"  原文地址：{', '.join(refs)}。模型完整状态={a['whole_premise']['state']}，覆盖声明={a['whole_premise']['complete']}；结构={ck['structural_status']}；审阅={ck['review']['decision']}。", '']
    textsave(ROOT / 'walkthrough.md', '\n'.join(md))
    report = '''# V15 自动来源对齐与条件性推导：完成报告

本轮完成四个固定DEV请求、四次来源对齐提议、四次独立来源审阅及D/P/R三个结果视图，重试0、本地模型调用0、新训练0。工程验收22项通过；所有八份回复可解析。**自动流程在两个深度开发请求中恢复了有来源、经模型辅助审阅接受的限定路径，但尚未证明能够稳定自行完成其他请求。保留来源对齐步骤作为需审阅的候选，不恢复用途三分类训练。**

| 案件／请求 | D确定性适配 | P条件性推导 | R审阅接受视图 | 实际含义与障碍 |
|---|---|---|---|---|
| 396336 / Q1::R1 | UNKNOWN | TRUE | TRUE | 恢复明确成员对应与新的文书见证，组合无联合／无全部分离推定规则；不证明全部继承产权。 |
| 594273 / Q2::R5 | UNKNOWN | TRUE | TRUE | 恢复地域、法条与共抵押争议前提；保留下级认定、否认与未决金额份额。 |
| 121775 / Q2::R6 | UNKNOWN | FALSE | UNKNOWN | 正确否定特殊提前终止，但正向制度主体绑定有未证对应；整项审阅拒绝使有依据的负向分类也未进入接受组合。 |
| 907531 / Q1::R1 | UNKNOWN | UNKNOWN | UNKNOWN | 四个候选前提得到接受，但既有规则引文断词差异使两条替代路线均未执行。 |

这些标签是固定请求规则的限定适用结果，不是案件胜败或未知事实的统计。前三案各一条既有候选路线，第四案两条；全部替代路线、反论和局部缺口保存。同案重复前提不作为独立案件。所有结果缺正式法律批准，R仅为独立模型辅助来源审阅后的研究接受状态。

## 实现与工程边界

新入口先由来源ID恢复允许原文，生成候选／前提地址目录及固定规则角色说明。模型只提出角色—变量—具体对象连接、见证、具体证据功能和单独的完整前提状态；程序附加版本、哈希和内部地址。原P不修改，旧null引文保留；模型另提明确见证与修补旧quote是两回事。594273仅有一处唯一大小写展示差异由共同适配恢复，记在deterministic_repairs中。

独立检查器由实际入口以单独进程运行，不调用任务装配器、旧参考、V14校准或学习模型。共享可逆引文定位格式，不共享模型语义判断。结构PASS只说明所声明地址、角色、见证和覆盖形式符合合同；名称等价、完整性和归属含义仍须来源审阅。背景或部分支持、USABLE均不产生整个前提真值。OPEN_TEXT不改为AND，未知不变为否定，例外和独立择一分支继续局部处理。

22项相关检查含10项本轮测试与12项既有回归，覆盖实际检查子进程、自我批准拒绝、类型／身份区分、部分不等于完整、否定引文变更、局部OR保留、阶段、开放规则和null失败。最初缺jsonschema时复用仓库既有无依赖校验器，未安装；另修正一处测试数据共用可变对象的错误。测试只验证工程行为。冻结后方法、合同、规则和任务未改，运行后发现的问题没有在同批修后重跑。

## 一次集中来源审阅

396336的L157承认Imrit分离，L159–164、L170／173支持法院采用的历史分家及财产份额推断；L139、L181–186的相反叙述、后续共同生活与交易没有被删除。L146–148的无推定规则与历史事实分开。自动过程建立明确成员对应并增加见证，没有读入V14校准值。L186是法院对反论的处理，提议将其列在counterevidence中不够准确；独立审阅明确指出功能差别。限定TRUE可保留，但不能变成所有财产及继承结论。

594273的L107明确归属于Subordinate Judge及High Court；L115–116是最高法院框定代位范围争议；L121–122是历史地域法与衡平原则选择。新提议没有将下级判断改称最高法院自己查明的事实，也保留L105–106的否认与L110–112的让与反论。L174／177未决份额与继承问题不能由R5填平。集合对象other_debtors只支持共同争议语境，不支持每人相同最终责任。

121775的L118–119清楚区分特殊提前终止与普通期满；L54记Province执行租约、L58将特殊权力写作Secretary of State。提议在承认尚未证明对应时，仍把前者BOUND到terminating_lessor。严格对象合同下，审阅拒绝A01整项是可解释的；但这不证明原文明确的负向分类错误。否定不存在的特殊事件是否还需其正向行为主体完整绑定，以及整项拒绝遮住合法负向判断，保留为接受粒度限制。A02反对／背景用途获接受，却因complete=false、部分未覆盖及混合陈述状态不能成为完整执行前提。合法反证仍完整保存，未将它们计为无用材料，也未人工修正提议。

907531的L136–149支持习惯存在与突然变道的历史范围，L155–163限制其在河道离开村界时的适用，L165保留未来复活且不确定后来河道位置。新提议与审阅保持主张、历史文书记载和法院评价分开。四个地址为同一两前提的替代材料，审阅九接受／一拒绝的总数不能当十个独立样本。阻碍来自旧R1 quote的established与L137的estab- lished，实际错误为RULE_SOURCE:QUOTE_NOT_LOCATED。原文已经送达，不是法源未取得或模型判断失败；不放宽定位、不给本案特判、不据此补报FALSE推导。

## 改善归因与投入决定

D共享确定性修复后仍全未决。P恢复前两案，来自新的对象、用途和完整前提语义提议；R增加独立审阅成本并保留这些限定结果。V14人工校准仅在运行后作解释对照，没有进入受测任务。模型参考、程序计算和正式法律批准始终分开，没有图／CrossEncoder收益证据。

选择预定方向一的有限开发结论：**保留自动来源对齐及独立审阅步骤作为后续候选，不启动新训练。** 两条真实路径恢复，其他请求也保留了有依据的负向判断及历史范围；一项明确绑定不一致被审阅发现，另一项旧引文障碍被单列。本批未显示普遍大量语义重写的需要，但四个已暴露案件不能证明新案件上稳定自动运行。下一轮若另获授权，先扩大既定开发覆盖；若确需学习，最小候选只复核“固定前提的一项来源支持的语义连接是否有效”，包括角色对象对应、声明地位、用途及完整覆盖，不能恢复笼统USABLE三分类。输入允许原文、固定规则、P及具体提议，输出有范围的接受／拒绝／未决；监督来自带引文、限制和分歧记录的独立审阅，不自动gold。最简单基线就是本轮确定性检查＋原提议。

本批只有一个明确整项绑定拒绝，还有负向证明及整项接受粒度争议；不足以形成新的可靠训练集。两个深度开发请求的恢复和一个新请求的有效前提，不证明泛化。旧20条校准只生成兼容清单：13条有限一致、3条语义不同、3条用途不明、1条争议；未检查的标签继续未认证，不改TRAIN，不启封TEST／SEALED。

## 成本、记录与交付

普通High新任务8次，先四提议后四审阅，均独立临时对话。提交前与登录恢复后的界面均实际显示GPT-6／High；精确revision、tokens、内部上下文和推理时间不可得。文件字节及提交到取回的观察时间见cost.json，不能作为精确推理耗时；中间登录恢复延迟也可能扩大该时间。已核对完整附件装配与来源身份，但无法证明网页端每个token实际被模型读取。未发现外部搜索或旧参考输入记录。

登录故障发生于第三份尚未提交审阅；前六份未重发。恢复后只提交剩余两份。旧V12当前CrossEncoder种子仍按原暂停安排运行及保存，未启动其他种子；不是V15训练成本。HEAD及工作区记录保存；89项旧实现文件和四对原来源／P哈希保持，未宣称重哈希全部历史输出。

完整交付：[逐案比较](case-comparison.json)、[D/P/R结果](three-views.json)、[逐步来源链](walkthrough.md)、[集中来源审阅](final-source-review.json)、[投入决定](learning-decision.json)、[成本](cost.json)、[工程验收](engineering-acceptance.json)、[冻结配置](freeze/config.json)、[实际提交清单](final-submission-manifest.json)、[旧记录保留核验](preservation-validation.json)。原始回复、完整任务、动态审阅装配、实际独立入口文件及网页URL均本地保存；截图及账户UI不进入发布清单。

本轮完成有界开发交付，正式法律批准缺失；不新增网页任务、训练、案件或法源，不提交或推送。prepare、清单检查和verify结果见repository-verification.json。交付后停止。
'''
    textsave(ROOT / 'report-zh.md', report)
    save(ROOT / 'completion.json', {'status': 'COMPLETE_BOUNDED_V15_DEVELOPMENT', 'web_tasks_complete': 8,
                                   'technical_failures': 0, 'new_fits': 0, 'formal_legal_approval': False,
                                   'prescribed_batch_and_single_concentrated_review_done': True,
                                   'no_automatic_next_round': True})


if __name__ == '__main__':
    main()
