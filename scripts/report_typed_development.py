"""Produce complete, nonselective development results with source-audit limits."""
import json
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256

ROOT=Path('outputs/development-20-typed-relations-v2')
RUN=ROOT/'runs/first-run'
read=lambda p:json.loads(p.read_text())
s=read(RUN/'summary.json');ps=read(RUN/'patterns.json');replay=read(RUN/'prior-audit-binding-replay.json')
audit=read(ROOT/'web-tasks/typed-audit-001/import-v1/audit.json')
validated=read(ROOT/'web-tasks/typed-audit-001/import-v1/validation.json')
assert validated['valid'] and len(audit['items'])==6
audit_counts=Counter((i['assertions_supported'],i['bindings_supported'],i['relation_holds']) for i in audit['items'])
categories={pool:dict(Counter(p['category'] for p in rows if p['repeated'])) for pool,rows in ps['pools'].items()}
changes=Counter()
for p in ps['pools']['typed']:
    for k,v in p['exact_identity_vs_typed_statuses'].items():changes[k]+=v
extra=[x for x in replay if x['previous_method']=='cooccurrence_extra']
recovered=sum(any(v['result']['status']=='MATCH' for v in x['typed_variants']) for x in extra)
lines=[
 '20案方法开发实验：直接成员关系与部分关系（v2）', '',
 '已完成：沿用原20案和277条事件／断言，不重新抽取事实。补充原文支持的直接对象关系，重跑共现、精确身份及新增关系查询，完成固定6项匹配核查。全部结果仍为开发数据；没有冻结正式检查集，也没有独立测试准确率。', '',
 '1. 本轮改了什么',
 'same(A,B)要求两个角色指向同一个已解析对象。part_of(A,B)要求A是B的一个有原文依据的直接物理部分。member_of(A,B)要求个人或机构A是当事人群体B的一个明确成员。后两种关系有方向，不等于身份相等。',
 '程序仅使用已保存的直接关系证据，不计算传递闭包；个人属于群体，不会自动继承群体的行为；房屋的一部分，也不会自动继承整栋楼的法律属性。模型补充关系不能解除旧记录中的未知字段或限定阻止。缺少关系记录时保持未知，材料没提到不等于关系不存在。陈述的来源阶段保留，但当前查询没有证明跨记录在同一时期成立。', '',
 '2. 来源和补充核查',
 '17案存在本轮目标，针对10组已有父子房产对象和22个已进入主请求记录的群体提交一次局部网页任务。另3案没有这些目标，仍参与20案计算。任务提供已有对象和相应原文上下文，要求逐项核查，不重做事件标注。',
 '网页结果支持8条部分关系和9条成员关系，另2条部分关系未知；没有因为未识别成员而推断群体为空。所有17案任务和目标都有覆盖记录，0条关系因格式、引用或引文定位问题被拒绝。这些是模型参考关系，不是人工金标准或完整关系图。',
 '两条未知关系涉及八间店铺的集合与其中一间、其余七间。文书没有充分识别一个共同物理整体，本轮不将“属于店铺集合”强制编码成物理part_of。此处需要另外的集合关系，当前仍未知。', '',
 '3. 固定配置与全部结果',
 '支持门槛仍为至少2份文书，每池1000个唯一候选，按规范化查询字符串排序。使用同一事实与陈述状态；至多两个记录、一个关系条件，不搜索时间、金额、结果标签或法律充分条件。只对有来源的直接边生成新候选，所有候选、未搜索项、匹配、未知与失败原因保留。',
 '方法 | 候选数 | 执行数 | 重复查询变体 | 有重复变体的展示骨架组',
]
for pool,label in [('cooccurrence','事实类型共现'),('identity','精确身份连接'),('typed','新增直接成员／部分关系')]:
    m=s['pools'][pool];lines.append('%s | %d | %d | %d | %d'%(label,m['generated'],m['executed'],m['repeated'],m['repeated_display_families']))
lines += [
 '三池均未触及预算上限。新增65个查询中，3个支持2案，其他62个只支持1案；没有为了增加重复数修改门槛或补换案件。',
 '原有113个共现重复查询、205个身份重复查询的支持数共318项逐项重放一致。旧报告中的“76种带状态组合”表述不准确：那个计数只取了记录类型，未纳入状态。本轮明确按类型、陈述状态及关系算子组织展示，205个重复身份查询属于96个骨架组。',
 '骨架组只方便阅读：同类记录对可以连受益人、受影响当事人或房产，含义仍不同，所有角色变体均单独保留。它们不是自动发现的事实family或已证明等价的语义cluster。',
 '重复查询按声明的记录类型分类：'+json.dumps(categories,ensure_ascii=False),
 '身份查询中62个仅含程序行为、93个混合事实与程序行为、50个仅含事实。程序结构不能直接解释为法律要件或胜败规则。', '',
 '4. 所有新增重复模式',
]
for p in ps['pools']['typed']:
    if p['repeated']:
        lines += ['查询ID '+p['id']+'；支持 '+str(p['support'])+' 案；'+p['category'],json.dumps(p['query'],ensure_ascii=False)]
