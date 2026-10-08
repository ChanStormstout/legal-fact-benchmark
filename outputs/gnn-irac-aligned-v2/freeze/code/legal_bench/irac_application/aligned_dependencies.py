"""Use-specific checks; no keyword guesses about unresolved qualifications."""
def usable_fields(record,needed):
    blocked=[]
    for u in record.get('unknowns',[]):
        fields=u.get('fields')
        if not fields or '*' in fields or set(fields)&set(needed):blocked.append(u)
    missing=[f for f in needed if record.get(f) is None]
    return dict(usable=not blocked and not missing,blocked=blocked,missing=missing)

def identity(a,b,witnesses):
    if a is None or b is None:return dict(status='UNRESOLVED',reason='MISSING_OBJECT_NOT_WILDCARD')
    for w in witnesses:
        if {w.get('left'),w.get('right')}=={a,b} and w.get('source_refs'):
            return dict(status=w['status'],origin='MODEL_PROPOSED_SOURCE_LINK',source_refs=w['source_refs'],semantic_verified=False)
    return dict(status='UNRESOLVED',reason='ID_OR_ROLE_EQUALITY_NOT_SOURCE_PROOF')

def time_order(left,right):
    """Explicit comparable ISO dates only. Missing/ambiguous intervals remain unknown."""
    from datetime import date
    if not all(x.get('source_refs') for x in (left,right)):return dict(status='UNRESOLVED',reason='UNSOURCED_TIME')
    try:a=date.fromisoformat(left['date']);b=date.fromisoformat(right['date'])
    except (KeyError,ValueError,TypeError):return dict(status='UNRESOLVED',reason='TIME_NOT_RESOLVED')
    return dict(status='SUPPORTED' if a<=b else 'REFUTED',property='LEFT_ON_OR_BEFORE_RIGHT',semantic_verified=False)
