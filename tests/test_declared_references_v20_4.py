import copy
import json
import unittest
from legal_bench.mlx_json_constraint_v20_4 import DeclaredReferenceParser
from legal_bench.proof_carrying.declared_references_v20_4 import audit, wire_order


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def arr(items, minimum=0, unique=False):
    return {'type': 'array', 'items': items, 'minItems': minimum, 'maxItems': 256, 'uniqueItems': unique}


def schema():
    ev = {'type': 'string', 'pattern': '^EV:[1-9][0-9]*$'}
    use = {'type': 'string', 'pattern': '^USE:[1-9][0-9]*$'}
    role = obj({'x': {'type': 'string', 'pattern': '^(OBJ:[1-9][0-9]*|UNMAPPED)$'}})
    unit = obj({'analysis_status': {'type': 'string', 'enum': ['ANALYZED', 'NOT_ANALYZED']},
                'records': arr(obj({'text': {'type': 'string'}})), 'objects': arr(obj({'text': {'type': 'string'}})),
                'uses': arr(obj({'records': arr(ev, 1, True), 'role_objects': role})),
                'judgments': arr(obj({'uses': arr(use, 0, True), 'opposition_uses': arr(use, 0, True),
                                     'role_objects': role, 'components': arr(obj({'alternatives': arr(arr(use, 1, True), 1)}))})),
                'limits': arr({'type': 'string'})})
    endpoint = {'type': 'string', 'enum': ['A', 'B']}
    link = obj({'left_premise': endpoint, 'left_object': {'type': 'string', 'pattern': '^OBJ:[1-9][0-9]*$'},
                'right_premise': endpoint, 'right_object': {'type': 'string', 'pattern': '^OBJ:[1-9][0-9]*$'}})
    return obj({'source_sets': arr(arr({'type': 'string', 'enum': ['SRC:1', 'SRC:2']}, 1, True)),
                'analyses': obj({'A': copy.deepcopy(unit), 'B': copy.deepcopy(unit)}), 'object_links': arr(link)})


def parse(text, s=None):
    p = DeclaredReferenceParser(s or schema())
    for c in text: p = p.add_character(c)
    return p


def prefix(records=1, objects=1):
    return '{"source_sets":[],"analyses":{"A":{"analysis_status":"ANALYZED","records":'+json.dumps([{'text': 'e'}]*records)+',"objects":'+json.dumps([{'text': 'o'}]*objects)+',"uses":'


def unit(n=1):
    return {'analysis_status': 'ANALYZED', 'records': [{'text': 'e'}]*n, 'objects': [{'text': 'o'}]*n,
            'uses': [{'records': ['EV:'+str(i) for i in range(1, n+1)], 'role_objects': {'x': 'OBJ:1' if n else 'UNMAPPED'}}] if n else [],
            'judgments': [{'uses': ['USE:1'] if n else [], 'opposition_uses': [], 'role_objects': {'x': 'UNMAPPED'}, 'components': []}], 'limits': []}


