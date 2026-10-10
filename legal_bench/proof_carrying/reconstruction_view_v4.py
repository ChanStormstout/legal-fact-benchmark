"""Deterministic display; unexamined request prose is never a checked conclusion."""
from .contracts import content_hash

ACCEPTED={'VALID_UNDER_ASSUMPTIONS','CONDITIONAL_RECONSTRUCTION'}

def view(snapshot, certificate, checked):
    if certificate['snapshot_sha256']!=content_hash(snapshot):
        raise ValueError('DISPLAY_SNAPSHOT_MISMATCH')
    steps={s['id']:s for s in certificate['proposal']['steps']}
    requests={q['id']:q for q in certificate['proposal']['requests']}
    rows=[]
    for result in checked.get('requests',[]):
        q=requests[result['id']];step=steps[q['step_id']]
        rule=snapshot['rules'].get(step['rule_ref'])
        accepted=result['draft_status'] in ACCEPTED and result['answer'] in ('TRUE','FALSE')
        if accepted and (not rule or result.get('predicate')!=rule['conclusion_predicate']):
            raise ValueError('DISPLAY_TYPED_RESULT_MISMATCH')
        rows.append({'id':q['id'],'submitted_prose':q['text'],
            'submitted_prose_semantically_checked':False,
            'checked_scope':{'predicate':q['predicate'],'rule':step['rule_ref'],
                'statement':rule['conclusion_text'] if rule else None,'bindings':step['bindings'],
                'time_scope':step['time_scope'],'rule_scope_limits':rule['scope_limits'] if rule else [],
                'basis':'SOURCE_REVIEWED_TRANSLATION_ASSUMED_NOT_AUTOMATICALLY_VERIFIED'},
            'published_conditional_statement':rule['conclusion_text'] if accepted else None,
            'status':result['draft_status'],'state':result['answer'],
            'semantic_assumptions':result.get('semantic_assumptions',[]),
            'source_refs':result.get('source_refs',[]),'gaps':result.get('gaps',[]),
            'errors':result.get('errors',[]),'legal_approval':False})
    return {'requests':rows,'policy':'Submitted natural-language prose is displayed only as an unverified claim; the conditional conclusion is rendered from the reviewed rule and explicit binding.',
            'interpretation':'This display prevents status labels from endorsing arbitrary prose. It does not detect semantic errors in prose or approved translations.'}
