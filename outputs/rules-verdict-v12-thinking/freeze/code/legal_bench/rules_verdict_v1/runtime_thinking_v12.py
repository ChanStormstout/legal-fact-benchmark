"""Versioned thinking runner. Native budget, final-only corrected Schema/guard."""
import json
import resource
import signal
import time
import traceback
from pathlib import Path
from .runtime_constraint_diag_v1 import Runner
from .source_views import digest, write_new
from .contracts import validate
from .repetition_v9 import RepetitionAbort
from .thinking_v12 import ThinkingSchemaMask, ThinkingOutput, partition_ids


class ThinkingRunner(Runner):
    def __init__(self, model_path, v11_settings):
        # Reuse pinned model loading and version validation, not the old off-only run.
        super().__init__(model_path, v11_settings)
        self.settings = dict(v11_settings, enable_thinking=True)
        self.end_id = self.tokenizer.encode('</think>', add_special_tokens=False)
        if len(self.end_id) != 1: raise ValueError('Thinking boundary is not one token')
        self.end_id = self.end_id[0]

    def render(self, text):
        from mlx_vlm.prompt_utils import apply_chat_template
        return apply_chat_template(self.processor, self.model.config, text,
                                   enable_thinking=True, num_images=0, num_audios=0)

    def run_thinking(self, prompt, schema, out, remaining_seconds):
        import mlx.core as mx
        from mlx_vlm.generate import stream_generate
        from mlx_vlm.generate.types import GenerateKwargs
        out = Path(out)
        if out.exists(): raise ValueError('No overwrite or retry of an existing attempt')
        out.mkdir(parents=True)
        rendered = self.render(prompt)
        prompt_tokens = len(self.tokenizer.encode(rendered))
        kwargs = {k: self.settings[k] for k in ['temperature', 'top_p', 'top_k', 'min_p',
                  'repetition_penalty', 'enable_thinking', 'prefill_step_size']}
        kwargs.update(max_tokens=8192, thinking_budget=4096,
                      thinking_start_token='<think>', thinking_end_token='</think>')
        write_new(out / 'start.json', {'started_epoch': time.time(), 'prompt_hash': digest(prompt.encode()),
                  'schema_hash': digest(schema), 'actual_parameters': kwargs})
        (out / 'prompt.txt').write_text(prompt)
        (out / 'rendered.txt').write_text(rendered)
        write_new(out / 'schema.json', schema)
        write_new(out / 'effective-parameters.json', kwargs)
        meta = {'run_status': None, 'answer_status': None, 'prompt_tokens': prompt_tokens,
                'source_input_truncated': False, 'actual_parameters': kwargs,
                'thinking_template_open_verified': rendered.endswith('<think>\n'),
                'versions': self.versions, 'model_config_hash': self.model_config_hash,
                'final_separate_token_cap_supported': False, 'final_budget_guaranteed_3072': False,
                'budget_mode': 'NATIVE_APPROX_4096_THINKING_SHARED_TOTAL_8192',
                'mask_version': 'thinking_v12 wraps unchanged mlx_json_constraint_v2',
                'fixed_seed': self.settings['seed'], 'format_repairs': []}
        if prompt_tokens + 8192 > 32768 or not meta['thinking_template_open_verified']:
            meta.update(run_status='INPUT_TOO_LONG' if meta['thinking_template_open_verified'] else 'UNSUPPORTED',
                        reason='FULL_INPUT_OVER_BUDGET' if meta['thinking_template_open_verified'] else 'THINKING_TEMPLATE_NOT_OPEN')
            write_new(out / 'run.json', meta); return meta
        unsupported = set(kwargs) - set(GenerateKwargs.__annotations__)
        if unsupported:
            meta.update(run_status='UNSUPPORTED', reason='UNSUPPORTED_KWARGS:' + repr(sorted(unsupported)))
            write_new(out / 'run.json', meta);return meta
        mx.random.seed(self.settings['seed']);mx.clear_cache();mx.reset_peak_memory()
        mask = ThinkingSchemaMask(self.constraint_data, schema, self.end_id)
        kwargs['logits_processors'] = [mask]
        stream = ThinkingOutput()
        raw, ids, last = '', [], None
        forced_events = []
        began = time.perf_counter()
        def timeout(signum, frame): raise TimeoutError('Frozen whole-round inference budget exhausted')
        previous_handler = signal.signal(signal.SIGALRM, timeout)
        signal.setitimer(signal.ITIMER_REAL, max(.001, remaining_seconds))
        print('START', out.name, 'input', prompt_tokens, flush=True)
        try:
            with (out / 'raw-response.txt').open('x') as handle:
                for last in stream_generate(self.model, self.processor, rendered, image=None, audio=None, video=None, **kwargs):
                    raw += last.text;handle.write(last.text);handle.flush()
                    if last.token_ids is not None: ids = list(last.token_ids)
                    elif last.token is not None: ids.append(int(last.token))
                    (out / 'token-ids-in-progress.json').write_text(json.dumps(ids))
                    criteria = getattr(self.tokenizer, 'thinking_budget_criteria', None)
                    if criteria is not None and criteria.forced_token_id is not None:
                        forced_events.append({'after_generated_count': len(ids),
                                              'pending_forced_id': int(criteria.forced_token_id),
                                              'native_thinking_count': criteria.thinking_token_count})
                    stream.feed(last.text)
                    if last.generation_tokens % 256 == 0:
                        print('PROGRESS', out.name, last.generation_tokens, round(time.perf_counter() - began, 1), flush=True)
            stream.finish()
            if last is None: raise ValueError('No generation result')
            meta['framework_finish_reason'] = last.finish_reason
            if last.finish_reason != 'stop': meta['run_status'] = 'OUTPUT_TRUNCATED'
            elif not stream.closed or self.end_id not in ids:
                meta.update(run_status='FORMAT_ERROR', reason='THINKING_DID_NOT_CLOSE_NO_FINAL_ANSWER')
            else:
                parsed = json.loads(stream.final)
                validate(parsed, schema)
                write_new(out / 'parsed.json', parsed)
                meta['run_status'] = 'OK'
        except Exception as exc:
            status = ('REPETITION_ABORT' if isinstance(exc, RepetitionAbort) else
                      'TIMEOUT' if isinstance(exc, TimeoutError) else
                      'OUT_OF_MEMORY' if isinstance(exc, MemoryError) or 'out of memory' in str(exc).lower() else
                      'FORMAT_ERROR' if isinstance(exc, (ValueError, TypeError, KeyError)) else 'UNSUPPORTED')
            meta.update(run_status=status, error=type(exc).__name__ + ': ' + str(exc), traceback=traceback.format_exc())
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0);signal.signal(signal.SIGALRM, previous_handler)
        stream.finish()
        assert stream.reconstruct() == raw, 'Demultiplexing changed raw content'
        (out / 'thinking-response.txt').write_text(stream.thinking)
        (out / 'final-response.txt').write_text(stream.final)
        write_new(out / 'token-ids.json', ids)
        eos = getattr(self.tokenizer.stopping_criteria, 'eos_token_ids', None)
        if eos is None: eos = [self.tokenizer.eos_token_id]
        if isinstance(eos, int): eos = [eos]
        parts = partition_ids(ids, self.end_id, eos)
        write_new(out / 'partitioned-token-ids.json', parts)
        write_new(out / 'mask-phase-history.json', mask.history)
        write_new(out / 'final-mask-history.json', mask.answer_mask.history)
        write_new(out / 'native-budget-events.json', forced_events)
        counts = {k + '_tokens': len(v) for k, v in parts.items() if isinstance(v, list)}
        assert sum(counts.values()) == len(ids)
        # EOS is excluded from final content count and reported separately.
        meta.update(**counts, output_tokens=len(ids), finish_reason=getattr(last, 'finish_reason', None) or meta['run_status'].lower(),
                    elapsed_seconds=time.perf_counter() - began, peak_mlx_memory_gb=mx.get_peak_memory() / 1e9,
                    peak_rss_gb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e9,
                    repetition_guard=stream.guard.hit, raw_hash=digest(raw.encode()),
                    final_raw_hash=digest(stream.final.encode()), demultiplexing_exact=True,
                    schema_mask_calls=mask.answer_mask.calls, processor_calls=mask.calls,
                    native_forced_boundary=bool(forced_events), final_parser_started_after_think=True,
                    thinking_is_not_evidence=True, actual_max_tokens=8192)
        if meta['run_status'] == 'OK':
            assert mask.answer_offset is not None and mask.answer_mask.calls > 0
        write_new(out / 'run.json', meta)
        print('END', out.name, meta['run_status'], round(meta['elapsed_seconds'], 1), counts, flush=True)
        return meta
