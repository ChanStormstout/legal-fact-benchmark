"""Extend byte-identical V48 methods; never regenerate its two development cases."""
import sys, os, ast, copy, json, re
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))
from common import read, save, write, filehash, utc
from transport import Client, service_metadata
from prompts import TRUST, PLAN, WRITE_DRAFT
from pipeline import execute

V48 = ROOT.parent / 'rapido-content-preserving-routes-v48-2026-10-27-v1'
V47 = ROOT.parent / 'rapido-ontology-specialist-review-v47-2026-10-27-v1'
WORK = ROOT / 'private/ten-case-transfer-v1'


def protect():
    for path, expected in read(ROOT / 'protected-inputs.json').items():
        assert filehash(path) == expected, path
    for filename, expected in read(ROOT / 'method-identity.json')['copied_src'].items():
        assert filehash(ROOT / 'src' / filename) == expected
        assert filehash(V48 / 'src' / filename) == expected


def ordinary_request(dossier):
    template = read(ROOT / 'baseline-template.json')
    request = copy.deepcopy(template['parameters'])
    sources = '\n\n'.join(
        f'[{sid} | {source["locator"]}]\n{source["text"]}'
        for sid, source in dossier['sources'].items())
    message = ('Question:\n' + dossier['question'] + '\n\nScope:\n' +
               dossier['scope'] + '\n\nAllowed case materials and law:\n' + sources)
    request['messages'] = [dict(role='system', content=template['system']),
                           dict(role='user', content=message)]
    return request


def offline():
    protect()
    cfg = read(ROOT / 'protocol.json')
    template = read(ROOT / 'baseline-template.json')
    reference_dir = V47 / 'private/two-case-qwen38-development-v1/transport/calls'
    reference_headers = {}
    baseline_proof = []
    for cid in ('1251841', '1252014'):
        request_path = next(reference_dir.glob('*-' + cid + '-A0/request.json'))
        previous = read(request_path)
        headers = dict(re.findall(r'^\[([SL][0-9a-f]{12}) \| ([^\n]+)\]$',
                                  previous['messages'][1]['content'], re.M))
        dossier = read(V48 / 'inputs' / (cid + '.json'))
        for sid, source in dossier['sources'].items():
            if source['domain'] == 'LAW':
                source['locator'] = headers[sid]
                assert sid not in reference_headers or reference_headers[sid] == headers[sid]
                reference_headers[sid] = headers[sid]
        assert ordinary_request(dossier) == previous
        baseline_proof.append(dict(case_id=cid, original_request=str(request_path),
                                   original_sha256=filehash(request_path), exact_sender_match=True,
                                   new_inference_calls=0))
    client = Client(cfg, ROOT / 'private/unused-offline-transport')
    rows = []
    for cid in cfg['case_ids']:
        assert cid not in ('1251841', '1252014')
        dossier = read(ROOT / 'inputs' / (cid + '.json'))
        assert all(s['domain'] in ('CASE', 'LAW') for s in dossier['sources'].values())
        a0 = ordinary_request(dossier)
        assert a0['max_tokens'] == cfg['stage_output_caps']['A0'] == 16384
        assert 'response_format' not in a0 and len(a0['messages']) == 2
        assert a0['messages'][0]['content'] == template['system']
        for sid, source in dossier['sources'].items():
            marker = f'[{sid} | {source["locator"]}]\n{source["text"]}'
            assert marker in a0['messages'][1]['content']
        initial_requests = []
        for arm, system, material, cap in [
                ('A0', None, a0, 16384),
                ('P-plan', TRUST + '\n' + PLAN, dossier, cfg['stage_output_caps']['plan']),
                ('E-draft', TRUST + '\n' + WRITE_DRAFT, dossier, cfg['stage_output_caps']['draft'])]:
            wire, body, check = client.preflight(system, material, cap)
            assert check['fits'] and wire['model'] == cfg['parameters']['model']
            assert not wire['reasoning']['enabled']
            if arm != 'A0':
                assert json.loads(wire['messages'][1]['content']) == dossier
            initial_requests.append(dict(arm=arm, **check))
        save(ROOT / 'inputs' / (cid + '-A0-request.json'), a0)
        rows.append(dict(case_id=cid, source_count=len(dossier['sources']),
                         text_chars=sum(len(s['text']) for s in dossier['sources'].values()),
                         request_checks=initial_requests))
    prior = read(V48 / 'private/two-route-development-v1/summary.json')
    a0_registry = read(V47 / 'private/baseline-registry-qwen38.json')
    observed_per_case = (prior['new_usd'] + sum(
        x['cost_usd'] for x in a0_registry['baselines'].values())) / 2
    save(ROOT / 'budget-forecast.json', dict(
        at=utc(), observed_two_case_mean_six_calls_usd=observed_per_case,
        simple_ten_case_extrapolation_usd=observed_per_case * 10,
        estimate_not_hard_completion_guarantee=True, hard_dispatch_cap_usd=cfg['max_new_usd'],
        unknown_usage_charged_at_current_call_reservation=True,
        later_model_generated_plan_expansion_checked_at_actual_dispatch=True,
        no_truncation_no_retry=True))
    save(ROOT / 'offline-entry-acceptance.json', dict(
        at=utc(), sender_and_whole_cohort_input_acceptance=True, new_model_calls=0,
        baseline_sender_proof=baseline_proof, rows=rows,
        method_and_transport_code_byte_identical_to_V48=True,
        no_synthetic_legal_answers=True,
        new_case_semantic_quality_not_yet_evaluated=True,
        this_is_not_a_new_case_end_to_end_model_acceptance=True))
    protect()
    print('ENTRY_AND_SOURCE_PARITY_ACCEPTANCE_COMPLETE', len(rows), flush=True)


