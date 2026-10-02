import unittest
from legal_bench.rules_verdict_v1.boolean_format_v3 import parse_boolean_literals


class BooleanFormatTests(unittest.TestCase):
    def test_only_bare_booleans_change(self):
        raw='{"primary":False,"quote":"True and False \\"yes\\"", "flag":True}'
        value,repairs,_=parse_boolean_literals(raw)
        self.assertEqual(value['quote'],'True and False "yes"')
        self.assertIs(value['primary'],False);self.assertEqual(len(repairs),2)

    def test_other_errors_not_guessed(self):
        for raw in ['{"primary":None}', '{"primary":False', '{"quote":"bad\nquote"}', '{"primary":Falsehood}']:
            with self.assertRaises(ValueError):parse_boolean_literals(raw)


if __name__=='__main__':unittest.main()
