"""Candidate discovery and strict request/result joins. Scores are relevance only."""
import math
from collections import Counter
from .contracts import ContractError, TASK, digest, seal, validate
from .graph import tokens


def compare_scope(query, other):
    checks={}
    for field in ('jurisdiction','stage','legal_period','claim_type','route_family'):
        a,b=query[field],other[field]
        canonical=(field=='stage' and a in {'pleading','trial','appeal','enforcement'} and b in {'pleading','trial','appeal','enforcement'}) or (
            isinstance(a,str) and isinstance(b,str) and a.startswith('urn:') and b.startswith('urn:'))
        checks[field]='PENDING' if a is None or b is None else 'MATCH' if a==b else 'MISMATCH' if canonical else 'PENDING'
    # Unequal descriptive strings are not proof of different legal scope.
    state='INCOMPATIBLE' if 'MISMATCH' in checks.values() else 'PENDING' if 'PENDING' in checks.values() else 'COMPATIBLE'
    return state,checks


def lexical_score(query,text):
    a=Counter(tokens(query)); b=Counter(tokens(text))
    den=math.sqrt(sum(v*v for v in a.values())*sum(v*v for v in b.values()))
    return sum(v*b[k] for k,v in a.items())/den if den else 0.0


def query_uid(graph):
    g=validate(graph,'GraphRelease')
    ids=[n['uid'] for n in g['nodes'] if n['node_type']=='ISSUE' and n['case_id']==g['query_case_id']]
    if len(ids)!=1:raise ContractError('EXPLICIT_QUERY_NODE_REQUIRED')
    return ids[0]


def candidate_pool(graph, references, query, capacity=200,features=None):
    g=validate(graph,'GraphRelease');q=validate(query,'CasePacket')
    from .graph import check_origins
    check_origins(graph,references,query)
    if type(capacity) is not int or capacity<1 or g['query_packet_hash']!=query['sha256']:
        raise ContractError('POOL_CONTEXT')
    rows=[];exclusions=[];graph_nodes={n['uid'] for n in g['nodes']}
    from .signatures import profile,cosine
    signature=profile(graph,[r['uid'] for r in q['routes']])
    dense=features is not None and features['config']['method']=='PINNED_E5_ALL_TOKEN_WINDOWS'
    if features is not None:
        from .graph import check_features
        check_features(graph,features)
    issue=query_uid(graph)
    query_vector=features['vectors'][issue] if dense else None
    scope={}
    for field in ('jurisdiction','stage','legal_period','claim_type','route_family'):
        values={r['scope'][field] for r in q['routes']}
        scope[field]=next(iter(values)) if len(values)==1 else None
    for p in references:
        b=validate(p,'CasePacket')
        if b['group_id']==q['group_id'] or b['case_id']==q['case_id']:
            exclusions.append({'case_id':b['case_id'],'reason':'QUERY_DISPUTE_GROUP'});continue
        if p['sha256'] not in g['packet_hashes']:
            raise ContractError('POOL_PACKET_NOT_IN_GRAPH')
        for r in b['routes']:
            if r['uid'] not in graph_nodes:
                raise ContractError('POOL_ROUTE_NOT_IN_GRAPH')
            status,checks=compare_scope(scope,r['scope'])
            if status=='INCOMPATIBLE':
                exclusions.append({'route_id':r['uid'],'reason':'SCOPE_INCOMPATIBLE','checks':checks});continue
            text=r['text'];other_signature=profile(graph,[r['uid']])
            spectral=cosine(signature['vector'],other_signature['vector']) if signature['available'] and other_signature['available'] else None
            row={'uid':r['uid'],'case_id':b['case_id'],'group_id':b['group_id'],
                'route_id':r['uid'],'scope':r['scope'],'source_ids':r['source_ids'],
                'scope_status':status,'scope_checks':checks,'discovery':['GLOBAL_ISSUE','LEXICAL_COSINE'],
                'discovery_scores':{'lexical':lexical_score(q['query_text'],text),
                    'dense':cosine(query_vector,features['vectors'][r['uid']]) if dense else None,
                    'spectral':spectral,'rrf':0.0},'signature':other_signature}
            if dense:row['discovery'].append('E5_COSINE')
            if spectral is not None:row['discovery'].append('SIGNED_SPECTRAL_COUNTS')
            rows.append(row)
    for channel in ('lexical','dense','spectral'):
        order=sorted((r for r in rows if r['discovery_scores'][channel] is not None),
                     key=lambda r:(-r['discovery_scores'][channel],r['uid']))
        for i,row in enumerate(order,1):row['discovery_scores']['rrf']+=1/(60+i)
    rows.sort(key=lambda r:(-r['discovery_scores']['rrf'],r['uid']))
    for row in rows[capacity:]:exclusions.append({'route_id':row['uid'],'reason':'CAPACITY','capacity':capacity})
    return seal('CandidatePool',{'task_id':TASK,'graph_sha256':graph['sha256'],
        'query_case_id':q['case_id'],'query_group_id':q['group_id'],'query_scope':scope,
        'candidates':rows[:capacity],'exclusions':exclusions,'capacity':capacity,
        'query_signature':signature,'retrieval_config':{'rrf_k':60,'weights':{'lexical':1,'dense':1,'spectral':1},
            'dense_feature_sha256':features['sha256'] if dense else None,
            'spectral_version':'SIGNED_PROPOSAL_COUNTS_V1','scope_unknown_is_negative':False}})


