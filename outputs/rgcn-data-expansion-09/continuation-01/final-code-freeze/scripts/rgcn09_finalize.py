"""Close a bounded V09 preparation checkpoint. No models, training or publication.

Frozen inputs remain unchanged. Completed interface data, provisional semantics,
missing capture and unsent work are separate states, never guessed answers.
"""
import collections
import json
import re
import shutil
import subprocess
from pathlib import Path

from scripts.rgcn09_continuation import ROOT, digest, save


def read(p):
    return json.loads(Path(p).read_text())


def finish():
    pool = read(ROOT.parent/'authority-pool/laws.json')
    manifest = read(ROOT/'split-manifest.json')
    report = read(ROOT/'imports/final-01/import-report.json')
    imported = {r['task_id']: r for r in report['tasks']}
    web = ROOT/'web'
    planned = ['LAW-NEW16'] + [r['task_id'] for r in report['tasks']]
    ledger = []
    for tid in planned:
        evidence = sorted(web.glob(tid+'-*json')) + sorted(web.glob(tid+'.*json'))
        evidence = list(dict.fromkeys(evidence))
        submitted = [p for p in evidence if p.name.endswith('submitted.json')]
        attempts = [p for p in evidence if p.name.endswith('send-attempt.json')]
        completed = [p for p in evidence if p.name.endswith('completed.json')]
        imported_ok = tid in imported and 'reason' not in imported[tid]
        downloaded = web/(tid+'.download.json')
        status = ('IMPORTED_PROVISIONAL' if imported_ok else
                  'SOURCE_CONDITIONS_IMPORTED' if tid == 'LAW-NEW16' and downloaded.exists() else
                  'COMPLETED_CAPTURE_PENDING' if completed else
                  'SUBMITTED_CAPTURE_PENDING' if submitted else
                  'SEND_ACK_UNCERTAIN_INSPECT_BEFORE_ANY_RESEND' if attempts else
                  'NOT_SUBMITTED_ACCESS_BLOCK')
        urls = []
        for path in evidence:
            data = read(path)
            if not isinstance(data,dict):continue
            for key in ('url', 'conversation_url'):
                url = data.get(key)
                if url and url.startswith('https://chatgpt.com/c/') and url not in urls:
                    urls.append(url)
        ledger.append({'task_id':tid, 'status':status,
                       'confirmed_submitted':bool(submitted),
                       'send_attempt_uncertain':bool(attempts and not submitted),
                       'conversation_urls':urls, 'exact_model':None,
                       'observed_mode':'High / 高 where visibly recorded; see per-task evidence',
                       'attempt_evidence':[str(p) for p in evidence],
                       'semantic_retry':0, 'answer':None})
    counts = dict(collections.Counter(r['status'] for r in ledger))
    confirmed = sum(r['confirmed_submitted'] for r in ledger)
    uncertain = sum(r['send_attempt_uncertain'] for r in ledger)
    save(ROOT/'web-task-status.json', {'tasks':ledger, 'counts':counts,
         'confirmed_submissions':confirmed, 'additional_uncertain_send_attempts':uncertain,
         'new_call_count_interval':[confirmed, confirmed+uncertain],
         'budget':60, 'retries':0, 'precise_tokens_and_generation_seconds':None,
         'failure_boundary':'Capture pending is not a model failure or UNKNOWN answer.',
         'blocker':'Chrome extension browser no longer present in the connected browser inventory.',
         'old_v09_calls_separate':True})

    labels = {r['case_id']:r for r in report['tasks'] if 'known' in r}
    graphs = {r['case_id']:r for r in report['tasks'] if 'nodes' in r}
    old_supervision = read(Path('outputs/rgcn-use-development-08/supervision.json'))
    old_accepted = old_supervision['accepted_by_case']
    availability=[]; known_classes=collections.Counter(); isolated_reasons=collections.Counter()
    for row in manifest['cases']:
        cid=str(row['case_id']); label=labels.get(cid); graph=graphs.get(cid)
        if label:
            v=read(ROOT/'imports/final-01/labels'/(cid+'.json'))
            known_classes.update(x['category'] for x in v['known'])
            isolated_reasons.update(x['reason'] for x in v['isolated'])
        state=('RESERVED_SOURCE_ONLY' if row['split']=='SEALED_TEST' else
               'OLD_DEV_REUSED_NEW16_NOT_PREPARED' if row['split']=='DEVELOPMENT' else
               'LABEL_GRAPH_INTERFACE_PAIRED_PROVISIONAL' if label and graph else
               'PARTIAL_IMPORT' if label or graph else 'SOURCE_READY_TASKS_NOT_IMPORTED')
        availability.append({'case_id':cid,'split':row['split'], 'group_id':row['group_id'],
             'mechanism':row.get('mechanism','LEGACY_NOT_RECLASSIFIED'),
             'stage':row.get('stage','LEGACY_STAGE_IN_ORIGINAL_SOURCE'),
             'association':row.get('association','Legacy checked associations only; broader links unconfirmed'),
             'status':state,'old14_accepted_uses':len(old_accepted.get(cid,[])),
             'new_label_known':label.get('known',0) if label else 0,
             'new_label_isolated':label.get('isolated',0) if label else 0,
             'new_label_unknown':label.get('unknown',0) if label else 0,
             'graph_available':bool(graph),
             'numeric_available':(ROOT/'imports/final-01/numeric'/(cid+'.npz')).exists(),
             'semantic_quality':'New labels/alignments are single-pass model proposals; engineering checks do not establish truth.',
             'ready_for_accepted_main_training':False})
    save(ROOT/'case-availability.json', availability)
    coverage={}
    for split in ('TRAIN','DEVELOPMENT','SEALED_TEST'):
        rows=[r for r in availability if r['split']==split]
        coverage[split]={'registered_cases':len(rows),
            'mechanisms':dict(collections.Counter(r['mechanism'] for r in rows)),
            'stages':dict(collections.Counter(r['stage'] for r in rows)),
            'label_graph_interface_paired':sum(r['status']=='LABEL_GRAPH_INTERFACE_PAIRED_PROVISIONAL' for r in rows)}
    save(ROOT/'coverage.json',{'splits':coverage,'unit_count':len(pool),
         'count_basis':'30 original passage units,15 source keys; not30 independent judgments.',
         'old14_accepted_uses_unchanged':sum(map(len,old_accepted.values())),
         'new_label_known':sum(r['known'] for r in labels.values()),
         'new_label_unknown':sum(r['unknown'] for r in labels.values()),
         'new_label_isolated':sum(r['isolated'] for r in labels.values()),
         'new_label_classes':dict(known_classes),'isolation_reasons':dict(isolated_reasons),
         'graphs_built':len(graphs), 'new_training_cases_labelled':0,
         'new_conditions':58,'total_source_condition_proposals':115,
         'reference_role':'MODEL_GENERATED_SOURCE_ANCHOR_CHECKED; NOT_HUMAN_GOLD',
         'new_label_semantic_review':'NOT_COMPLETED; no automatic acceptance into frozen training supervision'})

    # Recheck exact provenance, without semantic annotation or altering ranges.
    from legal_bench.rules_verdict_v1.source_identity_v2 import validate_view
    source_checks=[]
    for row in manifest['cases']:
        if 'allowed_source' not in row:continue
        view=read(row['allowed_source'])
        if 'full_source' in row:
            mapping=validate_view(view,read(row['full_source']))
            kind='FULL_RENDERING_AND_EXACT_SUBSTRING_PROVENANCE_CHECKED'
        else:
            inherited=read(row['inherited_view'])
            assert view['segments']==inherited['segments']
            mapping=[];kind='INHERITED_APPROVED_VIEW_SEGMENTS_UNCHANGED'
        assert digest(row['allowed_source'])==row['allowed_sha256']
        source_checks.append({'case_id':row['case_id'],'split':row['split'],
            'allowed_source':row['allowed_source'],'allowed_sha256':digest(row['allowed_source']),
            'segments':len(view['segments']),'provenance_records':len(mapping),
            'check':kind,'scope_review':'Explicit saved ranges exclude target decisive reasoning; model-assisted, not independently validated.'})
    roles={};reserved=set(read(ROOT.parent/'authority-pool/manifest.json')['reserved_authority_case_ids'])
    for row in manifest['cases']:
        group=row['group_id'];assert group not in roles or roles[group]==row['split'];roles[group]=row['split']
        assert str(row['case_id']) not in reserved
    tasks=read(ROOT/'prepared-task-ledger.json')
    role_by_id={r['case_id']:r['split'] for r in manifest['cases']}
    for task in tasks:
        assert role_by_id[task['case_id']]=='TRAIN'
        assert digest(task['path'])==task['sha256']
    save(ROOT/'source-and-isolation-checks.json',{'source_checks':source_checks,
         'known_group_cross_split':False,'reserved_authority_target_overlap':[],
         'sealed_model_tasks':0,'task_hashes_unchanged':True,
         'broader_association':'UNKNOWN_BEYOND_CHECKED_PARTIES_AND_DOCKET; no claim of proven independence',
         'not_proved':'Hashes/addresses do not establish legal relevance, annotation correctness or complete absence of hidden associations.'})
    save(ROOT/'training-gate.json',{'open':False,'registered_train':coverage['TRAIN']['registered_cases'],
         'registered_dev':coverage['DEVELOPMENT']['registered_cases'],
         'registered_sealed':coverage['SEALED_TEST']['registered_cases'],
         'target_train':30,'target_sealed':10,
         'provisional_label_graph_pairs':coverage['TRAIN']['label_graph_interface_paired'],
         'accepted_30pool_training_cases':0,
         'reasons':['TRAIN source count below30','3 TRAIN and2 SEALED source allocation targets unmet',
                    'New case graph/label outputs not captured','New16 semantic source review incomplete',
                    'Development new16 coverage not yet prepared'],
         'training_runs':0,'new_legal_answers':0,'methods':['S','B','C'],'unknown_and_unmarked_not_negative':True})
    code=['scripts/rgcn09_continuation.py','scripts/rgcn09_import.py','scripts/rgcn09_finalize.py',
          'scripts/rgcn09_labels.py','scripts/rgcn09_authorities.py',
          'legal_bench/rules_verdict_v1/rgcn_development_v3.py',
          'legal_bench/rules_verdict_v1/rgcn_use_v1.py','tests/test_rgcn09_continuation.py']
    hashes={p:digest(p) for p in code}
    for path in code:
        dest=ROOT/'final-code-freeze'/path;dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():assert dest.read_bytes()==Path(path).read_bytes()
        else:shutil.copyfile(path,dest)
    frozen=read(ROOT/'input-code-freeze.json')['files']
    changed={p:{'initial':old,'final':digest(p)} for p,old in frozen.items() if Path(p).exists() and digest(p)!=old}
    save(ROOT/'final-data-freeze.json',{'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
         'branch':subprocess.check_output(['git','branch','--show-current'],text=True).strip(),
         'code':hashes,'initial_freeze_differences':changed,
         'difference_scope':'Importer gained unchanged-text wrapper parsing and30-candidate numeric packaging. Legal label/graph semantics unchanged; synthetic import tests added. Initial freeze preserved.',
         'files':{str(p):digest(p) for p in sorted(ROOT.rglob('*')) if p.is_file() and not any(x in p.parts for x in ('web','documents','final-code-freeze')) and not p.name.startswith('open') and p.name!='final-data-freeze.json'},
         'training':False,'publication':'LOCAL_ONLY_NO_COMMIT_NO_PUSH'})
    print(json.dumps({'confirmed_submissions':confirmed,'uncertain_sends':uncertain,'task_states':counts,
           'registered':{k:v['registered_cases'] for k,v in coverage.items()},
           'labels':len(labels),'graphs':len(graphs),'provisional_pairs':coverage['TRAIN']['label_graph_interface_paired']},indent=2))


if __name__=='__main__':
    finish()
