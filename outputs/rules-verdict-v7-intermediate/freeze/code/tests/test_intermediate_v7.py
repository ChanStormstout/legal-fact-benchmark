import copy,unittest
from legal_bench.rules_verdict_v1.intermediate_v7 import check_facts
class V7Tests(unittest.TestCase):
 def setUp(self):
  self.source={'segments':[{'id':'s1','text':'Mira leased Shed Q from L. The handover involved Neri.'},{'id':'s2','text':'Mira used Shed Q. Another handover is disputed.'}]}
  m=lambda text,s='s1':{'text':text,'refs':[s]}
  self.data={'tenancies':[{'id':'t','tenant':m('Mira'),'landlord':None,'premises':m('Shed Q'),'value':'YES','status':'NARRATED','uncertain':[],'refs':['s1']}],
   'transfers':[{'id':'x','event':m('handover'),'transferor':m('Mira'),'recipient':None,'premises':m('Shed Q'),'mode':'SUBLET','status':'NARRATED','uncertain':[],'refs':['s1']}],
   'times':[],'consents':[],'links':[],'coverage_limits':''}
 def runcheck(self):return check_facts(self.data,self.source)[0]
 def test_partial_tenancy_survives(self):
  r=self.runcheck();self.assertEqual(r['record_checks'][0]['signal'],'PROPOSED_SUPPORT');self.assertIsNone(r['final_legal_conclusion']);self.assertEqual(r['combination_counts']['enumerated'],0)
 def test_local_unknown(self):
  self.data['transfers'][0]['uncertain']=['recipient'];r=self.runcheck();self.assertEqual(r['record_checks'][0]['signal'],'PROPOSED_SUPPORT');self.assertEqual(r['record_checks'][1]['signal'],'PROPOSED_SUPPORT')
 def test_null_not_wildcard(self):
  self.data['tenancies'][0]['tenant']=None;self.data['transfers'][0]['transferor']=None
  self.assertEqual(self.runcheck()['tenancy_transfer_checks'][0]['joins'][0]['state'],'UNRESOLVED')
 def test_role_word_or_other_source_not_identity(self):
  self.data['transfers'][0]['transferor']['refs']=['s2']
  self.assertEqual(self.runcheck()['tenancy_transfer_checks'][0]['joins'][0]['state'],'UNRESOLVED')
 def test_same_paragraph_not_identity(self):
  self.data['transfers'][0]['transferor']['text']='Neri'
  self.assertEqual(self.runcheck()['tenancy_transfer_checks'][0]['joins'][0]['state'],'UNRESOLVED')
 def test_conflicting_links(self):
  for rel in ['SAME','DIFFERENT']:self.data['links'].append({'left':'t.tenant','right':'x.transferor','relation':rel,'status':'NARRATED','refs':['s1']})
  self.assertEqual(self.runcheck()['tenancy_transfer_checks'][0]['joins'][0]['basis'],'CONFLICTING_MODEL_LINKS')
 def test_claim_not_accepted(self):
  self.data['transfers'][0]['status']='PARTY_CLAIMED';r=self.runcheck();self.assertEqual(r['record_checks'][1]['signal'],'UNRESOLVED');self.assertEqual(len(r['record_checks']),2)
 def test_unknown_scope_not_silently_ignored(self):
  self.data['tenancies'][0]['uncertain']=['some qualifier'];self.assertIn('UNKNOWN_UNCERTAINTY_SCOPE',self.runcheck()['record_checks'][0]['blockers'])
 def test_duplicate_id_not_identity(self):
  self.data['transfers'][0]['id']='t';r=self.runcheck();self.assertIn('DUPLICATE_FACT_ID',r['record_checks'][0]['blockers']);self.assertEqual(r['tenancy_transfer_checks'][0]['joins'][0]['state'],'UNRESOLVED')
if __name__=='__main__':unittest.main()
