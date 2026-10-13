"""One constraint repair regression suite; no neural generation."""
import unittest

from legal_bench.mlx_json_constraint_v19_6 import UniqueStringParser
from legal_bench.mlx_json_constraint_v20_1 import ViableUniqueEnumParser


def parse(cls, schema, text):
    p = cls(schema)
    for c in text:
        p = p.add_character(c)
    return p


class ConstraintViability(unittest.TestCase):
    def test_real_shape_dead_branch_and_legal_shared_prefix(self):
        s = {'type': 'array', 'uniqueItems': True,
             'items': {'type': 'string', 'enum': ['SRC:16', 'SRC:167', 'SRC:168', 'SRC:169']}}
        prefix = '["SRC:169","SRC:168","SRC:16'
        old = parse(UniqueStringParser, s, prefix)
        self.assertIn('8', old.get_allowed_characters())
        self.assertEqual(old.add_character('8').get_allowed_characters(), '')
        new = parse(ViableUniqueEnumParser, s, prefix)
        self.assertNotIn('8', new.get_allowed_characters())
        self.assertNotIn('9', new.get_allowed_characters())
        self.assertIn('7', new.get_allowed_characters())
        self.assertIn('"', new.get_allowed_characters())
        self.assertTrue(parse(ViableUniqueEnumParser, s, prefix + '7"]').can_end())

    def test_all_enum_values_consumed_can_close_not_append(self):
        s = {'type': 'array', 'uniqueItems': True,
             'items': {'type': 'string', 'enum': ['SRC:1', 'SRC:10']}}
        p = parse(ViableUniqueEnumParser, s, '["SRC:1","SRC:10"')
        self.assertNotIn(',', p.get_allowed_characters())
        self.assertIn(']', p.get_allowed_characters())
        self.assertTrue(p.add_character(']').can_end())

    def test_separate_arrays_do_not_share_seen_values(self):
        a = {'type': 'array', 'uniqueItems': True,
             'items': {'type': 'string', 'enum': ['SRC:1']}}
        s = {'type': 'object', 'properties': {'a': a, 'b': a}, 'required': ['a', 'b'],
             'additionalProperties': False}
        self.assertTrue(parse(ViableUniqueEnumParser, s,
                              '{"a":["SRC:1"],"b":["SRC:1"]}').can_end())

    def test_non_unique_enum_still_allows_repetition(self):
        s = {'type': 'array', 'items': {'type': 'string', 'enum': ['SRC:1']}}
        self.assertTrue(parse(ViableUniqueEnumParser, s, '["SRC:1","SRC:1"]').can_end())


if __name__ == '__main__':
    unittest.main()
