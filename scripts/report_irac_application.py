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
    lines=['# One Concentrated Case Analysis','', 'Cases 112400, 114533 and 50313565 were fixed in advance; 1114159 and 1870868 were selected by Flat/Graph mean-probability L1 differences under seed 20261006. Selection was not based on correctness; labels were not repaired and models were not retrained.','']
    for s in case_studies:
        lines += [f"## {s['case_id']}",'',s['analysis'],'']
        for t in s['target_conditions']:
            if t['supervision_mask']:
                lines += [t['condition_id']+' → '+t['target']+'; evidence: '+', '.join(x['source_id'] for x in t['target_refs']), '']
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
    table='\n'.join(f"{x['method']}: F1 {x['macro_f1_mean']:.3f} (range {x['macro_f1_range'][0]:.3f}–{x['macro_f1_range'][1]:.3f}), dispute-group mean correctness {x['dispute_mean_correct']:.3f}, group-balanced log loss {x['dispute_balanced_logloss']:.3f}, DEFEATED recall {','.join(str(v) for v in x['defeated_recall'])}" for x in comparison)
    report=f'''IRAC condition-application development01: real training completed; graph expansion paused

Completed consolidated screening of31 existing complete sources, two independent legal templates,17 real question packs/graphs,34 ordinary High tasks, frozen E5 caches, and18 actual fits across three folds × three seeds × Flat/Graph. Backpropagation and parameter updates actually occurred; this was not synthetic interface demonstration. No complete legal answers, automatic legal retrieval, outcome prediction, rule induction, SEALED access, commit, or push occurred.

Task and data
The target is the target court's merits assessment of an individual condition under a given legal standard, not real-world factual truth or whole-case outcome. Two cases concern historical residential need14(1)(e),15 concern14(1)(b). Each family has six fixed conditions,102 planned in total. Only13 conditions in eight packs have source-reviewed targets with sufficient input: ten SATISFIED, three DEFEATED, zero UNRESOLVED. Supervision covers13/102=12.75% overall and13/48=27.08% in the eight grouped-comparison packs. Nine other packs retain safe input graphs but no supervision, fitting, or held-out scoring.

All42 NOT_DECIDED items are excluded from loss. Input sufficiency is unconfirmed for46 items, overlapping other masks. Unknowns are not negatives; procedural restoration/dismissal does not imply every merits condition. Reversible citation-display mapping restores only one1870868 condition; the initial12-condition results/bytes remain. Other skipped-footer/noncontiguous quotations continue to fail. One84524189 object citation fails, locally isolating13 dependent records while two other facts remain graphable. No new source-review isolation does not prove complete semantic correctness.

Models and isolation
Input tasks see approved subspans and independently supplied rules only. Targets/supervision masks are separate and do not determine condition-node presence, edges, or features. Issue/Rule/Condition/Fact/Evidence/Entity nodes preserve identity, status, and stage. Facts/evidence connect to conditions through direction-free candidate links marked computational, not evidentiary proof. Flat reads the same nodes/directed-relation triples; Graph adds two R-GCN layers. Frozen E5-small-v2 revisionffb93f3bd4047442299a41ebb6fa998a38507c52 uses query prefixes,384 dimensions, complete-token chunking, no fine-tuning. None of271 distinct node texts exceeds one chunk. Supplied templates are oracle selection, not automatic retrieval. Current/historical statutory uncertainty and missing old residential Explanation coverage remain. Real group canonical data are not connected; this uses the local native interface.

Three DOC-dispute folds use independent internal validation/early stopping and seeds20261006/7/8. No known cross-document shared dispute was found, but relationship checks are incomplete; eight fully independent groups are not claimed. All cases were exposed in development/screening, not sealed independent testing. Of48 held-out condition nodes, only13 have targets; probabilities on others are not correctness scores. All18 fits succeeded with nonzero initial gradients/parameter changes. Flat has45,571 parameters; Graph78,491, so information is matched but capacity is not.

Grouped held-out results, against source-reviewed model references, not human gold
{table}

All three DEFEATED items fall in Fold1's held-out group, leaving only SATISFIED training examples in that fold. This is a major limitation of the predefined random split on tiny data; folds/negative examples were not changed or fabricated. Flat predicts all SATISFIED for every seed. Graph does so for two seeds and additionally misses one SATISFIED for the third. Apparent correctness gains over P do not establish use of case facts; majority guessing explains them, while neural probability loss worsens with confident errors. Zero DEFEATED recall and no third-class coverage are more decisive than overall correctness.

After averaging seeds within groups,2,000 descriptive bootstrap samples give Flat−P mean+0.125,95% interval[0,0.375], and Graph−Flat−0.0139, interval[−0.0417,0]. These are not independent-test significance claims. Family/full-stage breakdowns are in training/summary.json; strata are too small for selecting favorable scopes.

One case analysis
Fixed112400,114533,50313565 and added1114159/1870868 under predefined probability-difference rules. Both networks misclassify114533's unproved subletting as satisfied.50313565 lacks business documents used by the target court, so unsupported-input conditions are not forced to match its result. Some112400 labels infer conditions from historical claim success and are weaker references. Same-class probability differences for1114159 do not prove better reasoning.1870868 retains a1954 lease/lower-court subletting finding; known sources/dates are not verified network mechanisms. See case-study.json/md for anchors, allowed sources, condition grounds, and all predictions. No post-training relabeling, expansion, or rework occurred.

Costs and verification
Thirty-four ordinary High calls: eight screens, two rules, one rule review, nine inputs, nine targets, five source reviews. UI Latest/High did not expose exact model, browser tokens, or exact generation times; it was not labeled GPT-6. No semantic/format model retries occurred. Failed downloads were recovered from visible saved JSON or static literals in generated code, without running third-party code or changing semantics. Some submission files were saved afterward from unchanged task text, not falsely presented as complete pre-send snapshots. E5 CPU encoding took about {read(R/'text-cache/encoding.json')['seconds']:.2f}s, peak process RSS about373.2MiB. Internal18-fit time totals {sum(x['seconds'] for x in summary['runs']):.2f}s, excluding browser/data preparation/initialization/reporting. MLX peaks, epochs/losses/gradients/parameter changes/weights remain in local logs; weights are excluded from review packages. Nineteen tests establish engineering behavior only. A relative/absolute path mix blocked preparation freeze and was generically normalized before any fit; failed logs remain. All8,243 old-file bytes and training-freeze hashes were checked separately.

Decision
Retain condition-level interfaces, partial supervision, and runnable Flat/R-GCN training, without evidence for graph expansion or legal-application benefit. Flat has not demonstrated factual conditioning either. Minority misses, overconfidence, all negatives in one fold, and family imbalance make this mainly a supervision/task-discriminability diagnosis. If later authorized, obtain sufficient permitted inputs and opposite explicit merits judgments for the same conditions across disputes before testing against case-blind priors. Do not continue parameter sweeps. This budgeted round is complete/stopped, SEALED stays sealed, and separate local artifacts preserve old experiments.
'''
    report=report.replace('Some submitted files after submission',f'{len(ui_errors)} saved pages also show an analysis error; complete readable JSON or static raw data were separately saved and imported. Do not claim universal web-tool success; see web/tool-display-anomalies.json. Some submitted files after submission')
    (R/'report-zh.txt').write_text(report)
    print(json.dumps(dict(comparison=comparison,case_study=selected,historical_changed=len(changed),frozen_changed=len(fail)),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
