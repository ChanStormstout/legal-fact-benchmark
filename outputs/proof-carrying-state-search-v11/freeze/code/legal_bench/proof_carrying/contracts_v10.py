"""Versioned local certificate contract for declared variables and alternative routes."""
from .realcase_contracts import schemas as old_schemas, validate,unique,binding_map,STATES
from .contracts import content_hash

def schemas(kind):
    s=old_schemas(kind)
    if kind=='derivation':
        s['properties']['steps']['maxItems']=8192
        s['properties']['requests']['maxItems']=8192
        s['properties']['gaps']['maxItems']=1000
        step=s['properties']['steps']['items']['properties']
        step['bindings']['maxItems']=40
        step['bindings']['items']['properties']['role']={'type':'string'}
    return s

def propose(snap,derivation):
    validate(derivation,schemas('derivation'))
    return {'version':'REALCASE_V10','mode':'RESEARCH_DRAFT','case_id':snap['case_id'],'stage':snap['stage'],'snapshot_id':snap['snapshot_id'],'snapshot_sha256':content_hash(snap),'proposal':derivation}
