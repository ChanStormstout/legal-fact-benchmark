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
lines=['S/B/C Authority Selection: V11 Completion','', 'Decision: retain S as the current authority-selection comparator and pause expansion of this R-GCN route. B has specific single-case benefits but no stable net improvement across two seeds and multiple cases; C does not consistently exceed B. This applies to the current 27 weakly supervised cases, 30 authorities, 20k budget and six DEV cases. It does not reject case information or GNNs under other conditions.','', 'Completion: 12 independent ordinary High preparation calls, zero semantic retries; 757 known-use labels from 27 TRAIN cases enter the loss. All six fixed 200-step fits finish without failure, producing 36 actual DEV material packages. The eight original SEALED cases remain unopened and no new legal answers are generated.','The label path changes only four authorities: 87 KEEP and 45 CHANGE. The graph path contains 117 CHANGE and 15 UNKNOWN. Graph unknown is neither label-use unknown nor factual negation. Out-of-scope labels and shared facts/needs remain inherited unchanged. New graph isolation retains V10 conservative scope masks, so a rejected link can appear UNKNOWN in the actual graph. Review NONE does not mean real-world absence.','', 'Known nonmandatory CORE delivery under two seeds follows. This measures coverage of incomplete model references, not accuracy:','| seed | S | B | C |','| --- | --- | --- |','| 20261004 | 16/35 | 14/35 | 13/35 |','| 20261005 | 16/35 | 15/35 | 15/35 |','', 'All 35 known CORE units individually fit with the mandatory base provision under 20k, but need not fit together. Every missing known CORE is recorded as an atomic package exceeding the budget remaining after earlier-ranked/selected dependency packages. All methods rank all 30 units; there is no missing retrieval candidate or out-of-library source. Per-case lost authorities, rankings, dependencies and budget decisions are preserved.',"B reduces known-irrelevant selected case-unit slots from S's five to two; C has two and three. This meaningful selection change does not compensate for important opposing-rule omissions. S delivers identical packages across seeds, reflecting a shared prior. B/C changing packages does not establish better changes.",'', 'Concentrated per-case comparison:']
for cid,(analysis,basis,refs) in notes.items():lines.append(cid+'：'+analysis+' Evidence: '+('、'.join(refs) if refs else 'Existing reference status; four isolated items retained')+'。')
lines+=['', 'Overlapping authorities: HELP, Celina control and AH licence classification partly overlap, but differ in jurisdiction, procedure and proposition and are not automatically interchangeable. Clause 7/14 consent-scope restrictions cannot be replaced by base section 14(1)(b) or general assignment breadth. Telesound reservations are not a universal company-merger exemption. Document-level coverage across different units is auxiliary and does not prove delivery of the key proposition.','', 'Costs and engineering: six fits take approximately 10.7 seconds total; S/B about 0.2–0.3 seconds per fit and C about 4.8. MLX peak active allocations are approximately 242/540 MB, not whole-machine peak memory. Data loss and L2 are stored separately. C fits weak training labels more closely (data loss about 0.07 versus S/B 0.64–0.67), without stable DEV selection benefit; this does not justify more complexity.','One pre-fit freeze-packaging error used absolute __file__ to override the snapshot destination. It was repaired before any fit by using a repository-relative path; failure and partial artifacts remain in freeze-attempt-01. There were no training retries, data repairs or post-DEV method changes. The system-Python missing-numpy test log is preserved; all nine relevant tests pass in the project environment.','All 12 complete web code blocks are saved. Ten downloaded files match their code blocks; two downloads were unavailable without preventing full raw JSON retrieval. Exact web tokens and generation time are unavailable. Submission-to-observed-completion intervals are recorded rather than presented as exact generation latency.','', 'Limits: references are weak supervision and model-assisted source review, not human gold. DEV participated in development and is not independent testing. C adds text, nonlinearity and graph propagation together, so C/B differences do not isolate message passing. This round evaluates ranking and delivered materials, not new legal answers, rule induction or judgment correctness.','', 'Delivery includes protocol/criteria, 132 independent L/G dispositions, overlay history, readiness, pretraining freeze, six training-log/probability/ranking sets, 36 packages, comparison table, per-case interpretation and cost ledger. All 1,161 historical V08/V09 main-training/V10 files retain their bytes. Stop after updating the local review package; no commits or pushes.']
# The previous automatically assembled descriptive report is preserved as its own version.
p=r/'report-zh.txt';p.rename(r/'report-descriptive-01.txt');p.write_text('\n'.join(lines)+'\n')
# Observable latency, not precise generation cost.
cost=rd('cost-ledger.json');lat=[]
for x in rd('task-ledger.json'):
 sent=rd('web/'+x['id']+'.submitted.json');done=rd('web/'+x['id']+'.completed.json');start=datetime.datetime.fromisoformat(sent['submitted_at'].replace('Z','+00:00'));end=datetime.datetime.fromisoformat(done['completed_observed_at'].replace('Z','+00:00'));lat.append({'task_id':x['id'],'submitted_at':sent['submitted_at'],'completion_observed_at':done['completed_observed_at'],'elapsed_upper_bound_seconds':(end-start).total_seconds(),'not_exact_generation_time':True,'input_characters':x['characters'],'output_raw_characters':len((r/'web'/f"{x['id']}.raw.json").read_text())})
write('cost-observable-final.json',{'inherited_cost_file':'cost-ledger.json','new_preparation_calls':12,'semantic_retries':0,'fits':6,'technical_fit_failures':0,'pretraining_wrapper_failures':1,'web_observation_intervals':lat,'downloads':'download-transport-final.json','training':rd('training-cost.json'),'old_cost_separate':'outputs/rgcn-dev-contract-repair-10/cost-final.json'})
