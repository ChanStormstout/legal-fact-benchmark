import json,unittest,copy
from legal_bench.rules_verdict_v1.final_v9 import EXAMPLES,final_schema,compact_display,expand_display
from legal_bench.rules_verdict_v1.contracts import validate
from legal_bench.rules_verdict_v1.repetition_v9 import StringGuard,RepetitionAbort
class FinalV9Tests(unittest.TestCase):
 def test_complete_examples_valid(self):
  for e in EXAMPLES:
   validate(e['answer'],final_schema([x['id'] for x in e['case_segments']],[x['id'] for x in e['law_segments']]))
   self.assertTrue(e['answer']['reason']);self.assertNotIn('maxLength',json.dumps(final_schema(['c'],['l'])))
 def test_display_roundtrip_all_states(self):
  v={'joins':[{'id':'J1','left':'a.x','right':'b.y','result':{'state':'UNRESOLVED','basis':'CONFLICT','links':['L1','L2']}},{'id':'J2','left':'a.x','right':'c.z','result':{'state':'PROPOSED_DIFFERENT','basis':'EXPLICIT_DIFFERENCE'}},{'id':'J3','left':'d.x','right':'e.y','result':{'state':'UNRESOLVED','basis':'CONFLICT','links':['L1','L2']}}],'combinations':[{'facts':['a','b'],'condition_signals':['SUPPORT','OPPOSITION'],'state':'OPPOSED','joins':['J1']},{'facts':['a','c'],'condition_signals':['SUPPORT','OPPOSITION'],'state':'OPPOSED','joins':['J2']},{'facts':['d','e'],'condition_signals':['UNKNOWN','SUPPORT'],'state':'UNKNOWN','joins':['J3']}],'sources':['s1','s2'],'coverage_limits':['Keep every conflict']}
  original=copy.deepcopy(v);c=compact_display(v)
  self.assertEqual(expand_display(c),original);self.assertEqual(v,original)
  self.assertEqual(len(c['combinations']),3);self.assertEqual(len(c['result_definitions']),2)
 def test_merged_field_has_same_guard(self):
  f='abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ!!';g=StringGuard()
  with self.assertRaises(RepetitionAbort):
   for ch in json.dumps({'explanation':' separator '.join([f]*4)}):g.feed(ch)
  self.assertEqual(g.hit['field'],'explanation')
  g=StringGuard();g.feed(json.dumps({'point':f*3,'explanation':f*3,'reason':f*3}));self.assertIsNone(g.hit)
if __name__=='__main__':unittest.main()
