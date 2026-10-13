#!/usr/bin/env python3
"""Exactly two authorized Together generations using frozen V19_6 tasks.

No retries, prompt repair, local inference, labels or training. Credentials stay
outside the repository. Full acceptance uses the already frozen shared entry.
"""
import argparse
import hashlib
import json
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.proof_together_diagnostic import credential, read, save, sha, stream_event, utc
from scripts.proof_contract_integrity_v19_6 import accept_saved_output
from legal_bench.proof_carrying import local_pipeline_v19_6 as pipe
from legal_bench.proof_carrying.schema_contract_v19_6 import loads, validate
from legal_bench.proof_carrying.repetition_v19_6 import ExpansionGuard
from legal_bench.proof_carrying.string_guard_v19_compact import StringGuard
from legal_bench.rules_verdict_v1.repetition_v9 import RepetitionAbort

OUT = ROOT / 'outputs/proof-together-contract-v19-6'
REPAIR = ROOT / 'outputs/proof-contract-integrity-v19-6'
BASE = ROOT / 'outputs/proof-local-pipeline-v19/continuation-04'
OLD = ROOT / 'outputs/proof-together-diagnostic-v1/transport-02'
MODEL = 'Qwen/Qwen3.5-9B'
ENDPOINT = 'https://api.together.xyz/v1/chat/completions'
TASKS = [('1954254', 'P01'), ('1187427', 'P02')]


def context(cid, part_id):
    f = read(BASE / 'preparation/inputs' / cid / 'fixture.json')
    slot = next(s for s in read(BASE / 'freeze/protocol.json')['local_generation_slots']
                if s['case_id'] == cid and s.get('part', {}).get('id') == part_id)
    return f, slot['part']


def prepare():
    if (OUT / 'freeze/protocol.json').exists():
        print('Already frozen; no input rewritten.'); return
    assert str(OUT.relative_to(ROOT)) in read(ROOT / 'docs/repository-artifacts.json')['artifact_roots']
    freeze = read(REPAIR / 'freeze/protocol.json')
    assert all(sha(ROOT / p) == h for p, h in freeze['code_hashes'].items())
    model = read(OUT / 'startup/provider-model.json')['model']
    assert model['id'] == MODEL
    pricing = model['pricing']; tasks = []; preserved = {}
    for cid, part_id in TASKS:
        original = REPAIR / 'prepared' / cid / part_id
        dest = OUT / 'tasks' / cid / part_id; dest.mkdir(parents=True, exist_ok=True)
        for name in ('prompt.txt', 'schema.json', 'source-directory.json'):
            content = (original / name).read_bytes()
            if (dest / name).exists(): assert (dest / name).read_bytes() == content
            else: (dest / name).write_bytes(content)
            preserved[str((original / name).relative_to(ROOT))] = sha(original / name)
        body = read(OLD / 'tasks' / cid / part_id / 'request.json')
        body['messages'] = [{'role': 'user', 'content': (dest / 'prompt.txt').read_text()}]
        body['response_format']['json_schema'] = {'name': 'v19_6_premise_proposal', 'schema': read(dest / 'schema.json')}
        save(dest / 'request.json', body)
        fixture, part = context(cid, part_id)
        selected = [r for r in fixture['rules'] if r['id'] in part['rule_ids']]
        view = {**fixture['case'], 'segments': [s for s in fixture['case']['segments'] if s['id'] in part['source_ids']]}
        assert (dest / 'prompt.txt').read_text() == pipe.proposal_prompt(fixture['case'], fixture['rules'], part)
        assert read(dest / 'schema.json') == pipe.schema(selected, view)
        assert read(dest / 'source-directory.json') == pipe.source_directory(view)
        for oldfile in ('raw-response.txt', 'run.json'):
            p = OLD / 'runs' / cid / part_id / oldfile
            preserved[str(p.relative_to(ROOT))] = sha(p)
        fpath = BASE / 'preparation/inputs' / cid / 'fixture.json'
        preserved[str(fpath.relative_to(ROOT))] = sha(fpath)
        tasks.append({'case_id': cid, 'part': part_id, 'task': str(dest.relative_to(OUT)),
                      'prompt_sha256': sha(dest / 'prompt.txt'), 'schema_sha256': sha(dest / 'schema.json'),
                      'request_sha256': sha(dest / 'request.json'), 'source_count': len(view['segments']),
                      'expected_premises': [p['id'] for r in selected for p in r['premises']],
                      'part_contract': part, 'production_version': pipe.VERSION,
                      'old_API_directory': str((OLD / 'runs' / cid / part_id).relative_to(ROOT))})
    code_hashes = {**freeze['code_hashes'], 'scripts/proof_together_contract_v19_6.py': sha(Path(__file__)),
                   'scripts/proof_together_diagnostic.py': sha(ROOT / 'scripts/proof_together_diagnostic.py')}
    for name in code_hashes:
        target = OUT / 'freeze/code' / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    save(OUT / 'startup/workspace.json', {'HEAD': subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
         'dirty_files': subprocess.check_output(['git','status','--short'],text=True).splitlines()})
    save(OUT / 'freeze/protocol.json', {
        'version': 'TOGETHER_V19_6_TWO_TASK_DEVELOPMENT', 'frozen_at': utc(), 'model': MODEL,
        'endpoint': ENDPOINT, 'service_display_name': model['display_name'], 'tasks': tasks,
        'code_hashes': code_hashes, 'preserved_hashes': preserved,
        'V19_6_protocol_sha256': sha(REPAIR / 'freeze/protocol.json'),
        'maximum_generations': 2, 'retries': 0, 'per_call_seconds_cap': 3600,
        'maximum_listed_cost_usd': 0.10, 'pricing_usd_per_million': pricing,
        'parameters': {k:v for k,v in body.items() if k not in ('messages','response_format')},
        'unchanged_API_sampling_and_output_budget': True,
        'same_source_rule_request_and_scope_as_old_API': True,
        'changed_prompt_and_schema_are_joint_V19_6_contract_not_same_bytes_as_V19_5': True,
        'no_old_answers_labels_reviews_in_model_input': True,
        'provider_schema_decoder_not_local_LMFE': True, 'local_guards_offline_only': True,
        'exact_provider_weights_revision_template_and_sampling_implementation': 'UNAVAILABLE',
        'evaluation': ['natural completion and strict full schema', 'declared versus analyzed premise coverage',
                       'source and dynamic reference validity', 'objects and required roles',
                       'conditional uses, premises and unchanged rule execution',
                       'scoped decisive source fidelity and retained counterarguments',
                       'comparison with preserved two old API proposals, not full-answer legal evaluation'],
        'no_training_or_local_generation_or_web_review': True, 'all_other_batches_remain_paused': True,
        'official_sources': ['https://www.together.ai/models/qwen3-5-9b',
                             'https://docs.together.ai/docs/inference/chat/structured-outputs'],
        'stop': 'After two fixed attempts; no rerun, repair, alternate model, extra condition or full answer',
        'credential_storage': 'Existing user-home private configuration, never printed or saved to repository',
        'no_commit_or_push': True})
    print(json.dumps({'prepared': len(tasks), 'protocol_sha256': sha(OUT / 'freeze/protocol.json')}))


