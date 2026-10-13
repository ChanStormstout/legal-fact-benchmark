#!/usr/bin/env python3
"""One cached impact audit and immutable carry-forward; no LLM or reference repair."""
import collections,copy,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import proof_local_refs_v19 as entry
from legal_bench.proof_carrying import local_pipeline_v19_types as prior
from legal_bench.proof_carrying import local_pipeline_v19_refs as pipe
from legal_bench.proof_carrying.source_contract_v19 import convert as prior_convert
from legal_bench.proof_carrying.reference_addresses_v19 import audit,convert,contract
from legal_bench.proof_carrying.local_checker_v19_refs import check,check_import
from legal_bench.proof_carrying.p_monitor_v19_refs import streak
PARENT=ROOT/'outputs/proof-local-pipeline-v19/continuation-02'

def copy_file(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if entry.sha(source)!=entry.sha(target):raise ValueError('CARRY_FILE_MISMATCH:'+str(target))
    else:shutil.copy2(source,target)

def prepare():
    # Last call must be saved and scheduler actually stopped, not merely marked.
    proc=subprocess.run(['ps','-p','87390','-o','pid=,command='],capture_output=True,text=True)
    if proc.stdout.strip():raise ValueError('PRIOR_PROCESS_STILL_ACTIVE; wait for saved boundary')
    cfg=entry.read(PARENT/'freeze/protocol.json')
    for name,h in cfg['code_hashes'].items():
        if entry.sha(ROOT/name)!=h:raise ValueError('FROZEN_PARENT_CHANGED:'+name)
    costs=[];copied=[];guard=[]
    for slot in cfg['local_generation_slots']:
        d=PARENT/slot['dest'];run=d/'run.json'
        if (d/'start.json').exists() and not run.exists():raise ValueError('UNCERTAIN_CALL_NOT_RESUBMITTED:'+slot['dest'])
        if not run.exists():continue
        row=entry.read(run)
        if row.get('model_called') is False:continue
        if not (d/'start.json').exists():raise ValueError('MISSING_ACTUAL_START:'+slot['dest'])
        # Old D is incompatible with current check view; retain cost and original,
        # carry its recorded dependency skip instead of generating it again.
        if slot['role']!='P' and slot['role'] not in ('A','B','C'):continue
        for f in d.iterdir():
            if f.is_file():copy_file(f,entry.OUT/slot['dest']/f.name)
        costs.append({'dest':slot['dest'],'role':slot['role'],'run_status':row['run_status'],'elapsed_seconds':row.get('elapsed_seconds',0),'provenance':str(d.relative_to(ROOT)),'run_sha256':entry.sha(run)})
        copied.append({'dest':slot['dest'],'raw_sha256':entry.sha(d/'raw-response.txt'),'parsed_sha256':entry.sha(d/'parsed.json') if (d/'parsed.json').exists() else None,'production_version':entry.read(d/'production-version.json')['version'] if slot['role']=='P' else 'OLD_COMPATIBLE_FINAL_PENDING_EXACT_PROMPT_CHECK','no_regeneration':True})
    # Preserve costs of every historical call, including the old D result.
    by_dest={r['dest']:r for r in cfg['carried_cost']['calls']}
    by_dest.update({r['dest']:r for r in costs})
    allcost=list(by_dest.values())
    for slot in cfg['local_generation_slots']:
        if slot['role']!='P':continue
        d=entry.OUT/slot['dest']
        if (d/'start.json').exists() and (d/'run.json').exists():guard.append({'dest':slot['dest'],'run_status':entry.read(d/'run.json')['run_status']})
    seeded=next(i for i,row in enumerate(guard) if row['dest']=='local/1066467/P01')
    rolling=streak(guard[seeded:])
    web_ledger=PARENT/'web/call-ledger.jsonl'
    web_events=[json.loads(line) for line in web_ledger.read_text().splitlines() if line] if web_ledger.exists() else []
    new_web={e.get('web_task_number',e.get('task_count_consumed')) for e in web_events if e.get('event')=='SUBMITTED'}
    carried={'calls':allcost,'P_calls':sum(c['role']=='P' for c in allcost),'final_calls':sum(c['role']!='P' for c in allcost),'P_seconds':sum(c['elapsed_seconds'] or 0 for c in allcost if c['role']=='P'),'final_seconds':sum(c['elapsed_seconds'] or 0 for c in allcost if c['role']!='P'),'web_calls':cfg['carried_cost']['web_calls']+len(new_web),'fits':0,'budget_reset':False}
    cfg['carried_cost']=carried;cfg['version']='V19_4';cfg['production_policy']={'cached_P':'V19_1/V19_2 original bytes with deterministic valid-reference adapter, invalid references remain rejected','remaining_P':'V19_4 typed transport','whole_batch_uniform_production_contract':False,'historical_calls_counted':True,'no_completed_P_rerun':True};cfg['checking_policy']='V19_REFERENCE_1 + unchanged V19_OBJECT_TYPES_1';cfg['reference_contract']=contract()
    # Record old D skip unchanged; it is never a new answer.
    oldd=PARENT/'local/136109/D'
    if oldd.exists():
        for f in oldd.iterdir():
            if f.is_file():copy_file(f,entry.OUT/'local/136109/D'/f.name)
    for f in (PARENT/'freeze').iterdir():
        if f.is_file() and f.name not in ('protocol.json',):copy_file(f,entry.OUT/'freeze'/f.name)
    for folder in ['web/labels','web/frozen-references','private/frozen-references','web/submitted-tasks']:
        source=PARENT/folder
        if source.exists():
            for f in source.rglob('*'):
                if f.is_file():copy_file(f,entry.OUT/folder/f.relative_to(source))
    # Ledger stays original as provenance, no invented submissions or resets.
    if web_ledger.exists():copy_file(web_ledger,entry.OUT/'web/call-ledger.jsonl')
    evidence={'at':entry.utc(),'prior_process_pid':87390,'process_no_longer_running':True,'marker':entry.read(PARENT/'PAUSE_REQUESTED.json'),'last_P':guard[-1],'remaining_next_P':next(s['dest'] for s in cfg['local_generation_slots'] if s['role']=='P' and not (entry.OUT/s['dest']/'run.json').exists()),'rolling_guard_preserved':rolling,'original_protocol_sha256':entry.sha(PARENT/'freeze/protocol.json'),'old_outputs_preserved':True}
    entry.save(entry.OUT/'startup/pause-evidence.json',evidence);entry.save(entry.OUT/'startup/carried-cost.json',carried);entry.save(entry.OUT/'startup/cache-provenance.json',copied)
    entry.save(entry.OUT/'freeze/reference-contract.json',contract());entry.save(entry.OUT/'startup/pending-protocol.json',cfg)
    entry.save(entry.OUT/'remaining-tasks.json',{'P':[s for s in cfg['local_generation_slots'] if s['role']=='P' and not (entry.OUT/s['dest']/'run.json').exists()],'final':[s for s in cfg['local_generation_slots'] if s['role']!='P' and not (entry.OUT/s['dest']/'run.json').exists()],'no_retries_or_added_slots':True,'carry_guard':rolling})
    print(json.dumps({'carried_cost':{k:v for k,v in carried.items() if k!='calls'},'paused':evidence['last_P'],'next':evidence['remaining_next_P']}))

def replay():
    cfg=entry.read(entry.OUT/'startup/pending-protocol.json');cases=[];parts=[];bad=[];compat=[];retained=0;rawuses=0
    original_protocol=entry.protocol;entry.protocol=lambda:cfg
    try:
        for cid in cfg['TRAIN']+cfg['DEV']:
            f=entry.fixture(cid);beforeparts=[];afterparts=[];caseerrors=[]
            for slot in [s for s in cfg['local_generation_slots'] if s['role']=='P' and s['case_id']==cid]:
                d=entry.OUT/slot['dest']
                if not (d/'run.json').exists():continue
                if entry.read(d/'run.json')['run_status']!='OK':beforeparts.append((slot['part']['id'],None));afterparts.append((slot['part']['id'],None));continue
                raw=entry.read(d/'parsed.json');v=entry.read(d/'production-version.json')['version'];view={**f['case'],'segments':[s for s in f['case']['segments'] if s['id'] in slot['part']['source_ids']]}
                checks=audit(raw,view,v);invalid=[x for x in checks if x['status'] not in ('VALID','SOURCE_REQUIRES_LEGACY_RESOLUTION')]
                bad.extend({'case_id':cid,'part':slot['part']['id'],**x} for x in invalid);caseerrors+=invalid
                nrecord=sum(len(u['records']) for u in raw['analyses']);nuse=sum(len(u['uses']) for u in raw['analyses']);retained+=nrecord;rawuses+=nuse
                transformed,ledger=convert(raw,view,v);ind=check_import(raw,transformed,view,v)
                if ind['status']!='OK':raise ValueError('INDEPENDENT_IMPORT:'+cid+':'+str(ind['errors']))
                before,_=prior_convert(raw,view,v=='V19_2');beforeparts.append((slot['part']['id'],before));afterparts.append((slot['part']['id'],transformed))
                same_source_lists=sum(bool(use['records']) and use['records']==[ref for w in use['witnesses'] for ref in w['refs']] and any(type(index) is int and index>len(unit['records']) for index in use['records']) for unit in raw['analyses'] for use in unit['uses'])
                row={'case_id':cid,'part':slot['part']['id'],'production_version':v,'source_choices_repeated_verbatim_in_record_field':same_source_lists,'raw_records_saved':nrecord,'raw_uses_saved':nuse,'invalid_references':dict(collections.Counter(x['namespace']+':'+x['status'] for x in invalid)),'raw_sha256':entry.sha(d/'parsed.json'),'independent_import':ind['status']}
                parts.append(row);entry.save(entry.OUT/'private/raw-reference-audit'/cid/(slot['part']['id']+'.json'),{'summary':row,'all_raw_references':checks,'ledger':ledger})
            if not afterparts or not any(p is not None for _,p in afterparts):continue
            beforep,_=prior.merge_parts(beforeparts);afterp,_=pipe.merge_parts(afterparts);old=prior.apply_connection_decisions(f['case'],f['rules'],beforep);new=pipe.apply_connection_decisions(f['case'],f['rules'],afterp);ind=check(f['case'],f['rules'],afterp,None,new)
            if ind['status']!='OK' or len(afterp['records'])!=len(beforep['records']):raise ValueError('CACHE_ENTRY_RECOMPUTATION_FAILED:'+cid)
            changes=[]
            for a,b in zip(old['checks'],new['checks']):
                if any(a[k]!=b[k] for k in ('errors','disposition','full_basis_eligible')):changes.append({'id':b['connection_id'],'before':a,'after':b})
            pchanges=[{'id':a['id'],'before':a['conditional_state'],'after':b['conditional_state']} for a,b in zip(old['premise_judgments'],new['premise_judgments']) if a['conditional_state']!=b['conditional_state']]
            rchanges=[{'rule':a['rule_id'],'before':a['conditional_result'],'after':b['conditional_result']} for a,b in zip(old['conditional_rules'],new['conditional_rules']) if a['conditional_result']!=b['conditional_result']]
            entry.save(entry.OUT/'private/replay'/cid/'before.json',old);entry.save(entry.OUT/'private/replay'/cid/'after.json',new);entry.save(entry.OUT/'private/replay'/cid/'independent.json',ind)
            entry.consolidate(cid)
            data=entry.read(entry.OUT/'inputs'/cid/'learner-inputs.json') if (entry.OUT/'inputs'/cid/'learner-inputs.json').exists() else pipe.learner_inputs(f['case'],f['rules'],afterp)
            labels=entry.OUT/'web/labels'/cid/'parsed.json'
            if labels.exists():
                ref=entry.read(labels);rows=(ref or {}).get('connections',[])
                for label in rows:
                    k=int(label['connection_id'][1:])-1
                    same=0<=k<len(beforep['uses']) and beforep['uses'][k]==afterp['uses'][k]
                    verdict=entry.label_admissibility(label,set(data['common_material_manifest']['saved_source_ids']),pipe.source_match(label,pipe.sources(f['case'])))
                    compat.append({'case_id':cid,'use_id':label['connection_id'],'original_label_preserved':True,'same_semantic_use_and_bindings':same,'source_visible':set(label.get('mandatory_basis_refs',[]))<=set(data['common_material_manifest']['saved_source_ids']),'supervision_compatible':same and verdict['supervised'],'reason':verdict['reason'],'reference_is_not_input':True})
            row={'case_id':cid,'raw_records_saved_and_retained':len(afterp['records']),'connections':len(new['checks']),'raw_reference_errors':dict(collections.Counter(x['namespace']+':'+x['status'] for x in caseerrors)),'uses_blocked_by_record_reference':sum('RECORD_INDEX_INVALID' in x['errors'] for x in new['checks']),'uses_blocked_by_object_reference':sum('OBJECT_INDEX_INVALID' in x['errors'] for x in new['checks']),'structurally_valid_connections':sum(not x['errors'] for x in new['checks']),'conditionally_available_connections':sum(x['disposition']=='CONDITIONALLY_AVAILABLE_USE' for x in new['checks']),'premise_states':dict(collections.Counter(x['conditional_state'] for x in new['premise_judgments'])),'rule_states':dict(collections.Counter(x['conditional_result'] for x in new['conditional_rules'])),'connection_changes':changes,'premise_state_changes':pchanges,'rule_state_changes':rchanges,'independent_status':ind['status'],'no_guessed_old_reference_repair':True}
            cases.append(row)
    finally:entry.protocol=original_protocol
    summary={'at':entry.utc(),'scope':'COMPLETED_CURRENT_FIXED_P_ONLY_NO_NEW_DIAGNOSTIC_CALL','readable_P_parts':len(parts),'cases':cases,'part_summaries':parts,'original_records_saved_and_retained':retained,'raw_connections_retained':rawuses,'invalid_reference_occurrences':dict(collections.Counter(x['namespace']+':'+x['status'] for x in bad)),'invalid_occurrences_not_independent_legal_errors':True,'ambiguous_in_range_numeric_namespaces':'Cannot infer intended namespace or index base; never shifted/repaired','restored_old_connections_by_guessing':0,'changed_connection_dispositions':sum(len(x['connection_changes']) for x in cases),'changed_premise_states':sum(len(x['premise_state_changes']) for x in cases),'changed_rule_states':sum(len(x['rule_state_changes']) for x in cases),'model_or_legal_improvement_claimed':False,'references_used_in_runtime':False}
    entry.save(entry.OUT/'impact-summary.json',summary);entry.save(entry.OUT/'private/all-invalid-raw-references.json',bad);entry.save(entry.OUT/'label-compatibility.json',compat)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('cases','part_summaries')},indent=2))

if __name__=='__main__':
    if sys.argv[-1]=='prepare':prepare()
    elif sys.argv[-1]=='replay':replay()
    else:raise SystemExit('choose prepare or replay; neither generates an LLM response')
