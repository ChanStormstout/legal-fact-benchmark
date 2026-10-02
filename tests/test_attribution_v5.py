import unittest
from copy import deepcopy
from legal_bench.rules_verdict_v1.attribution_v5 import check
class AttributionGateTest(unittest.TestCase):
    def setUp(self):
        self.s={'segments':[{'id':'s','text':'The Tribunal found that X occurred.'}]}
        ev=[{'segment_id':'s','quote':'The Tribunal found that X occurred.'}]
        self.r={'status':'COURT_FOUND','origin':{'role':'COURT','side':'NOT_APPLICABLE','mention':'Tribunal','identity_evidence':ev},'attribution_evidence':ev,'finding_level':'LOWER_COURT','finding_evidence':ev}
    def test_located_binding_does_not_certify_semantics(self):
        v=check(self.r,self.s);self.assertEqual(v['structural_status'],'STRUCTURALLY_ADMISSIBLE');self.assertEqual(v['semantic_support'],'NOT_ESTABLISHED_BY_CHECKER')
    def test_unbound_combined_identity(self):
        self.r['origin']['mention']='Tribunal / Supreme Court';self.assertIn('MENTION_NOT_BOUND',check(self.r,self.s)['errors'])
    def test_missing_finding_scope(self):
        self.r['finding_level']='NOT_SHOWN';self.r['finding_evidence']=[];self.assertIn('FINDING_LEVEL_UNRESOLVED',check(self.r,self.s)['errors'])
    def test_wrong_source_is_quarantined(self):
        self.s['segments'][0]['text']='Different passage';self.assertEqual(check(self.r,self.s)['structural_status'],'QUARANTINED')
    def test_unknown_is_preserved(self):
        self.r.update(status='UNKNOWN',origin={'role':'UNKNOWN','side':'UNKNOWN','mention':'','identity_evidence':[]},finding_level='UNKNOWN',finding_evidence=[])
        self.assertEqual(check(self.r,self.s)['structural_status'],'STRUCTURALLY_ADMISSIBLE');self.assertEqual(self.r['status'],'UNKNOWN')
