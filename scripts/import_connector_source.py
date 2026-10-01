"""Import a complete PDF text export while retaining printed PDF page boundaries."""
import argparse
import json
import re
from pathlib import Path
from legal_bench.core import make_source, digest, write_new

p = argparse.ArgumentParser()
p.add_argument('input'); p.add_argument('--case-id', required=True); p.add_argument('--out', required=True)
p.add_argument('--terminal-reviewed', action='store_true', help='Set only after inspecting beginning and terminal disposition')
args = p.parse_args()
raw = Path(args.input).read_bytes(); data = json.loads(raw)
text = data['text']
pattern = r'Indian Kanoon\s*-\s*https?://indiankanoon\.org/doc/' + re.escape(args.case_id) + r'/\s+'
markers = list(re.finditer(pattern, text))
pages, start = [], 0
for number, marker in enumerate(markers, 1):
    # The provider concatenates a footer number with the next page's first word/number.
    # Consume the expected page token only, preserving the next page's text.
    if not text[marker.end():].startswith(str(number)):
        raise SystemExit('Nonconsecutive footer sequence')
    pages.append(text[start:marker.start()])
    start = marker.end() + len(str(number))
if not pages or text[start:].strip():
    raise SystemExit('PDF page sequence cannot be verified; do not mark complete')
s = make_source(args.case_id, '', data['url'], digest(raw), pages)
s['source_completeness'] = 'VERIFIED_FULL' if args.terminal_reviewed else 'REQUIRES_REVIEW'
s['completeness_basis'] = {'method': 'connector PDF text; contiguous printed footer pages; terminal disposition inspected',
                           'page_count': len(pages), 'raw_pdf_downloaded': False,
                           'limitation': 'Text extraction, not visual page comparison; source_sha256 hashes connector export'}
write_new(args.out, s)
print(json.dumps({'pages': len(pages), 'paragraphs': len(s['paragraphs']), 'out': args.out}))
