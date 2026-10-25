"""Single schema registry plus independent cross-record checks; stdlib only."""
import copy
import hashlib
import json
import math

VERSION = 'historical-contrasts/1.0'
TASK = 'BLOCKER_TO_HISTORICAL_ROUTE_V1'


class ContractError(ValueError):
    def __init__(self, code, path='$', detail=''):
        self.code, self.path, self.detail = code, path, detail
        super().__init__(f'{code} at {path}: {detail}')


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read_json(path):
    def pairs(rows):
        out = {}
        for k, v in rows:
            if k in out:
                raise ContractError('DUPLICATE_JSON_KEY', detail=k)
            out[k] = v
        return out
    def invalid(value):
        raise ContractError('NONFINITE_JSON', detail=value)
    with open(path, encoding='utf-8') as stream:
        return json.load(stream, object_pairs_hook=pairs, parse_constant=invalid)


def obj(**props):
    return {'type': 'object', 'properties': props, 'required': list(props),
            'additionalProperties': False}


def arr(item):
    return {'type': 'array', 'items': item}


def enum(*values):
    return {'enum': list(values)}


S = {'type': 'string', 'minLength': 1}
TEXT = {'type': 'string'}
B = {'type': 'boolean'}
I = {'type': 'integer', 'minimum': 0}
F = {'type': 'number'}
NULL_S = {'anyOf': [S, {'type': 'null'}]}
NULL_F = {'anyOf': [F, {'type': 'null'}]}
JSON_VALUE = {}  # Opaque legacy/provenance is retained, never a feature whitelist.
SCOPE = obj(jurisdiction=NULL_S, stage=NULL_S, legal_period=NULL_S,
            claim_type=NULL_S, route_family=NULL_S)
SOURCE = obj(uid=S, local_id=S, original_id=S, document_id=S, text=TEXT,
             text_sha256=S, view_sha256=S, start=I, end=I, original=JSON_VALUE)
RECORD = obj(uid=S, local_id=S, premise_id=S,
             kind=enum('EVIDENCE', 'ENTITY', 'USE', 'JUDGMENT', 'BINDING', 'LINK'),
             text=TEXT, source_ids=arr(S), dependency_ids=arr(S),
             direction=enum('SUPPORT', 'OPPOSE', 'CONTEXT', 'NONE'),
             computational_eligible=B, original=JSON_VALUE)
ROUTE = obj(uid=S, rule_id=S, issue_id=S, text=TEXT, scope=SCOPE,
            source_ids=arr(S), record_ids=arr(S))
NODE = obj(uid=S, node_type=S, case_id=S, group_id=S, text=TEXT,
           source_ids=arr(S))
EDGE = obj(src=S, relation=S, dst=S)
CANDIDATE = obj(uid=S, case_id=S, group_id=S, route_id=S, scope=SCOPE,
                source_ids=arr(S), scope_status=enum('COMPATIBLE', 'INCOMPATIBLE', 'PENDING'),
                scope_checks=JSON_VALUE, discovery=arr(S),
                discovery_scores=obj(lexical=F,dense=NULL_F,spectral=NULL_F,rrf=F),signature=JSON_VALUE)
SCORE = obj(uid=S, score=F, rank=I)
DISTINCTION = obj(text=S, left_refs=arr(S), right_refs=arr(S),
                  review=enum('MODEL_SOURCE_REVIEWED', 'STUDENT_CHECKED', 'LAWYER_APPROVED'),
                  status=enum('SUPPORTED'))
CONTRAST = obj(left=S, right=S, route_family=S, left_outcome=S, right_outcome=S,
               distinctions=arr(DISTINCTION), scope_receipt_sha256=S)

