"""V11 Flat/R-GCN architecture, only scalar output replaced by three use classes."""
import mlx.core as mx
import mlx.nn as nn
from .state_ranker_v11 import StateRanker,REL,parameter_hash
class UseClassifier(StateRanker):
 def __init__(self,kind,width):
  super().__init__(kind,width);self.head=nn.Linear(320,3)
 def __call__(self,d,dyn,qid):
  h=nn.relu(self.project(mx.concatenate([d['x'],dyn],axis=1)))
  for i,l in enumerate(self.layers):
   y=l(h)
   if self.kind=='RGCN':
    w=mx.einsum('rb,bij->rij',self.coef[i],self.bases[i]);y=y+mx.einsum('rtn,rnj->tj',d['adj'],mx.einsum('ni,rij->rnj',h,w))
   h=self.drop(nn.relu(y))
  c=h[mx.array(d['candidate_indices'])];q=mx.broadcast_to(h[d['request_indices'][qid]],c.shape)
  # Same architecture, no selected-route/label features. Selected pool therefore zero.
  selected=mx.zeros_like(c);pool=mx.softmax(c@h.T/8,axis=1)@h;e=d['edges']
  if e.shape[0]:
   z=nn.relu(self.triple(mx.concatenate([h[e[:,0]],mx.eye(2*len(REL))[e[:,2]],h[e[:,1]]],axis=1)));ep=mx.softmax(c@z.T/8,axis=1)@z
  else:ep=mx.zeros_like(c)
  return self.head(mx.concatenate([c,q,selected,pool,ep],axis=1))
