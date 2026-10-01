import unittest
from legal_bench.chunked_extraction_v4 import chunks,routed_source
class ChunkedExtractionTests(unittest.TestCase):
 def setUp(self):self.source={'case_id':'X','segments':[{'id':str(i),'text':'x'*n} for i,n in enumerate([3,9,2,5])]}
 def test_all_segments_retained_including_oversize(self):
  c=chunks(self.source,5);self.assertEqual([s for g in c for s in g],self.source['segments']);self.assertEqual(c[1][0]['text'],'x'*9)
 def test_context_is_lossless_not_a_new_assertion(self):
  r,m=routed_source(self.source,[{'relevant':['1'],'uncertain':[],'complete':True}],1);self.assertEqual(r['segments'],self.source['segments'][:3]);self.assertEqual(m['context_ids'],['0','2'])
 def test_partial_routing_does_not_become_negative(self):
  with self.assertRaises(ValueError):routed_source(self.source,[{'relevant':[],'uncertain':[],'complete':False}])
if __name__=='__main__':unittest.main()
