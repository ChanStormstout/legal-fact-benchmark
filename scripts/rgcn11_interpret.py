# Post-run report-only interpretation of frozen references and material selection.
# Run once in a fresh versioned output; never changes labels or training.
import json,hashlib,datetime
from pathlib import Path
r=Path('outputs/rgcn-sbc-finalization-11')
def rd(name):return json.load(open(r/name))
def write(name,value):
 p=r/name;assert not p.exists();p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
roles={
 'LAW:S02:DRC14:1b':'强制基础条款；不计案件条件化收益',
 'LAW:S02:DRC:16':'适用时间与书面同意的法定补充条件／限制',
 'LAW:S02:DRC:17':'实际涉及受保护次租户时的同意及通知机制',
 'LAW:S02:DRC:18':'合格次租户后续直接租户地位；保护或反对腾退框架',
 'LAW:V09:KR_BURDEN':'第三人占用与举证负担的测试',
 'LAW:V09:CEL_BURDEN':'独占占有及举证转移测试；保留Goa制度范围',
 'LAW:V09:CEL_CONTROL':'保留控制及真实合伙的限制／反论；保留Goa范围',
 'LAW:V09:AH_LICENCE':'租赁与许可的定性测试及控制限制',
 'LAW:V09:AH_CONSENT_SCOPE':'具体交易及时间的同意限制／反论；源自1952 Delhi-and-Ajmer制度',
 'LAW:V09:GD_COMMERCIAL_SUCCESSION':'普通商用租赁继承的反论；不自动解决遗嘱处分',
 'LAW:V09:HELP_GENUINENESS':'保留法律占有及真实合伙的限制／反论；保留Bombay范围',
 'LAW:V21:TS:PAR16':'公司合并的初步意见及明确保留腾退争点的限制',
 'LAW:V09:CK_ASSIGNMENT_SCOPE':'让与／交出占有的宽范围；清算出售不自动等于直接法定归属',
 'LAW:V09:CK_REGULATORY_TRANSFER':'监管背景下合同让与与直接法定归属的区别',
 'LAW:V09:GL_WRITTEN_CONSENT':'受保护次租户的书面同意与通知及可合于一份文件的范围',
 'LAW:V09:GL_CONCURRING_LIMIT':'特殊事实下的保护意见限制；保留协同意见地位',
 'LAW:V21:GR:REPORTED_DELHI':'Delhi非自愿转移命题的转述及其范围；不当作无限豁免',
}
role_rows=[]
for x in rd('core-role-register.json'):
 role_rows.append(dict(x,analysis_role=roles[x['unit_id']],potentially_replaceable='需比较具体命题与范围；同文书或相近词汇均不自动替代',provisional_overlap_group='保留法律占有／许可定性有部分重叠，但法域、要素及命题不同' if x['unit_id'] in ['LAW:V09:CEL_CONTROL','LAW:V09:HELP_GENUINENESS','LAW:V09:AH_LICENCE'] else '未认定可直接替代',role='POST_RUN_INTERPRETATION_OF_EXISTING_REFERENCE_NOT_NEW_GOLD'))
