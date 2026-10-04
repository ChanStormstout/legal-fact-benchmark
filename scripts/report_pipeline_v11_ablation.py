"""One decisive-source review and delivery ledger; never starts model generation."""
import csv
import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import digest, write_new
from legal_bench.rules_verdict_v1.final_v9 import prompt, expand_display
from scripts.pipeline_v11_ablation import verify

ROOT = Path('outputs/rules-verdict-v11-intermediate-ablation')
read = lambda p: json.loads(p.read_text())
result = read(ROOT / 'results.json')
assert result['all_six_complete'], 'Failure requires a distinct incomplete-round report, not this review'
frozen = verify()
source = read(ROOT / 'sources/69305.json')
law = read(ROOT / 'prepared/69305/law-package.json')
case_map = {x['id']: x['text'] for x in source['segments']}
law_map = {x['id']: x['text'] for x in law['law_segments']}
names = ['D', 'A-clean', 'B-P', 'B-C']
metas = {r['slot']: r for r in result['rows']}
answers = {n: read(ROOT / 'runs' / n / 'parsed.json') for n in names}
bp = read(ROOT / 'prepared/B-P/intermediate.json')
bc = read(ROOT / 'prepared/B-C/intermediate.json')
assert bp['proposal'] == bc['proposal'] == read(ROOT / 'intermediates/B-new.json')
assert set(bp) == {'proposal'} and set(bc) == {'proposal', 'program_checks'}
assert expand_display(bc['program_checks']) == read(ROOT / 'checks/compact-v8.json')
for n in names:
    assert (ROOT / 'runs' / n / 'prompt.txt').read_text() == prompt(source, law, read(ROOT / 'prepared' / n / 'intermediate.json'))
    assert read(ROOT / 'runs' / n / 'schema.json') == read(ROOT / 'prepared/final-schema.json')
for n, m in metas.items():
    assert m['run_status'] == 'OK' and m['constraint_mode'] == 'FIXED'
    assert m['effective_max_tokens'] == 3072 and m['actual_parameters'] == frozen['actual_parameters']
    assert m['thinking_disabled_template_verified'] and not m['thinking_output_present']
    assert m['schema_mask_calls'] > 0 and not m['format_repairs']
    assert len(read(ROOT / 'runs' / n / 'token-ids.json')) == m['output_tokens']
    assert m['prompt_tokens'] + 3072 <= 32768
write_new(ROOT / 'protocol-audit.json', {
    'all_six_fixed_mask_calls_complete': True, 'same_final_template_examples_schema_source_law': True,
    'B_P_B_C_share_exact_proposal': True, 'existing_check_display_exact_roundtrip': True,
    'no_format_or_semantic_repairs': True, 'all_effective_parameters_frozen': True,
    'all_full_inputs_within_budget': True, 'web_calls': 0, 'retries': 0,
    'stage1_actual_prompt_schema_exact_V8': all(
        (ROOT / 'runs' / name / file).read_bytes() == (ROOT / 'prepared' / (method + '-stage1') / file).read_bytes()
        for name, method in [('A-notes', 'A'), ('B-proposal', 'B')] for file in ['prompt.txt', 'schema.json']),
    'actual_mask_sha256': frozen['mask_sha256'], 'live_running_source_hashes': frozen['live_code']})

restored = {}
for n, answer in answers.items():
    restored[n] = [{'ground': i + 1, 'point': g['point'],
                    'case_sources': [{'id': ref, 'text': case_map[ref]} for ref in g['case_refs']],
                    'law_sources': [{'id': ref, 'text': law_map[ref]} for ref in g['law_refs']],
                    'address_validity_not_semantic_verification': True}
                   for i, g in enumerate(answer['grounds'])]
write_new(ROOT / 'restored-final-sources.json', restored)
write_new(ROOT / 'final-answers.json', answers)