SCHEMAS = {
    'CasePacket': obj(dataset=S, case_id=S, group_id=S, snapshot_id=S, material_snapshot_id=S, part_id=S, query_id=S,
        technical_status=S, contract_status=S, semantic_approval=enum(False),
        legal_approval=enum(False), sources=arr(SOURCE), records=arr(RECORD),
        routes=arr(ROUTE), query_text=S, legacy=JSON_VALUE, errors=arr(JSON_VALUE),
        binding_review_sha256=NULL_S),
    'GraphRelease': obj(task_id=enum(TASK), packet_hashes=arr(S), query_packet_hash=S,
        query_case_id=S, query_group_id=S, nodes=arr(NODE), edges=arr(EDGE),
        node_types=arr(S), relation_types=arr(S), node_map=JSON_VALUE,
        visibility_policy=S, visibility_manifest=JSON_VALUE, outcome_sidecar=JSON_VALUE),
    'CandidatePool': obj(task_id=enum(TASK), graph_sha256=S, query_case_id=S,
        query_group_id=S, query_scope=SCOPE, candidates=arr(CANDIDATE),
        exclusions=arr(JSON_VALUE), capacity=I,retrieval_config=JSON_VALUE,query_signature=JSON_VALUE),
    'RankRequest': obj(task_id=enum(TASK), run_id=S, query_id=S, graph_sha256=S,
        pool_sha256=S, feature_sha256=S, visibility_sha256=S,
        checkpoint_sha256=NULL_S, checkpoint_role=enum('NONE', 'RANDOM_SMOKE', 'TASK_TRAINED'),
        scorer=enum('LEXICAL','DENSE','SPECTRAL','RRF','SAGE_SMOKE','SAGE'), top_k=I,
        seed=I, fanouts=arr(I), serving_policy=enum('PRIVATE_REFERENCE_PLUS_ONE_QUERY')),
    'RankResult': obj(task_id=enum(TASK), request_sha256=S, graph_sha256=S,
        pool_sha256=S, runtime_status=enum('BASELINE_ONLY', 'UNTRAINED_SMOKE', 'OK', 'NO_CANDIDATES'),
        scores=arr(SCORE), selected_ids=arr(S), coverage=JSON_VALUE,
        semantic_approval=enum(False), legal_approval=enum(False)),
    'ContrastBundle': obj(task_id=enum(TASK), rank_sha256=S, pool_sha256=S,
        contrasts=arr(CONTRAST), pending=arr(JSON_VALUE),
        semantic_approval=enum(False), legal_approval=enum(False)),
    'ContrastReview': obj(task_id=enum(TASK), graph_sha256=S, pool_sha256=S,
        left=S, right=S, route_family=S, checked_scope=SCOPE,
        left_outcome=S, right_outcome=S, left_outcome_refs=arr(S), right_outcome_refs=arr(S),
        distinctions=arr(DISTINCTION), scope_left_refs=arr(S), scope_right_refs=arr(S),
        review=enum('MODEL_SOURCE_REVIEWED','STUDENT_CHECKED','LAWYER_APPROVED'),
        reviewer_id=S, review_version=S, label_origin=S),
    'RelevanceLabel': obj(task_id=enum(TASK), pool_sha256=S, candidate_id=S,
        query_group_id=S, candidate_group_id=S, split=enum('TRAIN','DEV'),
        utility=enum('POSITIVE','NEGATIVE','UNKNOWN','DISPUTED'),
        candidate_refs=arr(S), query_refs=arr(S), reason=S,
        review=enum('MODEL_SOURCE_REVIEWED','STUDENT_CHECKED','LAWYER_APPROVED'),
        label_origin=S),
}


def schema_check(value, spec, path='$'):
    if 'anyOf' in spec:
        for option in spec['anyOf']:
            try:
                schema_check(value, option, path)
                return
            except ContractError:
                pass
        raise ContractError('TYPE', path)
    if 'enum' in spec and not any(type(value) is type(v) and value == v for v in spec['enum']):
        raise ContractError('ENUM', path)
    types = {'object': dict, 'array': list, 'string': str, 'boolean': bool,
             'integer': int, 'null': type(None)}
    kind = spec.get('type')
    if kind == 'number':
        good = type(value) in (int, float) and math.isfinite(value)
    else:
        good = kind is None or type(value) is types[kind]
    if not good:
        raise ContractError('TYPE', path, str(kind))
    if isinstance(value, float) and not math.isfinite(value):
        raise ContractError('NONFINITE', path)
    if 'minimum' in spec and value < spec['minimum']:
        raise ContractError('MINIMUM', path)
    if 'minLength' in spec and len(value) < spec['minLength']:
        raise ContractError('EMPTY', path)
    if kind == 'object':
        keys = set(spec['properties'])
        if set(value) != keys:
            raise ContractError('FIELDS', path, f'missing={keys-set(value)} extra={set(value)-keys}')
        for k, v in value.items():
            schema_check(v, spec['properties'][k], path+'/'+k)
    elif kind == 'array':
        for i, v in enumerate(value):
            schema_check(v, spec['items'], path+'/'+str(i))
    elif not spec:
        # Validate even opaque JSON for finite, serializable values.
        try:
            canonical(value)
        except (TypeError, ValueError) as exc:
            raise ContractError('INVALID_JSON', path, str(exc)) from exc


