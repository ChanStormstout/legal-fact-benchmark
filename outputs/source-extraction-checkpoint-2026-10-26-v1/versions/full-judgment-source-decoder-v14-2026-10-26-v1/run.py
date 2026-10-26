"""Explicitly authorized technical retry of the unchanged frozen V12 method."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'full-judgment-source-repair-v12-2026-10-26-v1'
sys.path.insert(0, str(BASE))
import environment as env
sys.path.insert(0, str(HERE))
import source_v12 as method
from experiment import transport_request, wire
from source_v8 import save, digest


def load(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify():
    frozen = load(HERE / 'freeze.json')
    changed = [p for p, h in frozen['files'].items()
               if not Path(p).exists() or sha(p) != h]
    if changed:
        raise ValueError('FROZEN_FILE_CHANGED:' + repr(changed))
    return digest(frozen)


def reading_gate(sources, ask, dest):
    dest.mkdir(parents=True, exist_ok=False)
    catalog = method.prepare_units(sources)
    save(dest / 'source-units.json', catalog)
    calls = 0
    tag = None
    try:
        for i, focus in enumerate(catalog['groups'][:2]):
            requests = [('reading', method.reading_request(sources, catalog, focus)),
                        ('independent', method.reading_request(sources, catalog, focus, independent=True))]
            batch = {}
            for role, req in requests:
                tag = f'{role}-{i:03d}'
                save(dest / 'requests' / (tag + '.json'), req)
                calls += 1
                value = ask(tag, req)
                save(dest / 'responses' / (tag + '.json'), value)
                method.validate(value, req['schema'])
                batch[role] = method.pack_reading(value, sources, catalog, focus, f'B{i:03d}.{role}')
            save(dest / 'batches' / f'{i:03d}.json', batch)
        outcome = {'reading_gate_complete': True, 'whole_document_complete': False,
                   'logical_calls': calls, 'source_groups_completed': 2,
                   'semantic_quality': None, 'full_C_run': False}
        save(dest / 'outcome.json', outcome)
        return outcome
    except Exception as exc:
        save(dest / 'outcome.json', {'reading_gate_complete': False,
             'whole_document_complete': False, 'failed_stage': tag,
             'logical_calls': calls, 'error': type(exc).__name__ + ':' + str(exc),
             'semantic_quality': None, 'full_C_run': False})
        raise


def run():
    fingerprint = verify()
    cfg = load(HERE / 'protocol.json')
    cfg.update(execution_enabled=True, paid_api_enabled=True)
    dest = HERE / 'private/run-v1'
    if dest.exists():
        raise ValueError('EXISTING_ATTEMPT_NOT_REPEATED')
    if (HERE / 'private/STOP').exists():
        raise ValueError('USER_STOP_REQUEST_PRESENT')
    sources = load(BASE / 'private/input.json')['sources']
    catalog = method.prepare_units(sources)
    plan = [f'{stage}-{i:03d}' for i in range(len(catalog['groups']))
            for stage in ('reading', 'independent')]
    plan += [f'{stage}-{i:03d}'
             for stage in ('whole-document-reconcile', 'whole-document-final-review')
             for i in range(len(method.review_groups(catalog)))]
    plan = plan[:4]
    previous_first_wire = load(HERE / 'private/expected-first-wire.json')
    with (env.REPO / '.runtime/rapido-proof-task-api.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        save(dest / 'start.json', {
            'pid': os.getpid(), 'epoch': time.time(), 'freeze_hash': fingerprint,
            'authorization': 'User requested diagnosis and repair of repeated timeouts; four full-source reading calls test a decoder-only change within the remaining six-case $6 envelope.',
            'method_version': method.VERSION, 'case_id': '1251841',
            'logical_plan': plan, 'no_automatic_expansion': True,
            'previous_attempt_preserved': str(BASE / 'private/run-v1'),
            'technical_retry_is_not_an_independent_case': True,
        })
        from role_api_provider import APIProvider
        provider = APIProvider(cfg, dest / 'transport')
        attempted = []
        started = time.monotonic()
        stop = {'requested': False}

        def halt(*_):
            stop['requested'] = True

        signal.signal(signal.SIGTERM, halt)

        def ask(tag, req):
            if stop['requested'] or (HERE / 'private/STOP').exists():
                raise RuntimeError('USER_STOP_BETWEEN_CALLS')
            verify()
            if len(attempted) >= len(plan) or tag != plan[len(attempted)]:
                raise ValueError('UNPLANNED_STAGE')
            if req['sources'] != sources:
                raise ValueError('SOURCE_CHANGED')
            if not attempted and wire(req, cfg) != previous_first_wire:
                raise ValueError('INITIAL_TECHNICAL_RETRY_WIRE_CHANGED')
            attempted.append(tag)
            request = transport_request(req, cfg)
            for attempt in range(cfg['max_technical_retries'] + 1):
                try:
                    value, _ = provider.call('1251841', 'V14', tag, request, attempt)
                    return value
                except Exception as exc:
                    receipts = getattr(exc, 'receipts', [])
                    last = receipts[-1] if receipts else {}
                    if (stop['requested'] or provider.dispatch_stop or last.get('no_retry')
                        or last.get('status') not in ('STREAM_INCOMPLETE', 'STREAM_PROTOCOL_ERROR', 'CALL_TIMEOUT', 'TECHNICAL_FAILURE')
                        or attempt >= cfg['max_technical_retries']):
                        raise

        result = None
        error = None
        try:
            result = reading_gate(sources, ask, dest / 'case')
        except Exception as exc:
            error = type(exc).__name__ + ':' + str(exc)
        finally:
            outcome_path = dest / 'case/outcome.json'
            outcome = load(outcome_path) if outcome_path.exists() else result
            save(dest / 'summary.json', {
                'outcome': outcome, 'error': error,
                'attempted_stages': attempted, 'physical_calls': len(provider.receipts),
                'confirmed_usd': sum(r.get('known_cost_usd', 0) or 0 for r in provider.receipts),
                'accounted_usd': provider.spent,
                'unknown_usage_reserves': provider.unknown_requests,
                'elapsed_seconds': time.monotonic() - started,
                'prior_conservative_usd': cfg['prior_conservative_usd'],
                'cumulative_conservative_usd': cfg['prior_conservative_usd'] + provider.spent,
                'remaining_original_six_case_envelope_usd': cfg['maximum_new_usd'] - provider.spent,
                'extraction_method_unchanged': True, 'hosted_decoder_redundant_bounds_removed': True, 'semantic_quality': None,
                'full_C_run': False, 'next_case_started': False,
                'previous_failed_attempt_is_not_replaced': True,
            })
            verify()
        print(json.dumps({'outcome': result, 'error': error,
                          'accounted_usd': provider.spent}), flush=True)


if __name__ == '__main__':
    if sys.argv[1:] == ['verify']:
        print(verify())
    elif sys.argv[1:] == ['run']:
        run()
    else:
        raise SystemExit('Usage: run.py verify|run')
