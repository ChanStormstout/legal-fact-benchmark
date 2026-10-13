"""Prune exhausted unique-enum prefixes before sampling, without schema relaxation.

V19_6 rejected the closing quote of a repeated string, but still allowed an enum
prefix with no unused completion. Such a prefix has no legal next token. Keep
the historical adapter unchanged and remove those branches in this version.
Free-text uniqueness remains governed by the prior parser and final validator.
"""
import json

from legal_bench.mlx_json_constraint_v19_6 import UniqueStringParser, SchemaMask as OldMask
from legal_bench.mlx_json_constraint_v2 import CompositeQuoteEnforcer


class ViableUniqueEnumParser(UniqueStringParser):
    def unused_literals(self):
        if not self.stack or not self.stack[-1].get('unique'):
            return None
        array = self.stack[-1]
        spec = self.spec(array['path'] + (array['index'],))
        values = spec.get('enum')
        if values is None or not all(isinstance(x, str) for x in values):
            return None
        # The current contracts use ASCII address enums. Both standard JSON
        # spellings preserve Unicode enum support without fuzzy equivalence.
        return {json.dumps(x, ensure_ascii=mode) for x in values
                if x not in array['seen'] for mode in (False, True)}

    def get_allowed_characters(self):
        allowed = super().get_allowed_characters()
        literals = self.unused_literals()
        if literals is None:
            return allowed
        if self.is_unique_string():
            prefix = self.string['raw']
            next_chars = {s[len(prefix)] for s in literals
                          if s.startswith(prefix) and len(s) > len(prefix)}
            return ''.join(c for c in allowed if c in next_chars)
        if not literals:
            # Do not let a comma commit the parser to another array item after
            # all distinct enum values are consumed. The closing bracket stays.
            return allowed.replace(',', '').replace('"', '')
        return allowed

    def add_character(self, char):
        state = super().add_character(char)
        return type(self)(state.schema, state.delegate, state.stack, state.string,
                          state.escaped, state.config)


class SchemaMask(OldMask):
    def __init__(self, data, schema):
        self.enforcer = CompositeQuoteEnforcer(data, ViableUniqueEnumParser(schema))
        self.calls = 0
        self.prefix_length = None
        self.history = []

    def __call__(self, tokens, logits):
        try:
            return super().__call__(tokens, logits)
        except ValueError as exc:
            ids = tokens.tolist()
            self.failed_generated_ids = ids[self.prefix_length or 0:]
            self.history.append({'call': self.calls,
                                 'generated_count': len(self.failed_generated_ids),
                                 'failure': str(exc),
                                 'yielded_to_stream': False})
            raise