write('core-roles-interpreted.json',role_rows)
notes={
 '110204406':('B在两个种子均增加Telesound的保留意见，未失去S已送达的已知CORE，属于具体的单案改善。C两种子都丢掉该保留意见，分别换来assignment范围或licence定性，不能直接认定更好。','公司原租户被国有化／并入后继公司是允许记录中的主张或证言；不能据此认定具体法定归属已成立。',['IK-110204406:L103','IK-110204406:L136']),
 '172908545':('B两个种子都失去Section16、交易及时点特定同意限制、Celina举证框架。seed04增加商业继承，seed05增加让与范围；前者回应真实继承反论，但不能替代书面同意及举证问题。C的seed05只恢复Section16而无新增已知CORE损失；seed04又丢控制和继承框架，收益不稳定。','1964年许可、1997年公司经营、注册Will后的儿子接续，以及对遗嘱处分的反论在允许来源中分别出现。商用租赁普通继承与Will的法律效果不得合并。',['IK-172908545:L63','IK-172908545:L64','IK-172908545:L123','IK-172908545:L129','IK-172908545:L130']),
 '58386394':('B增加银行后继机制或许可定性材料，但两种子都失去Section16与具体同意范围限制。C恢复部分同意材料时又损失转移范围或Telesound保留意见。11项参考CORE不能靠20k同时全部装入；相同3/11计数也可能覆盖不同问题，不能据计数判为平局。','允许记录包含银行合并链、1944年租约授权主张及房东关于租约期限、禁止转租、租金不能替代同意的抗辩，均非目标法院最终认可。',['IK-58386394:L104','IK-58386394:L109','IK-58386394:L110','IK-58386394:L148','IK-58386394:L149','IK-58386394:L150']),
 '890045':('B两种子均多送达两项让与范围／监管背景材料，但都丢掉针对Clause7是否构成特定同意的反论。其3/5高于S的2/5，仍不能证明净改善；C又在两种子均丢掉assignment宽范围。','租约对lessee/assigns的表述与租户援引Clause7作为同意的主张均已在来源内，宽泛让与条款不能代替同意范围分析。',['IK-890045:L229@96:401','IK-890045:L230','IK-890045:L278@0:132']),
 '1908519':('S及B两个种子都未送达唯一已知非强制CORE。C仅seed05送达AH_LICENCE，seed04仍未送达。其他四项旧隔离参考保持不变，入选它们不计误报，也不能用其缺失判法律失败。','已有有限参考及允许来源缺口限制对不同材料包的可靠评价；未扩大核查或恢复范围外隔离。',[]),
 '869439':('B两种子均失去特定同意限制及保留法律占有反论，没有增加已知CORE。C恢复法律占有或许可定性时又丢Section16；两种子均未恢复特定同意限制。因此不是只减少无关材料就可视为改进。','Clause14分别使用written permission与permission，租户明确争辩共享不是交出法律占有且书面要求仅是证明形式；这些反论需要相应法律分析，不能由同意不存在或租户陈述已成立替代。',['IK-869439:L166','IK-869439:L171','IK-869439:L176','IK-869439:L177@0:232','IK-869439:L233@0:144'])}
