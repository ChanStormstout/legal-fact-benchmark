"""V8 loading-only adapter. V6 rendering/generation/constraint code is inherited."""
import importlib.metadata
import json
import time
from pathlib import Path

from .runtime_constraint_diag_v1 import Runner as V6Runner
from .source_views import digest

MODEL = 'mlx-community/Qwen3.5-9B-8bit'
REVISION = '16daa4818c54ce5f5436f929d52542eb65bbed9d'
VERSIONS = {'mlx-vlm': '0.7.4', 'mlx': '0.32.3', 'mlx-metal': '0.32.3',
            'transformers': '5.18.0', 'lm-format-enforcer': '0.11.2'}


def verify_settings(model_path, settings):
    expected = {'model': MODEL, 'revision': REVISION, 'mlx_vlm': '0.7.4',
                'schema_enforcer': '0.11.2', 'enable_thinking': False,
                'temperature': 0.0, 'top_p': 1.0, 'top_k': 0, 'min_p': 0.0,
                'repetition_penalty': 1.0, 'seed': 20261001, 'total_budget': 32768,
                'direct_max_tokens': 3072, 'prefill_step_size': 256, 'media_input': False}
    for key, value in expected.items():
        if settings.get(key) != value:
            raise ValueError('V8 frozen setting mismatch: ' + key)
    path = Path(model_path).resolve()
    if path.name != REVISION or path.parent.name != 'snapshots':
        raise ValueError('V8 snapshot revision not verified')
    config = json.loads((path / 'config.json').read_text())
    for field in ('quantization', 'quantization_config'):
        if config[field] != {'bits': 8, 'group_size': 64, 'mode': 'affine'}:
            raise ValueError('V8 quantization configuration mismatch: ' + field)
    return path


class Runner(V6Runner):
    # No override of render, count or run: generation is byte-for-byte V6 behavior.
    def __init__(self, model_path, settings):
        self.settings = dict(settings)
        path = verify_settings(model_path, self.settings)
        self.versions = {name: importlib.metadata.version(name) for name in VERSIONS}
        if self.versions != VERSIONS:
            raise ValueError('V8 runtime differs from V6: ' + repr(self.versions))
        from mlx_vlm import load
        from legal_bench.mlx_json_constraint import tokenizer_data
        start = time.perf_counter()
        self.model, self.processor = load(str(path))
        self.tokenizer = self.processor.tokenizer if hasattr(self.processor, 'tokenizer') else self.processor
        self.constraint_data = tokenizer_data(self.tokenizer, getattr(self.tokenizer, 'eos_token_ids', self.tokenizer.eos_token_id))
        self.loaded_seconds = time.perf_counter() - start
        self.model_config_hash = digest((path / 'config.json').read_bytes())
