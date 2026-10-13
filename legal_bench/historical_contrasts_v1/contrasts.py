"""Source-bound reviewed contrasts. Retrieval cannot create a factual distinction."""
from .contracts import ContractError, TASK, seal, validate
from .ranking import validate_result


def form(rank,req,graph,pool,reviews=()):
    ranked=validate_result(rank,req,graph,pool);p=pool['body'];g=graph['body']
    selected=set(ranked['selected_ids']);candidates={c['uid']:c for c in p['candidates']}
    nodes={n['uid']:n for n in g['nodes']};out=[];pending=[];used=set()
    def refs(values,candidate):
        if not values:raise ContractError('UNSOURCED_REVIEW')
        for uid in values:
            n=nodes.get(uid)
            if n is None or n['node_type']!='SOURCE' or n['case_id']!=candidate['case_id'] or not n['text'].strip():
                raise ContractError('WRONG_CASE_REVIEW_SOURCE',detail=uid)
    for value in reviews:
        r=validate(value,'ContrastReview')
        if r['graph_sha256']!=graph['sha256'] or r['pool_sha256']!=pool['sha256']:
            raise ContractError('STALE_CONTRAST_REVIEW')
        if {r['left'],r['right']}-selected:
            raise ContractError('REVIEW_NOT_SELECTED')
        a,b=candidates[r['left']],candidates[r['right']]
        if a['group_id']==b['group_id']:
            raise ContractError('SAME_DISPUTE_CONTRAST')
        for c in (a,b):
            for field,actual in c['scope'].items():
                canonical=isinstance(actual,str) and (actual.startswith('urn:') or field=='stage' and actual in {'pleading','trial','appeal','enforcement'})
                if canonical and actual!=r['checked_scope'][field]:
                    raise ContractError('REVIEW_SCOPE_CONFLICT',detail=field)
        refs(r['scope_left_refs'],a);refs(r['scope_right_refs'],b)
        refs(r['left_outcome_refs'],a);refs(r['right_outcome_refs'],b)
        for d in r['distinctions']:
            refs(d['left_refs'],a);refs(d['right_refs'],b)
        pair=tuple(sorted((a['uid'],b['uid'])))
        if pair in used:raise ContractError('DUPLICATE_CONTRAST')
        used.add(pair)
        out.append({'left':a['uid'],'right':b['uid'],'route_family':r['route_family'],
            'left_outcome':r['left_outcome'],'right_outcome':r['right_outcome'],
            'distinctions':r['distinctions'],'scope_receipt_sha256':value['sha256']})
    covered={uid for pair in used for uid in pair}
    for uid in sorted(selected-covered):
        pending.append({'candidate_id':uid,'scope_status':candidates[uid]['scope_status'],
            'reason':'NO_SOURCE_BOUND_ROUTE_OUTCOME_AND_DISTINCTION_REVIEW'})
    return seal('ContrastBundle',{'task_id':TASK,'rank_sha256':rank['sha256'],
        'pool_sha256':pool['sha256'],'contrasts':out,'pending':pending,
        'semantic_approval':False,'legal_approval':False})


def training_pairs(graph,pool,labels,exposed_groups=()):
    g=validate(graph,'GraphRelease');p=validate(pool,'CandidatePool')
    if p['graph_sha256']!=graph['sha256']:raise ContractError('STALE_LABEL_GRAPH')
    candidates={c['uid']:c for c in p['candidates']};nodes={n['uid']:n for n in g['nodes']}
    accepted={};ignored=[]
    for value in labels:
        r=validate(value,'RelevanceLabel')
        if r['pool_sha256']!=pool['sha256'] or r['candidate_id'] not in candidates:
            raise ContractError('STALE_RELEVANCE_LABEL')
        c=candidates[r['candidate_id']]
        if r['candidate_group_id']!=c['group_id'] or r['query_group_id']!=p['query_group_id']:
            raise ContractError('LABEL_GROUP_MISMATCH')
        if r['split']=='TRAIN' and {r['query_group_id'],r['candidate_group_id']}&set(exposed_groups):
            raise ContractError('EXPOSED_GROUP_IN_TRAIN')
        if r['split']=='TRAIN' and (g['visibility_policy']!='SOURCE_VIEW_APPROVED_FOR_TASK'
                or not g['visibility_manifest'].get('textual_outcome_blinding_reviewed')):
            raise ContractError('TRAIN_SOURCE_VISIBILITY_NOT_REVIEWED')
        for key,case in [('candidate_refs',c['case_id']),('query_refs',p['query_case_id'])]:
            for uid in r[key]:
                n=nodes.get(uid)
                if n is None or n['node_type']!='SOURCE' or n['case_id']!=case or not n['text'].strip():
                    raise ContractError('LABEL_SOURCE_MISMATCH')
        if r['utility'] in ('UNKNOWN','DISPUTED'):
            ignored.append({'label':value['sha256'],'reason':r['utility']});continue
        if r['candidate_id'] in accepted:raise ContractError('DUPLICATE_RELEVANCE_LABEL')
        accepted[r['candidate_id']]=(r,value['sha256'])
    pairs=[]
    for split in ('TRAIN','DEV'):
        pos=[(uid,h) for uid,(r,h) in accepted.items() if r['split']==split and r['utility']=='POSITIVE']
        neg=[(uid,h) for uid,(r,h) in accepted.items() if r['split']==split and r['utility']=='NEGATIVE']
        for a,ha in sorted(pos):
            for b,hb in sorted(neg):
                pairs.append({'task_id':TASK,'pool_sha256':pool['sha256'],'split':split,
                              'positive':a,'negative':b,'label_hashes':[ha,hb]})
    return {'pairs':pairs,'ignored':ignored,'training_ready':any(x['split']=='TRAIN' for x in pairs),
            'reference_type':'SOURCE_REVIEWED_REFERENCE_NOT_HUMAN_GOLD','training_calls':0}
