"""One concentrated, local post-run comparison. No parameter or ranking changes."""
import sys,json,collections,csv,html,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.proof_search_delivery_v11 import OUT as R,BASE,read,save
from legal_bench.proof_carrying.contracts import byte_hash
cfg=read(R/'protocol.json');results=[];requestrows=[];source=[]
for cond in ['pool','Simple']+[f'{k}-fold{fold}-seed{s}' for k in ['Flat','RGCN'] for fold in range(2) for s in cfg['seeds']]:
 root=R/'results'/cond
 if not root.exists():continue
 for folder in sorted(root.iterdir()):
  cid=folder.name;a=read(folder/'analysis.json');selection=read(folder/'selection.json');oracle=read(R/'results/pool'/cid/'oracle.json');checked=read(folder/'checked.json');chosen=set(selection['selected']);pred={q['id']:q['answer'] for q in a['requests']};cost=read(folder/'cost.json')
  present={p['request'] for p in oracle['valid_paths'] if set(p['members'])<=chosen};accepted={k for k,v in pred.items() if v=='TRUE'};poolaccepted={q['id'] for q in read(R/'results/pool'/cid/'analysis.json')['requests'] if q['answer']=='TRUE'}
  assert accepted<=poolaccepted
  row={'condition':cond,'case':cid,'selected':len(chosen),'requests':len(pred),'true_conditional':len(accepted),'unknown':sum(v=='UNKNOWN' for v in pred.values()),'null':sum(v is None for v in pred.values()),'known_budget_route_present':len(present),'accepted_outside_known_pool':len(accepted-poolaccepted),'checker_seconds':cost['seconds'],'selection_seconds':selection.get('inference_seconds'),'snapshot_bytes':cost['snapshot_bytes'],'derivation_bytes':cost['derivation_bytes'],'alternative_checks':cost['alternative_checks']};results.append(row)
  for q in a['requests']:requestrows.append({'condition':cond,'case':cid,'request':q['id'],'answer':q['answer'],'known_route_in_selection':q['id'] in present,'errors':sorted({e for z in q['alternatives'] for e in z.get('errors',[])}),'gaps':sorted({e for z in q['alternatives'] for e in z.get('gaps',[])})})
  if cond=='Simple':
   # Only proposition-level source disagreement, not audit every display field.
   retained=all(read(BASE/'runs'/cid/'proposal/usable.json').get(k,[])==a.get('all_raw_'+k,[]) for k in ['relations','limitations'])
   source.append({'case':cid,'source_role':'RECONSTRUCTION_INCLUDING_TARGET_REASONS_NOT_PREDICTION','new_source_or_model_output':False,'all_original_relations_and_limits_preserved':retained,'counterarguments_in_offline_file':a['counterarguments'],'selected_materials_do_not_automatically_preserve_all_counterarguments':True,'full_pool_true':sorted(poolaccepted),'review':'MODEL_ASSISTED_NOT_HUMAN_GOLD'})
summary=[]
for cid in cfg['cases']:
 row={'case':cid,'v10_simple':sum(q['answer']=='TRUE' for q in read(Path('outputs/proof-carrying-selection-readiness-v10/results/simple')/cid/'analysis.json')['requests']),'Simple':next(x['true_conditional'] for x in results if x['condition']=='Simple' and x['case']==cid),'pool':next(x['true_conditional'] for x in results if x['condition']=='pool' and x['case']==cid)}
 for k in ['Flat','RGCN']:row[k]=[next(x['true_conditional'] for x in results if x['case']==cid and x['condition'].startswith(k+'-') and x['condition'].endswith(str(s))) for s in cfg['seeds']]
 summary.append(row)
save(R/'final-comparison.json',results);save(R/'case-summary.json',summary);save(R/'request-comparison.json',requestrows);save(R/'source-review.json',source)
with (R/'case-summary.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
fits=[read(p) for p in (R/'training').glob('*/training-complete.json')];cost={'fit_count':len(fits),'training_seconds':sum(f['seconds'] for f in fits),'training_by_kind':{k:sum(f['seconds'] for f in fits if f['kind']==k) for k in ['Flat','RGCN']},'all_pool_checker_seconds':sum(x['checker_seconds'] for x in results if x['condition']=='pool'),'simple_checker_seconds':sum(x['checker_seconds'] for x in results if x['condition']=='Simple'),'learned_selection_seconds':sum(x['selection_seconds'] or 0 for x in results),'web_calls':0,'new_text_encodings':0,'peak_memory':'NOT_MEASURED','not_lawyer_review_time':True};save(R/'cost.json',cost)
# Verify labels were not flipped to force compatibility, and list all11 old-positive conflicts.
mig=read(R/'label-migration.json');conf=[x for x in mig if x['old_label']==1 and x['v10_eligibility']=='EXCLUDE_EXPLICIT_CONTRACT_ERROR'];assert len(conf)==11
save(R/'old-positive-conflicts.json',[{**x,'interpretation':'ROLE_CONTRACT_FIXED_ATTRIBUTION_ONLY' if x['v11_eligibility']=='KEEP' else 'PRIOR_USE_LABEL_CONFLICTS_WITH_CURRENT_LEAF_CONTRACT_NOT_AUTOMATICALLY_FALSE'} for x in conf])
checks=read(R/'registration.json')['history'];bad=[p for p,h in checks.items() if not Path(p).exists() or byte_hash(Path(p))!=h];assert not bad
freeze=read(R/'freeze.json');assert all(byte_hash(Path(p))==h for p,h in {**freeze['method_hashes'],**freeze['input_hashes']}.items())
assert len(fits)==12 and all(x['updated'] for x in fits)
save(R/'delivery-validation.json',{'history_files':len(checks),'history_changes':bad,'freeze_matches':True,'fitted':12,'weight_reload_checks':[read(p) for p in (R/'training').glob('*/reload.json')],'new_model_generation_calls':0,'no_heldout_training':'Only train cases in each fit training-complete.json contributed loss; all eight already development-exposed.','no_legal_approval':True,'not_independent_test':True})
links=''.join('<tr><td>'+r['case']+'</td><td>'+str(r['v10_simple'])+'</td><td>'+str(r['Simple'])+'</td><td>'+str(r['Flat'])+'</td><td>'+str(r['RGCN'])+'</td><td>'+str(r['pool'])+'</td></tr>' for r in summary)
(R/'index.html').write_text('<!doctype html><meta charset="utf-8"><h1>V11 request/state-conditioned proof selection</h1><p>Exposed development; no legal approval. Historical V10 is a cross-version reference, not a controlled ablation. Full pool is bounded enumeration, not an exact global oracle.</p><a href="report-zh.txt">中文报告</a> · <a href="request-comparison.json">All requests and gaps</a> · <a href="label-migration.json">Label migration</a><table border="1"><tr><th>Case</th><th>V10 historical</th><th>New Simple</th><th>Flat seeds</th><th>RGCN seeds</th><th>Pool</th></tr>'+links+'</table><p><a href="cost.json">Cost</a> · <a href="delivery-validation.json">Version verification</a></p>')
print(json.dumps({'summary':summary,'cost':cost},ensure_ascii=False))
