import unittest
from legal_bench.registry_extraction_v5 import object_schema,objects,fact_schema
from legal_bench.core import read
class RegistryExtractionTests(unittest.TestCase):
 def setUp(self):self.source={'case_id':'X','segments':[{'id':'s1','text':'source'}]};self.tasks=read('outputs/local-qwen-pattern-eval-v3/tasks.json')['tasks']
 def test_unique_structural_slots_not_segment_ids(self):
  s=object_schema(self.source);self.assertEqual(list(s['properties']['slots']['properties']),['o%d'%i for i in range(1,13)])
 def test_no_group_means_no_membership_edge_can_be_generated(self):
  t=next(t for t in self.tasks if t['task_id']=='52a7d11461a492d0');sc=fact_schema(self.source,[{'id':'o1','kind':'PERSON'}],t)
  self.assertEqual(sc['properties']['edges']['maxItems'],0)
 def test_actor_roles_cannot_point_to_property(self):
  t=next(t for t in self.tasks if t['task_id']=='9c74983b08ed3850');sc=fact_schema(self.source,[{'id':'o1','kind':'PERSON'},{'id':'o2','kind':'PROPERTY'}],t)
  own=next(v for v in sc['properties']['events']['items']['anyOf'] if v['properties']['type']['enum']==['OWN_PROPERTY']);owner=next(v for v in own['properties']['roles']['items']['anyOf'] if v['properties']['name']['enum']==['owner'])
  self.assertEqual(owner['properties']['object']['anyOf'][0]['enum'],['o1'])
if __name__=='__main__':unittest.main()
