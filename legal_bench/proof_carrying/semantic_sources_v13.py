"""Finite V13 attachment wrapper normalization; no source/label repair."""
import copy,re
from .semantic_sources_v12 import resolve_record as resolve_v12

HASH_ADDRESS=re.compile(r'^turn\d+file\d+#(IK-[0-9]+:L[0-9]+)$')

def resolve_record(record,case,task_path):
    # A '#' wrapper is an attachment address, not a new source. Only the exact
    # same-document ID and unchanged text printed in the actual task can resolve.
    task=task_path.read_text();sources={s['id']:s for s in case['segments']};changes=[]
    def walk(value,path='$'):
        if isinstance(value,dict):
            result={}
            for key,item in value.items():
                if key in ('refs','source_refs') and isinstance(item,list):
                    result[key]=[]
                    for i,ref in enumerate(item):
                        m=HASH_ADDRESS.fullmatch(ref) if isinstance(ref,str) else None
                        canonical=m.group(1) if m else None;s=sources.get(canonical)
                        if s and s['source_document']==case['case_id'] and '['+canonical+']\n'+s['text'] in task:
                            result[key].append(canonical);changes.append({'path':path+'.'+key+'['+str(i)+']','raw_ref':ref,'canonical_ref':canonical,'kind':'EXACT_PRINTED_HASH_ATTACHMENT_ADDRESS','semantic_verified':False})
                        else:result[key].append(copy.deepcopy(ref))
                else:result[key]=walk(item,path+'.'+key)
            return result
        if isinstance(value,list):return [walk(x,path+'['+str(i)+']') for i,x in enumerate(value)]
        return copy.deepcopy(value)
    resolved,ledger=resolve_v12(walk(record),case,task_path)
    ledger.update(version='v13-address-map-1',mappings=changes+ledger['mappings'])
    return resolved,ledger
