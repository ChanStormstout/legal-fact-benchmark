"""Bounded graph-ranker interfaces. No labels in graph; no implicit negatives.

Real-data training is gated separately. Synthetic tests are engineering evidence only.
"""
import hashlib
import math
import re
from collections import defaultdict

RELATIONS = ('has_assertion', 'has_object', 'has_condition', 'role', 'statement_status',
             'stage', 'member_of', 'part_of', 'depends_on', 'candidate_alignment')
FORBIDDEN = {'gold', 'reference', 'correct_authority', 'outcome', 'answer', 'label'}

def validate_graph(graph):
    ids = [n['id'] for n in graph['nodes']]
    if len(ids) != len(set(ids)):
        raise ValueError('DUPLICATE_NODE')
    nodes = {n['id']: n for n in graph['nodes']}
    for edge in graph['edges']:
        if edge['relation'] not in RELATIONS or edge['relation'] in FORBIDDEN:
            raise ValueError('FORBIDDEN_OR_UNKNOWN_RELATION')
        if edge['source'] not in nodes or edge['target'] not in nodes:
            raise ValueError('DANGLING_NODE')
        if not edge.get('evidence'):
            raise ValueError('MISSING_PROVENANCE')
        if edge.get('certainty') not in ('SOURCE_PROPOSED', 'DECLARED_DEPENDENCY', 'CANDIDATE_ONLY'):
            raise ValueError('UNKNOWN_IS_NOT_A_POSITIVE_EDGE')
    return graph

def build_graph(case_id, view, relations, units, allowed_segments):
    """Import only recorded assertions/roles; lexical existence is not truth validation.

    Caller must supply answer-isolated allowed_segments for experiments. Old full-source
    demonstrations remain DEMONSTRATION_ONLY regardless of syntactic validation.
    """
    nodes=[]; edges=[]; excluded=[]; pending=[]; prefix='case:'+str(case_id)+':'
    def node(key,kind,text,**metadata):
        if not any(n['id']==key for n in nodes): nodes.append(dict(id=key,kind=kind,text=text,**metadata))
    def evidence(items):
        return [dict(segment_id=e['segment_id'],quote=e['quote']) for e in items
                if e.get('segment_id') in allowed_segments and e.get('quote')
                and e['quote'] in allowed_segments[e['segment_id']]]
    def edge(a,r,b,refs,certainty='SOURCE_PROPOSED',**metadata):
        edges.append(dict(source=a,relation=r,target=b,evidence=refs,certainty=certainty,**metadata))
    case=prefix+'query';node(case,'case','case query')
    object_ids=set()
    for obj in view.get('objects',[]):
        refs=evidence(obj.get('evidence',[]))
        if not refs: excluded.append(dict(id=obj['id'],reason='OBJECT_EVIDENCE_NOT_IN_ALLOWED_SOURCE'));continue
        oid=prefix+obj['id'];object_ids.add(obj['id']);node(oid,'object',obj.get('label',''),object_kind=obj.get('kind'),identity_resolved=obj.get('identity_resolved',False))
        edge(case,'has_object',oid,refs)
    for fact in view.get('events',[]):
        refs=evidence(fact.get('evidence',[]))
        if not refs or fact.get('known_error'):
            excluded.append(dict(id=fact['id'],reason='KNOWN_ERROR_OR_NO_ALLOWED_EVIDENCE'));continue
        fid=prefix+fact['id'];node(fid,'assertion',fact.get('type','UNKNOWN'),polarity=fact.get('polarity','UNKNOWN'),unresolved=fact.get('unresolved',[]),origin=fact.get('origin',{}))
        edge(case,'has_assertion',fid,refs)
        for role,oid in fact.get('roles',{}).items():
            er=evidence(fact.get('role_evidence',{}).get(role,[]))
            if oid in object_ids and er:edge(fid,'role',prefix+oid,er,role=role)
            else:pending.append(dict(assertion=fact['id'],field='role:'+role,reason='MISSING_OR_UNLOCATED_ROLE_EVIDENCE'))
        state=fact.get('status','UNKNOWN');sid=prefix+'status:'+state;node(sid,'status',state);edge(fid,'statement_status',sid,refs,semantic_status='MODEL_PROPOSED_NOT_VERIFIED')
        stage=fact.get('origin',{}).get('stage')
        if stage:
            sid=prefix+'stage:'+hashlib.sha256(stage.encode()).hexdigest()[:12];node(sid,'stage',stage);edge(fid,'stage',sid,refs,semantic_status='MODEL_PROPOSED_NOT_VERIFIED')
    for item in relations.get('edges',[]):
        refs=evidence(item.get('computational_evidence',item.get('evidence',[])))
        if item.get('decision')=='SUPPORTED' and item['left'] in object_ids and item['right'] in object_ids and refs:
            edge(prefix+item['left'],item['op'],prefix+item['right'],refs,stage_scope=item.get('stage_scope'),semantic_status='MODEL_SOURCE_REVIEW_NOT_HUMAN_GOLD')
        else:pending.append(dict(relation=item,reason='UNKNOWN_OR_UNLOCATED_OR_MISSING_ENDPOINT'))
    for unit in units:node(unit['id'],'authority',unit['text'],scope=unit.get('scope',''),version=unit.get('version_status','UNKNOWN'))
    for unit in units:
        for dep in unit.get('dependencies',[]):
            edge(unit['id'],'depends_on',dep,[{'unit_id':unit['id'],'field':'dependencies','source':unit.get('source')}],certainty='DECLARED_DEPENDENCY')
    return validate_graph(dict(case_id=str(case_id),query_node=case,nodes=nodes,edges=edges,pending=pending,excluded=excluded,alignment_status='NOT_BUILT_NO_ANSWER_DERIVED_LINKS'))

