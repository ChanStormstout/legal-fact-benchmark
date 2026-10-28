"""Offline integrity and arithmetic checks for the archived V51 development table."""
import csv
import hashlib
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / 'outputs/rapido-v51-ten-case-development-2026-10-28-v1'


def read(path):
    return json.loads(path.read_text())


def same(a, b):
    return len(a) == len(b) and all(math.isclose(x, y, abs_tol=1e-9) for x, y in zip(a, b))


def main():
    manifest = read(ROOT / 'SNAPSHOT_MANIFEST.json')
    for entry in manifest['files']:
        file = ROOT / entry['path']
        assert file.is_file(), entry['path']
        actual = hashlib.sha256(file.read_bytes()).hexdigest()
        assert actual == entry['source_sha256'] == entry['published_sha256'], entry['path']
    data = read(ROOT / 'experiment-data.json')
    original = read(ROOT / 'records/rapido-source-plan-direct-edit-v51-2026-10-28-v1/private/experiment-tables-2026-10-28-v9/experiment-data.json')
    assert len(data['rows']) == len(original['rows']) == 50
    assert sum(row['report_available'] for row in data['rows']) == 48
    assert len({(row['case_id'], row['method']) for row in data['rows']}) == 50
    indexed = {(row['case_id'], row['method']): row for row in data['rows']}
    receipts = set()
    for row, raw in zip(data['rows'], original['rows']):
        for key in ['case_id', 'method', 'R', 'R_counts', 'P', 'P_counts', 'H',
                    'serious_error_observed', 'serious_error_unresolved',
                    'report_sha256', 'full_chain_completed', 'report_available']:
            assert row[key] == raw[key], (row['case_id'], row['method'], key)
        if row['report_available']:
            report = ROOT / row['report_path']
            assert hashlib.sha256(report.read_bytes()).hexdigest() == row['report_sha256']
            r = row['R_counts']
            if r is not None:
                assert same(row['R'], [r['correct'] / r['total'],
                                      (r['correct'] + r.get('unresolved', 0)) / r['total']])
            p = row['P_counts']
            if row['P'] is not None:
                assert p.get('inventory_complete') is not False
                assert same(row['P'], [p['supported'] / p['total'],
                                      (p['supported'] + p.get('unresolved', 0)) / p['total']])
                if row['R'] is not None:
                    harmonic = [100 * 2 * r * p / (r + p) if r + p else 0
                                for r, p in zip(row['R'], row['P'])]
                    assert same(row['H'], harmonic), (row['case_id'], row['method'], 'H')
                else:
                    assert row['H'] is None, (row['case_id'], row['method'], 'missing R')
            else:
                assert row['H'] is None, (row['case_id'], row['method'], 'missing axis')
        else:
            assert row['R'] == [0, 0] and row['H'] == [0, 0] and row['P'] is None
        for receipt in row['resources']['receipts']:
            assert (ROOT / receipt).is_file()
            receipts.add(receipt)
        if row['method'] == 'A0':
            assert row['resources']['calls'] == 1
            request = read((ROOT / row['resources']['receipts'][0]).parent / 'request.json')
            assert request['model'] == 'Qwen/Qwen3.8-Flash'
            assert request['max_tokens'] == 16384
            assert len(request['messages']) == 2 and 'response_format' not in request
    assert len(receipts) == data['physical_unique_resources']['calls'] == 68
    f_rows = [row for row in data['rows'] if row['method'] == 'F']
    assert sum(row['full_chain_completed'] for row in f_rows) == 9
    assert sum(row['report_sha256'] == indexed[row['case_id'], 'P']['report_sha256']
               for row in f_rows) == 6
    assert indexed['1388066', 'F']['R'][1] < indexed['1388066', 'A0']['R'][0]
    assert indexed['406910', 'A0']['H'] is None and indexed['1388066', 'A0']['H'] is None
    with (ROOT / 'comparison.csv').open(newline='') as file:
        assert len(list(csv.DictReader(file))) == 50
    print(json.dumps({'status': 'PASS', 'exact_archived_files': len(manifest['files']),
                      'endpoint_slots': 50, 'reports': 48, 'unique_calls': 68,
                      'ordinary_A0_calls': 10, 'new_model_calls': 0,
                      'semantic_legal_validation': False}))


if __name__ == '__main__':
    main()