def run_one(task, key, cfg):
    dest = OUT / 'runs' / task['case_id'] / task['part']
    if (dest / 'run.json').exists(): return read(dest / 'run.json')
    if (dest / 'start.json').exists(): raise ValueError('SUBMISSION_STATE_UNKNOWN_NO_RESEND')
    source = OUT / task['task']
    for name, field in [('request.json','request_sha256'),('prompt.txt','prompt_sha256'),('schema.json','schema_sha256')]:
        assert sha(source / name) == task[field]
    request = urllib.request.Request(ENDPOINT, data=(source / 'request.json').read_bytes(),
        headers={'Authorization':'Bearer '+key, 'Content-Type':'application/json',
                 'Accept':'text/event-stream', 'User-Agent':'legal-ai-together-diagnostic/1.0'}, method='POST')
    save(dest / 'start.json', {'started_at': utc(), 'request_sha256': task['request_sha256'], 'dispatch_count': 1})
    for name in ('prompt.txt','schema.json'):
        (dest / name).write_bytes((source / name).read_bytes())
    receipt = {'run_status': None, 'done_received': False, 'requested_model': MODEL, 'started_at': utc(),
               'production_version': pipe.VERSION, 'request_sha256': task['request_sha256'],
               'source_input_truncated_by_client': False, 'local_guard_enforcement': False}
    def timeout(signum, frame): raise TimeoutError('FROZEN_SINGLE_CALL_TIME_CAP')
    previous = signal.signal(signal.SIGALRM, timeout); signal.alarm(cfg['per_call_seconds_cap'])
    start = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            receipt['http_status'] = response.status
            receipt['response_headers'] = {k:response.headers.get(k) for k in ('content-type','x-request-id','cf-ray') if response.headers.get(k)}
            with (dest/'raw-sse.txt').open('w') as raw, (dest/'raw-response.txt').open('w') as content, (dest/'reasoning.txt').open('w') as reasoning:
                event_lines = []
                for binary in response:
                    line = binary.decode('utf-8'); raw.write(line); raw.flush()
                    if line.strip():
                        if line.startswith('data:'): event_lines.append(line[5:].lstrip().rstrip('\r\n'))
                    elif event_lines:
                        stream_event('\n'.join(event_lines),content,reasoning,receipt);event_lines=[]
                if event_lines: stream_event('\n'.join(event_lines),content,reasoning,receipt)
        receipt['reasoning_output_present'] = bool((dest/'reasoning.txt').stat().st_size)
        receipt['raw_sha256'] = sha(dest/'raw-response.txt')
        if receipt.get('finish_reason') == 'length': receipt['run_status'] = 'OUTPUT_TRUNCATED'
        elif not receipt['done_received']: receipt['run_status'] = 'STREAM_INCOMPLETE'
        elif receipt['reasoning_output_present']: receipt['run_status'] = 'THINKING_CONFIGURATION_MISMATCH'
        else:
            try:
                result = loads((dest/'raw-response.txt').read_text()); validate(result,read(source/'schema.json'))
                save(dest/'parsed.json',result);receipt['run_status']='OK'
            except (ValueError,TypeError,KeyError) as exc:
                receipt.update(run_status='FORMAT_OR_SCHEMA_FAILURE',validation_error=str(exc))
    except urllib.error.HTTPError as exc:
        receipt.update(run_status='HTTP_FAILURE',http_status=exc.code)
        (dest/'http-error.txt').write_text(exc.read().decode('utf-8',errors='replace').replace(key,'[REDACTED]'))
    except (OSError,ValueError) as exc:
        receipt.update(run_status='TRANSPORT_OR_STREAM_FAILURE',error_type=type(exc).__name__,error=str(exc).replace(key,'[REDACTED]'))
    finally:
        signal.alarm(0);signal.signal(signal.SIGALRM,previous)
    receipt.update(elapsed_seconds=time.monotonic()-start,finished_at=utc())
    usage=receipt.get('usage') or {}; prices=cfg['pricing_usd_per_million']
    if 'prompt_tokens' in usage and 'completion_tokens' in usage:
        receipt['listed_price_token_cost_usd']=(usage['prompt_tokens']*prices['input']+usage['completion_tokens']*prices['output'])/1000000
    save(dest/'run.json',receipt)
    if not (dest/'raw-response.txt').exists(): (dest/'raw-response.txt').write_text('')
    fixture,part=context(task['case_id'],task['part'])
    entry=accept_saved_output(fixture['case'],fixture['rules'],part,dest)
    save(dest/'entry-summary.json',summary(task,receipt,entry))
    print(json.dumps({'case':task['case_id'],'part':task['part'],'status':receipt['run_status'],
                      'elapsed_seconds':receipt['elapsed_seconds'],'usage':receipt.get('usage'),
                      'contract':entry['contract_status'],'coverage':(entry.get('coverage') or {}).get('status')}),flush=True)
    return receipt


