"""Same state/node/triple inputs, Flat versus two-layer 64d basis R-GCN.
Frozen cached E5 vectors only. Pairwise loss never treats unlabelled actions as negatives.
"""
import json,hashlib,time
from pathlib import Path
import numpy as np
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx.utils import tree_flatten
from .search_v11 import state_features
REL=('FACT_APPLICATION','RULE_APPLICATION','RULE_DEPENDENCY','REQUEST_APPLICATION','OBJECT_FACT','SUPPORT','OPPOSE','UNRESOLVED')

def base_data(facts,rules,candidates,requests,vectors,composites=()):
    nodes=[];index={};edges=[];width=len(next(iter(vectors.values())))
    def vector(text):
        k=hashlib.sha256(text.encode()).hexdigest()
        if k not in vectors:raise ValueError('ENCODING_NOT_CACHED:'+text[:80])
        return np.asarray(vectors[k])
    def add(k,v,kind):index[k]=len(nodes);nodes.append(np.concatenate([v,np.eye(5)[kind]]))
    fv={p['id']:vector(p['text']) for p in facts['premises']}
    for c in composites:fv[c['premise']['id']]=np.mean([fv[k] for k in c['components']],axis=0)
    for k,v in fv.items():add('F:'+k,v,0)
    rv={k:np.mean([vector(s['description']) for s in r['slots']],axis=0) for k,r in rules.items()}
    for k,v in rv.items():add('R:'+k,v,1)
    for c in candidates:
        pieces=[rv[c['rule_ref']]]+[fv[x['id']] for x in c['inputs'] if x['kind']=='PREMISE' and x['id'] in fv]
        add('C:'+c['id'],np.mean(pieces,axis=0),2);edges.append(('R:'+c['rule_ref'],'C:'+c['id'],1))
        for x in c['inputs']:
            if x['kind']=='PREMISE':edges.append(('F:'+x['id'],'C:'+c['id'],0))
            elif x['kind']=='RULE_DEPENDENCY':edges.append(('R:'+x['id'],'C:'+c['id'],2))
    for q in requests:
        qs=[v for k,v in rv.items() if rules[k]['conclusion_predicate']==q['predicate']];add('Q:'+q['id'],np.mean(qs,axis=0) if qs else np.zeros(width),3)
        for c in candidates:
            if rules[c['rule_ref']]['conclusion_predicate']==q['predicate']:edges.append(('C:'+c['id'],'Q:'+q['id'],3))
    for e in facts['entities']:
        vv=[fv[p['id']] for p in facts['premises'] if any(b['entity']==e['id'] for b in p['bindings'])];add('E:'+e['id'],np.mean(vv,axis=0) if vv else np.zeros(width),4)
    for p in facts['premises']:
        for b in p['bindings']:edges.append(('E:'+b['entity'],'F:'+p['id'],4))
    for e in facts['relations']:edges.append(('F:'+e['from'],'F:'+e['to'],{'SUPPORT':5,'OPPOSE':6,'UNRESOLVED':7}[e['sign']]))
    edges=[(index[a],index[b],r) for a,b,r in edges if a in index and b in index]
    # Reverse edges are computational messages only, not reversed legal implications.
    edges+= [(b,a,r+len(REL)) for a,b,r in list(edges)]
    adj=np.zeros((2*len(REL),len(nodes),len(nodes)),np.float32)
    for a,b,r in edges:adj[r,b,a]+=1
    adj/=np.maximum(adj.sum(axis=2,keepdims=True),1)
    return {'x':mx.array(np.asarray(nodes,dtype=np.float32)),'adj':mx.array(adj),'edges':mx.array(np.array(edges,np.int32).reshape(-1,3)),'candidate_indices':[index['C:'+c['id']] for c in candidates],'request_indices':{q['id']:index['Q:'+q['id']] for q in requests},'ids':[c['id'] for c in candidates],'node_ids':list(index),'node_count':len(nodes),'edge_count':len(edges)}

def state_tensor(base,features,qid):
    dyn=np.zeros((base['node_count'],16),np.float32)
    for idx,k in zip(base['candidate_indices'],base['ids']):dyn[idx,:14]=features[k]
    dyn[base['request_indices'][qid],14]=1
    dyn[:,15]=next(iter(features.values()))[5] if features else 0
    return mx.array(dyn)

