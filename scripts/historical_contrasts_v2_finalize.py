"""Replay already frozen fits and finish reporting after concurrent metadata updates.

No optimizer, annotation retry, model selection or new training is performed.
Only the three shared entry documents may differ from the old preservation audit;
all source, code, training inputs and checkpoints still have to match exactly.
"""
import hashlib, json, math, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.runtime/historical-contrasts-v1/site'));sys.path.insert(0,str(ROOT))
import numpy as np
import torch
from legal_bench.historical_contrasts_v1.contracts import ContractError,digest,read_json,write_immutable
from legal_bench.historical_contrasts_v1.model import Ranker,state_hash
from legal_bench.historical_contrasts_v2 import train,metrics

ALLOWED_SHARED_METADATA={'README.md','docs/PROJECT_STATE.json','review/START_HERE.md'}

def preservation(root,before):
    changed=[];same=0
    for name,old in before.items():
        path=root/name
        if not path.is_file():raise ContractError('PRESERVED_FILE_MISSING',detail=name)
        current=hashlib.sha256(path.read_bytes()).hexdigest()
        if current==old:same+=1
        elif name in ALLOWED_SHARED_METADATA:changed.append({'path':name,'before_sha256':old,'current_sha256':current})
        else:raise ContractError('SOURCE_OR_OLD_MODULE_CHANGED',detail=name)
    return {'unchanged_source_and_old_module_files':same,'concurrent_shared_metadata_changes':changed,
        'original_before_audit_retained':True,'shared_metadata_not_reverted':True,'actor_not_independently_identified':True}

