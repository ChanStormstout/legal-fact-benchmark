"""Lossless legacy adapter. Invalid proposals stay in quarantine, never repaired."""
import copy
from .contracts import ContractError, digest, seal, validate
from legal_bench.proof_carrying import evidence_binding_gate_v20_5_1 as gate
from legal_bench.proof_carrying import shared_sources_v20_3 as shared


def packet(case, rules, part, payload, original_schema, reviews=None,
           technical_status='OK', raw_response=None, dataset='LEGAL_AI_EXPOSED',query_id=None):
    if str(case.get('split','')).upper() in ('TEST','SEALED'):
        raise ContractError('SEALED_CASE_NOT_AUTHORIZED')
    if not isinstance(case.get('dispute_id'),str) or not case['dispute_id'].strip():
        raise ContractError('EXPLICIT_DISPUTE_GROUP_REQUIRED')
    targets=case.get('targets',[])
    if query_id is None:
        if len(targets)!=1:raise ContractError('EXPLICIT_SINGLE_QUERY_REQUIRED')
        query_id=targets[0]['id']
    selected=[t for t in targets if t['id']==query_id]
    if len(selected)!=1 or not isinstance(selected[0].get('text'),str) or not selected[0]['text'].strip():
        raise ContractError('EXPLICIT_SINGLE_QUERY_REQUIRED')
    query=selected[0]
    original = shared.expand(payload) if payload is not None and 'source_sets' in payload else payload
    legacy = copy.deepcopy({'case':case, 'rules':rules, 'part':part, 'payload':original,
        'original_schema':original_schema, 'reviews':reviews, 'raw_response':raw_response,
        'technical_status':technical_status,'selected_query_id':query_id})
    snap=digest(legacy); material=digest(case['segments']);cid=case['case_id']; group=case.get('dispute_id') or cid
    if len({s['id'] for s in case['segments']})!=len(case['segments']):
        raise ContractError('DUPLICATE_ORIGINAL_SOURCE_ADDRESS')
    def uid(kind, local):
        return kind+':'+digest([dataset,cid,snap,part['id'],local])
    sources=[]; source_lookup={}; source_original={}
    for i, s in enumerate(case['segments'],1):
        local='SRC:'+str(i); key='SOURCE:'+digest([dataset,cid,material,s['id']])
        source_lookup[local]=key; source_original[s['id']]=key
        sources.append({'uid':key,'local_id':local,'original_id':s['id'],
            'document_id':s['source_document'],'text':s['text'],'text_sha256':digest(s['text']),
            'view_sha256':digest(s['text']),'start':0,'end':len(s['text']),'original':copy.deepcopy(s)})
    errors=[]; records=[]
    if technical_status!='OK' or original is None:
        status='GENERATION_FAILED'; checked=None
    else:
        try:
            checked=gate.audit(shared.pack(original), original_schema, case, rules, reviews)
            status=checked['status']; errors=copy.deepcopy(checked['errors'])
        except (ValueError,KeyError,TypeError,IndexError) as exc:
            checked=None;status='REJECTED_FORMAT';errors=[{'kind':'LEGACY_FORMAT','detail':str(exc)}]
    if checked is not None and not errors:
        for pid,unit in original['analyses'].items():
            if unit['analysis_status']=='NOT_ANALYZED' and any(unit[k] for k in ('records','objects','uses','judgments')):
                errors.append({'kind':'NOT_ANALYZED_WITH_ARTIFACTS','premise_id':pid})
        if errors:status='REJECTED_STATUS_CONSISTENCY'
    if original is not None and technical_status=='OK' and not errors and checked is not None:
        eligible=status=='READY_FOR_CONDITIONAL_PROCESSING'
        pending=[]; addresses={}
        def declare(pid, local, kind, row, text, deps=(), refs=None, direction='NONE'):
            address=f'{part["id"]}/{pid}/{local}'
            key=uid(kind,address); addresses[(pid,local)]=key
            pending.append((key,pid,local,kind,row,text,list(deps),refs,direction))
        for pid, unit in original['analyses'].items():
            for collection,prefix,kind,text_key in [('records','EV','EVIDENCE','proposition'),
                    ('objects','OBJ','ENTITY','label'),('uses','USE','USE','claim'),
                    ('judgments','J','JUDGMENT',None)]:
                for i,row in enumerate(unit[collection],1):
                    local=f'{prefix}:{i}'; deps=[]
                    refs=row.get('refs',[])
                    if kind=='USE':
                        deps += [(pid,ref) for ref in row['records']]
                        refs=[w['source'] for w in row['witnesses']]
                    if kind=='JUDGMENT':
                        deps += [(pid,ref) for ref in row['uses']+row['opposition_uses']]
                    text=row.get(text_key,'') if text_key else 'Candidate premise assessment: '+pid
                    if kind=='EVIDENCE':text=f"Attribution: {row['status']}; stage: {row['stage']}; court: {row['court_level']}; proposition: {row['proposition']}"
                    if kind=='ENTITY':text=row['type']+': '+row['label']
                    if kind=='USE':text=f"Proposed direction: {row['direction']}; stage: {row['stage']}; claim: {row['claim']}"
                    declare(pid,local,kind,row,text,deps,refs,row.get('direction','NONE') if kind=='USE' else 'NONE')
                    if kind in ('USE','JUDGMENT'):
                        for role,ref in row['role_objects'].items():
                            role_local=local+'/ROLE:'+role
                            entity=unit['objects'][int(ref[4:])-1] if ref!='UNMAPPED' else None
                            declare(pid,role_local,'BINDING',{'role':role,'reference':ref},
                                role+': '+(entity['type']+': '+entity['label'] if entity else 'UNMAPPED'),
                                [(pid,ref)] if entity else [],entity.get('refs',[]) if entity else [])
                        # declare copied deps above; attach binding dependencies explicitly.
                        base=next(x for x in pending if x[1]==pid and x[2]==local)
                        base[6].extend((pid,local+'/ROLE:'+role) for role in row['role_objects'])
        for i, link in enumerate(original.get('object_links',[]),1):
            declare('GLOBAL','LINK:'+str(i),'LINK',link,'Proposed cross-premise object link',
                [(link['left_premise'],link['left_object']),(link['right_premise'],link['right_object'])],link['refs'])
        for key,pid,local,kind,row,text,deps,refs,direction in pending:
            try:
                resolved=[addresses[x] for x in deps]
                source_ids=[source_lookup[x] for x in refs]
            except KeyError as exc:
                raise ContractError('ADAPTER_UNDECLARED_REFERENCE',detail=str(exc)) from exc
            records.append({'uid':key,'local_id':f'{part["id"]}/{pid}/{local}',
                'premise_id':pid,'kind':kind,'text':text,
                'source_ids':list(dict.fromkeys(source_ids)),
                'dependency_ids':list(dict.fromkeys(resolved)),
                'direction':direction,'computational_eligible':eligible and original['analyses'].get(pid,{}).get('analysis_status')=='ANALYZED',
                'original':copy.deepcopy(row)})
    routes=[]
    if set(part['rule_ids'])-{r['id'] for r in rules}:
        raise ContractError('UNDECLARED_PART_RULE')
    for rule in rules:
        if rule['id'] not in part['rule_ids']:continue
        missing=set(rule.get('source_refs',[]))-set(source_original)
        if missing:
            raise ContractError('MISSING_RULE_SOURCE', detail=repr(sorted(missing)))
        issue='ISSUE:'+digest([dataset,cid,material,query_id])
        pids={p['id'] for p in rule['premises']}
        routes.append({'uid':uid('ROUTE',rule['id']), 'rule_id':rule['id'],'issue_id':issue,
            'text':rule.get('description','')+'\n'+'\n'.join(p['text'] for p in rule['premises']),
            'scope':{'jurisdiction':rule.get('jurisdiction'), 'stage':rule.get('stage'),
                     'legal_period':None,'claim_type':None,'route_family':None},
            'source_ids':list(dict.fromkeys(source_original[x] for x in rule.get('source_refs',[]))),
            'record_ids':[r['uid'] for r in records if r['premise_id'] in pids]})
    value=seal('CasePacket',{'dataset':dataset,'case_id':cid,'group_id':group,'snapshot_id':snap,'material_snapshot_id':material,
        'part_id':part['id'],'query_id':query_id,'technical_status':technical_status,'contract_status':status,
        'semantic_approval':False,'legal_approval':False,'sources':sources,'records':records,
        'routes':routes,'query_text':query['text'],'legacy':legacy,'errors':errors,
        'binding_review_sha256':digest(reviews) if reviews is not None else None})
    validate(value,'CasePacket')
    if value['body']['legacy']['payload']!=original:
        raise ContractError('LEGACY_FIDELITY')
    return value


def handoff(value):
    body=validate(value,'CasePacket'); old=body['legacy']
    if body['technical_status']!='OK' or old['payload'] is None:
        return {'technical_status':body['technical_status'],'contract_status':'GENERATION_FAILED',
                'formal_answer':None,'automatic_computation_status':'NOT_RUN_GENERATION_FAILED'}
    if any(isinstance(e,dict) and e.get('kind')=='NOT_ANALYZED_WITH_ARTIFACTS' for e in body['errors']):
        checked=gate.audit(shared.pack(old['payload']),old['original_schema'],old['case'],old['rules'],old['reviews'])
        return {'technical_status':body['technical_status'],'contract_status':'REJECTED_STATUS_CONSISTENCY',
            'existing_gate_status':checked['status'],'gate':checked,'adapter_errors':body['errors'],
            'formal_answer':None,'conditional_audit':None,'automatic_computation_status':'NOT_RUN_STATUS_CONSISTENCY'}
    # Authoritative existing gate is invoked again, independently of graph/ranking.
    return gate.process_saved(old['case'],old['rules'],old['part'],shared.pack(old['payload']),
                              old['original_schema'],body['technical_status'],old['reviews'])