class StateRanker(nn.Module):
    def __init__(self,kind,width):
        super().__init__();self.kind=kind;h=64;nr=2*len(REL)
        self.project=nn.Linear(width+16,h);self.layers=[nn.Linear(h,h) for _ in range(2)];self.drop=nn.Dropout(.1);self.triple=nn.Linear(2*h+nr,h);self.head=nn.Linear(5*h,1)
        if kind=='RGCN':self.bases=mx.random.normal((2,4,h,h))*.03;self.coef=mx.random.normal((2,nr,4))*.03
    def __call__(self,d,dyn,qid):
        h=nn.relu(self.project(mx.concatenate([d['x'],dyn],axis=1)))
        for i,l in enumerate(self.layers):
            y=l(h)
            if self.kind=='RGCN':
                w=mx.einsum('rb,bij->rij',self.coef[i],self.bases[i]);y=y+mx.einsum('rtn,rnj->tj',d['adj'],mx.einsum('ni,rij->rnj',h,w))
            h=self.drop(nn.relu(y))
        c=h[mx.array(d['candidate_indices'])];q=mx.broadcast_to(h[d['request_indices'][qid]],c.shape);chosen=dyn[mx.array(d['candidate_indices']),4];selected=mx.broadcast_to(mx.sum(c*chosen[:,None],axis=0)/mx.maximum(mx.sum(chosen),1),c.shape);pool=mx.softmax(c@h.T/8,axis=1)@h
        e=d['edges'];z=nn.relu(self.triple(mx.concatenate([h[e[:,0]],mx.eye(2*len(REL))[e[:,2]],h[e[:,1]]],axis=1)));ep=mx.softmax(c@z.T/8,axis=1)@z
        return self.head(mx.concatenate([c,q,selected,pool,ep],axis=1))[:,0]

def parameter_hash(m):
    h=hashlib.sha256()
    for k,v in tree_flatten(m.parameters()):h.update(k.encode());h.update(np.array(v).tobytes())
    return h.hexdigest()

def fit(kind,seed,data,examples,out,epochs=30,deadline=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);mx.random.seed(seed);m=StateRanker(kind,next(iter(data.values()))['x'].shape[1]);mx.eval(m.parameters());before=parameter_hash(m);opt=optim.AdamW(learning_rate=.001,weight_decay=.0001);start=time.perf_counter();cases=[c for c in data if examples.get(c)]
    if not cases:raise ValueError('NO_CONFIRMED_WITHIN_STATE_PAIRS')
    def loss(model,cid,ex):
        values=[]
        for e in ex:
            s=model(data[cid],e['tensor'],e['request']);pairs=mx.array(e['pair_indices']);delta=s[pairs[:,1]]-s[pairs[:,0]];values.append(mx.mean(mx.logaddexp(mx.array(0.),delta)))
        return mx.mean(mx.stack(values))
    grad=nn.value_and_grad(m,loss);m.train()
    with (out/'training.jsonl').open('x') as log:
        for epoch in range(epochs):
            losses=[]
            for cid in cases:
                # Fixed deterministic state minibatches, no heldout-based tuning.
                for a in range(0,len(examples[cid]),8):
                    if deadline and time.perf_counter()>deadline:raise TimeoutError('TRAINING_BUDGET_EXHAUSTED')
                    value,g=grad(m,cid,examples[cid][a:a+8]);opt.update(m,g);mx.eval(m.parameters(),opt.state,value);v=float(value.item())
                    if not np.isfinite(v):raise ValueError('NONFINITE_LOSS')
                    losses.append(v)
            log.write(json.dumps({'epoch':epoch+1,'loss':float(np.mean(losses))})+'\n');log.flush()
    m.eval();after=parameter_hash(m);meta={'kind':kind,'seed':seed,'epochs':epochs,'seconds':time.perf_counter()-start,'before':before,'after':after,'parameters':sum(v.size for _,v in tree_flatten(m.parameters())),'train_cases':cases,'updated':before!=after,'target':'WITHIN_STATE_PAIRWISE_COMPLETION_RANKING','heldout_used':False}
    (out/'training-complete.json').write_text(json.dumps(meta,indent=2))
    m.save_weights(str(out/'weights.safetensors'));fresh=StateRanker(kind,next(iter(data.values()))['x'].shape[1]);fresh.load_weights(str(out/'weights.safetensors'));fresh.eval();mx.eval(fresh.parameters());assert parameter_hash(fresh)==after
    (out/'reload.json').write_text(json.dumps({'parameter_hash_equal':True,'sha256':hashlib.sha256((out/'weights.safetensors').read_bytes()).hexdigest()}))
    return fresh
