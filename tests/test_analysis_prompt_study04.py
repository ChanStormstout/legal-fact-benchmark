import unittest
from legal_bench.rules_verdict_v1.analysis_prompt_study04 import ADDITION,MARKER,treatment,order_cases,parse_raw
class AnalysisStudyTests(unittest.TestCase):
 def test_exact_addition_only(self):
  base='case and law untouched\n'+MARKER+'{}'
  self.assertEqual(treatment(base).replace(ADDITION+'\n','',1),base)
 def test_unique_marker(self):
  with self.assertRaises(ValueError):treatment('no marker')
 def test_balanced_order_deterministic(self):
  cs=list('abcdef');x=order_cases(cs,20261004)
  self.assertEqual(x,order_cases(cs,20261004));self.assertEqual(len(x),12)
  self.assertEqual(sum(x[i]['arm']=='CONTROL' for i in range(0,12,2)),3)
 def test_format_failure_not_unknown(self):
  x=parse_raw('{"outcome":',[],[]);self.assertEqual(x['run_status'],'FORMAT_ERROR');self.assertIsNone(x['answer'])
 def test_complete_wrapped_answer_retains_value(self):
  x=parse_raw('```json\n{"outcome":"UNDETERMINED","grounds":[],"reason":"Only a syntax fixture."}\n```\nEND',[],[])
  self.assertEqual(x['run_status'],'OK');self.assertEqual(x['answer']['reason'],'Only a syntax fixture.')
if __name__=='__main__':unittest.main()
