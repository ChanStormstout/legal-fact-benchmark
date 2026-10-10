"""Untrusted certificate packaging. Does not import or call checker calculus."""
from .contracts import content_hash
from .realcase_contracts import validate, schemas

def propose(snapshot, derivation):
    validate(derivation,schemas('derivation'))
    return {'version':'REALCASE_V2','mode':'RESEARCH_DRAFT','case_id':snapshot['case_id'],
        'stage':snapshot['stage'],'snapshot_id':snapshot['snapshot_id'],
        'snapshot_sha256':content_hash(snapshot),'proposal':derivation}

def explanation(result, snapshot, certificate):
    """No generative completion. Every line comes from pinned data or checker status."""
    rows=['# Research reconstruction: '+snapshot['case_id'],
        'Model-assisted source review; qualified legal approval PENDING. This is not a legal certificate.',
        'Checks cover explicit typed bindings and supported rule operations, not source semantics.']
    for r in result.get('requests',[]):
        rows+=['','## '+r['id'],r['text'],'Draft status: '+r['draft_status']+'; answer: '+str(r['answer']),
               'Errors: '+', '.join(r.get('errors',[])),'Gaps: '+', '.join(r.get('gaps',[]))]
        for ref in r.get('source_refs',[]):
            s=snapshot['sources'][ref]
            rows.append('['+ref+']('+s['url']+') '+s['text'])
    rows+=['','## Preserved counterarguments']+certificate['proposal']['counterarguments']
    rows+=['','## Model-reported remaining gaps']+certificate['proposal']['gaps']
    rows+=['','## Accepted premises (attributed records; not independently seen exhibits)']
    for p in snapshot['premises'].values():
        rows.append(p['id']+' | '+p['statement_status']+' | '+p['stage']+' | '+p['state']+' | '+p['text'])
        rows+=['Limit: '+x for x in p['limitations']]
    return '\n\n'.join(rows)+'\n'