def main():
    torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    out=ROOT/'outputs/historical-contrasts-v2';run=out/'experiments/run-ede1059d97079c1c'
    freeze=read_json(run/'freeze.json');protocol=read_json(out/'protocol-final.json');bundle=read_json(out/'private/dataset.json')
    train.verify_hashes(ROOT,freeze['code_hashes']);train.verify_hashes(ROOT,freeze['input_file_hashes'])
    if digest(protocol)!=freeze['protocol_sha256'] or bundle['sha256']!=freeze['dataset_sha256']:
        raise ContractError('FINALIZATION_INPUT_HASH')
    train.validate_protocol(bundle,protocol)
    audit=preservation(ROOT,read_json(out/'preservation-before.json'))
    before_finalize={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ALLOWED_SHARED_METADATA}
    checkpoints=read_json(run/'checkpoints-frozen-before-holdout.json');rows=read_json(run/'private/per-query-results.json')
    learning_rows=read_json(run/'private/learning-curve-holdout.json')
    config=read_json(ROOT/'outputs/gnn-irac-aligned-v2/text-cache/encoder.json');frames=train.features(out,bundle,config)
    if len(rows)!=len(protocol['methods'])*len(protocol['training']['seeds'])*len(bundle['queries']):
        raise ContractError('INCOMPLETE_RESULT_ROWS')
    by_result={(r['method'],r['seed'],r['case_id']):r for r in rows}
    if len(by_result)!=len(rows):raise ContractError('DUPLICATE_RESULT_ROW')
    replayed=0;learning_replayed=0
    for meta in checkpoints['checkpoints']+checkpoints['learning_curve_checkpoints']:
        path=Path(meta['checkpoint_path'])
        if hashlib.sha256(path.read_bytes()).hexdigest()!=meta['checkpoint_sha256']:
            raise ContractError('TRAINED_CHECKPOINT_CHANGED')
        first=next(iter(frames.values()));g=first['graph']['body'];dim=first['features']['config']['dimension']
        model=train.Flat(dim,protocol['training']['hidden']) if meta['method']=='FLAT_MLP' else Ranker(g['node_types'],g['relation_types'],dim,protocol['training']['hidden'])
        model.load_state_dict(torch.load(path,map_location='cpu',weights_only=True));model.eval()
        if state_hash(model)!=meta['selected_state_hash']:raise ContractError('SELECTED_MODEL_HASH')
        is_learning='training_query_limit' in meta
        for cid,f in frames.items():
            if is_learning and f['query']['split']!='DEVELOPMENT_HOLDOUT':continue
            with torch.no_grad():values=train.score(model,f,meta['method']).tolist()
            if is_learning:
                y=train.dataset_api.supervision(f['labels'],'DEVELOPMENT_HOLDOUT')
                outcomes={x['case_id']:x['outcome'] for x in bundle['outcomes']}
                result=metrics.evaluate(dict(zip(f['candidate_ids'],values)),y,outcomes)
                saved=[r for r in learning_rows if r['size']==meta['training_query_limit'] and r['seed']==meta['seed'] and r['case_id']==cid]
                if len(saved)!=1 or saved[0]['metrics']!=result:raise ContractError('LEARNING_METRIC_REPLAY_MISMATCH')
                learning_replayed+=1
            else:
                saved=by_result[(meta['method'],meta['seed'],cid)]
                if saved['scores']!=dict(zip(f['candidate_ids'],values)):raise ContractError('SCORE_REPLAY_MISMATCH')
                replayed+=1
        if state_hash(model)!=meta['selected_state_hash']:raise ContractError('REPLAY_CHANGED_MODEL')
    summaries=[]
    keys=['NDCG@3','Recall@3','Precision@3','MRR','Recall@5','contrast_pair_coverage@3']
    for split in ['TRAIN','VALIDATION','DEVELOPMENT_HOLDOUT']:
        for method in protocol['methods']:
            per_seed=[{'seed':s,**metrics.aggregate([r for r in rows if r['split']==split and r['method']==method and r['seed']==s])} for s in protocol['training']['seeds']]
            mean={k:float(np.mean([x[k] for x in per_seed if x[k] is not None])) if any(x[k] is not None for x in per_seed) else None for k in keys}
            sd={k:float(np.std([x[k] for x in per_seed if x[k] is not None])) if any(x[k] is not None for x in per_seed) else None for k in keys}
            summaries.append({'split':split,'method':method,'per_seed':per_seed,'mean':mean,'seed_sd':sd})
    learning_summary=[]
    for size in sorted({r['size'] for r in learning_rows}):
        learning_summary.append({'trainable_query_count':size,'per_seed':[{'seed':s,**metrics.aggregate([r for r in learning_rows if r['size']==size and r['seed']==s])} for s in protocol['training']['seeds']]})
    hold=[r for r in rows if r['split']=='DEVELOPMENT_HOLDOUT' and r['metrics']['evaluable']];comparisons=[]
    for other in ['LEXICAL','E5','RRF','FLAT_MLP','GRAPH_SAGE_NO_EDGES','RANDOM','TRAIN_PRIOR']:
        diffs=[];details=[]
        for cid in sorted({r['case_id'] for r in hold}):
            a=[r['metrics']['NDCG@3'] for r in hold if r['case_id']==cid and r['method']=='GRAPH_SAGE']
            b=[r['metrics']['NDCG@3'] for r in hold if r['case_id']==cid and r['method']==other]
            delta=float(np.mean(a)-np.mean(b));diffs.append(delta);details.append({'case_id':cid,'difference':delta})
        comparisons.append({'GNN_vs':other,'metric':'judged NDCG@3','paired':metrics.paired_bootstrap(diffs),
            'wins':sum(d>1e-12 for d in diffs),'ties':sum(abs(d)<=1e-12 for d in diffs),'losses':sum(d< -1e-12 for d in diffs),'cases':details})
    meta=checkpoints['checkpoints'];learning_meta=checkpoints['learning_curve_checkpoints']
    evidence={'training_call_failed_at':'post-evaluation preservation audit','training_and_evaluation_outputs_retained':True,
        'original_failure_log':'private/full-training.log','freeze_kept':True,'new_optimizer_steps':0,
        'replayed_selected_model_query_scores':replayed,'replayed_learning_curve_metrics':learning_replayed,
        'checked_checkpoints':len(meta)+len(learning_meta),'preservation':audit,
        'finalizer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    write_immutable(run/'finalization-replay.json',evidence)
    summary={'version':'HISTORICAL_CONTRASTS_V2','run_id':run.name,'protocol':protocol,'data_readiness':read_json(out/'data-readiness.json'),
        'training_fits':len(meta),'optimizer_steps':sum(x['optimizer_steps'] for x in meta),'checkpoints':meta,'metrics':summaries,
        'holdout_comparisons':comparisons,'all_source_and_old_module_hashes_preserved':True,'all_preservation_files_unchanged':not audit['concurrent_shared_metadata_changes'],
        'preservation':audit,'learning_curve_fits':len(learning_meta),'learning_curve':learning_summary,
        'total_training_fits':len(meta)+len(learning_meta),'total_optimizer_steps':sum(m['optimizer_steps'] for m in meta+learning_meta),
        'new_sealed_test_read':False,'independent_final_test':False,'human_gold':False,'downstream_final_answer_effectiveness_evaluated':False,
        'existing_binding_gate_bypassed':False,'graph_structure_scope':'Source/case/issue/route grouping; no entity/reasoning edges; limited first training baseline',
        'parent_entry_switched_by_this_experiment':False,'parent_queue_resumed_by_this_experiment':False,'commit_or_push_by_this_experiment':False,
        'finalization_replay':evidence}
    train.verify_hashes(ROOT,freeze['code_hashes']);train.verify_hashes(ROOT,freeze['input_file_hashes']);train.verify_hashes(ROOT,before_finalize)
    write_immutable(run/'summary.json',summary);write_immutable(out/'completed-run.json',{'run':str(run),'summary_sha256':digest(summary)})
    print(json.dumps({'completed':str(run),'fits':summary['total_training_fits'],'optimizer_steps':summary['total_optimizer_steps'],'replay':evidence},indent=2))

if __name__=='__main__':main()
