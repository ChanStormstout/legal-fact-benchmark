"""Actual tokenizer/constraint fixtures, no model load or generation."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from transformers import AutoTokenizer
from lmformatenforcer import JsonSchemaParser
from legal_bench.mlx_json_constraint import tokenizer_data
from legal_bench.mlx_json_constraint_v2 import CompositeQuoteEnforcer
from legal_bench.irac_application.contract_v5 import address_directory
from legal_bench.irac_application.contract_v5_tasks import schema
from scripts.irac_contract_v5 import R, inputs, save, read, hf


def run():
    path = Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip()
    tok = AutoTokenizer.from_pretrained(path, local_files_only=True)
    data = tokenizer_data(tok, tok.eos_token_id)
    rows = []
    for cid in ('112400', '188721101'):
        m, t, law, sm = inputs(cid)
        directory = address_directory(t)
        sid = next(iter(m['sources']))
        # One complete small synthetic fixture per legal address, including child branches.
        for key, address in directory.items():
            sample = {
                'bindings': [{'id': 'b1', 'claim_ids': [t['claims'][0]['id']], 'objects': 'Synthetic fixture only',
                              'event': 'Synthetic event', 'stage': 'Synthetic review', 'refs': [sid]}],
                'evidence': [{'id': 'e1', 'binding_id': 'b1', 'record': 'The fixture ends with a composite quote.',
                              'statement_status': 'UNKNOWN', 'refs': [sid],
                              'uses': [{'condition_address': key, 'direction': 'UNKNOWN', 'use': 'RECORD_EXISTENCE'}]}],
                'limitations': [], 'conditions': [], 'coverage_limits': ['Syntax fixture, not a factual claim about this case.']}
            contract = schema('proposal', m, t, law)
            text = json.dumps(sample)
            ids = tok.encode(text, add_special_tokens=False)
            mask = CompositeQuoteEnforcer(data, JsonSchemaParser(contract))
            for i, token in enumerate(ids):
                assert token in mask.get_allowed_tokens(ids[:i]).allowed_tokens, (cid, key, i)
            assert tok.eos_token_id in mask.get_allowed_tokens(ids).allowed_tokens
            assert json.loads(tok.decode(ids)) == sample
            rows.append({'schema_case': cid, 'condition_address': key, 'legal_pair': address,
                         'tokens': len(ids), 'all_allowed': True, 'eos_allowed': True,
                         'synthetic_not_case_answer': True})
    prior = Path('outputs/json-constraint-diagnosis-v1')
    contract = read(prior / 'prepared/schema.json')
    ids = read(prior / 'runs/FIXED/token-ids.json')
    mask = CompositeQuoteEnforcer(data, JsonSchemaParser(contract))
    for i, token in enumerate(ids):
        assert token in mask.get_allowed_tokens(ids[:i]).allowed_tokens, i
    assert tok.decode(ids, skip_special_tokens=True) == (prior / 'runs/FIXED/raw-response.txt').read_text()
    result = {'passed': True, 'model_calls': 0, 'tokenizer_revision': Path(path).name,
              'constraint_path': 'legal_bench/mlx_json_constraint_v2.py',
              'constraint_sha256': hf('legal_bench/mlx_json_constraint_v2.py'),
              'rows': rows, 'historical_fixed_token_replay': {'tokens': len(ids), 'raw_exact': True}}
    save(R / 'engineering/real-tokenizer.json', result)
    print('PASS', len(rows), 'complete address fixtures; historical fixed-token replay; model calls 0')


if __name__ == '__main__':
    run()
