"""Pinned MLX text-only runner; immutable attempts and hash-checked reuse."""
import importlib.metadata
import json
import resource
import signal
import time
import traceback
from pathlib import Path
from .source_views import digest, write_new
from .contracts import validate
from legal_bench.model_output import parse_one

SETTINGS = {
    'model': 'mlx-community/Qwen3.5-9B-4bit',
    'revision': '8b2b98c00a6b4d291155e4890773ca8f769aee53',
    'mlx_vlm': '0.7.4', 'schema_enforcer': '0.11.2', 'total_budget': 32768,
    'extract_max_tokens': 8192, 'direct_max_tokens': 4096, 'merge_max_tokens': 4096,
    'temperature': 0.0, 'top_p': 1.0, 'top_k': 0, 'min_p': 0.0,
    'repetition_penalty': 1.0, 'seed': 20261001, 'enable_thinking': False,
    'prefill_step_size': 256, 'timeout_seconds': 1200,
    'window_tokens': 4000, 'overlap_tokens': 400, 'media_input': False,
}


class Runner:
    def __init__(self, model_path, settings=None):
        self.settings = dict(SETTINGS if settings is None else settings)
        for key in ['model', 'revision', 'mlx_vlm', 'schema_enforcer', 'enable_thinking']:
            if self.settings[key] != SETTINGS[key]:
                raise ValueError('Pinned runtime setting changed: ' + key)
        path = Path(model_path).resolve()
        if self.settings['revision'] not in path.parts:
            raise ValueError('Local snapshot revision not verified')
        self.versions = {name: importlib.metadata.version(name) for name in
                         ['mlx-vlm', 'mlx', 'mlx-metal', 'transformers', 'lm-format-enforcer']}
        if self.versions['mlx-vlm'] != self.settings['mlx_vlm'] or self.versions['lm-format-enforcer'] != self.settings['schema_enforcer']:
            raise ValueError('Runtime version mismatch')
        from mlx_vlm import load
        from legal_bench.mlx_json_constraint import tokenizer_data
        start = time.perf_counter()
        self.model, self.processor = load(str(path))
        self.tokenizer = self.processor.tokenizer if hasattr(self.processor, 'tokenizer') else self.processor
        self.constraint_data = tokenizer_data(self.tokenizer, getattr(self.tokenizer, 'eos_token_ids', self.tokenizer.eos_token_id))
        self.loaded_seconds = time.perf_counter() - start
        self.model_config_hash = digest((path / 'config.json').read_bytes())

    def count(self, text):
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def render(self, prompt):
        from mlx_vlm.prompt_utils import apply_chat_template
        return apply_chat_template(self.processor, self.model.config, prompt, enable_thinking=False, num_images=0, num_audios=0)

    def run(self, prompt, schema, out, max_tokens):
        out = Path(out)
        rendered = self.render(prompt)
        identity = {'prompt_hash': digest(prompt.encode()), 'schema_hash': digest(schema),
                    'settings_hash': digest(self.settings), 'max_tokens': max_tokens,
                    'versions': self.versions, 'model_config_hash': self.model_config_hash}
        if (out / 'run.json').exists():
            previous = json.loads((out / 'run.json').read_text())
            if previous['identity'] != identity:
                raise ValueError('Refusing incompatible reuse')
            return previous
        if (out / 'start.json').exists():
            raise ValueError('Incomplete attempt retained; explicit new attempt required, no silent retry')
        out.mkdir(parents=True, exist_ok=True)
        write_new(out / 'start.json', {'identity': identity, 'started_at_epoch': time.time()})
        (out / 'prompt.txt').write_text(prompt)
        (out / 'rendered.txt').write_text(rendered)
        write_new(out / 'schema.json', schema)
        prompt_tokens = len(self.tokenizer.encode(rendered))
        empty_think = '<think>\n\n</think>' in rendered[-150:]
        meta = {'identity': identity, 'settings': self.settings, 'run_status': None, 'answer_status': None,
                'prompt_tokens': prompt_tokens, 'source_input_truncated': False,
                'thinking_disabled_template_verified': empty_think, 'loaded_seconds': self.loaded_seconds}
        if prompt_tokens + max_tokens > self.settings['total_budget'] or not empty_think:
            meta.update(run_status='INPUT_TOO_LONG' if empty_think else 'UNSUPPORTED',
                        reason='FULL_INPUT_EXCEEDS_BUDGET' if empty_think else 'THINKING_DISABLE_UNVERIFIED')
            write_new(out / 'run.json', meta)
            return meta
        import mlx.core as mx
        from mlx_vlm.generate import stream_generate
        from mlx_vlm.generate.types import GenerateKwargs
        from legal_bench.mlx_json_constraint import SchemaMask
        mx.random.seed(self.settings['seed'])
        mx.clear_cache()
        mx.reset_peak_memory()
        kwargs = {k: self.settings[k] for k in ['temperature', 'top_p', 'top_k', 'min_p',
                  'repetition_penalty', 'enable_thinking', 'prefill_step_size']}
        mask = SchemaMask(self.constraint_data, schema)
        kwargs.update(max_tokens=max_tokens, logits_processors=[mask])
        unsupported = set(kwargs) - set(GenerateKwargs.__annotations__)
        if unsupported:
            meta.update(run_status='UNSUPPORTED', reason='UNSUPPORTED_PARAMETERS:' + repr(sorted(unsupported)))
            write_new(out / 'run.json', meta)
            return meta
        raw, last, start = '', None, time.perf_counter()
        def timeout(signum, frame):
            raise TimeoutError('Single generation exceeded frozen timeout')
        prior_handler = signal.signal(signal.SIGALRM, timeout)
        signal.alarm(self.settings['timeout_seconds'])
        print('START', out.name, 'input', prompt_tokens, flush=True)
        try:
            with (out / 'raw-response.txt').open('x') as handle:
                for last in stream_generate(self.model, self.processor, rendered, image=None, audio=None, video=None, **kwargs):
                    raw += last.text
                    handle.write(last.text)
                    handle.flush()
                    if last.generation_tokens % 256 == 0:
                        print('PROGRESS', out.name, last.generation_tokens, round(time.perf_counter() - start, 1), flush=True)
            if last is None:
                raise ValueError('No generation result')
            meta.update(output_tokens=last.generation_tokens, prompt_tokens_actual=last.prompt_tokens,
                        finish_reason=last.finish_reason, thinking_output_present=('<think>' in raw or '</think>' in raw))
            if last.finish_reason != 'stop':
                meta['run_status'] = 'OUTPUT_TRUNCATED'
            elif meta['thinking_output_present']:
                meta.update(run_status='UNSUPPORTED', reason='THINKING_OUTPUT_DETECTED')
            else:
                parsed, repairs = parse_one(raw.encode())
                validate(parsed, schema)
                write_new(out / 'parsed.json', parsed)
                meta.update(run_status='OK', format_repairs=repairs)
        except Exception as exc:
            status = 'TIMEOUT' if isinstance(exc, TimeoutError) else 'OUT_OF_MEMORY' if isinstance(exc, MemoryError) or 'out of memory' in str(exc).lower() else 'FORMAT_ERROR' if isinstance(exc, (ValueError, TypeError, KeyError)) else 'UNSUPPORTED'
            meta.update(run_status=status, error=type(exc).__name__ + ': ' + str(exc), traceback=traceback.format_exc())
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, prior_handler)
        meta.update(elapsed_seconds=time.perf_counter() - start, peak_mlx_memory_gb=mx.get_peak_memory() / 1e9,
                    peak_rss_gb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9,
                    raw_hash=digest(raw.encode()), schema_mask_calls=mask.calls,
                    actual_parameters={k: v for k, v in kwargs.items() if k != 'logits_processors'})
        write_new(out / 'run.json', meta)
        print('END', out.name, meta['run_status'], round(meta['elapsed_seconds'], 1), flush=True)
        return meta
