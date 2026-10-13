"""Actual local pairwise training, frozen checkpoints, and same-pool comparison."""
import copy, hashlib, json, math, random, time
from collections import Counter
from pathlib import Path
import numpy as np
import torch
from torch import nn
from legal_bench.historical_contrasts_v1.contracts import ContractError, TASK, digest, read_json, write_immutable, seal
from legal_bench.historical_contrasts_v1.graph import check_features
from legal_bench.historical_contrasts_v1.encoder import encode
from legal_bench.historical_contrasts_v1.model import Ranker, state_hash
from legal_bench.historical_contrasts_v1.ranking import lexical_score
from . import data as dataset_api, graph as graph_api, metrics

LEARNED=['FLAT_MLP','GRAPH_SAGE','GRAPH_SAGE_NO_EDGES']

class Flat(nn.Module):
    def __init__(self,dim=384,hidden=128):
        super().__init__();self.project=nn.Sequential(nn.Linear(dim,hidden),nn.ReLU(),nn.Linear(hidden,hidden),nn.ReLU())
        self.head=nn.Sequential(nn.Linear(hidden*4,hidden),nn.ReLU(),nn.Linear(hidden,1))
    def forward(self,q,c):
        a=self.project(q).expand(c.shape[0],-1);b=self.project(c)
        return self.head(torch.cat([a,b,torch.abs(a-b),a*b],1)).flatten()

def verify_hashes(root,hashes):
    bad=[n for n,h in hashes.items() if not (root/n).is_file() or hashlib.sha256((root/n).read_bytes()).hexdigest()!=h]
    if bad:raise ContractError('FROZEN_FILE_CHANGED',detail=repr(bad))

def features(out,bundle,configuration):
    out=Path(out);refs=bundle['references'];graphs={q['case_id']:graph_api.build(refs,q) for q in bundle['queries']}
    nodes={};packets=set()
    for g in graphs.values():
        for n in g['body']['nodes']:
            if n['uid'] in nodes and nodes[n['uid']]!=n:raise ContractError('ENCODER_NODE_COLLISION')
            nodes[n['uid']]=n
        packets.update(g['body']['packet_hashes'])
    one=copy.deepcopy(next(iter(graphs.values()))['body']);one.update(nodes=sorted(nodes.values(),key=lambda n:n['uid']),edges=[],
        relation_types=[],packet_hashes=sorted(packets),node_map={t:sorted(i for i,n in nodes.items() if n['node_type']==t) for t in graph_api.TYPES})
    one['visibility_manifest']={**one['visibility_manifest'],'no_other_query_case_in_graph':False,
        'purpose':'ENCODER_TEXT_BATCH_ONLY; never used for message passing, loss, or ranking'}
    batch=seal('GraphRelease',one);encoded_path=out/'private/encoding/all-text-features.json'
    if encoded_path.exists():
        encoded=read_json(encoded_path);check_features(batch,encoded)
    else:
        encoded=encode(batch,configuration,batch_size=32);write_immutable(encoded_path,encoded)
        write_immutable(out/'private/encoding/text-batch-only.json',batch)
    rows={r['uid']:r for r in encoded['coverage']};frames={};coverage=[]
    for q in bundle['queries']:
        g=graphs[q['case_id']];ids={n['uid'] for n in g['body']['nodes']}
        f={'graph_sha256':g['sha256'],'config':encoded['config'],'vectors':{i:encoded['vectors'][i] for i in sorted(ids)},
           'coverage':[rows[i] for i in sorted(ids)]};f['sha256']=digest(f);check_features(g,f)
        d,qi,ci,sample,mapping=graph_api.tensors(g,f,refs,q,seed=20261013)
        yrows=[x for x in bundle['labels'] if x['query_case_id']==q['case_id']]
        frames[q['case_id']]={'query':q,'graph':g,'features':f,'data':d,'qi':qi,'ci':ci,
            'labels':yrows,'candidate_ids':[r['case_id'] for r in refs],
            'sample':sample,'mapping':mapping}
        write_immutable(out/'private/graphs'/(q['case_id']+'.json'),g)
        write_immutable(out/'private/samples'/(q['case_id']+'.json'),sample)
        coverage.append({'case_id':q['case_id'],'split':q['split'],'nodes':len(ids),'sampled_nodes':len(sample['node_ids']),
            'body_tokens':sum(rows[i]['token_count'] for i in ids),'encoded_body_tokens':sum(rows[i]['encoded_tokens'] for i in ids),
            'graph_sha256':g['sha256'],'feature_sha256':f['sha256']})
    write_immutable(out/'encoding-coverage.json',{'encoder':encoded['config'],'unique_nodes':len(encoded['coverage']),
        'unique_body_tokens':sum(r['token_count'] for r in encoded['coverage']),
        'unique_encoded_tokens':sum(r['encoded_tokens'] for r in encoded['coverage']),
        'cases':coverage,'heldout_query_message_edges_in_training_graphs':0,
        'target_labels_encoded':False,'outcome_sidecars_encoded':False})
    return frames

