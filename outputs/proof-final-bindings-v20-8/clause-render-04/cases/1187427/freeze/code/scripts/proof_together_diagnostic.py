#!/usr/bin/env python3
"""Two immutable same-prompt Together runs; no SDK, implicit retries or key exports."""
import argparse
import datetime
import hashlib
import json
import os
import signal
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'outputs/proof-together-diagnostic-v1'
BASE = ROOT / 'outputs/proof-local-pipeline-v19/continuation-04'
MODEL = 'Qwen/Qwen3.5-9B'
ENDPOINT = 'https://api.together.ai/v1/chat/completions'
TASKS = [('1954254', 'P01'), ('1187427', 'P02')]
KEY_FILE = Path.home() / '.config/legal-ai/together-api-key'


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def save(path, value):
    """Immutable evidence; stdout never contains HTTP headers or credentials."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    if path.exists():
        if path.read_text() != text:
            raise ValueError('IMMUTABLE_RECORD_MISMATCH:' + str(path))
        return
    path.write_text(text)


def credential():
    value = os.environ.get('TOGETHER_API_KEY')
    if not value:
        if KEY_FILE.stat().st_mode & 0o077:
            raise ValueError('PRIVATE_KEY_FILE_PERMISSIONS_REQUIRED')
        value = KEY_FILE.read_text().strip()
    if not value or any(c.isspace() for c in value):
        raise ValueError('INVALID_CREDENTIAL_FORMAT')
    return value


def request_body(prompt, schema):
    return {
        'model': MODEL, 'messages': [{'role': 'user', 'content': prompt}],
        'response_format': {'type': 'json_schema', 'json_schema': {
            'name': 'v19_5_premise_proposal', 'schema': schema}},
        'reasoning': {'enabled': False},
        'temperature': 0.0, 'top_p': 1.0, 'top_k': 0, 'min_p': 0.0,
        'repetition_penalty': 1.0, 'seed': 20261001, 'max_tokens': 16384,
        'stream': True, 'n': 1, 'context_length_exceeded_behavior': 'error',
    }


def prepare():
    registration = read(ROOT / 'docs/repository-artifacts.json')
    assert str(OUT.relative_to(ROOT)) in registration['artifact_roots']
    manifest = []
    for cid, part in TASKS:
        original = BASE / 'local' / cid / part
        dest = OUT / 'tasks' / cid / part
        dest.mkdir(parents=True, exist_ok=True)
        for name in ('prompt.txt', 'schema.json'):
            target = dest / name
            if target.exists() and target.read_bytes() != (original / name).read_bytes():
                raise ValueError('COPIED_INPUT_CHANGED')
            if not target.exists():
                target.write_bytes((original / name).read_bytes())
        body = request_body((dest / 'prompt.txt').read_text(), read(dest / 'schema.json'))
        save(dest / 'request.json', body)
        old = read(original / 'run.json')
        manifest.append({'case_id': cid, 'part': part,
                         'original': str(original.relative_to(ROOT)),
                         'task': str(dest.relative_to(OUT)),
                         'prompt_sha256': sha(dest / 'prompt.txt'),
                         'schema_file_sha256': sha(dest / 'schema.json'),
                         'request_sha256': sha(dest / 'request.json'),
                         'prompt_identical_bytes': True, 'schema_identical_bytes': True,
                         'local_prompt_tokens': old['prompt_tokens'],
                         'local_status': old['run_status'],
                         'local_output_tokens': old['output_tokens'],
                         'local_elapsed_seconds': old['elapsed_seconds']})
    save(OUT / 'freeze/protocol.json', {
        'version': 'TOGETHER_SAME_INPUT_V1', 'frozen_at': utc(),
        'HEAD': os.popen('git rev-parse HEAD').read().strip(), 'tasks': manifest,
        'runner_sha256': sha(Path(__file__)), 'maximum_generations': 2,
        'retries': 0, 'per_call_seconds_cap': 3600, 'maximum_cost_usd': 0.10,
        'input_price_usd_per_million': 0.17, 'output_price_usd_per_million': 0.25,
        'model': MODEL, 'service_model_ui': 'Qwen3.5 9B FP8',
        'parameters': {k: v for k, v in body.items() if k not in ('messages', 'response_format')},
        'differences': ['FP8 versus local 4-bit MLX',
                        'Server framework, exact weights revision and chat template not available',
                        'Provider JSON Schema decoding versus patched local LM Format Enforcer',
                        'API reasoning disable versus local tokenizer template disable',
                        'Local repetition guards diagnostic only in API run; do not interrupt stream',
                        'Local 65536 input/output budget checked on saved inputs; provider native context 262144'],
        'evaluation': ['natural completion and strict original schema validation',
                       'original dynamic reference and local import/independent check',
                       'offline identical-record/address/string guards',
                       'source fidelity for selected decisive assertions; not whole-case legal evaluation'],
        'no_training_or_local_generation': True, 'V19_remains_paused': True,
        'credential_storage': 'User-home private file or environment; never repository',
        'credential_expiration_ui': '2027-06-12 00:00 as shown after user created key; not changed by agent',
        'official_sources': [
            'https://www.together.ai/models/qwen3-5-9b',
            'https://docs.together.ai/reference/chat-completions',
            'https://docs.together.ai/docs/inference/chat/structured-outputs'],
        'stop': 'After two prescribed attempts; no method changes, alternate models or repair retries',
    })
    print(json.dumps({'prepared': len(manifest), 'protocol_sha256': sha(OUT / 'freeze/protocol.json')}))


def stream_event(data, content, reasoning, receipt):
    """Interpret only SSE data; retain all originals separately."""
    if data == '[DONE]':
        receipt['done_received'] = True
        return
    event = json.loads(data)
    if event.get('error'):
        raise ValueError('PROVIDER_STREAM_ERROR')
    for k in ('id', 'model', 'created', 'system_fingerprint'):
        if k in event:
            receipt[k] = event[k]
    if event.get('usage'):
        receipt['usage'] = event['usage']
    for choice in event.get('choices', []):
        if choice.get('index', 0) != 0:
            raise ValueError('UNEXPECTED_EXTRA_CHOICE')
        delta = choice.get('delta', choice.get('message', {}))
        if delta.get('content'):
            content.write(delta['content'])
            content.flush()
        for k in ('reasoning', 'reasoning_content'):
            if delta.get(k):
                reasoning.write(delta[k])
                reasoning.flush()
        if choice.get('finish_reason'):
            receipt['finish_reason'] = choice['finish_reason']


def run_one(task, key):
    from legal_bench.proof_carrying.local_pipeline_v19_compact import validate
    config = read(OUT / 'freeze/protocol.json')
    if config['runner_sha256'] != sha(Path(__file__)):
        raise ValueError('FROZEN_RUNNER_CHANGED')
    dest = OUT / 'runs' / task['case_id'] / task['part']
    if (dest / 'run.json').exists():
        return read(dest / 'run.json')
    if (dest / 'start.json').exists():
        raise ValueError('UNFINISHED_ATTEMPT_NO_RESEND')
    source = OUT / task['task']
    assert sha(source / 'request.json') == task['request_sha256']
    assert sha(source / 'prompt.txt') == task['prompt_sha256']
    assert sha(source / 'schema.json') == task['schema_file_sha256']
    request = urllib.request.Request(ENDPOINT, data=(source / 'request.json').read_bytes(),
                                     headers={'Authorization': 'Bearer ' + key,
                                              'Content-Type': 'application/json',
                                              'Accept': 'text/event-stream'}, method='POST')
    save(dest / 'start.json', {'started_at': utc(), 'request_sha256': task['request_sha256'],
                              'dispatch_count': 1, 'no_implicit_retry': True})
    start = time.monotonic()
    receipt = {'run_status': None, 'done_received': False, 'source_input_truncated_by_client': False,
               'request_sha256': task['request_sha256'], 'requested_model': MODEL,
               'started_at': utc(), 'local_guard_enforcement': False}
    def timeout(signum, frame):
        raise TimeoutError('FROZEN_SINGLE_CALL_TIME_CAP')
    previous = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(config['per_call_seconds_cap'])
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            receipt['http_status'] = response.status
            receipt['response_headers'] = {k: response.headers.get(k) for k in
                                           ['content-type', 'x-request-id', 'cf-ray']
                                           if response.headers.get(k)}
            with (dest / 'raw-sse.txt').open('w') as raw, \
                 (dest / 'raw-response.txt').open('w') as content, \
                 (dest / 'reasoning.txt').open('w') as reasoning:
                event_lines = []
                for binary in response:
                    line = binary.decode('utf-8')
                    raw.write(line); raw.flush()
                    if line.strip():
                        if line.startswith('data:'):
                            event_lines.append(line[5:].lstrip().rstrip('\r\n'))
                    elif event_lines:
                        stream_event('\n'.join(event_lines), content, reasoning, receipt)
                        event_lines = []
                if event_lines:
                    stream_event('\n'.join(event_lines), content, reasoning, receipt)
        raw_text = (dest / 'raw-response.txt').read_text()
        receipt['reasoning_output_present'] = bool((dest / 'reasoning.txt').stat().st_size)
        receipt['raw_sha256'] = sha(dest / 'raw-response.txt')
        if receipt.get('finish_reason') == 'length':
            receipt['run_status'] = 'OUTPUT_TRUNCATED'
        elif not receipt['done_received']:
            receipt['run_status'] = 'STREAM_INCOMPLETE'
        elif receipt['reasoning_output_present']:
            receipt['run_status'] = 'THINKING_CONFIGURATION_MISMATCH'
        else:
            try:
                result = json.loads(raw_text)
                validate(result, read(source / 'schema.json'))
                save(dest / 'parsed.json', result)
                receipt['run_status'] = 'OK'
            except (ValueError, TypeError, KeyError) as exc:
                receipt['run_status'] = 'FORMAT_OR_SCHEMA_FAILURE'
                receipt['validation_error'] = str(exc)
    except urllib.error.HTTPError as exc:
        receipt.update(run_status='HTTP_FAILURE', http_status=exc.code)
        # No request/auth headers are copied. Provider error body retained locally.
        body = exc.read().decode('utf-8', errors='replace').replace(key, '[REDACTED]')
        (dest / 'http-error.txt').write_text(body)
    except (OSError, ValueError) as exc:
        receipt.update(run_status='TRANSPORT_OR_STREAM_FAILURE', error_type=type(exc).__name__,
                       error=str(exc).replace(key, '[REDACTED]'))
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
    receipt.update(elapsed_seconds=time.monotonic() - start, finished_at=utc())
    usage = receipt.get('usage') or {}
    if 'prompt_tokens' in usage and 'completion_tokens' in usage:
        receipt['listed_price_token_cost_usd'] = (usage['prompt_tokens'] * .17 + usage['completion_tokens'] * .25) / 1000000
    save(dest / 'run.json', receipt)
    save(dest / 'formal-answer.json', {'status': receipt['run_status'],
                                      'answer': read(dest / 'parsed.json') if receipt['run_status'] == 'OK' else None})
    print(json.dumps({'case': task['case_id'], 'part': task['part'], **receipt}), flush=True)
    return receipt


def run():
    config = read(OUT / 'freeze/protocol.json')
    key = credential()
    for task in config['tasks']:
        if (OUT / 'PAUSE_REQUESTED.json').exists():
            break
        result = run_one(task, key)
        if result.get('http_status') in (401, 402, 403) or result['run_status'] == 'THINKING_CONFIGURATION_MISMATCH':
            break


def audit():
    from legal_bench.proof_carrying import local_pipeline_v19_compact as pipe
    from legal_bench.proof_carrying.local_checker_v19_refs import check
    from legal_bench.proof_carrying.repetition_v19_compact import ExpansionGuard
    from legal_bench.proof_carrying.string_guard_v19_compact import StringGuard
    records = []
    cfg = read(BASE / 'freeze/protocol.json')
    for task in read(OUT / 'freeze/protocol.json')['tasks']:
        cid, part = task['case_id'], task['part']
        dest = OUT / 'runs' / cid / part
        if not (dest / 'run.json').exists():
            continue
        result = read(dest / 'run.json')
        row = {**task, 'api': result, 'offline_guard_hits': {}}
        if (dest / 'raw-response.txt').exists():
            for label, guard in [('record', ExpansionGuard()), ('string', StringGuard())]:
                try:
                    guard.feed((dest / 'raw-response.txt').read_text())
                except ValueError:
                    row['offline_guard_hits'][label] = guard.hit
        if result['run_status'] == 'OK':
            fixture = read(BASE / 'preparation/inputs' / cid / 'fixture.json')
            slot = next(x for x in cfg['local_generation_slots'] if x['case_id'] == cid and x.get('part', {}).get('id') == part)
            view = {**fixture['case'], 'segments': [x for x in fixture['case']['segments'] if x['id'] in slot['part']['source_ids']]}
            raw = read(dest / 'parsed.json')
            converted, ledger = pipe.convert(raw, view, pipe.VERSION)
            imported = pipe.independent_import(raw, converted, view, pipe.VERSION)
            merged, merge_ledger = pipe.merge_parts([(part, converted)])
            production = pipe.apply_connection_decisions(fixture['case'], fixture['rules'], merged)
            independent = check(fixture['case'], fixture['rules'], merged, None, production)
            save(dest / 'offline-audit.json', {'conversion': ledger, 'merge': merge_ledger,
                                               'independent_import': imported, 'production': production,
                                               'independent_check': independent})
            row.update(analyses=len(raw['analyses']), records=sum(len(x['records']) for x in raw['analyses']),
                       uses=sum(len(x['uses']) for x in raw['analyses']), independent_import=imported,
                       independent_check=independent)
        records.append(row)
    save(OUT / 'comparison.json', {'tasks': records, 'legal_review_status': 'REQUIRES_SCOPED_SOURCE_REVIEW',
                                   'no_claim_of_local_fault_isolation': True})
    print(json.dumps([{k:v for k,v in r.items() if k not in ('api','task','original')} for r in records], ensure_ascii=False)[:4500])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['prepare', 'run', 'audit'])
    args = parser.parse_args()
    globals()[args.phase]()
