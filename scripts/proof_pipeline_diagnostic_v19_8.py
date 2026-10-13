#!/usr/bin/env python3
"""Bounded local diagnostic/repair replay. No model, training, web or API calls."""
import argparse,copy,hashlib,json,subprocess,sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import proof_pipeline_contract_v19_8 as entry,proof_pipeline_contract_v19_7 as old_entry
from legal_bench.proof_carrying import local_pipeline_v19_8 as pipe,local_pipeline_v19_7 as old_pipe
from legal_bench.proof_carrying import final_delivery_v19_8 as delivery
from legal_bench.proof_carrying.rule_contracts_v19_7 import digest
from tests.test_pipeline_contract_v19_7 import fixture
OUT=ROOT/'outputs/proof-pipeline-diagnostic-repair-v19-8';OLD=ROOT/'outputs/proof-pipeline-contract-v19-7'
NEW_CODE=['legal_bench/proof_carrying/'+x for x in ('local_pipeline_v19_8.py','local_checker_v19_8.py','rule_contracts_v19_8.py','presentation_v19_8.py','final_delivery_v19_8.py')]+['scripts/proof_pipeline_contract_v19_8.py','scripts/proof_pipeline_diagnostic_v19_8.py','tests/test_pipeline_diagnostic_v19_8.py']
CONFIG={'context_budget':65536,'max_output_tokens':8192,'template_margin':256}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):return entry.save(OUT/path,value)
def counts(rows,key):return dict(Counter(x[key] for x in rows))
def accepted(c,r,x,old=False):
    module,pipeline=(old_entry,old_pipe) if old else (entry,pipe)
    part={'id':'P01','rule_ids':[q['id'] for q in r],'source_ids':[s['id'] for s in c['segments']]}
    return module.process_saved(c,r,part,json.dumps(x),pipeline.schema(r,c),'V19_7','OK')

def acceptance():
    commands=[sys.executable,'-m','unittest','tests.test_pipeline_diagnostic_v19_8','tests.test_contract_integrity_v19_6','tests.test_reference_addresses_v19','-v']
    result=subprocess.run(commands,cwd=ROOT,capture_output=True,text=True)
    entry.text(OUT/'engineering/tests.txt',result.stdout+result.stderr)
    save('engineering/tests.json',{'command':commands,'returncode':result.returncode,'tests':43,'model_calls':0,'mock_runner_only':True})
    if result.returncode:raise RuntimeError('ENGINEERING_TEST_FAILURE')
    c,r,x=fixture();faults=[]
    for name,collection,key,value in [('use binding','checks','binding',{'R1::tenant':999999}),
            ('use direction','checks','direction','OPPOSE'),('judgment basis','premise_judgments','basis','Invented'),
            ('judgment gaps','premise_judgments','gaps',['Invented'])]:
        pair=[]
        for old in (True,False):
            module=old_pipe if old else pipe;original=module.apply_connection_decisions
            def corrupt(*args):
                audit=original(*args);audit[collection][0][key]=value;return audit
            with patch.object(module,'apply_connection_decisions',corrupt):v=accepted(c,r,x,old)
            pair.append({'version':'V19_7' if old else 'V19_8','status':v['contract_status'],'checker':v.get('independent_check',{}).get('status')})
        faults.append({'fault':name,'type':'SYNTHETIC_IN_MEMORY_CORRUPTION_NOT_OBSERVED_NATURAL_LOSS','results':pair})
    rr=copy.deepcopy(r);rr[0]['premises'][0]['input_contract']['whole_basis_statuses']=[]
    faults.append({'fault':'explicit empty whitelist','type':'SYNTHETIC_CONTRACT_CONTROL','results':[
        {'version':'V19_7' if old else 'V19_8','whole_basis_eligible':accepted(c,rr,x,old)['conditional_audit']['checks'][0]['full_basis_eligible']} for old in (True,False)]})
    save('engineering/fault-reproductions.json',faults)

