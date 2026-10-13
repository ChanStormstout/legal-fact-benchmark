"""Shared source transport plus scope-specific, actually declared EV/OBJ/USE."""
import json
from legal_bench.mlx_json_constraint_v20_3 import SharedSourceParser
from legal_bench.mlx_json_constraint_v20_1 import SchemaMask as PreviousMask
from legal_bench.mlx_json_constraint_v2 import CompositeQuoteEnforcer
from legal_bench.proof_carrying.declared_references_v20_4 import PATTERNS, field_order


class DeclaredReferenceParser(SharedSourceParser):
    def __init__(self, schema, delegate=None, stack=(), string=None, escaped=False,
                 config=None, groups=(), table_closed=False, declarations=None):
        super().__init__(schema, delegate, stack, string, escaped, config, groups, table_closed)
        self.declarations = declarations if declarations is not None else {}

    def local_values(self, path):
        spec = self.spec(path); pattern = spec.get('pattern')
        if pattern not in PATTERNS: return None
        prefix, collection = PATTERNS[pattern]
        if len(path) > 2 and path[0] == 'analyses':
            pid = path[1]
        elif len(path) == 3 and path[0] == 'object_links':
            key = 'left_premise' if path[-1] == 'left_object' else 'right_premise'
            pid = self.stack[-1].get('scalar_values', {}).get(key)
        else:
            pid = None
        count = self.declarations.get(pid, {}).get(collection, 0)
        values = {prefix+':'+str(i) for i in range(1, count+1)}
        if 'UNMAPPED' in pattern: values.add('UNMAPPED')
        return values

    def eligible_premises(self):
        return {pid for pid, counts in self.declarations.items() if counts.get('objects', 0)}

    def unused_literals(self):
        if self.stack and self.stack[-1].get('unique'):
            top = self.stack[-1]; values = self.local_values(top['path']+(top['index'],))
            if values is not None:
                return {json.dumps(v) for v in values if v not in top['seen']}
        return super().unused_literals()

    def restricted_literals(self):
        key_mode = bool(self.string and self.string['key']) or bool(
            self.string is None and self.stack and self.stack[-1]['kind'] == '{' and self.stack[-1]['expect_key'])
        if key_mode:
            top = self.stack[-1]; order = field_order(top['path'], self.spec(top['path']))
            if order is not None:
                pending = [k for k in order if k not in top.get('completed_keys', frozenset())]
                return {json.dumps(pending[0])} if pending else set()
            return super().restricted_literals()
        path = self.value_path(); values = self.local_values(path)
        if values is not None:
            # An optional reference array may close before taking any value.
            # The finite-enum viability layer already guards commas and quotes.
            if self.string is None and self.stack and self.stack[-1]['kind'] == '[':
                return None
            if self.stack and self.stack[-1].get('unique'): values -= self.stack[-1]['seen']
            return {json.dumps(v) for v in values}
        if len(path) == 3 and path[0] == 'object_links' and path[-1] in ('left_premise', 'right_premise'):
            return {json.dumps(pid) for pid in self.eligible_premises()}
        return super().restricted_literals()

    def get_allowed_characters(self):
        chars = super().get_allowed_characters()
        if self.string is None and self.stack:
            path = self.stack[-1]['path']; empty_items = False
            if len(path) == 3 and path[0] == 'analyses' and path[-1] == 'uses':
                empty_items = not self.declarations.get(path[1], {}).get('records', 0)
            elif len(path) == 5 and path[0] == 'analyses' and path[-1] == 'components':
                empty_items = not self.declarations.get(path[1], {}).get('uses', 0)
            elif path == ('object_links',):
                empty_items = not self.eligible_premises()
            if empty_items: chars = chars.replace('{', '').replace(',', '')
        return chars

    def shortcut_key(self):
        # Only unconstrained free prose can use LMFE's string shortcut. Address
        # strings and dependency-bearing keys must traverse the actual parser.
        if self.restricted_literals() is not None: return None
        return super().shortcut_key()

    def add_character(self, char):
        completed_key = None; scalar = None; declaration = None
        if char == '"' and self.string and not self.string['key'] and not self.escaped:
            scalar = json.loads(self.string['raw']+'"')
            if self.stack[-1]['kind'] == '{': completed_key = self.stack[-1]['key']
        if char in '}]' and self.string is None and self.stack:
            top = self.stack[-1]; path = top['path']
            if len(path) == 3 and path[0] == 'analyses' and path[-1] in ('records', 'objects', 'uses'):
                declaration = (path[1], path[-1], top.get('completed_items', 0))
            if len(self.stack) > 1 and self.stack[-2]['kind'] == '{': completed_key = self.stack[-2]['key']
        state = super().add_character(char)
        stack = list(state.stack)
        if completed_key is not None and stack:
            stack[-1] = dict(stack[-1]); top = stack[-1]
            top['completed_keys'] = top.get('completed_keys', frozenset()) | {completed_key}
            if scalar is not None: top['scalar_values'] = {**top.get('scalar_values', {}), completed_key: scalar}
        if char == '}' and self.string is None and stack and stack[-1]['kind'] == '[':
            stack[-1] = dict(stack[-1]); stack[-1]['completed_items'] = stack[-1].get('completed_items', 0)+1
        declarations = self.declarations
        if declaration is not None:
            pid, collection, count = declaration
            declarations = {**declarations, pid: {**declarations.get(pid, {}), collection: count}}
        return type(self)(state.schema, state.delegate, tuple(stack), state.string, state.escaped,
                          state.config, state.groups, state.table_closed, declarations)


class SchemaMask(PreviousMask):
    def __init__(self, data, schema):
        self.enforcer = CompositeQuoteEnforcer(data, DeclaredReferenceParser(schema))
        self.calls = 0; self.prefix_length = None; self.history = []
