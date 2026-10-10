"""Fixed MLX Flat / two-layer basis R-GCN ranking, same nodes and triples."""
import json
import hashlib
import time
from pathlib import Path
import numpy as np
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx.utils import tree_flatten
from .candidates_v8 import RELATIONS,TYPES
from .contracts import write_once

STATUS=('PARTY_CLAIM','TESTIMONY','RECORDED_DOCUMENT','LOWER_COURT_FINDING','TARGET_COURT_FINDING','PROCEDURAL_RECORD','LEGAL_RULE','TARGET_DISPOSITION','UNKNOWN')

def features(node):
    m=node['metadata'];flags=m.get('structural_flags',[])
    # Binding values / stage / scope also enter the frozen text embedding, not just JSON.
    return ([float(node['type']==k) for k in TYPES]+[float(m.get('statement_status')==s) for s in STATUS]+
        [float(m.get('state')==s) for s in ('TRUE','FALSE','UNKNOWN','CONFLICTED')]+
        [float(m.get('document_role')==s) for s in ('TARGET','STATUTE','PRECEDENT')]+
        [float(m.get('operator')==s) for s in ('ALL','ANY','OPEN_TEXT')]+
        [float(any(x.startswith(s) for x in flags)) for s in ('MISSING','UNREVIEWED_PREDICATE_MAPPING','STATUS_MISMATCH','TIME_UNKNOWN','OBJECT_UNKNOWN','OBJECT_CONFLICT','TIME_SCOPE_JOIN_UNREVIEWED','FOREIGN_SOURCE')]+
        [float(bool(m.get(k))) for k in ('limitations','scope_limits','unimplemented','burden_policy','bindings','time_scope')])

def node_text(n):return n['text']+'\nMETADATA: '+json.dumps(n['metadata'],sort_keys=True,ensure_ascii=False)

def tensors(g,vectors):
    nodes=sorted(g['nodes'],key=lambda n:n['id']);idx={n['id']:i for i,n in enumerate(nodes)}
    x=mx.array(np.array([list(vectors[hashlib.sha256(node_text(n).encode()).hexdigest()])+features(n) for n in nodes],np.float32))
    edge=np.array([[idx[a],idx[b],RELATIONS.index(r)] for a,b,r in g['edges']],np.int32).reshape(-1,3)
    adj=np.zeros((len(RELATIONS),len(nodes),len(nodes)),np.float32)
    for a,b,r in edge:adj[r,b,a]+=1
    adj/=np.maximum(adj.sum(axis=2,keepdims=True),1)
    cs=[n['id'] for n in nodes if n['type']=='CANDIDATE']
    return {'x':x,'adj':mx.array(adj),'edges':mx.array(edge),'query':mx.array([idx[c] for c in cs],dtype=mx.int32),'ids':[c.split(':',1)[1] for c in cs]}

class Ranker(nn.Module):
    def __init__(self,kind,width):
        super().__init__();self.kind=kind;h=64
        self.project=nn.Linear(width,h);self.self_layers=[nn.Linear(h,h) for _ in range(2)]
        self.dropout=nn.Dropout(.1);self.edge_encoder=nn.Linear(2*h+len(RELATIONS),h);self.head=nn.Linear(3*h,2)
        if kind=='RGCN':
            self.bases=mx.random.normal((2,4,h,h))*.03
            self.coefficients=mx.random.normal((2,len(RELATIONS),4))*.03
    def __call__(self,d):
        h=nn.relu(self.project(d['x']))
        for i,layer in enumerate(self.self_layers):
            y=layer(h)
            if self.kind=='RGCN':
                w=mx.einsum('rb,bij->rij',self.coefficients[i],self.bases[i])
                y=y+mx.einsum('rtn,rnj->tj',d['adj'],mx.einsum('ni,rij->rnj',h,w))
            h=self.dropout(nn.relu(y))
        q=h[d['query']];pool=mx.softmax(q@h.T/8,axis=1)@h
        if len(d['edges']):
            e=d['edges'];z=nn.relu(self.edge_encoder(mx.concatenate([h[e[:,0]],mx.eye(len(RELATIONS))[e[:,2]],h[e[:,1]]],axis=1)))
            ep=mx.softmax(q@z.T/8,axis=1)@z
        else:ep=mx.zeros_like(q)
        return self.head(mx.concatenate([q,pool,ep],axis=1))

def parameter_hash(model):
    h=hashlib.sha256()
    for k,v in tree_flatten(model.parameters()):h.update(k.encode());h.update(np.array(v).tobytes())
    return h.hexdigest()

def predict(model,data):
    model.eval();out={}
    for cid,d in data.items():out[cid]=dict(zip(d['ids'],map(float,np.array(mx.softmax(model(d),axis=1)[:,1]))))
    return out

def fit(kind,seed,train,heldout,labels,out,epochs=100):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);mx.random.seed(seed)
    model=Ranker(kind,next(iter(train.values()))['x'].shape[1]);mx.eval(model.parameters());before=parameter_hash(model)
    optimizer=optim.AdamW(learning_rate=.001,weight_decay=.0001)
    def loss(m):
        losses=[]
        for cid,d in train.items():
            pairs=[(i,labels[cid][k]) for i,k in enumerate(d['ids']) if labels[cid].get(k) in (0,1)]
            if pairs:
                ix,y=zip(*pairs);losses.append(nn.losses.cross_entropy(m(d)[mx.array(ix)],mx.array(y),reduction='mean'))
        if not losses:raise ValueError('NO_SUPERVISION')
        return mx.mean(mx.stack(losses))
    step=nn.value_and_grad(model,loss);started=time.perf_counter();model.train()
    # No heldout early stopping: fixed 100 epochs; record each before export.
    with (out/'training.jsonl').open('x') as log:
        for epoch in range(epochs):
            l,g=step(model);optimizer.update(model,g);mx.eval(model.parameters(),optimizer.state,l)
            if not np.isfinite(float(l.item())):raise ValueError('NONFINITE_LOSS')
            log.write(json.dumps({'epoch':epoch+1,'loss':float(l.item())})+'\n');log.flush()
    predictions=predict(model,heldout);write_once(out/'predictions.json',predictions)
    after=parameter_hash(model);write_once(out/'training-complete.json',{'seed':seed,'kind':kind,'epochs':epochs,
        'seconds':time.perf_counter()-started,'before':before,'after':after,'updated':before!=after,
        'parameter_count':sum(v.size for _,v in tree_flatten(model.parameters())),
        'train':list(train),'heldout':list(heldout),'heldout_used_for_selection':False})
    try:
        model.save_weights(str(out/'weights.safetensors'))
        restored=Ranker(kind,next(iter(train.values()))['x'].shape[1]);restored.load_weights(str(out/'weights.safetensors'));mx.eval(restored.parameters())
        fresh=predict(restored,heldout)
        delta=max(abs(fresh[c][k]-predictions[c][k]) for c in fresh for k in fresh[c])
        write_once(out/'reload.json',{'max_absolute_difference':delta,'passed':delta<=1e-7,'weights_hash':hashlib.sha256((out/'weights.safetensors').read_bytes()).hexdigest()})
        if delta>1e-7:raise ValueError('WEIGHT_RELOAD_MISMATCH')
    except Exception as exc:
        write_once(out/'export-failure.json',{'stage':'WEIGHTS_EXPORT_OR_RELOAD','reason':str(exc),'logs_and_predictions_preserved':True});raise
    return predictions
