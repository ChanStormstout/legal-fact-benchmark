"""Two fresh C cases. No paid dispatch without separately recorded user approval."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / 'src'), str(REPO)]
from common import read, save, digest

CASES = ['1251841', '1252014']
MODE = 'V22_SCOPED_ACTUAL_USAGE_APPROVAL'


def verify():
    manifest = read(ROOT / 'freeze.json')
    for relative, expected in manifest['files'].items():
        if hashlib.sha256((REPO / relative).read_bytes()).hexdigest() != expected:
            raise RuntimeError('FROZEN_FILE_CHANGED:' + relative)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorization', type=Path, required=True)
    args = parser.parse_args()
    auth = read(args.authorization)
    if (auth.get('approved') is not True or auth.get('mode') != MODE
            or auth.get('cases') != CASES or auth.get('arms') != ['C']
            or auth.get('method_root') != str(ROOT.relative_to(REPO))
            or not auth.get('user_message')):
        raise RuntimeError('SCOPED_USER_BILLING_APPROVAL_REQUIRED')
    frozen = verify()
    cfg = read(ROOT / 'protocol.json')
    if cfg['cases'] != CASES or cfg['arms'] != ['C'] or not cfg['capacity_diagnostic']:
        raise RuntimeError('DIAGNOSTIC_SCOPE_CHANGED')
    if not read(ROOT / 'private/preparation.json')['ready_for_authorized_dispatch']:
        raise RuntimeError('PREPARATION_INCOMPLETE')
    lock = (REPO / '.runtime/rapido-proof-task-api.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    ledger=read(REPO / cfg['budget_ledger'])
    prior = ledger['cumulative_accounted_usd']
    unresolved=ledger.get('unreconciled_request_ids',[])
    if unresolved and auth.get('explicitly_accepted_prior_unknown_usage_reserves')!=unresolved:
        raise RuntimeError('PRIOR_UNKNOWN_USAGE_REQUIRES_RECONCILIATION_OR_EXPLICIT_RESERVED_CHARGE_APPROVAL')
    if abs(prior - cfg['prior_conservative_usd']) > 1e-9:
        raise RuntimeError('COST_LEDGER_CHANGED_RECONCILE_BEFORE_DISPATCH')
    dest = ROOT / 'private/run'
    if dest.exists():
        raise RuntimeError('EXISTING_ATTEMPT_PRESERVED_NO_RESUME_OR_RERUN')
    cfg.update(execution_enabled=True, paid_api_enabled=True,
               billing_authorization_mode=MODE,
               allow_unknown_usage_reserve_continuation=auth.get('allow_unknown_usage_reserve_continuation') is True,
               authorized_cumulative_usd=None, maximum_new_usd=None,
               cumulative_authorization='Explicit actual-usage exception for these two C attempts only.',
               implementation_hash=digest(frozen['files']))
    save(dest / 'authorization.json', auth)
    save(dest / 'run-protocol.json', cfg)
    save(dest / 'start.json', {'pid': os.getpid(), 'started_epoch': time.time(),
         'cases': CASES, 'arms': ['C'], 'prior_accounted_usd': prior,
         'method_freeze_hash': digest(frozen['files']),
         'aggregate_token_call_or_suffix_budget_disabled': True,
         'explicit_output_token_capacity': cfg['diagnostic_output_tokens'],
         'finite_workflow_and_technical_guards_retained': True})
    for cid in CASES:
        source = REPO / cfg['input_root'] / (cid + '.json')
        target = dest / 'inputs' / (cid + '.json')
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(source.read_bytes())
    from api_provider import APIProvider
    from runner import run_arm
    provider = APIProvider(cfg, dest / 'transport')
    started = time.monotonic()
    outcomes = []
    error = None
    try:
        for cid in CASES:
            result = run_arm(provider, read(dest / 'inputs' / (cid + '.json')),
                             cfg, dest / 'cases' / cid / 'C', 'C')
            outcomes.append(result)
            save(dest / 'progress' / (cid + '-C.json'), {
                'outcome': result, 'new_accounted_usd': provider.spent,
                'cumulative_accounted_usd': prior + provider.spent})
            print('CASE_FINISHED', cid, json.dumps(result, ensure_ascii=False), flush=True)
            if provider.dispatch_stop:
                break
    except BaseException as exc:
        error = type(exc).__name__ + ':' + str(exc)
        raise
    finally:
        save(dest / 'summary.json', {
            'outcomes': outcomes, 'planned_cases': CASES, 'arms': ['C'],
            'undispatched_cases': [cid for cid in CASES if cid not in {r['case_id'] for r in outcomes}],
            'paid_calls': len(provider.receipts), 'new_accounted_usd': provider.spent,
            'cumulative_accounted_usd': prior + provider.spent,
            'usage': {cid + '/' + arm: row for (cid, arm), row in provider.usage.items()},
            'elapsed_seconds': time.monotonic() - started, 'exception': error,
            'service_halted':provider.halt,'billing_hold':provider.billing_hold,
            'unknown_usage_reserves':provider.unknown_requests,
            'failed_case_keys':[list(k) for k in sorted(provider.blocked_cases)],
            'billing_authorization_mode': MODE, 'independent_quality_score': None,
            'exposed_development_only': True, 'cost_matched_comparison': False,
            'old_run_resumed': False})
        verify()
        save(dest / 'preservation.json', {'old_and_new_frozen_files_unchanged': True,
             'checked_files': len(frozen['files'])})


if __name__ == '__main__':
    main()
