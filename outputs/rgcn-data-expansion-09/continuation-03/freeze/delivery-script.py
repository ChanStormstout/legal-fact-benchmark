import json,hashlib,shutil,datetime,collections
from pathlib import Path
B=Path('outputs/rgcn-data-expansion-09');O=B/'continuation-03'
def load(p):return json.loads(Path(p).read_text())
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=load(O/'imports/final-01/import-report.json')['tasks'];ls=[x for x in r if 'known'in x];gs=[x for x in r if 'nodes'in x];pairs=set(x['case_id'] for x in ls)&set(x['case_id'] for x in gs)
a=load(O/'registration.json');bad=[p for p,h in a['old_hashes'].items() if sha(p)!=h];assert not bad
save(O/'preservation-audit.json',{'old_files':len(a['old_hashes']),'changed':bad,'v08':'356 files +3 source files preserved'})
for name in ['split-manifest.json','mechanism-stage-coverage.json']:
 shutil.copyfile(B/'continuation-02'/name,O/name)
summary={'status':'BOUNDED_PENDING_TASK_COMPLETION','train_registered':27,'development':6,'sealed':8,'graph_interfaces':len(gs),'label_interfaces':len(ls),'paired_interfaces':len(pairs),'known_new_labels':sum(x['known'] for x in ls),'isolated_new_labels':sum(x['isolated'] for x in ls),'old113_preserved':True,'new_calls':2,'replacement_calls':1,'cumulative_user_submissions':57,'new_sources':0,'training':False,'publication':'LOCAL_ONLY_NO_COMMIT_NO_PUSH','held_case':'125596702','reference_role':'MODEL_GENERATED_SOURCE_ANCHOR_CHECKED_NOT_HUMAN_GOLD'}
save(O/'completion-status.json',summary)
save(O/'training-gate.json',{'open':False,'reason':['27_SOURCE_TRAIN_BELOW30','8_SEALED_BELOW10','125596702_PROTOCOL_HOLD','SEMANTIC_ACCEPTANCE_PENDING'],'graphs':len(gs),'label_interfaces':len(ls),'paired_interfaces':len(pairs),'training':False})
report=f'''V09 continuation-03：剩余任务与重复标签处置

本轮沿用27 TRAIN、6 DEVELOPMENT、8 SEALED和固定30项法源。新完成33810117图任务；1106992原文件再次显示无法加载，因此用原任务文件、原High执行要求在独立对话做一次替代生成，旧失败未覆盖。实际两次网页提交，其中一次为文件不可恢复后的替代，不把它描述为最初单次输出。累计用户提交57次（含上一轮误重复），本轮未扩来源、未训练、未生成完整法律回答、未提交或推送。

最终导入得到{len(gs)}份图、{len(ls)}份用途标签、{len(pairs)}案接口配对。新用途标签已知{summary['known_new_labels']}条、隔离{summary['isolated_new_labels']}条，旧113条参考另存不变。这里只完成格式、引用和构图接口校验，不能称为全部语义正确。未知、未标记和隔离均不作负例；图输入不读取用途监督。原始回复、完整JSON、对话URL及实际模式保存在web/，确切模型名称与token数不可得。

125596702没有第一份完整答案可供比较，因此无法确定重复指令是否影响内容。原标签30条中22条法源引文不精确，仅8条通过既有地址检查。有限原文核对确认：L80/L84是租户主张与证言，L87是房东的举证责任论点，L88是租户的反论，不能把持续控制直接写成目标法院已认定。家庭允许使用与举证责任法源确实涉及争点，但这不证明全部用途分类正确。保留整个标签的流程隔离，不改写22条引文、不偷偷接纳8条，也没有重新生成125596702。细节见duplicate-disposition.json和duplicate-label-format-audit.json。

恢复工作减少了技术缺项，但V09整体仍未达到30 TRAIN/10 SEALED目标，125596702的标签仍隔离，其他单次模型标签尚未完成语义验收。训练门槛继续关闭，不以27份图齐备代替训练数据质量达标。准备预算已经结束，本轮没有重新筛案。后续需要明确处理标签验收与样本缺口，不能在此状态直接声称已具备冻结主训练数据。

原方法、法源池、允许来源和S/B/C主训练协议未改。新的导入适配仅选择本轮两份文件，继续复用原校验器并保留重复标签隔离。四项直接相关的适配检查通过（完整JSON、多个结果拒绝、错误案件ID拒绝、旧隔离保留），未重跑无关程序测试。登记的{len(a['old_hashes'])}个上一轮文件哈希保持，V08的356冻结文件及3个源码另行核验保持。
'''
(O/'report-zh.txt').write_text(report)
oldcur=load('docs/PROJECT_STATE.json')['current_review'];cur={**oldcur,'title':'V09 remaining task completion','report':str(O/'report-zh.txt'),'summary':f'27 TRAIN／6 DEV／8 SEALED；{len(gs)}图、{len(ls)}标签、{len(pairs)}案接口配对。补2项，125596702标签保留隔离；未训练或推送。','preparation_freeze':str(O/'delivery-freeze.json'),'stage_description':report}
for p in ['docs/PROJECT_STATE.json','docs/repository-artifacts.json']:
 x=load(p);x['current_review']=cur
 if p.endswith('PROJECT_STATE.json'):x['development_follow_up']['rgcn_data_expansion09_pending_completion']=summary
 save(p,x)
p=Path('README.md');txt=p.read_text();p.write_text('最新[V09剩余任务报告]('+cur['report']+')：'+cur['summary']+' 旧结果保持；接口完成不等于语义验收。\n\n'+txt[txt.index('历史第08轮'):])
p=Path('docs/CHANGELOG.md');p.write_text('# 2026-10-05 V09 continuation-03\n\n'+cur['summary']+' 一次标签替代生成单列，22条重复任务中的非精确引文未修补。\n\n'+p.read_text())
x=load('docs/EXPERIMENTS.json');x['experiments'].append({'id':'rgcn-data-expansion-09-continuation-03','role':'bounded_data_preparation','report':cur['report'],'note':cur['summary']});save('docs/EXPERIMENTS.json',x)
p=Path('docs/EXPERIMENT_INDEX.md');p.write_text(p.read_text()+'\n| rgcn-data-expansion-09-continuation-03 | data preparation | [报告](../'+cur['report']+') | '+cur['summary']+' |\n')
(O/'freeze').mkdir(exist_ok=True);shutil.copyfile('scripts/rgcn09_finish_pending.py',O/'freeze/rgcn09_finish_pending.py');shutil.copyfile('/tmp/v09_cont3_close.py',O/'freeze/delivery-script.py')
save(O/'delivery-freeze.json',{'role':'POST_PREPARATION_DELIVERY','files':{str(p):sha(p) for p in O.rglob('*') if p.is_file() and p.name!='delivery-freeze.json'},'training':False})
print(summary)
