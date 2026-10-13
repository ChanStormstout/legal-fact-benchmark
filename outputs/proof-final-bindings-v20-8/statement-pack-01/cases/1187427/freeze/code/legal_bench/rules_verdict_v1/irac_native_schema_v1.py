"""IRAC-native input contract. Address checks do not certify legal meaning.

No model inference, label recovery, quote repair or implicit stage inference.
Input and supervision are distinct files and APIs.
"""
import copy
import json
from pathlib import Path
from .irac_gate_v2 import ALLOWED, AVAILABILITY, admit_record, digest

INPUT_KEYS = {'case_id','issue','entities','rules','conditions','facts','evidence',
              'relations','blind_bindings','stage_metadata','provenance','prospective_availability'}
FORBIDDEN_KEYS = {'target','targets','element_targets','issue_target','target_provenance',
                  'target_reasoning','target_sources','target_outcome','conclusion','winning',
                  'losing','oracle_selection_basis','source_reviews','final_source_review',
                  'target_court_accepted','target_court_rejected','target_reasoning_embedding'}
COLLECTIONS = ('entities','rules','conditions','facts','evidence','relations','blind_bindings')
STATUSES = {'CLAIMED','DENIED','ADMITTED','PRIOR_FOUND','DOCUMENT_RECORDED','UNKNOWN'}
ELEMENT = {'SATISFIED','DEFEATED','UNRESOLVED'}
BASIS = {'FACT_ACCEPTED','FACT_FALSE','BURDEN_NOT_CARRIED','NOT_DECIDED',
         'INSUFFICIENT_RECORD','LEGAL_INTERPRETATION','AMBIGUOUS_REASONING'}

class ContractError(ValueError):
    pass

def forbidden_paths(value, path='$'):
    out=[]
    if isinstance(value,dict):
        for key,v in value.items():
            if key.lower() in FORBIDDEN_KEYS:out.append(path+'.'+key)
            out.extend(forbidden_paths(v,path+'.'+key))
    elif isinstance(value,list):
        for i,v in enumerate(value):out.extend(forbidden_paths(v,path+'['+str(i)+']'))
    return out

def quote_errors(refs, sources):
    """Each quote independently contiguous; whitespace-equivalent location only."""
    errors=[]
    if not isinstance(refs,list) or not refs:return ['NO_SOURCE_REFS']
    for i,ref in enumerate(refs):
        if not isinstance(ref,dict) or set(ref)!={'source_id','quote'}:
            errors.append('QUOTE_OBJECT_REQUIRED:'+str(i));continue
        if not isinstance(ref['source_id'],str):errors.append('SOURCE_ID_STRING_REQUIRED:'+str(i));continue
        source=sources.get(ref['source_id'],{})
        if not isinstance(source,dict):errors.append('SOURCE_OBJECT_REQUIRED:'+str(i));continue
        text=source.get('text','')
        quote=ref['quote']
        if not isinstance(quote,str) or not quote.strip():errors.append('EMPTY_QUOTE:'+str(i))
        elif ' '.join(quote.split()) not in ' '.join(text.split()):
            errors.append('NONCONTIGUOUS_OR_UNLOCATED_QUOTE:'+str(i))
    return errors

def record_ids(data):
    return {r['id'] for k in COLLECTIONS for r in data.get(k,[]) if isinstance(r,dict) and 'id' in r} | {data.get('issue',{}).get('id')}

def endpoint_ids(record):
    ids=list(record.get('entity_ids',[]))+list(record.get('evidence_ids',[]))
    for k in ('source_record_id','target_record_id','fact_id','condition_id','rule_id','asserted_by_entity_id','prior_court_entity_id','governs_issue_id'):
        if record.get(k) is not None:ids.append(record[k])
    ids+=record.get('supports_fact_ids',[])
    return ids

def referential_errors(data):
    ids=record_ids(data);errors=[];seen=set()
    for k in COLLECTIONS:
        for r in data.get(k,[]):
            if not isinstance(r,dict):errors.append('RECORD_NOT_OBJECT:'+k);continue
            ident=r.get('id')
            if not isinstance(ident,str) or not ident:errors.append('RECORD_ID_REQUIRED:'+k);continue
            if ident in seen:errors.append('DUPLICATE_ID:'+ident)
            seen.add(ident)
            for ep in endpoint_ids(r):
                if ep not in ids:errors.append('DANGLING_ENDPOINT:'+ident+':'+str(ep))
    return errors

