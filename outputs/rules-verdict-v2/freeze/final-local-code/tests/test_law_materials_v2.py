import unittest
from legal_bench.rules_verdict_v1.law_materials_v2 import units_from_judgment,eligible_units,citation_checks

class Sources(unittest.TestCase):
    def test_same_and_future_cases_excluded_even_if_relevant(self):
        sources=[{'case_id':c,'url':'https://example.test/'+c,'segments':[{'id':'p1','text':'Consent'}]} for c in ['old','target','future']]
        units=sum([units_from_judgment(s,d) for s,d in zip(sources,['1989-08-08','2004-08-13','2005-01-01'])],[])
        included,excluded=eligible_units(units,'target','2004-08-13')
        self.assertEqual([u['source']['case_id'] for u in included],['old'])
        self.assertEqual([u['reason'] for u in excluded],['SAME_CASE_TARGET_LEAKAGE','FUTURE_AUTHORITY'])

    def test_quote_verification_does_not_rewrite_controls_or_assert_entailment(self):
        sources={'x':{'segments':[{'id':'p1','text':'said "no"\nconsent\x02'}]}}
        result=citation_checks([{'case_id':'x','segment_id':'p1','quote':'"no"\nconsent'},{'case_id':'x','segment_id':'p1','quote':'no consent'}],sources)
        self.assertEqual((result['exact'],result['not_located']),(1,1))
        self.assertFalse(result['semantic_support_established'])
