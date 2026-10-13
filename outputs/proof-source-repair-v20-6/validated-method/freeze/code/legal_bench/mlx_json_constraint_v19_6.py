"""LMFE 0.11.2 plus schema-declared unique string-array enforcement.

The upstream decoder ignores uniqueItems. This immutable character-parser view
blocks a second equal string inside a declared unique array, before its closing
quote can be generated. It never edits output or relaxes the schema.
Generic object/array uniqueness remains the final validator's responsibility.
"""
import json
from lmformatenforcer import JsonSchemaParser, CharacterLevelParser
from legal_bench.mlx_json_constraint_v2 import CompositeQuoteEnforcer


class UniqueStringParser(CharacterLevelParser):
    def __init__(self, schema, delegate=None, stack=(), string=None, escaped=False, config=None):
        self.delegate = delegate if delegate is not None else JsonSchemaParser(schema)
        # LMFE's UnionParser does not initialize _config. Preserve the original
        # JsonSchemaParser configuration across its union branches.
        super().__init__(config if config is not None else getattr(self.delegate, '_config', None))
        self.schema = schema
        self.stack = stack
        self.string = string
        self.escaped = escaped

    def spec(self, path):
        result = self.schema
        for part in path:
            if '$ref' in result: result = self.schema['$defs'][result['$ref'].split('/')[-1]]
            result = result.get('items', {}) if isinstance(part, int) else result.get('properties', {}).get(part, {})
        if '$ref' in result: result = self.schema['$defs'][result['$ref'].split('/')[-1]]
        return result

    def value_path(self):
        if not self.stack: return ()
        top = self.stack[-1]
        return top['path'] + ((top['key'],) if top['kind'] == '{' else (top['index'],))

    def is_unique_string(self):
        return self.string is not None and not self.string['key'] and bool(self.stack) and self.stack[-1].get('unique', False)

    def repeated_close(self):
        if not self.is_unique_string() or self.escaped: return False
        try: value = json.loads(self.string['raw'] + '"')
        except ValueError: return False
        return value in self.stack[-1]['seen']

    def get_allowed_characters(self):
        chars = self.delegate.get_allowed_characters()
        return chars.replace('"', '') if self.repeated_close() else chars

    def can_end(self):
        return self.delegate.can_end()

    def shortcut_key(self):
        # A cached free-text shortcut must not bypass the duplicate close check.
        return None if self.is_unique_string() else self.delegate.shortcut_key()

    def add_character(self, char):
        if char not in self.get_allowed_characters(): raise ValueError('CHARACTER_OUTSIDE_STRICT_CONSTRAINT')
        stack = [dict(x) for x in self.stack]
        string = dict(self.string) if self.string is not None else None
        escaped = self.escaped
        if string is not None:
            if escaped:
                string['raw'] += char; escaped = False
            elif char == '\\':
                string['raw'] += char; escaped = True
            elif char == '"':
                value = json.loads(string['raw'] + '"')
                if string['key']:
                    stack[-1]['key'] = value; stack[-1]['expect_key'] = False
                elif stack and stack[-1].get('unique'):
                    stack[-1]['seen'] = stack[-1]['seen'] | {value}
                string = None
            else: string['raw'] += char
        elif char == '"':
            string = {'raw': '"', 'key': bool(stack and stack[-1]['kind'] == '{' and stack[-1]['expect_key'])}
        elif char in '{[':
            path = self.value_path()
            spec = self.spec(path)
            stack.append({'kind': char, 'path': path, 'key': None, 'index': 0, 'expect_key': char == '{',
                          'unique': char == '[' and bool(spec.get('uniqueItems')), 'seen': frozenset()})
        elif char in '}]': stack.pop()
        elif char == ',' and stack:
            if stack[-1]['kind'] == '{': stack[-1]['expect_key'] = True
            else: stack[-1]['index'] += 1
        return UniqueStringParser(self.schema, self.delegate.add_character(char), tuple(stack), string, escaped, self.config)


class SchemaMask:
    def __init__(self, data, schema):
        self.enforcer = CompositeQuoteEnforcer(data, UniqueStringParser(schema))
        self.calls = 0; self.prefix_length = None; self.history = []

    def __call__(self, tokens, logits):
        import mlx.core as mx
        ids = tokens.tolist()
        if self.prefix_length is None: self.prefix_length = len(ids)
        generated = ids[self.prefix_length:]
        allowed = self.enforcer.get_allowed_tokens(generated).allowed_tokens
        if not allowed: raise ValueError('No valid constrained tokens; mask never silently disabled')
        if any(i < 0 or i >= logits.shape[-1] for i in allowed): raise ValueError('Tokenizer/model vocabulary mismatch')
        self.history.append({'call': self.calls, 'generated_count': len(generated), 'allowed_count': len(allowed)})
        mask = mx.full((logits.shape[-1],), float('-inf'), dtype=logits.dtype)
        mask[mx.array(allowed)] = 0; self.calls += 1
        return logits + mask
