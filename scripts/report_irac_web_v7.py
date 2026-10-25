"""One concentrated source review and local V7 report; no model calls."""
import csv, io
from irac_web_v7 import *

def main():
 rows=[]; answers=['# V7 Complete Raw Web Answers and Proposals\n\nExact model version unavailable; the UI showed High in temporary, nonpersonalized chats. Six independent submissions, without correction or retries.\n']
 for c,s in ORDER:
  out=R/'runs'/c/s; run=read(out/'run.json');res=read(out/'result.json');man=read(R/'tasks'/c/s/'manifest.json')
  rows.append({'case':c,'stage':s,'status':res['run_status'],'task_bytes':man['bytes'],'reply_bytes':len((out/'raw-response.txt').read_bytes()),'observed_seconds':run['observed_elapsed_seconds'],'exact_tokens':None,'exact_generation_seconds':None,'url':run['url']})
  answers.append('\n## '+c+' '+s+'\n\n[Web conversation]('+run['url']+') (temporary conversation URLs may expire; local originals are authoritative).\n\n```json\n'+(out/'raw-response.txt').read_text()+'\n```\n')
 (R/'answers.md').write_text(''.join(answers))
 save(R/'costs.json',{'calls':rows,'generations':6,'retries':0,'local_inference':0,'paid_api':0,'downloaded_json':False,'capture':'Verbatim rendered code text; 188721101 A verbatim paragraph text. No follow-up to request a file.','observed_seconds_total':sum(x['observed_seconds'] for x in rows),'warning':'Elapsed submission-to-observed-completion includes browser, queue, polling and capture delay; not precise inference time or comparable to V6 local timing.'})
 with (R/'call-costs.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 review={'role':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD','review_passes':1,'reviewed_after_all_six_completed':True,'additional_model_calls':0,'scope':'Four web final answers versus four V6 final answers; P only for decisive error propagation. All allowed decisive sources including uncited opposition checked.','historical_verdict_not_gold':True,'cases':[]}
 def finding(id,refs,check,A,B,P,judgment):
  return dict(id=id,source_refs=refs,source_requirement=check,web_A=A,web_B=B,proposal_trace=P,judgment=judgment)
 review['cases'].append({'case':'112400','pair':'CLOSE_NO_IMPORTANT_INCREMENTAL_B_GAIN','findings':[
  finding('112-residential-purpose',['IK-112400:L123:span1','IK-112400:L124:restored-v2'],'租赁日期与部位有记录，原出租用途没有明确记载。','C01未决；明确区分后来自住用途与原出租用途。','相同，未将租约原件假装已取得。','P C01同样区分，不能因B一致便证明帮助来自P；A已经独立做到。','V6 A/B的明确无依据肯定在本轮A/B均消失。'),
  finding('112-accommodation-quantifier',['IK-112400:L137:context-v4','IK-112400:L138:context-v4','IK-112400:L139:restored-v2','IK-112400:L140:restored-v2'],'发回后现住房不适宜已有积极认定，不能扩大为无任何其他适宜住所。','保留报告日期、家庭成员及地位，C06未决且理由一致。','同样保留局部认定和全称命题缺口；未再编造固定五人。','P records8、C06及局部限制准确保持这一差别；A不靠P也正确。','较V6两组改进；A不再出现C06支持/理由未决矛盾。'),
  finding('112-alternative-route',['IK-112400:L124:restored-v2','IK-18143401:L41:historical-e'],'本人路径与家属依赖路径择一，不能把家属依赖未知用于封锁本人路径。','C03支持限于本人拟居住路径，明确未证明善意或实际入住。','C03明确OR关系，未被P SELF未决机械封锁。','P SELF和FAMILY较保守，要求未来意图独立确认；B回读原文调整，未视为必须服从的前提。','V6 B的择一路径错误消失；不把A/B支持标签等同于完整法定事实已证明。'),
  finding('112-prior-stage',['IK-112400:L127:restored-v2','IK-112400:L130:span6','IK-112400:L139:restored-v2'],'先前否定善意及后续不适宜报告均须保留，不能虚构11个月法定否定规则或上诉必须维持。','C02阶段限定REFUTED；反对理由实际展示有利房东的后续认定。','与A近似；把P C02未决改成阶段限定REFUTED，并说明预测假设。','P已保留相反材料，C02未决可解释为目标阶段判断；B称其未充分体现先前认定，只是另一种汇总视角，不足以判P法律错误。','未发现旧式无依据强制驳回。P与B状态差异保留解释争议，不以更确定标签奖励B。'),
  finding('112-organization',['IK-112400:L123:span1','IK-112400:L124:restored-v2','IK-112400:L138:context-v4'],'法院阶段变化不是新的租赁安排；文书记载的事实不等于原件已核验。','最终统一b1，没有按条件造多笔交易。','统一b1，并明确P的UNKNOWN不否定已记录的租赁、所有权和发回。','P8条记录、1安排；比V6按后续认定拆成3安排清楚。records1/7的UNKNOWN仍把文书记载与原件未核验揉在一起，属接口标记粗糙；文本未丢事实。','B能纠正中间标记的过度保留，但A本已保留同样事实；没有重要净改善证据。')],
 'remaining_limits':['原出租用途及其他住所情况在允许材料中未完整说明。','法律包只含历史条文片段，缺Explanation全文、进一步适用及上诉审查/举证标准。','目标高院最终接受情况是本来排除的待判断结果，不能把拿不到最终答案本身当作需要补回的输入；可记录先前认定的效力规则不足。','P UNKNOWN、材料支持与条件最终成立的汇总口径仍有歧义；本轮不修改。'],
 'new_material_error':'本次限定的决定性审阅未确认网页A/B出现与V6同等严重的新来源误读；不等于穷尽验证。',
 'decision':'网页A已完成主要纠错；B更长并主动调整P，但缺乏足以要求额外阶段的重要收益。'})
 review['cases'].append({'case':'188721101','pair':'MODEST_ORGANIZATIONAL_B_GAIN_NOT_ESTABLISHED_FINAL_ANSWER_NET_GAIN','findings':[
  finding('188-date',['IK-188721101:L72:restored-v2'],'1987年是房东主张的起租日，不是经法院确认的处分日；先租后处分可支持条件化时间推论。','C01未决且明确1987起租而非处分；若确认后来处分则可能满足阈值。','同样处理弟弟及父亲时间，未虚构法院日期认定。','P C01保留先后推论和争议；父亲未单列时间已在coverage说明，B补评未决而未补造事实。','V6 A/B日期错读及A虚构法院认定消失。'),
  finding('188-employment-control',['IK-188721101:L80:restored-v2','IK-188721101:L81:restored-v2'],'邻居称弟弟经营而非租户；兄弟承认经营和钥匙，工资只是证言且凭证未证明。','条件及opposition保留全部反论，不再把工资支付当事实。','同样保留，并明确工资凭证未证明不直接证明次租金。','P records6/7/8分别保留证言、承认和凭证缺口；R7混合证言与承认但文字区分，R8用UNKNOWN保存已记载的举证状况仍粗糙。','V6重要遗漏/强化工资证言明显减少。A opposition.response中“经营、持钥匙和工资凭单未获证明”存在语法歧义，但前后明确承认经营与钥匙；记录措辞风险，不升级为确定的相反事实判断。'),
  finding('188-consent',['IK-188721101:L73:restored-v2','LAW:S02:DRC14:1b'],'起诉许可不同于房东同意处分；缺少同意资料不是无同意事实，也不自动产生驳回规则。','C05明确区分Slum Authority许可；无旧版倒置同意主体或estoppel。','C05保持资料缺口；reason明确未决不等于虚假、不创设自动驳回。','P有针对两笔安排的分别待定标记；无人工改写。','V6 A/B相关条件误用消失；B未明确重复Slum许可区别，但未将其用作同意，非决定性遗漏。'),
  finding('188-prior-license',['IK-188721101:L83:restored-v2','IK-188721101:L84:restored-v2','IK-190902:L107','IK-190902:L110','IK-190902:L112'],'原审可撤销许可认定是现有相反司法判断，尚非目标上诉接受；家属关系不构成给定法源中的当然豁免。','三个处分路径分别处理，C02/3/4阶段限定REFUTED、C06支持；承认上诉可能推翻并保留相反证据。','C02未决、C03/4阶段限定反驳、C06支持；家属不当然豁免，预测依赖原审主要判断维持的假设。','P对未证明转租与积极否定assignment/parting作区别，B沿用但有限定。','C02 A/B不同不直接判优劣：A依积极许可推反驳，B突出未证明与存在反论。两者需读解释，单标签不能当成统一法律真值。'),
  finding('188-separate-arrangements',['IK-188721101:L72:restored-v2','IK-188721101:L73:restored-v2','IK-188721101:L74:restored-v2'],'父亲先前安排与弟弟后续使用须分开；6号铺及另一营业地点不等于15号铺的处分。','opposition和gaps保留父亲、6号铺柜台迁移及独立证明要求；未逐条件展开父亲。','b1弟弟、b2父亲分开列条件；父亲assignment缺口写在b2/C04解释，未另列C03；不借弟弟认定填父亲。','P9记录、3安排（弟弟、父亲、6号铺背景），只对前两者作处分条件分析。B父亲分项确与P组织对应，构成可追溯的组织收益。','比V6遗漏明显改善。B比网页A更细致，但A已识别同样决定性边界；没有发现B找回A漏掉的决定性原文。'),
  finding('188-final-prediction',['IK-188721101:L83:restored-v2','LAW:S02:DRC14:1b'],'预测须说明依赖先前认定的假设，不能把阶段认定升级最终判决。','DENY针对房东上诉，说明若权利转移/时间/无同意获确认可能改变。','DENY针对恢复占有请求，binding和reason持续保留第38条上诉阶段；不是新增请求或确定性程序裁判。','P未代替完整法律判断；B仍有原文访问。','没有用共同DENY判正确。未获目标最终理由，不能验证历史胜败准确率。')],
 'remaining_limits':['书面同意具体情况、父亲安排详情及权利/控制争议在允许材料中未获最终解决。','提供了转租、让与、交出占有标准，但未覆盖完整举证推定、事实评价及上诉审查标准。','姓名两种拼写已被双方保留，没有为此封锁全案；不得据拼写独立制造新交易。','已保留相反事实并不说明预测假设必然成立。'],
 'new_material_error':'限定审阅未确认B新增同等严重错误；A一处中文并列句歧义与两组汇总状态口径保留为限制。',
 'decision':'P使父亲/弟弟逐安排分析更清楚，但网页A本已覆盖关键反论。值得保留为可选组织组件，现有净收益不足以强制使用。'})
 review['overall_decision']='PRIORITIZE_WEB_DIRECT_A_KEEP_P_OPTIONAL'
 review['causal_limits']=['两案旧材料开发诊断；普通High具体型号不可得。','配置整体不同：内部推理、采样、Schema机制、输出长度和语言不同；不能只归因模型规模。','B两个调用、更多输入，A一个调用；非同计算预算。','未给B离线checks，不验证检查提示/GNN效果。','P与B内容对应仅证明可追踪，不能排除B回读原文得到同样结论。']
 save(R/'final-source-review.json',review)
 # Quote anchors taken from the actual model-visible source, not target excluded judgment.
 anchors=[]
 for c in ['112400','188721101']:
  txt=(R/'tasks'/c/'A/prompt.txt').read_text();src=json.loads(txt.split('COMPLETE ALLOWED CASE MATERIAL:\n\n')[1].split('\n\nTASK:')[0]);anchors.append(src)
 save(R/'review-source-anchors.json',anchors)
 pairs=[]
 for case in review['cases']:
  c=case['case'];r={x['stage']:x for x in rows if x['case']==c}
  pairs.append({'case':c,'A_status':'OK','P_status':'OK','B_status':'OK','A_outcome':'PREDICT_DENY','B_outcome':'PREDICT_DENY','pair_result':case['pair'],'source_errors_vs_v6':'CLEAR_REDUCTION_IN_IDENTIFIED_ERRORS','A_task_bytes':r['A']['task_bytes'],'P_plus_B_task_bytes':r['P']['task_bytes']+r['B']['task_bytes'],'A_observed_seconds':r['A']['observed_seconds'],'P_plus_B_observed_seconds':r['P']['observed_seconds']+r['B']['observed_seconds'],'decision':case['decision']})
 save(R/'case-comparison.json',pairs)
 with (R/'case-comparison.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=list(pairs[0]));w.writeheader();w.writerows(pairs)
 reg=read(R/'registration.json');old={**reg['historical_hashes'],**reg['old_code_hashes']};bad=[p for p,v in old.items() if h(p)!=v];assert not bad
 cfg=read(R/'freeze/config.json');assert h('scripts/irac_web_v7.py')==cfg['transport_code_hash']
 assert all(h(p)==v for p,v in cfg['task_hashes'].items());assert all(h(p)==v for p,v in cfg['material_hashes'].items())
 save(R/'preservation-after.json',{'passed':True,'V6_files':len(reg['historical_hashes']),'old_code_files':len(reg['old_code_hashes']),'changed':bad,'frozen_task_hashes_unchanged':True,'material_hashes_unchanged':True,'transport_code_unchanged':True})
 save(R/'progress.json',{'status':'COMPLETED_SIX_CALLS_ONE_SOURCE_REVIEW_STOPPED','slots':[{'case':x['case'],'stage':x['stage'],'status':x['status'],'url':x['url']} for x in rows],'no_more_calls':True})
 report='''IRAC V7: browser A/B comparison with V6 interfaces and materials

Provisional decision: prefer browser direct answer A; keep P optional for organization. The browser configuration substantially reduces V6's confirmed source misreadings/decisive omissions in both cases, but A independently delivers most gains. B is materially similar to A for112400. For188721101, B separates father/brother arrangements more explicitly without recovering decisive original content wholly absent from A. This does not justify mandatory extra P calls/longer final input per case, prove general structural ineffectiveness, or validate historical judgment accuracy.

Six browser answers completed: two readable P proposals and four finals, no failures/retries/extra browser reviews/local inference. Six fresh temporary chats separately handled A/P/B. The UI showed High and no personalization, explicitly without memory/plugins/custom instructions. Exact model was unavailable, not labeled GPT-6. Tasks excluded old answers, references, and program checks; no new authorities or target final reasons were added.

112400: old9B treated lease existence as established residential use, expanded unsuitable current housing into no alternative suitable accommodation, and let unknown family dependence block the personal alternative route in B. Browser A/B avoid these errors. Both retain the trial finding against bona fide need and the favorable1970 remand report, explaining that eleven months is not an automatic statutory disqualification. C06 remains unresolved with consistent reasons: gaps concern residential letting and alternative-accommodation scope, not loss of known ownership/personal routes.

P organizes one tenancy arrangement without splitting later findings into transactions and largely retains opposing evidence. But it marks tenancy/ownership/remand records UNKNOWN, confusing recorded content with unverified originals. B rereads sources and preserves these facts, changing P's C02 from unresolved to stage-limited rebuttal. P already retained early adverse/later contrary findings, so the status change alone is not a corrected legal error. A has the same core analysis; B shows no important extra net benefit.

188721101: both browser answers identify1987 as the landlord's alleged tenancy start, not a judicially confirmed transfer date, while allowing a conditional lease-before-transfer inference. Both preserve neighbors' brother-not-tenant account, admitted business/key possession, unproved wage vouchers, shop6/counter, and the father's earlier arrangement. Wage testimony is not promoted to proven payment, and kinship is not an automatic statutory exemption. A explicitly distinguishes Slum Authority permission to sue from landlord consent to transfer; B omits that distinction but does not misuse the permission.

Both retain the appellate status of the trial court's revocable-permission finding and specific written-consent gaps. Reasons condition predictions on the trial findings surviving appeal instead of claiming unknown consent necessarily blocks relief. P creates brother-use, earlier-father, and shop6-background arrangements. B lists b1/b2 conditions and assesses father timing as unresolved from the same sources. This is traceable organizational benefit, but A already explains that brother evidence cannot prove the father's arrangement. No decisive A omission is shown corrected by B's longer analysis.

Remaining disputes:188721101 A's opposition.response ambiguously coordinates unproved business, key possession, and wage vouchers. Earlier conditions/opposition/reasons explicitly acknowledge admitted business/keys, so this wording alone is not a confirmed factual reversal. A labels subletting stage-limited REFUTED; B uses UNRESOLVED. Both retain trial permission/opposing evidence; A infers rebuttal from positive permission, B emphasizes unproved facts/pending appellate assessment. Labels alone cannot decide correctness. P still has overly broad UNKNOWN states and mixed testimony/admissions; these were not repaired through further runs.

Final answers are more faithful/complete than V6 through specific error reduction and restored counterarguments, not uniform DENY, complete JSON, or more unknowns. Bounded review found no new decisive browser error comparable to V6, but did not exhaust every semantic issue. Both legal packages lack fuller burden/appellate-review standards.112400 lacks residential-use/alternative-housing details;188721101 lacks father details, written consent, and final factual assessment of control. The excluded target court's ultimate acceptance is the analytical target, not information to restore just to eliminate uncertainty.

Comparison boundaries: two exposed development cases use complete permitted material, not complete unmasked judgments. V6's historical-reconstruction/later-source limits remain. Browser generation lacks local token-level schema constraints; exact model, sampling, reasoning, context handling, and tokens are unavailable, and language/length differ. Only overall configuration improvement is supported, not parameter-size or single-field causality. B can reread sources, so all correct content is not attributable to P. Program-check blocks/GNN were not evaluated.

Per-call costs: seconds are submission-to-observed-completion intervals including queueing, browser, polling, and retrieval delays, not exact generation times.

|Case|Stage|Status|Full task UTF-8 bytes|Raw answer bytes|Observed seconds|
|---|---|---|---:|---:|---:|
'''
 for x in rows:report+=f"|{x['case']}|{x['stage']}|{x['status']}|{x['task_bytes']}|{x['reply_bytes']}|{x['observed_seconds']:.2f}|\n"
 for x in pairs:report+=f"\n{x['case']}: A uses one call, {x['A_task_bytes']:,} task bytes and an observed interval of {x['A_observed_seconds']:.2f} seconds; P+B uses two calls, {x['P_plus_B_task_bytes']:,} cumulative task bytes and {x['P_plus_B_observed_seconds']:.2f} seconds. Cumulative bytes include repeated case/legal materials and do not measure unique information.\n"
 report+='''
The browser produced no download links; complete rendered JSON was saved directly. Case188721101 A appeared as ordinary paragraphs. Changing the read location did not regenerate it; none of six replies needed fence removal or content repair. Upload success, verbatim assembly, and complete answers are observable; hidden browser retrieval/context trimming is not independently auditable. No external search, other-chat citations, or attachment-reading failure was observed. This is not proof of internal word-for-word reading.

Engineering and preservation: A/P prompts/schema equal V6 verbatim. B only replaces empty intermediate material with this run's raw P, with dynamic hashes saved after P completion. Both offline imports were OK without isolated records, not semantic certification; checks never entered B. All158 V6 files and27 old source hashes matched; existing workspace changes were not overwritten. Tasks, original replies, URLs, settings, and one consolidated source review are in the new directory. Temporary-chat URLs may expire; complete local originals are the durable evidence. Screenshots/browser pages stay local, excluded from publication.

File index: answers.md contains six raw outputs; case-comparison.csv/json contains case results; final-source-review.json/review-source-anchors.json contain review/allowed originals; call-costs.csv/costs.json contain costs; tasks/runs retain actual submissions, schema, originals, imports, and offline checks. freeze/config.json is the pre-run freeze, B-assembly-validation.json the dynamic assembly check, and preservation-after.json the historical-preservation check.

Stop after this batch. Do not add C, legal authorities, regeneration, training, SEALED access, commit, or GitHub push. Any later expansion of same-configuration direct answers or bounded legal-source supplementation requires the user's decision; it is not executed here.
'''
 (R/'report-zh.txt').write_text(report)
 # Repository metadata; no commit/push.
 summary='Six independent ordinary High temporary conversations completed, yielding two readable proposals and four final answers without retries. Web A/B reduce V6 source misreadings and omissions; B is close to A on 112400, while 188721101 gains arrangement-level organization without confirmed important net benefit. Historical decision: prefer web A, with P optional. One model-assisted source review, not human gold, on exposed development cases. No added authorities, executor changes, local inference or pushes.'
 policy=read('docs/repository-artifacts.json');policy['code_review_files'].append('scripts/report_irac_web_v7.py') if 'scripts/report_irac_web_v7.py' not in policy['code_review_files'] else None
 policy['current_review']={'contract_version':2,'review_kind':'IRAC_WEB_CROSSMODEL_V7_COMPLETED','title':'IRAC V7: Web A/B Comparison with Shared Interfaces and Materials','report':str(R/'report-zh.txt'),'summary':summary,'status':'COMPLETED_SIX_WEB_CALLS_ONE_REVIEW_STOPPED_LOCAL_ONLY','links':[{'label':label,'path':str(R/p)} for label,p in [('Report','report-zh.txt'),('Complete web answers and P','answers.md'),('Per-case comparison','case-comparison.csv'),('Concentrated source review','final-source-review.json'),('Permitted-source review anchors','review-source-anchors.json'),('Costs and conversation URLs','call-costs.csv'),('Frozen configuration','freeze/config.json'),('Dynamic B assembly','B-assembly-validation.json'),('Historical preservation','preservation-after.json')]],'review_request':"Read-only review of V7 web A/P/B with shared materials and the historical V6 comparator. Separate overall configuration improvement from P's incremental benefit. Check sources and key objections; common DENY outputs or valid JSON do not establish legal correctness. Examine 112400 over-inferences, the personal-use alternative and later report; and 188721101 lease date, wage receipts, neighbors, father/brother arrangements, written consent and trial-court effect. Preserve interpretive uncertainty in P/B C02 status differences. Browser records remain local and excluded from publication. No additional experiments, corrective reruns or publication are authorized."}
 policy['publication_authorization']['current_irac_web_v7_hold']='Explicit current user: local prepare/manifest/verify only; no commit/push.'
 save('docs/repository-artifacts.json',policy)
 cat=read('docs/EXPERIMENTS.json');assert not any(x['id']=='irac-web-crossmodel-v7' for x in cat['experiments']);cat['experiments'].append({'id':'irac-web-crossmodel-v7','role':'two_exposed_cases_same_information_web_configuration_AB_development','report':str(R/'report-zh.txt'),'note':summary});save('docs/EXPERIMENTS.json',cat)
 p=Path('README.md');old=p.read_text();old=old.replace('# Current work: IRAC V6 two-case comparison complete','# Historical: IRAC V6 two-case comparison complete',1);p.write_text('# Current work: IRAC V7 web A/B comparison complete\n\n'+summary+' See [report]('+str(R/'report-zh.txt')+'), [complete answers]('+str(R/'answers.md')+'), [per-case comparison]('+str(R/'case-comparison.csv')+')。\n\n'+old)
 p=Path('docs/CHANGELOG.md');p.write_text('## 2026-10-08 IRAC V7: Two-Case Web Comparison with Shared Materials\n\n'+summary+" The six submitted tasks retain V6 interfaces; B adds only this run's P. Exact tokens and inference time are unavailable; observed intervals are reported separately. Screenshots and account UI records are not published.\n\n"+p.read_text())
 print('V7 report, source review, costs and local metadata completed')
if __name__=='__main__':main()
