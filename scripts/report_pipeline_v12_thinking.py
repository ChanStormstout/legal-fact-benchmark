"""Bounded thinking comparison delivery; no model calls or output repairs."""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.pipeline_v12_thinking import ROOT, OLD, read, verify
from legal_bench.rules_verdict_v1.source_views import digest, write_new

frozen = verify()
results = read(ROOT / 'results.json')
assert results['new_model_calls'] == 2 and results['retries'] == 0
metas = {r['condition']: r for r in results['rows']}
source = read(ROOT / 'sources/69305.json')
law = read(ROOT / 'prepared/69305/law-package.json')
case_map = {s['id']: s['text'] for s in source['segments']}
law_map = {s['id']: s['text'] for s in law['law_segments']}
names = [('D-thinking', 'D'), ('B-P-thinking', 'B-P')]
new = {n: read(ROOT / 'runs' / n / 'parsed.json') for n, _ in names}
old = {o: read(ROOT / 'lineage' / o / 'parsed.json') for _, o in names}
assert metas['D-thinking']['run_status'] == 'RUN_LOG_ERROR'
assert metas['D-thinking']['answer_status'] is None
assert metas['B-P-thinking']['run_status'] == 'OK'

protocol_rows = []
restored = {}
for n, o in names:
    p = ROOT / 'runs' / n
    m = metas[n]
    assert (p / 'prompt.txt').read_bytes() == (OLD / 'runs' / o / 'prompt.txt').read_bytes()
    assert (p / 'schema.json').read_bytes() == (OLD / 'runs' / o / 'schema.json').read_bytes()
    assert (p / 'rendered.txt').read_bytes() == (ROOT / 'prepared' / n / 'rendered.txt').read_bytes()
    assert m['actual_parameters'] == frozen['actual_parameters']
    ids = read(p / 'token-ids.json')
    parts = read(p / 'partitioned-token-ids.json')
    assert ids == parts['thinking'] + parts['delimiter'] + parts['final'] + parts['terminal']
    assert len(ids) == m['output_tokens'] and m['prompt_tokens'] + 8192 <= 32768
    raw = (p / 'raw-response.txt').read_text()
    assert raw == (p / 'thinking-response.txt').read_text() + '</think>' + (p / 'final-response.txt').read_text()
    assert json.loads((p / 'final-response.txt').read_text()) == new[n]
    phases = read(p / 'mask-phase-history.json')
    final_mask = read(p / 'final-mask-history.json')
    assert phases[0]['phase'] == 'THINKING'
    first = next(x for x in phases if x['phase'] == 'FINAL')
    assert final_mask[0]['generated_count'] == 0 and final_mask[0]['prefix_length'] == 0
    assert len([x for x in phases if x['phase'] == 'FINAL']) == len(final_mask)
    assert all(x['answer_offset'] is None for x in phases if x['phase'] == 'THINKING')
    protocol_rows.append({'condition': n, 'input_tokens': m['prompt_tokens'],
        'prompt_schema_exact_V11': True, 'generated_partition_exact': True,
        'thinking_unconstrained_and_unguarded': True, 'first_final_parser_generated_count': 0,
        'first_final_callback': first, 'schema_mask_calls': len(final_mask),
        'thinking_template_open': True, 'raw_split_exact': True,
        'native_budget_events': read(p / 'native-budget-events.json'),
        'metadata_failure': m['run_status'] == 'RUN_LOG_ERROR'})
    restored[n] = [{'ground': i + 1, 'point': g['point'],
        'case_sources': [{'id': x, 'text': case_map[x]} for x in g['case_refs']],
        'law_sources': [{'id': x, 'text': law_map[x]} for x in g['law_refs']],
        'valid_address_not_support_verification': True} for i, g in enumerate(new[n]['grounds'])]
