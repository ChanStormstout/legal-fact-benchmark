"""Small fold-local pairwise linear/RGCN/no-message capacity comparison in MLX."""
import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as opt
from mlx.utils import tree_flatten
import numpy as np
from .rgcn_development_v2 import WIDTH,EDGE_TYPES,Z_NAMES

class Ranker(nn.Module):
 def __init__(self,kind):
  super().__init__();self.kind=kind
  if kind=='B':self.linear=nn.Linear(len(Z_NAMES),1,bias=False)
  else:
   self.project=nn.Linear(WIDTH,16)
   self.self_layers=[nn.Linear(16,16) for _ in range(2)]
   # Two basis matrices; identical parameters initialized for C and C0.
   self.bases=mx.random.normal((2,2,16,16))*.05
   self.coefficients=mx.random.normal((2,len(EDGE_TYPES),2))*.05
   self.hidden=nn.Linear(7*16+len(Z_NAMES),16)
   self.output=nn.Linear(16,1)
 def __call__(self,d):
  if self.kind=='B':return self.linear(d['z']).reshape(-1)
  h=nn.relu(self.project(d['x']))
  for i in range(2):
   y=self.self_layers[i](h)
   if self.kind=='C':
    # Relation-wise normalized messages. Axis order: relation,target,source.
    w=mx.einsum('rb,bij->rij',self.coefficients[i],self.bases[i])
    transformed=mx.einsum('ni,rij->rnj',h,w)
    y=y+mx.einsum('rtn,rnj->tj',d['adj'],transformed)
   h=nn.relu(y)
  pooled=mx.einsum('ltn,nw->ltw',d['pools'],h).reshape(d['pools'].shape[0],-1)
  return self.output(nn.relu(self.hidden(mx.concatenate([pooled,d['z']],axis=1)))).reshape(-1)

def params(model):return sum(x.size for _,x in tree_flatten(model.trainable_parameters()))
def fit(kind,train_data,preferences,seed,steps=200,lr=.003,l2=.001):
 if not preferences or not any(preferences.values()):raise ValueError('NO_VALID_EXPLICIT_PREFERENCES')
 mx.random.seed(seed);model=Ranker(kind);mx.eval(model.parameters());before={k:np.array(v) for k,v in tree_flatten(model.parameters())}
 optimizer=opt.Adam(lr)
 def loss(m):
  losses=[]
  for cid,pairs in preferences.items():
   if not pairs:continue
   scores=m(train_data[cid]);p=mx.array(pairs,dtype=mx.int32)
   losses.append(mx.mean(mx.logaddexp(mx.array(0.),scores[p[:,1]]-scores[p[:,0]])))
  data=mx.mean(mx.stack(losses));penalty=sum(mx.sum(v*v) for _,v in tree_flatten(m.trainable_parameters()))
  return data+l2*penalty
 grad=nn.value_and_grad(model,loss);hist=[];first_grad=None
 for step in range(steps):
  value,g=grad(model);optimizer.update(model,g);mx.eval(model.parameters(),optimizer.state,value,g)
  if first_grad is None:first_grad=float(sum(mx.sum(v*v).item() for _,v in tree_flatten(g)))**.5
  hist.append(float(value.item()))
 delta=float(sum(np.sum((np.array(v)-before[k])**2) for k,v in tree_flatten(model.parameters())))**.5
 if not np.isfinite(hist).all() or not np.isfinite(delta):raise ValueError('NONFINITE_TRAINING')
 return model,dict(loss=hist,gradient_norm_first=first_grad,parameter_delta_norm=delta,parameters=params(model),updates=steps,valid_preferences=sum(len(p) for p in preferences.values()),trained_cases=list(preferences),kind=kind,seed=seed)

def fold_data(raw,train_ids):
 z=np.concatenate([raw[c]['z'] for c in train_ids],axis=0);mean=z.mean(axis=0);std=z.std(axis=0);std=np.where(std>1e-6,std,1.)
 data={c:{k:mx.array((v-mean)/std if k=='z' else v) for k,v in d.items()} for c,d in raw.items()}
 return data,dict(mean=mean.tolist(),std=std.tolist(),fit_case_ids=train_ids)