def unique(values, path):
    if len(values) != len(set(values)):
        raise ContractError('DUPLICATE_ID', path)


def require_refs(refs, ids, path):
    unique(refs, path)
    missing = set(refs)-set(ids)
    if missing:
        raise ContractError('UNDECLARED_REFERENCE', path, repr(sorted(missing)))


def check_projection(body):
    """Reconcile canonical records with immutable original addresses, not counts alone."""
    old=body['legacy'];raw=old['payload'];case=old['case'];part=old['part']
    if (body['case_id']!=case['case_id'] or body['group_id']!=(case.get('dispute_id') or case['case_id'])
            or body['part_id']!=part['id'] or body['technical_status']!=old['technical_status']):
        raise ContractError('CASE_OR_PART_IDENTITY')
    if body['binding_review_sha256']!=(digest(old['reviews']) if old['reviews'] is not None else None):
        raise ContractError('BINDING_REVIEW_IDENTITY')
    expected_errors=[];expected_status='GENERATION_FAILED'
    if body['technical_status']=='OK' and raw is not None:
        from legal_bench.proof_carrying import evidence_binding_gate_v20_5_1 as old_gate
        from legal_bench.proof_carrying import shared_sources_v20_3 as old_shared
        try:
            checked=old_gate.audit(old_shared.pack(raw),old['original_schema'],case,old['rules'],old['reviews'])
            expected_status=checked['status'];expected_errors=checked['errors']
        except (ValueError,KeyError,TypeError,IndexError) as exc:
            expected_status='REJECTED_FORMAT';expected_errors=[{'kind':'LEGACY_FORMAT','detail':str(exc)}]
        if not expected_errors:
            expected_errors=[{'kind':'NOT_ANALYZED_WITH_ARTIFACTS','premise_id':pid}
                for pid,u in raw['analyses'].items() if u['analysis_status']=='NOT_ANALYZED'
                and any(u[k] for k in ('records','objects','uses','judgments'))]
            if expected_errors:expected_status='REJECTED_STATUS_CONSISTENCY'
    if body['contract_status']!=expected_status or body['errors']!=expected_errors:
        raise ContractError('GATE_PROJECTION_MISMATCH')
    sources={s['local_id']:s['uid'] for s in body['sources']}
    original_sources={s['original_id']:s['uid'] for s in body['sources']}
    addresses={r['local_id']:r['uid'] for r in body['records']}
    unique(list(addresses), '$/record_addresses')
    if len(addresses)!=len(body['records']):raise ContractError('DUPLICATE_RECORD_ADDRESS')
    if raw is not None and body['technical_status']=='OK' and not body['errors']:
        count=len(raw.get('object_links',[]))
        for unit in raw['analyses'].values():
            count+=sum(len(unit[k]) for k in ('records','objects','uses','judgments'))
            count+=sum(len(r['role_objects']) for k in ('uses','judgments') for r in unit[k])
        if count!=len(body['records']):raise ContractError('RECORD_COVERAGE')
    elif body['records']:
        raise ContractError('QUARANTINE_RECORDS_ESCAPED')
    for r in body['records']:
        try:
            part_id,pid,address=r['local_id'].split('/',2)
            if part_id!=body['part_id'] or pid!=r['premise_id']:raise ValueError('scope')
            expected_uid=r['kind']+':'+digest([body['dataset'],body['case_id'],body['snapshot_id'],part_id,r['local_id']])
            if r['uid']!=expected_uid:raise ValueError('uid')
            deps=[];refs=[]
            if r['kind']=='LINK':
                n=int(address[5:]);expected=raw['object_links'][n-1]
                if pid!='GLOBAL' or address!='LINK:'+str(n) or n<1:raise ValueError('link')
                text='Proposed cross-premise object link';refs=expected['refs']
                deps=[(expected['left_premise'],expected['left_object']),(expected['right_premise'],expected['right_object'])]
            else:
                unit=raw['analyses'][pid];base,_,role=address.partition('/ROLE:')
                prefix,nstr=base.split(':');n=int(nstr)
                collection={'EV':'records','OBJ':'objects','USE':'uses','J':'judgments'}[prefix]
                if base!=prefix+':'+str(n) or n<1:raise ValueError('address')
                row=unit[collection][n-1]
                if r['kind']=='BINDING':
                    if prefix not in ('USE','J') or not role:raise ValueError('role address')
                    ref=row['role_objects'][role];expected={'role':role,'reference':ref}
                    entity=unit['objects'][int(ref[4:])-1] if ref!='UNMAPPED' else None
                    text=role+': '+(entity['type']+': '+entity['label'] if entity else 'UNMAPPED')
                    refs=entity.get('refs',[]) if entity else [];deps=[(pid,ref)] if entity else []
                else:
                    if role or r['kind']!={'EV':'EVIDENCE','OBJ':'ENTITY','USE':'USE','J':'JUDGMENT'}[prefix]:raise ValueError('kind')
                    expected=row
                    text=row.get({'EV':'proposition','OBJ':'label','USE':'claim'}.get(prefix,''),'') if prefix!='J' else 'Candidate premise assessment: '+pid
                    if prefix=='EV':text=f"Attribution: {row['status']}; stage: {row['stage']}; court: {row['court_level']}; proposition: {row['proposition']}"
                    if prefix=='OBJ':text=row['type']+': '+row['label']
                    if prefix=='USE':text=f"Proposed direction: {row['direction']}; stage: {row['stage']}; claim: {row['claim']}"
                    refs=row.get('refs',[])
                    if prefix=='USE':refs=[w['source'] for w in row['witnesses']];deps=[(pid,x) for x in row['records']]
                    if prefix=='J':deps=[(pid,x) for x in row['uses']+row['opposition_uses']]
                    if prefix in ('USE','J'):deps+=[(pid,base+'/ROLE:'+k) for k in row['role_objects']]
            expected_deps=list(dict.fromkeys(addresses[f'{part_id}/{p}/{a}'] for p,a in deps))
            expected_refs=list(dict.fromkeys(sources[x] for x in refs))
            direction=expected.get('direction','NONE') if r['kind']=='USE' else 'NONE'
            if (r['original']!=expected or r['text']!=text or r['source_ids']!=expected_refs
                    or r['dependency_ids']!=expected_deps or r['direction']!=direction):raise ValueError('projection')
            eligible=expected_status=='READY_FOR_CONDITIONAL_PROCESSING' and raw['analyses'].get(pid,{}).get('analysis_status')=='ANALYZED'
            if r['computational_eligible']!=eligible:raise ValueError('eligibility')
        except (KeyError,ValueError,IndexError,TypeError) as exc:
            raise ContractError('RECORD_ORIGIN_MISMATCH',detail=r['local_id']) from exc
    rules={r['id']:r for r in old['rules']}
    if set(part['rule_ids'])!=set(r['rule_id'] for r in body['routes']) or len(body['routes'])!=len(part['rule_ids']):
        raise ContractError('ROUTE_COVERAGE')
    for r in body['routes']:
        rule=rules[r['rule_id']];pids={p['id'] for p in rule['premises']}
        scope={'jurisdiction':rule.get('jurisdiction'),'stage':rule.get('stage'),'legal_period':None,'claim_type':None,'route_family':None}
        expected_uid='ROUTE:'+digest([body['dataset'],body['case_id'],body['snapshot_id'],body['part_id'],r['rule_id']])
        expected_issue='ISSUE:'+digest([body['dataset'],body['case_id'],body['material_snapshot_id'],body['query_id']])
        if (r['uid']!=expected_uid or r['issue_id']!=expected_issue or r['scope']!=scope
                or r['text']!=rule.get('description','')+'\n'+'\n'.join(p['text'] for p in rule['premises'])
                or r['source_ids']!=list(dict.fromkeys(original_sources[x] for x in rule.get('source_refs',[])))
                or r['record_ids']!=[x['uid'] for x in body['records'] if x['premise_id'] in pids]):
            raise ContractError('ROUTE_ORIGIN_MISMATCH',detail=r['rule_id'])


