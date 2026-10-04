"""Import one frozen web result and record one source-grounded development review."""
import csv
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.contracts import validate

ROOT=Path('outputs/rules-verdict-v15-rule-supplement')
BASE=Path('outputs/rules-verdict-v14-web-direct')
read=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(path,value):
    with path.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')

freeze=read(ROOT/'freeze.json');audit=read(ROOT/'start-audit.json')
assert all(sha(p)==h for p,h in freeze['files'].items())
assert sha('scripts/prepare_v15_rule_supplement.py')==freeze['actual_preparation_script_sha256']
assert all(sha(p)==h for p,h in audit['historical_files'].items())
assert all(sha(p)==h for p,h in audit['preexisting_code'].items())
run=ROOT/'runs/1134266';task=ROOT/'tasks/1134266'
assert (run/'submitted-attachment.txt').read_bytes()==(run/'attachment-preview.txt').read_bytes()==(task/'case_1134266_task.txt').read_bytes()
raw=(run/'raw-response.txt').read_text();answer,end=json.JSONDecoder().raw_decode(raw.lstrip())
suffix=raw.lstrip()[end:];assert suffix.strip()=='END'
validate(answer,read(task/'schema.json'))
(run/'answer.json').write_text(raw.lstrip()[:end])
save(run/'format-check.json',{'raw_whole_reply_json':False,'format_status':'VALID_AFTER_EXPLICIT_END_SUFFIX_REMOVAL',
    'removed_suffix':suffix,'all_json_values_preserved':True,'attachment_citation_display_retained':True,
    'source_address_valid':True,'semantic_correctness_not_certified':True})
completion=read(run/'completion.json');start=read(run/'start.json');sent=read(run/'submission-time.json')['sent_at']
parse_time=lambda t:datetime.fromisoformat(t.replace('Z','+00:00'))
observed=(parse_time(completion['observed_complete_at'])-parse_time(sent)).total_seconds()
save(ROOT/'results.json',{'case':'1134266','method':'WEB_HIGH_DIRECT_PLUS_FROZEN_RULES','run_status':'OK','answer':answer,
    'baseline':str(BASE/'runs/1134266/answer.json'),'web_answers':1,'retries':0,'local_model_calls':0,'paid_api_calls':0,
    'displayed_model':'ChatGPT','exact_model':None,'displayed_mode':'High','conversation_url':completion['conversation_url'],
    'sent_at':sent,'observed_complete_at':completion['observed_complete_at'],
    'observed_submit_to_complete_upper_bound_seconds':observed,'displayed_thinking_seconds':158,
    'precise_generation_seconds':None,'input_tokens':None,'output_tokens':None,'peak_memory':None,
    'external_search_observed':False,'complete_attachment_verified':True,'internal_complete_read_not_observable':True,
    'same_original_case_and_law_and_answer_contract':True,'additional_source_ids_only':True})
source=read(task/'base-source.json');law=read(task/'base-law-package.json');added=read(ROOT/'rule-package.json')
cm={s['id']:s['text'] for s in source['segments']};lm={s['id']:s['text'] for s in law['law_segments']+added['law_segments']}
save(ROOT/'restored-final-sources.json',[{'ground':i+1,'point':g['point'],
    'case_sources':[{'id':s,'text':cm[s]} for s in g['case_refs']],
    'law_sources':[{'id':s,'text':lm[s]} for s in g['law_refs']]} for i,g in enumerate(answer['grounds'])])

