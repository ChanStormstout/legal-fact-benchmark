"""Persist a separately versioned model repair with its full prompt and change log."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.annotation_v2 import import_files
from legal_bench.core import read, write_new, digest


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', default='outputs/benchmark-pilot-v03')
    p.add_argument('--case', required=True)
    p.add_argument('--pass-name', choices=['A', 'B'], required=True)
    p.add_argument('--round', type=int, choices=[1, 2], default=1)
    for field in ['annotation', 'notes', 'change-log']:
        p.add_argument('--' + field, required=True)
    args = p.parse_args()
    root = Path(args.root)
    key = '%s-%s-repair%d' % (args.case, args.pass_name, args.round)
    tasks = root / 'next-dev-tasks'
    prepared = read(tasks / (key + '.json'))
    observed = read(tasks / (key + '-submission.json'))
    task = dict(prepared, id=key, prompt=(tasks / (key + '.txt')).read_text())
    target = root / 'downloads' / args.case / args.pass_name / ('repair%d' % args.round)
    target.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, path in [('annotation', args.annotation), ('review_notes', args.notes),
                       ('change_log', args.change_log)]:
        data = Path(path).read_bytes()
        obj = json.loads(data)
        if str(obj.get('case_id')) != args.case:
            raise ValueError('Case ID missing or different in ' + name)
        dest = target / (name + '.json')
        if dest.exists() and dest.read_bytes() != data:
            raise ValueError('Refusing changed repair artifact: ' + str(dest))
        if not dest.exists():
            dest.write_bytes(data)
        hashes[name] = digest(data)
    metadata_file = target / 'retrieval.json'
    if metadata_file.exists():
        meta = read(metadata_file)
    else:
        meta = dict(observed, retrieved_at=datetime.now(timezone.utc).isoformat(),
                    output_hashes=hashes, retrieval_state='FILES_DOWNLOADED_VIA_UI')
        write_new(metadata_file, meta)
    result = import_files(task, read(root / 'sources' / (args.case + '.segmented.json')),
                          target / 'annotation.json', target / 'review_notes.json',
                          meta, root / 'imports')
    print(json.dumps({'case_id': args.case, 'pass': args.pass_name, 'round': args.round,
                      'state': result['state'], 'validation': result.get('validation')}, indent=2))


if __name__ == '__main__':
    main()
