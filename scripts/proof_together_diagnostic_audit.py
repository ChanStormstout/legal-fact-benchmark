#!/usr/bin/env python3
"""Offline original-contract audit; never generates or repairs model output."""
import json
import sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import proof_together_diagnostic as core
from legal_bench.proof_carrying import local_pipeline_v19_compact as pipe
from legal_bench.proof_carrying.local_checker_v19_refs import check
from legal_bench.proof_carrying.repetition_v19_compact import ExpansionGuard
from legal_bench.proof_carrying.string_guard_v19_compact import StringGuard
from legal_bench.rules_verdict_v1.repetition_v9 import RepetitionAbort


def unique_errors(data, schema):
    """The inherited validator checks structure/patterns; also audit uniqueItems."""
    errors = []
    definitions = schema.get('$defs', {})
    def walk(value, spec, path):
        if '$ref' in spec:
            spec = definitions[spec['$ref'].split('/')[-1]]
        if isinstance(value, list):
            if spec.get('uniqueItems') and len({json.dumps(x,sort_keys=True) for x in value}) != len(value):
                errors.append(path)
            for i, child in enumerate(value):
                walk(child, spec.get('items', {}), path + '/' + str(i))
        elif isinstance(value, dict):
            for key, child in value.items():
                walk(child, spec.get('properties', {}).get(key, {}), path + '/' + key)
    walk(data, schema, '$')
    return errors


def audit():
    out = core.OUT / 'transport-02'
    cfg = core.read(core.BASE / 'freeze/protocol.json')
    report = []
    for task in core.read(out / 'freeze/protocol.json')['tasks']:
        dest = out / 'runs' / task['case_id'] / task['part']
        if not (dest / 'run.json').exists():
            report.append({**task, 'api': {'run_status': 'NOT_STARTED'}})
            continue
        result = core.read(dest / 'run.json')
        row = {**task, 'api': result, 'offline_guard_hits': {}}
        raw_text = (dest / 'raw-response.txt').read_text() if (dest / 'raw-response.txt').exists() else ''
        for label, guard in [('record', ExpansionGuard()), ('string', StringGuard())]:
            try:
                guard.feed(raw_text)
            except RepetitionAbort:
                row['offline_guard_hits'][label] = guard.hit
        if (dest / 'parsed.json').exists():
            raw = core.read(dest / 'parsed.json')
            duplicates = unique_errors(raw, core.read(out / task['task'] / 'schema.json'))
            row['unique_items_violations'] = duplicates
            fixture = core.read(core.BASE / 'preparation/inputs' / task['case_id'] / 'fixture.json')
            slot = next(x for x in cfg['local_generation_slots'] if x['case_id'] == task['case_id'] and x.get('part', {}).get('id') == task['part'])
            view = {**fixture['case'], 'segments': [x for x in fixture['case']['segments'] if x['id'] in slot['part']['source_ids']]}
            converted, ledger = pipe.convert(raw, view, pipe.VERSION)
            imported = pipe.independent_import(raw, converted, view, pipe.VERSION)
            merged, merge_ledger = pipe.merge_parts([(task['part'], converted)])
            production = pipe.apply_connection_decisions(fixture['case'], fixture['rules'], merged)
            independent = check(fixture['case'], fixture['rules'], merged, None, production)
            core.save(dest / 'offline-audit.json', {'conversion': ledger, 'merge': merge_ledger,
                                                    'independent_import': imported, 'production': production,
                                                    'independent_check': independent})
            core.save(dest / 'record-source-map.json', [
                {'premise': unit['premise'], 'records': unit['records']}
                for unit in converted['analyses']])
            row.update(analyses=len(raw['analyses']),
                       records=sum(len(x['records']) for x in raw['analyses']),
                       uses=sum(len(x['uses']) for x in raw['analyses']),
                       dynamic_reference_states=dict(Counter(x['status'] for x in ledger if 'status' in x)),
                       independent_import=imported, independent_check=independent)
            row['schema_success_including_uniqueness'] = result['run_status'] == 'OK' and not duplicates
        report.append(row)
    core.save(core.OUT / 'comparison.json', {'tasks': report,
              'pre_model_transport_failure': core.read(core.OUT / 'runs/1954254/P01/run.json'),
              'legal_review_status': 'REQUIRES_SCOPED_SOURCE_REVIEW',
              'no_claim_of_local_fault_isolation': True,
              'reviewer': 'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD'})
    print(json.dumps([{k: v for k,v in r.items() if k not in ('api', 'task', 'original', 'independent_check')}
                      for r in report], ensure_ascii=False)[:5000])


if __name__ == '__main__':
    audit()
