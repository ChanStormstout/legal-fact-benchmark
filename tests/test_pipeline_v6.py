import unittest
from legal_bench.rules_verdict_v1.pipeline_v6 import execute
class PipelineV6Test(unittest.TestCase):
 def setUp(self):
  self.pkg={'cards':[{'rule_card_id':'RC-01'}],'scope':{'mode':'TEST'}};self.view={'assertions':[],'quarantine':[]}
 def add(self,prop,value,event='E',status='NARRATED',unknown=None):
  self.view['assertions'].append({'id':str(len(self.view['assertions'])),'event':event,'tenant':'T','landlord':'L','recipient':'R','premises':'P','property':prop,'value':value,'status':status,'uncertain_fields':unknown or []})
 def complete(self,event='E'):
  for p,v in [('TENANCY','YES'),('TRANSFER_MODE','SUBLET'),('AFTER_1952_06_09','YES'),('LANDLORD_WRITTEN_CONSENT','NO')]:self.add(p,v,event)
 def test_full_conjunction(self):
  self.complete();self.assertEqual(execute(self.view,self.pkg)['outcome'],'SUPPORT_GROUND')
 def test_missing_date_blocks_only_date(self):
  self.complete();self.view['assertions'][2]['uncertain_fields']=['value'];r=execute(self.view,self.pkg);self.assertEqual(r['outcome'],'UNDETERMINED');self.assertEqual(r['bindings'][0]['conditions']['TENANCY']['state'],'SUPPORTED')
 def test_cross_event_not_joined(self):
  self.complete();self.view['assertions'][-1]['event']='OTHER';self.assertEqual(execute(self.view,self.pkg)['outcome'],'UNDETERMINED')
 def test_claim_not_finding(self):
  self.complete();self.view['assertions'][-1]['status']='PARTY_CLAIMED';self.assertEqual(execute(self.view,self.pkg)['outcome'],'UNDETERMINED')
 def test_failed_pair_not_case_absence(self):
  self.complete();self.view['assertions'][-1]['value']='YES';self.assertEqual(execute(self.view,self.pkg)['outcome'],'UNDETERMINED');self.complete('E2');self.assertEqual(execute(self.view,self.pkg)['outcome'],'SUPPORT_GROUND')
 def test_missing_law_does_not_skip_conditions(self):
  self.complete();r=execute(self.view,{'cards':[],'scope':{}});self.assertEqual(r['outcome'],'UNSUPPORTED');self.assertEqual(len(r['bindings']),1)
 def test_conflict_not_positive(self):
  self.complete();self.add('LANDLORD_WRITTEN_CONSENT','YES');self.assertEqual(execute(self.view,self.pkg)['outcome'],'UNDETERMINED')