assert read(ROOT / 'prepared/D-thinking/intermediate.json') == {}
assert read(ROOT / 'prepared/B-P-thinking/intermediate.json') == {'proposal': read(ROOT / 'inherited/B-proposal.json')}
assert read(ROOT / 'inherited/B-proposal.json') == read(OLD / 'intermediates/B-new.json')
addendum = read(ROOT / 'freeze/logging-only-addendum/config.json')
for p, h in addendum['live_code'].items(): assert digest(Path(p).read_bytes()) == h
write_new(ROOT / 'protocol-audit.json', {
    'rows': protocol_rows, 'two_inference_calls_only': True, 'web_calls': 0, 'retries': 0,
    'proposal_unmodified_no_checks': True, 'framework_packages_unmodified': True,
    'original_freeze_unchanged': True, 'logging_only_addendum_verified': True,
    'deviation': 'D run metadata serialization failed after complete output. A separately frozen logging-only copy ran unstarted B once; D was not rerun. D exact timing/memory remain unavailable.',
    'review_evidence_excludes_reasoning': True})
write_new(ROOT / 'restored-final-sources.json', restored)
write_new(ROOT / 'final-answers.json', {
    'D-thinking': {'run_status': 'RUN_LOG_ERROR', 'answer': None,
                   'retained_generated_json_path': 'runs/D-thinking/parsed.json',
                   'retained_text_is_not_completed_experiment_answer': True},
    'B-P-thinking': {'run_status': 'OK', 'answer': new['B-P-thinking']}})

