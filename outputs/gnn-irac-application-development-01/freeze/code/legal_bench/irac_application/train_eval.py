"""Frozen grouped development training; no labels used in input construction."""
import copy
import random
import time
import numpy as np
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx.utils import tree_flatten
from .application_models import ApplicationModel,masked_group_loss,parameter_count

def grouped_split(packages,seed=20261006,folds=3):
    groups=sorted({p['group_id'] for p in packages})
    if len(groups)<2:return []
    random.Random(seed).shuffle(groups);k=min(folds,len(groups));out=[]
    for fold in range(k):
        test=groups[fold::k];train=[g for g in groups if g not in test]
        shuffled=list(train);random.Random(seed+fold+1).shuffle(shuffled)
        val=shuffled[:max(1,len(train)//5)] if len(train)>=2 else []
        out.append({'fold':fold,'test_groups':test,'validation_groups':val,
                    'fit_groups':[g for g in train if g not in val],
                    'early_stopping':bool(val)})
    return out

def fit(kind,packages,validation,seed,epochs=100,batch_size=4,patience=10):
    train=[p for p in packages if any(p['mask'])]
    if not train:raise ValueError('NO_SUPERVISED_PACKAGES')
    mx.reset_peak_memory();mx.random.seed(seed);rng=random.Random(seed)
    model=ApplicationModel(kind,train[0]['tensors']['x'].shape[1])
    mx.eval(model.parameters());before={k:np.array(v) for k,v in tree_flatten(model.parameters())}
    optimizer=optim.AdamW(learning_rate=.001,weight_decay=.0001)
    grad=nn.value_and_grad(model,masked_group_loss)
    history=[];best=None;best_loss=float('inf');bad=0;t0=time.perf_counter();updates=0;first_grad=None
    bygroup={}
    for p in train:bygroup.setdefault(p['group_id'],[]).append(p)
    group_ids=sorted(bygroup)
    for epoch in range(epochs):
        model.train();rng.shuffle(group_ids);values=[]
        # Complete groups stay in a batch. A large group is never split and over-weighted.
        batches=[];batch=[]
        for gid in group_ids:
            if batch and len(batch)+len(bygroup[gid])>batch_size:batches.append(batch);batch=[]
            batch+=bygroup[gid]
        if batch:batches.append(batch)
        for batch in batches:
            value,g=grad(model,batch)
            if first_grad is None:first_grad=float(sum(mx.sum(v*v).item() for _,v in tree_flatten(g)))**.5
            optimizer.update(model,g);mx.eval(model.parameters(),optimizer.state,value,g)
            values.append(float(value.item()));updates+=1
        model.eval()
        usable=[p for p in validation if any(p['mask'])]
        val=float(masked_group_loss(model,usable).item()) if usable else None
        history.append({'epoch':epoch,'training_loss':float(np.mean(values)),
                        'validation_loss':val,'optimizer_updates':updates})
        if not np.isfinite(values).all() or val is not None and not np.isfinite(val):raise ValueError('NONFINITE_TRAINING')
        if val is not None:
            if val<best_loss-1e-7:
                best_loss=val;best=copy.deepcopy(model.parameters());bad=0
            else:bad+=1
            if bad>=patience:break
    last_delta=float(sum(np.sum((np.array(v)-before[k])**2) for k,v in tree_flatten(model.parameters())))**.5
    if best is not None:model.update(best);mx.eval(model.parameters())
    model.eval()
    return model,{'history':history,'updates':updates,'first_gradient_norm':first_grad,
        'pre_checkpoint_parameter_delta':last_delta,'parameters':parameter_count(model),
        'kind':kind,'seed':seed,'seconds':time.perf_counter()-t0,
        'fit_groups':sorted(bygroup),'validation_groups':sorted({p['group_id'] for p in validation}),
        'early_stop_checkpoint_used':best is not None,'peak_mlx_memory_bytes':mx.get_peak_memory()}

def prior_fit(packages):
    counts={};all_counts=np.ones(3,dtype=float)
    for p in packages:
        for key,y,mask in zip(p['template_condition_ids'],p['labels'],p['mask']):
            if not mask:continue
            counts.setdefault(key,np.ones(3,dtype=float))[y]+=1;all_counts[y]+=1
    return {'per_condition':{k:(v/v.sum()).tolist() for k,v in counts.items()},
            'fallback':(all_counts/all_counts.sum()).tolist(),'smoothing':1}

def package_group_values(rows,field):
    groups={}
    for r in rows:
        if not r['supervision_mask']:continue
        y=r['label'];p=r['probabilities'];v=float(int(np.argmax(p))==y) if field=='correct' else -float(np.log(max(p[y],1e-12)))
        groups.setdefault(r['group_id'],{}).setdefault(r['package_id'],[]).append(v)
    return {g:float(np.mean([np.mean(v) for v in packages.values()])) for g,packages in groups.items()}

def metrics(rows):
    admitted=[r for r in rows if r['supervision_mask']]
    matrix=np.zeros((3,3),int);loss=[]
    for r in admitted:
        y=r['label'];pred=int(np.argmax(r['probabilities']));matrix[y,pred]+=1
        loss.append(-np.log(max(r['probabilities'][y],1e-12)))
    recall=[];f1=[]
    for i in range(3):
        tp=matrix[i,i];fn=matrix[i].sum()-tp;fp=matrix[:,i].sum()-tp
        recall.append(float(tp/(tp+fn)) if tp+fn else None)
        f1.append(float(2*tp/(2*tp+fp+fn)) if tp+fn else None)
    correct=package_group_values(rows,'correct');balanced_loss=package_group_values(rows,'loss')
    return {'supervised_conditions':len(admitted),'dispute_groups':len(correct),
        'confusion_matrix':matrix.tolist(),'per_class_recall':recall,
        'macro_f1_observed_classes':float(np.mean([v for v in f1 if v is not None])) if any(v is not None for v in f1) else None,
        'unobserved_classes':[i for i,v in enumerate(recall) if v is None],
        'dispute_mean_correct':float(np.mean(list(correct.values()))) if correct else None,
        'condition_micro_probability_loss':float(np.mean(loss)) if loss else None,
        'dispute_balanced_probability_loss':float(np.mean(list(balanced_loss.values()))) if balanced_loss else None,
        'planned_conditions':len(rows),'supervision_coverage':len(admitted)/len(rows) if rows else 0}

def paired_group_bootstrap(rows,seed=20261006,repeats=2000):
    # Seeds averaged within each dispute, then resample disputes, not conditions or seeds.
    scores={}
    for method in ('P','Flat','Graph'):
        seeds=sorted({r['seed'] for r in rows if r['method']==method},key=lambda x:-1 if x is None else x)
        per_seed=[package_group_values([r for r in rows if r['method']==method and r['seed']==s],'correct') for s in seeds]
        gids=set.intersection(*(set(x) for x in per_seed)) if per_seed else set()
        scores[method]={g:float(np.mean([x[g] for x in per_seed])) for g in gids}
    out={}
    for a,b in [('Flat','P'),('Graph','Flat'),('Graph','P')]:
        gids=sorted(set(scores[a])&set(scores[b]));delta=np.array([scores[a][g]-scores[b][g] for g in gids]);rng=np.random.default_rng(seed)
        draws=np.mean(delta[rng.integers(0,len(delta),size=(repeats,len(delta)))],axis=1) if len(delta) else []
        out[a+'-'+b]=dict(groups=len(gids),mean_delta=float(delta.mean()) if len(delta) else None,percentile_95=np.percentile(draws,[2.5,97.5]).tolist() if len(draws) else None,repeats=repeats,seed=seed,scope='descriptive grouped development uncertainty, not independent-test significance')
    return out