def freeze():
    protect()
    assert read(ROOT / 'offline-entry-acceptance.json')['sender_and_whole_cohort_input_acceptance']
    save(ROOT / 'service-metadata-frozen.json', service_metadata())
    files = [ROOT / 'run.py', *(ROOT / 'src').glob('*.py'), *(ROOT / 'inputs').glob('*.json'),
             *[ROOT / name for name in ('protocol.json', 'baseline-template.json',
               'source-provenance.json', 'protected-inputs.json', 'method-identity.json',
               'offline-entry-acceptance.json', 'budget-forecast.json',
               'service-metadata-frozen.json', 'README.txt')]]
    for path in files:
        if path.suffix == '.py':
            ast.parse(path.read_text())
    save(ROOT / 'freeze.json', dict(at=utc(), files={str(p.relative_to(ROOT)):filehash(p) for p in files}))
    print('FROZEN', len(files), flush=True)


def export_prefix(cid):
    parent = WORK / 'cases' / cid
    candidate = parent / 'E/candidate-report.txt'
    if not candidate.exists():
        return
    receipts = list((WORK / 'transport/calls').glob('*-' + cid + '-E-draft/receipt.json'))
    if len(receipts) != 1 or read(receipts[0]).get('status') != 'OK':
        return
    raw = read(receipts[0].with_name('parsed.json'))
    assert raw['report'] == candidate.read_text()
    dest = parent / 'C0'
    dest.mkdir(exist_ok=True)
    if not (dest / 'final-report.txt').exists():
        (dest / 'final-report.txt').write_bytes(candidate.read_bytes())
        save(dest / 'outcome.json', dict(case_id=cid, method='C0', final_report_available=True,
              report_sha256=filehash(candidate), own_E_draft_endpoint=True,
              source_receipt=str(receipts[0]), resource_shared_with_E=True,
              no_extra_inference_call=True, not_an_enhanced_A0=True, quality=None))


