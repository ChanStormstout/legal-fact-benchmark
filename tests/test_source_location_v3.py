import unittest
from legal_bench.rules_verdict_v1.source_location_v3 import locate_all
class SourceLocationTests(unittest.TestCase):
 def test_whitespace_maps_raw(self):
  text='A court\n  found a fact.';r=locate_all(text,'court found');self.assertEqual(r['status'],'WHITESPACE_ONLY');a=r['matches'][0];self.assertEqual(text[a['raw_start']:a['raw_end']],'court\n  found')
 def test_no_semantic_repair(self):
  self.assertEqual(locate_all('did not consent','did consent')['status'],'UNLOCATED')
 def test_multiple_not_silently_first(self):
  r=locate_all('found X; found X','found X');self.assertFalse(r['unique']);self.assertEqual(len(r['matches']),2)
 def test_original_chars_not_changed(self):
  self.assertEqual(locate_all('“consent”','"consent"')['status'],'UNLOCATED')
 def test_blank_rejected(self):self.assertEqual(locate_all('abc','  ')['status'],'EMPTY_QUOTE')
if __name__=='__main__':unittest.main()
