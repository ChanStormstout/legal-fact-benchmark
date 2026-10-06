"""Import V09 model proposals without semantic repair or training.

The feature path reads only independently generated graph proposals and source
conditions. Use labels are saved separately and never arguments to graph code.
"""
import copy
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.rgcn09_continuation import ROOT, save, digest
from scripts.rgcn09_labels import validate


def read(path):
    return json.loads(Path(path).read_text())


def payload(task_id):
    web=ROOT/'web'
    path=web/(task_id+'.download.json')
    if path.exists():return read(path),str(path),'DOWNLOADED_JSON_UNCHANGED'
    blocks=web/(task_id+'.codeblocks.json')
    if blocks.exists():
        candidates=[]
        for block in read(blocks):
            try:
                p=json.loads(block)
                if isinstance(p,dict) and 'case_id' in p:candidates.append(p)
            except (ValueError,TypeError):pass
        if len(candidates)==1:return candidates[0],str(blocks),'JSON_CODE_BLOCK_WRAPPER_ONLY'
    raw=web/(task_id+'.response.txt')
    if raw.exists():
        text=raw.read_text(); candidates={}
        decoder=json.JSONDecoder(); expected=task_id.split('-',1)[1]
        for i,char in enumerate(text):
            if char!='{':continue
            try:
                p,end=decoder.raw_decode(text[i:])
                if isinstance(p,dict) and str(p.get('case_id'))==expected and ('uses' in p if task_id.startswith('LABEL') else 'alignments' in p):
                    candidates[json.dumps(p,sort_keys=True)]=p
            except (ValueError,TypeError):pass
        if len(candidates)==1:return next(iter(candidates.values())),str(raw),'COMPLETE_JSON_WITH_UNCHANGED_TEXT_WRAPPER_REMOVED'
    raise ValueError('NO_COMPLETE_JSON_SAVED')


def inspect_labels(p,case,units,target_ids):
    """Isolate a failed row, not the entire case; no missing class is supplied."""
    if str(p.get('case_id'))!=str(case['case_id']) or not isinstance(p.get('uses'),list) or not isinstance(p.get('unresolved'),list):
        raise ValueError('INVALID_CASE_OR_WRAPPER')
    seen=set();known=[];unknown=[];isolated=[]
    for row in p['uses']:
        uid=row.get('unit_id') if isinstance(row,dict) else None
        try:
            if uid not in target_ids or uid in seen:raise ValueError('UNREQUESTED_OR_DUPLICATE_USE')
            seen.add(uid)
            v=validate({'case_id':p['case_id'],'uses':[row],'unresolved':[]},case,units)
            known.extend(v['known']);unknown.extend(v['unknown'])
        except Exception as exc:isolated.append({'record':row,'reason':str(exc)})
    return {'case_id':p['case_id'],'known':known,'unknown':unknown,'isolated':isolated,
            'missing':sorted(set(target_ids)-seen),'unresolved':p['unresolved'],
            'reference_role':'MODEL_GENERATED_SOURCE_ANCHOR_CHECKED_NOT_HUMAN_GOLD',
            'semantic_status':'SINGLE_PASS_MODEL_REFERENCE; no independent accuracy established',
            'check_scope':'IDs, allowed source addresses, exact authority quotes and existing coarse fields',
            'unknown_unmarked_and_isolated_not_negative':True}


def join_old_graph(old,supplement,new_ids):
    """Keep every old fact byte-equivalent as data; only append new alignments."""
    if set(supplement)!={'case_id','alignments','coverage_limits'} or supplement['case_id']!=old['case_id']:
        raise ValueError('SUPPLEMENT_INTERFACE_OR_CASE')
    if len(supplement['alignments'])!=len(new_ids) or {a['unit_id'] for a in supplement['alignments']}!=set(new_ids):
        raise ValueError('SUPPLEMENT_CANDIDATE_COVERAGE')
    combined=copy.deepcopy(old)
    combined['alignments'].extend(copy.deepcopy(supplement['alignments']))
    combined['coverage_limits']+=supplement['coverage_limits']
    for k in ('needs','objects','facts','relations'):
        if combined[k]!=old[k]:raise AssertionError('OLD_GRAPH_CONTENT_CHANGED')
    return combined


def inspect_graph(p,source,units):
    required={'case_id','needs','objects','facts','relations','alignments','coverage_limits'}
    if set(p)!=required or str(p['case_id'])!=str(source['case_id']):raise ValueError('GRAPH_WRAPPER_CASE')
    if len(p['alignments'])!=len(units) or {a['unit_id'] for a in p['alignments']}!={u['id'] for u in units}:raise ValueError('GRAPH_CANDIDATE_COVERAGE')
    from legal_bench.rules_verdict_v1 import rgcn_development_v3 as g
    for f in p['facts']+p['relations']:
        if f['speaker'] not in g.SPEAKERS or f['status'] not in g.STATES or f['court'] not in g.COURTS or f['polarity'] not in g.POLARITY:
            raise ValueError('GRAPH_STATUS_ENUM')
    for a in p['alignments']:
        if a['scope'] not in g.SCOPES or a['state'] not in ('CANDIDATE','NONE','UNKNOWN','INCOMPATIBLE'):raise ValueError('ALIGNMENT_ENUM')
    return g


