"""Tiny R-GCN numerical interface, existing MLX only. No actual study05 training.

Per-relation matrices with normalized directed neighborhoods and separate self transform.
Parameters are shared across case graphs; node IDs never select learnable parameters.
"""
import mlx.core as mx
import mlx.nn as nn
from .rgcn_feasibility_v1 import features, adjacency, training_gate

class TinyRGCN(nn.Module):
    def __init__(self, relation_types, width=16):
        super().__init__()
        self.relation_types=tuple(sorted(relation_types));self.width=width
        self.self_layers=[nn.Linear(width,width,bias=False) for _ in range(2)]
        self.rel_layers=[[nn.Linear(width,width,bias=False) for _ in self.relation_types] for _ in range(2)]
        self.decoder=nn.Linear(width,width,bias=False)
    def __call__(self,x,adj):
        for self_layer,rel_layers in zip(self.self_layers,self.rel_layers):
            y=self_layer(x)
            for r,layer in zip(self.relation_types,rel_layers):
                if r in adj:y=y+adj[r]@layer(x)
            x=mx.maximum(y,0)
        return x
    def pair_scores(self,x,adj,query_index,law_indices):
        h=self(x,adj);return h[mx.array(law_indices)]@self.decoder(h[query_index])

def tensors(graph,relation_types=None):
    a=adjacency(graph)
    if relation_types is not None and set(a)-set(relation_types):raise ValueError('UNSUPPORTED_NEW_EDGE_TYPE')
    return mx.array(features(graph)),{r:mx.array(v) for r,v in a.items()}

def fit(model,graph_tensors,prefs,gate,steps=100,learning_rate=0.001):
    """Only explicit within-case preferences. Never sample unmarked laws as negatives.

    gate must be produced by training_gate; caller owns split/source validation.
    This interface is not invoked on study05 real cases.
    """
    if not gate.get('ready'):raise ValueError('TRAINING_GATE_CLOSED')
    if not prefs:raise ValueError('NO_PREFERENCES')
    import mlx.optimizers as optim
    optimizer=optim.Adam(learning_rate=learning_rate)
    def loss(model):
        terms=[]
        for cid,q,p,o in prefs:
            x,a=graph_tensors[cid];s=model.pair_scores(x,a,q,[p,o]);terms.append(mx.logaddexp(mx.array(0.),s[1]-s[0]))
        return mx.mean(mx.stack(terms))
    grad=nn.value_and_grad(model,loss);history=[]
    for _ in range(steps):
        value,g=grad(model);optimizer.update(model,g);mx.eval(model.parameters(),optimizer.state,value);history.append(float(value.item()))
    return history
