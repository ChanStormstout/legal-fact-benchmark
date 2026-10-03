"""One concentrated decisive-source review of the recovered 69305 final pair."""
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import digest, write_new

ROOT = Path('outputs/rules-verdict-v10-constraint-recovery')
read = lambda p: json.loads(p.read_text())
results = read(ROOT / 'results.json')
source = read(ROOT / 'sources/69305.json')
law = read(ROOT / 'prepared/69305/law-package.json')
case_map = {x['id']: x['text'] for x in source['segments']}
law_map = {x['id']: x['text'] for x in law['law_segments']}
answers = {}
restored = {}
rows = []
for method in ['A', 'B']:
    meta = read(ROOT / 'runs' / method / 'run.json')
    intermediate_meta_path = Path('outputs/rules-verdict-v8-paired/runs') / method / 'stage1/run.json'
    stage = read(intermediate_meta_path)
    if meta['run_status'] == 'OK':
        answer = answers[method] = read(ROOT / 'runs' / method / 'parsed.json')
        restored[method] = []
        for index, ground in enumerate(answer['grounds']):
            restored[method].append({
                'ground': index + 1, 'point': ground['point'],
                'case_sources': [{'id': ref, 'text': case_map[ref]} for ref in ground['case_refs']],
                'law_sources': [{'id': ref, 'text': law_map[ref]} for ref in ground['law_refs']],
                'address_validity_not_semantic_support': True})
    else:
        answers[method] = None
    rows.append({
        'case': '69305', 'method': method, 'run_status': meta['run_status'],
        'outcome': answers[method]['outcome'] if answers[method] else None,
        'final_generation_role': 'NEW' if method == 'A' else 'REUSED_COMPATIBLE_FIXED_CALL',
        'final_input_tokens': meta['prompt_tokens'], 'final_output_token_ids': meta['output_tokens'],
        'final_seconds': round(meta['elapsed_seconds'], 3),
        'intermediate_origin': str(intermediate_meta_path),
        'intermediate_input_tokens': stage['prompt_tokens'],
        'intermediate_output_tokens': stage['output_tokens'],
        'intermediate_seconds': round(stage['elapsed_seconds'], 3),
        'recorded_two_stage_seconds': round(stage['elapsed_seconds'] + meta['elapsed_seconds'], 3),
        'cost_note': 'Historical intermediate plus recovered final ledger, not simultaneous benchmark',
        'source_review': 'DECISIVE_ERRORS_REMAIN_NO_LEGAL_ACCURACY_SCORE'})
write_new(ROOT / 'restored-final-sources.json', restored)
write_new(ROOT / 'comparison-table.json', rows)
with (ROOT / 'comparison-table.csv').open('x') as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
assert all(answers.values()), 'No complete pairing: report failure instead of legal comparison'