review = {
    'type': 'ONE_CONCENTRATED_FINAL_SOURCE_REVIEW_AFTER_TWO_CALLS',
    'reference': 'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
    'reasoning_not_evaluated_or_used_as_evidence': True,
    'D_review_scope': 'Retained generated text only; technical failed answer stays null',
    'anchors': [
        {'refs': ['p0003.s003', 'p0003.s004'], 'finding': '1961是租约日期，不是明确记载的转移日期。租约后引入United可支持1952阈值的时间下界推断；必须说明这一连接，不得称原文明示了转移日期。条款文字跨两个片段，关联企业许可与本次交易适用、法定书面同意是不同问题。'},
        {'refs': ['p0004.s001', 'p0004.s002'], 'quote': case_map['p0004.s002'],
         'finding': '片段开头延续房东反对associate资格的立场。其后明确记载Rent Controller和上诉机构认为条款并非不可采、租户有权依赖，并认定United被引入为sub-lessee而命令腾退。最高法院最终处理被排除；已有下级认定不能升级为最高法院结论，也不能被说成不存在。'},
        {'refs': ['p0004.s003', 'p0004.s004'], 'finding': '佣金、同额租金和经销身份支持associate资格，以及S49 collateral purpose解释，均是租户律师的论证，允许材料没有最终法院采纳。'},
        {'refs': ['LAW:1134266:p0004.s004', 'LAW:1134266:p0004.s005'],
         'finding': '共同法律包支持历史S14(1)(b)基础条件，不完整解决本案未登记条款、关联企业范围或合同预先许可的法定效果。该法源晚于目标案，版本可迁移性未独立验证。'}],
    'D_thinking': {
        'eliminated_in_retained_text': [
            '不再说法院采纳租户律师的佣金等论点并认可United为associate。',
            '不再把未展示同意文件定为法院认定无同意，或说房东没有反对。',
            '不再直接把附条件租约文字定为足以击败请求的确定法定例外。'],
        'retained': ['仍遗漏条款可依赖和sub-lessee两项明确下级认定；g3/g4分别称转移定性、可采性没有法院认定。最高法院最终认定缺失不抹掉下级认定。'],
        'new_or_more_explicit': [
            'g1用租约日期作为转移事件日期的直接证明；reason称record establishes date of transfer。只能作带事件先后解释的阈值推断，原文没有明确转移日期。',
            'g2说明双方同意争议只引p0003.s003，没有指向房东无同意指控的续段p0003.s004及租户抗辩；有效编号不保证该行证据完整。'],
        'assessment': '更少无依据的确定判断，但把已有法院认定当成缺失。UNDETERMINED并非完整正确；D技术记录失败，仅作保留文本诊断。'},
    'B_P_thinking': {
        'improvements': ['g5和reason开始明确保留下级法院因转租命令腾退，并区分没有最高法院最终处理；没有自动升级为终审认可。',
                         '不再明确声称需要另行书面同意才能触发“无需进一步同意”的关联企业条款，旧reason的直接冲突不再出现。'],
        'retained': ['仍未保留下级法院允许依赖条款这一可采性处理。',
                     '合同存在、本次交易属于associate及法定书面同意的效力没有完整分开；输出只概括appellant论点，未具体处理United的经销身份/反对依据。',
                     '没有把租户主张升级为法院认可，也没有将没有专门同意文件定成确定无同意；这是旧B-P已具备的谨慎，不是本轮新增改进。'],
        'new_errors': [
            'g4称supplied text lacks a court finding resolving transfer characterization，g5又承认lower court ordered eviction on sub-letting；同一答案同时抹掉和承认下级定性。',
            'g3只以1961租约证明转移阈值，不再像旧B-P解释随后引入United的时间连接；reason不称确切日期，但证据解释变弱。',
            'g2 point合并“absent or unknown”，无法清楚区分同意不存在和资料未定，assessment的命题目标含糊；解释保持未决，没有确定否定。'],
        'source_binding_limit': 'g1仅引p0003.s003，许可条款的without such consent续文在p0003.s004，未引用；旧B-P也有条款引用不完整问题。没有新增颠倒身份或迁移公司合并事实。',
        'assessment': '有具体下级腾退认定保留的改善，但同一答案仍出现来源与内部矛盾，且遗漏下级可采性处理。无法作为可靠完整法律回答。'},
    'shared_limits': ['没有提供目标最高法院最终理由，不能要求猜回历史裁判。',
                      'associate资格和条款的法定效力仍有真实解释缺口；该缺口不能改称没有下级认定。',
                      '没有全部回答未知：两份均保留条款或时间的SUPPORTED，但支持解释仍需校验。',
                      '本轮没有程序检查块。问题不应解释为程序未实现；最终判断者可直接读同一原文。'],
    'decision': 'DO_NOT_ADOPT_THINKING_AS_DEFAULT_FOR_CURRENT_PIPELINE',
    'decision_zh': '暂不采用thinking作为当前流程的默认配置',
    'decision_basis': 'B-P出现下级腾退认定保留这一局部改善，但新增同一回答的定性矛盾，仍漏可采性认定；生成耗时约5.48倍。D保留文本减少过度判断但仍误称认定缺失，且技术元数据不完整。没有足够证据认领更忠实一致的完整答案，不代表thinking普遍无效。',
    'no_new_round_authorized_or_started': True,
    'independent_test_or_single_case_accuracy_claim': False}
write_new(ROOT / 'final-source-review.json', review)
write_new(ROOT / 'decision.json', {k: review[k] for k in ['decision', 'decision_zh', 'decision_basis']})