def summary(task,run,entry):
    audit=entry.get('conditional_audit') or {}
    result={'case_id':task['case_id'],'part':task['part'],'run':run,'contract_status':entry['contract_status'],
        'formal_answer_present':entry.get('formal_answer') is not None,'coverage':entry.get('coverage'),
        'schema_violations':entry.get('schema_violations',[]),
        'records_retained':audit.get('raw_records_retained'),
        'uses':dict(Counter(x['disposition'] for x in audit.get('checks',[]))),
        'use_error_counts':dict(Counter(e for x in audit.get('checks',[]) for e in x['errors'])),
        'judgment_states':dict(Counter(x['conditional_state'] for x in audit.get('premise_judgments',[]))),
        'judgment_error_counts':dict(Counter(e for x in audit.get('premise_judgments',[]) for e in x['errors'])),
        'rule_states':[{k:r[k] for k in ('rule_id','operator','conditional_result','not_executed')} for r in audit.get('conditional_rules',[])],
        'missing_role_judgments':sum(bool(x['missing_roles']) for x in entry.get('role_coverage',[])),
        'independent_import':entry.get('independent_import'),'independent_check':entry.get('independent_check'),
        'reference_used':False,'semantic_status':'REQUIRES_SCOPED_SOURCE_REVIEW'}
    return result


def run():
    cfg=read(OUT/'freeze/protocol.json')
    assert all(sha(ROOT/p)==h for p,h in cfg['code_hashes'].items())
    assert all(sha(ROOT/p)==h for p,h in cfg['preserved_hashes'].items())
    key=credential();spent=0
    for task in cfg['tasks']:
        if (OUT/'PAUSE_REQUESTED.json').exists(): break
        if spent>=cfg['maximum_listed_cost_usd']: break
        result=run_one(task,key,cfg);spent+=result.get('listed_price_token_cost_usd',0)
        if result.get('http_status') in (401,402,403) or result['run_status']=='THINKING_CONFIGURATION_MISMATCH': break


def audit():
    rows=[]
    for task in read(OUT/'freeze/protocol.json')['tasks']:
        dest=OUT/'runs'/task['case_id']/task['part']
        if not (dest/'entry-summary.json').exists(): continue
        row=read(dest/'entry-summary.json');row['offline_guard_hits']={}
        raw=(dest/'raw-response.txt').read_text()
        for name,guard in [('record_and_refs',ExpansionGuard()),('string',StringGuard())]:
            try: guard.feed(raw)
            except RepetitionAbort: row['offline_guard_hits'][name]=guard.hit
        old_entry=read(REPAIR/'replay-final/api_saved'/task['case_id']/task['part']/'entry-result.json')
        old_run=read(OLD/'runs'/task['case_id']/task['part']/'run.json')
        row['old_API']=summary(task,old_run,old_entry)
        rows.append(row)
    save(OUT/'comparison.json',{'tasks':rows,'reviewer':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
        'joint_interface_development_comparison_not_independent_test':True,'no_full_answer_or_learning_model_claim':True})
    print(json.dumps([{k:r.get(k) for k in ('case_id','contract_status','coverage','uses','judgment_states','missing_role_judgments')} for r in rows]))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','run','audit'])
    globals()[parser.parse_args().phase]()
