"""Versioned semantic-address repair; no natural-language legal inference."""
from .realcase_grounding_v3 import source_match, reviewed, role_view
from .contracts import content_hash

def step_semantic_hash(step):
    """Pin all executable fields; named-slot/binding order and prose are irrelevant.

    Duplicate slots/roles and unknown fields are rejected by the checker before
    this function is reached. IDs, source references, states and time are pinned.
    """
    return content_hash({'id':step['id'],'rule_ref':step['rule_ref'],
        'bindings':sorted(step['bindings'],key=lambda x:x['role']),
        'time_scope':step['time_scope'],'inputs':sorted(step['inputs'],key=lambda x:x['slot']),
        'proposed_state':step['proposed_state']})

def court_assessment(snap, step, rule):
    record=snap.get('court_assessments',{}).get(step['id'])
    if record is None:return None,None
    expected={'case_id':snap['case_id'],'stage':snap['stage'],
        'rule_ref':step['rule_ref'],'rule_hash':content_hash(rule),
        'predicate':rule['conclusion_predicate'],'time_scope':step['time_scope'],
        'statement_status':'TARGET_COURT_FINDING','state':'TRUE'}
    pinned=(record.get('step_semantic_hash')==step_semantic_hash(step)
            if 'step_semantic_hash' in record else record.get('step_hash')==content_hash(step))
    same_bindings=sorted(record.get('bindings',[]),key=lambda x:x['role'])==sorted(step['bindings'],key=lambda x:x['role'])
    if (not reviewed(record) or not pinned or not same_bindings or
        any(record.get(k)!=v for k,v in expected.items()) or source_match(record,snap['sources'])['error']):
        return None,'COURT_ASSESSMENT_UNVERIFIED'
    if any(snap['sources'][r]['role']=='DISPOSITION_ONLY' or
           snap['sources'][r]['document']!=snap['case_id'] for r in record['refs']):
        return None,'COURT_ASSESSMENT_SOURCE_ROLE'
    return record,None