summary=[]
for cid,(analysis,basis,refs) in notes.items():
 src={s['id']:s['text'] for s in rd('sources/'+cid+'.json')['segments']}
 rows={str(seed):{k:rd(f'runs/{seed}-{k}/{cid}.json')['metrics'] for k in ['S','B','C']} for seed in [20261004,20261005]}
 summary.append({'case_id':cid,'analysis':analysis,'source_status_basis':basis,'source_evidence':[{'id':ref,'text':src[ref]} for ref in refs],'both_seeds':rows,'no_reference_labels_changed':True,'review_role':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD'})
write('concentrated-comparison-review.json',{'cases':summary,'one_concentrated_post_run_review':True,'no_new_model_calls':True,'interpretation_disputes_retained':True,'decision':'保留S作为本阶段基线；未证明B稳定净改善，C未稳定超过B，暂停扩大当前图排序路线。S并未解决所有重要材料遗漏。'})
lines=['S/B/C authority-selection：V11收尾','', '本轮决定：保留S作为当前法源选择基线，暂停扩大当前R-GCN路线。B有单案具体收益，但没有在两种子、多个案件中显示稳定净改善；C也没有稳定超过B。这个决定只适用于当前27案弱监督、30项法源、20k预算和6个开发案，不否定案件信息或GNN在其他条件下的价值。','', '完成情况：12次独立普通High准备调用，语义重试0；27 TRAIN的757项已知用途进入损失；六次200步固定拟合全部完成，失败0；生成36份DEV实际材料包。原8个SEALED未启封，没有新法律回答。','标签路径仅处理四项法源：87项KEEP、45项CHANGE；图路径117项CHANGE、15项UNKNOWN。图的未知不等于标签用途未知，更不等于事实否定。范围外标签及共享事实／needs原样继承。新增图隔离仍沿用V10的保守scope掩码，因此被拒绝连接的单元可能在实际图中表现为UNKNOWN，不能把复核的NONE误读成现实事实不存在。','', '两个种子下已知非强制CORE送达如下。这是已有不完整模型参考的覆盖，不是准确率：','| seed | S | B | C |','| --- | --- | --- |','| 20261004 | 16/35 | 14/35 | 13/35 |','| 20261005 | 16/35 | 15/35 | 15/35 |','', '35项已知CORE均能分别在强制基础条款和20k预算下装入；不表示它们能同时装入。所有已知CORE漏送都记录为在先前排名／已选依赖包消耗预算后，原子包超过剩余预算。三方法均给出完整30项排名，没有检索候选缺失或库外来源问题。逐案失去哪项法源、排名、依赖与预算决定完整保存在结果文件。','B的已知无关入选从S的5个case-unit位置降到2个；C为2和3个。这是有意义的选择变化，但不能补偿重要反对规则遗漏。S两种子送达完全相同的材料组合，显示共享先验基线；B/C改变各案材料，不等于改变更好。','', '逐案集中比较：']
for cid,(analysis,basis,refs) in notes.items():lines.append(cid+'：'+analysis+' 依据：'+('、'.join(refs) if refs else '现有参考状态；4项隔离保留')+'。')
lines+=['', '如何理解重复法源：HELP、Celina控制及AH许可定性有局部重叠，但法域、程序及命题不同，不自动互换。Clause7/14的特定同意限制，不能由基础§14(1)(b)或一般assignment宽范围代替。Telesound的保留意见也不能当作公司合并一律合法的确定规则。同文书不同单元的文书覆盖只作辅助，不能证明关键命题已送达。','', '成本与工程：六次训练总计约10.7秒，S/B单次约0.2–0.3秒，C约4.8秒；MLX峰值活跃分配约242MB／540MB，不是整机峰值内存。训练数据损失与L2已分开保存；C拟合训练弱标签更充分（数据损失约0.07，S/B约0.64–0.67），这没有转换为稳定DEV材料选择收益，不能据此继续加复杂度。','冻结准备出现一次路径包装错误（绝对__file__覆盖快照目标），在任何拟合前修复，仅改成仓库相对路径；原失败及部分产物保存在freeze-attempt-01。没有训练重试、数据修补或看过DEV后改方法。系统Python缺numpy的测试日志保留，项目专用环境九个相关测试全部通过。','网页12份完整代码块均已保存，10份下载文件与代码块内容一致，2份下载传输未取到，但不影响原始完整JSON读取。精确网页tokens与实际生成时间不可得；记录提交到观察完成的时间区间，不将其写成精确生成耗时。','', '边界：参考为弱监督及模型辅助来源审阅，不是人工金标准；DEV已参与开发，不是独立测试。C同时加入文本、非线性与图传播，不能将C/B差异归因于纯消息传递。本轮只评价排序及实际材料送达，没有评估新法律回答、规则归纳或裁判正确性。','', '交付：protocol/criteria、132位置L/G独立处置、overlay历史、readiness、pretraining-freeze、六套training logs/probabilities/rankings、36份材料、comparison-table、逐案集中解释及cost ledger。1161项V08/V09主训练/V10历史文件字节核验未变；本地审阅包更新后停止，不提交或推送。']
# The previous automatically assembled descriptive report is preserved as its own version.
p=r/'report-zh.txt';p.rename(r/'report-descriptive-01.txt');p.write_text('\n'.join(lines)+'\n')
# Observable latency, not precise generation cost.
cost=rd('cost-ledger.json');lat=[]
for x in rd('task-ledger.json'):
 sent=rd('web/'+x['id']+'.submitted.json');done=rd('web/'+x['id']+'.completed.json');start=datetime.datetime.fromisoformat(sent['submitted_at'].replace('Z','+00:00'));end=datetime.datetime.fromisoformat(done['completed_observed_at'].replace('Z','+00:00'));lat.append({'task_id':x['id'],'submitted_at':sent['submitted_at'],'completion_observed_at':done['completed_observed_at'],'elapsed_upper_bound_seconds':(end-start).total_seconds(),'not_exact_generation_time':True,'input_characters':x['characters'],'output_raw_characters':len((r/'web'/f"{x['id']}.raw.json").read_text())})
write('cost-observable-final.json',{'inherited_cost_file':'cost-ledger.json','new_preparation_calls':12,'semantic_retries':0,'fits':6,'technical_fit_failures':0,'pretraining_wrapper_failures':1,'web_observation_intervals':lat,'downloads':'download-transport-final.json','training':rd('training-cost.json'),'old_cost_separate':'outputs/rgcn-dev-contract-repair-10/cost-final.json'})