lines += [
 '这三个结构分别表达：有转租记录的房产是另一个所有权记录所述房产的部分；另行提起程序的人属于腾退请求的被请求人群体；租赁记录中的租户属于腾退请求的被请求人群体。它们描述判决中可追溯的记录结构，不意味着所有权状态与转租在同一时期成立，也不证明某种腾退请求在法律上成立。', '',
 '5. 上轮三个额外共现组合如何处理',
 '三个组合仍不满足原来的精确身份条件；本轮全部找到直接成员或部分关系。原身份判断没有被改写，新增关系回答的是另一个有明确定义的问题。',
 '“上诉人和第二被告”群体与“上诉人”个人：身份不相等，个人属于群体成立。“转租的部分房间”与“整栋楼”：身份不相等，部分属于整体成立。“请求腾退的底层”与“原所有权记录中的整栋楼”：同样以部分关系连接。不能把身份不相等统称为不相关，也不能把有部分／成员关系统称为同一对象。',
 '固定组合重放：%s/%s找到直接关系。这是已知错误分析材料上的设计检查，不是新样本成绩。'%(recovered,len(extra)),
 '65个新查询在20案中，精确身份条件与有方向的关系条件的配对状态计数：'+json.dumps(dict(changes),ensure_ascii=False),
 '不同算子回答不同含义；状态变化和匹配增加不是准确率提升。', '',
 '6. 固定小规模原文核查',
 '取顺序最前3个重复新查询，加固定随机种子抽取的3个其他查询；每项取首个匹配，实际6项。全部返回，全部引文定位通过。断言、角色绑定与直接关系的判定统计：'+str(dict(audit_counts)),
 '6项均得到原文支持，其中3项对应重复查询，另3项对应单案查询。多项复用同一案件／对象关系；新对话审阅仍使用相同模型，不能当成独立人工验证或把6/6称为整体准确率。',
]
for i in audit['items']:
    lines.append(i['id']+' | assertions='+i['assertions_supported']+' | bindings='+i['bindings_supported']+' | relation='+i['relation_holds']+' | '+i['explanation'])
lines += [
 '', '7. 仍未解决的部分和下一轮',
 '新增关系只能补充已抽取对象之间的明确连接，不修复事实遗漏、原文状态误解、对象身份未解析或任意限定。本轮新查询共1300个文书判断中，68次匹配、872次未知、360次未找到。这个未知计数同时受旧记录的限定阻止和新增边覆盖不足影响，不能直接归因于标注质量差。',
 '下一轮先把未知按原文缺少信息、抽取未解析、限定影响哪个用途、缺少哪种对象关系分开。对无法使用的记录做有限的用途限定处理，仍保存原来的保守版本。需要集合关系时另定义“元素属于集合”／“集合包含子集”，不要把它们混入物理部分或个人成员关系。',
 '在改善可计算覆盖之前，不以扩大模式数量或引入结果预测作为成功标准。继续在这20案开发；之后才使用新案件评估泛化。', '',
 '8. 工程验收与文件',
 '138项程序测试通过，其中16项新增测试覆盖方向、未知、冲突、不推导传递关系、不继承群体事件、旧限定继续生效及引用完整性。逐条检查14540个轨迹行，所有事件／证据／关系引用都能解析。',
 '所有原输入哈希仍与上轮相同，旧结果保存。完整轨迹改为案件／事件／关系引用，原文、字段与关系证据在inputs/保存一次；traces.jsonl.gz约%.2f MB，所有失败和未知轨迹保留，没有只保留成功样例。'%(RUN.joinpath('traces.jsonl.gz').stat().st_size/1e6),
 '本轮网页调用：1个关系补充对话、1个固定匹配核查对话，均为普通High、非Pro，0次付费API调用。界面未暴露确切模型编号。关系任务257004字符，回复69100字符；核查任务86211字符，回复9897字符。本地执行约%.2f秒。'%(s['elapsed_local_seconds']),
 '入口：config.json、input-manifest.json；relations/逐案关系；web-tasks/原始任务、回复、URL、截图、引文校验；runs/first-run/patterns.json、candidates.json、traces.jsonl.gz、prior-audit-binding-replay.json、artifact-validation.json。',
]
(RUN/'report-zh.txt').write_text('\n\n'.join(lines)+'\n')
complete_listing=[]
for pool,rows in ps['pools'].items():
    for p in rows:
        complete_listing.append('%s | %s | support=%s | repeated=%s | family=%s | %s'%(pool,p['id'],p['support'],p['repeated'],p['family_id'],json.dumps(p['query'],ensure_ascii=False)))
(RUN/'all-patterns.txt').write_text('\n'.join(complete_listing)+'\n')
status={'completed_at':datetime.now(timezone.utc).isoformat(),'cases':20,'unchanged_events':277,
        'targeted_enrichment_complete':True,'typed_query_audit_complete':True,'audit_items':6,
        'held_out':False,'formal_check_set_frozen':False,'independence_proven':False,
        'tests_passed':138,'prior_repeated_query_supports_replayed':318,
        'trace_rows_validated':14540,'source_reference_kind':'WEB_MODEL_REFERENCE_NOT_HUMAN_GOLD',
        'report':str(RUN/'report-zh.txt'),'config_hash':s['config_hash'],
        'code_hashes':{p:sha256(Path(p).read_bytes()).hexdigest() for p in ['legal_bench/typed_relations.py','scripts/run_typed_development.py','scripts/prepare_typed_relations.py','tests/test_typed_relations.py']}}
(ROOT/'status-complete-v1.json').write_text(json.dumps(status,indent=2))
print({'report':str(RUN/'report-zh.txt'),'audit_counts':dict(audit_counts),'recovered_known_combinations':recovered,'repeated_categories':categories})
