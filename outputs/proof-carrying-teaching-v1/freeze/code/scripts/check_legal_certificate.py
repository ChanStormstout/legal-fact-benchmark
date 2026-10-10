"""Separate process entry: no proposal engine, model or spectral import."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.checker import check
from legal_bench.proof_carrying.contracts import read_json


def main():
    p = argparse.ArgumentParser()
    p.add_argument('certificate'); p.add_argument('--trust-root', required=True)
    p.add_argument('--mode', choices=['TEACHING', 'LEGAL'], default='TEACHING')
    p.add_argument('--current-snapshot')
    args = p.parse_args()
    result = check(read_json(args.certificate), args.trust_root, mode=args.mode, current_snapshot=args.current_snapshot)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] in ('CHECKED', 'CONDITIONAL', 'INCOMPLETE', 'MIXED') else 2


if __name__ == '__main__':
    sys.exit(main())
