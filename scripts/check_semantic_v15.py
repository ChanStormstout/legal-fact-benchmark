#!/usr/bin/env python3
"""Standalone independent checker entry. No task assembler import."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.semantic_checker_v15 import check

if __name__ == '__main__':
    root = Path(sys.argv[1])
    read = lambda name: json.loads((root / (name + '.json')).read_text())
    settings = read('settings')
    result = check(read('bundle'), read('search'), read('supplement') if settings['view'] != 'D' else None,
                   read('review') if settings['view'] == 'R' and (root / 'review.json').exists() else None,
                   settings['view'])
    print(json.dumps(result, ensure_ascii=False))