review = {
    'review_type': 'ONE_CONCENTRATED_LOCAL_DECISIVE_SOURCE_REVIEW',
    'label': 'MODEL_ASSISTED_DEVELOPMENT_REVIEW_NOT_HUMAN_GOLD',
    'historical_final_judgment_not_used_as_expected_label': True,
    'source_findings': [
        {'id': 'S1', 'refs': ['p0003.s003', 'p0003.s004'],
         'finding': 'Conditional lease proviso exists: assignment or parting with possession to associate concerns without further consent. Its statutory effect for this occupant is not settled just by quoting it.'},
        {'id': 'S2', 'refs': ['p0004.s002'], 'quote': case_map['p0004.s002'],
         'finding': 'Allowed input explicitly reports the Rent Controller and appellate authority accepting reliance on the clause and ordering eviction on induction as sub-lessee. These are lower-court findings, not a withheld Supreme Court final endorsement.'},
        {'id': 'S3', 'refs': ['p0004.s001', 'p0004.s003', 'p0004.s004'],
         'finding': 'Authorized-dealer/associate status and collateral admissibility arguments remain party submissions; detailed final resolution of associate qualification is absent in the allowed material.'},
        {'id': 'S4', 'refs': ['LAW:1134266:p0004.s004', 'LAW:1134266:p0004.s005'],
         'finding': 'Law package supplies historical Section14(1)(b) transfer alternatives and written-consent requirement. It does not supply a source rule resolving Section49 collateral use or associate-concern interpretation for this tenant.'}],
    'decisive_checks': [
        {'method': 'A', 'ground': 1, 'finding': 'Allegation attributed to landlord correctly; SUPPORTED is proper for existence of allegation, not truth of every eviction element.'},
        {'method': 'A', 'ground': 2, 'reason_affected': True,
         'classification': 'AVAILABLE_LOWER_COURT_FINDING_MISREPORTED_AS_ABSENT',
         'source': 'p0004.s002',
         'finding': 'Claim that no judicial determination on admissibility is provided conflicts with explicit lower-court treatment. Legal completeness at the appeal stage can still be uncertain; the lower-court determination must be retained.'},
        {'method': 'A', 'ground': 3,
         'classification': 'QUALIFICATION_UNRESOLVED_IS_PLAUSIBLE_LABEL_BUT_POINT_ROLE_IMPRECISE',
         'finding': 'Absence of a supplied finding deciding associate qualification supports retaining this issue. However the proviso authorizes the original tenant to transfer to an associate, not United Automobiles to assign onward.'},
        {'method': 'B', 'ground': 1, 'classification': 'TEXTUAL_PROVISO_SUPPORTED_STATUTORY_EFFECT_NOT_ESTABLISHED',
         'finding': 'Proviso exists, but phrasing it as written consent for subletting imports a legal interpretation. No supplied rule conclusively resolves that interpretation; literal clause existence and statutory satisfaction should remain separate.'},
        {'method': 'B', 'ground': 2, 'classification': 'KEY_ASSOCIATE_QUALIFICATION_UNRESOLVED',
         'finding': 'Model retains actual dispute over associate qualification. This does not establish that every court-treated fact is missing.'},
        {'method': 'B', 'ground': 3, 'reason_affected': True,
         'classification': 'SOURCE_CONTRADICTED_POINT_AND_INTERNAL_INCONSISTENCY',
         'source': 'p0004.s002',
         'finding': 'Point asserts legally established parting with possession rather than subletting and marks SUPPORTED. Source reports induction as sub-lessee; explanation itself calls precise mode unverified. A general rule listing alternatives cannot establish which alternative happened.'}],
    'intermediate_trace': {
        'A': 'Final repeats the notes coverage claim that key court findings were omitted, despite full source being supplied.',
        'B': 'Proposal x2 classified court-reported sub-lessee induction as PART_WITH_POSSESSION; program gave local PROPOSED_SUPPORT, not semantic validation. Final point3 resembles this misclassification. This is a plausible propagation path, not proof of model attention or causal attribution.',
        'B_not_propagated': 'Corporate-amalgamation/US-versus-Indian identity contamination in old proposal did not appear in final answer; this is not evidence of B superiority because A did not make that error.',
        'program_checks': 'All54 old combinations remain UNRESOLVED; this expresses limits of supplied proposals/bindings, not absence of source court findings.'},
    'shared_limits': ['Both final outcomes UNDETERMINED can be defensible under restricted legal materials; same label is not proof of correctness.',
                      'Both use a conditional proviso without a supplied interpretation closing its statutory scope.',
                      'Missing target appellate reasoning differs from absent lower-court determination.',
                      'Neither identifies program-derived facts as the decisive source of an improved final answer.'],
    'decision': 'PRIORITIZE_TEXT_FOR_CURRENT_DEVELOPMENT_PAIR',
    'decision_basis': 'No source-verified overall B improvement; B introduces categorical mode misclassification and label inconsistency while using much more final input. A is also materially flawed. This is a resource choice for this old-case development configuration, not proof text reasoning is accurate or structured methods generally inferior.',
    'next_change_recommendation_only': 'Prioritize final judgement use of already supplied court findings and separation from unresolved legal scope. No new prompt or rerun in this round.',
    'accuracy_or_generalization_claim': False, 'new_annotations': 0, 'web_calls': 0}
write_new(ROOT / 'final-source-review.json', review)
write_new(ROOT / 'decision.json', {k: review[k] for k in ['decision', 'decision_basis', 'next_change_recommendation_only']})

start = read(ROOT / 'start-audit.json')
changed = [name for name, value in start['old_outputs'].items() if digest(Path(name).read_bytes()) != value]
assert not changed, changed
write_new(ROOT / 'preservation-check.json', {'old_files_checked': len(start['old_outputs']), 'changed_files': changed})
frozen = read(ROOT / 'freeze/config.json')
assert all(digest(Path(name).read_bytes()) == value for name, value in {**frozen['files'], **frozen['live_code']}.items())
(ROOT / 'final-answer-slots.md').write_text(
    '# 69305恢复后的完整回答\n\n[A文本笔记后的完整回答](runs/A/parsed.json)；'
    '[B部分事实与程序检查后的完整回答](runs/B/parsed.json)。\n\n'
    'A为本轮唯一新调用，B复用约束诊断FIXED结果，两份V8中间结果未重新生成。'
    '完整原始输出、来源恢复、成本与一次集中审阅均保留；开发审阅不是人工金标准。\n', encoding='utf-8')
