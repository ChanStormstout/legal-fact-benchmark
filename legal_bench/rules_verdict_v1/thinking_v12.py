"""Thinking demultiplexing only. Reuse corrected final JSON mask unchanged."""
from .repetition_v9 import StringGuard
from legal_bench.mlx_json_constraint_v2 import SchemaMask


class ThinkingSchemaMask:
    def __init__(self, data, schema, end_token_id):
        self.end_token_id = end_token_id
        self.prefix_length = None
        self.answer_offset = None
        self.calls = 0
        self.history = []
        self.answer_mask = SchemaMask(data, schema)
        # Only final generated IDs enter this parser, so there is no prompt prefix.
        self.answer_mask.prefix_length = 0

    def __call__(self, tokens, logits):
        ids = tokens.tolist()
        if self.prefix_length is None:
            self.prefix_length = len(ids)
        generated = ids[self.prefix_length:]
        if self.answer_offset is None and self.end_token_id in generated:
            self.answer_offset = self.prefix_length + generated.index(self.end_token_id) + 1
        self.calls += 1
        self.history.append({'call': self.calls, 'processor_tokens': len(ids),
                             'generated_tokens': len(generated), 'answer_offset': self.answer_offset,
                             'phase': 'FINAL' if self.answer_offset is not None else 'THINKING'})
        if self.answer_offset is None:
            return logits
        return self.answer_mask(tokens[self.answer_offset:], logits)


class ThinkingOutput:
    """Split the original text without editing it; JSON guard runs on final only."""
    marker = '</think>'

    def __init__(self):
        self.pending = ''
        self.thinking = ''
        self.final = ''
        self.closed = False
        self.guard = StringGuard()

    def feed(self, chunk):
        if self.closed:
            self.final += chunk
            self.guard.feed(chunk)
            return
        self.pending += chunk
        if self.marker in self.pending:
            before, after = self.pending.split(self.marker, 1)
            self.thinking += before
            self.pending = ''
            self.closed = True
            self.final += after
            self.guard.feed(after)
        else:
            count = max(0, len(self.pending) - (len(self.marker) - 1))
            self.thinking += self.pending[:count]
            self.pending = self.pending[count:]

    def finish(self):
        if not self.closed:
            self.thinking += self.pending
            self.pending = ''

    def reconstruct(self):
        return self.thinking + (self.marker + self.final if self.closed else self.pending)


def partition_ids(ids, end_token_id, eos_ids):
    """Exact generated ID partition, with delimiter/EOS counted separately."""
    eos_ids = set(eos_ids)
    if end_token_id not in ids:
        return {'thinking': ids, 'delimiter': [], 'final': [], 'terminal': [], 'closed': False}
    offset = ids.index(end_token_id)
    tail = ids[offset + 1:]
    terminal = []
    while tail and tail[-1] in eos_ids:
        terminal.insert(0, tail.pop())
    return {'thinking': ids[:offset], 'delimiter': [ids[offset]], 'final': tail,
            'terminal': terminal, 'closed': True}
