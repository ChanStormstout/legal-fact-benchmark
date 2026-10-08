#!/usr/bin/env python3
"""Post-fit reporting only. Does not change inputs, masks, fitting or predictions."""
import collections, csv, hashlib, json, statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
R=ROOT/'outputs/gnn-irac-application-development-01'
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def pred(r):return max(range(3),key=lambda i:r['probabilities'][i])
def main():
    manifest=read(R/'construction-manifest.json');summary=read(R/'training/summary.json')
    rows=read(R/'training/all-predictions.json');classes=['SATISFIED','DEFEATED','UNRESOLVED']
    target={m['case_id']:read(R/'targets'/f"{m['case_id']}.json") for m in manifest}
    counts=collections.Counter();reasons=collections.Counter();coverage=[]
    for m in manifest:
        tt=target[m['case_id']]['adapted_targets']
        for t in tt:
            if t['supervision_mask']:counts[t['target']]+=1
            reasons.update(t['mask_reasons'])
        inp=read(R/'inputs'/f"{m['case_id']}.json");g=read(R/'graphs'/f"{m['case_id']}.json")
        coverage.append(dict(case_id=m['case_id'],family=m['family'],stage=m['target_stage'],court=m['target_court'],group_id=m['group_id'],association=m['association'],planned_conditions=len(tt),supervised_conditions=sum(t['supervision_mask'] for t in tt),facts=len(inp['facts']),evidence=len(inp['evidence']),nodes=len(g['nodes']),edges=len(g['edges'])))
    save(R/'data-quality.json',dict(candidates=31,packages=len(manifest),family_counts=collections.Counter(m['family'] for m in manifest),planned_conditions=sum(x['planned_conditions'] for x in coverage),class_counts=counts,supervised_packages=sum(x['supervised_conditions']>0 for x in coverage),mask_reason_counts_overlapping=reasons,packages_detail=coverage,reference_kind='MODEL_GENERATED_SOURCE_REVIEWED_NOT_HUMAN_GOLD',sealed_read=False,known_cross_document_associations=[],association_complete=False,all_packages_exposed_development=True))
    with (R/'package-coverage.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(coverage[0]));w.writeheader();w.writerows(coverage)
    split=read(R/'training-freeze.json')['folds'];fit_counts=[]
    for s in split:
        c=collections.Counter(t['target'] for m in manifest if m['group_id'] in s['fit_groups'] for t in target[m['case_id']]['adapted_targets'] if t['supervision_mask'])
        fit_counts.append(dict(fold=s['fold'],fit_class_counts=c,validation_groups=s['validation_groups'],test_groups=s['test_groups']))
    save(R/'training/fold-label-coverage.json',fit_counts)
    comparison=[]
    for method in ['P','Flat','Graph']:
        items=[summary['metrics']['P']] if method=='P' else list(summary['metrics'][method].values())
        rr=[x for x in summary['runs'] if x['kind']==method]
        comparison.append(dict(method=method,seeds=0 if method=='P' else 3,macro_f1_mean=statistics.mean(x['macro_f1_observed_classes'] for x in items),macro_f1_range=[min(x['macro_f1_observed_classes'] for x in items),max(x['macro_f1_observed_classes'] for x in items)],dispute_mean_correct=statistics.mean(x['dispute_mean_correct'] for x in items),dispute_balanced_logloss=statistics.mean(x['dispute_balanced_probability_loss'] for x in items),defeated_recall=[x['per_class_recall'][1] for x in items],parameters=rr[0]['parameters'] if rr else 0,fit_seconds=sum(x['seconds'] for x in rr),peak_mlx_bytes=max((x['peak_mlx_memory_bytes'] for x in rr),default=0)))
    save(R/'comparison.json',comparison)
    with (R/'comparison-table.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(comparison[0]));w.writeheader();w.writerows(comparison)
    protocol=read(R/'case-study-protocol.json');distance=[]
    for ident in sorted({x['package_id'] for x in rows}):
        a={x['condition_id']:x for x in rows if x['package_id']==ident and x['method']=='Flat' and x['seed']==20261006}
        b={x['condition_id']:x for x in rows if x['package_id']==ident and x['method']=='Graph' and x['seed']==20261006}
        d=statistics.mean(sum(abs(v-w) for v,w in zip(a[k]['probabilities'],b[k]['probabilities'])) for k in a)
        distance.append(dict(case_id=ident,mean_probability_l1=d))
    extras=[x['case_id'] for x in sorted(distance,key=lambda x:(-x['mean_probability_l1'],x['case_id'])) if x['case_id'] not in protocol['fixed_cases']][:protocol['extra_max']]
    selected=protocol['fixed_cases']+extras
    notes={
      '112400':'3个成立标签有来源支持；所有权和住宅不适宜与允许输入对应。但C03/C04部分依赖从“该请求成立”推认构成条件，弱于逐项独立裁判。C02缺少关于提高租金的背景，被局部屏蔽。Fold0拟合中没有该family，两个模型均预测成立，不能证明读取了这些事实。',
      '114533':'C02是房东未尽证明责任，不是转租事实被证明确实为假。输入保存租户否认、夫妻关系的下级认定及房东未调查的承认。原文目标理由拒绝转租推论。P、Flat、Graph均漏掉该DEFEATED；该案所在Fold1拟合数据没有任何DEFEATED，这是重要划分限制，而不是必须补负例的理由。',
      '50313565':'输入保留儿子开关店门、协助父亲以及继续控制的相反主张，但目标法院依赖未取得内容的营业归属文件。三个可解释的历史判断仍因input_sufficient=false屏蔽。该包构图但没有监督，因此没有留出评分；不能将模型生成的“成立”概率当成对真实未决的评价。',
      '1114159':'仅住宅用途C01有可监督的成立判断：允许输入含下级住宅用途认定，目标原文接受住宅用途。其他需求、受益人及住所条件没有独立决定，所有权缺购房事实。Flat/Graph最高概率同类，但概率差异最大，不能把概率差异包装成法律推理机制。',
      '1870868':'1954年起租与已成立转租的采纳支持C01；目标“sub-letting has been substantiated”支持C02。允许输入含租约日期及Tribunal的转租认定；二者不是本轮目标法院认定。C01地址只移除显示层citation wrapper后可定位，未改法律字词、标签或依据。两个模型均猜成立，尚未证明对象/日期关系被利用。'
    }
    case_studies=[]
    for ident in selected:
        m=next(x for x in manifest if x['case_id']==ident);inp=read(R/'inputs'/f'{ident}.json')
        case_studies.append(dict(case_id=ident,selection='PREDECLARED' if ident in protocol['fixed_cases'] else 'PREDECLARED_PROBABILITY_DISTANCE_RULE',analysis=notes[ident],target_conditions=target[ident]['adapted_targets'],input_sources=inp['provenance'],oof_predictions=[x for x in rows if x['package_id']==ident],reference_kind='MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',no_post_fit_label_or_feature_change=True))
    save(R/'case-study.json',dict(protocol=protocol,distance_ranking=sorted(distance,key=lambda x:(-x['mean_probability_l1'],x['case_id'])),selected=selected,cases=case_studies))
    lines=['# 一次集中案例分析','', '预先固定112400、114533、50313565，另按种子20261006的Flat/Graph平均概率L1差异选择1114159和1870868。未按正确与否选例，没有修标签或重新训练。','']
    for s in case_studies:
        lines += [f"## {s['case_id']}",'',s['analysis'],'']
        for t in s['target_conditions']:
            if t['supervision_mask']:
                lines += [t['condition_id']+' → '+t['target']+'；依据：'+', '.join(x['source_id'] for x in t['target_refs']), '']
    (R/'case-study.md').write_text('\n'.join(lines))
    # These are independent invariants, not accuracy certification.
    initial=read(R/'historical-preservation-before.json');changed=[];missing=[]
    for p,h in initial.items():
        path=ROOT/p
        if not path.exists():missing.append(p)
        elif hashlib.sha256(path.read_bytes()).hexdigest()!=h:changed.append(p)
    save(R/'preservation-after.json',dict(checked=len(initial),changed=changed,missing=missing,old_bytes_preserved=not changed and not missing))
    cfg=read(R/'training-freeze.json');fail=[p for p,h in cfg['hashes'].items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    save(R/'frozen-integrity-after.json',dict(checked=len(cfg['hashes']),changed=fail,passed=not fail,training_runs=len(summary['runs'])))
    ui_errors=[p.stem for p in (R/'web').glob('*.snapshot.txt') if '分析出错' in p.read_text()]
    save(R/'web/tool-display-anomalies.json',dict(tasks=ui_errors,count=len(ui_errors),interpretation='UI analysis/tool error remained visible; complete retained JSON or static original literals were imported separately. This does not certify the web file tool succeeded, or establish semantic correctness. No model retry.'))
    ledger=read(R/'web/ledger.json');save(R/'cost.json',dict(ordinary_High_calls=len(ledger),Pro=0,paid_api=0,semantic_retries=0,format_model_retries=0,web_ui_error_tasks=ui_errors,actual_visible_model='Latest',mode='High',exact_model=None,web_tokens=None,web_elapsed_exact=None,mlx_real_fits=len(summary['runs']),real_fit_seconds=sum(x['seconds'] for x in summary['runs']),encoder=read(R/'text-cache/encoding.json')|{'audit':'see text-cache/encoding.json'},peak_mlx_bytes=max(x['peak_mlx_memory_bytes'] for x in summary['runs']),engineering_smoke_not_legal_evaluation=True))
    save(R/'status.json',dict(status='COMPLETED_REAL_GROUPED_DEVELOPMENT_COMPARISON',packages=len(manifest),supervised_conditions=sum(counts.values()),supervised_groups=8,real_fits=18,ordinary_High_calls=34,sealed_read=False,new_legal_answers=0,committed=False,pushed=False,decision='NO_EVIDENCE_TO_EXPAND_GRAPH; RETAIN_RUNNABLE_INTERFACE; NEXT_RESEARCH_NEEDS_CONTRASTIVE_SUPERVISION_NOT_PARAMETER_SEARCH',stopped=True))
    table='\n'.join(f"{x['method']}: F1 {x['macro_f1_mean']:.3f}（范围{x['macro_f1_range'][0]:.3f}–{x['macro_f1_range'][1]:.3f}），纠纷组平均正确比例{x['dispute_mean_correct']:.3f}，组均概率损失{x['dispute_balanced_logloss']:.3f}，DEFEATED召回{','.join(str(v) for v in x['defeated_recall'])}" for x in comparison)
    report=f'''IRAC条件适用开发实验01：已经完成真实训练，暂不扩大图模型

本轮完成31份已有完整来源的集中筛查、两套独立法源模板、17个真实问题包与图、34次普通High任务、冻结E5缓存，以及三折×三种子×Flat/Graph共18次真实拟合。训练已实际反向传播和更新参数，不是合成接口演示。没有完整法律回答、自动找法、胜败预测、规则归纳、SEALED访问、提交或推送。

实际任务与数据
预测对象是给定法律标准下目标法院对单个条件的实体裁判状态。不是“事实现实为真”，也不是整案胜败。2案属于历史住宅需要14(1)(e)，15案属于14(1)(b)。两类各6个固定条件，计划102条件；只有8个问题包的13条件有来源审阅且输入充分的目标：10 SATISFIED、3 DEFEATED、0 UNRESOLVED。全体监督覆盖13/102=12.75%；参与分组比较的8包覆盖13/48=27.08%，其余9包仍有安全输入图，但无监督，不进入拟合或留出计分。

42项NOT_DECIDED明确不入损失；46项输入充分性未确认，与其他屏蔽原因有重叠。未知标签不是否定，程序性恢复/驳回不倒推所有实体条件。引文地址的可逆显示标记映射只恢复1870868的一个条件，初始12条件结果及原字节保留。其他页脚跳过或内容不连续引文继续失败。84524189的一项对象引文失败，13条依赖记录局部隔离，其余2事实仍可构图。来源审阅未新增隔离，不等于已经证明全部语义正确。

模型与隔离
输入任务只见批准子跨度与独立给定规则；目标和监督mask另存，不参与条件节点有无、边或文本特征。Issue/Rule/Condition/Fact/Evidence/Entity六种节点保留身份、陈述状态和阶段。所有事实/证据与条件生成无支持方向的候选连接，标记为计算关系而非证据证明。Flat读取同样节点及有向关系三元组；Graph仅增加两层R-GCN传播。E5-small-v2 revision ffb93f3bd4047442299a41ebb6fa998a38507c52，query前缀、384维、全token覆盖分块，不微调。本轮271个独立节点文本未超过单块容量。给定模板是oracle选择，不证明自动检索；法条当前复制与历史范围不确定、住宅旧条文缺Explanation覆盖均已保留。组内canonical没有真实接入，此处使用本地native接口。

按DOC纠纷组分三折，内部验证组独立早停，种子20261006/7/8。未发现已知同纠纷跨文书，但关联核验不完整，不能声称8组完全独立。所有案例暴露过开发/历史筛查，不是sealed或独立测试。48个留出条件节点中只有13有目标，模型对其他节点仍可输出概率但不作为已知正确性评分。固定18次拟合均成功；每次初始梯度非零，参数更新非零。Flat45,571参数，Graph78,491参数，信息相同但容量不严格相同。

分组留出结果（相对模型来源审阅参考，非人工金标准）
{table}

三个DEFEATED全部位于Fold1留出组，该折拟合数据恰好只有SATISFIED。这是预先随机分组在极小数据上的重要限制，不改折、不补造负例。Flat所有种子输出全SATISFIED，Graph两种子同样全SATISFIED，另一种子还错掉一个SATISFIED。两种网络相对P的表面正确比例增加不能证明利用了案件事实；这与直接全猜多数类一致，而且神经模型概率损失明显恶化，出现高置信误判。DEFEATED的0召回和第三类完全未覆盖，比总体正确比例更决定本轮结论。

以组为单位、先跨种子平均的2000次描述性bootstrap：Flat−P均值+0.125、95%范围[0,0.375]；Graph−Flat −0.0139、范围[−0.0417,0]。这不是独立测试显著性。按family及完整阶段的细分见training/summary.json；每个阶段样本极少，不能据细分选有利范围。

一次案例分析
固定112400、114533、50313565，按预定概率差异加入1114159、1870868。114533的“未证明转租”被两网络误判成立；50313565缺目标法院依赖的营业文件，不硬要求还原其未充分输入的条件；112400部分构成条件标签依赖历史请求成立的推认，需视为较弱参考；1114159最高概率同类的差异不证明推理改善；1870868保留1954租约与下级转租认定，不能把已知来源或日期变成已验证网络机制。关键原文位置、允许来源、各条件依据与全部预测见case-study.json/md。没有训练后改标签、扩例或返工。

成本与验证
34次普通High（8筛查、2规则、1规则审阅、9输入、9目标、5集中来源审阅），实际界面Latest/High，确切型号、网页tokens及精确生成耗时不可得，不写成GPT-6。没有语义/格式模型重试；下载失败通过已保存可见JSON或工具生成代码的静态字面量恢复，未执行第三方代码、未修语义。提交文件部分在提交后从未修改任务原文补存，不能称作全程发送前快照。E5 CPU编码约{read(R/'text-cache/encoding.json')['seconds']:.2f}秒，进程峰值RSS约373.2MiB；18拟合内部计时合计{sum(x['seconds'] for x in summary['runs']):.2f}秒，不包含网页、数据准备、初始化与报告。MLX峰值与每次epoch/损失、梯度、参数变化、weights保存在本地日志，权重不入审阅包。19项直接相关测试通过，只证明工程行为。冻结前路径相对/绝对混用阻止freeze，已改通用路径规范化，原失败日志保留；发生于任何真实拟合之前。8,243个历史文件原字节及训练冻结哈希另行核验。

投入决定
保留已实现的条件级数据接口、部分监督、Flat/R-GCN可运行训练；本轮没有支持扩大GNN或宣称法律适用收益的证据。也不能断言Flat取得事实条件化能力：少数类漏检、概率过度自信、反例集中于一折与两个family覆盖不均，使这次比较更接近监督质量和任务可判别性诊断。下一步若另行授权，应先取得同一模板/条件在不同纠纷中有明确相反实体判断、且允许输入足够的监督，再评价是否超过不读案件的先验；不继续参数扫描。本轮已按预算完成并停止，SEALED继续封存。全部产物本地另存，旧实验不改。
'''
    report=report.replace('提交文件部分在提交后',f'{len(ui_errors)}个保存页面另显示“分析出错”，完整可读JSON或静态原始数据另行保存导入，不能将其称为网页工具全部成功；详见web/tool-display-anomalies.json。提交文件部分在提交后')
    (R/'report-zh.txt').write_text(report)
    print(json.dumps(dict(comparison=comparison,case_study=selected,historical_changed=len(changed),frozen_changed=len(fail)),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
