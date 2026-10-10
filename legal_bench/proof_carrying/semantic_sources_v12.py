"""Lossless attachment-address resolution. Address identity is not semantic approval."""
import copy
import hashlib
import re
from pathlib import Path

PREFIX = re.compile(r'^turn\d+file\d+:(IK-[0-9]+:L[0-9]+)$')
ATTACHMENT = re.compile(r'^turn0file0$')
REF_FIELDS = {'refs', 'source_refs'}


def resolve_record(record, case, task_path):
    """Resolve only exact addresses printed in the actual single task attachment.

    Preserve the raw record separately. No text, quote, status, binding or label
    changes; unknown/foreign addresses remain unchanged and fail normal checks.
    """
    path = Path(task_path)
    task = path.read_text()
    task_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    sources = {s['id']: s for s in case['segments']}
    changes = []
    def walk(value, location='$'):
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if key in REF_FIELDS and isinstance(item, list):
                    resolved = []
                    anchors=[]
                    for ref in item:
                        match=PREFIX.fullmatch(ref) if isinstance(ref,str) else None
                        canonical=match.group(1) if match else ref
                        if isinstance(canonical,str) and canonical in sources and sources[canonical]['source_document']==case['case_id']:
                            anchors.append(canonical)
                    for index, ref in enumerate(item):
                        # The single submitted attachment is a document pointer,
                        # not another paragraph. Keep it in the mapping ledger;
                        # never expand a bare pointer into unlisted paragraphs.
                        if isinstance(ref,str) and ATTACHMENT.fullmatch(ref) and anchors and all('['+a+']\n'+sources[a]['text'] in task for a in anchors):
                            changes.append({'path':f'{location}.{key}[{index}]','raw_ref':ref,
                                'kind':'ATTACHMENT_DOCUMENT_POINTER','canonical_document':case['case_id'],
                                'explicit_paragraph_refs':anchors,'task_sha256':task_hash,
                                'source_sha256':case['source_sha256'],'semantic_verified':False,
                                'whole_document_quote_search':False})
                            continue
                        match = PREFIX.fullmatch(ref) if isinstance(ref, str) else None
                        canonical = match.group(1) if match else ref
                        source = sources.get(canonical) if isinstance(canonical, str) else None
                        if match and source and source['source_document'] == case['case_id'] and canonical in task and source['text'] in task:
                            changes.append({'path':f'{location}.{key}[{index}]', 'raw_ref':ref,
                                'canonical_ref':canonical, 'task_sha256':task_hash,
                                'source_sha256':case['source_sha256'],
                                'document_id':source['source_document'],
                                'original_line':source.get('original_line'),
                                'provenance':source.get('provenance',[]),
                                'semantic_verified':False})
                            resolved.append(canonical)
                        else:
                            resolved.append(ref)
                    result[key] = resolved
                else:
                    result[key] = walk(item, location+'.'+key)
            return result
        if isinstance(value, list):
            return [walk(item, f'{location}[{index}]') for index,item in enumerate(value)]
        return copy.deepcopy(value)
    return walk(record), {'version':'v12-address-map-2', 'task_path':str(path),
        'task_sha256':task_hash, 'mappings':changes, 'semantic_verified':False,
        'policy':'Exact attachment prefix plus same-document printed source only. A known single attachment pointer is separately retained when explicit source paragraphs are listed; no whole-document quote search. Raw unchanged.'}


def trace_sources(case):
    """Confirm frozen source text against recorded original response positions."""
    rows=[]; cache={}
    for source in case['segments']:
        matches=[]
        for p in source.get('provenance',[]):
            path=Path(p['raw_path'])
            if path not in cache:
                cache[path]=path.read_bytes() if path.exists() else None
            raw=cache[path]
            ok=raw is not None and hashlib.sha256(raw).hexdigest()==p['raw_sha256']
            text=raw.decode('utf-8') if ok else ''
            span=p.get('raw_char_range',[])
            excerpt=text[span[0]:span[1]] if ok and len(span)==2 else ''
            matches.append({'raw_path':str(path),'raw_hash_valid':ok,
                'document_identity_valid':str(p.get('document_id'))==str(case['case_id']),
                'text_in_raw_span':source['text'] in excerpt,
                'response_index':p.get('response_index'),'range':span,
                'url':p.get('url')})
        rows.append({'ref':source['id'],'original_line':source.get('original_line'),
            'valid':any(m['raw_hash_valid'] and m['document_identity_valid'] and m['text_in_raw_span'] for m in matches),
            'locations':matches})
    return {'case_id':case['case_id'],'rows':rows,'all_traceable':all(r['valid'] for r in rows),
        'semantic_verified':False}
