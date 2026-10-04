"""Import two completed web replies and record a single source review; no generation."""
import csv
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.contracts import validate

ROOT=Path('outputs/rules-verdict-v14-web-direct')
OLD=Path('outputs/rules-verdict-v13-crosscase')
CASES=['661475','1134266']
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
    if p.exists():
        assert read(p)==x, 'Do not overwrite completed report record'
        return
    with p.open('x',encoding='utf-8') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')

answers={};runs=[];restored={}
freeze=read(ROOT/'freeze.json')
assert all(sha(p)==h for p,h in freeze['files'].items()),'Prepared material changed'
for c in CASES:
    p=ROOT/'runs'/c;t=ROOT/'tasks'/c
    raw=(p/'raw-response.txt').read_text()
    obj,end=json.JSONDecoder().raw_decode(raw.lstrip())
    trailing=raw.lstrip()[end:]
    assert trailing.strip()=='END','Do not guess repairs of ambiguous structure'
    # Explicit end-of-answer marker outside the closed object; all JSON values remain intact.
    clean=raw.lstrip()[:end]
    validate(obj,read(t/'schema.json'))
    (p/'answer.json').write_text(clean,encoding='utf-8')
    write(p/'format-check.json',{'raw_whole_reply_is_json':False,'format_status':'VALID_AFTER_EXPLICIT_END_MARKER_REMOVAL',
        'removed_suffix':trailing,'content_inside_json_unchanged':True,'missing_fields_added':False,
        'source_id_contract_valid':True,'semantic_correctness_not_certified':True,
        'file_citation_display_text_retained':c=='1134266'})
    start=read(p/'start.json');done=read(p/'completion.json');sent=read(p/'submission-time.json')['sent_at']
    observed=(datetime.fromisoformat(done['observed_complete_at'].replace('Z','+00:00'))-datetime.fromisoformat(sent.replace('Z','+00:00'))).total_seconds()
    assert start['url_before']=='https://chatgpt.com/' and start['pro_used'] is False
    assert done['ui_status']=='回答已完成' and done['external_search_visible'] is False
    submitted=(p/'submitted-attachment.txt').read_bytes()
    assert submitted==(p/'attachment-preview.txt').read_bytes()
    assert submitted.startswith((OLD/'runs'/c/'D/prompt.txt').read_bytes())
    assert (t/'prompt.txt').read_bytes()==(OLD/'runs'/c/'D/prompt.txt').read_bytes()
    assert (t/'schema.json').read_bytes()==(OLD/'runs'/c/'D/schema.json').read_bytes()
    source=read(t/'source.json');law=read(t/'law-package.json')
    cm={s['id']:s['text'] for s in source['segments']};lm={s['id']:s['text'] for s in law['law_segments']}
    restored[c]=[{'ground':i+1,'point':g['point'],
        'case_sources':[{'id':r,'text':cm[r]} for r in g['case_refs']],
        'law_sources':[{'id':r,'text':lm[r]} for r in g['law_refs']]} for i,g in enumerate(obj['grounds'])]
    runs.append({'case':c,'method':'WEB_HIGH_D','run_status':'OK','answer':obj,'format_status':'VALID_AFTER_EXPLICIT_END_MARKER_REMOVAL',
        'conversation_url':done['conversation_url'],'displayed_model':'ChatGPT','specific_model_name':None,'displayed_mode':'High',
        'model_identity_limitation':'UI did not expose exact underlying model; no inference from previous conversations',
        'sent_at':sent,'observed_complete_at':done['observed_complete_at'],'observed_submit_to_completion_upper_bound_seconds':observed,
        'precise_generation_seconds':None,'displayed_thinking_duration':done['displayed_thinking_duration'],
        'input_tokens':None,'output_tokens':None,'peak_memory':None,'external_search_observed':False,
        'model_internal_read_coverage_independently_observable':False,'operator_complete_attachment_verified':True,
        'submitted_attachment_sha256':sha(p/'submitted-attachment.txt'),'raw_sha256':sha(p/'raw-response.txt'),
        'generation_calls':1,'retries':0})
    answers[c]=obj
