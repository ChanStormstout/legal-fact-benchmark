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
lines=['Case | S (seeds 04/05) | B (04/05) | C (04/05) | Labeled core grounds','--- | --- | --- | --- | ---']
for cid in read(R/'protocol.json')['config']['dev_ids']:
 vals={k:[next(x for x in rows if x['case_id']==cid and x['method']==k and x['seed']==s)['core_delivered'] for s in [20261004,20261005]] for k in 'SBC'}
 lines.append(cid+' | '+' | '.join('/'.join(str(x[0]) for x in vals[k]) for k in 'SBC')+' | '+str(vals['S'][0][1]))
save('case-comparison.md','\n'.join(lines)+'\n\nOnly nonmandatory core grounds with explicit references are counted. Unlabeled items are not errors, and multiple grounds in one case are not independent samples.\n')
report='''V09: first S/B/C main training with incomplete27-case supervision, development evaluation

All six fits completed without technical failure. Pause graph-ranking expansion and retain S as comparator: stable B>S/C>B evidence was not obtained. C's better second seed does not cancel its first-seed deterioration, nor prove relations/GNN universally ineffective. No legal answers were generated; complete-answer benefits are unknown.

S learns shared source-use tendencies without case features. B uses18 case–authority relation features from the same graphs in a linear ranker. C retains V08's two-layer,16-dimensional,two-basis R-GCN, combining propagation with those18 features. All predict CORE/BACKGROUND/IRRELEVANT and rank by2×P(CORE)+P(BACKGROUND). Training:200 steps, learning rate0.003,L2 coefficient0.001,seeds20261004/20261005. Average loss within cases, then across cases. No architecture tuning/best-seed selection.

There are27 TRAIN cases and730 computable labels:113 old,609 new, and eight unchanged125596702 labels passing address/quotation checks. The user authorized duplicate submission not to exclude the entire case; its effect remains unknown. Those eight are provisional model references;22 other labels are isolated from loss. Other unknown/unlabeled/isolated items are not negatives. Eight SEALED cases received inventory identity/group checks only, without reading contents/features/evaluation. Known groups do not cross splits; broader relations are incompletely checked.

Six old cases remain DEVELOPMENT only. Just35 old use records map to explicit classes. Other items are excluded from class scoring. After subtracting mandatory14(1)(b),11 labeled CORE authorities remain. The16 added authorities lack use labels/case-condition alignment for these cases. Originals/source-condition nodes are retained with case links UNKNOWN, not fabricated. This may disadvantage case-relation-dependent B/C; evaluation neither fully covers30 sources nor establishes independent generalization.

With the same30 candidates/20,000-character budget, seed04 CORE delivery is S8/11,B7/11,C4/11; seed05 is S8/11,B7/11,C9/11. See case-comparison.md and runs for rankings, probabilities, original packs, and budget decisions. Counts measure confirmed-source coverage, not accuracy or full recall. No selected item is labeled IRRELEVANT, but many lack development labels, so error-free selection is not established. S/B each deliver identical sets across seeds; C varies substantially and two seeds cannot estimate stability.

Specific trade-offs: in110204406,S delivers DRC16 and General Radio's Delhi discussion; B retains the latter but loses16 in both seeds. In58386394,B replaces S's16 with Telesound paragraph16; both score2/3 but differ in content. C seed04 delivers no nonmandatory labeled CORE in either case; seed05 delivers2/3 and3/3. material-changes.json retains every addition/displacement without favorable selection.

Old preference diagnostics are S71/73,B56/73,C59/73 in both seeds. These incomplete model references are not used for tuning/selection. Ranking changes, material delivery, and final legal effectiveness are separate stages; only the first two were tested.

Six fits/local selection took about22.48s, with no new browser/LLM/paid API calls. Fits took S0.27/1.14s,B0.29/1.13s,C8.89/10.15s. Scheduling is included; these are not exact hardware benchmarks. Peak MLX active memory was about500MB, not whole-machine memory. All methods had nonzero gradients/updates and decreasing objectives, proving fitting, not legal correctness. Larger C training-loss improvement did not yield stable development delivery.

Implementation adds only30-candidate and CORE-mapping interfaces, preserving V08. Missing development links remain UNKNOWN. Four checks cover class/isolation masks,30-dimensional shared comparator, missing alignment, and TRAIN-only normalization. A preparation absolute-path snapshot error was corrected before fitting, with partial originals retained in preparation-attempt-01; SEALED_TEST name validation was also corrected. No training retries occurred. Main code, actual numerical inputs, supervision, parameters, and order were frozen before fitting. Some inherited helpers received post-run hashes only, not falsely claimed recursive pre-run snapshots.

Limits: single model references may be semantically wrong; development labels/alignment for16 new authorities are incomplete; six cases are exposed, not unseen tests. Further parameter/architecture experiments are not justified. A later authorized decision should first complete uniform development alignment/coarse-use coverage. No relabeling/new training occurs here; eight SEALED cases stay sealed and labels are not changed to improve results.

V08/prior files retain hashes; see preservation-audit.json. All six weights are saved/hashed locally and excluded from publication under repository policy. Only local state/reports/review packages change, without commit/push. Model references are not human gold. This round ends here.
'''
save('report-zh.txt',report)
summary='Training on 27 TRAIN cases, 730 provisional use labels and 30 legal sources completed six S/B/C fits across two seeds. DEV core retrieval: S 8/11, B 7/11, C 4/11 and 9/11. No stable conditioning benefit; graph expansion is paused. Eight SEALED cases remain unused. No legal answers or pushes.'
entry={'id':'rgcn09-main-training-01','role':'partial_supervision_development_training','report':str(R/'report-zh.txt'),'note':summary}
p=Path('docs/EXPERIMENTS.json');obj=read(p);obj['experiments'].append(entry);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
p=Path('docs/EXPERIMENT_INDEX.md');s=p.read_text();p.write_text(s+f"\n| {entry['id']} | {entry['role']} | [Report](../{entry['report']}) | {summary} |\n")
p=Path('README.md');s=p.read_text();p.write_text('Latest [V09 main training report]('+entry['report']+')：'+summary+'\n\n'+s.replace('Latest [V09 remaining-task report]','Preparation [V09 remaining-task report]',1))
p=Path('docs/CHANGELOG.md');p.write_text('# 2026-10-05 V09: Initial 27-Case Main Training\n\n'+summary+' Duplicate source 125596702 is preserved; only eight labels passing quote checks unchanged are admitted and 22 remain isolated. A 30-candidate/CORE mapping interface is added; V08 is preserved.\n\n'+p.read_text())
cur={'title':'V09 27-case partial-supervision S/B/C training','report':entry['report'],'summary':summary,'review_kind':'RGCN_MAIN_TRAINING','candidate_report':'outputs/rgcn-data-expansion-09/continuation-01/candidate-audit.json','pool_manifest':'outputs/rgcn-data-expansion-09/authority-pool/manifest.json','comparison_protocol':str(R/'protocol.json'),'preparation_freeze':str(R/'training-freeze.json'),'stage_description':report}
for name in ['docs/PROJECT_STATE.json','docs/repository-artifacts.json']:
 p=Path(name);x=read(p);x['current_review']=cur
 if name.endswith('PROJECT_STATE.json'):x['development_follow_up']['rgcn09_main_training']={'status':'COMPLETED','report':entry['report'],'training_fits':6,'failures':0,'train_cases':27,'development_cases':6,'sealed_cases':8,'sealed_evaluated':False,'accepted_uses':730,'decision':'PAUSE_GRAPH_EXPANSION_NO_STABLE_GAIN','publication':'LOCAL_ONLY_NO_COMMIT_NO_PUSH'}
 else:
  for f in ['scripts/rgcn09_train.py','legal_bench/rules_verdict_v1/rgcn_use_v2.py','tests/test_rgcn09_train.py']:
   if f not in x['code_review_files']:x['code_review_files'].append(f)
 p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(agg,ensure_ascii=False))