review={
 'type':'ONE_CONCENTRATED_FINAL_SOURCE_REVIEW','reference_status':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
 'no_new_reference_labels_or_web_review':True,'baseline_review_preserved':str(BASE/'final-source-review.json'),
 'baseline_answer_not_gold':True,'baseline_review_revision_required':False,
 'source_checked_outside_model_active_citations':['p0002.s002','p0002.s005','p0002.s007','p0003.s001','p0003.s003','p0003.s007','p0004.s001'],
 'improvements':[
  {'item':'Separate vesting from rent-law consequences','baseline':'g3 repeated corporate-shell positions and missing amalgamation authority','new':'g2 preserves rights vesting; g3 applies supplied transfer authorities separately',
   'evidence':['p0002.s003','LAW:V15:GENERAL_RADIO:P6','LAW:V15:TELESOUND:PAR12'],'assessment':'Concrete supported improvement in explanation, not certification of final adjudication'},
  {'item':'Scope of Telesound','baseline':'No substantive treatment of the cited company-scheme view','new':'g3 expressly notes that Telesound reserves the Delhi eviction issue',
   'evidence':['LAW:V15:TELESOUND:PAR16'],'assessment':'Correctly retained reserved jurisdiction; does not promote prima facie view into final rent-law immunity'},
  {'item':'Scope of Hindustan Petroleum','baseline':'HP/compulsion argument not substantively handled','new':'g3 distinguishes the special statutory acquisition and vesting regime',
   'evidence':['p0003.s006','LAW:V15:HINDUSTAN_PETROLEUM:P15','LAW:V15:HINDUSTAN_PETROLEUM:P16'],'assessment':'Supported distinction; not a complete analysis of every route to statutory compulsion'},
  {'item':'No need for withheld target reasoning','baseline':'g3 pointed to absence of target-court reasoning when keeping characterization unresolved','new':'g3 offers a legal characterization on supplied authorities without requesting the withheld outcome',
   'evidence':['LAW:V15:GENERAL_RADIO:P6','LAW:V15:GENERAL_RADIO:P10'],'assessment':'Useful source-based application; cross-statute migration and target compulsion still deserve qualified explanation'}],
 'preserved_correct_parts':[
  {'item':'Registered 1966 lease and original American tenant','sources':['p0001.s003','p0002.s001'],'ground':1},
  {'item':'Sanctioned scheme transfers tenancy/occupancy rights to Indian company','sources':['p0002.s003'],'ground':2},
  {'item':'No-consent allegation not upgraded through added law or appellate disposition','sources':['p0002.s001','p0002.s004'],'ground':4},
  {'item':'Tribunal/High Court hierarchy retained in g4, not upgraded to target final adoption','sources':['p0002.s004'],'ground':4}],
 'remaining_omissions_or_disputes':[
  {'item':'Alternative ways to reduce equity and no direction specifically requiring amalgamation','sources':['p0003.s007','p0003.s008'],
   'finding':'Still not explicitly assessed. New answer contrasts equity reduction and alleged compulsion but does not articulate or evaluate the landlord alternative-modes counterargument.'},
  {'item':'AP principal holding migrated to Delhi transfer characterization','sources':['LAW:V15:GENERAL_RADIO:P6','LAW:V15:GENERAL_RADIO:P10'],
   'finding':'Delhi breadth is linked to Supreme Court description of Parasaram, so application has a basis; main AP statutory context is not stated in answer. g3 SUPPORTED is a qualified legal inference, not a source-explicit target adjudication.'},
  {'item':'RBI direction attribution','sources':['p0002.s002','p0002.s005','p0002.s006','p0003.s007'],
   'finding':'g3 calls equity reduction target narration, although p0002.s006 continues counsel submission and p0002.s002 narrates a defense. Both sides refer to equity reduction, but no independent directive or adopted finding is supplied. This should be described as a common premise of submissions, not a court-established directive.'},
  {'item':'Approval date versus effective vesting date','sources':['p0002.s003'],
   'finding':'g2 names the amalgamation by 31 December 1981; original text dates sanction, not a separately established vesting date. Same precision issue was present in baseline. No withheld effective date is imported.'},
  {'item':'Overly narrow formulation of evidence sufficiency','sources':['p0002.s001','p0002.s004'],
   'finding':'reason demands an adopted finding for absence of consent. The task does not universally require a preexisting court finding: evidence and lawful inference could suffice. Here allowed material still does not separately settle consent; UNDETERMINED is defensible, its stated criterion is too narrow.'},
  {'item':'Rent Controller dismissal and corporate-shell argument','sources':['p0002.s004','p0003.s001','p0003.s003'],
   'finding':'ARC initial dismissal no longer stated explicitly; corporate-shell defense handled only indirectly by Telesound and transfer analysis. Do not claim every decisive opposing contention has been fully addressed.'}],
 'confirmed_new_severe_source_reversals':[],
 'no_cross_case_fact_import_confirmed':True,
 'internal_consistency':'g3 supported legal transfer, g4 unresolved absence of consent and UNDETERMINED conclusion are compatible; no supported/refuted polarity contradiction identified.',
 'fact_gaps':['Actual landlord written consent or its absence is not independently settled in allowed record.','Actual RBI directive, alternative compliance choices and mandatory merger status are not independently verified by added authorities.'],
 'law_gaps':['No full historical FERA s29/RBI instrument added.','No complete proof-burden framework added; do not manufacture absent-consent facts.'],
 'benefit_boundary':'Rules improved legal distinctions and applicability explanation, but not a fully complete or independently correct verdict. Single targeted source addition also changes length/attention; summaries and excerpts effects not isolated.',
 'decision':'CONTINUE_SOURCE_GROUNDED_RULE_EXTRACTION_AND_APPLICATION',
 'decision_zh':'补充规则带来具体且可核验的法律分析增益，保留规则提取与应用方向；双方论点处理仍不完整，本案不继续返工。',
 'no_automatic_next_round':True
}
save(ROOT/'final-source-review.json',review)
save(ROOT/'decision.json',{k:review[k] for k in ['decision','decision_zh','benefit_boundary','no_automatic_next_round']})
baseline=read(BASE/'runs/1134266/answer.json');baseline_run=read(BASE/'results.json')['runs'][1]
rows=[
 {'condition':'V14 web High D','case':'1134266','run_status':'OK','outcome':baseline['outcome'],'complete_answers':1,
  'legal_transfer':'UNRESOLVED; no amalgamation-specific law provided','opposition':'Corporate-shell argument retained, HP/FERA/alternative-modes omitted',
  'consent':'UNRESOLVED; allegation not upgraded','legal_scope':'No relevant merger rules to apply','source_errors':'No comparable serious source reversals confirmed; approval/effective-date precision issue',
  'displayed_thinking_seconds':49,'generation_seconds':None,'observed_completion_upper_bound_seconds':baseline_run['observed_submit_to_completion_upper_bound_seconds'],
  'input_tokens':None,'output_tokens':None,'new_calls_this_round':0},
 {'condition':'V15 web High D + three authorities','case':'1134266','run_status':'OK','outcome':answer['outcome'],'complete_answers':1,
  'legal_transfer':'SUPPORTED as qualified legal inference; statutory migration not fully explained','opposition':'HP special regime and Telesound reservation correctly distinguished; landlord alternative-modes argument still omitted',
  'consent':'UNRESOLVED; added law does not create absence of consent','legal_scope':'Concrete new distinctions; AP/Delhi boundary needs more explicit treatment',
  'source_errors':'No new severe reversal confirmed; RBI common submission premise called narration; existing date precision retained',
  'displayed_thinking_seconds':158,'generation_seconds':None,'observed_completion_upper_bound_seconds':observed,
  'input_tokens':None,'output_tokens':None,'new_calls_this_round':1}]