write(ROOT/'results.json',{'runs':runs,'web_answers':2,'local_model_calls':0,'paid_api_calls':0,'retries':0,
    'new_intermediates':0,'new_sources':0,'same_information_scope_verified':True,'no_local_schema_mask_on_web':True})
write(ROOT/'restored-final-sources.json',restored)

review={'type':'ONE_CONCENTRATED_FINAL_SOURCE_AND_OMISSION_REVIEW','reference_status':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
    'previous_source_review_preserved':str(OLD/'final-source-review.json'),'old_reference_revision_required':False,
    'review_agent_or_web_review_calls':0,'full_reannotation':False,'cases':{
    '661475':{
        'decisive_source_refs':['p0001.s001','p0001.s002','p0001.s003','p0001.s004','p0001.s005','p0002.s002@0:412'],
        'local_D_errors_avoided':[
            {'local':'g2/reason用1965起诉日期证明转移在1952之后','web':'g3明确区分程序日期与转移事件，保留时间未定','sources':['p0001.s001','p0001.s002','p0001.s004']},
            {'local':'g4 point把租户父亲许可误写为房东一般许可','web':'g4明确许可来自租户，不能证明房东书面同意或不存在同意','sources':['p0002.s002@0:412']},
            {'local':'reason把written consent写为成立腾退所需必要条件','web':'g4/reason正确把absence of written consent列为未定条件','sources':['LAW:1134266:p0004.s004','LAW:1134266:p0004.s005']}],
        'omission_reduced':'web g2保留下级法院否定共同经营抗辩及缺少财务证据；本地D遗漏此项。',
        'court_and_identity':'租户为父亲，受占有人为两儿子，房东另为respondent。g2明确Rent Controller认定，reason称prior-court finding，没有升为目标终审认可。',
        'condition_logic':'不要求先证明SUBLET/ASSIGN才承认PART_WITH_POSSESSION；已知转移认定与未定日期/同意分别保留。',
        'confirmed_serious_new_errors':[],
        'remaining_precision_and_omissions':['g3描述1965起诉日期，但case_refs未含准确记载此日期的p0001.s001；整份输入确有此事实，属于引用粒度不足。','未完整复述Tribunal和High Court两次驳回上诉；已保留决定性Rent Controller认定，未据这些程序结果推导目标最终结论。','未在最终回答展开后出法源/历史法条版本限制；报告继续保留该范围边界。'],
        'true_gaps':['转移发生的日期未给；1965起诉不能提供1952时间下界。','房东具体书面同意或无同意均未在允许来源确立；父亲许可不能代替。'],
        'internal_consistency':'SUPPORTED转移认定、UNRESOLVED时间与无同意、UNDETERMINED reason一致，未发现同等严重的新矛盾。',
        'assessment':'比本地D更忠实、依据更完整；仍不是历史裁判恢复或完全可靠法律分析。'},
    '1134266':{
        'decisive_source_refs':['p0001.s003','p0002.s001','p0002.s003','p0002.s004','p0002.s006','p0002.s007','p0003.s001','p0003.s003','p0003.s006','p0003.s007','p0003.s008','p0004.s001','p0004.s002'],
        'local_D_errors_avoided':[
            {'local':'g3把registered读成unregistered，套用另一案不可采规则','web':'g1准确保留registered，不将另案associate-concern许可条款混入目标','sources':['p0002.s001','LAW:69305:p0005.s002']},
            {'local':'g2/reason声称没有证据证明Bombay High Court批准合并','web':'g2保存31.12.1981批准及权利转归；g3另列法定定性争议','sources':['p0002.s003','p0002.s006']},
            {'local':'g1/reason将无同意指控及未展示反证升级为absence established','web':'g4将房东指控与法院认定分开， absence仍未定','sources':['p0002.s001','p0004.s002']}],
        'omission_reduced':'g5保留ARC驳回、Tribunal反转、Delhi High Court维持的层级变化；明确程序结果本身不能补出各实质条件认定。',
        'court_and_identity':'原租户American Company，承受权利Indian Company；Bombay审批事件与Delhi腾退程序分别保存，没有升级为被排除的最高法院最终认可。',
        'law_scope':'现有LAW片段涉及specific consent、未登记条款及家庭许可/迟提出抗辩，不完整解决公司合并的法定定性。未凭RC-04宣布目标租约不可采，未把RC-05家庭案事实移入公司案。',
        'confirmed_serious_new_errors':[],
        'remaining_precision_and_omissions':['未充分处理租户FERA法定强制/HP判例抗辩及房东降低股本可有多途径、合并自愿的具体反驳；g3主要保留corporate-shell争议，完整法律分析仍有重要遗漏。','g2把事件称1981 amalgamation，来源明确的是批准日期，未给单独生效日期；不能据此视为已经确认权利转归也在1981。此处可解释为给获批准方案命名，保留精度争议，不认定同等严重的虚构日期。','g4称respondent重复无同意，p0004.s002主要陈述法条与适用主张，不是新增独立证据；其UNRESOLVED状态未把它当反证缺失证明。'],
        'true_gaps':['权利归属事实已给，是否构成S14(1)(b)特定转移及强制合并的法律影响仍未由本包充分解决。','无房东书面同意仍是指控，给定来源未单独说明其是否获认定；不能由没有展示文件推出无同意。'],
        'internal_consistency':'已登记租赁/批准/归属SUPPORTED，合并法定定性与缺乏同意UNRESOLVED，reason与UNDETERMINED对应。未发现本地D的明显相反来源断言，但仍有主要抗辩遗漏。',
        'assessment':'比本地D减少明确来源误读，正确保留事实并区分法律覆盖不足；完整性仍不够，不认证所有决定性依据均已处理。'}},
    'B_P_background_only':'V13 B-P在661475新增日期/择一条件错误，在1134266减少D误读但增加默示同意抗辩；本轮未给网页提议或检查，也没有重新运行B-P。',
    'common_limitations':['两案历史开发材料，非独立测试。','各案法律包、后出法源、下级裁判信息及研究者目标来源基础公式边界不变。','新独立聊天不含本项目历史；模型预训练知识、账户记忆和内部上下文处理不可完全审计。','没有观察到外部搜索；不据此证明所有隐藏处理均相同。','网页没有复用本地token mask、greedy、thinking off或确定预算，具体型号未在界面显示。'],
    'decision':'CONSIDER_WEB_HIGH_RUNTIME_AND_PAUSE_9B_COMPONENT_COMPLEXITY',
    'decision_zh':'网页High配置在两案明显减少基础来源错误，值得继续考虑；暂缓给9B流程增加复杂组件。',
    'decision_boundary':'不能把改善全部归因模型大小，不能确认具体网页型号，不推断整体法律正确性或独立泛化。法源缺口与事实理解分别报告。'}
