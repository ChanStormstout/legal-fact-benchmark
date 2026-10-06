"""Fixed six-fit descriptive DEV comparison; conservative predeclared investment rules."""
import sys,json,hashlib,csv,collections,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
R=Path('outputs/rgcn-sbc-finalization-11')
def read(p):return json.loads(Path(p).read_text())
def save(p,v):
 p=R/p;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError(p)
 p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 cfg=read(R/'protocol.json');fits=read(R/'training-results.json');allrows=read(R/'selection-results.json');by={(x['case_id'],x['seed'],x['method']):x for x in allrows};comparisons=[];table=[];detail=[];roles=read(R/'core-role-register.json');rd={(x['case_id'],x['unit_id']):x for x in roles}
 for seed in cfg['training']['seeds']:
  for cid in cfg['dev']:
   slots=read(R/'labels'/f'{cid}.json')['slots'];core={u for u,s in slots.items() if s['state']=='KNOWN' and s['canonical_category']=='CORE'}-set(cfg['training']['mandatory']);rs={k:by.get((cid,seed,k)) for k in ['S','B','C']}
   for k,m in rs.items():
    if not m:table.append({'case_id':cid,'seed':seed,'method':k,'status':'NOT_COMPLETED'});continue
    selected=set(m['selected_ids']);items=[dict(rd[(cid,u)],delivered=u in selected,missing_reason=m['core_missing_reasons'].get(u),role_interpretation='existing condition kinds and use rationale; no new exhaustive semantic gold') for u in sorted(core)]
    detail.append({'case_id':cid,'seed':seed,'method':k,'core_evidence':items,'reference_unavailable':[{ 'unit_id':u,'state':s['state'],'reason':s.get('reason')} for u,s in slots.items() if s['state']!='KNOWN'],'material_file':f'materials/{seed}-{k}-{cid}.txt','metrics':m})
    table.append({'case_id':cid,'seed':seed,'method':k,'status':'OK','core_delivered':m['core_delivered'][0],'core_denominator':m['core_delivered'][1],'feasible_core_delivered':m['feasible_core_delivered'][0],'feasible_core_denominator':m['feasible_core_delivered'][1],'delivered_ids':';'.join(sorted(core&selected)),'missed_ids':';'.join(sorted(core-selected)),'irrelevant_selected':';'.join(m['known_irrelevant_selected']),'irrelevant_characters':m['known_irrelevant_characters'],'unknown_selected':';'.join(m['unknown_selected']),'legal_characters':m['legal_characters'],'source_document_coverage':str(m['core_document_delivered']),'material_sha256':m['material_sha256'],'material_file':f'materials/{seed}-{k}-{cid}.txt'})
   for left,right in [('S','B'),('B','C')]:
    if not rs[left] or not rs[right]:comparisons.append({'case_id':cid,'seed':seed,'left':left,'right':right,'direction':'INCOMPLETE'});continue
    a=set(rs[left]['selected_ids']);b=set(rs[right]['selected_ids']);gain=sorted((b-a)&core);loss=sorted((a-b)&core)
    direction='GAIN_WITHOUT_KNOWN_CORE_LOSS' if gain and not loss else 'KNOWN_CORE_LOSS' if loss and not gain else 'MATERIAL_SWAP_UNRESOLVED' if gain and loss else 'NO_CONFIRMED_CORE_GAIN'
    comparisons.append({'case_id':cid,'seed':seed,'left':left,'right':right,'direction':direction,'core_gained':gain,'core_lost':loss,'all_units_added':sorted(b-a),'all_units_removed':sorted(a-b),'material_set_same':a==b,'full_material_bytes_same':rs[left]['material_sha256']==rs[right]['material_sha256'],'gained_evidence':[rd[(cid,u)] for u in gain],'lost_evidence':[rd[(cid,u)] for u in loss],'not_weighted_score':True})
 summary={}
 for k in ['S','B','C']:
  summary[k]={}
  for seed in cfg['training']['seeds']:
   rows=[m for m in allrows if m['method']==k and m['seed']==seed]
   summary[k][str(seed)]={'cases':len(rows),'core_delivered':sum(m['core_delivered'][0] for m in rows),'core_denominator':sum(m['core_delivered'][1] for m in rows),'irrelevant_selected':sum(len(m['known_irrelevant_selected']) for m in rows),'unknown_selected':sum(len(m['unknown_selected']) for m in rows),'irrelevant_characters':sum(m['known_irrelevant_characters'] for m in rows)}
 def signal(left,right):
  per={}
  for seed in cfg['training']['seeds']:
   xs=[x for x in comparisons if x['seed']==seed and x['left']==left and x['right']==right];per[str(seed)]={'gain_cases':[x['case_id'] for x in xs if x['direction']=='GAIN_WITHOUT_KNOWN_CORE_LOSS'],'loss_or_ambiguous_cases':[x['case_id'] for x in xs if x['direction'] in ('KNOWN_CORE_LOSS','MATERIAL_SWAP_UNRESOLVED','INCOMPLETE')]}
  stable=all(len(x['gain_cases'])>1 and not x['loss_or_ambiguous_cases'] for x in per.values());return {'stable_development_signal':stable,'per_seed':per,'rule':'requires >1 case meaningful gain in both seeds and no known material CORE tradeoff; redundant sources not mechanically independent'}
 bs=signal('S','B');cb=signal('B','C');complete=sum(f['status']=='OK' for f in fits)==6
 decision='STILL_UNDETERMINED_TECHNICAL_FAILURE' if not complete else 'KEEP_C_CANDIDATE' if bs['stable_development_signal'] and cb['stable_development_signal'] else 'KEEP_B_PAUSE_RGCN_EXPANSION' if bs['stable_development_signal'] else 'KEEP_S_NO_STABLE_NET_CASE_CONDITIONED_VALUE_ESTABLISHED'
 save('paired-comparison.json',comparisons);save('case-comparison-detail.json',detail);save('summary.json',{'methods':summary,'B_over_S':bs,'C_over_B':cb,'decision':decision,'DEV_not_independent':True,'not_human_gold':True,'new_legal_answers':0,'sealed_untouched':True})
 fields=list(dict.fromkeys(k for r in table for k in r));f=R/'comparison-table.csv'
 with f.open('x',newline='') as fp:w=csv.DictWriter(fp,fields);w.writeheader();w.writerows(table)
 old=read(R/'historical-preservation-before.json');changed=[p for p,h in old.items() if not Path(p).exists() or sha(p)!=h];save('historical-preservation-after.json',{'checked_files':len(old),'changed':changed,'sealed_content_not_opened':True});assert not changed
 counts=read(R/'cohort-counts.json');ct={s:{t:sum(x['states'][t] for x in counts if x['split']==s) for t in ['KNOWN','UNKNOWN','ISOLATED','UNPROCESSED','REVIEW_NOT_COMPLETED']} for s in ['TRAIN','DEV']};save('final-state-counts.json',ct)
 tasks=read(R/'task-ledger.json');web=[]
 for x in tasks:
  f=R/'web'/f"{x['id']}.completed.json";v=read(f) if f.exists() else read(R/'web'/f"{x['id']}.failure.json");web.append(v)
 tc=read(R/'training-cost.json');save('cost-ledger.json',{'preparation_web_calls':len(list((R/'web').glob('*.submitted.json'))),'semantic_retries':0,'web_tasks':web,'precise_web_tokens_unavailable':True,'web_generation_seconds_observable_only':True,'training':tc,'old_costs_separate':read('outputs/rgcn-dev-contract-repair-10/cost-final.json'),'new_legal_answers':0})
 lines=['S/B/C authority-selection 收尾：V11','',f'决定：{decision}。这是6个已参与开发案件上的材料选择判断，不是独立测试、法律回答正确性或纯图消息传递效应。','',f'27 TRAIN／6 DEV／8 SEALED；30项法源不变。六次固定拟合完成{sum(f["status"]=="OK" for f in fits)}次，失败{sum(f["status"]=="FAILED" for f in fits)}次；网页准备最多12次、语义重试0、新法律回答0。','标签与图分别在独立High对话处理指定四项，共132个位置。其余记录原样继承V10。UNKNOWN、ISOLATED和未完成不进入确定类别loss；现有弱标签不被称为人工金标准。','',f'最终状态：{json.dumps(ct,ensure_ascii=False)}。','', '已知非强制CORE的送达计数（只表示现有不完整参考的覆盖，不作准确率排名）：']
 for seed in cfg['training']['seeds']:
  lines.append(str(seed)+': '+ '；'.join(k+' '+str(summary[k][str(seed)]['core_delivered'])+'/'+str(summary[k][str(seed)]['core_denominator'])+'，已知无关入选'+str(summary[k][str(seed)]['irrelevant_selected']) for k in ['S','B','C']))
 lines+=['','逐案及逐seed的增益、损失、反对规则与范围限制见paired-comparison.json及case-comparison-detail.json。任何重要CORE丢失都不能被重复法源计数掩盖；同一文书不等于段落可替代。计数变化不能证明法律回答改善。','', 'B>S信号：'+json.dumps(bs,ensure_ascii=False),'C>B信号：'+json.dumps(cb,ensure_ascii=False),'',f'本轮训练耗时{tc["seconds"]:.1f}秒；完整成本见cost-ledger.json。网页精确tokens不可得，不估造。',f'历史字节核验{len(old)}文件，无改变；SEALED正文、图和标签未读。首次拟合前代码、数据、图、特征、TRAIN标准化、材料视图及readiness均已冻结。','', 'S不读案件且有30项独立先验；B是18维共享线性模型；C同时增加文本、非线性和图传播，因此不是严格嵌套消融。未对架构、seed、步数或类别权重调参。','', '本轮到此停止，不自动修标签、重训、启封SEALED、生成法律答案、提交或推送。']
 (R/'report-zh.txt').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))
if __name__=='__main__':main()