review = {
    'review_type': 'ONE_CONCENTRATED_DECISIVE_SOURCE_REVIEW_AFTER_ALL_GENERATION',
    'reference_status': 'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
    'historical_withheld_outcome_not_expected_label': True,
    'new_full_intermediate_annotations': 0, 'review_agents': 0, 'web_calls': 0,
    'anchors': [
        {'id': 'S1', 'refs': ['p0003.s003', 'p0003.s004'],
         'finding': '租约1961年成立。条款一般禁止未经书面许可转移，但有向associate concerns转让或交出占有的附条件文字。条款存在不等于本次交易已满足法定书面同意要求。'},
        {'id': 'S2', 'refs': ['p0004.s001', 'p0004.s002'], 'quote': case_map['p0004.s002'],
         'finding': '前句“不能假定为associate”延续房东立场；随后明确记载Rent Controller和上诉机构允许租户依赖条款，并以United被引入为sub-lessee命令腾退。这是可见下级认定，不是被排除的目标最高法院最终认可。'},
        {'id': 'S3', 'refs': ['p0004.s003', 'p0004.s004'],
         'finding': '代理、佣金、相同租金和collateral purpose均为租户或其律师论点；没有在允许片段中变成法院采纳的associate资格结论。'},
        {'id': 'L1', 'refs': ['LAW:1134266:p0004.s004', 'LAW:1134266:p0004.s005', 'LAW:1134266:p0004.s006'],
         'finding': '提供历史S14(1)(b)日期、转移方式及书面同意基础条件，及动机无关解释；不提供解决本案S49/associate proviso效力的完整规则。动机无关不是待满足的积极条件。'}],
    'checks': [
        {'condition': 'D', 'grounds': [1], 'classification': 'UNSUPPORTED_STATUTORY_EXCEPTION',
         'finding': '将租约文字直接定为有效法定例外；“accepted as a valid collateral term”超出可见下级允许依赖这一认定。未引用实际下级认定片段p0004.s002。'},
        {'condition': 'D', 'grounds': [2], 'classification': 'PARTY_SUBMISSION_PROMOTED_TO_COURT_FINDING',
         'finding': '称法院接受佣金等主张并认定United为associate，p0004.s003仅记律师论点。决定性身份基础不受来源支持。'},
        {'condition': 'D', 'grounds': [3], 'classification': 'ABSENCE_OF_DOCUMENT_AS_NEGATIVE_FINDING',
         'finding': '把未展示同意文件升级为法院认定没有书面同意；来源只有房东指控和条款/抗辩。理由还称房东未反对这个类别，原文显示房东确实反对适用。'},
        {'condition': 'A-clean', 'grounds': [1], 'classification': 'SUPPORTED_ALLEGATION_NOT_ESTABLISHED_TRANSFER',
         'finding': '正确区分指控存在与转租事实证明；没有把租户的associate主张升级为法院认可。'},
        {'condition': 'A-clean', 'grounds': [2, 3], 'classification': 'AVAILABLE_LOWER_COURT_FINDING_OMITTED',
         'finding': '称材料没有下级决定或法院认定解决转移方式，遗漏p0004.s002的sub-lessee认定。associate资格解释仍未决不抹掉已给出的下级结论。'},
        {'condition': 'A-clean', 'grounds': [2], 'classification': 'POINT_ASSESSMENT_TARGET_MISMATCH',
         'finding': 'point是“租户提出某抗辩”，来源明确支持其提出抗辩，却标UNRESOLVED；实际在评价抗辩内容是否真实，而不是point所写的行为。'},
        {'condition': 'A-clean', 'grounds': [5], 'classification': 'IRRELEVANT_FACTOR_AS_VACUOUS_CONDITION',
         'finding': '动机无关命题有来源，但“vacuously satisfied”把不参与要件判断的因素误写为已满足条件。'},
        {'condition': 'B-P', 'grounds': [1, 2, 4], 'classification': 'PARTIAL_SOURCE_GROUNDED_CAUTION',
         'finding': '保留条款文字与associate资格未证实的区别；没有从未展示额外同意文件推断同意不存在。相比D减少了两项无依据的确定判断，不等于完整答案正确。'},
        {'condition': 'B-P', 'grounds': [3], 'classification': 'EXPLICIT_CHRONOLOGY_INFERENCE_NOT_EXACT_EVENT_DATE',
         'finding': '以1961年租约及其后租户引入United作日期下界推断，具有材料依据，但属于序列推断，并非明确转移日期或法院日期认定；精确日期缺失本身不足以否定1952阈值。'},
        {'condition': 'B-P', 'grounds': [1, 2, 4], 'classification': 'OMITTED_LOWER_FINDING_AND_CONSENT_LOGIC_GAP',
         'finding': '遗漏可见下级允许依赖条款及sub-lessee认定；reason又要求特别书面同意来trigger“无需进一步同意”的例外，混淆条款效力与额外交易许可。提供的法源不足以确定二者法律关系。'},
        {'condition': 'B-C', 'grounds': [1], 'classification': 'SOURCE_CONTRADICTED_ADMISSIBILITY',
         'finding': '称法院认定条款不可采，直接反于p0004.s002的“was not inadmissible”及“entitled to rely”。又把条款文字是否存在与法律效果未决混成同一assessment。'},
        {'condition': 'B-C', 'grounds': [2], 'classification': 'LANDLORD_OBJECTION_PROMOTED_TO_COURT_REJECTION',
         'finding': '称法院明确否定associate资格；该语句其实是前段延续的房东立场。UNRESOLVED标签与“法院明确否定”的解释也不一致。'},
        {'condition': 'B-C', 'grounds': [3], 'classification': 'EXACT_DATE_GAP_OVERRIDES_AVAILABLE_LOWER_BOUND',
         'finding': '承认1961年租约，却称缺少精确引入日期使1952阈值无法核实；没有处理B-P已使用的事件先后下界。不能据此判定原文一定缺少决定性日期。'},
        {'condition': 'B-C', 'grounds': [4], 'classification': 'SPECIFIC_CONSENT_UNRESOLVED_BUT_RULE_SCOPE_OPEN',
         'finding': '没有把缺少专门交易许可文件直接判成否定，这部分较谨慎；仍未解释租约内预先许可的法律效力。'},
        {'condition': 'B-C', 'grounds': [], 'classification': 'REASON_WRONG_OBJECT_AND_COURT_STATUS',
         'finding': 'reason把需判断是否associate的United写成appellant，并称法院没有解决转租适用，遗漏已给出的下级腾退认定。'}],
    'comparisons': {
        'D_to_A_clean': '文本笔记后不再确定认可associate资格或判请求被击败，但继承“没有下级事实认定”的错误；谨慎标签不构成来源正确的完整回答。D只用一次调用。',
        'D_to_B_P': '结构化提议后不再捏造associate司法认可，也不把未见同意等同无同意；仍有下级认定遗漏及同意逻辑错误。A-clean也出现相同谨慎变化，未证明结构格式独有收益。',
        'B_P_to_B_C': '共用同一提议、同一最终模板，加入整个检查块后新增条款不可采与法院否定associate两项直接来源错误，并增加不必要的日期未知。只能归于整个块的净影响，不能拆分长度、权威感或注意力原因。',
        'shared': '四份答案均未准确保留下级“条款可依赖＋sub-lessee”两项决定性认定及其层级；材料缺少最终associate/S49解释，但不是完全没有法院认定。程序范围不足不是来源事实不存在。'},
    'intermediate_trace_limited_to_final_decisive_issues': {
        'A': '新A的coverage_limits仍声称没有下级sub-tenant finding，A-clean复述该缺失；这是文本相似的传播线索，不证明注意力机制。',
        'B': '新B把同一引入事件列成三种转移且均mode未决，引用主要p0003而遗漏p0004.s002；coverage错误称1961租约早于1952。程序36个组合未决是提议/连接不足，不是来源否定。',
        'program': '所有角色短语未通过exact mention局部检查，连接均未决；可用于离线识别提议与接口的限制，没有验证法院观点或法律效力。检查视图从未断言法院认定条款不可采，B-C此断言仍是最终模型错误。',
        'no_full_field_annotation': True},
    'decision': 'ONLY_RETAIN_PROGRAM_FOR_OFFLINE_AUDIT',
    'decision_zh': '仅保留程序离线审计',
    'decision_basis': '本案加入整个检查块没有带来可核查完整答案改善，却新增严重来源与归属错误，因此当前不继续将该检查块作为最终判断输入。A-clean/B-P有减少D过度判断的局部信号，但都未形成可靠完整回答；这不是永久排除结构化，也不是判定D可靠。',
    'next_investment_recommendation_only': '先解决最终回答如何准确保留既有下级认定，并与未决的合同/法源解释区分。本轮不修改提示、不重跑、不启动下一轮。',
    'single_case_accuracy_ranking': False, 'generalization_claim': False}