write(ROOT/'final-source-review.json',review)
write(ROOT/'decision.json',{k:review[k] for k in ['decision','decision_zh','decision_boundary']})
rows=[]
for i,c in enumerate(CASES):
    old=read(OLD/'runs'/c/'D/parsed.json');oldrun=read(OLD/'runs'/c/'D/run.json');rev=review['cases'][c];r=runs[i]
    rows.append({'case':c,'local_D_status':'OK','web_status':r['run_status'],'web_format':r['format_status'],
        'local_outcome':old['outcome'],'web_outcome':answers[c]['outcome'],'avoided_errors':'；'.join(x['local'] for x in rev['local_D_errors_avoided']),
        'source_support_improvement':rev['omission_reduced'],'confirmed_serious_new_errors':'本次有限来源审阅未确认；不等于全部正确',
        'remaining_omissions_and_disputes':'；'.join(rev['remaining_precision_and_omissions']),
        'true_gaps':'；'.join(rev['true_gaps']),'consistency':rev['internal_consistency'],
        'local_input_tokens':oldrun['prompt_tokens'],'local_output_ids':oldrun['output_tokens'],'local_seconds':oldrun['elapsed_seconds'],
        'web_input_tokens':None,'web_output_tokens':None,'web_generation_seconds':None,'web_peak_memory':None,
        'observed_submit_to_completion_upper_bound_seconds':r['observed_submit_to_completion_upper_bound_seconds'],
        'displayed_thinking_duration':r['displayed_thinking_duration'],'displayed_model':'ChatGPT (exact model unavailable)',
        'displayed_mode':'High','conversation_url':r['conversation_url'],'reference_status':review['reference_status']})