class DeclaredReferences(unittest.TestCase):
    def test_legal_payload_is_unchanged_and_complete(self):
        v = {'source_sets': [], 'analyses': {'A': unit(), 'B': unit(0)}, 'object_links': []}
        self.assertEqual(wire_order(v, schema()), v)
        self.assertTrue(parse(json.dumps(v)).can_end()); self.assertEqual(audit(v, schema())['status'], 'PASS')

    def test_ev_bounds_are_actual_not_schema_max(self):
        p = parse(prefix()+'[{"records":["EV:')
        self.assertIn('1', p.get_allowed_characters()); self.assertNotIn('2', p.get_allowed_characters())
        with self.assertRaises(ValueError): parse(prefix()+'[{"records":["EV:2')

    def test_unique_exhaustion_keeps_close_without_dead_comma(self):
        p = parse(prefix()+'[{"records":["EV:1"')
        self.assertIn(']', p.get_allowed_characters()); self.assertNotIn(',', p.get_allowed_characters())

    def test_shared_digit_prefix_and_used_short_literal(self):
        p = parse(prefix(10)+'[{"records":["EV:1","EV:1')
        self.assertIn('0', p.get_allowed_characters()); self.assertNotIn('"', p.get_allowed_characters())
        p = parse(prefix(10)+'[{"records":["EV:10"')
        self.assertIn(',', p.get_allowed_characters()); self.assertIn(']', p.get_allowed_characters())

    def test_zero_records_cannot_enter_an_impossible_use(self):
        p = parse(prefix(0, 0)+'[')
        self.assertIn(']', p.get_allowed_characters()); self.assertNotIn('{', p.get_allowed_characters())

    def test_obj_bound_and_unmapped_when_empty(self):
        p = parse(prefix(1, 0)+'[{"records":["EV:1"],"role_objects":{"x":')
        p = p.add_character('"'); self.assertIn('U', p.get_allowed_characters()); self.assertNotIn('O', p.get_allowed_characters())

    def test_declaration_field_order_is_enforced(self):
        p = parse('{"source_sets":[],"analyses":{"A":{"')
        self.assertEqual(p.get_allowed_characters(), 'a')
        with self.assertRaises(ValueError): parse('{"source_sets":[],"object_links"')

    def test_use_refs_and_nested_alternatives(self):
        v = {'source_sets': [], 'analyses': {'A': unit(2), 'B': unit(0)}, 'object_links': []}
        v['analyses']['A']['judgments'][0]['components'] = [{'alternatives': [['USE:1']]}]
        self.assertTrue(parse(json.dumps(v)).can_end())
        v['analyses']['A']['judgments'][0]['components'][0]['alternatives'] = [['USE:2']]
        with self.assertRaises(ValueError): parse(json.dumps(v))
        self.assertEqual(audit(v, schema())['violations'][0]['declared_count'], 1)

    def test_scope_isolation(self):
        v = {'source_sets': [], 'analyses': {'A': unit(2), 'B': unit(1)}, 'object_links': []}
        v['analyses']['B']['uses'][0]['records'] = ['EV:2']
        with self.assertRaises(ValueError): parse(json.dumps(v))
        self.assertEqual(audit(v, schema())['violations'][0]['premise'], 'B')

    def test_links_resolve_each_endpoint_separately(self):
        v = {'source_sets': [], 'analyses': {'A': unit(2), 'B': unit(1)}, 'object_links': [
            {'left_premise': 'A', 'left_object': 'OBJ:2', 'right_premise': 'B', 'right_object': 'OBJ:1'}]}
        self.assertTrue(parse(json.dumps(v)).can_end()); self.assertEqual(audit(v, schema())['status'], 'PASS')
        v['object_links'][0]['right_object'] = 'OBJ:2'
        with self.assertRaises(ValueError): parse(json.dumps(v))
        self.assertEqual(audit(v, schema())['violations'][0]['declared_count'], 1)

    def test_empty_link_premise_excluded_before_endpoint(self):
        v = {'source_sets': [], 'analyses': {'A': unit(1), 'B': unit(0)}, 'object_links': []}
        t = json.dumps(v).rsplit('[]', 1)[0]+'[{"left_premise":"'
        p = parse(t); self.assertIn('A', p.get_allowed_characters()); self.assertNotIn('B', p.get_allowed_characters())
        v['analyses']['A'] = unit(0)
        t = json.dumps(v).rsplit('[]', 1)[0]+'['
        p = parse(t); self.assertNotIn('{', p.get_allowed_characters()); self.assertIn(']', p.get_allowed_characters())

    def test_wire_key_order_preserves_all_values_and_escaped_prose(self):
        v = {'object_links': [], 'analyses': {'A': dict(reversed(list(unit().items()))), 'B': unit(0)}, 'source_sets': []}
        v['analyses']['A']['records'][0]['text'] = 'prose "EV:999" and { [ punctuation.'
        w = wire_order(v, schema()); self.assertEqual(w, v); self.assertTrue(parse(json.dumps(w)).can_end())
        self.assertEqual(audit(w, schema())['status'], 'PASS')

    def test_zero_use_components_cannot_enter_required_alternative(self):
        t = prefix(0, 0)+'[],"judgments":[{"uses":[],"opposition_uses":[],"role_objects":{"x":"UNMAPPED"},"components":['
        p = parse(t); self.assertNotIn('{', p.get_allowed_characters()); self.assertIn(']', p.get_allowed_characters())

    def test_unmapped_not_allowed_for_link(self):
        v = {'source_sets': [], 'analyses': {'A': unit(1), 'B': unit(1)}, 'object_links': [
            {'left_premise': 'A', 'left_object': 'UNMAPPED', 'right_premise': 'B', 'right_object': 'OBJ:1'}]}
        with self.assertRaises(ValueError): parse(json.dumps(v))
        self.assertEqual(audit(v, schema())['status'], 'REJECTED_INVALID_LOCAL_REFERENCE')


if __name__ == '__main__': unittest.main()
