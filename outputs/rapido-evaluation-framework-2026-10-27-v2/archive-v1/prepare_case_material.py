"""Copy permitted evidence and existing outputs for offline, source-bound evaluation."""
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
V38 = BASE.parent / 'rapido-source-first-complete-report-v38-2026-10-27-v1'
CASE = V38 / 'private/real-continuation-1251841-v1/cases/1251841'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

if __name__ == '__main__':
    dest = BASE / 'case1251841'
    dest.mkdir(exist_ok=False)
    manifest = json.loads((V38 / 'input-manifest.json').read_text())
    item = next(row for row in manifest['cases'] if row['case_id'] == '1251841')
    source = Path(item['snapshot_path'])
    assert sha(source) == item['file_sha256']
    snapshot = json.loads(source.read_text())
    permitted = {ref: row for ref, row in snapshot['directory'].items() if row['domain'] in ('CASE', 'LAW')}
    (dest / 'allowed-sources.json').write_text(json.dumps({
        'case_id':'1251841', 'question':snapshot['question'], 'scope':snapshot['scope'],
        'parent_snapshot':str(source), 'parent_sha256':sha(source), 'sources':permitted,
        'no_hidden_target_or_reference_imported':True
    }, ensure_ascii=False, indent=2))
    reports = {
        'A0': CASE / 'A0/final-report.txt',
        'C38_candidate': CASE / 'C/final-report.txt',
        'C38_delivered': CASE / 'C/qualified-report.txt',
    }
    saved = {}
    for key,path in reports.items():
        new = dest / (key + '.txt')
        new.write_bytes(path.read_bytes())
        saved[key] = {'parent':str(path), 'path':str(new), 'sha256':sha(new)}
    saved['frozen_V38'] = {'path':str(V38/'freeze.json'), 'sha256':sha(V38/'freeze.json')}
    (dest / 'manifest.json').write_text(json.dumps(saved, indent=2))
    print(json.dumps({'outputs':list(reports), 'permitted_sources':len(permitted), 'new_model_calls':0}))
