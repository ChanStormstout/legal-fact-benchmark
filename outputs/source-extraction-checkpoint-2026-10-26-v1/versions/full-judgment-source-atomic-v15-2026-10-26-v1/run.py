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
import source_v15 as method
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
    previous_first_wire = load(HERE / 'private/expected-first-wire.json')
    with (env.REPO / '.runtime/rapido-proof-task-api.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        save(dest / 'start.json', {
            'pid': os.getpid(), 'epoch': time.time(), 'freeze_hash': fingerprint,
            'authorization': 'User requested repairing composite source records and completing the remaining first-case source extraction. New version reruns prior groups to avoid mixed-version results; original remaining $6 envelope applies.',
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
            if len(attempted) == 4 and not (HERE / 'private/CONTINUE_AFTER_READING_GATE').exists():
                save(dest / 'reading-gate.json', {'status': 'AWAITING_SOURCE_BASED_REVIEW', 'completed_calls': 4,
                     'not_a_user_permission_request': True, 'no_more_api_dispatch_until_review': True})
                print('PAUSED_AT_READING_GATE', flush=True)
                while not (HERE / 'private/CONTINUE_AFTER_READING_GATE').exists():
                    if stop['requested'] or (HERE / 'private/STOP').exists():
                        raise RuntimeError('STOP_AFTER_READING_GATE')
                    time.sleep(1)
                print('CONTINUE_AFTER_SOURCE_REVIEW', flush=True)
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
                    value, _ = provider.call('1251841', 'V15', tag, request, attempt)
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
            result = method.run(sources, ask, dest / 'case')
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
                'new_method_version': method.VERSION, 'semantic_quality': None,
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
