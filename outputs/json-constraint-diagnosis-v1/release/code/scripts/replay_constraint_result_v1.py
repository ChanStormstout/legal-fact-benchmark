"""Post-run token replay; no model generation or answer repair."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from transformers import AutoTokenizer
from lmformatenforcer import TokenEnforcer, JsonSchemaParser
from legal_bench.mlx_json_constraint import tokenizer_data
from legal_bench.mlx_json_constraint_v2 import CompositeQuoteEnforcer
from legal_bench.rules_verdict_v1.source_views import write_new

ROOT = Path('outputs/json-constraint-diagnosis-v1')
read = lambda path: json.loads(path.read_text())
tokenizer = AutoTokenizer.from_pretrained(
    Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),
    local_files_only=True)
data = tokenizer_data(tokenizer, tokenizer.eos_token_id)
schema = read(ROOT / 'prepared/schema.json')
ids = read(ROOT / 'runs/FIXED/token-ids.json')
old = TokenEnforcer(data, JsonSchemaParser(schema))
new = CompositeQuoteEnforcer(data, JsonSchemaParser(schema))
first_divergence = None
for index, token in enumerate(ids):
    assert token in new.get_allowed_tokens(ids[:index]).allowed_tokens, index
    if first_divergence is None and token not in old.get_allowed_tokens(ids[:index]).allowed_tokens:
        first_divergence = {'position': index, 'token_id': token,
                            'decoded': tokenizer.decode([token]),
                            'prefix_tail': tokenizer.decode(ids[:index])[-150:],
                            'legacy_allowed': False, 'corrected_allowed': True}
    # After a legacy-disallowed transition its parser state is not a valid trace;
    # do not use later legacy states to make further claims.
history = read(ROOT / 'runs/FIXED/mask-history.json')
for index, row in enumerate(history):
    assert row['call'] == index and row['generated_count'] == index
    assert row['processor_tokens'] == index + row['prefix_length']
    assert row['last_generated_id'] == (ids[index-1] if index else None)
raw = (ROOT / 'runs/FIXED/raw-response.txt').read_text()
assert tokenizer.decode(ids, skip_special_tokens=True) == raw
assert raw == (ROOT / 'runs/NONE/raw-response.txt').read_text()
assert first_divergence is not None
write_new(ROOT / 'post-run-token-replay.json', {
    'model_calls': 0, 'first_legacy_disallowed_transition': first_divergence,
    'all_generated_tokens_allowed_by_corrected_mask': True,
    'callback_count': len(history), 'generated_token_ids_including_eos': len(ids),
    'prefix_tracking_matches_actual_token_ids': True,
    'streamed_raw_matches_decoded_token_ids': True,
    'no_mask_and_fixed_raw_identical': True,
    'eos_last': ids[-1] == tokenizer.eos_token_id})
print(json.dumps(first_divergence, indent=2))
