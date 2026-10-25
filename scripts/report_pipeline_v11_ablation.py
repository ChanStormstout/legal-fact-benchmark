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
report = f'''V11: intermediate-analysis ablation with repaired constraints, 69305

Decision: retain program traces for offline audit only. All six generations completed, but no condition produced a complete legally source-supported answer. A-clean text notes and B-P structured proposals reduced some D overstatement while missing decisive lower-court findings. Adding the entire check block to B-C introduced source-contradicting admissibility and attribution errors. Under this configuration, do not continue adding that block to final input. This endorses neither D nor permanent rejection of lightweight structure. There is no single-case accuracy ranking, statistical claim, or generalization inference.

Version and execution
Starting HEAD/review base {start['head']}, branch {start['branch']}. Only untracked local_chunk_v11.py existed initially; it was unchanged/excluded from publication. The experiment is separate. Code, actual V8 intermediate prompts/schema, final_v9 templates/full synthetic examples, case/legal hashes, call order, and stop rules were frozen before generation.

Fixed Qwen3.5-9B-4bit revision8b2b98c00a6b4d291155e4890773ca8f769aee53, MLX-VLM0.7.4, LMFE0.11.2, greedy, seed20261001, repetition_penalty1, thinking off, actual max_tokens3072, context32768. Five repair regressions passed without skips; real-tokenizer fixtures and old-token replay preceded generation. The verified FIXED entry applied masks on every call and preserved parameters, IDs, raw text, finish reasons, and parses without format/semantic additions.

runtime-differences.json/runtime-entry-diff.txt document restored compound-quote tokens and added runtime audit relative to V8. Sampling, budgets, and stop thresholds are unchanged. V9 additionally monitors explanation, absent from both first-stage schemas, so intermediate stopping is unchanged. The guard detects four nonoverlapping occurrences of an identical 64-character fragment within one JSON string, not necessarily consecutive and never across fields.

Order: D, A-notes, A-clean, B-proposal, B-P, B-C. All six were OK/stop, with zero browser calls/retries/extra diagnostic calls. Inference {result['inference_seconds']:.1f} seconds, round wall time {result['round_wall_seconds']:.1f}, both below30 minutes; loading separately {result['model_load_seconds_excluded_from_inference']:.1f}. Total input {total_in}, output IDs {total_out}, including end tokens. No source truncation, repetition stop, format repair, or resource failure.

| Condition | Technical status | Final conclusion | Final input/output tokens | Final seconds | Including intermediate seconds |
| --- | --- | --- | --- | --- | --- |
{table}

D uses one call, not an equal-call-budget comparator. A-clean/B use two stages; B's first stage is physically shared once, so method ledgers must not be added as if separately billed. B-C adds {metas['B-C']['prompt_tokens'] - metas['B-P']['prompt_tokens']} input tokens over B-P. All36 combinations and48 independent links remain; compact display reuses the original reversible conversion. Equal call counts do not imply equal cost.

Single consolidated source review: shared evidence
Allowed p0004.s002 states: “The Rent Controller, as well as, the appellate authority held that the afore-mentioned term of the lease was not inadmissible and the appellant was enti- tled to rely upon the same, but ordered eviction on the ground that M/s. United Automobiles was inducted in the premises as a sub-lessee.” Preserve lower-court reliance/sub-lessee findings without promoting them to excluded Supreme Court endorsement. “United Automobiles can not be assumed…” continues the landlord's position from p0004.s001, not a court rejection of associate status.

The1961 lease/associate proviso appear at p0003.s003/s004. Commission/equal-rent/agency arguments at p0004.s003 and collateral-purpose arguments at s004 belong to tenant counsel. The legal package supplies S14(1)(b) date/transfer/consent basics but not full conditional-clause/S49 interpretation. Unknowns remain valid; saying no court findings exist does not.

What happened in the four answers
D opposes eviction based on court acceptance of United as associate and a valid statutory exception. The former is counsel's argument; the latter exceeds supplied law. D also converts absent consent documents into a court finding of no consent and adds lack of landlord objection. A definite answer is not more useful when its decisive basis fails.

A-clean becomes indeterminate and separates allegations from established facts, but claims no court/lower decision resolved transfer mode, omitting the sub-lessee finding. Ground2's point says the tenant raised a defense, which is sourced, yet labels it UNRESOLVED, changing the assessed proposition. A sourced motive-irrelevance explanation becomes a mistaken vacuously-satisfied condition. Text notes reduce overstatement but propagate an invented information gap.

B-P preserves the clause and leaves associate eligibility/specific consent unresolved, without invented court endorsement or inferring absent consent from an unseen document. Its1961 lease/subsequent-introduction lower bound is an explainable inference, not an explicit transfer date. It still omits both lower-court findings. Its reason says no further consent is needed while requiring specific consent to trigger the exception, confusing prior contractual and additional transaction permission. This is local improvement, not a fully correct answer.

B-C uses the identical B proposal but, after receiving the check block, says courts held the clause inadmissible, reversing “was not inadmissible.” It recasts landlord objections as express judicial rejection, contradicting UNRESOLVED labels. Despite acknowledging the1961 lease, it treats the1952 threshold as unverifiable without an exact introduction date, ignoring the existing lower bound. Its reason also calls United the appellant. It fails to cure B-P's decisive omissions and introduces serious errors.

Intermediate material and program boundaries
Old/new intermediate texts and diffs are saved for diagnosis, not gold or complete-method comparison. New A still claims lower-court findings absent; A-clean repeats that. New B mainly cites p0003, leaves three transfer modes unresolved, omits p0004.s002, and incorrectly says the1961 lease predates1952. Only these final-answer-relevant clues were inspected, without field-by-field relabeling.

All36 program combinations remain unresolved. Role phrases fail exact-source-mention checks, leaving links unconfirmed; local PROPOSED_SUPPORT is not semantic certification. The program never says the clause is inadmissible; B-C's explanation is a final-model error. B-P/B-C isolates the net effect of the whole check block, not input length, perceived authority, or attention as separate causes.

Separate real gaps from model errors
Clause/sub-lessee findings are present: omission/reversal is not missing case facts. Full associate eligibility, statutory effect of prior contractual permission, and complete S49 rules remain genuine factual/legal scope gaps. Missing program implementation of those interpretations is a program limit. All four final answers can reread originals, so errors cannot all be attributed to extraction; excluded historical outcomes should not be guessed.

Delivery and stopping
See final-answer-slots.md, final-answers.json, and runs/parsed.json for all four answers. comparison-table.json/csv separate technical status, decisive-source correctness, omissions, contradictions, legal gaps, and conclusions. final-source-review.json is model-assisted source review, not human gold. Both new intermediates, complete/compact checks, restored sources, actual prompt/schema/raw/token records, costs, hashes, and stop records are saved.

This repeatedly exposed case uses later authorities, lower-court information, and an existing researcher-supplied target-source formula; it is retrospective development, not independent prediction. All {len(start['historical_outputs'])} historical files and {len(start['code_hashes'])} original code files were byte-identical. Local state/review updates did not commit or push. Preserving accurate lower-court findings and distinguishing open legal interpretation is only a proposed next focus. No further changes, reruns, or V12 occurred in this round.
'''
(ROOT / 'report-zh.txt').write_text(report, encoding='utf-8')
print(json.dumps({'complete_final_answers': 4, 'calls': 6, 'decision': review['decision'],
                  'historical_files_preserved': len(start['historical_outputs'])}, indent=2))