write_new(ROOT / 'final-source-review.json', review)
write_new(ROOT / 'decision.json', {k: review[k] for k in ['decision', 'decision_zh', 'decision_basis', 'next_investment_recommendation_only']})

summaries = {
    'D': ['关键法院采纳和同意否定不受来源支持', '遗漏可见下级认定与其层级', '无直接形式矛盾；reason新增房东不反对说法', '将附条件条款当确定法定例外', '反对腾退的决定性依据不成立'],
    'A-clean': ['指控归属与基础法条部分正确；误称下级转移认定缺失', '遗漏条款可依赖及sub-lessee认定', '抗辩提出事实的point与UNRESOLVED不一致；动机无关误作已满足条件', '认识到条款与法定同意解释未决，但混成事实全部缺失', '无法判断标签可能合理，决定性理由有误'],
    'B-P': ['条款文字、associate未证实及同意未知较谨慎；时间下界属推断', '遗漏下级条款处理和sub-lessee认定', '无需进一步同意的条款与reason要求同意trigger例外相冲突', '预先合同许可的法定效果未解决', '无法判断可能合理；局部纠正D，不是完整正确答案'],
    'B-C': ['反向写成条款不可采；房东反对被写成法院否定', '遗漏真实下级认定；不处理可用日期下界', 'UNRESOLVED与明确法院否定冲突；reason对象写错', '用不采纳条款的虚构认定代替法律解释缺口', '无法判断标签相同，依据较B-P新增严重错误']}
