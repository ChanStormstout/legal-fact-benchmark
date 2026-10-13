"""Actual PyG relation-aware GraphSAGE; frozen inference, no fitting entry point."""
import hashlib
import torch
from torch import nn
from torch_geometric.data import HeteroData
from torch_geometric.nn import HeteroConv, SAGEConv
from .contracts import ContractError, TASK, digest, validate
from .graph import check_features, sample
from .ranking import join, result, validate_result


class Ranker(nn.Module):
    def __init__(self,node_types,relation_types,input_dim=64,hidden=128):
        super().__init__()
        self.types=tuple(node_types);self.relations=tuple(tuple(x.split('|')) for x in relation_types)
        self.project=nn.ModuleDict({t:nn.Linear(input_dim,hidden) for t in self.types})
        self.self_layers=nn.ModuleList([nn.ModuleDict({t:nn.Linear(hidden,hidden) for t in self.types}) for _ in range(2)])
        self.layers=nn.ModuleList([HeteroConv({r:SAGEConv((hidden,hidden),hidden,
            aggr='mean',root_weight=False,bias=False) for r in self.relations},aggr='mean') for _ in range(2)])
        self.head=nn.Sequential(nn.Linear(hidden*4,hidden),nn.ReLU(),nn.Linear(hidden,1))

    def forward(self,data):
        x={t:self.project[t](data[t].x) for t in self.types}
        for layer,root in zip(self.layers,self.self_layers):
            messages=layer(x,data.edge_index_dict)
            x={t:torch.relu(root[t](x[t])+messages.get(t,torch.zeros_like(x[t]))) for t in self.types}
        return x

    def score(self,query,candidates):
        q=query.expand(candidates.shape[0],-1)
        return self.head(torch.cat((q,candidates,torch.abs(q-candidates),q*candidates),dim=1)).flatten()


def to_data(graph,features,sampled):
    g=validate(graph,'GraphRelease');check_features(graph,features)
    if sampled['graph_sha256']!=graph['sha256']:
        raise ContractError('STALE_SAMPLE')
    nodes={n['uid']:n for n in g['nodes']};chosen=set(sampled['node_ids'])
    if chosen-set(nodes):raise ContractError('SAMPLE_NODE_SET')
    allowed={digest(e) for e in g['edges']}
    if any(digest(e) not in allowed or e['src'] not in chosen or e['dst'] not in chosen for e in sampled['edges']):
        raise ContractError('SAMPLE_EDGE_SET')
    data=HeteroData();mapping={}
    for t in g['node_types']:
        ids=sorted(i for i in chosen if nodes[i]['node_type']==t);mapping[t]=ids
        data[t].x=torch.tensor([features['vectors'][i] for i in ids],dtype=torch.float32).reshape(-1,features['config']['dimension'])
    indices={t:{i:j for j,i in enumerate(ids)} for t,ids in mapping.items()}
    for key in g['relation_types']:
        a,r,b=key.split('|')
        edges=[(indices[a][e['src']],indices[b][e['dst']]) for e in sampled['edges']
               if e['relation']==r and nodes[e['src']]['node_type']==a and nodes[e['dst']]['node_type']==b]
        data[a,r,b].edge_index=torch.tensor(edges,dtype=torch.long).reshape(-1,2).T.contiguous()
    data.validate(raise_on_error=True)
    return data,mapping


def state_hash(model):
    h=hashlib.sha256()
    for name,t in sorted(model.state_dict().items()):
        h.update(name.encode());h.update(str(tuple(t.shape)).encode());h.update(t.detach().cpu().numpy().tobytes())
    return h.hexdigest()


def initialize_smoke(graph,features,seed=0):
    g=validate(graph,'GraphRelease');check_features(graph,features)
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        model=Ranker(g['node_types'],g['relation_types'],features['config']['dimension'])
    model.eval()
    checkpoint={'task_id':TASK,'role':'RANDOM_SMOKE','sha256':state_hash(model),
        'feature_config_sha256':digest(features['config']), 'seed':seed,
        'node_types':g['node_types'],'relation_types':g['relation_types'],
        'architecture':'PYG_RELATION_SAGE_2X128_MEAN','trained':False}
    return model,checkpoint


def rank(req,graph,pool,features,model,checkpoint):
    r,g,p=join(req,graph,pool,features)
    if (r['checkpoint_sha256']!=state_hash(model) or r['checkpoint_sha256']!=checkpoint['sha256']
            or r['checkpoint_role']!=checkpoint['role'] or checkpoint['task_id']!=TASK
            or checkpoint['feature_config_sha256']!=digest(features['config'])
            or list(model.types)!=g['node_types'] or ['|'.join(x) for x in model.relations]!=g['relation_types']):
        raise ContractError('MODEL_CHECKPOINT_MISMATCH')
    if r['scorer'] not in ('SAGE_SMOKE','SAGE'):
        raise ContractError('NEURAL_SCORER')
    query=[n['uid'] for n in g['nodes'] if n['node_type']=='ISSUE' and n['case_id']==g['query_case_id']]
    if len(query)!=1:raise ContractError('QUERY_ISSUE_COUNT')
    sampled=sample(graph,query+[c['route_id'] for c in p['candidates']],r['fanouts'],r['seed'])
    data,mapping=to_data(graph,features,sampled)
    model.eval()
    with torch.no_grad():
        embeddings=model(data)
        qi=mapping['ISSUE'].index(query[0]); ci=[mapping['ROUTE'].index(c['route_id']) for c in p['candidates']]
        scores=model.score(embeddings['ISSUE'][qi:qi+1],embeddings['ROUTE'][ci]).tolist()
    out=result(req,graph,pool,dict(zip([c['uid'] for c in p['candidates']],scores)),
        {'method':'PYG_GRAPH_SAGE','sampling':sampled,'feature_method':features['config']['method'],
         'weights_before':checkpoint['sha256'],'weights_after':state_hash(model),'training_calls':0,
         'complete_rule_conditions_read_by_neural_model':False})
    validate_result(out,req,graph,pool)
    return out,data,mapping
