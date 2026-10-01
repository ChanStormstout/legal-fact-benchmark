"""Complete bounded exploratory report; preserve failures and no accuracy claim."""
import json,gzip,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read,write_new,digest
from scripts.run_new10_exploration import ROOT,verify_freeze
verify_freeze()
run=ROOT/'runs/first-run';result=read(run/'results.json');summary=read(run/'summary.json');sample=read(ROOT/'sample.json');cards=read(ROOT/'tasks.json')['tasks'];selection=read(run/'audit-selection.json')
af=ROOT/'web-tasks/audit-001/import-v1/audit.json';audit=read(af) if af.exists() else {'items':[]}
av=read(af.parent/'validation.json') if af.exists() else {'valid':True,'errors':[]}
assert len(audit['items'])==len(selection['items'])
views={p.stem:read(p) for p in (ROOT/'views').glob('*.json')};edges={p.stem:read(p) for p in (ROOT/'relations').glob('*.json')}
submissions=[read(p) for p in (ROOT/'web-tasks').glob('*/submission.json')]
retrievals=[read(p) for p in (ROOT/'web-tasks').glob('*/retrieval.json')]
seen_cases={c for s in submissions if s['kind'].startswith('SINGLE_STRUCTURED') for c in s['case_ids']}
assert seen_cases=={r['case_id'] for r in sample['cases']}
errors=Counter(x['reason'] for v in views.values() for x in v['excluded'])
blocked=Counter(x['reason'] for v in views.values() for e in v['events'] for x in e['field_contract']['blocked'])
edge_reject=Counter(x['reason'] for r in edges.values() for x in r['rejected'])
now=datetime.now(timezone.utc);start=datetime.fromisoformat(read(ROOT/'freeze.json')['saved_at'])
lines=['10个新案件：已有事实关系能否跨案件匹配？','',
'本轮已结束。固定沿用上一轮3个重复查询及执行器；10案均为原开发文书之外的新材料。关联未全部查清，因此结果是新案件探索性实验，不是已证明独立的正式测试成绩。原20案没有重新标注。',
'直接回答A读取完整判决，B单次抽取事实和已有对象关系后由本地执行器回答；共现对照读取B的同一份事实，只移除关系约束。原型回答的是指定状态下的来源断言结构，不是当前法律事实、胜败规律或开放模式发现能力。', '',
'1. 固定题目与完整匹配结果',
'题目 | 类别 | A：直接回答 | B：结构化后执行 | 共现（不检查关系）']
for c in cards:
 stats=summary['per_task'][c['task_id']]
 lines.append(c['task_id']+' '+c['meaning_zh']+' | '+c['category']+' | '+' | '.join(json.dumps(stats[m],ensure_ascii=False) for m in ['A','B','cooccurrence']))
positive_cases={r['case_id'] for r in result['rows'] if r['B']['status']=='MATCH'}
a_positive_cases={r['case_id'] for r in result['rows'] if r['A']['status']=='MATCH'}
lines+=['B在%d/10案找到至少一项匹配；A在%d/10案声称至少一项匹配。两者都只是方法输出，不能先当成正确答案。'%(len(positive_cases),len(a_positive_cases)),
'NOT_FOUND只表示在当前材料或可用记录中没有找到完整实例。UNKNOWN不作为否定；暂不支持、格式失败另计。一个具体组合失败，不等于案件中所有组合均失败。',
'原题的转租与所有权状态、物理部分关系，以及两题的个人/机构至群体成员方向均未改变。后两题是程序或混合关系诊断，不能包装成实体事实规律。', '',
'2. 有限来源抽查',
'候选池及固定种子：'+json.dumps({'seed':selection['seed'],'candidate_counts':selection['category_candidates'],'selected':len(selection['items'])},ensure_ascii=False),
'抽样规则：'+selection['rule'],
'实际完成%d项，一项最多一次来源复核；没有为了凑满继续查找。'%len(audit['items']),
'本地引文定位检查：'+json.dumps(av,ensure_ascii=False)]
for item in audit['items']:
 lines.append('%s；案%s；题%s；断言=%s；对象=%s；关系=%s；A状态支持=%s；B状态支持=%s；诊断=%s。%s'%(item['id'],item['case_id'],item['task_id'],item.get('assertions_supported'),item.get('bindings_supported'),item.get('relation_holds'),item.get('A_status_supported'),item.get('B_status_supported'),item.get('error_source'),item.get('explanation','')))
 for ev in item.get('evidence',[]):lines.append('  原文 '+ev['segment_id']+'：'+ev['quote'])
