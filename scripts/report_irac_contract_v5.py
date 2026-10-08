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
    links = ['# V5 完整回答与提议', '', 'A直接回答；P结构化提议；B原提议＋原文；C再加程序检查。全部本轮实际生成，没有旧答案补位。', '', '|案件|A|P|B|C|', '|---|---|---|---|---|']
    for cid in CASES:
        links.append('|'+cid+'|'+ '|'.join('[raw](runs/'+cid+'/'+s+'/raw-response.txt)' for s in ('A','P','B','C'))+'|')
    links += ['', '每个P目录同时保存 evidence-records.json、import.json、checks-full.json、checks-compact.json。每个位置保存 prompt、schema、rendered、raw、token IDs、run/result、delivery及实际参数。', '', '旧V5工程检查点在父目录，未覆盖；本轮freeze/config.json与freeze/code为实际生成版本。']
    (R / 'answers.md').write_text('\n'.join(links)+'\n')

    lines = ['IRAC V5：接口契约修复与两案完整流程开发验收', '',
      '结论：E工程处理在本轮验收范围内通过；M事实安排和证据用途组织未通过；L完整法律回答未通过。保留已经修好的工程接口，不能宣布法律分析已修好，也没有依据否定整个图方法。本轮未训练GNN。', '',
      '运行：112400、188721101按A/P/B/C顺序完成8次本地调用，得到2份完整提议及6份完整回答。截断、格式失败、资源失败、跳过、重试、网页调用均为0。总生成时间1158.80秒（19.31分钟），模型加载另计4.13秒。完成后已停止，不提交或推送。', '',
      'E：复用已通过的限制范围、合法地址及原文排序修复，补完独立证据账本与用途局部隔离。22项直接相关测试通过；15个真实tokenizer完整样例与5项约束回归按未变Schema和约束哈希复用。实际入口保留13/13条原始证据，188721101的1条跨绑定限制仅局部隔离，B/C均正常运行。模型条件汇总与证据计算分开，最终C输入没有MISSING_DECLARED_USABLE_EVIDENCE。合法地址与引文地址只证明接口，不证明语义。', '',
      '112400：首次取得这一版本的完整配对，但P把同一请求的诉讼、家庭规模、住房适宜性拆成3个安排；把“需求不真实”连为支持真实需求，把家属名单连为支持依赖。A还把现住处不适合反写成反驳“无其他适宜住所”。B纠正这两项方向，仍无依据认定原租赁为住宅用途、家庭成员依赖及无其他住所。C新增“High Court采纳不真实需求认定”的错误，并把L140已有的not reasonably suitable说成仅有not reasonably sufficient。原文顺序已正确、后续认定已送达，这些错误不能再归因于缺段或程序删除。', '',
      '188721101：P的6条用途均选择ADDR-001时间条件，其中原审许可与家庭判断被当作反驳1952阈值，程序据此得出b1请求REFUTED。这是提议语义错误传播，不是正确法律证明。A把1987租赁日期当精确转移日期，并将雇佣领薪证言说成法院认定。B保留工资凭证未证明，是局部改善；但把交出占有一条路线失败说成足以否定整体，并反转书面同意主体。C传播不存在的日期证言冲突，新增无法源支持的举证责任和原审对上诉有约束力的说法。三者均不足以处理父亲先前安排、另租6号铺与柜台迁移、邻居关于实际经营者的反论。', '',
      '真实缺口：112400未明确原租约住宅用途；一处住所不适合不完整证明无其他住所；给定法条缺进一步适用、证明及上诉规则。188721101未交代相应书面同意，父亲安排细节少，证言与控制权存在争议；精确日期未知不等于可以忽略所述先租后转移的条件化时间顺序。最终预测均为PREDICT_DENY，但本轮没有建立二元gold，不以历史裁判方向判断六份答案正确。', '',
      '比较判断：B出现具体局部纠错，未达到忠实完整分析验收；C未显示相对B的可靠净收益。未知状态和拒绝预测有时出自模型自行制造的缺口。程序检查也会正确计算错误的用途提议，其作用限于已声明结构。停止继续添加字段或立刻重跑；若以后另行授权，优先检验安排识别与语义用途对应。', '',
      '|案件|方法|输入tokens|输出tokens|生成秒|', '|---|---|---:|---:|---:|']
    for r in rows:
        lines.append('|%s|%s|%s|%s|%.2f|' % (r['case_id'],r['stage'],r['input_tokens'],r['output_tokens'],r['seconds']))
    lines += ['', 'B的方法成本按P+B、C按P+C计算；本批P实际共享一次，不能把两种方法成本相加当批次总成本。112400：A71.52秒、P+B253.43秒、P+C303.82秒。188721101：A142.57秒、P+B324.71秒、P+C372.80秒。C最终输入分别为19527/20812 tokens，B为10405/13181；成本增加未转化为可靠完整答案改善。MLX峰值最高7.557GB，进程峰值RSS最高1.621GB，两者口径不同，不相加。', '',
      '固定配置：Qwen3.5-9B-4bit revision 8b2b98c00a6b4d291155e4890773ca8f769aee53；MLX-VLM0.7.4、LMFE0.11.2、已修复约束、greedy、seed20261001、repetition_penalty=1、thinking关闭。提议4096，最终3072，总上下文32768。完整材料输入核验8/8通过。代码与材料冻结哈希未变，保留清单2426项未变化；没有读取SEALED。', '',
      '请求记录说明：未在当前可访问会话及附件找到END_V5_CONTINUATION原文；已向用户说明并按最新明确授权的两案、证据独立保存、最多8次/30分钟等要求执行，不声称核对过未取得的附加文本。', '',
      '审阅为一次模型辅助来源审阅，不是人工金标准；未重标注所有中间字段。以上只适用于两份已参与开发的问题包，不是独立测试，也不是对全部图方法的否定。原V4失败、V5初始工程快照及所有旧结果保持原字节。', '',
      '完整入口：answers.md；逐案结果：case-comparison.csv/json；逐调用成本：call-costs.csv、costs.json；一次审阅：final-source-review.json；E/M/L：acceptance.json；工程证据：engineering/；实际冻结：freeze/config.json；送达：delivery-validation.json；保留检查：preservation-after.json。']
    (R / 'report-zh.txt').write_text('\n'.join(lines)+'\n')
    print('V5 delivery created; no inference or output modification')


if __name__ == '__main__':
    build()
