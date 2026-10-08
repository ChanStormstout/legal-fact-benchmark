"""Condition-level admission. Mask controls loss, never graph construction."""
from .rendered_quotes import check_refs

CLASSES=('SATISFIED','DEFEATED','UNRESOLVED')
BASIS={'FACT_ACCEPTED','FACT_FALSE','BURDEN_NOT_CARRIED','INSUFFICIENT_RECORD',
       'LEGAL_INTERPRETATION','AMBIGUOUS_REASONING','NOT_DECIDED'}

def adapt_targets(condition_ids, proposal, sources):
    rows=proposal.get('element_targets',proposal.get('application_targets',[]))
    indexed={};duplicates=set()
    for row in rows:
        cid=row.get('condition_id')
        if cid in indexed:duplicates.add(cid)
        indexed[cid]=row
    result=[]
    for cid in condition_ids:
        row=indexed.get(cid,{})
        label=row.get('status',row.get('label'))
        basis=row.get('basis_kind');refs=row.get('target_refs',row.get('source_refs',[]))
        reasons=[]
        if cid in duplicates:reasons.append('DUPLICATE_TARGET')
        if not row:reasons.append('NO_TARGET_PROPOSED')
        if basis=='NOT_DECIDED':reasons.append('NOT_DECIDED_IS_UNOBSERVED')
        if basis=='AMBIGUOUS_REASONING':reasons.append('AMBIGUOUS_REFERENCE_NOT_OBSERVED_UNRESOLVED')
        if label not in CLASSES:reasons.append('NO_VALID_CLASS')
        if basis not in BASIS:reasons.append('BASIS_UNSUPPORTED')
        if row.get('substantive_adjudication') is not True:reasons.append('SUBSTANTIVE_ADJUDICATION_NOT_CONFIRMED')
        if row.get('input_sufficient') is not True:reasons.append('INPUT_SUFFICIENCY_NOT_CONFIRMED')
        if row.get('source_review') not in {'SUPPORTED','QUALIFIED'}:reasons.append('SOURCE_REVIEW_NOT_ADMITTED')
        if label=='UNRESOLVED' and row.get('explicit_evidentiary_unresolved') is not True:
            reasons.append('UNRESOLVED_NOT_EXPLICITLY_ADJUDICATED')
        if basis=='BURDEN_NOT_CARRIED' and row.get('fact_truth')=='FALSE':reasons.append('BURDEN_IS_NOT_FACT_FALSE')
        if label=='SATISFIED' and basis in {'FACT_FALSE','BURDEN_NOT_CARRIED'}:reasons.append('LABEL_BASIS_CONFLICT')
        quote_failures,render_audit=check_refs(refs,sources);reasons+=quote_failures
        result.append({'condition_id':cid,'target':label if not reasons else None,
                       'class_index':CLASSES.index(label) if not reasons else None,
                       'supervision_mask':not reasons,'basis_kind':basis,'target_refs':refs,
                       'mask_reasons':sorted(set(reasons)),'quote_rendering_audit':render_audit,'original_proposal':row})
    return result
