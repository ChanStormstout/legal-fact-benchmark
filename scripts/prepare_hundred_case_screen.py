"""Register a reproducible, outcome-blind source screening queue, not a frozen split."""
import argparse
import sqlite3
import json
from pathlib import Path
from legal_bench.core import read, digest, write_new
from legal_bench.sampling import candidate_queue

p = argparse.ArgumentParser()
p.add_argument('--db', default='outputs/benchmark-pilot/data/cases.sqlite')
p.add_argument('--out', default='outputs/benchmark-pilot-v04/sampling-v1')
p.add_argument('--seed', type=int, default=20260930)
args = p.parse_args()
db = Path(args.db).resolve()
with sqlite3.connect(db.as_uri() + '?mode=ro', uri=True) as connection:
    records = [json.loads(r[0]) for r in connection.execute('select raw_json from cases order by doc_id')]
dev = ['1064407', '755721', '184866874', '934120', '1988625']
q = candidate_queue(records, dev, 100, args.seed)
out = Path(args.out)
write_new(out / 'candidate-queue.json', q)
policy = {
    'version': '100-case-source-screen-v1', 'target_counts': {'development': 5, 'check': 100},
    'database_sha256': digest(db.read_bytes()), 'queue_sha256': digest(q),
    'request_family': 'TENANCY_EVICTION_OR_RECOVERY_OF_POSSESSION',
    'include': 'Original dispute involves landlord or lessor seeking tenant or lessee eviction/ejectment or return of leased immovable property; a Supreme Court appeal or subsequent stage concerning this request qualifies.',
    'exclude': ['Only a cited precedent has this request', 'Pure acquisition, revenue, title or adverse-possession dispute without this tenancy request', 'Non-Supreme-Court judgment', 'Unable to obtain complete judgment'],
    'do_not_exclude': ['Hard cases', 'Unknown dates', 'Conflicting assertions', 'Multiple objects', 'Partial success', 'Unsupported representations', 'Agricultural or different statutory tenancy regimes: record regime and report scope'],
    'unit': 'One independent dispute; record all requests, primary = first explicitly described request in this family at the present stage',
    'grouping': 'Review parties, property description, suit/appeal/docket IDs, earlier and later judgments; cross-check all selected candidates and five development disputes before declaring independent',
    'fallback': 'If fewer than 100 independent source-confirmed cases exist, report shortfall; any broader request-family protocol gets a new version before annotation',
    'candidate_fields': ['facts', 'issues'], 'candidate_fields_are_full_source': False,
    'model': 'ChatGPT Web ordinary GPT-6/High where actually exposed; save observed UI name, no Pro requirement, no paid API',
    'annotation_origin': 'MODEL_GENERATED_MODEL_REVIEWED_NOT_HUMAN_GOLD',
    'sequence': ['source screening in fixed rank order', 'cross-case dispute grouping', 'freeze sample and method files', 'A and B independent extraction', 'bounded discrepancy/source review', 'frozen comparisons and development-derived pattern replication'],
    'batch_size': 10, 'repair_limit_per_discrepancy': 2,
    'check_data_may_generate_patterns': False, 'development_is_flow_pilot_not_same_request_cohort': True,
    'state': 'SAMPLING_POLICY_REGISTERED_NOT_METHOD_OR_SAMPLE_FREEZE'}
write_new(out / 'sampling-policy.json', policy)
write_new(out / 'initial-screening-batch.json', {'state': 'PROVISIONAL_CANDIDATES_NOT_FROZEN_CHECK_SET', 'cases': q['cases'][:100], 'reserve_starts_at_rank': 101})
write_new(out / 'input-manifest.json', {'db': str(db), 'sha256': policy['database_sha256'], 'script_sha256': digest(Path(__file__).read_bytes()), 'sampling_code_sha256': digest(Path('legal_bench/sampling.py').read_bytes())})
print(json.dumps({'candidate_count': len(q['cases']), 'target': 100, 'state': q['state'], 'out': str(out)}))