def stage_errors(record, sources):
    refs=record.get('source_refs',[])
    grant={'semantic_stage':record.get('semantic_stage'), 'input_allowed':record.get('semantic_stage') in ALLOWED,
           'prospective_availability':record.get('prospective_availability'),
           'source_refs':[r.get('source_id') for r in refs if isinstance(r,dict)]}
    original=dict(record,refs=grant['source_refs'])
    source_grants={sid:{'semantic_stage':s.get('semantic_stage'),'input_allowed':s.get('semantic_stage') in ALLOWED} for sid,s in sources.items()}
    _,errors=admit_record(original,grant,source_grants)
    if record.get('statement_status') not in STATUSES:errors.append('STATEMENT_STATUS_INVALID')
    if record.get('statement_status')=='PRIOR_FOUND' and record.get('semantic_stage')!='PRIOR_COURT_FINDING':errors.append('PRIOR_FINDING_STAGE_MISMATCH')
    if record.get('court_level')=='TARGET' and record.get('statement_status')=='PRIOR_FOUND':errors.append('PRIOR_FINDING_PROMOTED')
    return errors

def binding_errors(binding, data):
    records={r['id']:r for k in ('facts','evidence') for r in data.get(k,[])}
    fact=records.get(binding.get('fact_id'));conds={r['id'] for r in data.get('conditions',[])}
    errors=[]
    if fact is None:return ['BINDING_FACT_NOT_ADMITTED']
    if binding.get('condition_id') not in conds:errors.append('BINDING_CONDITION_NOT_FOUND')
    if binding.get('relation') not in {'SUPPORTS','DEFEATS','RELEVANT_TO'}:errors.append('BINDING_RELATION_INVALID')
    for key in ('statement_status','semantic_stage','court_level'):
        if binding.get(key)!=fact.get(key):errors.append('BINDING_CHANGED_'+key.upper())
    permitted={(r['source_id'],r['quote']) for r in fact.get('source_refs',[])}
    for ref in binding.get('source_refs',[]):
        if (ref.get('source_id'),ref.get('quote')) not in permitted:errors.append('BINDING_REF_NOT_IN_RECORD_PROVENANCE')
    if not binding.get('source_refs'):errors.append('BINDING_SOURCE_REQUIRED')
    return errors

def validate_input(data):
    errors=[]
    if not isinstance(data,dict):return ['INPUT_NOT_OBJECT']
    errors+=['TARGET_OR_AUDIT_FIELD_FORBIDDEN:'+p for p in forbidden_paths(data)]
    errors+=['UNKNOWN_INPUT_KEY:'+k for k in set(data)-INPUT_KEYS]
    errors+=['MISSING_INPUT_KEY:'+k for k in INPUT_KEYS-set(data)]
    for k in COLLECTIONS:
        if not isinstance(data.get(k),list):errors.append('COLLECTION_REQUIRED:'+k)
        elif any(not isinstance(r,dict) for r in data[k]):errors.append('RECORD_OBJECT_REQUIRED:'+k)
        elif any(not isinstance(r.get('id'),str) or not r['id'] for r in data[k]):errors.append('RECORD_ID_REQUIRED:'+k)
    if errors:return sorted(set(errors))
    sources=data['provenance']
    if not isinstance(sources,dict):return ['PROVENANCE_MAP_REQUIRED']
    metadata=data.get('stage_metadata')
    if not isinstance(metadata,dict) or set(metadata)-{'policy_version'}:errors.append('STAGE_METADATA_NOT_INPUT_SAFE')
    # All semantic-stage/status metadata is carried on the actual records.
    # Sidecar audit decisions and excluded target IDs are not model features.
    for sid,s in sources.items():
        if not isinstance(s,dict) or not all(k in s for k in ('text','document_id','url','semantic_stage','prospective_availability')):
            errors.append('SOURCE_METADATA_MISSING:'+sid);continue
        if s['semantic_stage'] not in ALLOWED:errors.append('TARGET_SOURCE_IN_INPUT:'+sid)
        if s['prospective_availability'] not in AVAILABILITY:errors.append('SOURCE_AVAILABILITY_INVALID:'+sid)
    if errors:return sorted(set(errors))
    if data.get('prospective_availability') not in AVAILABILITY:errors.append('AVAILABILITY_INVALID')
    issue=data.get('issue')
    if not isinstance(issue,dict) or not isinstance(issue.get('id'),str) or not issue['id']:return ['ISSUE_REQUIRED']
    else:errors+=quote_errors(issue.get('source_refs'),sources)+stage_errors(issue,sources)
    rules={r.get('id'):r for r in data['rules']}
    for kind in COLLECTIONS:
        for r in data[kind]:
            if not isinstance(r,dict):continue
            qe=quote_errors(r.get('source_refs'),sources);errors+=qe
            if qe:continue
            errors+=stage_errors(r,sources)
            if kind=='rules':
                if r.get('independent_source') is not True:errors.append('INDEPENDENT_RULE_SOURCE_REQUIRED:'+str(r.get('id')))
                for ref in r.get('source_refs',[]):
                    if sources.get(ref['source_id'],{}).get('document_id')==data['case_id']:errors.append('TARGET_JUDGMENT_CANNOT_BE_INPUT_RULE')
            if kind=='conditions':
                rule=rules.get(r.get('rule_id'))
                if rule is None:errors.append('CONDITION_RULE_REQUIRED')
                elif not set(ref['source_id'] for ref in r['source_refs']) <= set(ref['source_id'] for ref in rule['source_refs']):errors.append('CONDITION_REF_NOT_IN_RULE')
                for dep in r.get('dependencies',[]):
                    if dep.get('operator') not in {'AND','OR','QUALIFICATION'}:errors.append('DEPENDENCY_OPERATOR_INVALID')
                    if dep.get('condition_id') not in {c['id'] for c in data['conditions']}:errors.append('DEPENDENCY_CONDITION_MISSING')
            if kind=='blind_bindings':errors+=binding_errors(r,data)
    errors+=referential_errors(data)
    types={r.get('id'):k for k in COLLECTIONS for r in data[k]}
    types[data.get('issue',{}).get('id')]='issue'
    for r in data['conditions']:
        if types.get(r.get('rule_id'))!='rules':errors.append('CONDITION_WRONG_RULE_TYPE')
    for r in data['relations']:
        a=types.get(r.get('source_record_id'));b=types.get(r.get('target_record_id'))
        required={'EVIDENCE_SUPPORTS_FACT':({'evidence'},{'facts'}),'PARTY_ASSERTS_FACT':({'entities'},{'facts'}),'PRIOR_COURT_FOUND_FACT':({'entities'},{'facts'}),'FACT_RELATES_TO_ENTITY':({'facts'},{'entities'})}
        pair=required.get(r.get('relation'))
        if pair is None or a not in pair[0] or b not in pair[1]:errors.append('RELATION_ENDPOINT_TYPES_INVALID')
        if r.get('relation')=='PRIOR_COURT_FOUND_FACT':
            fact=next((f for f in data['facts'] if f['id']==r.get('target_record_id')), {})
            if fact.get('statement_status')!='PRIOR_FOUND' or fact.get('semantic_stage')!='PRIOR_COURT_FINDING':errors.append('PRIOR_COURT_EDGE_NOT_SUPPORTED_BY_FACT_STATUS')
    return sorted(set(errors))

