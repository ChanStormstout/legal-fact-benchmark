"""Download public primary papers and extract text. No model or experiment calls."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request
from pypdf import PdfReader

BASE = Path(__file__).resolve().parent
PAPERS = [
    ('pyramid', 'https://aclanthology.org/N04-1019.pdf'),
    ('rose', 'https://aclanthology.org/2023.acl-long.228.pdf'),
    ('qaeval', 'https://aclanthology.org/2021.tacl-1.47.pdf'),
    ('factscore', 'https://aclanthology.org/2023.emnlp-main.741.pdf'),
    ('alce', 'https://aclanthology.org/2023.emnlp-main.398.pdf'),
    ('dfactscore', 'https://aclanthology.org/2024.findings-acl.160.pdf'),
    ('finesure', 'https://aclanthology.org/2024.acl-long.51.pdf'),
    ('rarr', 'https://aclanthology.org/2023.acl-long.910.pdf'),
    ('attribute_first', 'https://aclanthology.org/2024.acl-long.182.pdf'),
    ('qasem', 'https://aclanthology.org/2026.tacl-1.6.pdf'),
    ('fava', 'https://openreview.net/pdf?id=dJMTn3QOWO'),
    ('purr', 'https://arxiv.org/pdf/2305.14908'),
    ('self_refine', 'https://proceedings.neurips.cc/paper_files/paper/2023/file/91edff07232fb1b55a505a9e9f6c0ff3-Paper-Conference.pdf'),
    ('cannot_self_correct', 'https://openreview.net/pdf?id=IkmD3fKBPQ'),
    ('critical_survey', 'https://aclanthology.org/2024.tacl-1.78.pdf'),
    ('defacto', 'https://aclanthology.org/2023.acl-long.844.pdf'),
    ('cove', 'https://aclanthology.org/2024.findings-acl.212.pdf'),
    ('facts_grounding', 'https://arxiv.org/pdf/2501.03200'),
    ('facts_suite', 'https://arxiv.org/pdf/2512.10791'),
    ('judge_bias', 'https://proceedings.neurips.cc/paper_files/paper/2023/file/91f18a1287b398d378ef22505bf41832-Paper-Datasets_and_Benchmarks.pdf'),
    ('rubric_artifacts', 'https://arxiv.org/pdf/2609.02942'),
]

def fetch(item):
    key, url = item
    dest = BASE / 'papers' / (key + '.pdf')
    dest.parent.mkdir(exist_ok=True)
    try:
        if not dest.exists():
            req = urllib.request.Request(url, headers={'User-Agent': 'LegalAI-ResearchReview/1.0'})
            with urllib.request.urlopen(req, timeout=60) as response:
                raw = response.read()
            if not raw.startswith(b'%PDF'):
                raise ValueError('Not a PDF; original bytes not imported as paper')
            dest.write_bytes(raw)
        raw = dest.read_bytes()
        reader = PdfReader(dest)
        text = '\n\n'.join(f'=== PDF PAGE {i+1} ===\n' + (page.extract_text() or '') for i, page in enumerate(reader.pages))
        dest.with_suffix('.txt').write_text(text)
        return {'id':key, 'url':url, 'status':'DOWNLOADED_AND_EXTRACTED_NOT_YET_READ',
                'pdf_sha256':hashlib.sha256(raw).hexdigest(), 'pages':len(reader.pages),
                'text_chars':len(text)}
    except Exception as exc:
        return {'id':key, 'url':url, 'status':'UNAVAILABLE', 'error':str(exc)}

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fetch, PAPERS))
    out = BASE / 'paper-downloads.json'
    if out.exists():
        raise SystemExit('Preserve existing manifest; use its saved results instead of overwriting')
    out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
