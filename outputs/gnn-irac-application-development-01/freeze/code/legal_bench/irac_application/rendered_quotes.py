"""Reversible presentation-only citation-label view; no page/footer deletion.
Cached web responses wrap hyperlink labels in cite metadata. All legal characters
inside labels are retained. This is an address representation, not semantic repair.
"""
import re,hashlib
from .input_partition import locate
from legal_bench.rules_verdict_v1.irac_native_schema_v1 import quote_errors
MARKER=re.compile(r'\ue200cite\ue202[^†\ue201]*†([^\ue201]*)\ue201')

def citation_view(text):
    chars=[];mapping=[];start=0;wrappers=[]
    for m in MARKER.finditer(text):
        chars.extend(text[start:m.start()]);mapping.extend(range(start,m.start()))
        chars.extend(m.group(1));mapping.extend(range(m.start(1),m.end(1)))
        wrappers.append([m.start(),m.end()]);start=m.end()
    chars.extend(text[start:]);mapping.extend(range(start,len(text)))
    return ''.join(chars),mapping,wrappers

def check_refs(refs,sources):
    errors=quote_errors(refs,sources);audit=[]
    if not isinstance(refs,list):return errors,audit
    for i,ref in enumerate(refs):
        error='NONCONTIGUOUS_OR_UNLOCATED_QUOTE:'+str(i)
        if error not in errors:continue
        text=sources.get(ref.get('source_id'),{}).get('text','');quote=ref.get('quote')
        if not isinstance(quote,str):continue
        view,mapping,wrappers=citation_view(text);qview,_,qwrappers=citation_view(quote)
        bounds=locate(view,qview)
        if not bounds or not (wrappers or qwrappers):continue
        # Only markup removed, no page text or legal words; quote unchanged in storage.
        a,b=bounds;original=[mapping[a],mapping[b-1]+1]
        audit.append(dict(source_id=ref['source_id'],ref_index=i,match='CITATION_LABEL_RENDERED_VIEW',original_char_range=original,source_sha256=hashlib.sha256(text.encode()).hexdigest(),quote_sha256=hashlib.sha256(quote.encode()).hexdigest(),source_marker_ranges=wrappers,legal_text_modified=False))
        errors.remove(error)
    return errors,audit