def request(graph,pool,features,run_id,query_id=None,scorer='LEXICAL',checkpoint=None,seed=0,top_k=10,fanouts=(15,10)):
    g=validate(graph,'GraphRelease');p=validate(pool,'CandidatePool')
    from .graph import check_features
    check_features(graph,features)
    expected=query_uid(graph)
    if query_id is not None and query_id!=expected:raise ContractError('REQUEST_QUERY_NODE_MISMATCH')
    query_id=expected
    if p['graph_sha256']!=graph['sha256']:
        raise ContractError('STALE_POOL')
    role='NONE' if checkpoint is None else checkpoint['role']
    if checkpoint is not None:
        if checkpoint['task_id']!=TASK or checkpoint['feature_config_sha256']!=digest(features['config']):
            raise ContractError('CHECKPOINT_TASK_OR_FEATURES')
        if scorer=='SAGE' and (not checkpoint.get('trained',False) or g['visibility_policy']!='SOURCE_VIEW_APPROVED_FOR_TASK'
                or not g['visibility_manifest'].get('textual_outcome_blinding_reviewed')):
            raise ContractError('UNREVIEWED_FEATURE_VISIBILITY')
    return seal('RankRequest',{'task_id':TASK,'run_id':run_id,'query_id':query_id,
        'graph_sha256':graph['sha256'],'pool_sha256':pool['sha256'],'feature_sha256':features['sha256'],
        'visibility_sha256':digest([g['visibility_policy'],g['visibility_manifest']]),
        'checkpoint_sha256':checkpoint['sha256'] if checkpoint else None,'checkpoint_role':role,
        'scorer':scorer,'top_k':top_k,'seed':seed,'fanouts':list(fanouts),
        'serving_policy':'PRIVATE_REFERENCE_PLUS_ONE_QUERY'})


def join(req,graph,pool,features=None):
    r=validate(req,'RankRequest');g=validate(graph,'GraphRelease');p=validate(pool,'CandidatePool')
    if r['graph_sha256']!=graph['sha256'] or r['pool_sha256']!=pool['sha256'] or p['graph_sha256']!=graph['sha256']:
        raise ContractError('STALE_RANK_CONTEXT')
    if r['visibility_sha256']!=digest([g['visibility_policy'],g['visibility_manifest']]):
        raise ContractError('VISIBILITY_MISMATCH')
    if features is not None:
        from .graph import check_features
        check_features(graph,features)
        if r['feature_sha256']!=features['sha256']:
            raise ContractError('STALE_FEATURE_REQUEST')
    if p['query_case_id']!=g['query_case_id'] or p['query_group_id']!=g['query_group_id']:
        raise ContractError('QUERY_IDENTITY_MISMATCH')
    if r['query_id']!=query_uid(graph):raise ContractError('REQUEST_QUERY_NODE_MISMATCH')
    nodes={n['uid']:n for n in g['nodes']}
    for c in p['candidates']:
        node=nodes.get(c['route_id'])
        if node is None or node['node_type']!='ROUTE' or node['case_id']!=c['case_id'] or node['group_id']!=c['group_id']:
            raise ContractError('CANDIDATE_IDENTITY_MISMATCH')
        if c['uid']!=c['route_id'] or c['source_ids']!=node['source_ids']:
            raise ContractError('CANDIDATE_SOURCE_MISMATCH')
        status,checks=compare_scope(p['query_scope'],c['scope'])
        if status!=c['scope_status'] or checks!=c['scope_checks']:
            raise ContractError('SCOPE_STATUS_MISMATCH')
    return r,g,p


