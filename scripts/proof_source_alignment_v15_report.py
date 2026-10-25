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
    md = ['# V15: Source-to-Derivation Traces for Four Requests', '', 'Original P, automated proposals and independent reviews are preserved separately. TRUE/FALSE denotes scoped applicability of the selected rules, without formal legal approval.', '']
    for r in rows:
        cid = r['case_id'];md += [f"## {cid} / {r['request_id']}", '', f"D={r['D']}；P={r['P']}；R={r['R']}。{r['finding']}", '', r['boundary'], '', r['natural_problem'], '',
             f"[Full stepwise trace](paths/{cid}/trace.json) · [Original proposal](raw/{cid}/proposal/assistant.txt) · [Independent review](raw/{cid}/review/assistant.txt)", '',
             'Source → role and use → whole premise → fixed rule → scoped result:', '']
        t = read(ROOT / 'paths' / cid / 'trace.json')
        for slot in t['slots']:
            d, a, ck = slot['directory'], slot['model_alignment'], slot['checks']
            refs = sorted({ref for comp in a['whole_premise']['components'] for wit in comp['witnesses'] for ref in wit['refs']})
            md += [f"- **{d['address']} / {d['premise_id']}**：{d['proposition']}", f"  Source addresses: {', '.join(refs)}。model whole-premise state={a['whole_premise']['state']}，coverage declaration={a['whole_premise']['complete']}；structure={ck['structural_status']}；review={ck['review']['decision']}。", '']
    textsave(ROOT / 'walkthrough.md', '\n'.join(md))
    report = "# V15 Automated Source Alignment and Conditional Derivation: Completion Report\n\nFour fixed DEV requests, four source-alignment proposals, four independent source reviews and three D/P/R views are complete. Retries: 0; local model calls: 0; new training: 0. All eight replies parse and 22 engineering checks pass. The automated process restores two sourced, model-reviewed scoped paths on deeply developed requests, but stable autonomous completion of other requests remains unproven. Retain source alignment as a candidate requiring review; do not resume three-class evidence-use training.\n\n| Case/request | D: deterministic adaptation | P: conditional derivation | R: review-accepted view | Meaning and blocker |\n|---|---|---|---|---|\n| 396336 / Q1::R1 | UNKNOWN | TRUE | TRUE | Explicit member correspondence and new documentary witnesses restore the no-jointness/no-total-separation presumptions; this does not establish all inherited title. |\n| 594273 / Q2::R5 | UNKNOWN | TRUE | TRUE | Territorial, statutory and co-mortgagor premises are restored while lower-court findings, denials and unresolved amounts/shares remain distinct. |\n| 121775 / Q2::R6 | UNKNOWN | FALSE | UNKNOWN | Special early termination is correctly negated, but affirmative institutional binding is unproved; rejection of the whole item also blocks its supported negative classification. |\n| 907531 / Q1::R1 | UNKNOWN | UNKNOWN | UNKNOWN | Four candidate premises are accepted, but an existing rule quotation's hyphenation mismatch blocks both alternative routes. |\n\nLabels describe scoped applicability under fixed request rules, not case outcomes or counts of unknown facts. The first three cases each have one existing route; the fourth has two. Alternative routes, objections and local gaps are retained. Repeated premises within a case are not independent cases. All results lack formal legal approval; R is research acceptance after independent model-assisted source review.\n\n## Implementation and Engineering Limits\n\nThe entry point restores permitted source text by ID and builds candidate/premise addresses with fixed-rule role descriptions. The model proposes role-variable-object links, witnesses, specific evidential functions and separate whole-premise states. The program adds versions, hashes and internal addresses. Original P is unchanged and null quotations remain preserved. Proposing a new explicit witness is distinct from repairing an old quotation. One uniquely resolvable capitalization/display difference in 594273 is handled by the shared adapter and recorded in deterministic_repairs.\n\nThe real entry point runs the independent checker in a separate process. It does not call the task assembler, old references, V14 calibration or a learned model. It shares a reversible quote-location format, not model semantic judgments. Structural PASS establishes address, role, witness and coverage-form compliance only. Name equivalence, completeness and attribution still require source review. Background/partial support or USABLE does not establish whole-premise truth. OPEN_TEXT is not converted to AND, unknown is not negative, and exceptions and independent alternatives remain local.\n\nThe 22 checks comprise 10 new tests and 12 regressions, covering the actual checker subprocess, rejection of self-approval, type/identity separation, partial versus complete support, changed negative quotations, local OR preservation, stage, open rules and null failures. When jsonschema was initially unavailable, the existing dependency-free validator was reused without installation. A shared mutable test-fixture error was also corrected. Tests establish engineering behavior only. Method, contracts, rules and tasks remained fixed after freezing; post-run findings were not repaired and rerun within this batch.\n\n## One Concentrated Source Review\n\nFor 396336, L157 acknowledges Imrit's separation; L159–164 and L170/173 support the court's historical partition/share inference. Opposing accounts at L139 and L181–186, later shared living and transactions remain present. The no-presumption rules at L146–148 remain separate from historical facts. Automation adds explicit member links and witnesses without reading V14 calibration values. L186 addresses a counterargument; labeling it counterevidence is imprecise, as the independent review notes. Scoped TRUE can stand, but does not establish all property or inheritance conclusions.\n\nFor 594273, L107 attributes findings to the Subordinate Judge and High Court. L115–116 frame the Supreme Court's subrogation issue; L121–122 concern historical territorial law and equity. The proposal does not relabel lower-court findings as Supreme Court fact-finding, and retains denials at L105–106 and assignment objections at L110–112. R5 cannot resolve shares and succession at L174/177. The collective other_debtors object supports the shared dispute context, not identical final liability for every person.\n\nFor 121775, L118–119 distinguish special early termination from ordinary expiry. L54 records execution by the Province; L58 assigns the special power to the Secretary of State. Despite acknowledging unproved correspondence, the proposal binds the former to terminating_lessor. Whole-item rejection of A01 is explicable under the strict object contract, but does not disprove the explicit negative classification. Whether negating a nonexistent special event needs complete affirmative actor binding, and whether whole-item rejection hides a valid negative judgment, remain acceptance-granularity limitations. A02's opposition/background use is accepted, but complete=false, missing coverage and mixed statement statuses prevent whole-premise execution. Valid counterevidence remains preserved, not classified as useless or manually repaired.\n\nFor 907531, L136–149 support the historical custom and sudden channel shift; L155–163 limit applicability after the river leaves village boundaries; L165 preserves possible future revival and uncertainty about the later channel. Proposal and review distinguish allegations, historical documents and court assessment. Four addresses provide alternatives for two premises. Nine acceptances and one rejection are not ten independent samples. The blocker is established in the old R1 quote versus estab- lished at L137, producing RULE_SOURCE:QUOTE_NOT_LOCATED. The source was delivered; this is neither missing legal material nor failed model judgment. Quote matching was not relaxed, no case-specific exception added, and no FALSE derivation invented.\n\n## Attribution and Investment Decision\n\nD remains unresolved after shared deterministic repairs. P restores the first two cases through new object, use and whole-premise semantic proposals. R adds independent-review cost while retaining these scoped results. V14 manual calibration is only a post-run explanatory comparison, not test input. Model references, program computation and formal legal approval stay distinct. No GNN or CrossEncoder benefit is established.\n\nThe bounded development decision is to retain automated source alignment and independent review as candidates, without new training. Two real paths are restored; other requests retain supported negative judgments and historical scope. Review identifies one explicit binding inconsistency and a separate old-quotation blocker. Widespread semantic rewriting was not demonstrated, but four exposed cases cannot establish stable automation on new cases. If separately authorized, first expand the declared development coverage. Any later learning candidate should assess whether a specific source-supported link to a fixed premise is valid, covering role/object correspondence, statement status, use and full coverage; do not return to generic USABLE three-class prediction. Inputs would be permitted sources, fixed rules, P and the proposal; outputs scoped ACCEPT/REJECT/UNRESOLVED. Supervision would be independent review with quotes, restrictions and disagreements, not automatic gold. The historical simple comparator here is deterministic checking plus the original proposal.\n\nOne definite whole-item binding rejection, plus disputes about negative proof and acceptance granularity, is insufficient for a reliable new training set. Restoring two deeply developed requests and a valid premise on another does not establish generalization. The 20 old calibration labels only receive a compatibility inventory: 13 limited agreements, 3 semantic differences, 3 unclear uses and 1 dispute. Unchecked labels remain uncertified; TRAIN is unchanged and TEST/SEALED unopened.\n\n## Costs, Records and Delivery\n\nEight ordinary High tasks ran in independent temporary conversations: four proposals followed by four reviews. The UI showed GPT-6/High before submission and after login recovery. Exact revision, tokens, internal context and reasoning time are unavailable. cost.json records file bytes and observed submission-to-retrieval time, not exact inference time; login recovery can inflate it. Attachment assembly and source identity were checked, but actual model reading of every token cannot be proven. No external-search or old-reference input record was found.\n\nLogin failed before the third review was submitted. The first six tasks were not resent; only the remaining two were submitted after recovery. The existing V12 CrossEncoder seed continued and saved under its previous pause arrangement, without new seeds; it is not V15 training cost. HEAD and workspace records are preserved. Hashes of 89 old implementation files and four source/P pairs are unchanged; no claim is made to have rehashed all historical outputs.\n\nDelivery: [case comparison](case-comparison.json), [D/P/R views](three-views.json), [source walkthrough](walkthrough.md), [concentrated source review](final-source-review.json), [learning decision](learning-decision.json), [costs](cost.json), [engineering acceptance](engineering-acceptance.json), [frozen configuration](freeze/config.json), [actual submissions](final-submission-manifest.json), and [preservation checks](preservation-validation.json). Raw replies, full tasks, dynamic review assembly, actual independent entry files and web URLs remain local; screenshots and account UI are excluded from publication.\n\nThis bounded development delivery is complete without formal legal approval. No further web tasks, training, cases, legal sources, commits or pushes are authorized by it. Prepare, manifest inspection and verify results are recorded in repository-verification.json. Stop after delivery.\n"
    textsave(ROOT / 'report-zh.md', report)
    save(ROOT / 'completion.json', {'status': 'COMPLETE_BOUNDED_V15_DEVELOPMENT', 'web_tasks_complete': 8,
                                   'technical_failures': 0, 'new_fits': 0, 'formal_legal_approval': False,
                                   'prescribed_batch_and_single_concentrated_review_done': True,
                                   'no_automatic_next_round': True})


if __name__ == '__main__':
    main()