rows = []
for n in names:
    m = metas[n]
    stage = metas['A-notes'] if n == 'A-clean' else metas['B-proposal'] if n in ['B-P', 'B-C'] else None
    s = summaries[n]
    rows.append({'case': '69305', 'condition': n, 'technical_status': m['run_status'],
                 'final_outcome': answers[n]['outcome'], 'decisive_source_correctness': s[0],
                 'omissions': s[1], 'internal_contradictions': s[2], 'law_gaps': s[3], 'conclusion_assessment': s[4],
                 'final_input_tokens': m['prompt_tokens'], 'final_output_token_ids': m['output_tokens'],
                 'final_seconds': round(m['elapsed_seconds'], 3), 'final_peak_mlx_gb': round(m['peak_mlx_memory_gb'], 3),
                 'logical_method_calls': 1 + bool(stage),
                 'logical_method_total_input_tokens': m['prompt_tokens'] + (stage['prompt_tokens'] if stage else 0),
                 'logical_method_total_output_tokens': m['output_tokens'] + (stage['output_tokens'] if stage else 0),
                 'logical_method_seconds': round(m['elapsed_seconds'] + (stage['elapsed_seconds'] if stage else 0), 3),
                 'cost_note': 'B第一阶段实际只运行一次；两种逻辑方法账本各计入共同阶段，不能再相加作为本轮总成本' if stage and n.startswith('B') else 'D是一次调用基线，非同调用预算',
                 'review_status': 'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD'})
write_new(ROOT / 'comparison-table.json', rows)
with (ROOT / 'comparison-table.csv').open('x', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)

diagnostics = {}
for method, name in [('A', 'A-notes'), ('B', 'B-proposal')]:
    old = read(ROOT / 'lineage' / method / 'v8-intermediate.json')
    new = read(ROOT / 'intermediates' / (method + '-new.json'))
    diff = ''.join(difflib.unified_diff(json.dumps(old, ensure_ascii=False, indent=2).splitlines(True),
                                      json.dumps(new, ensure_ascii=False, indent=2).splitlines(True),
                                      fromfile='V8-' + method, tofile='V11-' + method))
    (ROOT / 'lineage' / method / 'old-new-output.diff.txt').write_text(diff)
    diagnostics[method] = {'identical_output': old == new, 'old_hash': digest(old), 'new_hash': digest(new),
                           'old_array_counts': {k: len(v) for k, v in old.items() if isinstance(v, list)},
                           'new_array_counts': {k: len(v) for k, v in new.items() if isinstance(v, list)},
                           'prompt_schema_sampling_unchanged': True, 'new_intermediate_gold': False,
                           'comparison_is_diagnostic_not_complete_method_evaluation': True}
write_new(ROOT / 'intermediate-differences.json', diagnostics)
start = read(ROOT / 'start-audit.json')
changed = [p for p, h in start['historical_outputs'].items() if digest(Path(p).read_bytes()) != h]
changed_code = [p for p, h in start['code_hashes'].items() if digest(Path(p).read_bytes()) != h]
assert not changed and not changed_code, (changed, changed_code)
write_new(ROOT / 'preservation-check.json', {'historical_files_checked': len(start['historical_outputs']),
          'changed_historical_files': changed, 'preexisting_code_files_checked': len(start['code_hashes']),
          'changed_preexisting_code_files': changed_code, 'unrelated_local_chunk_v11_preserved': True})
verify()

parts = ['# 69305四个最终条件\n\n原始完成输出逐字保存在各runs目录；以下JSON直接来自parsed，未补写或修正。来源审阅为模型辅助开发评价，不是人工gold。\n']
for n in names:
    parts.append('\n## ' + n + '\n\n```json\n' + (ROOT / 'runs' / n / 'parsed.json').read_text() + '\n```\n')
