"""Immutable local flow. The old gate remains the sole computation entry."""
from . import adapter, graph, ranking, contrasts
from .contracts import ContractError, validate, write_immutable


def run(query,references,destination,run_id='LOCAL_CONTRACT_ACCEPTANCE',neural_smoke=False,feature_provider=None):
    from pathlib import Path
    dest=Path(destination);q=validate(query,'CasePacket')
    for value in references:validate(value,'CasePacket')
    release=graph.build(references,query)
    features=graph.hashed_features(release) if feature_provider is None else feature_provider(release)
    graph.check_features(release,features)
    pool=ranking.candidate_pool(release,references,query,features=features)
    req=ranking.request(release,pool,features,run_id,scorer='RRF')
    ranked=ranking.baseline(req,release,pool,features)
    bundle=contrasts.form(ranked,req,release,pool)
    gate=adapter.handoff(query)
    result={'query_packet_sha256':query['sha256'],'graph_sha256':release['sha256'],
        'pool_sha256':pool['sha256'],'rank_sha256':ranked['sha256'],'contrast_sha256':bundle['sha256'],
        'candidate_count':len(pool['body']['candidates']),
        'accepted_contrasts':len(bundle['body']['contrasts']),
        'existing_gate_status':gate['contract_status'],'formal_answer_present':gate['formal_answer'] is not None,
        'automatic_computation_status':gate['automatic_computation_status'],
        'generation_calls':0,'training_calls':0,'semantic_approval':False,'legal_approval':False,
        'historical_contrasts_are_query_evidence':False,
        'effectiveness_evaluated':False,'feature_method':features['config']['method']}
    for name,value in [('query-packet.json',query),('graph.json',release),('pool.json',pool),
            ('features.json',features),('rank-request.json',req),('rank-result.json',ranked),
            ('contrasts.json',bundle),('existing-gate.json',gate)]:write_immutable(dest/name,value)
    if neural_smoke:
        from . import model
        import torch
        net,checkpoint=model.initialize_smoke(release,features)
        nr=ranking.request(release,pool,features,run_id+'/SAGE_SMOKE',None,
                           'SAGE_SMOKE',checkpoint)
        predicted,data,mapping=model.rank(nr,release,pool,features,net,checkpoint)
        if {s['uid'] for s in predicted['body']['scores']}!={s['uid'] for s in ranked['body']['scores']}:
            raise ContractError('BASELINE_NEURAL_CANDIDATE_ASYMMETRY')
        write_immutable(dest/'sage-request.json',nr);write_immutable(dest/'sage-result.json',predicted)
        write_immutable(dest/'sage-checkpoint-metadata.json',checkpoint)
        write_immutable(dest/'sage-node-map.json',mapping)
        # Tensor-only serialization supports weights_only=True; no model weights exported.
        tensor_path=dest/'sage_graph.pt'
        if not tensor_path.exists():
            with tensor_path.open('xb') as stream:
                torch.save({'graph_sha256':release['sha256'],'feature_sha256':features['sha256'],
                            'node_map':mapping,'x_dict':data.x_dict,'edge_index_dict':data.edge_index_dict},stream)
        saved=torch.load(tensor_path,map_location='cpu',weights_only=True)
        if (saved['node_map']!=mapping or saved['graph_sha256']!=release['sha256']
                or saved['feature_sha256']!=features['sha256']
                or set(saved['x_dict'])!=set(data.x_dict) or set(saved['edge_index_dict'])!=set(data.edge_index_dict)
                or any(not torch.equal(saved['x_dict'][k],v) for k,v in data.x_dict.items())
                or any(not torch.equal(saved['edge_index_dict'][k],v) for k,v in data.edge_index_dict.items())):
            raise ContractError('TENSOR_ROUNDTRIP')
        result.update(neural_runtime_status=predicted['body']['runtime_status'],
                      random_weight_hash=checkpoint['sha256'],gnn_effectiveness_evaluated=False)
    write_immutable(dest/'summary.json',result)
    return result