def freeze():
    old=json.loads((OLD/'freeze/protocol.json').read_text())
    code=sorted(set(old['code_hashes'])|set(NEW_CODE)|{'legal_bench/proof_carrying/final_delivery_v19_7.py','scripts/proof_pipeline_delivery_v19_7.py'})
    hashes={f:sha(ROOT/f) for f in code};tasks=[]
    for t in old['tasks']:
        f,part=entry.context(t);d=OLD/'runs'/t['case_id']/t['part']
        tasks.append({'case_id':t['case_id'],'part':t['part'],'original_generation_version':'V19_7',
            'raw':str((d/'raw-response.txt').relative_to(ROOT)),'raw_sha256':sha(d/'raw-response.txt'),
            'schema_sha256':sha(d/'schema.json'),'case_sha256':digest(f['case']),'rules_sha256':digest(f['rules']),
            'part_contract':part})
    save('freeze/protocol.json',{'processing_version':pipe.VERSION,'frozen_at':entry.utc(),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'code_hashes':hashes,'tasks':tasks,'final_preparation_config':CONFIG,
        'P_prompt_schema_and_raw_unchanged':True,'role_types_not_identity':True,'closed_status_whitelist':True,
        'FALSE_policy':'Explicit complete model FALSE with at least one fixed necessary component and usable OPPOSE basis; not evidence voting or legal verification.',
        'identity_policy':'Distinct local declarations are unresolved identity, not automatic inequality; no equality inferred from names/types/null.',
        'ANY_policy':'Each independent branch keeps its own binding; positive branch does not depend on identity with unrelated alternative.',
        'presentation_policy':'Exact repeated long strings pooled; JSON roundtrip required. Full allowed source and counterevidence retained.',
        'evaluation':'Separate engineering fault injection, real unchanged-cache effects, old model-assisted semantic review and unrun final-answer effects.',
        'new_model_calls':0,'training':0,'TEST_SEALED_read':False,'no_commit_or_push':True,'stop':'After one replay and concentrated review; no new generation.'})
    for f in code:entry.text(OUT/'freeze/code'/f,(ROOT/f).read_text())

def frozen():
    protocol=entry.read(OUT/'freeze/protocol.json')
    assert all(sha(ROOT/f)==h for f,h in protocol['code_hashes'].items()),'Frozen code changed'
    return protocol

def replay():
    protocol=frozen();summaries=[];capacities=[]
    from transformers import AutoTokenizer
    model_path=(ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip()
    tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True)
    for t in protocol['tasks']:
        f,part=entry.context({'case_id':t['case_id'],'part_contract':t['part_contract']});d=OLD/'runs'/t['case_id']/t['part']
        assert sha(d/'raw-response.txt')==t['raw_sha256']
        raw=(d/'raw-response.txt').read_text();schema=entry.read(d/'schema.json');receipt=entry.read(d/'run.json')
        before=entry.read(d/'entry-audit.json')
        result=entry.process_saved(f['case'],f['rules'],part,raw,schema,'V19_7',receipt['run_status'])
        if result['contract_status']!='CONTRACT_VALID':raise RuntimeError('Real cache checker failed:'+str(result.get('independent_check')))
        save(Path('replay')/t['case_id']/'entry.json',result)
        save(Path('replay')/t['case_id']/'old-entry.json',before)
        changes=[]
        old_by={j['id']:j for j in before['conditional_audit']['premise_judgments']}
        for j in result['conditional_audit']['premise_judgments']:
            previous=old_by[j['id']]
            if previous['conditional_state']!=j['conditional_state'] or previous['errors']!=j['errors']:
                changes.append({'premise':j['premise'],'model_state_unchanged':j['model_state'],
                    'before':previous['conditional_state'],'after':j['conditional_state'],
                    'old_errors':previous['errors'],'new_errors':j['errors'],'model_basis_unchanged':j['basis']==previous['basis']})
        audit=result['conditional_audit'];old_audit=before['conditional_audit']
        summaries.append({'case_id':t['case_id'],'raw_sha256':t['raw_sha256'],'processing_version':pipe.VERSION,
            'production_version':'V19_7','formal_P_unchanged':result['formal_answer']==entry.read(d/'parsed.json'),
            'coverage':result['coverage'],'records_saved':len(result['canonical_P']['records']),
            'old_use_dispositions':counts(old_audit['checks'],'disposition'),'new_use_dispositions':counts(audit['checks'],'disposition'),
            'old_conditional_states':counts(old_audit['premise_judgments'],'conditional_state'),
            'new_conditional_states':counts(audit['premise_judgments'],'conditional_state'),
            'judgment_changes':changes,'old_rule_trace_count':len(old_audit['conditional_rules']),
            'new_rule_trace_count':len(audit['conditional_rules']),'rule_coverage':audit['rule_coverage'],
            'new_rule_results':counts(audit['conditional_rules'],'conditional_result'),
            'semantic_approval':False,'complete_legal_answer_run':False})
        # Prepare real A/C/D; E/F/G have no new compatible trained predictions.
        for method in ('A','C','D'):
            value=delivery.task(f['case'],f['rules'],result,method,part,full_rules=f['full_rules'])
            dest=OUT/'final-material'/t['case_id']/method
            entry.save(dest/'task.json',value);entry.text(dest/'prompt.txt',value['prompt']);entry.save(dest/'schema.json',value['schema'])
            cap=delivery.capacity(value,tokenizer,CONFIG)
            capacities.append({'case_id':t['case_id'],'method':method,**cap,
                'prompt_characters':len(value['prompt']),'input_sha256':value['input_sha256'],
                'presentation_audit':value['presentation_audit'],'source_count':len(value['source_ids']),
                'source_alias_count':len(value['P_source_aliases']),'generated':False})
    save('comparison.json',summaries);save('final-capacity.json',{'rows':capacities,'tokenizer_revision':'8b2b98c00a6b4d291155e4890773ca8f769aee53','thinking':False,'local_context_budget_not_native_model_limit':True,'model_loaded':False,'model_calls':0})

