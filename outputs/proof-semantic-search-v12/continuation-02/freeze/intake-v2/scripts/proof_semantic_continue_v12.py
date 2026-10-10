#!/usr/bin/env python3
"""Versioned V12 intake; raw retained, exact source aliases resolved separately."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.semantic_sources_v12 import resolve_record,trace_sources
from legal_bench.proof_carrying.semantic_import_v12 import adapt
from legal_bench.proof_carrying.semantic_features_v12 import graph,ce_pairs
from legal_bench.proof_carrying.semantic_tasks_v12 import task
from scripts.proof_semantic_run_v12 import save,run
ROOT=Path('outputs/proof-semantic-search-v12')
OUT=ROOT/'continuation-02'

def intake(cid,role,raw_path,task_path):
    case=json.loads((ROOT/'cohort'/cid/'case.json').read_text())
    if case['split'] not in ('TRAIN','DEV'):raise ValueError('TEST_ISOLATED')
    dest=OUT/'generated'/cid/role
    dest.mkdir(parents=True,exist_ok=False)
    raw=Path(raw_path).read_text();(dest/'raw.txt').write_text(raw)
    text=raw.strip();ops=[]
    # Browser Copy can serialize outer visible whitespace as HTML entities.
    # Only outside the JSON object; never decode or alter a quoted value.
    if re.match(r'^(?:&#x20;\s*)+\{',text) or re.search(r'\}(?:\s*&#x20;)+$',text):
        text=re.sub(r'^(?:&#x20;\s*)+|(?:\s*&#x20;)+$','',text)
        ops.append('REMOVED_OUTER_HTML_SPACE_ENTITIES_VISIBLE_AS_WHITESPACE')
    if re.fullmatch(r'```(?:json)?\s*\n[\s\S]*\n```',text):
        text=re.sub(r'^```(?:json)?\s*\n|\n```$','',text);ops=['OUTER_FENCE_REMOVED']
    try:
        data=json.loads(text)
        if not isinstance(data,dict):raise ValueError('OBJECT_REQUIRED')
    except (ValueError,TypeError) as e:
        save(dest/'failure.json',{'run_status':'FORMAT_ERROR','answer':None,'error':str(e),'operations':ops});return
    save(dest/'parsed.json',data)
    resolved,mapping=resolve_record(data,case,task_path)
    save(dest/'resolved.json',resolved);save(dest/'address-map.json',mapping)
    save(dest/'format.json',{'status':'PARSED','raw_sha256':hashlib.sha256(raw.encode()).hexdigest(),'operations':ops,'semantic_verified':False})
    if role=='proposal':
        # A readable proposal remains reviewable even if graph adaptation fails.
        review=task('review',case,data);(dest.parent/'review-task.txt').write_text(review)
        save(dest.parent/'review-task-manifest.json',{'task_sha256':hashlib.sha256(review.encode()).hexdigest(),'proposal_raw_sha256':hashlib.sha256(raw.encode()).hexdigest(),'independent_reference_read':False})
        trace=trace_sources(case);save(dest/'source-trace.json',trace)
        if not trace['all_traceable']:
            save(dest/'interface-failure.json',{'run_status':'SOURCE_MAPPING_FAILURE','answer':None});return
        try:s,c,q=adapt(case,resolved)
        except (ValueError,KeyError,TypeError) as e:
            save(dest/'interface-failure.json',{'run_status':'INTERFACE_ERROR','answer':None,'error':str(e)});return
        save(dest/'input-snapshot.json',s);save(dest/'candidates.json',c);save(dest/'requests.json',q)
        try:
            save(dest/'graph.json',graph(case,resolved));save(dest/'ce-pairs.json',ce_pairs(case,resolved))
        except (ValueError,KeyError,TypeError) as e:
            save(dest/'graph-failure.json',{'run_status':'INTERFACE_ERROR','answer':None,'error':str(e)});return
        run(s,c,q,dest/'nonlearning')
    print(json.dumps({'case':cid,'role':role,'mappings':len(mapping['mappings']),'saved':str(dest)}))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('case');ap.add_argument('role',choices=['proposal','reference','review']);ap.add_argument('raw');ap.add_argument('--task',required=True);a=ap.parse_args();intake(a.case,a.role,a.raw,a.task)
