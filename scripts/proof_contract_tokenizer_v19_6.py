#!/usr/bin/env python3
"""One deterministic pinned-tokenizer/real-mask acceptance; no model is loaded."""
import copy
import importlib.metadata
import json
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from scripts import proof_contract_integrity_v19_6 as entry
from legal_bench.proof_carrying import local_pipeline_v19_6 as pipe
from tests.test_contract_integrity_v19_6 import fixture


def run():
    from transformers import AutoTokenizer
    from legal_bench.mlx_json_constraint import tokenizer_data
    from legal_bench.mlx_json_constraint_v19_6 import SchemaMask
    start = time.perf_counter()
    model_path = (ROOT / 'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip()
    assert '8b2b98c00a6b4d291155e4890773ca8f769aee53' in model_path
    tok = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    data = tokenizer_data(tok, tok.eos_token_id)
    c, r, x = fixture(); sc = pipe.schema(r, c); cases = [('valid', x, True)]
    bad = copy.deepcopy(x); bad['analyses']['R1.P1']['records'][0]['refs'] = ['SRC:1', 'SRC:1']; cases.append(('second_duplicate_source', bad, False))
    bad = copy.deepcopy(x); bad['analyses']['R1.P1']['uses'][0]['records'] = ['SRC:1']; cases.append(('source_is_not_record', bad, False))
    bad = copy.deepcopy(x); bad['analyses'] = {}; cases.append(('missing_fixed_premise', bad, False))
    bad = copy.deepcopy(x); bad['analyses']['R1.P1']['judgments'][0]['role_objects'] = {}; cases.append(('missing_role_key', bad, False))
    # Existential local references are NOT decoder-enforced; the importer must reject.
    bad = copy.deepcopy(x); bad['analyses']['R1.P1']['uses'][0]['records'] = ['EV:999']; cases.append(('dynamic_missing_import_only', bad, True))
    receipts = []
    for name, value, expected in cases:
        ids = tok.encode(json.dumps(value, separators=(',', ':')), add_special_tokens=False)
        mask = SchemaMask(data, sc); prefix = []; blocked = None
        for i, token in enumerate(ids):
            if token not in mask.enforcer.get_allowed_tokens(prefix).allowed_tokens:
                blocked = i; break
            prefix.append(token)
        ended = blocked is None and tok.eos_token_id in mask.enforcer.get_allowed_tokens(prefix).allowed_tokens
        assert ended == expected, (name, ended, blocked, tok.decode(prefix[-20:]))
        receipts.append({'name': name, 'token_count': len(ids), 'complete_and_EOS_allowed': ended, 'blocked_at': blocked, 'expected': expected})
    capacity = []
    for p in sorted((entry.OUT / 'prepared').glob('*/*/prompt.txt')):
        prompt = p.read_text(); rendered = tok.apply_chat_template([{'role': 'user', 'content': prompt}], tokenize=False, add_generation_prompt=True, enable_thinking=False)
        required = len(tok.encode(rendered)) + 16384 + 256
        old = entry.BASE / 'local' / p.parent.parent.name / p.parent.name / 'prompt.txt'
        capacity.append({'case_id': p.parent.parent.name, 'part': p.parent.name, 'new_prompt_tokens': len(tok.encode(rendered)),
                         'old_prompt_tokens': entry.read(old.parent / 'run.json')['prompt_tokens'], 'required_total': required,
                         'budget_65536_unchanged': True, 'fits': required <= 65536})
        assert required <= 65536
    record = {'status': 'PASS', 'receipts': receipts, 'capacity': capacity,
              'tokenizer_revision': '8b2b98c00a6b4d291155e4890773ca8f769aee53',
              'constraint': 'V19_6 UniqueStringParser + CompositeQuoteEnforcer',
              'lmfe': importlib.metadata.version('lm-format-enforcer'), 'model_loaded': False,
              'model_generation_calls': 0, 'elapsed_seconds': time.perf_counter() - start,
              'guarantee': 'Declared unique string arrays, fixed keys, namespaces; dynamic existence and legal semantics are import/review responsibilities.'}
    entry.save(entry.OUT / 'engineering/tokenizer-replay.json', record)
    print(json.dumps(record, indent=2))


if __name__ == '__main__': run()