(ROOT / 'final-answer-slots.md').write_text(''.join(parts))
total_in = sum(m['prompt_tokens'] for m in metas.values())
total_out = sum(m['output_tokens'] for m in metas.values())
write_new(ROOT / 'cost-ledger.json', {'actual_calls': 6, 'input_tokens': total_in, 'output_token_ids': total_out,
          'inference_seconds': result['inference_seconds'], 'round_wall_seconds': result['round_wall_seconds'],
          'model_load_seconds': result['model_load_seconds_excluded_from_inference'],
          'B_stage_shared_once': True, 'program_check_display_extra_final_input_tokens': metas['B-C']['prompt_tokens'] - metas['B-P']['prompt_tokens'],
          'all_token_id_counts_include_end_token': True, 'timings_not_simultaneous_performance_benchmark': True})
table = '\n'.join(f"| {r['condition']} | {r['technical_status']} | {r['final_outcome']} | {r['final_input_tokens']} / {r['final_output_token_ids']} | {r['final_seconds']} | {r['logical_method_seconds']} |" for r in rows)
report = f'''V11：修复约束下的中间分析消融，69305

结论与投入决定：仅保留程序离线审计。六次生成全部完成，但没有一个条件得到来源充分支持的完整法律回答。A-clean文本笔记和B-P结构化提议都减少了D的部分过度判断，仍遗漏决定性下级认定；B-C加入整个检查块后新增了直接反于原文的可采性判断与观点归属错误。本配置下不继续将该检查块加入最终判断输入，保留轨迹用于离线审计。这不等于认可D，也不等于永久排除轻量结构化；没有进行单案准确率排名或统计、泛化推断。

实际版本与执行
起点HEAD与审查基点均为{start['head']}，分支{start['branch']}。开始前只有未追踪local_chunk_v11.py，未修改，且排除发布清单。新实验独立保存；首次生成前冻结源码、原V8实际中间prompt/schema、final_v9模板及完整虚构示例、输入与法律包哈希、调用顺序和停止规则。
固定Qwen3.5-9B-4bit revision8b2b98c00a6b4d291155e4890773ca8f769aee53、MLX-VLM0.7.4、LMFE0.11.2、greedy、seed20261001、repetition_penalty1、thinking off，每次实际max_tokens3072，总上下文32768。修复回归5项全部通过、零跳过；真实tokenizer fixture及旧实际token回放完成，之后才生成。使用已验证FIXED入口；每次mask均生效，实际参数、token IDs、raw、finish_reason及解析结果完整保存，零格式或语义补写。
与V8运行入口的差异见runtime-differences.json和runtime-entry-diff.txt：约束补回合法复合引号token，新增运行审计；采样、预算和止损阈值不变。v9保护额外监测explanation，该字段不在两份第一阶段Schema内，不改变中间生成止损规则。保护检测同一JSON字符串内非重叠64字符片段出现四次，不要求四次紧邻；不跨字段。
顺序为D、A-notes、A-clean、B-proposal、B-P、B-C，六次均OK/stop，网页0、重试0、额外诊断模型调用0。推理{result['inference_seconds']:.1f}秒，整轮{result['round_wall_seconds']:.1f}秒，均小于30分钟；模型加载另计{result['model_load_seconds_excluded_from_inference']:.1f}秒。实际总输入{total_in}、输出token IDs{total_out}，输出口径含结束token。没有截断来源、重复中止、格式修补或资源失败。

| 条件 | 技术状态 | 最终结论 | 最终输入/输出tokens | 最终秒 | 含中间阶段秒 |
| --- | --- | --- | --- | --- | --- |
{table}

D只用一次调用，不是等调用预算基线。A-clean和B路径各需两阶段，B第一阶段实际共用一次；方法账本不能重复相加为整轮成本。B-C比B-P多{metas['B-C']['prompt_tokens'] - metas['B-P']['prompt_tokens']}输入tokens。完整36组合及48项独立连接全部保留，检查展示只复用原转换并核验可逆。成本不因调用次数相同而相同。

一次集中来源审阅：共同依据
允许片段p0004.s002明确记载：“The Rent Controller, as well as, the appellate authority held that the afore-mentioned term of the lease was not inadmissible and the appellant was enti- tled to rely upon the same, but ordered eviction on the ground that M/s. United Automobiles was inducted in the premises as a sub-lessee.” 必须保留下级允许依赖条款及sub-lessee认定，同时不能升级成被排除的最高法院最终认可。同段开头“United Automobiles can not be assumed…”延续p0004.s001中房东立场，不是法院否定associate的认定。
租约1961年成立及associate proviso文字在p0003.s003/s004；租户关于佣金、相同租金、代理身份的论点在p0004.s003，collateral purpose论点在s004。法律包给出S14(1)(b)日期、转移和书面同意基础条件，没有解决该附条件条款与S49的完整适用解释。未知可保留，但不能说材料完全没有法院认定。

四种回答具体发生了什么
D反对腾退，核心依据是“法院接受United为associate”及“条款构成有效法定例外”。前者只来自租户律师主张，后者超出给定法源；D还把未展示同意文件当成法院认定无同意，reason加入房东未反对的说法。决定性基础不成立，不能因为它给出确定结论就认定更有用。
A-clean改为无法判断，并正确区分指控与事实成立；但声称没有法院或下级决定解决转移方式，遗漏可见sub-lessee认定。第二行point说“租户提出抗辩”，实际已被原文支持，却标UNRESOLVED，评价对象发生变化。动机无关解释有法源，但被错误写成vacuously satisfied条件。文本笔记减少过度判断，同时传播了虚构信息缺口。
B-P保留条款文字，将associate资格与专门同意保留未决，没有捏造法院认可，也没有从未见文件推出同意不存在。其日期判断使用1961租约及后续引入的时间下界，属于可解释推断而非具体日期认定。但仍漏掉两项下级认定；reason一面说无需进一步同意，一面要求特别同意来trigger该例外，混淆了合同预先许可与本次额外许可。它提供局部改善信号，没有构成完整正确答案。
B-C沿用完全相同B提议，新增检查块后称法院认为条款不可采，直接反于“was not inadmissible”；又将房东关于associate的异议写成法院明确否定，UNRESOLVED标签与解释冲突。它承认1961租约却因缺少精确引入日期把1952阈值判为无法核实，未处理已有时间下界；reason还把需判断是否associate的United写成appellant。它没有消除B-P的决定性遗漏，并新增严重错误。

中间材料和程序作用的边界
新旧中间输出不同，完整旧/新文件及文本diff已保存，仅用于诊断，不是gold或完整方法比较。新A仍写下级事实认定缺失，A-clean复述这个缺失。新B主要引用p0003，列举同一引入事件的三种模式均未决，未保留p0004.s002；coverage还误称1961租约早于1952。只查看这些影响最终答案的线索，没有逐字段重标注。
程序36组合均未决，角色短语没有通过原文精确提及检查，连接不能确认；局部PROPOSED_SUPPORT不是语义认证。程序没有声称法院认定条款不可采，B-C的错误属于最终模型给出的错误解释。B-P/B-C比较只说明提供整个检查块的净影响；不能据此分离输入长度、权威感或注意力原因。

材料真实缺口与模型错误须分开
条款和sub-lessee的下级认定已在输入内，遗漏或反向理解不是案件事实缺失。associate资格的完整解释、合同预先许可是否满足法定要求及S49完整规则未提供，属于事实/法律范围仍未决。程序未实现这些法律解释是程序覆盖限制。四份最终答案均可回读原文，不能把最终错误全部归因于抽取，更不能要求它们猜回被排除的目标历史裁判。

交付与停止
完整四份答案见final-answer-slots.md、final-answers.json及各runs/parsed.json；逐条件comparison-table.json/csv分开技术状态、决定性来源正确性、遗漏、内部矛盾、法律缺口与结论。final-source-review.json保存本次模型辅助来源审阅，不是人工gold。两份新中间结果、完整和紧凑检查、来源恢复、全部实际prompt/schema/raw/token记录、成本、版本哈希及停止记录均保留。
本案反复参与开发，使用后出法源、下级法院信息及既有目标来源公式限制，仍是回顾性开发，不是独立预测。{len(start['historical_outputs'])}个历史文件及{len(start['code_hashes'])}个原有代码文件核验原字节不变。新轮更新本地状态和审阅包，不提交、不推送。下一步投入建议仅为保留准确下级认定并区分法律解释未决；未实施新修改、补跑或V12。本轮结束。
'''
(ROOT / 'report-zh.txt').write_text(report, encoding='utf-8')
print(json.dumps({'complete_final_answers': 4, 'calls': 6, 'decision': review['decision'],
                  'historical_files_preserved': len(start['historical_outputs'])}, indent=2))