def stage_partition(records, source_grants):
    """Exclude forbidden records then cascading dependents, with original audit."""
    admitted=[];excluded=[]
    for r in records:
        errors=quote_errors(r.get('source_refs'),source_grants)+stage_errors(r,source_grants)
        (excluded if errors else admitted).append({'original':copy.deepcopy(r),'reasons':errors} if errors else copy.deepcopy(r))
    changed=True
    while changed:
        ids={r['id'] for r in admitted};changed=False;keep=[]
        for r in admitted:
            missing=[x for x in endpoint_ids(r) if x not in ids]
            if missing:excluded.append({'original':r,'reasons':['DEPENDENCY_ENDPOINT_EXCLUDED'],'missing_endpoints':missing});changed=True
            else:keep.append(r)
        admitted=keep
    return admitted,excluded

def validate_targets(targets, condition_ids, source_lookup):
    """Audit labels; never invent FACT_FALSE from evidentiary failure."""
    errors=[]
    for row in targets.get('element_targets',[]):
        if row.get('condition_id') not in condition_ids:errors.append('TARGET_CONDITION_UNKNOWN')
        if row.get('status') not in ELEMENT:errors.append('TARGET_STATUS_INVALID')
        if row.get('basis_kind') not in BASIS:errors.append('TARGET_BASIS_INVALID')
        errors+=quote_errors(row.get('target_refs'),source_lookup)
        if row.get('basis_kind')=='BURDEN_NOT_CARRIED' and row.get('fact_truth')=='FALSE':errors.append('BURDEN_IS_NOT_FACT_FALSE')
    issue=targets.get('issue_target',{})
    if issue.get('status') not in {'SUPPORTED','NOT_SUPPORTED','UNRESOLVED'}:errors.append('ISSUE_TARGET_STATUS_INVALID')
    for k in ('procedural_scope','reasoning','derivative_or_de_novo','unresolved_element_relationship'):
        if k not in issue:errors.append('ISSUE_TARGET_MISSING:'+k)
    errors+=quote_errors(issue.get('target_refs'),source_lookup)
    return sorted(set(errors))

def load_input(path):
    data=json.loads(Path(path).read_text());errors=validate_input(data)
    if errors:raise ContractError(';'.join(errors))
    return data

def input_from_case(case):
    """Explicit envelope separation, never deletes fields inside input."""
    data=copy.deepcopy(case['input']);errors=validate_input(data)
    if errors:raise ContractError(';'.join(errors))
    return data

def schema_description():
    return {'version':'IRAC_NATIVE_V1','input_keys':sorted(INPUT_KEYS),'forbidden_keys':sorted(FORBIDDEN_KEYS),'allowed_stages':sorted(ALLOWED),'availability':sorted(AVAILABILITY),'statement_status':sorted(STATUSES),'quotes':'array of separately contiguous {source_id,quote}; no concatenation repair','unknown_is_not_false':True,'basis_kind':sorted(BASIS),'targets_are_separate':True}