def result(req,graph,pool,scores,coverage):
    r,g,p=join(req,graph,pool)
    wanted={c['uid'] for c in p['candidates']}
    if set(scores)!=wanted:
        raise ContractError('SCORE_CANDIDATE_SET')
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in scores.values()):
        raise ContractError('NONFINITE_SCORE')
    ordered=sorted(scores.items(),key=lambda x:(-x[1],x[0]))
    state='NO_CANDIDATES' if not ordered else 'UNTRAINED_SMOKE' if r['scorer']=='SAGE_SMOKE' else 'OK' if r['scorer']=='SAGE' else 'BASELINE_ONLY'
    return seal('RankResult',{'task_id':TASK,'request_sha256':req['sha256'],
        'graph_sha256':graph['sha256'],'pool_sha256':pool['sha256'],'runtime_status':state,
        'scores':[{'uid':i,'score':float(s),'rank':j} for j,(i,s) in enumerate(ordered,1)],
        'selected_ids':[i for i,_ in ordered[:r['top_k']]],'coverage':coverage,
        'semantic_approval':False,'legal_approval':False})


def validate_result(value,req,graph,pool):
    b=validate(value,'RankResult');r,g,p=join(req,graph,pool)
    if b['request_sha256']!=req['sha256'] or b['graph_sha256']!=graph['sha256'] or b['pool_sha256']!=pool['sha256']:
        raise ContractError('STALE_RANK_RESULT')
    ids={c['uid'] for c in p['candidates']}
    if {s['uid'] for s in b['scores']}!=ids or len(b['selected_ids'])!=min(r['top_k'],len(ids)):
        raise ContractError('RESULT_CANDIDATE_COVERAGE')
    expected='NO_CANDIDATES' if not ids else 'UNTRAINED_SMOKE' if r['scorer']=='SAGE_SMOKE' else 'OK' if r['scorer']=='SAGE' else 'BASELINE_ONLY'
    if b['runtime_status']!=expected:
        raise ContractError('FALSE_MODEL_STATUS')
    return b


def baseline(req,graph,pool,features):
    r,g,p=join(req,graph,pool,features)
    if r['scorer'] not in ('LEXICAL','DENSE','SPECTRAL','RRF'):raise ContractError('BASELINE_TASK')
    nodes={n['uid']:n for n in g['nodes']}
    qtexts=[n['text'] for n in g['nodes'] if n['node_type']=='ISSUE' and n['case_id']==g['query_case_id']]
    query='\n'.join(qtexts)
    channel={'LEXICAL':'lexical','DENSE':'dense','SPECTRAL':'spectral','RRF':'rrf'}[r['scorer']]
    scores={c['uid']:c['discovery_scores'][channel] for c in p['candidates']}
    if any(v is None for v in scores.values()):raise ContractError('BASELINE_CHANNEL_UNAVAILABLE',detail=channel)
    if r['scorer']=='DENSE' and p['retrieval_config']['dense_feature_sha256']!=features['sha256']:
        raise ContractError('STALE_DENSE_POOL')
    out=result(req,graph,pool,scores,{'method':r['scorer'],'candidate_count':len(scores),
        'stored_sources':g['visibility_manifest']['retained_sources'],
        'consumed_fields':['query_issue_text','candidate_route_text','discovery_scores'],
        'ranking_weights_loaded':False,'pretrained_encoder_used':features['config']['method']=='PINNED_E5_ALL_TOKEN_WINDOWS'})
    validate_result(out,req,graph,pool);return out
