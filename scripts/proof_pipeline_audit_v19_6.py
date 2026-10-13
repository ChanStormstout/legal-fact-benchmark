#!/usr/bin/env python3
"""One deterministic audit of the two saved API proposals; never runs models.

Fault injections are synthetic controls, not natural errors or new results.
Production code, raw answers, labels and frozen methods remain untouched.
"""
import copy
import hashlib
import io
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.proof_together_diagnostic import read,save,sha,utc,stream_event
from scripts.proof_contract_integrity_v19_6 import process_saved
from legal_bench.proof_carrying import local_pipeline_v19_6 as pipe,local_checker_v19_6 as checker
from legal_bench.proof_carrying.schema_contract_v19_6 import loads,violations
from legal_bench.proof_carrying.object_types_v19 import compare as types

OUT=ROOT/'outputs/proof-pipeline-audit-v19-6'
API=ROOT/'outputs/proof-together-contract-v19-6'
BASE=ROOT/'outputs/proof-local-pipeline-v19/continuation-04'


def context(task):
    fixture=read(BASE/'preparation/inputs'/task['case_id']/'fixture.json');part=task['part_contract']
    rules=[r for r in fixture['rules'] if r['id'] in part['rule_ids']]
    view={**fixture['case'],'segments':[s for s in fixture['case']['segments'] if s['id'] in part['source_ids']]}
    d=API/'runs'/task['case_id']/task['part']
    return fixture,part,rules,view,d


def inspect(task):
    f,part,rules,view,d=context(task);raw_text=(d/'raw-response.txt').read_text();raw=loads(raw_text)
    schema=read(d/'schema.json');entry=read(d/'entry-audit.json');request=read(API/task['task']/'request.json')
    content=io.StringIO();reasoning=io.StringIO();receipt={};chunks=[]
    for line in (d/'raw-sse.txt').read_text().splitlines():
        if line.startswith('data:'):chunks.append(line[5:].lstrip())
        elif chunks:stream_event('\n'.join(chunks),content,reasoning,receipt);chunks=[]
    if chunks:stream_event('\n'.join(chunks),content,reasoning,receipt)
    assert content.getvalue()==raw_text
    assert raw==read(d/'parsed.json')
    assert request['messages'][0]['content']==pipe.proposal_prompt(f['case'],f['rules'],part)
    assert schema==pipe.schema(rules,view)
    directory=pipe.source_directory(view)
    assert read(API/task['task']/'source-directory.json')==directory
    assert all(row['choice']+' | '+row['address']+'\n'+row['text'] in request['messages'][0]['content'] for row in directory)
    converted,ledger=pipe.convert(raw,view,pipe.VERSION)
    canonical,_=pipe.merge_parts([(part['id'],converted)])
    assert canonical==entry['canonical_P']
    original_records=[r for unit in raw['analyses'].values() for r in unit['records']]
    assert len(original_records)==len(canonical['records'])
    assert [r['proposition'] for r in original_records]==[r['text'] for r in canonical['records']]
    check=entry['conditional_audit'];m=entry['learner_inputs']['common_material_manifest']
    assert m['actual_encoded_source_ids'] is None
    statuses=Counter(x['status'] for x in ledger if x.get('namespace') in ('EV','OBJ','USE'))
    fields={p['id']:{'text':p['text'],'allowed_statuses':p.get('allowed_statuses',[]),
             'explicit_stage':p.get('stage'),'explicit_court':p.get('court_level'),
             'role_types':p.get('variables',{})} for r in rules for p in r['premises']}
    result={'case_id':task['case_id'],'part':part['id'],'material_identity':{
        'prompt_sha256':sha(d/'prompt.txt'),'schema_sha256':sha(d/'schema.json'),
        'source_count':len(directory),'all_source_fragments_present':True,
        'SSE_equals_raw_equals_parsed':True,'record_count_unchanged_after_merge':len(original_records),
        'record_interpretations_unchanged':True},'schema_violations':violations(raw,schema),
        'coverage':entry['coverage'],'dynamic_reference_statuses':dict(statuses),
        'use_dispositions':dict(Counter(x['disposition'] for x in check['checks'])),
        'use_errors':dict(Counter(e for x in check['checks'] for e in x['errors'])),
        'binding_type_statuses':dict(Counter(t['status'] for x in check['checks'] for t in x['type_compatibility'])),
        'missing_role_judgments':sum(bool(x['missing_roles']) for x in entry['role_coverage']),
        'conditional_states':dict(Counter(x['conditional_state'] for x in check['premise_judgments'])),
        'rule_execution':[{k:r[k] for k in ('rule_id','operator','conditional_result','not_executed','inputs')} for r in check['conditional_rules']],
        'model_input':{'saved_source_fragments':len(m['saved_source_ids']),
            'encoding_status':m['encoding_status'],'actual_encoded_source_ids':None,
            'not_full_document_omission_detection':True,'relation_counts':entry['learner_inputs']['relation_counts'],
            'RULE_DEPENDENCY_edges':entry['learner_inputs']['relation_counts'].get('RULE_DEPENDENCY',0)},
        'fixed_premise_contracts':fields,'reference_used':False}
    save(OUT/'replay'/task['case_id']/'pipeline-audit.json',result)
    return result


