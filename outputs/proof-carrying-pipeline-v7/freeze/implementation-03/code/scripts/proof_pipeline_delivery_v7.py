"""Adapt existing research records into the unified workflow, without new inference."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.contracts import read_json, byte_hash, write_once
from legal_bench.proof_carrying.realcase_tasks_v2_2 import CASES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/proof-carrying-pipeline-v7'
IDS = ('789051', '1418721', '1841885', '840688', '161859415', '74028', '522414', '1144022')


def prepare():
    assert (OUT / 'registration.json').exists()
    history = {}
    cases = []
    for cid in IDS:
        target = OUT / 'inputs' / cid
        if cid in CASES:
            snapshot_path = ROOT / 'outputs/proof-carrying-checker-evaluation-v4/repair-01/policies' / (cid + '.json')
            cert_path = ROOT / 'outputs/proof-carrying-checker-evaluation-v4/natural' / cid / 'certificate.json'
            proposal = read_json(cert_path)['proposal']
            fact_path = ROOT / 'outputs/proof-carrying-realcase-v2/runs' / cid / 'facts/parsed.json'
            facts = read_json(fact_path)
            ref_path = ROOT / 'outputs/proof-carrying-realcase-v2/runs' / cid / 'reference/parsed.json'
            name, question = CASES[cid]['name'], CASES[cid]['question']
            origin = 'CACHED_V2_MODEL_DERIVATION_WITH_V3_SOURCE_REVIEW_POLICY_V4_ADDRESS_MIGRATION'
        else:
            folder = ROOT / 'outputs/proof-carrying-calibration-v6/cases' / cid / 'attributed-reconstruction'
            snapshot_path, cert_path = folder / 'snapshot.json', folder / 'certificate.json'
            proposal = read_json(folder / 'proposal.json')
            fact_path = ROOT / 'outputs/proof-carrying-calibration-v5/cases' / cid / 'facts-draft.json'
            facts = read_json(fact_path)
            ref_path = ROOT / 'outputs/proof-carrying-calibration-v6/cases' / cid / 'reference-content.json'
            scope = read_json(fact_path.parent / 'reconstruction-scope.json')
            name, question = scope['title'], scope['issue']
            origin = 'CACHED_SOURCE_REVIEWED_MAINTAINER_ASSEMBLY_NOT_NEW_MODEL_DERIVATION'
        snapshot = read_json(snapshot_path)
        # Preserve explicitly reviewed earlier revisions; raw original facts remain at their origin.
        adapted_facts = {'entities': list(snapshot['entities'].values()), 'premises': list(snapshot['premises'].values()),
                         'relations': facts['relations'], 'coverage_limits': facts['coverage_limits']}
        rules = {'rules': list(snapshot['rules'].values()), 'coverage_limits': ['Existing research translations; original approval status retained.']}
        excluded = {'case_id', 'stage', 'jurisdiction', 'sources', 'documents', 'entities', 'premises', 'rules', 'snapshot_id'}
        policy = {k: v for k, v in snapshot.items() if k not in excluded}
        for kind, value in [('sources', snapshot['sources']), ('facts', adapted_facts), ('rules', rules), ('policy', policy), ('derivation', proposal)]:
            write_once(target / (kind + '.json'), value)
        documents = []
        for doc in snapshot['documents']:
            p = (snapshot_path.parent / doc['path']).resolve()
            if byte_hash(p) != doc['sha256']: raise ValueError('OLD_SOURCE_HASH_CONFLICT')
            documents.append({'path': str(p), 'sha256': doc['sha256']})
            history[str(p.relative_to(ROOT))] = byte_hash(p)
        cached = {k: {'path': k + '.json', 'origin': origin if k == 'derivation' else 'EXPLICIT_EXISTING_RECORD_ADAPTER',
                       'upstream_snapshot': str(snapshot_path.relative_to(ROOT))} for k in ('facts', 'rules', 'policy', 'derivation')}
        cached['reference'] = {'path': str(ref_path), 'origin': 'EXISTING_REFERENCE_TEXT_NO_REGENERATION',
                               'historical_contract_status': 'SEE_ORIGINAL_IMPORT_UNCHANGED'}
        spec = {'case_id': cid, 'name': name, 'question': question, 'stage': snapshot['stage'],
                'jurisdiction': snapshot['jurisdiction'], 'sources': 'sources.json', 'documents': documents,
                'cached': cached, 'proposal_origin': origin,
                'source_scope': 'Exactly the prior approved reconstruction span; no added source or excerpt',
                'identity_basis': 'Existing source boundary audit plus exact restoration to original segments',
                'parent': {'snapshot': str(snapshot_path), 'sha256': byte_hash(snapshot_path)},
                'not_a_new_model_experiment': True}
        write_once(target / 'spec.json', spec)
        write_once(target / 'adapter-lineage.json', {'source_snapshot': str(snapshot_path),
            'original_fact_proposal': str(fact_path), 'original_derivation_certificate': str(cert_path),
            'input_changes': 'Only component packaging and paths; reviewed source records and rule versions are preserved verbatim.',
            'reference_used_in_graph_or_generation': False,
            'reference_has_historical_overlap_with_policy': True,
            'no_independent_accuracy_claim': True})
        for p in (snapshot_path, cert_path, fact_path, ref_path): history[str(p.relative_to(ROOT))] = byte_hash(p)
        cases.append({'case_id': cid, 'spec': str((target / 'spec.json').relative_to(ROOT)), 'origin': origin})
    # Protect all previously delivered proof-carrying artifacts, not only sampled paths.
    for folder in (ROOT / 'outputs').glob('proof-carrying-*'):
        if folder == OUT: continue
        for p in folder.rglob('*'):
            if p.is_file(): history[str(p.relative_to(ROOT))] = byte_hash(p)
    write_once(OUT / 'history-manifest.json', history)
    write_once(OUT / 'run-plan.json', {'cases': cases, 'mode': 'FULL_PIPELINE_INTEGRATION_REUSING_CACHED_RECORDS',
        'new_model_calls': 0, 'component_experiments': 0, 'change_legal_rules': False,
        'formal_approval': 'PENDING', 'no_component_benefit_scoring': True})


def run():
    plan = read_json(OUT / 'run-plan.json')
    summary = []
    for item in plan['cases']:
        dest = OUT / 'cases' / item['case_id']
        command = [sys.executable, str(ROOT / 'scripts/proof_pipeline_v7.py')]
        command += ['advance', str(dest)] if dest.exists() else ['init', '--spec', str(ROOT / item['spec']), '--out', str(dest)]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        entry = {'case_id': item['case_id'], 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
        write_once(OUT / 'invocations' / (item['case_id'] + '.json'), entry)
        parsed = json.loads(result.stdout)
        summary.append(parsed)
        print(json.dumps({'case_id': item['case_id'], 'status': parsed['status']}, ensure_ascii=False), flush=True)
    write_once(OUT / 'integration-results.json', summary)
    return summary


def verify():
    historical = read_json(OUT / 'history-manifest.json')
    changed = [p for p, h in historical.items() if byte_hash(ROOT / p) != h]
    result = {'historical_files': len(historical), 'historical_changed': changed, 'cases': []}
    for cid in IDS:
        proc = subprocess.run([sys.executable, str(ROOT / 'scripts/proof_pipeline_v7.py'), 'verify', str(OUT / 'cases' / cid)], capture_output=True, text=True)
        result['cases'].append({'case_id': cid, 'returncode': proc.returncode, 'result': json.loads(proc.stdout)})
    result['passed'] = not changed and all(c['returncode'] == 0 for c in result['cases'])
    write_once(OUT / 'delivery-validation.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result['passed']: raise ValueError('DELIVERY_INTEGRITY_FAILED')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['prepare', 'run', 'verify']); a = p.parse_args()
    {'prepare': prepare, 'run': run, 'verify': verify}[a.action]()
