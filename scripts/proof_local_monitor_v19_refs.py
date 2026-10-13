#!/usr/bin/env python3
"""Continue unchanged frozen V19 via independently frozen scheduling supplement."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import proof_local_refs_v19 as entry
from legal_bench.proof_carrying.p_monitor_v19_refs import Monitor, digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['observe', 'P'])
    args = parser.parse_args()
    path = entry.OUT / 'monitor-01/protocol-supplement.json'
    supplement = entry.read(path)
    if digest(entry.OUT / 'freeze/protocol.json') != supplement['original_protocol_sha256']:
        raise ValueError('ORIGINAL_PROTOCOL_CHANGED')
    for rel, expected in supplement['code_hashes'].items():
        if digest(ROOT / rel) != expected:
            raise ValueError('MONITOR_SUPPLEMENT_CODE_CHANGED:' + rel)
    monitor = Monitor(entry, supplement)
    report = monitor.observe()
    print(json.dumps({k: report[k] for k in ['completed_P_calls', 'P_technical_success',
          'P_technical_failure', 'rolling_guard', 'TRAIN_effective_label_counts',
          'TRAIN_source_reviewed_supervised_disputes', 'P_seconds_remaining']}, indent=2), flush=True)
    if args.action == 'observe':
        return
    if report['rolling_guard']['stop'] or report['common_engineering_exceptions']:
        print('NOT_DISPATCHED: USER_MONITOR_STOP', flush=True)
        return
    if (entry.OUT / 'PAUSE_REQUESTED.json').exists():
        raise ValueError('SAFE_PAUSE_MARKER_REQUIRES_DOCUMENTED_RESUME')
    # Frozen generation and checks are unmodified; only saved-boundary callback
    # is substituted in this new process, not in an already-running process.
    entry.schedule = monitor.schedule
    print('PHASE_RESULT', entry.run_local('P'), flush=True)


if __name__ == '__main__':
    main()