def features(graph, width=16):
    """Stable signed token hashing of whitelisted content only; never hash node IDs.

    Simple fixed features, not pretrained embeddings or a statement of semantic adequacy.
    """
    out=[]
    for n in graph['nodes']:
        row=[0.0]*width
        text=' '.join(str(n.get(k,'')) for k in ('kind','text','polarity','scope','version','object_kind'))
        for token in re.findall(r'[a-z0-9]+',text.lower()):
            h=hashlib.sha256(token.encode()).digest();row[int.from_bytes(h[:2],'big')%width]+=1 if h[2]%2 else -1
        norm=math.sqrt(sum(v*v for v in row)) or 1;out.append([v/norm for v in row])
    return out

def adjacency(graph):
    """A[target, source], normalized per target and relation. Reverse types distinct."""
    validate_graph(graph);index={n['id']:i for i,n in enumerate(graph['nodes'])};n=len(index);out={}
    for e in graph['edges']:
        # role name is an edge type, not proof of object identity.
        rel=e['relation']+(':'+e['role'] if e['relation']=='role' else '')
        for a,b,r in [(e['source'],e['target'],rel),(e['target'],e['source'],rel+':inverse')]:
            out.setdefault(r,[[0.0]*n for _ in range(n)])[index[b]][index[a]]=1.0
    for matrix in out.values():
        for row in matrix:
            total=sum(row)
            if total:
                for i in range(n):row[i]/=total
    return out

def simple_rank(graph, bm25):
    """Transparent B: distinct source-anchored candidate conditions, BM25 tie break.

    Conditions and alignments must be supplied by the frozen upstream method for BOTH
    B and C. This function never constructs semantic links or uses reference labels.
    """
    validate_graph(graph)
    aligns={e['target'] for e in graph['edges'] if e['relation']=='candidate_alignment'}
    supports=defaultdict(set)
    for e in graph['edges']:
        if e['relation']=='has_condition' and e['target'] in aligns:supports[e['source']].add(e['target'])
    if not aligns:raise ValueError('NOT_READY_NO_CONDITION_ALIGNMENTS')
    rows=[dict(x,relation_score=len(supports[x['id']]),baseline_rank=i) for i,x in enumerate(bm25,1)]
    return sorted(rows,key=lambda x:(-x['relation_score'],x['baseline_rank']))

def training_gate(train_ids, check_ids, graphs, preferences, group_ids):
    errors=[]
    if not train_ids:errors.append('NO_TRAINING_CASES')
    if not check_ids:errors.append('NO_SEPARATE_CHECK_CASES')
    if set(train_ids)&set(check_ids):errors.append('CASE_LEAKAGE')
    tg={group_ids.get(c) for c in train_ids};cg={group_ids.get(c) for c in check_ids}
    if None in tg|cg:errors.append('GROUP_STATUS_UNDECLARED')
    if (tg&cg)-{None}:errors.append('DISPUTE_GROUP_LEAKAGE')
    usable=[p for p in preferences if p.get('case_id') in train_ids and p.get('status')=='EXPLICIT_REVIEWED_PREFERENCE' and p.get('preferred')!=p.get('other') and p.get('evidence')]
    if not usable:errors.append('NO_EXPLICIT_TRAINING_PREFERENCES_UNKNOWN_NOT_NEGATIVE')
    for cid in train_ids+check_ids:
        g=graphs.get(cid)
        if not g or g.get('input_scope')!='ANSWER_ISOLATED':errors.append('NO_ANSWER_ISOLATED_GRAPH:'+cid)
        elif not any(e['relation']=='candidate_alignment' for e in g['edges']):errors.append('NO_FACT_CONDITION_ALIGNMENT:'+cid)
    return dict(ready=not errors,reasons=errors,usable_preferences=len(usable))