def review():
    frozen();old=entry.read(OLD/'source-review.json');cases=[]
    for review_case in old['cases']:
        t=next(t for t in entry.read(OUT/'freeze/protocol.json')['tasks'] if t['case_id']==review_case['case_id'])
        f,part=entry.context({'case_id':t['case_id'],'part_contract':t['part_contract']})
        result=entry.read(OUT/'replay'/t['case_id']/'entry.json');segments={s['id']:s for s in f['case']['segments']}
        judgments={j['premise']:j for j in result['conditional_audit']['premise_judgments']}
        items=[]
        for item in review_case['items']:
            evidence=[{'id':ref,'line':segments[ref].get('original_line'),'text':segments[ref]['text']} for ref in item['source_refs'] if ref in segments]
            items.append({**item,'review_origin':'V19_7_EXISTING_MODEL_ASSISTED_REVIEW_RECHECKED_ON_UNCHANGED_P_AND_SOURCE',
                'located_allowed_sources':evidence,'current_conditional_states':{pid:judgments[pid]['conditional_state'] for pid in item.get('premises',[]) if pid in judgments},
                'correction':'Missing object links now retain IDENTITY_PENDING routes; separate local IDs do not establish explicit incompatibility.' if item['id'].endswith('cross-identities') else None,
                'not_used_in_runtime_input_or_acceptance':True})
        cases.append({'case_id':t['case_id'],'items':items,'legal_final_evaluation':'NOT_RUN'})
    save('source-review.json',{'review_kind':'ONE_CONCENTRATED_MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
        'natural_model_errors_not_corrected':True,'cases':cases,'new_review_model_calls':0,
        'source_review_does_not_approve_model_semantics':True})

def verify_preserved():
    original=entry.read(OUT/'startup/preserved.json');changed=[p for p,h in original.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
    current=frozen()
    save('preservation.json',{'checked_files':len(original),'changed':changed,'frozen_code_files':len(current['code_hashes']),
        'head_unchanged':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==current['head']})
    assert not changed,'Historical bytes changed'

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['acceptance','freeze','replay','review','preservation'])
    globals()[{'preservation':'verify_preserved'}.get(ap.parse_args().phase,sys.argv[1])]()
