"""Actual updates are immutable events. No invented investigation outcomes."""
import copy
from common import digest, prepare_sources, save

def apply_update(old_snapshot,event,new_library=None):
    kind=event['kind']
    if event.get('parent_snapshot')!=old_snapshot['snapshot_id']:raise ValueError('UPDATE_PARENT_MISMATCH')
    allowed={'REVEAL_SOURCE','REASSESS_SOURCE','REVOKE_REVIEW','RULE_VERSION','HYPOTHETICAL'}
    if kind not in allowed or not event.get('reason'):raise ValueError('INVALID_UPDATE_EVENT')
    if old_snapshot['namespace']=='HYPOTHETICAL' and kind!='HYPOTHETICAL':raise ValueError('HYPOTHESIS_CANNOT_UPDATE_ACTUAL_BRANCH')
    rows=copy.deepcopy(old_snapshot['original_sources'])
    if kind=='REVEAL_SOURCE':
        additional=event.get('sources',[])
        if not additional or not event.get('acquisition_record'):raise ValueError('ACTUAL_MATERIAL_AND_PROVENANCE_REQUIRED')
        if set(s['source_id'] for s in additional)&{s['source_id'] for s in rows}:raise ValueError('REVEAL_CANNOT_REPLACE_OLD_SOURCE')
        rows+=copy.deepcopy(additional)
    if kind!='REVEAL_SOURCE' and event.get('sources'):raise ValueError('UNDECLARED_SOURCE_CHANGE')
    lib=old_snapshot['rule_library'] if new_library is None else new_library
    if kind=='RULE_VERSION':
        if new_library is None or new_library['version']==old_snapshot['rule_library']['version']:raise ValueError('NEW_RULE_VERSION_REQUIRED')
    elif digest(lib)!=old_snapshot['rules_hash']:raise ValueError('RULE_CHANGE_REQUIRES_NEW_VERSION_EVENT')
    if kind=='REVOKE_REVIEW' and not event.get('receipt_ids'):raise ValueError('SPECIFIC_REVOCATION_REQUIRED')
    if kind=='REASSESS_SOURCE' and not event.get('review_request_id'):raise ValueError('INDEPENDENT_REASSESSMENT_REQUEST_REQUIRED')
    packet={'case_id':old_snapshot['case_id'],'question':old_snapshot['question'],'scope':old_snapshot['scope'],'sources':rows,'corpus_manifest_hash':old_snapshot.get('corpus_manifest_hash')}
    new=prepare_sources(packet,lib,'HYPOTHETICAL' if kind=='HYPOTHETICAL' else old_snapshot['namespace'],old_snapshot['snapshot_id'])
    new['update_event']=copy.deepcopy(event);new['prior_acceptances_transferred']=False
    new['assumptions']=copy.deepcopy(event.get('assumptions',[])) if kind=='HYPOTHETICAL' else []
    new['snapshot_id']=digest({k:v for k,v in new.items() if k!='snapshot_id'})
    return new,{'event_id':digest(event),'kind':kind,'parent':old_snapshot['snapshot_id'],'snapshot_id':new['snapshot_id'],
        'source_view_changed':kind=='REVEAL_SOURCE','new_evidence_obtained':kind=='REVEAL_SOURCE',
        'invalidated_dependencies':'ALL_SOURCE_ASSESSMENTS_USES_BINDINGS_BUNDLES_RULES_REPORTS',
        'review_execution':'REQUIRES_FRESH_PROVIDER_CALLS','assumptions_not_actual_facts':True,'legal_approval':False}
