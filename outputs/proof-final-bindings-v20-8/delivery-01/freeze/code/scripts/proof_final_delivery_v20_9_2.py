"""Verify exact accepted artifacts and write the isolated local delivery report."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.proof_final_bindings_v20_8 import OUT, read, verify as verify_base
from legal_bench.proof_carrying import final_statement_review_v20_9_1 as core
from legal_bench.proof_carrying.artifact_state_v20_2 import immutable, digest, byte_hash, freeze_files, verify_files

CASES = [('1954254', 'statement-pack-01', 'final-acceptance-corrected.json',
          'whole-answer-review/web-response-corrected.json', 'generation/parsed.json'),
         ('569555', 'statement-pack-03', 'final-acceptance.json',
          'whole-answer-review/parsed.json', 'ordering-plan.json'),
         ('1187427', 'statement-pack-02', 'final-acceptance.json',
          'whole-answer-review/parsed.json', 'ordering-plan.json')]


def write_once(path, body):
    path = Path(path)
    if path.exists() and path.read_text() != body:
        raise ValueError('DELIVERY_TEXT_CHANGED:' + str(path))
    if not path.exists(): path.write_text(body)


def readable(cid, answer):
    parts = [f'# {cid} — 本轮来源核验通过的案例重建',
             '这是开发案例的模型来源核验结果。不是人工金标准、律师批准或可执行法律结论；旧前提的计算状态仍保留。',
             '## 摘要', answer['conclusion'], '## 当事人、法院与物业']
    for r in answer['case_frame']['actors']:
        parts.append(f"- {r['name']}：{', '.join(r['capacities'])}；{r['kind']}；编号 {r['id']}。")
    for r in answer['case_frame']['properties']:
        parts.append(f"- 物业：{r['description']}；编号 {r['id']}。")
    parts.append('## 程序与事件')
    for r in answer['case_frame']['events']:
        parts.append(f"- {r['description']}（行为主体 {r['actor_id']}；阶段 {r['stage']}；来源 {', '.join(r['refs'])}）")
    for label, key, textkey in [('依据', 'grounds', 'explanation'),
                                ('相反观点与处理', 'counterarguments', 'treatment')]:
        parts.append('## ' + label)
        for r in answer[key]:
            parts.extend([r['point'], r[textkey],
                          '来源：' + ', '.join(r.get('case_refs', r.get('refs', [])))])
    parts.append('## 未决与裁判范围')
    parts.extend(answer['gaps'])
    return '\n\n'.join(parts) + '\n'


def deliver():
    verify_base()
    rows = []
    for cid, root, result_file, review_file, plan_file in CASES:
        d = OUT / root / 'cases' / cid
        verify_files(ROOT, read(d / 'freeze/protocol.json'))
        task, case, plan, review = (read(d / f) for f in
                                   ('task.json', 'source.json', plan_file, review_file))
        result = read(d / result_file)
        recomputed = core.accept_final(task, json.dumps(plan), 'OK', case=case, review=review)
        if result != recomputed:
            raise ValueError('FINAL_RESULT_REPLAY_MISMATCH:' + cid)
        if result['contract_status'] != 'MODEL_SOURCE_REVIEW_ACCEPTED_NOT_LEGAL_SUCCESS' or result['answer'] is None:
            raise ValueError('FINAL_SOURCE_REVIEW_NOT_ACCEPTED:' + cid)
        if result['legal_approval']:
            raise ValueError('UNAUTHORIZED_LEGAL_SUCCESS_CLAIM')
        rt = read(d / 'whole-answer-review/task.json')
        if any(v['label'] != 'SUPPORTED' for group in ('verdicts', 'coverage')
               for v in review[group].values()):
            raise ValueError('SOURCE_REVIEW_NOT_ALL_SUPPORTED:' + cid)
        if digest(case['segments']) != read(OUT / 'cases' / cid / 'bridge.json')['source_sha256']:
            raise ValueError('SOURCE_CHANGED:' + cid)
        answer = result['answer']
        for record in task['pack']['records']:
            section = record['section']
            if section == 'SUMMARY': assert record['text'] in answer['conclusion']
            elif section == 'LIMITATION': assert record['text'] in answer['gaps']
            else:
                pool = answer['grounds'] if section == 'GROUND' else answer['counterarguments']
                row = next(x for x in pool if x['claim_ids'] == [record['id']])
                assert row.get('explanation', row.get('treatment')) == record['text']
                assert all(row[k] == record[k] for k in ('actor_ids', 'property_ids', 'event_ids'))
        assert answer['case_frame'] == task['frame']
        assert len(plan['record_order']) == len(set(plan['record_order'])) == len(task['pack']['records'])
        write_once(d / 'accepted-answer-zh-heading.md', readable(cid, answer))
        rows.append({'case_id': cid, 'accepted_result': str((d / result_file).relative_to(ROOT)),
                     'readable_answer': str((d / 'accepted-answer-zh-heading.md').relative_to(ROOT)),
                     'contract_status': result['contract_status'], 'legal_approval': False,
                     'summary_characters': len(answer['conclusion']), 'statement_records': len(task['pack']['records']),
                     'field_review_units': len(rt['units']), 'supported_field_units': len(review['verdicts']),
                     'coverage_checks': len(review['coverage']), 'all_source_checks_supported': True,
                     'source_sha256': digest(case['segments']), 'task_sha256': task['input_sha256'],
                     'answer_sha256': digest(answer), 'all_reviewed_statement_text_and_bindings_preserved': True,
                     'unreviewed_assumptions': len(answer['assumptions']),
                     'actual_new_ordering_call': str((OUT/'statement-pack-01/cases'/cid/'generation/run.json').relative_to(ROOT)),
                     'final_adjustment_is_cache_replay': cid in ('1187427','569555')})
    accounting = read(OUT / 'engineering/run-accounting-final.json')
    tests = read(OUT / 'engineering/tests-v20-9-2.json')
    assert tests['passed'] and accounting['total_api_cost_or_bound_usd'] <= accounting['maximum_total_cost_usd']
    results = {'version': 'V20_9_2_LOCAL_SOURCE_RECONSTRUCTION_DELIVERY', 'cases': rows,
               'accepted_cases': len(rows), 'total_cases': len(rows), 'tests': tests,
               'api_accounting': accounting,
               'scope': 'EXPOSED_DEVELOPMENT_CASE_ENGINEERING_AND_MODEL_SOURCE_REVIEW',
               'not_human_gold': True, 'not_automatic_extraction_accuracy': True,
               'not_paper_or_gnn_effectiveness_evaluation': True,
               'main_entry_switched': False, 'training_commit_push': False,
               'old_freewriting_server_truncation_unique_cause': 'UNKNOWN',
               'other_side_chat_and_shared_files_not_written': True}
    immutable(OUT / 'results.json', results)
    table = '\n'.join(f"| {r['case_id']} | {r['statement_records']} | {r['summary_characters']} | {r['supported_field_units']}/{r['field_review_units']} | {r['coverage_checks']}/11 |"
                      for r in rows)
    answers = '\n'.join(f"- [{r['case_id']}完整答案](/{ROOT}/{r['readable_answer']})".replace('//Users','/Users') for r in rows)
    report = f'''# 最终答案修复与实验验收报告

本轮三个开发案例全部通过最终原文一致性与覆盖验收，85项工程检查通过。通过范围是核验后声明的主体、物业、程序阶段、条件、相反观点和裁判范围；不是人工金标准、自动抽取准确率、Paper/GNN效果或法律批准。主实验入口尚未切换。

| 案例 | 固定声明条数 | 摘要字符数 | 支持的字段/字段总数 | 支持的覆盖检查 |
|---|---:|---:|---:|---:|
{table}

## 修了什么，为什么

480字符上限来自此前共用字段规则导致摘要和辅助说明共用限制。已有修复保留，当前摘要直接完整渲染已核验原句，没有480字符切片。三案最终摘要均超过480字符，所有摘要声明原句都完整保留。

主体错配包含明确的接口缺陷：局部OBJ编号跨前提含义不同，合并数组位置却被当成身份；记录声明的法院与实际行为法院混用；最终输入缺少原对象定义。新桥接保存局部业务地址、全局位置映射、原定义和依赖。行为主体、受影响当事人、听审法院与记录法院分别保存；政府通知与退休使用独立类别。旧错误声明保留阻断，新实体必须重新来源核验。

固定主体表之后，一次真实自由写作仍把下级认定写成高等法院认定。后续旧声明选择又遗漏明确的裁判保留。这些失败说明，仅修格式或提示词不够。当前接口让Qwen只组织已来源核验的类型声明编号，程序逐字生成全部声明及事件表，模型不能补写事实、重新绑定主体或添加未经核验假设。摘要保留声明的归属和裁判阶段，已排除事实也不能在最终写作阶段重新进入正文。

整案核验进一步修正了1187427把退休日期与任职期间占用房屋过度合并的问题；修正框架重新核验，原26条声明和真实排序结果不变。569555补入多数意见拒绝采用“但书仅为指导性”的理论和Sarkar异议对其他1958年事由不作意见的保留，并补齐联合判决对Association的影响。原22条声明保持不变，两条新增保留重新来源核验后才追加；整案核验重做且通过。

1954254最初的177项字段与11项覆盖全部支持，但核验记录把规则哈希抄漏一个字符。程序先拒绝；网页核验会话用Python从原Schema读取绑定值并合并原记录。本地确认来源判定、理由与覆盖完全不变，旧拒绝结果保留，修正验收另存。验收条件没有放宽。

## 实验与缓存证据

7次真实Qwen API调用包含一次自由写作、三次旧声明选择、三次完整类型声明排序。最终三案各有一次真实排序生成，完整原文输入未删减，均正常结束；后续1187427和569555的来源修正使用透明缓存回放，没有伪装成再次生成。569555的两条新增声明由程序追加到原排序前缀，回放收据记录新增内容与重新来源核验。1954254只校正核验记录的绑定字段。

缓存检查确认三案完整原文、338个原局部声明、171个全局对象位置、509个原已接受声明、102个原被阻断声明及其依赖保留。所有当前72条核验声明在最终答案中保留完整原句与绑定；原始缓存的保存不等于原始所有内容都展示在答案中，答案覆盖按当前请求的11项要求另行核验。旧前提计算仍保留UNKNOWN，没有把法院历史叙述当成已满足的法律证明。

85项工程检查包括范围编号、非法主体类型、空白来源、依赖、声明变动使核验失效、禁止遗漏/重复编号/新正文、身份审阅材料、来源补充回放及技术失败保持null。标签注入只用于程序检查。另对旧V20.7保存的480个文件逐一核对哈希，全部未变；三案当前冻结代码与数据依赖也验证通过。

本轮API费用或保守估计为 {accounting['new_api_cost_or_bound_usd']:.8f} 美元，连同此前为 {accounting['total_api_cost_or_bound_usd']:.8f} 美元，保持原0.50美元上限。ChatGPT Web来源核验的订阅使用不计入API token费用。分词计数修复在孤立运输层实现，7个观察请求的实际token序列长度与服务计数一致，当前余量策略覆盖已观察请求；没有宣称任意未来请求都保证相同上限。

## 剩余边界

声明包包含开发阶段的模型提议、原文核对和补充，尚未证明未见案例能自动得到同等完整的声明包。核验者是另一个ChatGPT Web会话，没有人工金标准，网页精确模型修订号不可用。不能从这三案得出Paper机制有效或GNN优于检索的结论。

旧1954254自由生成时服务提前结束的唯一原因仍未知。当前接口生成编号并渲染固定文字，避免模型重新生成长事实正文；这没有证明原来长自由写作的服务端截断问题已根治。此前4个分析任务的完整性结果也不能由本轮三案的最终答案验收推广到所有任务。

本次只写独立模块、自己的文档和输出目录，未修改另一条side chat的检索/GNN模块、测试、运行环境或共享入口。没有训练、提交或推送；共享索引注册与主入口接线留给整合阶段，避免并行写入冲突。可重放入口是 `scripts/proof_final_statement_completion_v20_9_2.py`；当前已接受结果的本地验证与报告入口是 `scripts/proof_final_delivery_v20_9_2.py`，不会调用模型。

## 完整结果与核验材料

{answers}

结果摘要：`results.json`。缓存与预算材料：`engineering/cache-acceptance.json`、`engineering/run-accounting-final.json`、`engineering/token-budget-calibration-final.json`、`engineering/tests-v20-9-2.json`、`engineering/preservation-final.json`。各案例目录保存完整来源、任务、原始生成、声明包、事件框架、原文核验与最终验收；`replay-receipt.json`保存缓存回放差异。网页核验会话来源见 `engineering/reviewer-provenance.json`，可见记录截图保存在 `engineering/review-1954254-proof.png`。
'''
    write_once(OUT / 'report-zh.md', report)
    prepared = [str((OUT / p).relative_to(ROOT)) for p in
                ('results.json', 'report-zh.md', 'ownership-v20-9-2.json',
                 'engineering/run-accounting-final.json', 'engineering/tests-v20-9-2.json',
                 'engineering/preservation-final.json', 'engineering/reviewer-provenance.json',
                 'engineering/token-budget-calibration-final.json')]
    for row in rows:
        prepared.extend([row['accepted_result'], row['readable_answer']])
    prepared.append('docs/FINAL_BINDINGS_V20_8.md')
    manifest = freeze_files(ROOT, OUT / 'delivery-01', ['scripts/proof_final_delivery_v20_9_2.py',
                             'scripts/proof_final_statement_completion_v20_9_2.py'], prepared)
    immutable(OUT / 'delivery-01/freeze/protocol.json', manifest)
    verify_files(ROOT, manifest)
    print(json.dumps({'accepted': len(rows), 'tests': tests['tests_run'],
                      'api_calls': accounting['actual_api_calls'],
                      'total_cost': accounting['total_api_cost_or_bound_usd']}))


if __name__ == '__main__': deliver()