rows = []
for n, o in names:
    m = metas[n]; off = read(ROOT / 'lineage' / o / 'run.json')
    baseline_ids = read(ROOT / 'lineage' / o / 'token-ids.json')
    assert baseline_ids[-1] == 248046
    dr = n == 'D-thinking'
    rows.append({'case': '69305', 'condition': n, 'baseline': o,
        'technical_status': m['run_status'], 'answer_status': None if dr else new[n]['outcome'],
        'retained_text_outcome_not_accepted_answer': new[n]['outcome'] if dr else None,
        'baseline_outcome': old[o]['outcome'],
        'improvement': '不再捏造associate法院认可、无同意认定与房东未反对' if dr else '保留下级转租腾退及未有最高法院最终处理；旧同意trigger冲突不再明示',
        'remaining_error': '仍称转移定性与可采性没有法院认定' if dr else '仍漏下级允许依赖条款；associate及法定同意解释未完整处理',
        'new_error_or_weaker_evidence': '租约日期被称为转移日期的直接证明' if dr else 'g4没有法院定性与g5下级转租腾退相冲突；日期连接说明变弱',
        'input_tokens': m['prompt_tokens'], 'baseline_input_tokens': off['prompt_tokens'],
        'thinking_tokens': m['thinking_tokens'], 'final_content_tokens': m['final_tokens'],
        'delimiter_tokens': m['delimiter_tokens'], 'EOS_tokens': m['terminal_tokens'],
        'total_generated_ids': m['output_tokens'], 'baseline_generated_ids': off['output_tokens'],
        'baseline_final_content_tokens': len(baseline_ids) - 1,
        'extra_total_generated_ids': m['output_tokens'] - off['output_tokens'],
        'elapsed_seconds': m['elapsed_seconds'], 'baseline_seconds': off['elapsed_seconds'],
        'extra_exact_seconds': None if dr else m['elapsed_seconds'] - off['elapsed_seconds'],
        'elapsed_file_timestamp_estimate_seconds_not_exact': m.get('elapsed_file_timestamp_estimate_seconds'),
        'peak_mlx_memory_gb': m['peak_mlx_memory_gb'], 'baseline_peak_mlx_gb': off['peak_mlx_memory_gb'],
        'delta_peak_mlx_gb': None if dr else m['peak_mlx_memory_gb'] - off['peak_mlx_memory_gb'],
        'peak_rss_gb': m['peak_rss_gb'], 'baseline_peak_rss_gb': off['peak_rss_gb'],
        'review_status': 'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD'})
