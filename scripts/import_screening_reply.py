"""Import a saved actual model reply without rewriting its contents or accepting a sample."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.core import read, digest, write_new
from legal_bench.source_screening import validate_screening_reply

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
if task['batch_id'] != args.batch or submission['batch_id'] != args.batch:
    raise ValueError('Wrong submission batch')
if submission.get('prompt_sha256') != task['prompt_sha256']:
    raise ValueError('Submission needs the exact task hash')
if digest((folder / 'task.txt').read_bytes()) != task['prompt_sha256']:
    raise ValueError('Prompt file changed')
if not submission.get('conversation_url', '').startswith('https://chatgpt.com/c/'):
    raise ValueError('Missing actual conversation URL')
if Path(args.attempt).name != args.attempt:
    raise ValueError('Attempt must be a simple folder name')
incoming = Path(args.reply).read_bytes()
out = folder / args.attempt
out.mkdir(parents=True, exist_ok=True)
raw = out / 'download.json'
if raw.exists() and raw.read_bytes() != incoming:
    raise ValueError('Different reply; use a new attempt version')
if not raw.exists():
    with raw.open('xb') as f: f.write(incoming)
sources = [read(root / 'sources' / cid / 'segments.json') for cid in task['case_ids']]
try:
    reply = __import__('json').loads(incoming)
    validation = validate_screening_reply(reply, task, sources)
except (ValueError, TypeError) as error:
    reply = None
    validation = {'valid': False, 'errors': ['Cannot import reply: ' + str(error)]}
manifest = {'batch_id': args.batch, 'raw_reply_sha256': digest(incoming),
            'prompt_sha256': task['prompt_sha256'], 'submission_sha256': digest(submission),
            'source_hashes': task['source_hashes'], 'conversation_url': submission['conversation_url'],
            'validation': validation, 'state': 'ANCHORED_SCREENING_REFERENCE' if validation['valid'] else 'FORMAT_OR_ANCHOR_REPAIR_REQUIRED',
            'label_origin': 'MODEL_SOURCE_SCREEN_NOT_HUMAN_GOLD',
            'sample_selected': False, 'cross_case_group_review_complete': False}
write_new(out / 'import-manifest.json', manifest)
if validation['valid']: write_new(out / 'screening-reference.json', reply)
print(__import__('json').dumps(manifest, ensure_ascii=False))
if not validation['valid']: raise SystemExit(2)
