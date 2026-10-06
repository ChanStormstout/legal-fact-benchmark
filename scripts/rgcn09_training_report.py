"""Post-run aggregation only; no model calls or parameter changes."""
import json,hashlib,collections,csv
from pathlib import Path
R=Path('outputs/rgcn-data-expansion-09/main-training-01')
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
 p=R/p
 if p.exists():raise FileExistsError(p)
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(x if isinstance(x,str) else json.dumps(x,ensure_ascii=False,indent=2)+'\n')
rows=read(R/'selection-results.json');fits=read(R/'training-results.json');agg=[]
for seed in [20261004,20261005]:
 for method in 'SBC':
  z=[x for x in rows if x['seed']==seed and x['method']==method]
  agg.append(dict(seed=seed,method=method,cases=len(z),core_delivered=[sum(x['core_delivered'][i] for x in z) for i in range(2)],macro_core_coverage=sum(x['core_delivered'][0]/x['core_delivered'][1] for x in z)/len(z),known_irrelevant_selected=sum(len(x['irrelevant_selected']) for x in z),unlabeled_selected=sum(len(x['unlabeled_selected']) for x in z),preference_agreement=[sum(x['preference_agreement'][i] for x in z) for i in range(2)],mean_material_characters=sum(x['legal_characters'] for x in z)/len(z),unique_material_packs=len({x['material_sha256'] for x in z})))
save('aggregate.json',agg)
changes=[]
for seed in [20261004,20261005]:
 for cid in read(R/'protocol.json')['config']['dev_ids']:
  by={x['method']:x for x in rows if x['seed']==seed and x['case_id']==cid}
  for a,b in [('S','B'),('B','C')]:
   x,y=by[a],by[b];old,new=set(x['selected_ids']),set(y['selected_ids']);core=set(x['core_excluding_mandatory'])
   changes.append(dict(seed=seed,case_id=cid,comparison=b+'-'+a,added=sorted(new-old),removed=sorted(old-new),known_core_added=sorted((new-old)&core),known_core_removed=sorted((old-new)&core),material_bytes_equal=x['material_sha256']==y['material_sha256']))
save('material-changes.json',changes)
quality=[]
for p in sorted(R.glob('runs/*/train.json')):
 x=read(p);quality.append(dict(run=p.parent.name,updates=x['updates'],accepted_uses=x['accepted_uses'],trained_cases=len(x['trained_cases']),first_objective=x['loss'][0],last_objective=x['loss'][-1],first_gradient_norm=x['gradient_norm_first'],parameter_delta=x['parameter_delta_norm'],parameters=x['parameters'],seconds=x['seconds'],peak_active_bytes=x['peak_active_bytes']))
save('training-quality.json',quality)
labels=collections.Counter(y for pairs in read(R/'supervision.json').values() for _,y in pairs);save('supervision-summary.json',{'known':dict(zip(['CORE','BACKGROUND','IRRELEVANT'],[labels[i] for i in range(3)])),'unknown_unmarked_isolated_in_loss':False,'source_anchor_check_not_semantic_gold':True,'125596702_accepted':8,'125596702_isolated':22})
checks={}
for name,m in [('historical',read(R/'registration.json')['preserve_hashes']),('training_freeze',read(R/'training-freeze.json')['files'])]:
 bad=[p for p,h in m.items() if not Path(p).exists() or sha(p)!=h];checks[name]={'checked':len(m),'changed':bad};assert not bad
save('preservation-audit.json',checks)
save('local-weights-manifest.json',{'local_only':True,'files':{str(p):sha(p) for p in R.glob('runs/*/weights.npz')}})
# Record inherited helper hashes after the run; not misrepresented as pre-run freeze.
helpers=['rgcn_development_v2.py','source_location_v3.py','authority_index.py','rule_retrieval_v21.py','final_v9.py']
save('inherited-helper-hashes-postrun.json',{'timing':'POST_RUN; primary run/numeric/method files were frozen before training','files':{str(Path('legal_bench/rules_verdict_v1')/p):sha(Path('legal_bench/rules_verdict_v1')/p) for p in helpers}})
save('training-gate.json',{'status':'AUTHORIZED_PARTIAL_SUPERVISION_RUN_COMPLETED','fits':len(fits),'failures':sum(x['status']!='OK' for x in fits),'train':27,'development':6,'sealed':8,'sealed_evaluated':False,'next_training_authorized':False,'decision':'PAUSE_GRAPH_EXPANSION_KEEP_S_BASELINE_NO_STABLE_B_GT_S_OR_C_GT_B'})
lines=['案件 | S(种子04/05) | B(04/05) | C(04/05) | 已标记核心依据数','--- | --- | --- | --- | ---']
for cid in read(R/'protocol.json')['config']['dev_ids']:
 vals={k:[next(x for x in rows if x['case_id']==cid and x['method']==k and x['seed']==s)['core_delivered'] for s in [20261004,20261005]] for k in 'SBC'}
 lines.append(cid+' | '+' | '.join('/'.join(str(x[0]) for x in vals[k]) for k in 'SBC')+' | '+str(vals['S'][0][1]))