def score(model,frame,method):
    d=frame['data'];qi=frame['qi'];ci=frame['ci']
    if method=='FLAT_MLP':return model(d['ISSUE'].x[qi:qi+1],d['ROUTE'].x[ci])
    if method=='GRAPH_SAGE_NO_EDGES':
        # Preserve all nodes/features and the architecture; remove only messages.
        d=d.clone()
        for key in d.edge_types:d[key].edge_index=torch.empty((2,0),dtype=torch.long)
    x=model(d);return model.score(x['ISSUE'][qi:qi+1],x['ROUTE'][ci])

def fit_one(out,frames,protocol,method,seed,run_id,train_subset=None):
    torch.manual_seed(seed);np.random.seed(seed);random.seed(seed)
    train=[f for f in frames.values() if f['query']['split']=='TRAIN']
    if train_subset is not None:train=[f for f in train if f['query']['case_id'] in train_subset]
    val=[f for f in frames.values() if f['query']['split']=='VALIDATION']
    if not train or not val:raise ContractError('EMPTY_TRAIN_OR_VALIDATION')
    g=train[0]['graph']['body'];dim=train[0]['features']['config']['dimension'];cfg=protocol['training']
    model=Flat(dim,cfg['hidden']) if method=='FLAT_MLP' else Ranker(g['node_types'],g['relation_types'],dim,cfg['hidden'])
    initial=state_hash(model);opt=torch.optim.AdamW(model.parameters(),lr=cfg['learning_rate'],weight_decay=cfg['weight_decay'])
    best=None;best_metric=-math.inf;best_epoch=None;logs=[];steps=0;train_ids=set();start=time.monotonic()
    def validated():
        model.eval();rows=[]
        with torch.no_grad():
            for f in val:
                y=dataset_api.supervision(f['labels'],'VALIDATION');s=score(model,f,method).tolist()
                rows.append({'metrics':metrics.evaluate(dict(zip(f['candidate_ids'],s)),y)})
        return metrics.aggregate(rows)
    for epoch in range(1,cfg['epochs']+1):
        model.train();losses=[]
        order=list(train);random.Random(seed*1000+epoch).shuffle(order)
        for f in order:
            if f['query']['split']!='TRAIN':raise ContractError('NONTRAIN_IN_OPTIMIZER')
            y=dataset_api.supervision(f['labels'],'TRAIN');pos=[i for i,c in enumerate(f['candidate_ids']) if y.get(c)==1]
            neg=[i for i,c in enumerate(f['candidate_ids']) if y.get(c)==0]
            if not pos or not neg:continue
            opt.zero_grad(set_to_none=True);s=score(model,f,method)
            loss=torch.nn.functional.softplus(s[neg][None,:]-s[pos][:,None]).mean()
            if not torch.isfinite(loss):raise ContractError('NONFINITE_TRAIN_LOSS')
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.0);opt.step()
            steps+=1;train_ids.add(f['query']['case_id']);losses.append(float(loss.detach()))
        if not losses:raise ContractError('NO_OPTIMIZER_STEPS')
        v=validated();criterion=v['NDCG@3']
        if criterion is None:raise ContractError('VALIDATION_UNEVALUABLE')
        if criterion>best_metric+1e-12:
            best_metric=criterion;best=copy.deepcopy(model.state_dict());best_epoch=epoch
        logs.append({'epoch':epoch,'loss':float(np.mean(losses)),'validation':v,'steps':steps})
        if epoch%10==0:print(json.dumps({'method':method,'seed':seed,**logs[-1]}),flush=True)
    final=state_hash(model);model.load_state_dict(best);model.eval();selected=state_hash(model)
    if initial==final or steps==0:raise ContractError('NO_TRAINED_PARAMETER_CHANGE')
    path=Path(out)/'private/training'/run_id/(method+'-'+str(seed));path.mkdir(parents=True,exist_ok=True)
    checkpoint=path/'selected.pt'
    if checkpoint.exists():raise ContractError('EXISTING_TRAINING_CHECKPOINT')
    torch.save(model.state_dict(),checkpoint)
    loaded=torch.load(checkpoint,map_location='cpu',weights_only=True);model.load_state_dict(loaded)
    if state_hash(model)!=selected:raise ContractError('CHECKPOINT_ROUNDTRIP')
    meta={'method':method,'seed':seed,'epochs':cfg['epochs'],'optimizer_steps':steps,'selected_epoch':best_epoch,
        'selected_validation_NDCG@3':best_metric,'initial_state_hash':initial,'last_state_hash':final,'selected_state_hash':selected,
        'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),'checkpoint_path':str(checkpoint),
        'train_query_ids':sorted(train_ids),'validation_query_ids':sorted(f['query']['case_id'] for f in val),
        'holdout_query_ids_seen_by_optimizer':[],'parameters':sum(p.numel() for p in model.parameters()),
        'seconds':time.monotonic()-start,'source_config':cfg,'trained':True}
    write_immutable(path/'metadata.json',meta);write_immutable(path/'learning-curve.json',logs)
    return model,meta