a, b = rows
report = f'''V10：修复约束后的69305同案最终回答比较

结论：同案配对已恢复，A和B都完整生成并回答UNDETERMINED，但决定性依据均有错误。本案暂优先文本流程继续开发：未发现B完整答案的可核查整体改善，B新增了转移方式的确定判断与解释矛盾，并增加输入负担。A也不能作为可靠法律方法。本结论是一个旧案例下的投入决定，不是泛化能力或准确率排名。

实际运行
A复用V8文本笔记，使用原V9最终prompt与修复约束，只新调用一次。B复用JSON约束诊断中已完成的FIXED结果；逐字核对prompt、Schema、共同来源、法源包、生成设置及修复mask定义，兼容后直接采用，没有补跑B。两份中间材料均来自旧约束下已完成的V8提议，因此这是恢复后的最终阶段比较，不是把整套两阶段方法都用新约束重新跑一遍。
Qwen3.5-9B-4bit revision8b2b98c00a6b4d291155e4890773ca8f769aee53、MLX-VLM0.7.4、greedy、repetition_penalty1、thinking off、Schema约束不变；每次最终上限3072，总预算32768，没有截断原文。A输入{a['final_input_tokens']}、输出token IDs{a['final_output_token_ids']}、{a['final_seconds']}秒；B输入{b['final_input_tokens']}、输出token IDs{b['final_output_token_ids']}、{b['final_seconds']}秒。两边均stop，无重复保护触发、格式修补或重试。输出计数沿用保存的token IDs口径，包含结束token。新调用1、复用最终调用1、网页0、重试0。
历史第一阶段耗时A{a['intermediate_seconds']}秒、B{b['intermediate_seconds']}秒。连同恢复最终阶段账本为A{a['recorded_two_stage_seconds']}、B{b['recorded_two_stage_seconds']}秒，未包含历史失败尝试或额外诊断调用；这些运行发生于不同时间，不能当作严格同步性能测试。

两份答案具体哪里成立，哪里有问题
1. A正确区分房东提出“未经同意转租”的主张与主张本身是否成立。但A第二项与总理由说材料没有可采性的法院判断。原文p0004.s002明确写Rent Controller及上诉机构认定租约条款“was not inadmissible”，允许租户依赖，并以United Automobiles被引入为sub-lessee为由命令腾退。A把可见的下级认定丢失了；不能用目标最高法院理由被排除来解释下级认定不存在。
2. B第二项保留associate concern身份尚未明确的争点，这与允许材料一致。B第三项却断言“转移方式已依法确定为parting with possession而非subletting”，标SUPPORTED，解释又说具体方式尚未核实。原文记载的是下级法院认定sub-lessee。旧提议x2同样把该记录填成PART_WITH_POSSESSION，程序局部PROPOSED_SUPPORT仅基于提议。错误可能沿这条链传播；最终文字与提议相似不能证明模型必然依赖程序。
3. 双方仍须区分租约中存在有条件的associate例外，与该例外在Section14(1)(b)下是否等同本次交易的书面同意。共同法源提供转移行为、书面同意及日期的基本条件，没有提供解决Section49 collateral purpose和本案associate定义的完整解释。B把条款称为written consent for subletting，不能仅以来源编号有效就认为法定效果已核验。A第三项还把应由原租户向associate转移的权限写得像由United Automobiles继续assign，角色表达不够准确。

结构化材料的作用与限制
B保留了一部分下级裁判信息，并未在最终答案照抄旧提议中混入的American/Indian公司合并身份。然而A没有该身份错误，不能把B的自我纠错算成胜过A。B未纠正转移方式，程序54个组合UNRESOLVED也没有带来明确、可靠的最终判断增益。两边最终UNDETERMINED可以是合理的谨慎标签，但标签相同不代表理由正确。本轮没有用历史案件胜败要求模型猜回被排除的最终判决。

三种缺口
材料明确提供了下级法院的可采性和sub-lessee认定，这不是事实缺失。允许输入未给出完整associate资格裁判细节，需保留范围限定。法源包没有解决关键合同/登记法解释，这是法律覆盖缺口。程序没有实现这些开放法律解释，是程序覆盖缺口，不能改说原文没记载。两个最终判断器有完整原文，因此可见认定被遗漏也不能全部归责于抽取字段。

范围、交付与停止
仅69305一个已反复参与开发的旧案，复用已有检索、允许来源、法律包和中间结果；含下级裁判信息及后于目标年份的法源，仍是回顾性开发材料。原V1–V9及约束诊断结果未覆盖，首次A生成前冻结当前源码、prompt、Schema、设置、来源哈希、调用和审阅规则。只对两份最终答案做一次集中决定性来源审阅，没有全量中间标注、网页复核、新gold或额外模型调用。完整答案、raw、逐案表、引用恢复、B检查轨迹与兼容审计均保存。
下一轮最值得修改的是最终判断如何保留已经给出的法院认定，并把事实未决与法律解释未决分开；本轮只提出建议，未改prompt或重新生成。本轮结束，不扩案、不自动启动下一轮、不提交或推送。
'''
(ROOT / 'report-zh.txt').write_text(report, encoding='utf-8')
print(json.dumps({'new_calls': results['new_model_calls'], 'complete_final_answers': 2,
                  'decision': review['decision'], 'preserved_files': len(start['old_outputs'])}, indent=2))