def finalize(client, results, interrupted):
    cfg = read(ROOT / 'protocol.json')
    rows = []
    for cid in cfg['case_ids']:
        export_prefix(cid)
        for arm in ('A0', 'P', 'C0', 'E'):
            path = WORK / 'cases' / cid / arm
            report = path / 'final-report.txt'
            meta = read(path / 'outcome.json') if (path / 'outcome.json').exists() else {}
            rows.append(dict(case_id=cid, arm=arm, final_report_available=report.exists(),
                report_sha256=filehash(report) if report.exists() else None,
                report_chars=len(report.read_text()) if report.exists() else 0,
                outcome=meta, quality=None))
    ledger = client.ledger()
    save(WORK / 'outcome.json', dict(at=utc(), results=results, slots=rows,
        resources=ledger, interrupted=interrupted, source_model='Qwen/Qwen3.8-Flash',
        prior_two_cases_rerun=False, same_method_development_extension=True,
        R=None, H=None, goal_achieved=False))
    save(WORK / 'summary.json', dict(at=utc(), slot_count=len(rows),
        final_reports=sum(r['final_report_available'] for r in rows),
        report_counts={arm:sum(r['arm']==arm and r['final_report_available'] for r in rows)
                       for arm in ('A0','P','C0','E')},
        new_calls=ledger['new_calls'], conservative_new_usd=ledger['new_conservative_usd'],
        service_halted=client.halt, interrupted=interrupted,
        slot_results=rows, R=None, H=None, independent_test=False, goal_achieved=False))


def run():
    protect()
    for rel, expected in read(ROOT / 'freeze.json')['files'].items():
        assert filehash(ROOT / rel) == expected, rel
    cfg = read(ROOT / 'protocol.json')
    WORK.mkdir(parents=True, exist_ok=False)
    client = Client(cfg, WORK / 'transport')
    results = []
    interrupted = None
    save(WORK / 'started.json', dict(at=utc(), pid=os.getpid(),
        freeze_sha256=filehash(ROOT / 'freeze.json'), prior_cases_rerun=False))
    try:
        save(WORK / 'service-metadata-at-start.json', service_metadata())
        for cid in cfg['case_ids']:
            dossier = read(ROOT / 'inputs' / (cid + '.json'))
            for arm in cfg['arm_order'][cid]:
                path = WORK / 'cases' / cid / arm
                if client.halt:
                    path.mkdir(parents=True, exist_ok=False)
                    out = dict(case_id=cid, method=arm, status='NOT_RUN_GLOBAL_SERVICE_HALT',
                               final_report_available=False, quality=None)
                    save(path / 'outcome.json', out)
                elif arm == 'A0':
                    path.mkdir(parents=True, exist_ok=False)
                    save(path / 'input.json', dossier)
                    try:
                        value = client.call(cid + '-A0', None,
                            read(ROOT / 'inputs' / (cid + '-A0-request.json')), 16384)
                        write(path / 'final-report.txt', value['text'])
                        out = dict(case_id=cid, method=arm, final_report_available=True,
                            ordinary_calls=1, helpers=0, quality=None)
                    except Exception as exc:
                        out = dict(case_id=cid, method=arm, final_report_available=False,
                            error=type(exc).__name__ + ':' + str(exc), quality=None)
                    save(path / 'outcome.json', out)
                else:
                    out = execute(client, dossier, arm, path, cfg['stage_output_caps'])
                results.append(out)
                if arm == 'E':
                    export_prefix(cid)
                save(WORK / (cid + '-' + arm + '-terminal.json'), out)
                finalize(client, results, interrupted)
    except BaseException as exc:
        interrupted = type(exc).__name__ + ':' + str(exc)
        raise
    finally:
        finalize(client, results, interrupted)
        protect()
        save(WORK / 'exit.json', dict(at=utc(), terminal=True, interrupted=interrupted,
            all_slots_attempted=len(results)==len(cfg['case_ids'])*3,
            service_halted=client.halt))
    print('DEVELOPMENT_BATCH_TERMINAL', flush=True)


if __name__ == '__main__':
    {'offline':offline, 'freeze':freeze, 'run':run}[sys.argv[1]]()
