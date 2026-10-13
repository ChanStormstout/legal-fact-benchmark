"""Typed proposal graph, explicit visibility and deterministic bounded sampling."""
import hashlib
import math
import re
from collections import defaultdict
from .contracts import ContractError, TASK, digest, seal, validate

NODE_TYPES=['CASE','ISSUE','ROUTE','SOURCE','EVIDENCE','ENTITY','USE','JUDGMENT','BINDING','LINK']


def check_origins(value,references,query):
    """Check source/proposal joins against packet values, not array positions."""
    g=validate(value,'GraphRelease');q=validate(query,'CasePacket');expected={};packets=[]
    if g['query_packet_hash']!=query['sha256'] or g['query_case_id']!=q['case_id'] or g['query_group_id']!=q['group_id']:
        raise ContractError('GRAPH_QUERY_ORIGIN')
    for p in references:
        b=validate(p,'CasePacket')
        if b['case_id']!=q['case_id'] and b['group_id']!=q['group_id']:packets.append(p)
    packets.append(query)
    if sorted(p['sha256'] for p in packets)!=g['packet_hashes']:
        raise ContractError('GRAPH_PACKET_ORIGINS')
    def expect(uid,kind,b,text,refs=()):
        row={'uid':uid,'node_type':kind,'case_id':b['case_id'],'group_id':b['group_id'],'text':text,'source_ids':list(refs)}
        if uid in expected and expected[uid]!=row:raise ContractError('GRAPH_ORIGIN_COLLISION')
        expected[uid]=row
    wanted_edges=set()
    def relation(a,name,b):
        wanted_edges.add((a,name,b));wanted_edges.add((b,name+'_REV',a))
    for p in packets:
        b=p['body'];expect('CASE:'+digest([b['dataset'],b['case_id'],b['material_snapshot_id']]),'CASE',b,'Case context')
        case='CASE:'+digest([b['dataset'],b['case_id'],b['material_snapshot_id']])
        issue='ISSUE:'+digest([b['dataset'],b['case_id'],b['material_snapshot_id'],b['query_id']])
        expect(issue,'ISSUE',b,b['query_text']);relation(case,'HAS_ISSUE',issue)
        for s in b['sources']:
            expect(s['uid'],'SOURCE',b,s['text']);relation(s['uid'],'CASE_MATERIAL',case)
        for r in b['records']:
            expect(r['uid'],r['kind'],b,r['text'],r['source_ids']);relation(r['uid'],'CASE_PROPOSAL',case)
            for s in r['source_ids']:relation(s,'ATTRIBUTED_SOURCE',r['uid'])
            name={'SUPPORT':'PROPOSED_SUPPORT','OPPOSE':'PROPOSED_OPPOSE','CONTEXT':'PROPOSED_CONTEXT'}.get(r['direction'],'DEPENDS_ON')
            for dep in r['dependency_ids']:relation(dep,name,r['uid'])
        for r in b['routes']:
            expect(r['uid'],'ROUTE',b,r['text'],r['source_ids'])
            relation(issue,'HAS_ROUTE',r['uid'])
            for s in r['source_ids']:relation(s,'RULE_SOURCE',r['uid'])
            for record in r['record_ids']:relation(record,'ROUTE_MEMBER',r['uid'])
    actual={n['uid']:n for n in g['nodes']}
    if expected!=actual:raise ContractError('GRAPH_NODE_ORIGIN_MISMATCH')
    if wanted_edges!={(e['src'],e['relation'],e['dst']) for e in g['edges']}:
        raise ContractError('GRAPH_EDGE_ORIGIN_MISMATCH')
    return True


