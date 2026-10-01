import unittest,json
from legal_bench.compact_output_v3 import schema,validate_shape,examples,convert
from legal_bench.core import read

class BoundedFormatTests(unittest.TestCase):
 def setUp(self):
  self.tasks=read('outputs/local-qwen-pattern-eval-v3/tasks.json')['tasks'];self.source={'case_id':'DEMO','segments':[{'id':'demo.s001','text':('Quote: "x"\n\t\u0001 '+ 'a'*300)*4}]}
 def test_generated_label_bound_does_not_cut_source_evidence(self):
  b,_=examples(self.tasks);converted,_=convert(b,self.source,'B',self.tasks)
  self.assertEqual(converted['events'][0]['evidence'][0]['quote'],self.source['segments'][0]['text'])
  b['objects'][0]['label']='a'*241
  with self.assertRaises(ValueError):validate_shape(b,schema(self.source,'B',self.tasks))
 def test_array_bound_rejects_without_discarding_items(self):
  b,_=examples(self.tasks);b['unit_evidence']=['demo.s001']*21
  with self.assertRaises(ValueError):convert(b,self.source,'B',self.tasks)

if __name__=='__main__':unittest.main()