def import_all(version):
    out=ROOT/'imports'/version
    pool=read(ROOT.parent/'authority-pool/laws.json');new_ids=[u['id'] for u in pool if u['id'].startswith('LAW:V09:')]
    rows=read(ROOT/'split-manifest.json')['cases']; conditions=read(ROOT/'freeze/source-condition-proposals.json')
    oldroot=Path('outputs/rgcn-ranking-diagnostic-07/pilot');ledger=read(ROOT/'prepared-task-ledger.json')
    existing={str(r['case_id']) for r in rows if r.get('status','').startswith('EXISTING') and r['split']=='TRAIN'}
    tasks=[dict(task_id='LABEL-'+cid,case_id=cid,role='OLD_LABEL_NEW16_ONLY') for cid in sorted(existing)]+ledger
    from legal_bench.rules_verdict_v1 import authority_index
    authority_index.build(pool, out/'indexes/original.sqlite')
    reports=[]
    for task in tasks:
        cid=task['case_id'];tid=task['task_id'];rep={'task_id':tid,'case_id':cid,'role':task['role']}
        if next(r['split'] for r in rows if str(r['case_id'])==cid)!='TRAIN':raise ValueError('NONTRAIN_TASK')
        case=read(oldroot/'sources'/(cid+'.json')) if cid in existing else read(ROOT/'freeze/allowed'/(cid+'.json'))
        try:
            p,path,processing=payload(tid);save(out/'proposals'/(tid+'.json'),p)
            rep.update(raw_input=path,raw_sha256=digest(path),format_processing=processing)
            if tid.startswith('LABEL'):
                v=inspect_labels(p,case,pool,new_ids if cid in existing else [u['id'] for u in pool]);save(out/'labels'/(cid+'.json'),v)
                rep.update(status='IMPORTED_WITH_LOCAL_ISOLATION',known=len(v['known']),unknown=len(v['unknown']),isolated=len(v['isolated']),missing=len(v['missing']))
            else:
                if tid.startswith('ALIGN'):
                    oldp=next(read(f) for f in (oldroot/'parsed').glob('GRAPH*.json') if read(f)['case_id']==cid)
                    p=join_old_graph(oldp,p,new_ids)
                    rejected=[]
                    for f in (oldroot/'parsed').glob('GREV*.json'):
                        rv=read(f)
                        if rv['case_id']==cid:rejected=[x['id'] for x in rv['rejections']]
                else:rejected=[]
                g=inspect_graph(p,case,pool);graph=g.make_graph(p,conditions,case,pool,rejected)
                save(out/'graph-inputs'/(cid+'.json'),p);save(out/'graphs'/(cid+'.json'),graph)
                if cid in existing:
                    question=read(oldroot/'task-material'/(cid+'.json'))['question']
                else:
                    task_text=(ROOT/'tasks'/('GRAPH-'+cid+'.txt')).read_text()
                    question=json.loads(task_text.split('\nMATERIAL\n',1)[1].rsplit('\nEND_OF_INPUT ',1)[0])['question']
                query=question+'\n'+'\n'.join(s['text'] for s in case['segments'])
                ranking=authority_index.search(out/'indexes/original.sqlite',query,40)
                data=g.numeric(graph,ranking,pool)
                import numpy as np
                feature_path=out/'numeric'/(cid+'.npz');feature_path.parent.mkdir(parents=True,exist_ok=True)
                if feature_path.exists():raise ValueError('IMMUTABLE_FEATURE_FILE_EXISTS')
                np.savez_compressed(str(feature_path),**data)
                save(out/'numeric'/(cid+'.json'),{'unit_ids':[u['id'] for u in pool], 'shapes':{k:list(v.shape) for k,v in data.items()},'path':str(feature_path),'sha256':digest(feature_path),'training':False,'labels_in_input':False,'standardization':'not performed; future training-only scaling', 'ranking':ranking,'query':query})
                rep.update(status='GRAPH_BUILT_MODEL_PROPOSAL_NOT_GOLD',nodes=len(graph['nodes']),edges=len(graph['edges']),quarantined=len(graph['quarantine']),pending=len(graph['pending']),labels_visible=False)
        except Exception as exc:rep.update(status='PENDING_OR_IMPORT_FAILURE',reason=type(exc).__name__+': '+str(exc),answer=None)
        reports.append(rep)
    save(out/'import-report.json',{'tasks':reports,'trained':False,'sealed_used':False,'semantic_repair':False})
    print(json.dumps({'version':version,'tasks':len(reports),'labels_imported':sum('known'in r for r in reports),'graphs_built':sum('nodes'in r for r in reports),'pending_or_failures':sum('reason'in r for r in reports)},indent=2))

if __name__=='__main__':import_all(sys.argv[1])