def baselines(frame,refs,seed,train_prior):
    q=frame['query'];query=graph_api.text(q);f=frame['features'];qv=f['vectors'][graph_api.uid(q,'ISSUE')]
    lex={r['case_id']:lexical_score(query,graph_api.text(r)) for r in refs}
    dense={r['case_id']:float(np.dot(qv,f['vectors'][graph_api.uid(r,'ROUTE')])) for r in refs}
    rrf={c:0.0 for c in lex}
    for scores in (lex,dense):
        for i,c in enumerate(sorted(scores,key=lambda c:(-scores[c],c)),1):rrf[c]+=1/(60+i)
    rng=random.Random(seed+int(digest(q['model_text_sha256'])[:8],16));rdm={c:rng.random() for c in lex}
    return {'LEXICAL':lex,'E5':dense,'RRF':rrf,'RANDOM':rdm,'TRAIN_PRIOR':train_prior}

def experiment(root,out):
    root=Path(root);out=Path(out);torch.set_num_threads(2);torch.use_deterministic_algorithms(True)
    protocol=read_json(out/('protocol-final.json' if (out/'protocol-final.json').exists() else 'protocol-expanded.json'));bundle=read_json(out/'private/dataset.json')
    if digest({k:v for k,v in bundle.items() if k!='sha256'})!=bundle['sha256']:raise ContractError('DATASET_HASH')
    verify_hashes(root,read_json(out/('source-input-hashes-expanded.json' if (out/'source-input-hashes-expanded.json').exists() else 'source-input-hashes.json')))
    files=[*sorted((root/'legal_bench/historical_contrasts_v2').glob('*.py')),
        root/'scripts/historical_contrasts_v2.py',root/'scripts/historical_contrasts_v2_prepare.py',
        root/'tests/test_historical_contrasts_v2.py',root/'legal_bench/historical_contrasts_v1/model.py',
        root/'legal_bench/historical_contrasts_v1/encoder.py',root/'legal_bench/historical_contrasts_v1/graph.py']
    code={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    freeze={'code_hashes':code,'protocol_sha256':digest(protocol),'dataset_sha256':bundle['sha256'],
            'candidate_ids':[r['case_id'] for r in bundle['references']],'frozen_before_optimizer':True}
    run_id='run-'+digest(freeze)[:16];run=out/'experiments'/run_id;write_immutable(run/'freeze.json',freeze)
    for name in code:
        target=run/'freeze-code'/name;target.parent.mkdir(parents=True,exist_ok=True)
        raw=(root/name).read_bytes()
        if target.exists() and target.read_bytes()!=raw:raise ContractError('FREEZE_COPY_CHANGED')
        if not target.exists():target.write_bytes(raw)
    configuration=read_json(root/'outputs/gnn-irac-aligned-v2/text-cache/encoder.json')
    frames=features(out,bundle,configuration);models=[];meta=[]
    # No holdout metric is evaluated before every selected checkpoint is frozen.
    for seed in protocol['training']['seeds']:
        for method in LEARNED:
            model,m=fit_one(out,frames,protocol,method,seed,run_id);models.append((method,seed,model));meta.append(m)
    learning_models=[];learning_meta=[]
    trainable=sorted(bundle['trainable_queries']);random.Random(20261013).shuffle(trainable)
    for size in protocol.get('learning_curve_sizes',[]):
        if size>=len(trainable):continue
        chosen=set(trainable[:size])
        for seed in protocol['training']['seeds']:
            model,m=fit_one(out,frames,protocol,'GRAPH_SAGE',seed,run_id+'-n'+str(size),chosen)
            learning_models.append((size,seed,model));learning_meta.append({**m,'training_query_limit':size})
    write_immutable(run/'checkpoints-frozen-before-holdout.json',{'checkpoints':meta,'learning_curve_checkpoints':learning_meta,'holdout_metrics_computed':False})
    outcomes={x['case_id']:x['outcome'] for x in bundle['outcomes']};rows=[];candidate_ids=[r['case_id'] for r in bundle['references']]
    train_prior={}
    for cid in candidate_ids:
        y=[1 if x['utility']=='POSITIVE' else 0 for x in bundle['labels'] if x['split']=='TRAIN'
           and x['candidate_case_id']==cid and x['utility'] in ('POSITIVE','NEGATIVE')]
        train_prior[cid]=(sum(y)+1)/(len(y)+2)
    write_immutable(run/'train-only-prior-baseline.json',{'scores':train_prior,'formula':'(train_positive+1)/(train_known+2)','holdout_labels_used':False})
    for split in ['TRAIN','VALIDATION','DEVELOPMENT_HOLDOUT']:
        for f in frames.values():
            if f['query']['split']!=split:continue
            y=dataset_api.supervision(f['labels'],split)
            for seed in protocol['training']['seeds']:
                scores=baselines(f,bundle['references'],seed,train_prior)
                for method,s,m in models:
                    if s!=seed:continue
                    before=state_hash(m)
                    with torch.no_grad():values=score(m,f,method).tolist()
                    if before!=state_hash(m):raise ContractError('EVALUATION_CHANGED_PARAMETERS')
                    scores[method]=dict(zip(candidate_ids,values))
                for method,values in scores.items():
                    if set(values)!=set(candidate_ids) or any(not math.isfinite(v) for v in values.values()):raise ContractError('SCORE_POOL')
                    rows.append({'split':split,'case_id':f['query']['case_id'],'method':method,'seed':seed,
                        'scores':values,'ordered_ids':sorted(values,key=lambda c:(-values[c],c)),
                        'metrics':metrics.evaluate(values,y,outcomes),'judged_labels':y,
                        'unknown_or_rejected_candidates':sorted(set(candidate_ids)-set(y)),
                        'graph_sha256':f['graph']['sha256'],'feature_sha256':f['features']['sha256']})
    write_immutable(run/'private/per-query-results.json',rows)
    learning_rows=[]
    for size,seed,m in learning_models:
        for f in frames.values():
            if f['query']['split']!='DEVELOPMENT_HOLDOUT':continue
            y=dataset_api.supervision(f['labels'],'DEVELOPMENT_HOLDOUT')
            with torch.no_grad():values=score(m,f,'GRAPH_SAGE').tolist()
            learning_rows.append({'size':size,'seed':seed,'case_id':f['query']['case_id'],
                'metrics':metrics.evaluate(dict(zip(candidate_ids,values)),y,outcomes)})
    write_immutable(run/'private/learning-curve-holdout.json',learning_rows)
    learning_summary=[]
    for size in sorted({r['size'] for r in learning_rows}):
        learning_summary.append({'trainable_query_count':size,'per_seed':[{'seed':s,**metrics.aggregate([r for r in learning_rows if r['size']==size and r['seed']==s])} for s in protocol['training']['seeds']]})
    summaries=[]
    for split in ['TRAIN','VALIDATION','DEVELOPMENT_HOLDOUT']:
        for method in protocol['methods']:
            per_seed=[{'seed':seed,**metrics.aggregate([r for r in rows if r['split']==split and r['method']==method and r['seed']==seed])}
                      for seed in protocol['training']['seeds']]
            keys=['NDCG@3','Recall@3','Precision@3','MRR','Recall@5','contrast_pair_coverage@3']
            means={k:float(np.mean([x[k] for x in per_seed if x[k] is not None])) if any(x[k] is not None for x in per_seed) else None for k in keys}
            sd={k:float(np.std([x[k] for x in per_seed if x[k] is not None])) if any(x[k] is not None for x in per_seed) else None for k in keys}
            summaries.append({'split':split,'method':method,'per_seed':per_seed,'mean':means,'seed_sd':sd})
    comparisons=[]
    hold=[r for r in rows if r['split']=='DEVELOPMENT_HOLDOUT' and r['metrics']['evaluable']]
    for other in ['LEXICAL','E5','RRF','FLAT_MLP','GRAPH_SAGE_NO_EDGES','RANDOM','TRAIN_PRIOR']:
        diffs=[];details=[]
        for cid in sorted({r['case_id'] for r in hold}):
            a=[r['metrics']['NDCG@3'] for r in hold if r['case_id']==cid and r['method']=='GRAPH_SAGE']
            b=[r['metrics']['NDCG@3'] for r in hold if r['case_id']==cid and r['method']==other]
            delta=float(np.mean(a)-np.mean(b));diffs.append(delta);details.append({'case_id':cid,'difference':delta})
        comparisons.append({'GNN_vs':other,'metric':'judged NDCG@3','paired':metrics.paired_bootstrap(diffs),
            'wins':sum(d>1e-12 for d in diffs),'ties':sum(abs(d)<=1e-12 for d in diffs),'losses':sum(d< -1e-12 for d in diffs),'cases':details})
    verify_hashes(root,freeze['code_hashes']);verify_hashes(root,read_json(out/'preservation-before.json'))
    summary={'version':'HISTORICAL_CONTRASTS_V2','run_id':run_id,'protocol':protocol,
        'data_readiness':read_json(out/'data-readiness.json'),'training_fits':len(meta),
        'optimizer_steps':sum(x['optimizer_steps'] for x in meta),'checkpoints':meta,
        'metrics':summaries,'holdout_comparisons':comparisons,'all_source_and_old_module_hashes_preserved':True,
        'learning_curve_fits':len(learning_meta),'learning_curve':learning_summary,
        'total_training_fits':len(meta)+len(learning_meta),
        'total_optimizer_steps':sum(m['optimizer_steps'] for m in meta+learning_meta),
        'new_sealed_test_read':False,'independent_final_test':False,'human_gold':False,
        'downstream_final_answer_effectiveness_evaluated':False,'existing_binding_gate_bypassed':False,
        'graph_structure_scope':'Source/case/issue/route grouping; no entity/reasoning edges; limited first training baseline',
        'parent_entry_switched':False,'parent_queue_resumed':False,'commit_or_push':False}
    write_immutable(run/'summary.json',summary);write_immutable(out/'completed-run.json',{'run':str(run),'summary_sha256':digest(summary)})
    print(json.dumps({'completed':str(run),'training_fits':len(meta),'holdout':[(x['method'],x['mean']) for x in summaries if x['split']=='DEVELOPMENT_HOLDOUT']}),flush=True)
    return summary