save('case-comparison.md','\n'.join(lines)+'\n\n只计已有明确参考的非强制核心依据。未标记不计错误，同案多依据不是独立样本。\n')
report='''V09：27案不完整监督的首次S/B/C主训练（开发评价）

六次训练已完成，零技术失败。当前决定：暂停扩大图排序，保留S作为基线；本轮没有获得稳定的B>S或C>B证据。不能用C第二个种子的较好结果抵消第一个种子的明显退步，也不能据此宣称关系信息或GNN普遍无效。本轮未生成法律回答，无法判断完整法律回答收益。

S只学习每项法源的共享用途倾向，不读取案件特征；B读取同一图数据导出的18项案件—法源关系特征，用线性分类器排序；C沿用V08的两层、16维、2个基矩阵R-GCN，将图传播表示与同一18项特征结合。三者都预测CORE、BACKGROUND、IRRELEVANT，以2×P(CORE)+P(BACKGROUND)排序。训练均为200步、学习率0.003、L2系数0.001、种子20261004和20261005；每案损失先取均值，再对案件取均值。没有调架构或选最优种子。

本轮使用27个TRAIN，730项可计算标签：旧113项、新导入609项、125596702中8项地址及引文检查通过的原始标签。按用户授权，重复提交不再整体阻止该案参加训练；重复影响仍未知，8项只作为暂定模型参考，另外22项隔离不进入损失。其他未知、未标记及隔离项同样不当负例。8个SEALED仅核对清单身份与组号，没有读取内容、建立特征或评价。已知纠纷组没有跨集合；更广泛关联未经完全核查。

旧6案继续只作DEVELOPMENT。它们的旧用途记录中只有35条可映射到明确三类，其余未确定项不进入类别评分；强制提供的第14(1)(b)条扣除后，共11项已标记核心依据。新增16项法源没有这6案的用途标签和案件条件对齐。本轮保留新增法源原文及来源条件节点，案件连接为UNKNOWN，没有填造连接。该缺失对依赖案件关系的B/C可能不利，因此这次评价不能完整代表30法源池，也不是独立泛化成绩。

在相同30候选和20,000字符预算下，种子04的核心送达为S8/11、B7/11、C4/11；种子05为S8/11、B7/11、C9/11。各案结果见case-comparison.md，所有排名、概率、原文材料和预算决定保存在runs。以上是已确认依据覆盖，不是准确率或完整召回率。三种方法选中的已标记IRRELEVANT均为0，但大批所选法源没有开发标签，因此不能推断没有错误选择。两个种子下S/B各自送达集合相同；C有明显变化，两个种子不足以估计稳定性。

具体取舍：110204406中，S送达DRC第16条及GR的Delhi报道段，B保留后者却丢失第16条，两种子均少一项已确认依据。58386394中B把S的第16条换为Telesound第16段，数量同为2/3，不能只看总数当作内容相同。C在第一个种子对这两个案件均未送达任何非强制已标记核心依据；第二个种子分别送达2/3、3/3。material-changes.json保存全部新增/挤出项，未按结果筛选展示。

排序的旧偏好诊断S71/73、B56/73、C59/73（两种子相同）；这些偏好也来自模型参考且不完整，不用于调参或挑选模型。排序变化、材料送达和最终法律效能是不同环节，本轮只测到前两者。

六次拟合和本地开发选择合计约22.48秒，未新增网页、LLM或付费API调用。单次拟合S约0.27/1.14秒，B约0.29/1.13秒，C约8.89/10.15秒；时间包括当前进程调度，不能当精确硬件基准。MLX峰值活动内存最高约500MB（不是整机总内存）。三种方法均有非零梯度、参数更新和下降的训练目标，证明实际拟合发生，不证明法律正确。C训练目标下降更大但开发送达不稳定，不能用训练拟合替代开发效果。

实施仅增加30候选接口与CORE标签映射，旧V08源码未改。开发新增法源的缺失连接明确保留UNKNOWN。四项相关程序检查通过，覆盖类别映射/隔离掩码、30维共享基线、缺失对齐以及只用TRAIN计算标准化。准备阶段一次绝对路径快照错误在训练前修正，部分准备原样保存在preparation-attempt-01；同时修正SEALED_TEST名称校验。没有训练重试。主运行代码、实际数值输入、监督、参数及顺序在首次训练前冻结；若干继承辅助模块仅另存运行后哈希，未冒充完整的运行前递归依赖快照。

结论的限制来自三处：单次模型参考仍可能含语义错误；开发对新增16项没有完整标签和对齐；6案此前用于开发，不是未见测试。当前不值得继续参数或架构试验。若下一步要作更强投入判断，应先按统一规则补齐开发法源对齐与粗用途覆盖，再另行授权评价；本轮不执行补标或新训练。暂不启封8案SEALED，不改已有监督追求更好结果。

V08及前一轮原文件哈希保持，完整检查见preservation-audit.json。所有六次权重在本地保存并有哈希，因仓库约定不进入发布清单。本轮更新本地状态、报告和审阅包，不提交或推送。模型参考不是人工金标准，本轮至此结束。
'''
save('report-zh.txt',report)
summary='27 TRAIN、730项暂定用途监督、30法源，两个种子共6次S/B/C训练完成。DEV核心送达S8/11、B7/11、C4/11与9/11；无稳定条件化收益，暂停扩大图。8 SEALED未用；未生成法律回答或推送。'
entry={'id':'rgcn09-main-training-01','role':'partial_supervision_development_training','report':str(R/'report-zh.txt'),'note':summary}
p=Path('docs/EXPERIMENTS.json');obj=read(p);obj['experiments'].append(entry);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
p=Path('docs/EXPERIMENT_INDEX.md');s=p.read_text();p.write_text(s+f"\n| {entry['id']} | {entry['role']} | [报告](../{entry['report']}) | {summary} |\n")
p=Path('README.md');s=p.read_text();p.write_text('最新[V09主训练报告]('+entry['report']+')：'+summary+'\n\n'+s.replace('最新[V09剩余任务报告]','准备阶段[V09剩余任务报告]',1))
p=Path('docs/CHANGELOG.md');p.write_text('# 2026-10-05 V09首次27案主训练\n\n'+summary+' 保留125596702重复来源，仅纳入8项原样通过引文检查的标签，其余22项隔离。新增30候选与CORE映射接口，V08保持。\n\n'+p.read_text())
cur={'title':'V09 27-case partial-supervision S/B/C training','report':entry['report'],'summary':summary,'review_kind':'RGCN_MAIN_TRAINING','candidate_report':'outputs/rgcn-data-expansion-09/continuation-01/candidate-audit.json','pool_manifest':'outputs/rgcn-data-expansion-09/authority-pool/manifest.json','comparison_protocol':str(R/'protocol.json'),'preparation_freeze':str(R/'training-freeze.json'),'stage_description':report}
for name in ['docs/PROJECT_STATE.json','docs/repository-artifacts.json']:
 p=Path(name);x=read(p);x['current_review']=cur
 if name.endswith('PROJECT_STATE.json'):x['development_follow_up']['rgcn09_main_training']={'status':'COMPLETED','report':entry['report'],'training_fits':6,'failures':0,'train_cases':27,'development_cases':6,'sealed_cases':8,'sealed_evaluated':False,'accepted_uses':730,'decision':'PAUSE_GRAPH_EXPANSION_NO_STABLE_GAIN','publication':'LOCAL_ONLY_NO_COMMIT_NO_PUSH'}
 else:
  for f in ['scripts/rgcn09_train.py','legal_bench/rules_verdict_v1/rgcn_use_v2.py','tests/test_rgcn09_train.py']:
   if f not in x['code_review_files']:x['code_review_files'].append(f)
 p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(agg,ensure_ascii=False))
