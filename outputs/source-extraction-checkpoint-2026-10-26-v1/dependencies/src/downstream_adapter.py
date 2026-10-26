"""Fail-closed source-stage handoff, deliberately not a full C orchestrator.

The full pipeline must still assess evidence uses, legal premises and applicability.
This interface never maps source-fidelity review to legal ACCEPT or premise TRUE.
"""
import copy
from common import digest, witness_registry

def source_packet(snapshot, catalog, records, eligibility):
    entries = {}
    for rid, record in records.items():
        item = eligibility[rid]
        if item['record_hash'] != digest(record) or item['catalog_hash'] != digest(catalog):
            raise ValueError('STALE_RECORD_ELIGIBILITY:' + rid)
        entries[rid] = {
            'record': copy.deepcopy(record), 'record_hash': digest(record),
            'source_fidelity_status': 'MODEL_SUPPORTED' if item['eligible'] else 'NOT_FULLY_VERIFIED',
            'field_review': copy.deepcopy(item),
            'may_supply_complete_source_interpretation': item['eligible'],
            'legal_use_status': 'NOT_REVIEWED', 'premise_truth': 'NOT_DETERMINED',
            'lawyer_approval': 'NOT_REQUESTED',
        }
    return {'version': 'SOURCE_PACKET_V25', 'case_id': snapshot['case_id'],
            'catalog': copy.deepcopy(catalog), 'catalog_hash': digest(catalog),
            'source_witnesses': witness_registry(snapshot, 'CASE'), 'records': entries,
            'source_hash': digest({i:s for i,s in snapshot['directory'].items() if s['domain']=='CASE'}),
            'consumer_requirements': [
                'Require model review of the specific intended evidence use before inference.',
                'Do not promote an allegation, denial, or prior finding into a present accepted fact.',
                'Unknown procedure cannot satisfy a procedure-dependent premise.',
                'Rebind and re-review every changed record/catalog dependency.',
                'Partial field support does not license the complete free-text proposition.'],
            'full_pipeline_connected': False, 'legal_acceptance_granted': False}
