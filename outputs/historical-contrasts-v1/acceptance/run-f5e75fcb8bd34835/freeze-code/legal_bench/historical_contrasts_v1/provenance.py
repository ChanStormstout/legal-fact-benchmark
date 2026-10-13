"""Check frozen extracted spans against saved original response bytes."""
import hashlib
from pathlib import Path
from .contracts import ContractError, validate


def audit(packet,root):
    b=validate(packet,'CasePacket');root=Path(root).resolve();cache={};checked=0;view_only=[]
    for s in b['sources']:
        links=s['original'].get('provenance',[])
        if not links:view_only.append(s['uid'])
        for link in links:
            path=(root/link['raw_path']).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                raise ContractError('SOURCE_PATH_OR_FILE',detail=link['raw_path'])
            if path not in cache:
                raw=path.read_bytes();cache[path]=(raw,raw.decode('utf-8'),hashlib.sha256(raw).hexdigest())
            raw,text,h=cache[path]
            if h!=link['raw_sha256']:
                raise ContractError('SOURCE_FILE_CHANGED',detail=link['raw_path'])
            for field,content,quote in [('raw_char_range',text,s['text']),('raw_byte_range',raw,s['text'].encode('utf-8'))]:
                bounds=link[field]
                if (not isinstance(bounds,list) or len(bounds)!=2 or any(type(i) is not int for i in bounds)
                        or not 0<=bounds[0]<=bounds[1]<=len(content) or content[bounds[0]:bounds[1]]!=quote):
                    raise ContractError('ORIGINAL_SOURCE_SPAN_MISMATCH',detail=s['local_id']+'/'+field)
            if link['document_id']!=s['document_id']:
                raise ContractError('SOURCE_DOCUMENT_ID_MISMATCH',detail=s['local_id'])
            checked+=1
    return {'material_snapshot_id':b['material_snapshot_id'],'source_count':len(b['sources']),
        'checked_original_spans':checked,'original_files':{
            str(p.relative_to(root)):v[2] for p,v in sorted(cache.items())},
        'view_only_source_ids':view_only,'legal_semantics_verified':False}
