#!/usr/bin/env python3
"""Official API host recovery after a pre-model Cloudflare access denial."""
import sys
import urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import proof_together_diagnostic as core

core.OUT = core.OUT / 'transport-02'
core.ENDPOINT = 'https://api.together.xyz/v1/chat/completions'

def prepare():
    core.prepare()
    core.save(core.OUT / 'freeze/transport.json', {
        'endpoint': core.ENDPOINT, 'user_agent': 'legal-ai-together-diagnostic/1.0',
        'wrapper_sha256': core.sha(Path(__file__)),
        'reason': 'api.together.ai returned Cloudflare 1010 HTML before inference; official .xyz model-list API returned HTTP 200 and the exact requested model',
        'previous_attempt': 'outputs/proof-together-diagnostic-v1/runs/1954254/P01/run.json',
        'new_inference_generations_cap': 2, 'no_model_response_retry': True,
        'prompt_schema_sampling_unchanged': True,
        'source': 'https://www.together.ai/models/qwen3-5-9b',
    })

def run():
    frozen = core.read(core.OUT / 'freeze/transport.json')
    assert frozen['wrapper_sha256'] == core.sha(Path(__file__))
    assert frozen['endpoint'] == core.ENDPOINT
    opener = urllib.request.build_opener()
    opener.addheaders = [('User-Agent', frozen['user_agent'])]
    urllib.request.install_opener(opener)
    core.run()

if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        prepare()
    elif sys.argv[1] == 'run':
        run()
    else:
        raise ValueError('Only prepare and run; audit is a separate offline stage')
