"""Import a source-anchored provisional grouping proposal, never select a sample."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read, digest, write_new
from legal_bench.grouping_review import validate_grouping_reply

p = argparse.ArgumentParser()
p.add_argument('--root', default='outputs/benchmark-pilot-v04/sampling-v1')
p.add_argument('--batch', required=True)
p.add_argument('--reply', required=True)
p.add_argument('--attempt', default='reply-v1')
args = p.parse_args()
root = Path(args.root)
folder = root / 'web-tasks' / args.batch
task = read(folder / 'task.json')
submission = read(folder / 'submission.json')
if submission.get('prompt_sha256') != task['prompt_sha256'] or digest((folder / 'task.txt').read_bytes()) != task['prompt_sha256']:
    raise ValueError('Task or submission hash differs')
if Path(args.attempt).name != args.attempt: raise ValueError('Invalid attempt')
sources, paths = [], []
for cid in task['case_ids']:
    path = root / 'sources' / cid / 'segments.json'
    if not path.exists(): path = Path('outputs/semantic-audit-side-20260930') / cid / 'source.json'
    sources.append(read(path)); paths.append(path)
raw = Path(args.reply).read_bytes()
out = folder / args.attempt
out.mkdir(parents=True, exist_ok=True)
destination = out / 'raw.json'
if destination.exists() and destination.read_bytes() != raw: raise ValueError('Use a new attempt')
if not destination.exists(): destination.write_bytes(raw)
try:
    reply = json.loads(raw)
    validation = validate_grouping_reply(reply, task, sources)
except (ValueError, TypeError) as error:
    validation = {'valid': False, 'errors': [str(error)]}
manifest = {'batch_id': args.batch, 'validation': validation, 'raw_sha256': digest(raw),
            'prompt_sha256': task['prompt_sha256'], 'submission_sha256': digest(submission),
            'conversation_url': submission['conversation_url'],
            'source_file_hashes': {str(path): digest(path.read_bytes()) for path in paths},
            'state': 'ANCHORED_GROUPING_PROPOSAL' if validation['valid'] else 'REPAIR_REQUIRED',
            'label_origin': 'MODEL_REVIEW_NOT_HUMAN_GOLD', 'sample_selected': False}
write_new(out / 'import-manifest.json', manifest)
if validation['valid']: write_new(out / 'grouping-proposal.json', reply)
print(json.dumps(manifest, ensure_ascii=False))
if not validation['valid']: raise SystemExit(2)
