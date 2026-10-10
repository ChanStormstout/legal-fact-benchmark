import json
import re
import unittest
from pathlib import Path
from scripts import irac_web_v9 as old
from scripts import irac_web_v10 as new

class LanguageContract(unittest.TestCase):
    def test_only_language_diff_all_tasks(self):
        for c in new.CASES:
            for s in ('A','P'):
                a,sa,_=old.assemble(c,s)
                b,sb,_=new.assemble(c,s)
                self.assertEqual(b,new.LANGUAGE+a)
                self.assertEqual(sa,sb)
                self.assertIsNone(re.search('[\u4e00-\u9fff]',b))
    def test_dynamic_raw_p_and_same_final_contract(self):
        for c in new.CASES:
            proposal={'records':[],'arrangements':[],'conditions':[],'limitations':[],'coverage_limits':['Synthetic fixture only.']}
            a,sa,_=new.assemble(c,'A')
            b,sb,audit=new.assemble(c,'B',proposal)
            before,rest=b.split(new.MARK,1);mid,after=rest.split(new.END,1)
            self.assertEqual(json.loads(mid),{'proposal':proposal})
            self.assertEqual(before+new.MARK+'{}'+new.END+after,a)
            self.assertEqual(sa,sb)
            self.assertTrue(audit['no_program_checks'])
    def test_transport_english_and_one_shot(self):
        self.assertIsNone(re.search('[\u4e00-\u9fff]',new.TRANSPORT))
        self.assertIn('once',new.TRANSPORT)
        self.assertIn('English',new.TRANSPORT)
        self.assertIs(new.process,old.process)
        self.assertIs(new.validate_final,old.validate_final)

if __name__=='__main__':unittest.main()