save(ROOT/'comparison-table.json',rows)
with (ROOT/'comparison-table.csv').open('x',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
(ROOT/'final-answer-slots.md').write_text('# V15 完整网页回答\n\n对话：'+completion['conversation_url']+'\n\n仅移除闭合JSON后的独立END。所有JSON字段及附件引用显示文本保留；不是人工gold。\n\n```json\n'+(run/'answer.json').read_text()+'\n```\n\n基线：../rules-verdict-v14-web-direct/runs/1134266/answer.json\n')
save(ROOT/'preservation-check.json',{'historical_files_unchanged':len(audit['historical_files']),'preexisting_code_unchanged':len(audit['preexisting_code']),
    'frozen_files_verified':len(freeze['files']),'base_case_law_examples_requirements_preserved':True,
    'semantic_output_repairs':0,'format_suffix_only':True})
save(ROOT/'stop.json',{'reason':'ONE_NEW_WEB_ANSWER_AND_ONE_CONCENTRATED_SOURCE_REVIEW_COMPLETE','web_answers':1,
    'local_calls':0,'paid_api_calls':0,'retries':0,'new_extractions':0,'no_commit_push_next_round':True})
(ROOT/'report-zh.txt').write_text(f'''V15：1134266补充有来源规则后的直接法律回答

投入决定：保留有来源的规则提取与应用方向。三份相关法源让网页答案产生具体法律分析增益：区分公司合并的权利转归与租赁法后果，识别Telesound保留的腾退问题，区分Hindustan Petroleum依赖的专门法保护。没有确认同等严重新增来源反写。但它仍未充分处理双方主要论点，不能称为完整法律回答已经正确；本案不继续修prompt或追问。

固定范围与材料
仅1134266，V14网页High直接回答保持为基线，不重新生成。案情、原法律包、问题、两个教学示例和最终合同完整保留；只插入冻结的三份早期判例规则与七个原文片段，Schema仅扩展law_refs地址枚举。首次生成前冻结源码、材料、选择理由、评价和停止规则。没有旧答案、参考判断、错误清单、特定目标段落提示或目标最终理由。新的独立网页High对话，非Pro，网页没有本地逐token约束。界面只显示ChatGPT/High，具体型号不明；内部知识、文件读取和采样无法独立观测。

规则包包含General Radio（最高法院1986，主要适用安得拉邦租赁法，并描述Delhi Parasaram先例）、Hindustan Petroleum（最高法院1988，专门Esso收购法、通知、s396合并及孟买s15A保护）、Telesound（德里高院1980，1983为报告年份，公司方案批准、prima facie意见及明确保留的租赁审理权限）。不把法院批准等同房东许可，不创造一般强制转移豁免，不提供当前案专用适用结论。General Radio与HP的片段逐字来自PDF提取；HP扫描OCR原样保存。Telesound直连403，改用web工具已读取的原判决文字：第12段明确标为不连续完整句摘录，第16段完整保留。Delhi法条官方PDF下载超时，未添加猜测文本；共检查4个不同文档，使用3个，在最多5份范围内停止。获取失败与本地准备阶段的空白锚点修正均发生于冻结/模型提交前，保留记录；不是受测回答重试。没有启动自动检索算法评价或跨案规则归纳。

具体变化
V14 g3因缺少合并法源保留定性未知，主要复述corporate-shell争议。V15 g3引用General Radio的转移分析及其Delhi先例描述，给出有依据的转移定性推论，并正确指出Telesound保留Delhi腾退问题、HP依赖不同专门法承继。其法律依据确实来自新包，不是单纯引用ID增加。V15不再把缺少目标法院最终理由当作无法分析该问题的理由。这些是可核验的分析进步，但跨AP/Delhi法条迁移只简略提及，不能把SUPPORTED视为已由目标法院判定。
两份outcome均UNDETERMINED。V15仍保留1966已登记租赁、American/Indian公司的正确关系、31.12.1981法院批准及租赁权转归；没有从新判例的无同意事实推导本案无同意，也没有把批准等同房东同意。g4保留Tribunal/High Court层级，原Rent Controller驳回在本次回答未展开。g3支持转移定性、g4无同意未决，与最终标签没有极性矛盾。

仍存在的问题
最重要的遗漏仍是p0003.s007：房东主张降低股本可用其他路径，RBI并未要求具体合并。答案只区分股本要求与租户声称的合并强制，没有明确比较这一反驳；不能宣称“双方论点已完整处理”。p0002.s006承接租户律师陈述、p0002.s002记录其抗辩，双方都提股本要求，但无独立RBI命令；g3称其target narration，表述应限于双方陈述的共同前提，而非法院已认定命令。g2把合并称31 December 1981，原文明确的是批准日，不能确定单独生效日；此精度问题基线已有。g3SUPPORTED是法律推论，仍需说明主案AP法与Delhi宽泛转移条款为何可比较。reason以没有adopted finding说明无同意未定，条件过紧：一般可从充分证据作有依据分析，并非必须已有法院认定；但本次允许材料仍未独立解决同意，保留未决有依据。
真正未提供的是本案书面同意或其不存在的充分事实、实际RBI命令及具体强制合并状态；本包也未新增完整历史FERA文本或举证责任规则。法律材料可以帮助定性，不能制造这些事实。未读取被排除的目标最终理由，也不要求恢复历史裁判。

评价与成本
一次集中来源审阅，包括答案未引用的p0003.s007等主要反对内容，无新gold、整案重标、网页复核或审阅agent；标记为模型辅助来源审阅，非人工金标准。一次新网页回答、本地生成0、API0、重试0、抽取0。新附件53517字符，预览与实际提交逐字一致。原始回复保留，只有完整JSON后的独立END被移除，附件引用显示文字仍在reason。格式及ID通过现有校验不代表语义正确。
界面思考时长158秒，基线49秒；这是可见思考阶段增加109秒，不是精确总推理耗时。发送至首次确认完成的观察上界{observed:.1f}秒，含观察间隔；输入输出tokens、精确生成时间和峰值内存不可得，保持null。不能声称等输入成本或纯规则语义因果收益：规则摘要、原文、输入长度和注意力变化共同加入，单次旧案开发观察没有排除生成波动。

交付与停止
完整答案、原始回复、实际任务/Schema、三份规则及原文、来源URL/哈希、逐项审阅和比较表均保存。原5041个历史输出与既有方法代码原字节不变；V14基线不改，不把新增法源回填旧实验。修订文档、实验索引和本地审阅包，核验发布清单后结束；不再搜索、重答、重抽、改算法、提交或推送。结果支持继续考虑规则提取和适用分析组件，尚未验证自动取得规则、完整裁判可靠性或跨案泛化。
对话：{completion['conversation_url']}
''')
print(json.dumps({'web_answers':1,'status':'OK','outcome':answer['outcome'],'decision':review['decision'],'observed_upper_bound_seconds':observed},ensure_ascii=False))
