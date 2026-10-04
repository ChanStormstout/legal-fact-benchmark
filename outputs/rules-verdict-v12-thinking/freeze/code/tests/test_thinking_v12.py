import json
import unittest
from legal_bench.rules_verdict_v1.thinking_v12 import ThinkingOutput, ThinkingSchemaMask, partition_ids
from legal_bench.rules_verdict_v1.repetition_v9 import RepetitionAbort
from tests.test_mlx_constraint_v2 import data, SCHEMA, PREFIX, TOKENS


class ThinkingSeparationTests(unittest.TestCase):
    def test_unconstrained_reasoning_and_fresh_final_parser(self):
        import mlx.core as mx
        end = len(TOKENS) + 2
        mask = ThinkingSchemaMask(data(), SCHEMA, end)
        logits = mx.zeros((len(TOKENS) + 1,))
        # Prompt may contain end tokens; only generated end token changes phase.
        self.assertTrue(mx.array_equal(mask(mx.array([end]), logits), logits))
        self.assertTrue(mx.array_equal(mask(mx.array([end, 11, 11]), logits), logits))
        self.assertEqual(mask.answer_mask.calls, 0)
        answer = mask(mx.array([end, 11, 11, end]), logits)
        self.assertEqual(float(answer[0].item()), 0)
        self.assertEqual(float(answer[11].item()), float('-inf'))
        for n in range(1, len(PREFIX) + 1):
            out = mask(mx.array([end, 11, 11, end] + PREFIX[:n]), logits)
        self.assertEqual(float(out[5].item()), 0)  # corrected composite quote remains allowed
        self.assertEqual(mask.answer_mask.history[-1]['generated_count'], len(PREFIX))

    def test_cross_chunk_boundary_and_guard_final_only(self):
        output = ThinkingOutput()
        reasoning = 'x' * 80 * 5 + ' {"point":"not JSON reasoning"}'
        final = json.dumps({'point': 'Short final', 'assessment': 'SUPPORTED'})
        raw = reasoning + '</think>' + final
        for i in range(0, len(raw), 3): output.feed(raw[i:i + 3])
        output.finish()
        self.assertEqual(output.thinking, reasoning)
        self.assertEqual(output.final, final)
        self.assertEqual(output.reconstruct(), raw)
        self.assertIsNone(output.guard.hit)
        failing = ThinkingOutput()
        with self.assertRaises(RepetitionAbort):
            failing.feed('</think>{"point":"' + 'y' * 80 * 5)

    def test_partition_and_unclosed_no_final(self):
        self.assertEqual(partition_ids([1, 2, 9, 3, 4, 10], 9, [10]),
                         {'thinking': [1, 2], 'delimiter': [9], 'final': [3, 4], 'terminal': [10], 'closed': True})
        self.assertFalse(partition_ids([1, 2], 9, [10])['closed'])
        stream = ThinkingOutput();stream.feed('unfinished reasoning');stream.finish()
        self.assertEqual(stream.final, '')
        self.assertEqual(stream.reconstruct(), 'unfinished reasoning')

    def test_actual_tokenizer_template_and_native_budget(self):
        from pathlib import Path
        from transformers import AutoTokenizer
        from mlx_vlm.prompt_utils import apply_chat_template
        from mlx_vlm.utils import ThinkingBudgetCriteria
        from mlx_vlm.generate.types import GenerateKwargs
        p = Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip()
        t = AutoTokenizer.from_pretrained(p)
        config = json.loads((Path(p) / 'config.json').read_text())
        on = apply_chat_template(t, config, 'Synthetic interface fixture', enable_thinking=True, num_images=0, num_audios=0)
        off = apply_chat_template(t, config, 'Synthetic interface fixture', enable_thinking=False, num_images=0, num_audios=0)
        self.assertTrue(on.endswith('<think>\n'))
        self.assertTrue(off.endswith('<think>\n\n</think>\n\n'))
        start, end = [t.encode(s, add_special_tokens=False)[0] for s in ['<think>', '</think>']]
        self.assertEqual(t.encode('</think>', add_special_tokens=False), [end])
        self.assertIn('thinking_budget', GenerateKwargs.__annotations__)
        self.assertNotIn('final_max_tokens', GenerateKwargs.__annotations__)
        budget = ThinkingBudgetCriteria(t, 2, '</think>', '<think>', True, True)
        ordinary = t.encode('a', add_special_tokens=False)[0]
        budget(ordinary);self.assertIsNone(budget.pop_forced_token_id())
        budget(ordinary);self.assertIsNone(budget.pop_forced_token_id())
        budget(ordinary);newline = budget.pop_forced_token_id()
        self.assertEqual(newline, t.encode('\n', add_special_tokens=False)[-1])
        budget(newline);self.assertEqual(budget.pop_forced_token_id(), end)
        budget(end);self.assertFalse(budget.in_thinking)
        self.assertEqual(budget.thinking_token_count, 4)  # > threshold + forced newline


if __name__ == '__main__': unittest.main()
