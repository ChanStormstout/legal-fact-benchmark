"""V20.4 local bounds plus declared type conflicts and nonblank citation enums."""
import json
from legal_bench.mlx_json_constraint_v20_4 import DeclaredReferenceParser
from legal_bench.mlx_json_constraint_v20_1 import SchemaMask as PreviousMask
from legal_bench.mlx_json_constraint_v2 import CompositeQuoteEnforcer
from legal_bench.proof_carrying.evidence_binding_gate_v20_5 import ROLE_DESCRIPTION
from legal_bench.proof_carrying.object_types_v19 import compare


class EvidenceBindingParser(DeclaredReferenceParser):
    def local_values(self, path):
        values = super().local_values(path)
        description = self.spec(path).get('description', '')
        if values is None or not description.startswith(ROLE_DESCRIPTION):
            return values
        expected = description[len(ROLE_DESCRIPTION):]
        types = self.declarations.get(path[1], {}).get('object_types', ())
        return {v for v in values if v == 'UNMAPPED' or
                compare(types[int(v.split(':')[1])-1], expected)['status'] != 'EXPLICIT_TYPE_CONFLICT'}

    def add_character(self, char):
        typed_object = None
        if char == '}' and self.string is None and self.stack:
            top = self.stack[-1]; path = top['path']
            if len(path) == 4 and path[0] == 'analyses' and path[2] == 'objects':
                typed_object = (path[1], top.get('scalar_values', {}).get('type', 'UNMAPPED'))
        state = super().add_character(char)
        if typed_object is not None:
            pid, typ = typed_object
            counts = state.declarations.get(pid, {})
            state.declarations = {**state.declarations, pid: {
                **counts, 'object_types': counts.get('object_types', ())+(typ,)}}
        return state

    def get_allowed_characters(self):
        chars = super().get_allowed_characters()
        if self.string is None and self.stack:
            path = self.stack[-1]['path']
            if path == ('source_sets',) and not self.schema['$defs']['source_choice']['enum']:
                chars = chars.replace('[', '').replace(',', '')
            if len(path) == 3 and path[0] == 'analyses' and path[-1] in ('records', 'objects') and not self.groups:
                chars = chars.replace('{', '').replace(',', '')
        return chars


class SchemaMask(PreviousMask):
    def __init__(self, data, schema):
        self.enforcer = CompositeQuoteEnforcer(data, EvidenceBindingParser(schema))
        self.calls = 0; self.prefix_length = None; self.history = []
