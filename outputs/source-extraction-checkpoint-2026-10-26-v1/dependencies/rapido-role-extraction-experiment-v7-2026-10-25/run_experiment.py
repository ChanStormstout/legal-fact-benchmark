"""Isolated source-stage runner. No authorization means no provider or API import."""
import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
from source_reading import run, digest, save_new


def read(path):
    return json.loads(Path(path).read_text())


def verify():
    manifest = read(ROOT/'freeze.json')
    for relative, expected in manifest['files'].items():
        if hashlib.sha256((REPO/relative).read_bytes()).hexdigest() != expected:
            raise ValueError('FROZEN_FILE_CHANGED:' + relative)
    return digest(manifest)


def dispatch_plan(cfg):
    result = {}
    for cid in cfg['cases']:
        data = read(ROOT/'private/inputs'/f'{cid}.json')
        n = math.ceil(len(data['sources'])/cfg['paragraphs_per_batch'])
        result[cid] = [f'{stage}-{i:03d}' for i in range(n) for stage in ['reading', 'review']]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--authorization', type=Path)
    args = parser.parse_args()
    cfg = read(ROOT/'protocol.json'); frozen_hash = verify(); plan = dispatch_plan(cfg)
    if args.authorization is None:
        print(json.dumps({'status': 'OFFLINE_READY_NOT_MODEL_VALIDATED', 'freeze_hash': frozen_hash,
                          'planned_calls': {cid: len(tags) for cid, tags in plan.items()},
                          'api_calls': 0, 'new_version_authorization_required': True}))
        return
    auth = read(args.authorization)
    if (auth.get('approved') is not True or auth.get('version') != cfg['version']
            or auth.get('freeze_hash') != frozen_hash or auth.get('case_stage_plan') != plan
            or auth.get('retain_prior_unknown_reserves') is not True
            or type(auth.get('maximum_new_usd')) not in (float, int) or auth['maximum_new_usd'] <= 0
            or type(auth.get('prior_conservative_usd')) not in (float, int) or auth['prior_conservative_usd'] < 0
            or auth.get('allow_unknown_usage_reserve_continuation') not in (True, False)):
        raise ValueError('EXPLICIT_VERSION_BOUND_COST_AND_CALL_AUTHORIZATION_REQUIRED')
    dest = ROOT/'private/model-run-v1'
    if dest.exists():
        raise ValueError('EXISTING_ATTEMPT_NOT_REPEATED')
    # Lock is shared with the original experiment runner; no parallel model work.
    import fcntl
    with (REPO/'.runtime/rapido-proof-task-api.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        sys.path[:0] = [str(ROOT), str(REPO/'outputs/rapido-ontology-source-v25-2026-10-25-v1/src'), str(REPO)]
        from role_api_provider import APIProvider
        cfg.update(execution_enabled=True, paid_api_enabled=True,
                   billing_authorization_mode='ROLE_SOURCE_TWO_CASE_APPROVAL',
                   maximum_new_usd=auth['maximum_new_usd'], prior_conservative_usd=auth['prior_conservative_usd'],
                   allow_unknown_usage_reserve_continuation=auth['allow_unknown_usage_reserve_continuation'])
        save_new(dest/'authorization.json', auth)
        provider = APIProvider(cfg, dest/'transport'); outcomes = []
        try:
            for cid in cfg['cases']:
                verify(); source = read(ROOT/'private/inputs'/f'{cid}.json')['sources']; attempted = []
                def ask(tag, request):
                    if len(attempted) >= len(plan[cid]) or tag != plan[cid][len(attempted)]:
                        raise ValueError('UNPLANNED_OR_REPEATED_STAGE')
                    if request['sources'] != source:
                        raise ValueError('ORIGINAL_INPUT_CHANGED')
                    attempted.append(tag)
                    transported = {'policy': request['policy'], 'task': request['task'], 'schema': request['schema'],
                        'material': {k: copy.deepcopy(v) for k, v in request.items() if k not in ['policy', 'task', 'schema']},
                        'output_token_cap': cfg['diagnostic_output_tokens']}
                    for attempt in range(cfg['max_technical_retries'] + 1):
                        try:
                            return provider.call(cid, 'ROLE', tag, transported, attempt)[0]
                        except Exception as exc:
                            receipts = getattr(exc, 'receipts', [])
                            last = receipts[-1] if receipts else {}
                            if (provider.dispatch_stop or last.get('no_retry')
                                    or last.get('status') not in ['FORMAT_ERROR', 'STREAM_INCOMPLETE',
                                        'STREAM_PROTOCOL_ERROR', 'CALL_TIMEOUT', 'TECHNICAL_FAILURE']
                                    or attempt >= cfg['max_technical_retries']):
                                raise
                try:
                    run(source, ask, dest/'cases'/cid, cfg['paragraphs_per_batch'])
                except Exception as exc:
                    # run() preserves the complete error and previous successful batches.
                    if not (dest/'cases'/cid/'outcome.json').exists():
                        save_new(dest/'cases'/cid/'outcome.json', {'technical_complete': False,
                                 'error': type(exc).__name__ + ':' + str(exc), 'answer': None})
                outcomes.append({'case_id': cid, **read(dest/'cases'/cid/'outcome.json')})
                if provider.dispatch_stop:
                    break
        finally:
            save_new(dest/'summary.json', {'outcomes': outcomes, 'paid_calls': len(provider.receipts),
                'new_accounted_usd': provider.spent,
                'unknown_usage_reserves': provider.unknown_requests,
                'semantic_quality': None, 'full_pipeline_run': False, 'failed_cases_not_repeated': True})
            verify()


if __name__ == '__main__':
    main()
