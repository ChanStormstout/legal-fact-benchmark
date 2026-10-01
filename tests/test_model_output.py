import unittest
from legal_bench.model_output import parse_one,failure_answers
class ModelOutputTests(unittest.TestCase):
 def test_complete_root_extra_closers_only_are_logged(self):
  obj,changes=parse_one(b'{"answer":"UNKNOWN","quote":"x"}\n]}');self.assertEqual(obj,{'answer':'UNKNOWN','quote':'x'});self.assertTrue(changes)
 def test_incomplete_root_or_second_object_is_never_repaired(self):
  for s in [b'{"x":[{"a":1}}]}',b'{"a":1}{"b":2}',b'{"a":']:
   with self.assertRaises(ValueError):parse_one(s)
 def test_failure_never_becomes_unknown(self):
  self.assertEqual(failure_answers([{'task_id':'q'}],'FORMAT_ERROR','bad')[0]['answer_status'],None)