def controls(task):
    f,part,rules,view,d=context(task);raw=loads((d/'raw-response.txt').read_text());schema=read(d/'schema.json')
    original=read(d/'entry-audit.json');results=[]
    def import_control(name,converted,data=raw):
        value=checker.check_import(data,converted,view,pipe.VERSION)
        results.append({'id':name,'kind':'SYNTHETIC_CONVERSION_FAULT','status':value['status'],'errors':value.get('errors',[])})
        return value
    converted,ledger=pipe.convert(raw,view,pipe.VERSION)
    changed=copy.deepcopy(converted);changed['analyses'].pop();import_control('DELETE_ANALYSIS',changed)
    changed=copy.deepcopy(converted);changed['analyses'][0]['records'][0]['stage']='wrong stage';import_control('ALTER_RECORD_STAGE',changed)
    changed=copy.deepcopy(converted);changed['analyses'][0]['uses'][0]['bindings'][0]['object']=2;import_control('ALTER_BINDING_INDEX',changed)
    changed=copy.deepcopy(converted);changed['analyses'][0]['uses'][0]['witnesses'][0]['quote']=changed['analyses'][0]['uses'][0]['witnesses'][0]['quote'][:30]
    import_control('SHORTEN_CODE_RESTORED_WITNESS',changed)
    with patch.object(pipe,'convert',return_value=(changed,ledger)):
        out=process_saved(f['case'],f['rules'],part,json.dumps(raw),schema,pipe.VERSION,'OK')
    results[-1].update(entry_contract=out['contract_status'],independent=out.get('independent_check',{}).get('status'))
    # A declared blocker is introduced only in the synthetic control. Then its
    # kind is silently corrupted during conversion. Nothing is written to raw P.
    data=copy.deepcopy(raw);data['analyses']['R03.P2']['judgments'][0]['necessary_limits'][0]['kind']='BLOCK_SCOPE'
    baseline=process_saved(f['case'],f['rules'],part,json.dumps(data),schema,pipe.VERSION,'OK')
    converted,ledger=pipe.convert(data,view,pipe.VERSION);changed=copy.deepcopy(converted)
    unit=next(u for u in changed['analyses'] if u['premise']=='R03.P2');unit['judgments'][0]['necessary_limits'][0]['kind']='NOTE'
    import_control('BLOCK_SCOPE_CHANGED_TO_NOTE',changed,data)
    with patch.object(pipe,'convert',return_value=(changed,ledger)):
        out=process_saved(f['case'],f['rules'],part,json.dumps(data),schema,pipe.VERSION,'OK')
    def state(value):return next(j['conditional_state'] for j in value['conditional_audit']['premise_judgments'] if j['premise']=='R03.P2')
    results[-1].update(entry_contract=out['contract_status'],independent=out['independent_check']['status'],
                       before_state=state(baseline),after_state=state(out))
    analysis=copy.deepcopy(original['conditional_audit']);analysis['conditional_rules']=[]
    value=checker.check(f['case'],rules,original['canonical_P'],None,analysis)
    results.append({'id':'DELETE_ALL_RULE_TRACES','kind':'SYNTHETIC_CHECK_OUTPUT_FAULT','status':value['status'],
                    'original_trace_count':len(original['conditional_audit']['conditional_rules']),'remaining_trace_count':0})
    converted,ledger=pipe.convert(raw,view,pipe.VERSION);merged,merge_ledger=pipe.merge_parts([(part['id'],converted)])
    changed=copy.deepcopy(merged);changed['records'].pop()
    with patch.object(pipe,'merge_parts',return_value=(changed,merge_ledger)):
        out=process_saved(f['case'],f['rules'],part,json.dumps(raw),schema,pipe.VERSION,'OK')
    results.append({'id':'DELETE_RECORD_DURING_MERGE','kind':'SYNTHETIC_MERGE_FAULT','entry_contract':out['contract_status'],
                    'independent':out['independent_check']['status'],'formal_present':out['formal_answer'] is not None,
                    'before_records':len(merged['records']),'after_records':out['conditional_audit']['raw_records_retained']})
    results.append({'id':'EXPLICIT_TYPE_CONFLICT','kind':'DETERMINISTIC_TYPE_CONTROL','result':types('PERSON','PROPERTY')['status']})
    results.append({'id':'FREE_DESCRIPTION_NOT_STRING_CONFLICT','kind':'DETERMINISTIC_TYPE_CONTROL','result':types('direct landlord','demised premises')['status']})
    # Existing use predictions may block an erroneous path; they do not correct
    # whole-premise FALSE/TRUE, objects or missing opposing source links.
    task2=read(API/'freeze/protocol.json')['tasks'][1];f2,part2,rules2,_,d2=context(task2);entry2=read(d2/'entry-audit.json');p=entry2['canonical_P']
    decisions={'K%03d'%(i+1):u['self_assessment'] for i,u in enumerate(p['uses'])}
    altered=[]
    for i,u in enumerate(p['uses']):
        if u['premise']=='R6.P2':decisions['K%03d'%(i+1)]='UNSUPPORTED';altered.append('K%03d'%(i+1))
    audit=pipe.apply_connection_decisions(f2['case'],rules2,p,decisions)
    after=next(j['conditional_state'] for j in audit['premise_judgments'] if j['premise']=='R6.P2')
    results.append({'id':'USES_CAN_BLOCK_BUT_NOT_REWRITE_WHOLE_JUDGMENT','kind':'SYNTHETIC_PREDICTION_CONTROL_NOT_MODEL_RESULT',
        'altered_uses':altered,'original_state':'TRUE','after_state':after,'objects_or_truth_not_repaired':True,
        'independent_check':checker.check(f2['case'],rules2,p,decisions,audit)['status']})
    save(OUT/'deterministic-controls.json',{'controls':results,'natural_failure_count':0,
        'fault_injections_do_not_establish_occurrence_in_saved_answers':True,'production_code_unchanged':True})
    return results


