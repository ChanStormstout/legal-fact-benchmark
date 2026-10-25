# -*- coding: utf-8 -*-
"""Persist the single post-batch source review; never edits model outputs."""
import csv
import json
from pathlib import Path

from irac_contract_v5 import read, save, hf, inputs
from irac_contract_v5_run import R, CASES, ORDER, preserved


def finding(key, location, sources, judgment):
    return {'id': key, 'output_locations': location, 'source_ids': sources, 'judgment_zh': judgment}


def build():
    assert not (R / 'final-source-review.json').exists(), 'Do not overwrite the completed source review'
    cfg = read(R / 'freeze/config.json')
    assert all(hf(p) == h for p, h in dict(cfg['code_hashes'], **cfg['material_hashes']).items())
    summary = read(R / 'run-summary.json')
    assert summary['generation_calls'] <= 8 and summary['elapsed_generation_seconds'] <= 1800
    rows, reports, audits = [], [], []
    for cid, stage in ORDER:
        out = R / 'runs' / cid / stage
        meta, result = read(out / 'run.json'), read(out / 'result.json')
        delivery = read(out / 'delivery.json')
        assert delivery['passed'] and meta['thinking_disabled_template_verified']
        assert meta['identity']['constraint_mode'] == 'FIXED' and meta['schema_mask_calls'] > 0
        assert meta['raw_hash'] == hf(out / 'raw-response.txt')
        assert meta['prompt_tokens'] + cfg['max_tokens'][stage] <= 32768
        assert result['run_status'] == 'OK' or result['prediction'] is None
        rows.append({'case_id': cid, 'stage': stage, 'run_status': result['run_status'],
            'input_tokens': meta['prompt_tokens'], 'output_tokens': meta['output_tokens'],
            'max_output_tokens': cfg['max_tokens'][stage], 'seconds': meta['elapsed_seconds'],
            'peak_mlx_gb': meta['peak_mlx_memory_gb'], 'process_peak_rss_gb': meta['peak_rss_gb'],
            'answer': str(out / 'result.json'), 'raw': str(out / 'raw-response.txt')})
        audits.append({'case_id': cid, 'stage': stage, 'delivery': str(out / 'delivery.json'),
                      'mask_calls': meta['schema_mask_calls'], 'raw_sha256': meta['raw_hash'],
                      'actual_max_tokens': meta['actual_parameters']['max_tokens'], 'checked': True})
    for cid in CASES:
        pdir = R / 'runs' / cid / 'P'
        raw, imp = read(pdir / 'parsed.json'), read(pdir / 'import.json')
        ledger = read(pdir / 'evidence-records.json')
        assert [r['raw_record'] for r in ledger] == raw['evidence']
        assert imp['raw_proposal'] == raw
        for method in ('B', 'C'):
            assert read(R / 'runs' / cid / method / 'intermediate.json')['proposal'] == raw
            assert 'MISSING_DECLARED_USABLE_EVIDENCE' not in (R / 'runs' / cid / method / 'prompt.txt').read_text()
        reports.append({'case_id': cid, 'record_count': len(ledger), 'record_exact': True,
            'projection_record_count': len(imp['projection']['evidence']),
            'computable_uses': imp['computable_use_count'], 'quarantines': imp['quarantine'],
            'import_status': imp['status'], 'B_C_share_exact_P': True})
    save(R / 'delivery-validation.json', {'passed': True, 'slots': audits, 'proposals': reports,
        'code_and_material_hashes_unchanged': True, 'scope': 'Delivery and execution checks, not legal correctness.'})
    save(R / 'preservation-after.json', preserved())
    assert preserved()['passed']
    save(R / 'costs.json', {'calls': rows, 'generation_calls': summary['generation_calls'],
        'total_input_tokens': sum(r['input_tokens'] for r in rows),
        'total_output_tokens': sum(r['output_tokens'] for r in rows),
        'total_generation_seconds': sum(r['seconds'] for r in rows),
        'model_load_seconds_separate': read(R / 'environment.json')['loaded_seconds'],
        'memory_note': 'MLX allocation peak and process peak RSS are different observations; do not add them or treat RSS as total unified-memory consumption.',
        'cost_note': 'P was generated once per case and shared by B/C. Standalone B cost=P+B and standalone C=P+C; these two method costs are not additive batch costs.'})
    with (R / 'call-costs.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

    review = {
      'evaluation_role': 'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
      'review_rounds': 1, 'web_calls': 0, 'after_all_eight_calls': True,
      'coverage': 'Six full final answers and decisive proposal/check evidence, compared with all allowed source records including unquoted opposing material. No full-field annotation or inferred historical gold.',
      'cases': {
        '112400': {
          'M': 'NOT_PASSED', 'L': 'NOT_PASSED',
          'supported_parts': '原文明确租赁楼上、房东拥有整处房产并占用楼下；早期Rent Controller与Tribunal否定真实需求；发回后Tribunal于1970-05-04认定现住房不适合家庭居住。这些已提供内容应保留各自阶段。',
          'proposal_findings': [
            finding('112-M1', ['P:bindings/b1,b2,b3'], ['IK-112400:L124:restored-v2', 'IK-112400:L139:restored-v2', 'IK-112400:L140:restored-v2'], '同一自住请求的诉讼、家庭人数认定、居住适宜性认定被拆成三个安排。认定的阶段应保留，但不因此成为三个彼此独立的实质安排；程序没有擅自合并。'),
            finding('112-M2', ['P:evidence/e4', 'P:checks b1/C02'], ['IK-112400:L127:restored-v2'], 'e4文本正确记载not bona fide，却以SUPPORT连接表示bona fide的ADDR-002。程序按提议与e2支持、e3反对形成冲突；它没有验证自然语言极性。'),
            finding('112-M3', ['P:evidence/e6', 'P:limitations/l3'], ['IK-112400:L139:restored-v2'], '家庭人数及房屋不足被连接为SUPPORT依赖关系ADDR-005。原文没有独立确认家庭成员对房东的依赖；l3只限制TARGET_ACCEPTANCE，没有改变PROVEN_FACT用途。'),
            finding('112-M4', ['P:limitations/l2,l4', 'P:evidence/e7'], ['IK-112400:L137:context-v4', 'IK-112400:L138:context-v4', 'IK-112400:L139:restored-v2', 'IK-112400:L140:restored-v2'], '提议保存了后续认定，却又从此前发回推称不存在可用认定；l4把L140的not reasonably suitable转述为not reasonably sufficient，并制造措辞不一致缺口。L140正有suitable用语。'),
          ],
          'final_findings': [
            finding('112-L1', ['A:C01', 'B:C01', 'C:C01'], ['IK-112400:L123:span1', 'IK-112400:L124:restored-v2'], '三者均声称租赁明确用于住宅；L123只说明楼层、日期、租金，L124说明房东拟自住，不等于原租约用途。C标签UNRESOLVED但理由仍虚构住宅用途已记载，仅以目标法院尚未接受为理由保留未知。'),
            finding('112-L2', ['A:C02,reason', 'B:C02,reason', 'C:C02,opposition'], ['IK-112400:L127:restored-v2', 'IK-112400:L130:span6'], 'A将否定真实需求的早期认定标为SUPPORTED真实需求，标签与解释矛盾，并虚构目标法院接受。B/C修正C02极性为REFUTED；C又称High Court接受该认定，允许材料只记载发回，不能支持这一归属。B的“contradicts ... tenant denial”措辞也与租户反对需求的立场不符。'),
            finding('112-L3', ['A:C06,reason', 'B:C06', 'C:C06'], ['IK-112400:L139:restored-v2', 'IK-112400:L140:restored-v2'], 'A把现住处不适合误作反驳无其他适宜住所，方向相反。B修正该方向，但把已知一处不适合扩大为全称的无其他住所SUPPORTED。C保留未知却重复虚假的sufficient/suitable区别；正确缺口应限定其他可用住所与目标阶段法律效果，不应抹去已记载的不适合认定。'),
            finding('112-L4', ['B:C03,gaps', 'C:C03,gaps'], ['IK-112400:L124:restored-v2', 'IK-112400:L139:restored-v2', 'IK-18143401:L41:historical-e'], 'B以家庭名单推依赖，同时在gaps承认未确认。C指出依赖未明，却未处理房东本人自住这条择一路径；不能让家庭依赖缺口封锁本人路径。本人自住系已提出的用途主张，不等于已证明真实需求。'),
          ],
          'real_gaps': ['原租赁住宅用途没有明确说明。', '现住处不适合不完整证明不存在其他适宜住宅。', '给定法条未提供bona fide的进一步适用标准或证明责任、审查标准；目标最终裁判仍排除。'],
          'comparison': 'B较A纠正了两个重要极性错误，但仍有用途、依赖与全称判断过度推断。C没有稳定增益，并引入明确的High Court采纳归属错误及虚假缺口。均不能作为完整法律分析通过。',
        },
        '188721101': {
          'M': 'NOT_PASSED', 'L': 'NOT_PASSED',
          'supported_parts': 'L72是房东所述租赁及先父亲、后弟弟安排；L80为邻近店主证言；L81为租户与弟弟证言、钥匙承认及工资凭证未证明；L83是可撤销许可且不构成让与/交出占有的原审判断；L84家庭关系推理也仅为原审意见。',
          'proposal_findings': [
            finding('188-M1', ['P:bindings/b1,b2,b3', 'P:evidence/e1-e6'], ['IK-188721101:L72:restored-v2', 'IK-188721101:L81:restored-v2', 'IK-188721101:L83:restored-v2'], '弟弟使用店铺的争议被拆为指控、原审占有、雇佣/许可三个安排；全部证据又集中在b1，b2/b3无用途。父亲的先前安排没有单独保留。'),
            finding('188-M2', ['P:evidence/e1-e6', 'P:checks b1/C01'], ['IK-188721101:L72:restored-v2', 'IK-188721101:L80:restored-v2', 'IK-188721101:L81:restored-v2', 'IK-188721101:L83:restored-v2', 'IK-188721101:L84:restored-v2'], '六条用途全部选择合法但语义错误的ADDR-001（1952年后时间条件）。其中e5/e6的原审许可、家庭关系判断不能反驳发生于1952年后。程序因此计算C01为REFUTED，b1请求为REFUTED：这是错误提议传播，不是程序取得了法律证明。'),
            finding('188-M3', ['P:evidence/e3,e4', 'P:limitations/l2', 'P:coverage_limits'], ['IK-188721101:L80:restored-v2', 'IK-188721101:L81:restored-v2', 'IK-188721101:L83:restored-v2'], '证人证言被标PARTY_CLAIM；l2使用b2但指向属于b1的e5/e6，被局部隔离且保留未映射限制，没有删除六条证据。提议另外虚构起始日期证言冲突及原审判断对上诉有约束力，给定材料均未提供这些依据。'),
          ],
          'final_findings': [
            finding('188-L1', ['A:C01', 'B:C01,gaps', 'C:C01,gaps'], ['IK-188721101:L72:restored-v2', 'IK-188721101:L80:restored-v2', 'IK-188721101:L81:restored-v2'], 'A把1987-01-06租赁日期直接写成转移日期。B避免精确日期替换，但与C一起虚构关于起始日期的证言冲突。若接受所述先租赁后安排的顺序，可以条件化说明1952阈值；该条件化推断不证明转移实际发生，也不要求知道精确日期才能理解阈值。'),
            finding('188-L2', ['A:C05', 'B:C05,gaps,opposition', 'C:C05'], ['IK-188721101:L72:restored-v2', 'LAW:S02:DRC14:1b'], 'A虚构房东主张没有许可、租户否认取得许可，并以没有记录支持没有书面同意。B/C虽标未决，仍把转移性质未决当同意记录不可判断的原因；B反转为landlord obtained written consent，C增加无法源的证明责任结论。正确未知原因是允许材料没有交代相关书面同意，不是其他条件争议本身。'),
            finding('188-L3', ['A:C04,C06', 'B:C02,C06', 'C:C02,C06'], ['IK-188721101:L80:restored-v2', 'IK-188721101:L81:restored-v2', 'IK-188721101:L83:restored-v2'], 'A把雇佣领薪从证言升级为法院认定，遗漏工资凭证未证明。B在C02明确保留工资缺证这一限制，是局部改善；其C06仍以薪资证言支持控制权而未充分处理相反证据。C再次把原审许可与mere employment混写。L83支持原审许可及保留法律占有的分析，不证明所有薪资证言已获采纳。'),
            finding('188-L4', ['B:opposition,reason', 'C:opposition,gaps,reason'], ['IK-190902:L109', 'IK-190902:L110', 'IK-190902:L112', 'IK-188721101:L83:restored-v2'], 'B称否定最重要的交出占有路线足以否定整个请求，同时另两条路线未决；这没有忠实保留法条的择一关系。C把原审许可结论当成对上诉有约束力，给定材料没有该上诉规则，且同时说其他路线尚未解决。保留原审不等于升级为目标法院认可。'),
            finding('188-L5', ['A/B/C:opposition,reason'], ['IK-188721101:L72:restored-v2', 'IK-188721101:L73:restored-v2', 'IK-188721101:L80:restored-v2', 'IK-188721101:L81:restored-v2'], '三份最终回答均未充分处理父亲的先前安排、弟弟另租6号铺且柜台转到15号铺的指控，以及邻近店主认为实际经营者为弟弟而非租户的证言。B只恢复了工资凭证未证明的一项反论。原文中未被模型引用的重要内容也纳入本次审阅。'),
          ],
          'real_gaps': ['书面同意未交代；精确安排日期未知，但不能忽略所述先租后安排的条件化时间顺序。', '父亲安排的具体条件资料稀少。', '关于占有与雇佣的证据有冲突；给定法律没有补齐证据权重、上诉拘束或举证责任的规则。'],
          'comparison': 'B避免A的精确日期误写并保留工资凭证未证明，C也保留原审许可分析；但B新增择一路径必需化和许可主体反转，C新增或传播无依据举证责任/上诉拘束。完整答案净收益未得到可靠支持。',
        }
      },
      'decision': 'KEEP_ENGINEERING_REPAIRS_NO_COMPLETE_LEGAL_ANALYSIS_ACCEPTANCE',
      'next_investment_boundary': '保留证据与用途隔离、合法地址和来源排序。下一步若另行授权，应先检验安排识别及语义用途对应；本轮停止，不再加字段、调提示或训练图。两案未训练GNN，不能否定整个图方法。',
      'binary_prediction_boundary': '六份答案都为PREDICT_DENY；这不是六个正确标签。目标最终裁判未输入，没有建立新的二元gold，本轮评价决定性依据而非猜中历史结果。',
    }
    # Preserve exact excerpts and locate them in the approved material only.
    excerpts = {
      '112400': [('IK-112400:L123:span1', 'The appellant took on lease, the first floor'),
        ('IK-112400:L127:restored-v2', 'the requirement of the landlord for his occupation was not bona fide'),
        ('IK-112400:L140:restored-v2', 'were not reasonably suitable for his residence')],
      '188721101': [('IK-188721101:L72:restored-v2', 'on 06.01.1987'),
        ('IK-188721101:L81:restored-v2', 'Salary vouchers of payment of salary to Sh. Bhagwan Dass were also not proved.'),
        ('IK-188721101:L83:restored-v2', 'which licence or privilege could be terminated at the sweet will and pleasure of respondent'),
        ('IK-190902:L109', 'These three expressions deal with different concepts and apply to different circumstances.')]}
    for cid, xs in excerpts.items():
        m, t, law, sm = inputs(cid)
        sources = dict(m['sources'], **{s['source_id']: s for s in law})
        rows_q = []
        for sid, quote in xs:
            text = sources[sid]['text']; start = text.index(quote)
            rows_q.append({'source_id': sid, 'quote': quote, 'source_char_range': [start, start + len(quote)],
                           'source_sha256': __import__('hashlib').sha256(text.encode()).hexdigest()})
        review['cases'][cid]['key_excerpts'] = rows_q
    save(R / 'final-source-review.json', review)
    acceptance = {'E': {'status': 'PASS_BOUNDED_ENGINEERING_CONTRACT', 'tests': 22,
        'real_calls': 8, 'raw_records_preserved': 13, 'local_quarantines': 1,
        'limits': 'Actual record meaning, use direction and arrangement identity are not certified by E.'},
        'M': {'status': 'NOT_PASSED', 'cases': {c: review['cases'][c]['M'] for c in CASES}},
        'L': {'status': 'NOT_PASSED', 'cases': {c: review['cases'][c]['L'] for c in CASES}},
        'technical_completed_answers': 6, 'technical_failed_answers': 0,
        'review_role': review['evaluation_role'], 'stopped': True, 'git_commit': False, 'git_push': False}
    save(R / 'acceptance.json', acceptance)

    comparisons = []
    details = {
      ('112400','A'): ('保留所有权及早期不真实需求认定文字', '住宅租赁用途无据；C02与C06极性反写；虚构目标采纳', '安排按条件拆分；理由与标签相矛盾'),
      ('112400','B'): ('修正A的需求与住所条件方向；明确先前认定', '家庭名单推依赖；现住处不适合推无其他住宅；住宅用途仍无据', '同一请求分成多个认定安排；未准确限定全称缺口'),
      ('112400','C'): ('保存所有权；部分未决继续保留', '虚构High Court采纳；把L140适合用语改成充分；忽略本人择一分支', '未知理由包含模型制造的缺口'),
      ('188721101','A'): ('保留原审可撤销许可及法律占有方向', '租赁日期当转移日期；编造无同意陈述；雇佣证言升级法院认定', '忽略工资凭证缺失、父亲及邻居/另铺反论'),
      ('188721101','B'): ('恢复工资凭证未证明；避免精确转移日期；保留许可判断', '一条OR路线失败当足够否定；同意主体反转；虚构日期冲突', '其余路线未决却以某一路线必需化定案；遗漏重要反论'),
      ('188721101','C'): ('保留原审许可与当前未知，不直接沿用程序时间REFUTED', '新增举证责任；原审上诉拘束；无同意及日期冲突仍无据', '模型制造的未知与真实缺口混合；遗漏重要反论'),
    }
    for cid in CASES:
        pr = next(r for r in rows if r['case_id'] == cid and r['stage'] == 'P')
        for stage in ('A', 'B', 'C'):
            rr = next(r for r in rows if r['case_id'] == cid and r['stage'] == stage)
            own = [rr] if stage == 'A' else [pr, rr]
            supported, errors, omissions = details[(cid,stage)]
            comparisons.append({'case_id': cid, 'method': stage, 'technical_status': rr['run_status'],
                'prediction': read(R / 'runs' / cid / stage / 'result.json')['prediction']['answers'][0]['prediction'],
                'source_supported': supported, 'confirmed_errors': errors, 'omissions_or_inconsistency': omissions,
                'real_gaps': '；'.join(review['cases'][cid]['real_gaps']), 'L': 'NOT_PASSED',
                'method_calls': len(own), 'method_input_tokens': sum(x['input_tokens'] for x in own),
                'method_output_tokens': sum(x['output_tokens'] for x in own),
                'method_seconds': round(sum(x['seconds'] for x in own), 3), 'answer_path': rr['raw']})
    with (R / 'case-comparison.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(comparisons[0])); w.writeheader(); w.writerows(comparisons)
    save(R / 'case-comparison.json', comparisons)
    links = ['# V5 Complete Answers and Proposals', '', 'A: direct answer; P: structured proposal; B: original proposal plus source; C: additional program checks. All outputs were actually generated in this run; no old answers fill slots.', '', '|Case|A|P|B|C|', '|---|---|---|---|---|']
    for cid in CASES:
        links.append('|'+cid+'|'+ '|'.join('[raw](runs/'+cid+'/'+s+'/raw-response.txt)' for s in ('A','P','B','C'))+'|')
    links += ['', 'Each P directory preserves evidence-records.json, import.json, checks-full.json and checks-compact.json. Every slot retains prompt, schema, rendered input, raw output, token IDs, run/result, delivery and actual parameters.', '', 'The old V5 engineering checkpoint in the parent directory remains unchanged; freeze/config.json and freeze/code identify the actual generation version.']
    (R / 'answers.md').write_text('\n'.join(links)+'\n')

    lines = ['IRAC V5: Interface-Contract Repairs and Two-Case End-to-End Development Acceptance', '',
      'Conclusion: E engineering handling passes within this acceptance scope; M factual-arrangement/evidence-use organization and L complete legal answers do not. Retain repaired interfaces, without declaring legal analysis fixed or rejecting graph methods generally. No GNN was trained.', '',
      'Execution: 112400 and 188721101 completed eight local A/P/B/C calls, producing two complete proposals and six complete answers. Truncations, format/resource failures, skipped slots, retries and web calls: zero. Generation took 1,158.80 seconds (19.31 minutes), plus 4.13 seconds for model loading. The run stopped without commits or pushes.', '',
      'E: reuse of validated restriction scope, legal addresses and source ordering, with an independent evidence ledger and use-local isolation added. All 22 relevant tests pass. Fifteen full real-tokenizer examples and five constraint regressions are reused under unchanged schema/constraint hashes. The actual entry preserves all 13 original evidence records; one cross-binding restriction in 188721101 is isolated locally and B/C run normally. Model condition summaries remain separate from evidence computation. Final C input has no MISSING_DECLARED_USABLE_EVIDENCE. Valid addresses establish interfaces, not semantics.', '',
      '112400: the first complete paired run for this version. P splits litigation, family size and accommodation suitability into three arrangements for one request, links a not-bona-fide finding as support for bona fides, and treats a family list as dependency evidence. A also reverses unsuitable current accommodation into opposition to no other suitable residence. B corrects these two directions but still asserts unsupported residential lease purpose, family dependency and absence of other accommodation. C invents High Court adoption of the adverse bona-fide finding and says L140 only contains not reasonably sufficient despite its actual not reasonably suitable wording. Source order and later findings were correctly delivered; missing passages or program deletion cannot explain these errors.', '',
      '188721101: all six P uses select the ADDR-001 timing condition, treating trial-court licence/family assessments as rebutting the 1952 threshold. The program consequently marks b1 REFUTED, propagating a semantic proposal error rather than proving a legal conclusion. A substitutes the 1987 lease date for the transfer date and promotes employment/pay testimony to a court finding. B retains the unproved wage receipt, a local improvement, but treats failure of the parting-with-possession route as sufficient to reject the whole request and reverses the written-consent actor. C propagates a nonexistent date-testimony conflict and adds unsupported burden-of-proof and appellate-binding rules. All three inadequately address the earlier father arrangement, separate shop 6/counter relocation and neighboring shopkeeper testimony about actual operation.', '',
      'Real gaps: 112400 does not establish original residential lease purpose; one unsuitable residence does not prove absence of all alternatives; supplied law lacks further applicability, proof and appellate rules. In 188721101, written consent is unspecified, father-arrangement details are sparse, and testimony/control are disputed. An unknown exact date does not erase the conditional lease-before-transfer sequence. All predictions are PREDICT_DENY, but no binary gold is established and matching historical outcomes does not validate the six answers.', '',
      'Comparison: B makes specific local corrections but fails faithful, complete-analysis acceptance. C shows no reliable net gain over B. Unknown states and refusal predictions sometimes reflect model-invented gaps. Program checks can correctly compute incorrect use proposals and are limited to declared structure. Stop adding fields or immediately rerunning. If separately authorized later, prioritize arrangement identification and semantic evidence-use alignment.', '',
      '|Case|Method|Input tokens|Output tokens|Generation seconds|', '|---|---|---:|---:|---:|']
    for r in rows:
        lines.append('|%s|%s|%s|%s|%.2f|' % (r['case_id'],r['stage'],r['input_tokens'],r['output_tokens'],r['seconds']))
    lines += ['', 'B method cost is P+B and C cost is P+C; the batch actually shares P once, so method costs must not be summed as batch spending. For 112400: A 71.52 seconds, P+B 253.43, P+C 303.82. For 188721101: A 142.57, P+B 324.71, P+C 372.80. Final C inputs are 19,527/20,812 tokens versus B 10,405/13,181. Higher cost does not yield reliable full-answer improvement. Maximum MLX peak is 7.557 GB and process peak RSS 1.621 GB; these measures differ and are not additive.', '',
      'Fixed configuration: Qwen3.5-9B-4bit revision 8b2b98c00a6b4d291155e4890773ca8f769aee53; MLX-VLM 0.7.4, LMFE 0.11.2, repaired constraints, greedy decoding, seed 20261001, repetition_penalty=1 and thinking disabled. Proposal limit 4,096; final limit 3,072; total context 32,768. Full-material input checks pass 8/8. Frozen code/material hashes and 2,426 preservation entries are unchanged. SEALED was not read.', '',
      'Authorization record: END_V5_CONTINUATION was not found in accessible conversation or attachments. This was disclosed to the user; execution followed the latest explicit authorization for two cases, separate evidence preservation and at most eight calls/30 minutes. No claim is made to have checked unavailable supplemental text.', '',
      'The single concentrated model-assisted source review is not human gold; intermediate fields were not all reannotated. Conclusions apply only to these two development question packages, not independent testing or all graph methods. V4 failures, the initial V5 engineering snapshot and all old results retain original bytes.', '',
      'Complete entry: answers.md; per-case results: case-comparison.csv/json; call costs: call-costs.csv, costs.json; single review: final-source-review.json; E/M/L: acceptance.json; engineering evidence: engineering/; actual freeze: freeze/config.json; delivery: delivery-validation.json; preservation: preservation-after.json.']
    (R / 'report-zh.txt').write_text('\n'.join(lines)+'\n')
    print('V5 delivery created; no inference or output modification')


if __name__ == '__main__':
    build()
