"""Versioned integration guards. Historical runs are data, never silently reinterpreted."""
import copy
import json
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from .contracts import byte_hash, content_hash, read_json
from .workflow_v7 import contract, write_once

VERSION = 'PROOF_GRAPH_INTEGRATION_V8'

def verify_history(root):
    root = Path(root)
    freeze = read_json(root/'freeze/config.json')
    verified = []
    # Live source changes are intentionally irrelevant to historical integrity.
    groups = [(root/'freeze/code', freeze['code_hashes']),
              (root, freeze['initial_material_hashes'])]
    if (root/'artifacts.json').exists(): groups.append((root, read_json(root/'artifacts.json')['hashes']))
    for base, hashes in groups:
        for rel, expected in hashes.items():
            p = base/rel
            if not p.is_file() or byte_hash(p) != expected:
                raise ValueError('HISTORICAL_BYTES_CHANGED:'+str(p))
            verified.append(str(p))
    return {'status':'VERIFIED_FROZEN_BYTES','files':len(verified),'reinterpreted':False}

def replay_history(root, destination):
    """Run the exact historical checker in its frozen import environment."""
    root=Path(root).resolve(); destination=Path(destination)
    integrity=verify_history(root)
    script=root/'freeze/code/scripts/check_realcase_certificate_v4.py'
    if not script.exists(): raise ValueError('FROZEN_ENTRY_UNAVAILABLE')
    # V7 froze checker files but omitted transitive support imports. Register an
    # explicit compatibility overlay, restoring EVERY frozen file over support code.
    repo=Path(__file__).resolve().parents[2]
    support={str(p.relative_to(repo)):byte_hash(p) for p in (repo/'legal_bench').rglob('*.py')}
    with tempfile.TemporaryDirectory(prefix='proof-v7-compatible-replay-') as tmp:
        work=Path(tmp)
        shutil.copytree(repo/'legal_bench',work/'legal_bench',ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(root/'freeze/code',work,dirs_exist_ok=True)
        entry=work/'scripts/check_realcase_certificate_v4.py'
        result=subprocess.run([sys.executable,str(entry),str(root/'certificate.json'),
            '--manifest',str(root/'manifest.json')],capture_output=True,text=True,timeout=120,cwd=work)
    out={'integrity':integrity,'entry':str(script),'entry_sha256':byte_hash(script),
         'compatibility_entry':'V8_REGISTERED_V7_FROZEN_CORE_WITH_EXPLICIT_SUPPORT_OVERLAY',
         'support_hashes':support,'all_frozen_core_bytes_restored':True,
         'limitation':'Historical freeze omitted transitive imports; support dependency environment is explicitly current and hashed, not claimed identical historical runtime.',
         'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
    write_once(destination,out)
    return out

def fixed_requests(raw):
    """Only called at preparation, on the declared task, not filtered new output."""
    rows=raw['requests']; ids=[q['id'] for q in rows]
    if not ids or len(set(ids))!=len(ids):raise ValueError('FIXED_REQUESTS_AMBIGUOUS')
    return [{'id':q['id'],'predicate':q['predicate'],'text':q['text']} for q in rows]

def import_derivation(raw, inventory):
    usable,isolated=contract('derivation',raw)
    expected={r['id']:r for r in inventory}
    errors={};unmapped=[]
    for record in isolated:
        if record['field']=='requests':
            key=record.get('original',{}).get('id') if isinstance(record.get('original'),dict) else None
            if key in expected: errors.setdefault(key,[]).append(record['reason'])
            else:unmapped.append(record)
    seen={r['id']:r for r in usable['requests']}
    for key,q in seen.items():
        if key not in expected:unmapped.append({'reason':'UNREGISTERED_REQUEST','original':q})
        elif q['predicate']!=expected[key]['predicate']:errors.setdefault(key,[]).append('REQUEST_PREDICATE_CHANGED')
    slots=[]
    for key,q in expected.items():
        if key not in seen:errors.setdefault(key,[]).append('REQUEST_MISSING_OR_ISOLATED')
        slots.append({**q,'technical_status':'CONTRACT_ERROR' if key in errors else 'READY',
            'answer':None,'failure_stage':'IMPORT' if key in errors else None,'reason':errors.get(key,[])})
    usable['requests']=[q for q in usable['requests'] if q['id'] in expected and q['id'] not in errors]
    return {'proposal':usable,'isolated':isolated,'request_slots':slots,'unmapped_errors':unmapped,
        'coverage_status':'INCOMPLETE' if errors or unmapped else 'ALL_DECLARED_REQUESTS_PRESENT'}

def complete_requests(imported, checked):
    actual={q['id']:q for q in checked.get('requests',[])};rows=[]
    for slot in imported['request_slots']:
        key=slot['id'];row=copy.deepcopy(slot)
        if slot['technical_status']=='READY':
            if checked.get('status')!='COMPLETED' or key not in actual:
                row.update(technical_status='CHECKER_FAILURE',failure_stage='CHECK',reason=[checked.get('reason','NO_REQUEST_RESULT')])
            else:row.update(technical_status='OK',answer=actual[key].get('answer'),checker_result=actual[key])
        rows.append(row)
    return {'requests':rows,'artifacts_delivered':True,'all_slots_accounted':True,
        'all_slots_technically_complete':all(q['technical_status']=='OK' for q in rows),
        'unmapped_errors':imported['unmapped_errors'],'semantics_verified':False,'legal_approval':False}

def source_roles(case_id, sources, documents):
    """Identity restoration per document, independent of citations inside its body."""
    index={};roles={};evidence=[]
    for doc in documents:
        p=Path(doc['path'])
        if byte_hash(p)!=doc['sha256']:raise ValueError('DOCUMENT_HASH_CHANGED')
        raw=read_json(p);did=str(raw['document_id']);role=doc.get('role','TARGET' if did==str(case_id) else None)
        if role not in ('TARGET','STATUTE','PRECEDENT'):raise ValueError('SOURCE_ROLE_REQUIRED')
        if (role=='TARGET')!=(did==str(case_id)):raise ValueError('SOURCE_IDENTITY_ROLE_CONFLICT')
        roles[did]=role
        for seg in raw['segments']:
            key=(did,seg['id'])
            if key in index and index[key]['text']!=seg['text']:raise ValueError('SOURCE_WINDOW_CONFLICT')
            index[key]=seg
        evidence.append({'document':did,'role':role,'sha256':doc['sha256'],'path':str(p)})
    out={}
    for ref,s in sources.items():
        seg=index.get((str(s['document']),ref))
        if not seg or seg['text']!=s['text'] or seg.get('original_line')!=s.get('original_line'):raise ValueError('SOURCE_NOT_RESTORED:'+ref)
        out[ref]={**s,'document_role':roles[str(s['document'])]}
    return out,evidence

def fact_source_check(premise,sources):
    refs=premise.get('refs',[])
    if not refs or any(r not in sources for r in refs):return 'UNRESOLVED_ADDRESS'
    if not any(sources[r]['document_role']=='TARGET' for r in refs):return 'FOREIGN_SOURCE_CANNOT_ESTABLISH_TARGET_FACT'
    if all(sources[r].get('role')=='DISPOSITION_ONLY' for r in refs):return 'CIRCULAR_DISPOSITION_PREMISE'
    return 'ADDRESS_AND_ROLE_VALID_NOT_SEMANTIC_APPROVAL'

def reverse_index(snapshot,derivation):
    edges={}
    def add(a,b):edges.setdefault(a,set()).add(b)
    for pid,p in snapshot['premises'].items():
        for r in p['refs']:add('source:'+r,'premise:'+pid)
        add('predicate:'+p['predicate'],'premise:'+pid)
    for rid,r in snapshot['rules'].items():
        for ref in r['source_refs']:add('source:'+ref,'rule:'+rid)
    for s in derivation['steps']:
        add('rule:'+s['rule_ref'],'step:'+s['id'])
        for x in s['inputs']:add(x['kind'].lower()+':'+x['id'],'step:'+s['id'])
    for q in derivation['requests']:add('step:'+q['step_id'],'request:'+q['id'])
    return {k:sorted(v) for k,v in sorted(edges.items())}

def revision_impact(index,changed):
    affected=set(changed);todo=list(changed)
    while todo:
        for child in index.get(todo.pop(),[]):
            if child not in affected:affected.add(child);todo.append(child)
    all_nodes=set(index)|{x for values in index.values() for x in values}
    return {'changed':sorted(changed),'affected':sorted(affected),'unchanged':sorted(all_nodes-affected),
        'invalidate_reviews':[x for x in sorted(affected) if x.startswith(('premise:','rule:','step:'))],
        'semantic_change_inherits_approval':False}
