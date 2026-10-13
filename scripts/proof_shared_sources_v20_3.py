#!/usr/bin/env python3
"""Four explicitly authorized P reruns. No Q, training, scoring or full-batch resume."""
import argparse
import copy
import datetime
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from legal_bench.proof_carrying import shared_sources_v20_3 as transport
from legal_bench.proof_carrying.schema_contract_v19_6 import validate
from legal_bench.proof_carrying.artifact_state_v20_2 import immutable,freeze_files,verify_files,byte_hash,digest,paused
from scripts.proof_pipeline_contract_v19_8 import process_saved

OUT=ROOT/'outputs/proof-shared-sources-v20-3'
PARENT=ROOT/'outputs/proof-source-verification-v20/continuation-01'
REPAIR=ROOT/'outputs/proof-source-verification-repair-v20-2'
TASKS=[('569555','P01'),('1187427','P01'),('1954254','P01'),('1954254','P02')]

def read(p):return json.loads(Path(p).read_text())
def save(p,v):return immutable(p,v)
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def serialized(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'))

def prepare():
    if (OUT/'preparation/plan.json').exists():return read(OUT/'preparation/plan.json')
    verify_files(ROOT,read(REPAIR/'freeze/protocol.json'))
    policy=read(ROOT/'docs/repository-artifacts.json')
    assert str(OUT.relative_to(ROOT)) in policy['artifact_roots']
    old=read(PARENT/'freeze/protocol.json');preserved={}
    for base in (PARENT,REPAIR):
        preserved.update({str(p.relative_to(ROOT)):byte_hash(p) for p in base.rglob('*') if p.is_file()})
    preserved.update(old['code_hashes']);preserved.update(read(REPAIR/'freeze/protocol.json')['code_hashes'])
    save(OUT/'preserved-old-files.json',preserved)
    slots=[]
    sentence='records and objects cite only relevant unique refs; a witness selects ONE source address in its source field. Multiple discontinuous locations are separate witnesses, not a fabricated continuous quote.'
    replacement='records and objects cite only relevant source sets using ref_set. Witnesses select source_set and necessity; code restores a separate witness per source, including discontinuous locations. The shared-source transport instruction defines these field spellings.'
    for cid,part in TASKS:
        prior=PARENT/'local'/cid/part;dest=OUT/'preparation'/cid/part
        schema=read(prior/'schema.json');prompt=(prior/'prompt.txt').read_text();assert prompt.count(sentence)==1
        f=read(PARENT/'preparation'/cid/'fixture.json');assert f['case']['split']=='TRAIN'
        slot=next(copy.deepcopy(s) for s in old['slots'] if s['case_id']==cid and s['part']['id']==part)
        save(dest/'original-schema.json',schema);save(dest/'schema.json',transport.schema(schema));save(dest/'fixture.json',f)
        dest.mkdir(parents=True,exist_ok=True)
        (dest/'prompt.txt').write_text(transport.INSTRUCTION+'\n'+prompt.replace(sentence,replacement))
        save(dest/'old-task.json',{'old_run':str((prior/'run.json').relative_to(ROOT)),
            'old_prompt_sha256':byte_hash(prior/'prompt.txt'),'old_schema_sha256':byte_hash(prior/'schema.json'),
            'old_raw_sha256':byte_hash(prior/'raw-response.txt'),'old_status':read(prior/'run.json')['run_status'],
            'representation_only_instruction_replacement':{'original':sentence,'new':replacement},
            'full_source_case_sha256':digest(f['case']),'rules_sha256':digest(f['rules'])})
        assert read(prior/'run.json')['run_status']=='OUTPUT_TRUNCATED'
        slot['dest']='local/'+cid+'/'+part;slots.append(slot)
    old_used=read(PARENT/'pause-summary.json')['generation']['P']['generation_seconds']
    plan={'version':transport.VERSION,'tasks':slots,'created_at':utc(),'model_runtime':old['runtime'],
        'per_call_seconds':3600,'bounded_run_seconds':14400,'old_P_seconds_used':old_used,
        'old_P_stage_budget':old['stage_seconds']['P'],'old_P_remaining_seconds':old['stage_seconds']['P']-old_used,
        'max_output_tokens':16384,'retry_count':0,'no_training':True,'no_web':True,'no_push':True,
        'original_batch_stays_paused':True,'scope':'FOUR_USER_AUTHORIZED_TRUNCATED_P_TASKS_ONLY',
        'stop_policy':'One attempt per listed task; save technical failures; no silent retry. Respect new-root pause and resource faults.'}
    assert plan['bounded_run_seconds']<=plan['old_P_remaining_seconds']
    save(OUT/'preparation/plan.json',plan);return plan

def cache_acceptance():
    prepare()
    result=subprocess.run([sys.executable,'-B','-m','unittest',
        'tests.test_constraint_viability_v20_1','tests.test_source_verification_v20',
        'tests.test_pipeline_diagnostic_v19_8','tests.test_final_capacity_v19_8_1',
        'tests.test_source_verification_v20_2','tests.test_shared_sources_v20_3','-q'],cwd=ROOT,capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    (OUT/'engineering').mkdir(parents=True,exist_ok=True)
    (OUT/'engineering/tests.txt').write_text(result.stdout+result.stderr)
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained((ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),local_files_only=True)
    rows=[]
    for path in sorted((PARENT/'local').glob('*/P*/parsed.json')):
        prior=path.parent;raw=read(path);cid=prior.parent.name;part=prior.name
        original_schema=read(prior/'schema.json');compact=transport.pack(raw);validate(compact,transport.schema(original_schema))
        expanded=transport.expand(compact);audit=transport.check_expansion(compact,expanded,original_schema);assert expanded==raw
        f=read(PARENT/'preparation'/cid/'fixture.json');slot=next(s for s in read(PARENT/'freeze/protocol.json')['slots'] if s['case_id']==cid and s['part']['id']==part)
        old_entry=process_saved(f['case'],f['rules'],slot['part'],serialized(raw),original_schema,'V19_8','OK')
        new_entry=process_saved(f['case'],f['rules'],slot['part'],serialized(expanded),original_schema,'V19_8','OK')
        # Dict key order can change its serialized byte hash; values and all
        # conversion, check, inference and learner-input results must match.
        assert {k:v for k,v in old_entry.items() if k!='raw_sha256'}=={k:v for k,v in new_entry.items() if k!='raw_sha256'}
        save(OUT/'engineering/replays'/cid/part/'compact.json',compact)
        save(OUT/'engineering/replays'/cid/part/'expanded.json',expanded)
        save(OUT/'engineering/replays'/cid/part/'entry.json',new_entry)
        rows.append({'case_id':cid,'part':part,'exact_payload_equal':True,'actual_entry_equal_except_serialized_raw_hash':True,
            'original_tokens':len(tok.encode(serialized(raw),add_special_tokens=False)),
            'shared_tokens':len(tok.encode(serialized(compact),add_special_tokens=False)),
            'sets':len(compact['source_sets']),'independent_check':audit['status']})
    # Only complete analysis units from failed prefixes; never synthesize a completed old answer.
    partial=[];dec=json.JSONDecoder()
    for cid,part in TASKS:
        prior=PARENT/'local'/cid/part;raw=(prior/'raw-response.txt').read_text();s=read(prior/'schema.json');units={}
        for match in re.finditer(r'"([^"\\]+)"\s*:\s*\{',raw):
            pid=match[1]
            if pid not in s['properties']['analyses']['properties']:continue
            try:unit,_=dec.raw_decode(raw,raw.find('{',match.start()))
            except ValueError:continue
            units[pid]=unit
        ps=copy.deepcopy(s);ps['properties']={'analyses':copy.deepcopy(s['properties']['analyses'])};ps['required']=['analyses']
        ps['properties']['analyses']['properties']={k:v for k,v in ps['properties']['analyses']['properties'].items() if k in units}
        ps['properties']['analyses']['required']=list(units)
        value={'analyses':units};compact=transport.pack(value);expanded=transport.expand(compact)
        validate(value,ps);audit=transport.check_expansion(compact,expanded,ps);assert expanded==value
        save(OUT/'engineering/partial'/cid/part/'compact.json',compact)
        partial.append({'case_id':cid,'part':part,'complete_units_checked':len(units),'prefix_only_not_formal_answer':True,
            'exact_payload_equal':True,'independent_check':audit['status'],
            'original_tokens':len(tok.encode(serialized(value),add_special_tokens=False)),
            'shared_tokens':len(tok.encode(serialized(compact),add_special_tokens=False))})
    # Actual tokenizer/enforcer replay of a compact formerly failing case prefix.
    from legal_bench.mlx_json_constraint import tokenizer_data
    from legal_bench.mlx_json_constraint_v20_3 import SchemaMask
    compact=read(OUT/'engineering/partial/1954254/P01/compact.json')
    old=read(PARENT/'local/1954254/P01/schema.json');old['properties']={'analyses':old['properties']['analyses']};old['required']=['analyses']
    keys=compact['analyses'];old['properties']['analyses']['properties']={k:v for k,v in old['properties']['analyses']['properties'].items() if k in keys};old['properties']['analyses']['required']=list(keys)
    data=tokenizer_data(tok,getattr(tok,'eos_token_ids',tok.eos_token_id));mask=SchemaMask(data,transport.schema(old))
    ids=tok.encode(serialized(compact),add_special_tokens=False)
    for i,tid in enumerate(ids):
        if tid not in mask.enforcer.get_allowed_tokens(ids[:i]).allowed_tokens:
            raise ValueError('REAL_TOKEN_REPLAY_REJECTED:'+str(i))
    eos=tok.eos_token_id;assert eos in mask.enforcer.get_allowed_tokens(ids).allowed_tokens
    acceptance={'status':'PASS','tests':int(re.search(r'Ran (\d+) tests',result.stderr)[1]),'complete_P_caches':len(rows),
        'cache_rows':rows,'failed_prefix_rows':partial,'actual_tokenizer_enforcer_replay_tokens':len(ids),
        'EOS_allowed':True,'model_calls':0,'model_weights_loaded':False,'semantic_success':False}
    save(OUT/'engineering/cache-acceptance.json',acceptance)
    print(json.dumps({k:acceptance[k] for k in ('status','tests','complete_P_caches','actual_tokenizer_enforcer_replay_tokens','model_calls') }),flush=True)
    return acceptance

def freeze():
    gate=read(OUT/'engineering/cache-acceptance.json');assert gate['status']=='PASS'
    plan=read(OUT/'preparation/plan.json')
    entries=['scripts/proof_shared_sources_v20_3.py','legal_bench/proof_carrying/local_runtime_v20_3.py','tests/test_shared_sources_v20_3.py']
    prepared=[str(p.relative_to(ROOT)) for p in (OUT/'preparation').rglob('*') if p.is_file()]
    model_path=Path((ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip())
    configs=['outputs/local-qwen-pattern-eval-v3/environment/model-path.txt',
             str((model_path/'config.json').relative_to(ROOT)),str((model_path/'tokenizer_config.json').relative_to(ROOT))]
    cfg={**plan,**freeze_files(ROOT,OUT,entries,prepared,configs),'frozen_at':utc(),
         'cache_acceptance_sha256':byte_hash(OUT/'engineering/cache-acceptance.json')}
    save(OUT/'freeze/protocol.json',cfg);return cfg

def run():
    cfg=read(OUT/'freeze/protocol.json');verify_files(ROOT,cfg)
    assert cfg['cache_acceptance_sha256']==byte_hash(OUT/'engineering/cache-acceptance.json')
    from legal_bench.proof_carrying.local_runtime_v20_3 import Runner,SETTINGS
    assert SETTINGS==cfg['model_runtime'];runner=None
    for slot in cfg['tasks']:
        if paused(OUT):print('PAUSED',flush=True);return
        verify_files(ROOT,cfg)
        dest=OUT/slot['dest'];cid=slot['case_id'];part=slot['part']['id'];prepared=OUT/'preparation'/cid/part
        if (dest/'run.json').exists():continue
        if (dest/'start.json').exists():raise ValueError('UNCERTAIN_TASK_NOT_RESUBMITTED')
        used=sum(read(p).get('elapsed_seconds',0) or 0 for p in (OUT/'local').glob('*/*/run.json'))
        remaining=cfg['bounded_run_seconds']-used
        if remaining<=0:raise ValueError('BOUNDED_RUN_BUDGET_EXHAUSTED')
        if runner is None:runner=Runner((ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),SETTINGS)
        meta=runner.run((prepared/'prompt.txt').read_text(),read(prepared/'schema.json'),dest,16384,min(3600,remaining),'FIXED')
        formal=None;status=meta['run_status']
        if status=='OK':
            try:
                compact=read(dest/'parsed.json');expanded=transport.expand(compact)
                audit=transport.check_expansion(compact,expanded,read(prepared/'original-schema.json'));save(dest/'expansion-check.json',audit);save(dest/'expanded.json',expanded)
                f=read(prepared/'fixture.json');entry=process_saved(f['case'],f['rules'],slot['part'],serialized(expanded),read(prepared/'original-schema.json'),'V19_8','OK')
                save(dest/'entry-audit.json',entry)
                if entry.get('formal_answer') is None:status=entry['contract_status']
                else:formal=expanded
            except (ValueError,KeyError,TypeError) as exc:
                status='EXPANSION_OR_ENTRY_REJECTED';save(dest/'expansion-failure.json',{'error':repr(exc),'answer':None})
        save(dest/'formal-answer.json',{'answer':formal,'status':status,'semantic_approval':False,'legal_approval':False})
        summary()
        if meta['run_status'] in ('OUT_OF_MEMORY','UNSUPPORTED','INTERRUPTED_BY_USER_PAUSE'):return
    summary();print('FOUR_TASKS_FINISHED',flush=True)

def summary():
    cfg=read(OUT/'freeze/protocol.json');rows=[]
    for slot in cfg['tasks']:
        cid=slot['case_id'];part=slot['part']['id'];dest=OUT/slot['dest'];old=read(PARENT/'local'/cid/part/'run.json')
        if not (dest/'run.json').exists():rows.append({'case_id':cid,'part':part,'status':'NOT_STARTED'});continue
        meta=read(dest/'run.json');formal=read(dest/'formal-answer.json') if (dest/'formal-answer.json').exists() else {'status':'SAVE_INCOMPLETE','answer':None}
        compact=read(dest/'parsed.json') if (dest/'parsed.json').exists() else None
        raw=(dest/'raw-response.txt').read_text() if (dest/'raw-response.txt').exists() else ''
        uses=collections_count(compact) if compact else {}
        expanded=read(dest/'expanded.json') if (dest/'expanded.json').exists() else None
        coverage=collections_count_analyses(expanded) if expanded else {}
        rows.append({'case_id':cid,'part':part,'old_status':old['run_status'],'old_output_tokens':old['output_tokens'],
            'run_status':meta['run_status'],'status':formal['status'],'answer_present':formal['answer'] is not None,
            'output_tokens':meta.get('output_tokens'),'finish_reason':meta.get('finish_reason'),'seconds':meta.get('elapsed_seconds'),
            'raw_source_mentions':len(re.findall(r'"SRC:\d+"',raw)),
            'source_sets':len(compact['source_sets']) if compact else None,
            'source_set_uses':uses,'analysis_coverage':coverage,
            'transport_is_shared_schema':compact is not None,'semantic_accuracy_evaluated':False})
    preserved=read(OUT/'preserved-old-files.json');changed=[k for k,v in preserved.items() if byte_hash(ROOT/k)!=v]
    if changed:raise ValueError('OLD_FILES_CHANGED:'+str(changed))
    result={'version':transport.VERSION,'tasks':rows,'started':sum(r.get('run_status') is not None for r in rows),
        'transport_OK':sum(r.get('run_status')=='OK' for r in rows),'accepted_P':sum(r.get('answer_present',False) for r in rows),
        'truncated':sum(r.get('run_status')=='OUTPUT_TRUNCATED' for r in rows),
        'old_files_verified':len(preserved),'old_batch_pause_preserved':(PARENT/'PAUSE_REQUESTED.json').exists(),
        'training_calls':0,'Q_calls':0,'web_calls':0,'push':False,'semantic_success':False}
    dest=OUT/'results';dest.mkdir(parents=True,exist_ok=True)
    key=digest(result);save(dest/(key+'.json'),result)
    # Latest pointer is metadata, each result content snapshot is immutable.
    (dest/'latest.json').write_text(json.dumps({'path':key+'.json'})+'\n')
    return result

def collections_count(compact):
    counts={}
    def walk(v):
        if isinstance(v,dict):
            for k,x in v.items():
                if k in ('ref_set','source_set'):counts[x]=counts.get(x,0)+1
                else:walk(x)
        elif isinstance(v,list):
            for x in v:walk(x)
    walk({k:v for k,v in compact.items() if k!='source_sets'});return counts

def collections_count_analyses(value):
    units=value['analyses'];return {'planned_keys':len(units),'ANALYZED':sum(v['analysis_status']=='ANALYZED' for v in units.values()),
        'NOT_ANALYZED':sum(v['analysis_status']=='NOT_ANALYZED' for v in units.values()),
        'records':sum(len(v['records']) for v in units.values()),'uses':sum(len(v['uses']) for v in units.values()),
        'judgments':sum(len(v['judgments']) for v in units.values())}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','accept','freeze','run','summary']);args=p.parse_args()
    {'prepare':prepare,'accept':cache_acceptance,'freeze':freeze,'run':run,'summary':summary}[args.command]()
