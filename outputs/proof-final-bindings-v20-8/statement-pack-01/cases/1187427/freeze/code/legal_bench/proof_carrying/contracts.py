"""Wire contracts reuse the existing strict JSON validator and durable writer."""
import hashlib
import json
from pathlib import Path

from legal_bench.irac_application.contract_v5 import digest
from legal_bench.irac_application.aligned_v2_runtime import atomic_json
from legal_bench.rules_verdict_v1.contracts import obj, array, string, enum, validate

STATES = ('TRUE', 'FALSE', 'UNKNOWN', 'CONFLICTED')
CONCLUSIONS = ('SPECIFIC_AUTHORIZATION_COVERS_ENTRY', 'NO_AUTHORIZATION_EXISTS',
               'FINAL_LIABILITY', 'DEMO_ISSUE_CONDITION_MET')


def content_hash(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False))


def byte_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_once(path, value):
    path = Path(path)
    if path.exists():
        raise FileExistsError('IMMUTABLE_RECORD_EXISTS: ' + str(path))
    atomic_json(path, value)


def subject_hash(record):
    return content_hash({k: v for k, v in record.items() if k != 'review_id'})


def certificate_schema():
    step = obj({'id': string(), 'rule_ref': string(), 'premise_ids': array(string(), 32),
                'depends_on': array(string(), 32),
                'bindings': obj({'person': string(), 'property': string()}),
                'proposed_result': enum(STATES)})
    request = obj({'id': string(), 'step_id': string(), 'claim': enum(CONCLUSIONS),
                   'proposed_result': enum(STATES)})
    return obj({'certificate_id': string(), 'snapshot_id': string(), 'snapshot_sha256': string(),
                'registry_sha256': string(), 'policy_sha256': string(),
                'mode': enum(('TEACHING', 'LEGAL')),
                'steps': array(step, 64), 'requests': array(request, 64)})


def validate_certificate(value):
    validate(value, certificate_schema())
    for key in ('steps', 'requests'):
        ids = [v['id'] for v in value[key]]
        if not ids or any(not i for i in ids) or len(set(ids)) != len(ids):
            raise ValueError('EMPTY_OR_DUPLICATE_' + key.upper())
    for step in value['steps']:
        if len(set(step['premise_ids'])) != len(step['premise_ids']):
            raise ValueError('DUPLICATE_PREMISE')


def read_json(path):
    return json.loads(Path(path).read_text())
