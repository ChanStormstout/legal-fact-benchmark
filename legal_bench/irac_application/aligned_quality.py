"""Local admission audits. Never promotes address validity to semantic truth."""
import hashlib,json
from .aligned_graph import check_refs

def validate_reference(reference,template,sources):
    expected={t['id'] for t in template['tests']};seen=set();audit=[]
    for r in reference['tests']:
        errors=[];key=r['test_id']
        if key in seen:errors.append('DUPLICATE_TEST_REFERENCE')
        if key not in expected:errors.append('TEST_NOT_IN_TEMPLATE')
        seen.add(key)
        refs=r.get('support_refs',[])+r.get('opposition_refs',[])
        for binding in r.get('bindings',[]):refs+=binding.get('source_refs',[])
        errors+=check_refs(refs,sources)
        if r['status']=='UNRESOLVED' and not r.get('gap_reason'):errors.append('UNRESOLVED_WITHOUT_SPECIFIC_GAP')
        audit.append(dict(test_id=key,errors=errors,semantic_review_required=True))
    return dict(rows=audit,missing_tests=sorted(expected-seen),complete_address_check=not any(x['errors'] for x in audit) and expected==seen,semantic_correctness_established=False)

def admission(reference,review):
    """Explicit review decisions only; training results may not be an input."""
    if review.get('basis')!='ALLOWED_SOURCES_AND_GIVEN_LAW':raise ValueError('INVALID_REVIEW_BASIS')
    decisions={r['test_id']:r for r in review['tests']};out=json.loads(json.dumps(reference))
    for r in out['tests']:
        d=decisions.get(r['test_id'],{});ok=d.get('decision')=='ADMIT' and not r.get('automatic_check_errors')
        r['supervision_mask']=bool(ok and r['status'] in ('SUPPORTED','REFUTED','UNRESOLVED'))
        r['admission']='ADMITTED_MODEL_REFERENCE' if r['supervision_mask'] else 'MASKED'
        r['admission_reason']=d.get('reason','NO_REVIEW_DECISION')
    out['reference_kind']='MODEL_GENERATED_SOURCE_REVIEWED_NOT_HUMAN_GOLD';return out

def preserve_snapshot(paths):return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

def assert_preserved(snapshot):
    from pathlib import Path
    return [p for p,h in snapshot.items() if not Path(p).exists() or hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h]