def build(reference_packets, query_packet):
    q=validate(query_packet,'CasePacket'); packets=[]; excluded=[]; seen=set();materials={}
    for p in reference_packets:
        b=validate(p,'CasePacket')
        if b['group_id']==q['group_id'] or b['case_id']==q['case_id']:
            excluded.append({'packet':p['sha256'],'reason':'QUERY_DISPUTE_GROUP'})
            continue
        key=(b['case_id'],b['part_id'])
        if key in seen:
            raise ContractError('MULTIPLE_REFERENCE_SNAPSHOTS',detail=str(key))
        if b['case_id'] in materials and materials[b['case_id']]!=b['material_snapshot_id']:
            raise ContractError('MIXED_CASE_MATERIAL_SNAPSHOTS',detail=b['case_id'])
        materials[b['case_id']]=b['material_snapshot_id']
        seen.add(key);packets.append(p)
    packets.append(query_packet)
    nodes=[];edges=[]
    def add(uid,kind,b,text,source_ids=()):
        nodes.append({'uid':uid,'node_type':kind,'case_id':b['case_id'],
                      'group_id':b['group_id'],'text':text,'source_ids':list(source_ids)})
    def edge(src,rel,dst):
        edges.append({'src':src,'relation':rel,'dst':dst})
        edges.append({'src':dst,'relation':rel+'_REV','dst':src})
    for p in packets:
        b=p['body']; case_uid='CASE:'+digest([b['dataset'],b['case_id'],b['material_snapshot_id']])
        add(case_uid,'CASE',b,'Case context')  # Identifiers never become numeric features.
        for s in b['sources']:
            add(s['uid'],'SOURCE',b,s['text']);edge(s['uid'],'CASE_MATERIAL',case_uid)
        for r in b['records']:
            add(r['uid'],r['kind'],b,r['text'],r['source_ids'])
            edge(r['uid'],'CASE_PROPOSAL',case_uid)
            for s in r['source_ids']:edge(s,'ATTRIBUTED_SOURCE',r['uid'])
            for dep in r['dependency_ids']:
                relation={'SUPPORT':'PROPOSED_SUPPORT','OPPOSE':'PROPOSED_OPPOSE','CONTEXT':'PROPOSED_CONTEXT'}.get(r['direction'],'DEPENDS_ON')
                edge(dep,relation,r['uid'])
        issue='ISSUE:'+digest([b['dataset'],b['case_id'],b['material_snapshot_id'],b['query_id']])
        add(issue,'ISSUE',b,b['query_text']);edge(case_uid,'HAS_ISSUE',issue)
        for r in b['routes']:
            add(r['uid'],'ROUTE',b,r['text'],r['source_ids'])
            edge(r['issue_id'],'HAS_ROUTE',r['uid'])
            for s in r['source_ids']:edge(s,'RULE_SOURCE',r['uid'])
            for record in r['record_ids']:edge(record,'ROUTE_MEMBER',r['uid'])
    lookup={}
    for n in nodes:
        if n['uid'] in lookup and lookup[n['uid']]!=n:raise ContractError('SHARED_NODE_CONTENT_CONFLICT')
        lookup[n['uid']]=n
    nodes=sorted(lookup.values(),key=lambda n:n['uid'])
    edges=sorted({digest(e):e for e in edges}.values(),key=lambda e:(e['src'],e['relation'],e['dst']))
    relations=sorted({'|'.join((lookup[e['src']]['node_type'],e['relation'],lookup[e['dst']]['node_type'])) for e in edges})
    body={'task_id':TASK,'packet_hashes':sorted(p['sha256'] for p in packets),
        'query_packet_hash':query_packet['sha256'],'query_case_id':q['case_id'],'query_group_id':q['group_id'],
        'nodes':nodes,'edges':edges,'node_types':NODE_TYPES,'relation_types':relations,
        'node_map':{t:sorted(n['uid'] for n in nodes if n['node_type']==t) for t in NODE_TYPES},
        'visibility_policy':'EXPOSED_DEVELOPMENT_SOURCE_VIEW_NOT_BLIND',
        'visibility_manifest':{'excluded_packets':excluded,
            'feature_fields':['node_type','text'],
            'never_features':['uid','case_id','group_id','original','review_label','review_reason',
                              'judgment_status','outcome_sidecar','training_labels'],
            'target_and_reverse_supervision_edges_present':False,
            'textual_outcome_blinding_reviewed':False,
            'retained_sources':sum(n['node_type']=='SOURCE' for n in nodes),
            'quarantined_legacy_packets':[p['sha256'] for p in packets if p['body']['errors']]},
        'outcome_sidecar':{}}
    result=seal('GraphRelease',body)
    check_origins(result,reference_packets,query_packet)
    return result


def tokens(text):
    return re.findall(r'\w+',text.casefold(),flags=re.UNICODE)


def hashed_features(graph, dimension=64, window_tokens=512):
    """All token windows are consumed. Explicitly a smoke feature, not E5."""
    b=validate(graph,'GraphRelease')
    if type(dimension) is not int or dimension<2 or window_tokens<1:
        raise ContractError('FEATURE_CONFIGURATION')
    vectors={};ledger=[]
    for n in b['nodes']:
        words=tokens(n['text']); v=[0.0]*dimension
        for word in words:
            h=hashlib.sha256(word.encode()).digest()
            v[int.from_bytes(h[:4],'big')%dimension]+=1 if h[4]%2 else -1
        length=math.sqrt(sum(x*x for x in v))
        if length:v=[x/length for x in v]
        vectors[n['uid']]=v
        windows=[[i,min(i+window_tokens,len(words))] for i in range(0,len(words),window_tokens)]
        ledger.append({'uid':n['uid'],'text_sha256':digest(n['text']),
                       'token_count':len(words),'windows':windows,'encoded_tokens':len(words)})
    config={'method':'SMOKE_HASHED_TEXT_ALL_WINDOWS','revision':'sha256-word-v1',
            'dimension':dimension,'window_tokens':window_tokens,'task_id':TASK,
            'normalization':'L2','prefix':'','effectiveness_evaluated':False}
    value={'graph_sha256':graph['sha256'],'config':config,'vectors':vectors,'coverage':ledger}
    value['sha256']=digest(value);check_features(graph,value)
    return value


