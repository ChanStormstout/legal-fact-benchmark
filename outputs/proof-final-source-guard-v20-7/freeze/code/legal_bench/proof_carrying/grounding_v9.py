"""One exact, reversible source locator for acceptance and checking; never semantic approval."""
from .realcase_grounding_v3 import canonical_chars, reviewed, role_view
from .realcase_grounding_v4 import step_semantic_hash
from .contracts import content_hash

def source_match(record,sources):
    refs=record.get('refs',record.get('source_refs',[])); quote=record.get('quote',record.get('source_quote',''))
    if not refs or any(r not in sources for r in refs):return {'error':'SOURCE_ADDRESS_MISSING'}
    refs=list(dict.fromkeys(refs))
    if len({sources[r]['document'] for r in refs})!=1:return {'error':'MULTI_DOCUMENT_QUOTE'}
    refs.sort(key=lambda r:(sources[r].get('original_line',10**12),r))
    groups=[]
    for r in refs:
        line=sources[r].get('original_line')
        if groups and line is not None and sources[groups[-1][-1]].get('original_line') is not None and line==sources[groups[-1][-1]]['original_line']+1:groups[-1].append(r)
        else:groups.append([r])
    def locate(text):
        q,_=canonical_chars(text)
        if not q:return []
        matches=[]
        for group in groups:
            joined=' '.join(sources[r]['text'] for r in group); canon,offset=canonical_chars(joined);pos=canon.find(q)
            while pos>=0:
                lo,hi=offset[pos],offset[pos+len(q)-1]+1;spans=[];base=0
                for r in group:
                    raw=sources[r]['text'];a,b=max(0,lo-base),min(len(raw),hi-base)
                    if a<b:spans.append({'ref':r,'start':a,'end':b,'original':raw[a:b]})
                    base+=len(raw)+1
                if spans not in matches:matches.append(spans)
                pos=canon.find(q,pos+1)
        return matches
    whole=locate(quote)
    if len(whole)==1:return {'error':None,'mode':'CONTIGUOUS_EXACT_RENDERER_NORMALIZED','original_spans':whole[0],'semantic_verified':False}
    if len(whole)>1:return {'error':'QUOTE_AMBIGUOUS','semantic_verified':False}
    # Newline-separated excerpts are explicit segments, never rendered as one continuous quote.
    parts=[p.strip() for p in quote.splitlines() if p.strip()]
    if len(parts)>1:
        found=[locate(p) for p in parts]
        if all(len(x)==1 for x in found):return {'error':None,'mode':'EXPLICIT_SEPARATE_EXCERPTS','segments':[x[0] for x in found],'original_spans':[s for x in found for s in x[0]],'semantic_verified':False}
    return {'error':'QUOTE_NOT_LOCATED','semantic_verified':False}

def court_assessment(snap,step,rule):
    record=snap.get('court_assessments',{}).get(step['id'])
    if record is None:return None,None
    expected={'case_id':snap['case_id'],'stage':snap['stage'],'rule_ref':step['rule_ref'],'rule_hash':content_hash(rule),'predicate':rule['conclusion_predicate'],'time_scope':step['time_scope'],'statement_status':'TARGET_COURT_FINDING','state':'TRUE'}
    if not reviewed(record) or record.get('step_semantic_hash')!=step_semantic_hash(step) or sorted(record.get('bindings',[]),key=lambda x:x['role'])!=sorted(step['bindings'],key=lambda x:x['role']) or any(record.get(k)!=v for k,v in expected.items()) or source_match(record,snap['sources'])['error']:return None,'COURT_ASSESSMENT_UNVERIFIED'
    if any(snap['sources'][r]['document']!=snap['case_id'] or snap['sources'][r]['role']=='DISPOSITION_ONLY' for r in record['refs']):return None,'COURT_ASSESSMENT_SOURCE_ROLE'
    return record,None
