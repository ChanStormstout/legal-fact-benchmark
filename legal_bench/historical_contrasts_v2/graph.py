"""Outcome-blind source/case/issue/route graph with explicit original-text lineage."""
from legal_bench.historical_contrasts_v1.contracts import TASK, digest, seal, validate, ContractError
from legal_bench.historical_contrasts_v1.graph import sample
from legal_bench.historical_contrasts_v1.model import to_data

TYPES=['CASE','ISSUE','ROUTE','SOURCE']
GROUND='Delhi Rent Control Act section 14(1)(b): subletting, assignment or parting with possession without written consent. Assess this ground only, preserving unresolved claims and lower-court attribution.'

def text(view):return GROUND+'\n'+'\n'.join(s['text'] for s in view['segments'])
def uid(view,kind,local=''):
    # Source identities stay outside numeric and textual model features.
    return kind+':'+digest(['HISTORICAL_CONTRASTS_V2',view['case_id'],view['model_text_sha256'],local])

def build(refs,query):
    if any(r['group_id']==query['group_id'] for r in refs):raise ContractError('QUERY_REFERENCE_GROUP')
    nodes=[];edges=[]
    def add(v,kind,local,words):
        key=uid(v,kind,local);nodes.append({'uid':key,'node_type':kind,'case_id':v['case_id'],
            'group_id':v['group_id'],'text':words,'source_ids':[]});return key
    def edge(a,name,b):
        edges.extend([{'src':a,'relation':name,'dst':b},{'src':b,'relation':name+'_REV','dst':a}])
    for v in refs+[query]:
        case=add(v,'CASE','','Retrospective case context')
        issue=add(v,'ISSUE','',text(v));route=add(v,'ROUTE','',text(v))
        edge(case,'HAS_ISSUE',issue);edge(case,'HAS_ROUTE',route)
        for s in v['segments']:
            source=add(v,'SOURCE',s['id'],s['text'])
            edge(source,'CASE_MATERIAL',case)
            # This is source availability, not a claimed legal support/entailment.
            edge(source,'ATTRIBUTED_SOURCE',issue);edge(source,'ATTRIBUTED_SOURCE',route)
    nodes.sort(key=lambda n:n['uid']);edges.sort(key=lambda e:(e['src'],e['relation'],e['dst']))
    by_id={n['uid']:n for n in nodes}
    body={'task_id':TASK,'packet_hashes':sorted(v['sha256'] for v in refs+[query]),
        'query_packet_hash':query['sha256'],'query_case_id':query['case_id'],'query_group_id':query['group_id'],
        'nodes':nodes,'edges':edges,'node_types':TYPES,
        'relation_types':sorted({'|'.join([by_id[e['src']]['node_type'],e['relation'],by_id[e['dst']]['node_type']]) for e in edges}),
        'node_map':{t:sorted(n['uid'] for n in nodes if n['node_type']==t) for t in TYPES},
        'visibility_policy':'SOURCE_VIEW_APPROVED_FOR_TASK',
        'visibility_manifest':{'source_view_review_hashes':{v['case_id']:v['source_view_review_hash'] for v in refs+[query]},
            'textual_outcome_blinding_reviewed':True,'review_type':'GPT6_HIGH_SOURCE_REVIEWED_NOT_HUMAN_GOLD',
            'feature_fields':['node_type','original_allowed_text'],
            'never_features':['uid','case_id','group_id','split','labels','review_reasons','route_outcome','route_description'],
            'target_and_reverse_supervision_edges_present':False,
            'no_other_query_case_in_graph':True,'retained_sources':sum(len(v['segments']) for v in refs+[query]),
            'masked_source_ids':{v['case_id']:v['excluded_ids'] for v in refs+[query]},
            'graph_structure_scope':'Source availability and grouping only; no learned or unreviewed entity bindings'},
        'outcome_sidecar':{}}
    return seal('GraphRelease',body)

def check_view(graph,refs,query):
    validate(graph,'GraphRelease')
    if build(refs,query)!=graph:raise ContractError('GRAPH_SOURCE_VIEW_MISMATCH')
    return True

def tensors(graph,features,refs,query,seed=0):
    check_view(graph,refs,query)
    seeds=[uid(query,'ISSUE')]+[uid(r,'ROUTE') for r in refs]
    sampled=sample(graph,seeds,[15,10],seed)
    data,mapping=to_data(graph,features,sampled)
    qi=mapping['ISSUE'].index(uid(query,'ISSUE'));ci=[mapping['ROUTE'].index(uid(r,'ROUTE')) for r in refs]
    return data,qi,ci,sampled,mapping