def check_features(graph, features):
    b=validate(graph,'GraphRelease')
    if set(features)!={'sha256','graph_sha256','config','vectors','coverage'}:
        raise ContractError('FEATURE_FIELDS')
    if features['sha256']!=digest({k:v for k,v in features.items() if k!='sha256'}):
        raise ContractError('FEATURE_HASH')
    if features['graph_sha256']!=graph['sha256']:
        raise ContractError('STALE_FEATURES')
    ids={n['uid'] for n in b['nodes']}
    if set(features['vectors'])!=ids:
        raise ContractError('FEATURE_NODE_SET')
    config=features['config'];dim=config['dimension']
    if type(dim) is not int or dim<2 or config['task_id']!=TASK:
        raise ContractError('FEATURE_CONFIGURATION')
    for uid,vector in features['vectors'].items():
        if len(vector)!=dim or any(type(x) not in (float,int) or not math.isfinite(x) for x in vector):
            raise ContractError('FEATURE_DIMENSION_OR_VALUE',detail=uid)
    ledger={r['uid']:r for r in features['coverage']}
    if len(ledger)!=len(features['coverage']) or set(ledger)!=ids:
        raise ContractError('FEATURE_COVERAGE_IDS')
    for n in b['nodes']:
        row=ledger[n['uid']]
        if config['method']=='SMOKE_HASHED_TEXT_ALL_WINDOWS':
            total=len(tokens(n['text']));cap=config['window_tokens']
        elif config['method']=='PINNED_E5_ALL_TOKEN_WINDOWS':
            ids=row['token_ids'];offsets=row['offsets'];total=len(ids);cap=row['window_capacity']
            if (len(offsets)!=total or any(type(i) is not int or i<0 for i in ids)
                    or cap!=config['max_length']-row['prefix_token_count']-row['special_token_count']
                    or any(len(pair)!=2 or any(type(i) is not int for i in pair)
                           or not 0<=pair[0]<=pair[1]<=len(n['text']) for pair in offsets)):
                raise ContractError('TOKENIZATION_RECEIPT',detail=n['uid'])
            if row['token_ids_sha256']!=digest(ids):raise ContractError('TOKEN_IDS_HASH')
        else:raise ContractError('FEATURE_METHOD')
        if type(cap) is not int or cap<1:raise ContractError('TOKEN_CAPACITY')
        expected=[[i,min(i+cap,total)] for i in range(0,total,cap)]
        if row['text_sha256']!=digest(n['text']) or row['token_count']!=total or row['encoded_tokens']!=total or row['windows']!=expected:
            raise ContractError('FEATURE_COVERAGE_GAP',detail=n['uid'])


def sample(graph, seed_ids, fanouts=(15,10), seed=0):
    b=validate(graph,'GraphRelease'); nodes={n['uid']:n for n in b['nodes']}
    if set(seed_ids)-set(nodes) or len(fanouts)!=2 or any(type(f) is not int or f<0 for f in fanouts):
        raise ContractError('SAMPLER_INPUT')
    incoming=defaultdict(list)
    for e in b['edges']:
        key='|'.join((nodes[e['src']]['node_type'],e['relation'],nodes[e['dst']]['node_type']))
        incoming[(e['dst'],key)].append(e)
    visited=set(seed_ids); frontier=set(seed_ids); used={}; counts=[]
    for hop,budget in enumerate(fanouts):
        next_frontier=set()
        for dst in sorted(frontier):
            for rel in b['relation_types']:
                candidates=incoming.get((dst,rel),[])
                candidates=sorted(candidates,key=lambda e:(digest([seed,hop,dst,rel,e['src']]),e['src']))
                selected=candidates[:budget]
                counts.append({'hop':hop,'destination':dst,'relation':rel,'available':len(candidates),'sampled':len(selected)})
                for e in selected:used[digest(e)]=e;next_frontier.add(e['src'])
        visited.update(next_frontier);frontier=next_frontier
    # Only sampled edges enter computation, not an induced graph with extra edges.
    return {'graph_sha256':graph['sha256'],'node_ids':sorted(visited),
        'edges':sorted(used.values(),key=lambda e:(e['src'],e['relation'],e['dst'])),
        'fanouts':list(fanouts),'seed':seed,'counts':counts,
        'stored_node_count':len(nodes),'sampled_node_count':len(visited),
        'sampled_source_ids':sorted(i for i in visited if nodes[i]['node_type']=='SOURCE')}
