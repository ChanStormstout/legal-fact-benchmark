"""Same node/edge records and head; Graph adds typed neighborhood propagation."""
import numpy as np
import mlx.core as mx
import mlx.nn as nn
from mlx.utils import tree_flatten

from .aligned_graph import RELATIONS,TYPES as NODE_TYPES
STATUS=('CLAIMED','DENIED','ADMITTED','PRIOR_FOUND','DOCUMENT_RECORDED','UNKNOWN')
STAGES=('PRE_TARGET_RECORD','PRIOR_COURT_FINDING','TARGET_STAGE_PARTY_ARGUMENT')
AVAIL=('DIRECT_PRE_TARGET_SOURCE','RETROSPECTIVELY_RECONSTRUCTED_PRE_TARGET','UNKNOWN')
COURTS=('NONE','RENT_CONTROLLER','ARC','ARCT','TRIBUNAL','HIGH_COURT','SUPREME_COURT','UNKNOWN')
SIDE=('CLAIMANT','RESPONDENT','NEUTRAL','UNKNOWN')
POLARITY=('POSITIVE','NEGATIVE','UNKNOWN')
CONDITION_KIND=('NECESSARY','ALTERNATIVE','QUALIFICATION','BURDEN_TRIGGER','FACTOR','UNKNOWN')

def onehot(value,values):return [float(value==x) for x in values]
def metadata(n):
    f=n['features']
    return (onehot(n['type'],NODE_TYPES)+onehot(f.get('statement_status'),STATUS)+
        onehot(f.get('semantic_stage'),STAGES)+onehot(f.get('prospective_availability'),AVAIL)+
        onehot(f.get('court_level'),COURTS)+onehot(f.get('party_side'),SIDE)+
        onehot(f.get('polarity'),POLARITY)+onehot(f.get('condition_kind'),CONDITION_KIND)+onehot(f.get('source_status'),('STATUTE','COURT_ADOPTED','REPORTED_OPINION','RESEARCHER_TRANSLATION','MODEL_PROPOSAL'))+[float(n['source_grounded'])])

def tensorize(graph, embeddings, use_anco=False):
    nodes=sorted(graph['nodes'],key=lambda n:n['id']);idx={n['id']:i for i,n in enumerate(nodes)}
    x=np.array([list(embeddings[n['id']])+metadata(n)+([float(n.get('anco',{}).get('score',0)),float(n.get('anco',{}).get('valid',False)),float(n.get('anco',{}).get('conflict',False))] if use_anco else []) for n in nodes],dtype=np.float32)
    edges=sorted(graph['edges'],key=lambda e:(e['source'],e['target'],e['type']))
    if any(e['type'] not in RELATIONS for e in edges):raise ValueError('UNSUPPORTED_RELATION')
    edge_idx=np.array([[idx[e['source']],idx[e['target']],RELATIONS.index(e['type'])] for e in edges],dtype=np.int32).reshape(-1,3)
    adj=np.zeros((len(RELATIONS),len(nodes),len(nodes)),dtype=np.float32)
    for s,t,r in edge_idx:adj[r,t,s]+=1
    den=adj.sum(axis=2,keepdims=True);adj/=np.maximum(den,1)
    condition_ids=[n['id'] for n in nodes if n['type']=='Test']
    return {'x':mx.array(x),'edges':mx.array(edge_idx),'adj':mx.array(adj),
        'conditions':mx.array([idx[c] for c in condition_ids],dtype=mx.int32),
        'condition_ids':condition_ids}

class ApplicationModel(nn.Module):
    def __init__(self,kind,input_width,hidden=64,dropout=.1):
        super().__init__();self.kind=kind;self.hidden=hidden
        self.project=nn.Linear(input_width,hidden)
        self.self_layers=[nn.Linear(hidden,hidden) for _ in range(2)]
        self.dropout=nn.Dropout(dropout)
        self.edge_encoder=nn.Linear(2*hidden+len(RELATIONS),hidden)
        self.head=nn.Linear(3*hidden,3)
        if kind=='Graph':
            self.bases=mx.random.normal((2,4,hidden,hidden))*.03
            self.coefficients=mx.random.normal((2,len(RELATIONS),4))*.03
        elif kind!='Flat':raise ValueError(kind)
    def __call__(self,d):
        h=nn.relu(self.project(d['x']))
        for layer in range(2):
            y=self.self_layers[layer](h)
            if self.kind=='Graph':
                w=mx.einsum('rb,bij->rij',self.coefficients[layer],self.bases[layer])
                y=y+mx.einsum('rtn,rnj->tj',d['adj'],mx.einsum('ni,rij->rnj',h,w))
            h=self.dropout(nn.relu(y))
        q=h[d['conditions']]
        node_pool=mx.softmax(q@h.T/(self.hidden**.5),axis=1)@h
        if len(d['edges']):
            e=d['edges'];rels=mx.eye(len(RELATIONS))[e[:,2]]
            z=nn.relu(self.edge_encoder(mx.concatenate([h[e[:,0]],rels,h[e[:,1]]],axis=1)))
            edge_pool=mx.softmax(q@z.T/(self.hidden**.5),axis=1)@z
        else:edge_pool=mx.zeros_like(q)
        return self.head(mx.concatenate([q,node_pool,edge_pool],axis=1))

def parameter_count(model):return sum(v.size for _,v in tree_flatten(model.trainable_parameters()))

def masked_group_loss(model,packages):
    groups={}
    for p in packages:
        mask=np.array(p['mask'],bool)
        if not mask.any():continue
        ids=mx.array(np.where(mask)[0],dtype=mx.int32)
        # Only select supervised targets before CE; masked placeholders never evaluated.
        labels=mx.array(np.array(p['labels'])[mask],dtype=mx.int32)
        loss=nn.losses.cross_entropy(model(p['tensors'])[ids],labels,reduction='mean')
        groups.setdefault(p['group_id'],[]).append(loss)
    if not groups:raise ValueError('NO_SUPERVISED_CONDITIONS_IN_BATCH')
    return mx.mean(mx.stack([mx.mean(mx.stack(values)) for values in groups.values()]))
