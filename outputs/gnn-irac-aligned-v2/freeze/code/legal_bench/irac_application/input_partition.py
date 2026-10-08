"""Reversible, explicitly approved quoted spans; never infer stages by keywords."""
import copy,re
from legal_bench.rules_verdict_v1.irac_native_schema_v1 import quote_errors,stage_partition,endpoint_ids
ALLOWED={'PRE_TARGET_RECORD','PRIOR_COURT_FINDING','TARGET_STAGE_PARTY_ARGUMENT'}
AVAIL='RETROSPECTIVELY_RECONSTRUCTED_PRE_TARGET'
def locate(text,quote):
    if not isinstance(quote,str) or not quote.strip():return None
    matches=list(re.finditer(re.escape(quote),text))
    if len(matches)==1:return [matches[0].start(),matches[0].end()]
    # Exact words with whitespace differences; recovered text preserves original bytes.
    pattern=r'\s+'.join(re.escape(w) for w in quote.split())
    matches=list(re.finditer(pattern,text))
    return [matches[0].start(),matches[0].end()] if len(matches)==1 else None

def partition(document,approved):
    lookup={s['id']:s for s in document['segments']};sources={};audit=[]
    for i,span in enumerate(approved):
        parent=span.get('source_id');stage=span.get('semantic_stage');s=lookup.get(parent)
        bounds=locate(s['text'],span.get('quote')) if s else None
        reasons=[]
        if s is None:reasons.append('SOURCE_NOT_FOUND')
        if bounds is None:reasons.append('UNLOCATED_OR_AMBIGUOUS_CONTIGUOUS_QUOTE')
        if stage not in ALLOWED:reasons.append('STAGE_NOT_ALLOWED')
        sid=str(parent)+':span'+str(i+1)
        if not reasons:
            sources[sid]=dict(text=s['text'][bounds[0]:bounds[1]],document_id=document['document_id'],url=document.get('url'),semantic_stage=stage,prospective_availability=AVAIL)
        audit.append(dict(source_id=sid,parent_source_id=parent,original_char_range=bounds,proposal=copy.deepcopy(span),admitted=not reasons,reasons=reasons))
    return sources,audit

def isolate_records(proposal,sources):
    """Local malformed/unsafe records and dependents excluded; other records remain."""
    records=[];kinds={}
    for kind in ('entities','facts','evidence','relations'):
        for row in proposal.get(kind,[]):
            row=copy.deepcopy(row);kinds[row.get('id')]=kind
            if row.get('prospective_availability') is None:row['prospective_availability']=AVAIL
            records.append(row)
    admitted,excluded=stage_partition(records,sources)
    # Duplicate identity records are all isolated, not arbitrarily selected.
    counts={}
    for r in admitted:counts[r['id']]=counts.get(r['id'],0)+1
    duplicate={i for i,n in counts.items() if n>1}
    while True:
        ids={r['id'] for r in admitted if r['id'] not in duplicate};keep=[];changed=False
        for r in admitted:
            missing=[x for x in endpoint_ids(r) if x not in ids]
            if r['id'] in duplicate or missing:
                excluded.append(dict(original=r,reasons=['DUPLICATE_ID'] if r['id'] in duplicate else ['DEPENDENCY_ENDPOINT_EXCLUDED'],missing_endpoints=missing));changed=True
            else:keep.append(r)
        admitted=keep;duplicate=set()
        if not changed:break
    return {k:[r for r in admitted if kinds[r['id']]==k] for k in ('entities','facts','evidence','relations')},excluded
