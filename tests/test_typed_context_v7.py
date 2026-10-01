import unittest
from legal_bench.typed_context_v7 import task_source,registry_map,fact_schema,CATEGORIES
from legal_bench.core import read
class TypedContextTests(unittest.TestCase):
 def test_relevant_source_is_exact_not_summarized(self):
  s={'case_id':'X','segments':[{'id':str(i),'text':'line%d'%i} for i in range(4)]};r={k:[] for k in CATEGORIES};r.update(complete=True,LEASE_PROPERTY=['2'],FILE_EVICTION=['3'])
  t=next(t for t in read('outputs/local-qwen-pattern-eval-v3/tasks.json')['tasks'] if t['task_id']=='52a7d11461a492d0');selected,_=task_source(s,[r],t)
  self.assertEqual(selected['segments'],[s['segments'][i] for i in [0,2,3]])
 def test_ambiguous_labels_are_not_guessed(self):
  with self.assertRaises(ValueError):registry_map([{'id':'o1','label':'T'},{'id':'o2','label':'T'}])
if __name__=='__main__':unittest.main()