def check_body(kind, body):
    schema_check(body, SCHEMAS[kind])
    if kind == 'CasePacket':
        if body['snapshot_id'] != digest(body['legacy']):
            raise ContractError('SNAPSHOT_MISMATCH')
        if body['material_snapshot_id']!=digest(body['legacy']['case']['segments']):
            raise ContractError('MATERIAL_SNAPSHOT_MISMATCH')
        targets=[t for t in body['legacy']['case']['targets'] if t['id']==body['query_id']]
        if len(targets)!=1 or targets[0]['text']!=body['query_text'] or body['legacy']['selected_query_id']!=body['query_id']:
            raise ContractError('QUERY_SELECTION_MISMATCH')
        src = {s['uid']: s for s in body['sources']}
        rec = {r['uid']: r for r in body['records']}
        routes = {r['uid']: r for r in body['routes']}
        unique([x['uid'] for group in (body['sources'], body['records'], body['routes']) for x in group], '$/uids')
        unique([s['local_id'] for s in body['sources']], '$/sources/local_id')
        for s in body['sources']:
            try:
                n=int(s['local_id'].split(':')[1])-1
                expected=body['legacy']['case']['segments'][n]
            except (ValueError,IndexError,KeyError) as exc:
                raise ContractError('SOURCE_ORIGIN', detail=s['local_id']) from exc
            if s['local_id']!='SRC:'+str(n+1) or n<0 or s['original']!=expected:
                raise ContractError('SOURCE_ORIGIN',detail=s['local_id'])
            if s['original_id']!=expected['id'] or s['document_id']!=expected['source_document']:
                raise ContractError('SOURCE_ADDRESS_OR_DOCUMENT',detail=s['local_id'])
            expected_uid='SOURCE:'+digest([body['dataset'],body['case_id'],body['material_snapshot_id'],s['original_id']])
            if s['uid']!=expected_uid:
                raise ContractError('GLOBAL_SOURCE_ID',detail=s['uid'])
            if s['text'] != s['original']['text'] or s['text_sha256'] != digest(s['text']):
                raise ContractError('SOURCE_CHANGED', '$/sources/'+s['uid'])
            if s['start'] != 0 or s['end'] != len(s['text']) or s['view_sha256'] != s['text_sha256']:
                raise ContractError('SPAN_MISMATCH', '$/sources/'+s['uid'])
        if len(src)!=len(body['legacy']['case']['segments']):
            raise ContractError('SOURCE_COVERAGE')
        for r in body['records']:
            require_refs(r['source_ids'], src, '$/records/'+r['uid']+'/source_ids')
            require_refs(r['dependency_ids'], rec, '$/records/'+r['uid']+'/dependency_ids')
            if any(not src[x]['text'].strip() for x in r['source_ids']):
                raise ContractError('BLANK_EVIDENCE', '$/records/'+r['uid'])
            if r['computational_eligible'] and body['contract_status'] != 'READY_FOR_CONDITIONAL_PROCESSING':
                raise ContractError('GATE_BYPASS', '$/records/'+r['uid'])
        for r in routes.values():
            require_refs(r['source_ids'], src, '$/routes/'+r['uid'])
            require_refs(r['record_ids'], rec, '$/routes/'+r['uid'])
        check_projection(body)
    elif kind == 'GraphRelease':
        nodes = {n['uid']: n for n in body['nodes']}
        unique([n['uid'] for n in body['nodes']], '$/nodes')
        unique(body['node_types'], '$/node_types'); unique(body['relation_types'], '$/relation_types')
        for n in nodes.values():
            if n['node_type'] not in body['node_types']:
                raise ContractError('NODE_TYPE', '$/nodes/'+n['uid'])
            require_refs(n['source_ids'], nodes, '$/nodes/'+n['uid']+'/source_ids')
            if any(nodes[i]['node_type']!='SOURCE' or nodes[i]['case_id']!=n['case_id'] for i in n['source_ids']):
                raise ContractError('NODE_SOURCE_TYPE_OR_CASE',detail=n['uid'])
        unique([digest(e) for e in body['edges']], '$/edges')
        for e in body['edges']:
            require_refs([e['src']], nodes, '$/edge/src'); require_refs([e['dst']], nodes, '$/edge/dst')
            key='|'.join((nodes[e['src']]['node_type'], e['relation'], nodes[e['dst']]['node_type']))
            if key not in body['relation_types']:
                raise ContractError('EDGE_TYPE', '$/edges', key)
            base=e['relation'].removesuffix('_REV')
            if base not in {'ATTRIBUTED_SOURCE','DEPENDS_ON','PROPOSED_SUPPORT','PROPOSED_OPPOSE','PROPOSED_CONTEXT','HAS_ISSUE','HAS_ROUTE','RULE_SOURCE','ROUTE_MEMBER','CASE_MATERIAL','CASE_PROPOSAL'}:
                raise ContractError('SUPERVISION_OR_UNKNOWN_EDGE', '$/edges', e['relation'])
        expected = {t: sorted(n['uid'] for n in nodes.values() if n['node_type']==t) for t in body['node_types']}
        if body['node_map'] != expected:
            raise ContractError('NODE_MAP_MISMATCH')
        if any(n['case_id'] == body['query_case_id'] and n['group_id'] != body['query_group_id'] for n in nodes.values()):
            raise ContractError('QUERY_GROUP_MISMATCH')
    elif kind == 'CandidatePool':
        unique([c['uid'] for c in body['candidates']], '$/candidates')
        if len(body['candidates']) > body['capacity']:
            raise ContractError('CANDIDATE_BUDGET')
        for c in body['candidates']:
            if c['case_id']==body['query_case_id'] or c['group_id']==body['query_group_id']:
                raise ContractError('QUERY_GROUP_LEAK', '$/candidates/'+c['uid'])
            if c['scope_status']=='INCOMPATIBLE':
                raise ContractError('INCOMPATIBLE_CANDIDATE')
    elif kind == 'RankRequest':
        if len(body['fanouts']) != 2 or not body['top_k']:
            raise ContractError('RANK_CONFIGURATION')
        role, scorer = body['checkpoint_role'], body['scorer']
        baseline=scorer in ('LEXICAL','DENSE','SPECTRAL','RRF')
        if (baseline and (role!='NONE' or body['checkpoint_sha256'] is not None)
                or scorer=='SAGE_SMOKE' and role!='RANDOM_SMOKE'
                or scorer=='SAGE' and role!='TASK_TRAINED'
                or not baseline and body['checkpoint_sha256'] is None):
            raise ContractError('CHECKPOINT_ROLE_MISMATCH')
    elif kind == 'RankResult':
        ids=[s['uid'] for s in body['scores']]; unique(ids, '$/scores')
        require_refs(body['selected_ids'], ids, '$/selected_ids')
        ordered=sorted(body['scores'], key=lambda s:(-s['score'],s['uid']))
        if body['scores'] != ordered or [s['rank'] for s in ordered] != list(range(1,len(ordered)+1)):
            raise ContractError('RANK_ORDER')
        if body['selected_ids'] != ids[:len(body['selected_ids'])]:
            raise ContractError('TOP_K_MISMATCH')
    elif kind == 'ContrastBundle':
        for c in body['contrasts']:
            if c['left']==c['right'] or not c['distinctions']:
                raise ContractError('EMPTY_CONTRAST')
            for d in c['distinctions']:
                if not d['left_refs'] or not d['right_refs']:
                    raise ContractError('UNSOURCED_DISTINCTION')
    elif kind == 'ContrastReview':
        if body['left']==body['right'] or not body['distinctions'] or any(v is None for v in body['checked_scope'].values()):
            raise ContractError('INCOMPLETE_CONTRAST_REVIEW')
        if body['route_family']!=body['checked_scope']['route_family']:
            raise ContractError('ROUTE_FAMILY_REVIEW')
        for field in ('left_outcome_refs','right_outcome_refs','scope_left_refs','scope_right_refs'):
            if not body[field]:raise ContractError('UNSOURCED_REVIEW', '$/'+field)
    elif kind == 'RelevanceLabel':
        if body['candidate_group_id']==body['query_group_id']:
            raise ContractError('LABEL_QUERY_GROUP_LEAK')
        if body['utility'] in ('POSITIVE','NEGATIVE') and (not body['candidate_refs'] or not body['query_refs']):
            raise ContractError('UNSOURCED_RELEVANCE_LABEL')


