"""One entry for source tasks, persisted model ingress, graphs, proofs and delivery."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.workflow_v7 import initialize, advance, ingest, verify, revise, KINDS


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    a = sub.add_parser('init'); a.add_argument('--spec', required=True); a.add_argument('--out', required=True)
    for name in ('advance', 'verify'):
        a = sub.add_parser(name); a.add_argument('workspace')
    a = sub.add_parser('ingest'); a.add_argument('workspace'); a.add_argument('kind', choices=(*KINDS, 'policy'))
    a.add_argument('--response', required=True); a.add_argument('--metadata', required=True)
    a = sub.add_parser('revise'); a.add_argument('parent'); a.add_argument('--spec', required=True)
    a.add_argument('--out', required=True); a.add_argument('--reason', required=True)
    args = p.parse_args()
    try:
        if args.action == 'init': result = initialize(args.spec, args.out)
        elif args.action == 'advance': result = advance(args.workspace)
        elif args.action == 'verify': result = verify(args.workspace)
        elif args.action == 'ingest': result = ingest(args.workspace, args.kind, args.response, args.metadata)
        else: result = revise(args.parent, args.spec, args.out, args.reason)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(json.dumps({'status': 'FAILED', 'answer': None, 'reason': str(exc)}, ensure_ascii=False))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