def main():
    assert str(OUT.relative_to(ROOT)) in read(ROOT/'docs/repository-artifacts.json')['artifact_roots']
    cfg=read(API/'freeze/protocol.json');hashes=cfg['code_hashes']
    assert all(sha(ROOT/p)==h for p,h in hashes.items())
    preserved=read(ROOT/'outputs/proof-contract-integrity-v19-6/startup/preserved-hashes.json')
    preserved.update({str(p.relative_to(ROOT)):sha(p) for p in API.rglob('*') if p.is_file()})
    save(OUT/'private/workspace.json',{'HEAD':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
         'status':subprocess.check_output(['git','status','--short'],text=True).splitlines()})
    save(OUT/'frozen-audit-scope.json',{'at':utc(),'code_hashes':hashes,'diagnostic_script_sha256':sha(Path(__file__)),
         'preserved':preserved,'two_current_tasks':[(t['case_id'],t['part']) for t in cfg['tasks']],
         'no_calls_no_training_no_TEST_SEALED_no_production_modification':True})
    rows=[inspect(t) for t in cfg['tasks']];tests=controls(cfg['tasks'][0])
    save(OUT/'pipeline-summary.json',rows)
    assert all(sha(ROOT/p)==h for p,h in hashes.items())
    assert all(sha(ROOT/p)==h for p,h in preserved.items())
    save(OUT/'preservation.json',{'frozen_code_files':len(hashes),'all_code_unchanged':True,
         'historical_and_current_material_files':len(preserved),'all_material_unchanged':True,'calls':0,'fits':0})
    print(json.dumps({'tasks_audited':len(rows),'controls':len(tests),'unexpectedly_accepted_faults':[
         x['id'] for x in tests if x['kind'].startswith('SYNTHETIC') and (x.get('status')=='OK' or x.get('independent')=='OK')],
         'calls':0,'fits':0},ensure_ascii=False))


if __name__=='__main__':main()
