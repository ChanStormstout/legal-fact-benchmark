"""One concentrated source review and local V7 report; no model calls."""
import csv, io
from irac_web_v7 import *

def main():
 rows=[]; answers=['# V7完整网页原始回答与提议\n\n模型具体版本不可得；界面High，临时聊天且不个性化。六次独立提交，未纠错或重试。\n']
 for c,s in ORDER:
  out=R/'runs'/c/s; run=read(out/'run.json');res=read(out/'result.json');man=read(R/'tasks'/c/s/'manifest.json')
  rows.append({'case':c,'stage':s,'status':res['run_status'],'task_bytes':man['bytes'],'reply_bytes':len((out/'raw-response.txt').read_bytes()),'observed_seconds':run['observed_elapsed_seconds'],'exact_tokens':None,'exact_generation_seconds':None,'url':run['url']})
  answers.append('\n## '+c+' '+s+'\n\n[网页对话]('+run['url']+')（临时对话地址不保证长期可用，以本地原文为准）。\n\n```json\n'+(out/'raw-response.txt').read_text()+'\n```\n')
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
 report='''IRAC V7：V6同接口、同材料的网页A/B对照

暂定决定：优先网页直接回答A，P作为可选组织组件。网页配置在两案中都明显减少了V6的已确认来源误读和决定性遗漏；但网页A已独立做到大部分改进。112400的B与A实质接近，188721101的B更明确地分别分析父亲和弟弟安排，却没有找回A完全遗漏的决定性原文。尚不足以要求每案增加一次P生成及更长的最终输入。这个投入选择不证明结构化方法普遍无效，也不验证历史判决准确率。

实际完成6次网页回答，2份P、4份最终回答全部可读取，失败0、重试0、额外网页复核0、本地推理0。A/P/B分别使用6个新的临时对话；界面显示High及“不个性化”，明确说明不使用记忆、插件、自定义指令。未显示具体模型型号，记为不可得，没有写成GPT-6。任务不含旧答案、参考审阅或程序检查；没有新增法源或目标最终理由。

112400：旧9B将租约存在当作住宅用途已确认，将现住房不适宜扩大为没有其他适宜住所；B又让家属依赖未知封锁本人择一路线。网页A/B均避免这些错误，保留原审否定善意需要与1970年发回报告有利于房东的认定，说明11个月不是给定法条中的自动否定规则。C06均为未决，解释与结论一致；未知对应住宅出租用途、其他住所范围等具体缺口，已知所有权和本人路径没有一起丢掉。

P将整案整理为一个租赁安排，未再把后续法院认定拆成交易；正反材料基本齐全。不过，租赁/所有权及发回程序的记录标成UNKNOWN，仍把文书记载与原件未核验混在状态字段中。B回读来源后明确保留这些事实，并将P的C02未决改成阶段限定的反驳。P已经保留早期不利认定与后续相反依据，不能仅凭这个状态改变宣称B纠正了法律错误。A本来就有相同核心分析，B未显示重要额外净收益。

188721101：网页A/B均将1987年识别为房东所称起租日，不再虚构法院确认处分发生于当天；保留先租后处分可形成条件化时间推论。两者都保留邻居所说“弟弟经营而非租户”、兄弟承认经营和持钥匙、工资凭证未证明，以及6号铺/柜台和父亲先前安排。工资证言没有再被强化成已证明的工资支付，家属关系也没有被当作给定法源中的当然豁免。A另明确区分Slum Authority起诉许可与房东同意处分；B未重复此区分，但也未错误使用该许可。

两者对原审可撤销许可的判断均保留上诉地位，书面同意仍为具体资料缺口。理由明确交代预测依赖原审核心认定维持的假设，不再说“同意未知必然阻止授予”。P形成弟弟使用、父亲先前安排、6号铺背景三个安排；B明确列b1/b2条件，父亲时间由B根据同一原文补评未决。这是可追溯的组织收益，但网页A在反论和缺口中已经说明父亲安排不能借弟弟证据证明；尚未见这份更长分析纠正A的一项决定性遗漏。

保留的问题与争议：网页A的188721101 opposition.response中“经营、持钥匙和工资凭单未获证明”存在并列修饰歧义；前文条件、反论和理由均明确经营/钥匙已承认，因此不将这一措辞单独升级成确定的事实反写。A把转租条件阶段限定为REFUTED，B为UNRESOLVED；二者都保留原审许可及反对证据，前者依积极许可推反驳，后者强调未证明与待上诉评价。不能仅凭标签确定谁对。P仍有UNKNOWN状态过粗、混合证言/承认等表达限制；这些问题没有在本轮被修复，也没有为消除它们追加运行。

本批最终回答比V6更忠实且完整，依据是具体错误减少和反论恢复，不是四份都预测DENY、JSON完整或全部变成未知。限定审阅未确认网页最终答案新增与V6同等严重的决定性错误，但不等于全部语义已穷尽验证。两案真实法律包仍缺更完整的举证和上诉审查标准；112400缺住宅出租用途及其他住所情况，188721101缺父亲详情、书面同意及权利控制的最终事实评价。目标法院最终接受何种判断本来就是被排除的待分析结果，不能要求补回目标答案来消除未知。

比较边界：这是两件已参与开发的案件，来源为完整“允许材料”，不是完整未遮挡判决。法源保留V6的历史重建及后出材料限制。网页端没有本地逐token Schema约束；具体型号、采样、内部推理、上下文处理及精确tokens不可得，输出语言和长度也不同。因此只能说更强网页运行配置整体有改善，不能证明改进全部来自参数规模或某一个接口字段。B能回读原文，不能将所有正确处归功于P；本轮也没有评价程序检查块或GNN。

逐调用成本（秒为提交至观察到完成的间隔，包括排队、浏览器、轮询及取回延迟，不是精确生成耗时）：

|案件|阶段|状态|完整任务UTF-8字节|原始回答字节|观察间隔秒|
|---|---|---|---:|---:|---:|
'''
 for x in rows:report+=f"|{x['case']}|{x['stage']}|{x['status']}|{x['task_bytes']}|{x['reply_bytes']}|{x['observed_seconds']:.2f}|\n"
 for x in pairs:report+=f"\n{x['case']}：A一调用，{x['A_task_bytes']:,}任务字节、观察间隔{x['A_observed_seconds']:.2f}秒；P+B两调用，{x['P_plus_B_task_bytes']:,}累计任务字节、观察间隔{x['P_plus_B_observed_seconds']:.2f}秒。累计字节包含重复发送的案情与法源，不代表独有信息量。\n"
 report+='''
网页未生成下载链接；直接保存了完整渲染JSON原文。188721101 A使用普通段落呈现，读取位置切换不涉及再次生成；六份均无需删除围栏或修补内容。上传成功、材料逐字装配检查和完整回答可观察，但无法审计网页内部是否对附件作隐藏检索或上下文裁剪；未观察到外部搜索、其他聊天引用或附件读取失败。此限制不能包装成已证明内部逐字读取。

工程与保存：A/P原prompt和Schema逐字等于V6；B仅将空中间材料替换成本轮原P，动态哈希在P完成后保存。两份离线导入均为OK，没有隔离记录；这不代表语义正确，checks从未进入B。V6的158份原文件及27项旧源码哈希不变，当前工作区已有修改未覆盖。所有任务、原回复、URL、设置和一次集中来源审阅均在新目录。临时对话URL不保证长期可用，完整本地原文是持久审阅依据。截图及浏览器页面仅本地保存，排除发布清单。

文件入口：answers.md为六份原始输出；case-comparison.csv/json为逐案结果；final-source-review.json及review-source-anchors.json为集中审阅与允许原文；call-costs.csv/costs.json为成本；tasks和runs为实际提交、Schema、原文、导入及离线checks；freeze/config.json为预先冻结，B-assembly-validation.json为动态装配核验，preservation-after.json为历史保留核验。

完成本轮后停止。不追加C、不补法源、不重新生成、不训练、不启封SEALED、不提交或推送GitHub。下一步若继续，应由用户决定是否扩展同配置直接回答验证或有边界地补充真实法源；本轮不执行。
'''
 (R/'report-zh.txt').write_text(report)
 # Repository metadata; no commit/push.
 summary='V7六次普通High独立临时对话完成，2份P与4份最终回答均可读，零重试。网页A/B明显减少V6来源误读及遗漏；112400 B接近A，188721101 B有逐安排组织收益但未确认重要额外净收益。优先网页A、P可选；一次模型辅助来源审阅，非人工gold，旧案开发诊断。未新增法源、执行器改动、本地推理或推送。'
 policy=read('docs/repository-artifacts.json');policy['code_review_files'].append('scripts/report_irac_web_v7.py') if 'scripts/report_irac_web_v7.py' not in policy['code_review_files'] else None
 policy['current_review']={'contract_version':2,'review_kind':'IRAC_WEB_CROSSMODEL_V7_COMPLETED','title':'IRAC V7 同接口同材料网页A/B对照','report':str(R/'report-zh.txt'),'summary':summary,'status':'COMPLETED_SIX_WEB_CALLS_ONE_REVIEW_STOPPED_LOCAL_ONLY','links':[{'label':label,'path':str(R/p)} for label,p in [('中文报告','report-zh.txt'),('完整网页回答及P','answers.md'),('逐案比较','case-comparison.csv'),('集中来源审阅','final-source-review.json'),('允许来源审阅锚点','review-source-anchors.json'),('成本与对话URL','call-costs.csv'),('冻结配置','freeze/config.json'),('动态B装配','B-assembly-validation.json'),('历史保留','preservation-after.json')]],'review_request':'只读核对V7同材料网页A/P/B及V6基线。区分整体配置改善与P额外净收益；核对原文和主要反论，不以共同DENY或JSON成功为法律正确。112400两项过度推断、本人择一路线、后续报告；188721101起租日期、工资凭证、邻居、父亲/弟弟、书面同意及原审效力。P/B C02状态分歧保留解释空间；浏览器记录本地排除。不授权追加实验、纠错重跑或发布。'}
 policy['publication_authorization']['current_irac_web_v7_hold']='Explicit current user: local prepare/manifest/verify only; no commit/push.'
 save('docs/repository-artifacts.json',policy)
 cat=read('docs/EXPERIMENTS.json');assert not any(x['id']=='irac-web-crossmodel-v7' for x in cat['experiments']);cat['experiments'].append({'id':'irac-web-crossmodel-v7','role':'two_exposed_cases_same_information_web_configuration_AB_development','report':str(R/'report-zh.txt'),'note':summary});save('docs/EXPERIMENTS.json',cat)
 p=Path('README.md');old=p.read_text();old=old.replace('# 当前工作：IRAC V6 两案完整比较已完成','# 历史：IRAC V6 两案完整比较已完成',1);p.write_text('# 当前工作：IRAC V7 网页同接口A/B比较已完成\n\n'+summary+' 见[报告]('+str(R/'report-zh.txt')+')、[完整回答]('+str(R/'answers.md')+')、[逐案比较]('+str(R/'case-comparison.csv')+')。\n\n'+old)
 p=Path('docs/CHANGELOG.md');p.write_text('## 2026-10-08 IRAC V7：两案同材料网页比较\n\n'+summary+' 六份实际任务保留原V6接口，B只增加本轮P；精确tokens与推理耗时不可得，观察间隔单列。截图与账户界面记录不发布。\n\n'+p.read_text())
 print('V7 report, source review, costs and local metadata completed')
if __name__=='__main__':main()