def seal(kind, body):
    if kind not in SCHEMAS:
        raise ContractError('UNKNOWN_CONTRACT', detail=kind)
    check_body(kind, body)
    core={'kind':kind,'schema_version':VERSION,'body':copy.deepcopy(body)}
    return {**core, 'sha256':digest(core)}


def validate(value, kind=None):
    if type(value) is not dict or set(value)!={'kind','schema_version','body','sha256'}:
        raise ContractError('ENVELOPE_FIELDS')
    if value['schema_version']!=VERSION:
        raise ContractError('SCHEMA_VERSION')
    actual=value['kind']
    if actual not in SCHEMAS or kind is not None and actual!=kind:
        raise ContractError('CONTRACT_KIND')
    core={k:value[k] for k in ('kind','schema_version','body')}
    if digest(core)!=value['sha256']:
        raise ContractError('CONTENT_HASH')
    check_body(actual,value['body'])
    return value['body']


def write_immutable(path, value):
    from pathlib import Path
    p=Path(path); data=canonical(value)+b'\n'
    p.parent.mkdir(parents=True,exist_ok=True)
    try:
        with p.open('xb') as stream:
            stream.write(data)
    except FileExistsError:
        if p.read_bytes()!=data:
            raise ContractError('IMMUTABLE_ARTIFACT_CHANGED',str(p))
