"""Import explicitly identified UI downloads; never infer the latest file is correct."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.annotation_v2 import import_files
from legal_bench.core import read, write_new


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='outputs/benchmark-pilot-v03')
    parser.add_argument('--case', required=True)
    parser.add_argument('--pass-name', choices=['A', 'B'], required=True)
    parser.add_argument('--annotation', required=True)
    parser.add_argument('--notes', required=True)
    args = parser.parse_args()
    root = Path(args.root)
    submission = read(root / 'next-dev-tasks' /
                      ('%s-%s-submission.json' % (args.case, args.pass_name)))
    task = read(root / 'next-dev-tasks' / (submission['task_id'] + '.json'))
    dest = root / 'downloads' / args.case / args.pass_name
    dest.mkdir(parents=True, exist_ok=True)
    for name, path in [('annotation', args.annotation), ('review_notes', args.notes)]:
        data = Path(path).read_bytes()
        parsed = json.loads(data)
        if str(parsed.get('case_id')) != args.case:
            raise ValueError('Downloaded file belongs to another case: ' + path)
        target = dest / (name + '.json')
        if target.exists() and target.read_bytes() != data:
            raise ValueError('Immutable download differs; choose a new version')
        if not target.exists():
            target.write_bytes(data)
    metadata_path = dest / 'retrieval.json'
    if metadata_path.exists():
        metadata = read(metadata_path)
    else:
        metadata = dict(submission)
        metadata['retrieved_at'] = datetime.now(timezone.utc).isoformat()
        metadata['retrieval_state'] = 'FILES_DOWNLOADED_VIA_UI'
        write_new(metadata_path, metadata)
    record = import_files(task, read(root / 'sources' / (args.case + '.segmented.json')),
                          dest / 'annotation.json', dest / 'review_notes.json',
                          metadata, root / 'imports')
    print(json.dumps({'case_id': args.case, 'pass': args.pass_name,
                      'state': record['state'], 'validation': record.get('validation')},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
