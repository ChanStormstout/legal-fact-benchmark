import unittest
from legal_bench.registry_extraction_v6 import objects,object_schema,fact_schema
from legal_bench.core import read
class ArrayRegistryTests(unittest.TestCase):
 def setUp(self):self.source={'case_id':'X','segments':[{'id':'s1','text':'quote'}]}
 def test_id_assignment_does_not_change_identity_or_evidence(self):
  x={'label':'Tenant T','kind':'PERSON','resolved':False,'evidence':['s1']};v=objects({'case_id':'X','objects':[x],'overflow':False},self.source)
  self.assertEqual(v,[dict(id='o1',**x)])
 def test_absent_group_uses_explicit_sentinel_not_fabricated_edge(self):
  t=next(t for t in read('outputs/local-qwen-pattern-eval-v3/tasks.json')['tasks'] if t['task_id']=='52a7d11461a492d0')
  s=fact_schema(self.source,[{'id':'o1','kind':'PERSON'}],t)
  self.assertEqual(s['properties']['edges'],{'enum':['NO_ELIGIBLE_OBJECT_PAIR']})
if __name__=='__main__':unittest.main()