write(ROOT/'comparison-table.json',rows)
with (ROOT/'comparison-table.csv').open('x',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
parts=['# V14两份网页完整答案\n\n原始回复保留；仅移除完整JSON后的独立END标记。1134266原文引用显示文本保留在reason内，未改事实或法律内容。\n']
for c in CASES:parts.append(f'\n## {c}\n\n对话：{runs[CASES.index(c)]["conversation_url"]}\n\n```json\n'+(ROOT/'runs'/c/'answer.json').read_text()+'\n```\n')
(ROOT/'final-answer-slots.md').write_text(''.join(parts),encoding='utf-8')
start=read(ROOT/'start-audit.json')
old_changed=[p for p,h in start['historical_files'].items() if sha(p)!=h]
code_changed=[p for p,h in start['code'].items() if sha(p)!=h and p!='scripts/prepare_v14_web_direct.py']
assert not old_changed and not code_changed
write(ROOT/'preservation-check.json',{'historical_files':len(start['historical_files']),'old_changes':old_changed,'preexisting_method_code_changes':code_changed,
    'pre_submission_packaging_fix':'prepare_v14 script initially used wrong retrieval location; resumed preparation before model submission, no method change',
    'initial_preparation_script_hash':start['code'].get('scripts/prepare_v14_web_direct.py'),'frozen_actual_preparation_script_hash':sha('scripts/prepare_v14_web_direct.py')})
write(ROOT/'stop.json',{'reason':'TWO_INDEPENDENT_WEB_ANSWERS_AND_ONE_SOURCE_REVIEW_COMPLETE','web_answers':2,'retries':0,'new_local_calls':0,
    'no_semantic_repair':True,'no_next_round_commit_or_push':True})
report=f'''V14：相同材料的普通High网页直接回答对照

投入决定：网页High配置在两案明显减少基础来源错误，值得继续考虑；暂缓给9B流程增加复杂组件。这个结果说明本轮那些来源误读并非在相同任务材料下不可避免，但不能证明错误根因只在参数规模。网页界面只显示ChatGPT和High/高，没有具体型号；本轮只能比较实际网页配置，不能将它标成已确认的GPT型号。两份答案都是UNDETERMINED，但改善证据来自具体来源处理，而不是标签一致。

范围及执行
661475、1134266各一个新普通High对话，各一次回答，固定顺序。两案V13 D实际prompt前缀原字节、问题、完整示例、允许来源和各自法律包保持一致，附上同一Schema；新增文字只说明完整读取任务、禁止外部搜索/其他版本/其他对话及一次性输出。附件不含旧答案、B提议、检查、评价提示或被排除的目标最终理由。网页无本地逐token约束；内部thinking、采样、预算及文件处理不同，属于同信息范围跨模型/运行配置开发诊断。源材料仍是两个历史开发案件，保留回顾性、后出法源、下级信息及研究者基础公式边界。
Chrome文件上传的file URL权限未启用，没有改浏览器权限。通过网页输入框完整粘贴，由界面自动生成文本附件；逐字比较网页附件预览与实际提交文本，两案均完全相等。保留完整任务文件、实际附件、正文、哈希与对话URL。模型是否内部逐字阅读所有内容不可独立观察；回复引用了本案各个主要来源，没有看到读取失败、外部搜索或混入项目历史的迹象，不冒称内部机制相同。
两份回答完整结束，原始回复均在已闭合JSON后附独立END。本地仅删除该后缀，字段/内容不改，使用现有contracts.validate验证同一Schema；1134266复制出的附件引用名保留于reason。没有补字段、改状态或借网页修复旧答案。网页未给下载JSON链接，因此保存完整原回复和解析文件，没有追问生成文件。

661475：减少的错误与仍未确定的部分
网页g2准确保存Rent Controller的两儿子独占、父亲交出占有认定，并说明共同经营抗辩因缺少财务资料被否定。这比本地D遗漏主要反对理由更完整。网页g3明确1965起诉/后续裁定日期不是转移事件日期，避免本地D用起诉时间证明1952之后；g4明确父亲许可来自租户而非房东，且没有材料证明房东具体书面同意或其不存在。reason正确保留“缺乏书面同意”这个条件的否定方向，没有把正面书面同意当腾退成立的必要条件。
原文p0001.s004：“the first appellant has parted with possession of their portion to them”；同段明确没有接受joint business。p0002.s002@0:412只是父亲许可儿子占用的律师论点。已有下级认定仍保留，转移日期与房东同意状态未定不使它消失。网页没有要求必须另证subletting/assignment才接受parting。未发现同等严重新增错误；g3日期描述的引用没有准确指向p0001.s001，是较轻引用精度问题。未完整复述两次上诉的程序结果，未在最终回答展开历史版本边界，不视为全部法律分析已完备。

1134266：减少的错误及重要遗漏
网页g1正确保留原租户American Company与registered lease deed，避免本地D反写unregistered并套用另一案不可采规则。g2保存Bombay High Court于31.12.1981批准及权利转归Indian Company，g3另行保留其是否构成S14特定转移的法律争议，没有再把批准事实说成缺失。g4没有把房东无同意指控和缺少反证当成无同意已经成立。g5保留ARC驳回、Tribunal反转、Delhi High Court维持的程序层级，同时不猜这些结果背后的具体条件认定，更不升级为目标最高法院最终认可。
p0002.s001原文：“vide a registered lease deed dated 11.7.1966”；p0002.s003：“which was allowed on 31.12.1981, and a scheme of amalgamation was sanctioned”。这些是本地D反写/遗漏而网页保留的明确内容。网页没有新增V13 B-P的“法院批准等于房东默示同意”抗辩，也没有将另案associate concern/家庭许可事实搬入公司案。
网页仍没有充分处理租户FERA强制/HP抗辩及房东“降低股本可有多种路径、没有命令必须合并”的具体反驳。审阅已对照p0002.s007、p0003.s006–s008和p0004.s001，而非只看网页引用。g3主要保留corporate-shell争议，完整法律回答仍有重要遗漏；“1981 amalgamation”只能稳定理解为批准方案的称呼，不能证明权利转归的具体生效日，不从被排除材料补答案。批准/归属事实已知而法定定性未决，是合法区分；包中未提供完整公司合并及强制抗辩的法律处理，不要求猜回历史结论。

成本与记录
网页回答2、本地模型0、API0、重试0、额外网页复核0；两次只生成直接回答。界面思考时长显示29s和49s，不能当总生成时间。发送到首次确认完整结束的观察上界分别{runs[0]['observed_submit_to_completion_upper_bound_seconds']:.1f}秒和{runs[1]['observed_submit_to_completion_upper_bound_seconds']:.1f}秒，包含观察间隔，不是精确模型耗时；网页输入/输出tokens、峰值内存、底层采样参数均不可得，保持null，不据此计算相对9B成本倍数。本地D记录为64.2/64.8秒，但生成机制不同，不声称成本完全可比。
661475：{runs[0]['conversation_url']}
1134266：{runs[1]['conversation_url']}

解释与停止
两案均减少明确事实反写、来源角色混淆及制造缺口；661475额外保留反对理由，1134266额外保留下级程序层级。未确认与本地D同等严重新增错误，但1134266仍有重要反对理由遗漏，不把网页答案称gold或完全正确。V13 B-P只作背景，未新增受测条件。法源真正覆盖不足与模型误读分别记录，旧审阅依据无须修订。现有证据支持暂缓复杂化9B流程并考虑实际网页High配置；不能断言模型大小是唯一原因、9B普遍无能力或网页具独立裁判准确率。
完整答案、actual submission/source/schema/hash、原始回复、格式处理、比较表及来源恢复均保留。评价标记模型辅助来源审阅、非人工金标准，不计算两案准确率排名。{len(start['historical_files'])}历史文件原字节不变，算法/运行器没有改动；准备脚本的路径包装修正发生在首个模型提交前，单独记录，不混成受测方法修复。更新本地文档、实验索引和审阅包并完整性核验后停止；不补跑、不修改算法、不加法源、不重答、不提交或推送。
'''
(ROOT/'report-zh.txt').write_text(report,encoding='utf-8')
print(json.dumps({'root':str(ROOT),'answers':2,'decision':review['decision'],'format_normalizations':2},ensure_ascii=False))