lines+=['以上是模型参考判断，经来源复核但没有人工金标准。没有独立逐项答案，不报告30题准确率，也不从抽查比例推算整批性能。', '',
'3. 每案完整状态及差异',
'案ID / 原候选排名 / 判决标题：三题按上述顺序列A/B/共现']
for case in sample['cases']:
 rows=[r for r in result['rows'] if r['case_id']==case['case_id']]
 lines.append('%s / %s / %s: %s'%(case['case_id'],case['rank'],case['title'],'; '.join(r['task_id'][:4]+': '+r['A']['status']+'/'+r['B']['status']+'/'+r['cooccurrence']['status'] for r in rows)))
 for r in rows:
  if r['A']['status']!=r['B']['status']:
   lines.append('  分歧 '+r['task_id']+': A '+r['A'].get('explanation',r['A'].get('reason','')))
   lines.append('  B匹配=%d；未知组合=%d；失败组合=%d；完整对象及出处见results.json'%(len(r['B']['witnesses']),len(r['B']['uncertain_bindings']),len(r['B']['rejected_bindings'])))
lines+=['', '4. 自动检查与失败范围',
'成功形成结构化视图%d/10案，进入计算的断言%d条。'%(len(views),sum(len(v['events']) for v in views.values())),
'隔离记录原因：'+json.dumps(dict(errors),ensure_ascii=False),
'字段阻止原因：'+json.dumps(dict(blocked),ensure_ascii=False),
'对象关系记录：'+json.dumps(dict(Counter(e['op']+'/'+e['decision'] for reg in edges.values() for e in reg['edges'])),ensure_ascii=False),
'关系隔离原因：'+json.dumps(dict(edge_reject),ensure_ascii=False),
'A/B状态配对：'+json.dumps(summary['A_B_status_pairs'],ensure_ascii=False),
'这些检查证明可读取和引用能定位，不能证明抽取完整或语义正确。保留原始回复，局部字段/记录隔离；没有第二次整案抽取或消除全部未知的修订。', '',
'5. 样本、配置与工作量',
'样本按既有固定候选顺序选取10个模型筛查为完整且符合腾退/返还租赁标的请求的来源。排除原5案和后20案，以及已知重复或关联；未确定关联保留。资格与完整性仍是既有模型来源判断，不是本轮新的人工作证。没有因抽取难或无匹配换案。',
'网页正式提交任务%d个，其中直接回答%d个、一次抽取%d个、局部核查%d个。0次Pro、0次付费API。界面显示普通High，未暴露确切模型编号。'%(len(submissions),sum(s['kind']=='DIRECT_FULL_SOURCE_ANSWER' for s in submissions),sum(s['kind'].startswith('SINGLE_STRUCTURED') for s in submissions),sum(s['kind']=='FIXED_SMALL_SOURCE_AUDIT' for s in submissions)),
'任务包共%d UTF-8字符；下载JSON共%d字节。网页模型任务重提/格式修复次数0；附件、页面导航及下载恢复另见UI记录。'%(sum(len((ROOT/'web-tasks'/s['batch_id']/'task.txt').read_text()) for s in submissions),sum(s['bytes'] for s in retrievals)),
'从固定配置保存到交付约%.1f分钟，包含浏览器恢复、网页生成及本地导入。'%( (now-start).total_seconds()/60),
'核心算法代码与冻结哈希一致，未新增或重跑全套程序测试；自动哈希、JSON和来源引用检查属于本轮导入步骤，不能作为法律能力成绩。', '',
'6. 文件与停止状态',
'入口：tasks.json、config.json、freeze.json、sample.json；sources/完整判决和稳定段落编号；web-tasks/原始任务、下载回复、URL、时间、设置、截图；views/和relations/计算视图、隔离记录及关系；runs/first-run/results.json全部30题的匹配/未知/失败组合，summary.json和audit-selection.json保存完整计数与抽样。',
'本轮止于10案和实际不超过6项复核。没有根据这些新案件更改抽取规范、查询条件、关系定义或原执行器；没有开启下一轮修复。']
(run/'report-detail-zh.txt').write_text('\n\n'.join(lines)+'\n')
brief='''10个新案件探索性实验：已有关系是否正确匹配？

结论：本轮没有找到完整模式匹配，因此还不能确认已有模式在新案件中的正例识别能力。有限抽查支持程序对3个具体组合的排除，但没有证明整体准确率提高。两个方法均已完成10案、每案3题；127条主请求记录进入计算，4条其他请求记录保留原版并隔离。

本轮沿用原来的3题、事实规范和关系执行器，按既有队列选取完整来源，没有因难例或无匹配换案。已排除旧5案、旧20案和已知重复/关联；未查清的关联仍有标记，不能称为已确认独立的纠纷。固定题目分别要求：法院认定的转租标的属于文书叙述的拥有标的；另案提起人属于腾退被请求人群体；租赁承租人属于该群体。题目包含特定陈述状态与关系方向。后两题是程序或混合关系诊断，不是实体事实规律。

方法输出（不是准确率）
方法                  完整匹配    信息不足    未找到
A 完整判决直接回答       0           4        26
B 一次抽取后关系执行     0          21         9
同份事实的类型共现      16          11         3

转租部分题：A在10案均未找到，B有7项未知、3项未找到。另案提起人题：A为2项未知、8项未找到，B为7项未知、3项未找到。承租人题也是这一分布。B另外记录了12条成员关系和1条部分关系提议，引文可定位，但尚未整体语义核验；存在这些关系，不代表同时满足固定模式的事实类型与陈述状态。共现的16项仅说明需要的事实类型同时出现，没有检查完整关系，不能直接计为错误。“未找到”不是现实中不存在；未知与暂不支持分开，本轮没有整案导入失败或方法输出暂不支持。

按预存排序和种子20261001，实际核查3个共现与关系判断不同的组合，来自2案。正匹配候选为0，所以没有补齐6项。普通High的一次集中来源复核认为，3组断言有来源，但题目要求的群体成员关系均不成立；6段核查引文全部能在原文定位。这是模型参考判断，不是人工金标准，也未核查整案的所有候选。

具体区别：1170087案原文写Janardhan是该土地承租人，也写追索占有的程序针对Janardhan。两端指向同一人，不能因此构造“Janardhan属于被请求人群体”。265203案中，被请求腾退的Sarup Singh Gupta后来提起二审及特别许可申请，另外两组也是同一人的身份重合。程序排除这3组符合固定题意；如果另一个题目问“是否为同一个人”，则答案可能相反。因此，这些共现组合不是毫无联系，只是不满足当前成员关系。

主要阻碍也已暴露。B的21项未知全部出现在同样7案中；记录使用“全部字段尚未确定”的限制符号*，执行器会把原有事件类型也视为未确定。例如1982777案的PAY_RENT记录因欠租区间不能表示成单次付款而受限，竟进入了转租/所有权查询的未知候选。这个执行轨迹说明，不确定性的传播范围过大可能压低可判定率；它不证明原文真的缺少21项答案。A在其中17项回答未找到，但这些较明确的回答没有逐项核查，不能把A较少未知解释成A更准确。本轮未确认执行器违反其既有规则，也没有对全部抽取进行语义审核；无法把每项失败都归因于抽取错误、资料缺失或模式未出现。

下一步最值得修改的是“不确定字段如何影响查询”的抽象与执行接口：保留可靠的事件类型，只让未解析的对象、时间或范围阻止依赖那些字段的判断。是否能安全这样做，要在下一轮核验；本轮没有改变规则或统一未知为否定。现有3题可以保留为边界诊断任务，但本批材料缺少已确认的正匹配实例，尚不足以形成兼有正负例的完整匹配测试。

工作量：6个普通High网页任务，包含2批直接回答、3批单次抽取、1批局部复核；每案A与B使用独立对话和同一完整来源。0次Pro、0次付费API、0次格式修复、0次模型任务重提。界面未显示确切模型编号。自配置保存到报告约ELAPSED分钟，含页面恢复和下载时间。核心方法哈希保持不变，未新增全套程序测试。全部回复、出处、对象绑定、未知、隔离原因、网页URL及截图已保存；本轮结束于10案与3项抽查，没有增加样本、重标旧案或开启修复轮次。

文件入口：sample.json和sources/保存样本与完整来源；tasks.json/config.json/freeze.json保存预定任务和方法；runs/first-run/results.json包含全部30题及所有匹配/未知/失败组合；audit-selection.json、web-tasks/audit-001/import-v1/audit.json保存选择与原文复核；report-detail-zh.txt保存逐案详细记录。
'''
(run/'report-zh.txt').write_text(brief.replace('ELAPSED','%.1f'%((now-start).total_seconds()/60)))
write_new(ROOT/'status-complete-v1.json',{'completed_at':now.isoformat(),'selected_cases':10,'question_results':30,'usable_structured_cases':len(views),'audit_items':len(audit['items']),'method_unchanged':True,'formal_benchmark_verified':False,'accuracy':None,'web_tasks':len(submissions),'format_repairs':0,'held_out':False,'dispute_independence_proven':False,'report':str(run/'report-zh.txt'),'source_reference_kind':'MODEL_REFERENCE_WITH_SOURCE_REVIEW_NOT_HUMAN_GOLD'})
print(json.dumps({'report':str(run/'report-zh.txt'),'B_matching_cases':len(positive_cases),'A_matching_cases':len(a_positive_cases),'audit_items':len(audit['items'])}))