write_new(ROOT / 'comparison-table.json', rows)
with (ROOT / 'comparison-table.csv').open('x', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
write_new(ROOT / 'cost-ledger.json', {'actual_calls': 2, 'web_calls': 0, 'retries': 0,
    'input_tokens': sum(m['prompt_tokens'] for m in metas.values()),
    'total_generated_ids': sum(m['output_tokens'] for m in metas.values()),
    'thinking_tokens': sum(m['thinking_tokens'] for m in metas.values()),
    'final_content_tokens': sum(m['final_tokens'] for m in metas.values()),
    'delimiter_and_EOS_tokens': 4,
    'exact_total_inference_seconds': None,
    'estimated_total_from_D_file_timestamp_plus_B_seconds': results['round_inference_estimate_seconds'],
    'conservative_shared_wall_deadline_includes_logging_fix': True,
    'D_exact_memory_and_duration_missing': True,
    'not_equal_compute_toggle_experiment': True,
    'B_stage_reused_no_extraction_cost_this_round': True,
    'memory_note': 'MLX peak is framework allocated device memory; process RSS is separate and cannot be added as hardware total. Separate process and historical running order differ; small peak differences are not efficiency conclusions.'})

start = read(ROOT / 'start-audit.json')
changed = [p for p,h in start['historical_outputs'].items() if digest(Path(p).read_bytes()) != h]
changed_code = [p for p,h in start['preexisting_code_hashes'].items() if digest(Path(p).read_bytes()) != h]
assert not changed and not changed_code
verify()
write_new(ROOT / 'preservation-check.json', {'historical_files_checked': len(start['historical_outputs']),
    'changed_historical_files': changed, 'preexisting_code_files_checked': len(start['preexisting_code_hashes']),
    'changed_preexisting_code_files': changed_code, 'unrelated_local_chunk_v11_preserved': True,
    'original_V12_freeze_preserved': True})

sections = ['# 69305 thinking最终回答\n\nD正式实验答案为null：输出已经保存并可解析，但运行日志失败，缺少精确耗时和峰值内存。保留文本供质性诊断，不补写、不冒充完成。B-P正式完成。推理另存，不作依据。\n']
for n,o in names:
    label = '技术失败的保留生成文本，不是完成实验答案' if n.startswith('D') else '完成的最终答案'
    sections.append('\n## '+n+'：'+label+'\n\n```json\n'+(ROOT/'runs'/n/'parsed.json').read_text()+'\n```\n')
(ROOT/'final-answer-slots.md').write_text(''.join(sections),encoding='utf-8')
b = metas['B-P-thinking']; bo = read(ROOT/'lineage/B-P/run.json')
report = f'''V12：有限thinking开关开发对照，69305

决定：暂不采用thinking作为当前流程的默认配置。本轮有局部改善，但未得到更忠实、一致的完整法律回答。D的保留生成文本不再捏造法院认可associate资格、无同意认定或房东未反对，却仍误称没有转移定性和可采性认定。B-P开始保留下级法院以转租为由命令腾退，并区分没有目标最高法院最终处理；但g4称材料没有法院定性，g5又承认下级转租腾退，形成新的内部矛盾，仍漏掉下级允许依赖条款。不能用更保守的UNDETERMINED当作正确。

技术状态与执行偏差
仅两次新生成，D-thinking后B-P-thinking；网页0、重试0、额外模型预跑0。两份最终JSON都生成结束，没有截断或字段重复中止。D在输出保存、解析之后，运行元数据序列化失败：actual_parameters字典被后续加入不可JSON序列化的约束对象。D正式run_status为RUN_LOG_ERROR，answer为null；raw、推理、最终JSON、完整token IDs、约束轨迹已保留，精确耗时和峰值内存缺失。其文本审阅仅作技术失败输出的诊断，不作为完成实验答案。
遵照单次失败不取消尚未开始B的规则，在独立版本仅把日志参数字典改为副本；差异验证和源码冻结addendum在B调用前保存。没有改变模型、prompt、生成设置、约束算法、法律语义或任何D输出，没有重跑D。B-P为OK/stop，完整答案UNDETERMINED。加载模型两次是日志错误进程退出后的恢复，不是额外推理诊断；实际推理调用仍为2。

接口、冻结与预算
起点HEAD {start['head']}，分支{start['branch']}；已有V11未提交修改与local_chunk_v11.py保留。固定9B revision8b2b98c00a6b4d291155e4890773ca8f769aee53、MLX-VLM0.7.4、LMFE0.11.2，greedy、seed20261001、repetition_penalty1。两份prompt及schema逐字复用各自V11实际输入，B同一提议不修正、不含检查块。唯一聊天模板变化为空thinking预填段变成开放<think>换行。
本地9项直接检查全过、零跳过，无模型预跑。实际约束轨迹显示推理token未进入JSON解析或字段重复检测，</think>后解析器从generated_count0开始。跨流块分离的原始文本可精确还原。重复保护仍是同一JSON字符串内四次至少64字符的非重叠相同片段，不是必须相邻的连续重复。
每次max_tokens8192，总上下文32768；D输入8914、B输入10777，均完整不截断。框架原生thinking_budget4096在计数超过4096后强制换行和</think>，实际每份thinking4098、边界1。没有独立final预算参数，不声称已保留3072。最终分别766、760内容tokens，EOS各1，未耗尽总生成预算。总推理上限20分钟；B沿D开始时间的保守共同墙钟截止执行，连日志处理间隔也计入。

一次集中来源审阅
关键来源p0004.s002明确记载：下级Rent Controller及上诉机构认为条款was not inadmissible，租户entitled to rely，并以United被引入为sub-lessee命令腾退。没有最高法院最终处理不能被解释成没有任何法院定性。D仍称这两项法院认定不存在；B只恢复腾退认定且在另一项解释中否定其存在。
p0004.s003的佣金、同额租金和经销资格以及p0004.s004的S49解释均为租户律师论点；D-thinking不再把这些升级为法院采纳。B-P原来已经不这样升级，本轮不能重复认领为thinking收益。B-P旧reason要求特定同意trigger无需进一步同意例外的明示矛盾不再出现，但合同条款存在、适用于United及满足法定书面同意仍没有完整法律分析。
两份新答案都把1961租约日期直接用于转移阈值。该时间下界可能有依据，但须解释租约后引入United的事件连接，不能称原文明示转移日期。D reason明确说establishes date of transfer，是新增过度表述；B比旧B-P省略了随后引入的说明，证据解释变弱。B g1引用缺少许可条款续段；g2把absence与unknown合并到一个命题，目标含糊。没有新增转移方向或公司身份的明确颠倒，但抽象称谓和遗漏使对象依据不够具体。
给定法源仍没有完整解决associate资格、合同预先许可的法定效果与S49解释；这些属于真实法律覆盖缺口。已经展示的下级认定遗漏属于模型错误，二者不能混合。没有程序检查输入，不能归因为程序未实现。既不要求猜回被排除的历史结论，也不以JSON完成、来源ID有效或UNKNOWN减少判正确。此次仅审阅最终决定性依据，未逐句评分推理、未重标注事实、无网页复核；参考标记为模型辅助来源审阅，非人工金标准。

成本（生成ID总数包含边界和EOS，final内容单独列）
| 条件 | V11总生成 | 新thinking / final / 总生成 | 输入 | 耗时 | MLX峰值 |
| --- | --- | --- | --- | --- | --- |
| D | 583 | 4098 / 766 / 4866 | 8914 | 精确缺失；文件时间戳估计321.1秒（旧53.1秒） | 缺失（旧6.943569GB） |
| B-P | 689 | 4098 / 760 / 4860 | 10777 | {b['elapsed_seconds']:.1f}秒（旧{bo['elapsed_seconds']:.1f}秒） | {b['peak_mlx_memory_gb']:.6f}GB（旧{bo['peak_mlx_memory_gb']:.6f}GB） |
D总生成增加4283，最终内容较旧582增加184；精确时间/内存增量无法确认。B总生成增加4171，最终内容较旧688增加72；耗时增加{b['elapsed_seconds']-bo['elapsed_seconds']:.1f}秒，约{b['elapsed_seconds']/bo['elapsed_seconds']:.2f}倍；MLX峰值变化约{(b['peak_mlx_memory_gb']-bo['peak_mlx_memory_gb'])*1000:.2f}MB，未观察到明显增加。B进程RSS1.595GB（旧1.779GB），与MLX峰值含义不同，不能相加为机器总内存或解释成优化。运行顺序与进程不同，不构成内存性能基准。
两次总生成9726，其中推理8196、最终内容1526、边界及EOS4；输入19691。总推理精确值缺失，以D文件时间戳加B实测估计824.9秒，不冒充精确计时。比较是增加推理计算后的质量和成本，不是等计算预算的纯开关效应。

交付与停止
comparison-table.json/csv分别记录技术状态、来源问题、遗漏/新增矛盾、结论、token分段、耗时与内存。final-answers.json中D为null，保留的parsed路径明确标记诊断；B完整回答单独保存。final-source-review.json保存本次唯一来源审阅；restored-final-sources.json恢复每项引文；runs保留raw/推理/最终文本、IDs、mask和预算轨迹。freeze保留首次配置和B前日志addendum。
{len(start['historical_outputs'])}历史输出及{len(start['preexisting_code_hashes'])}原有源码文件原字节未变；V11和所有失败仍保留。此为单个旧案例的回顾性开发，继承后出法源、下级法院信息、非独立开发及研究者基础公式限制，不能估计准确率或thinking普遍能力。本轮到此结束，不调参、不补跑、不扩案、不提交、不推送。
'''
(ROOT/'report-zh.txt').write_text(report,encoding='utf-8')
print(json.dumps({'report':str(ROOT/'report-zh.txt'),'decision':review['decision'],'calls':2,'stop':True}))
