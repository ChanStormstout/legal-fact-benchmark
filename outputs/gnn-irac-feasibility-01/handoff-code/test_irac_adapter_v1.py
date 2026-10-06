import copy,unittest
from legal_bench.rules_verdict_v1.irac_adapter_v1 import adapt_canonical,check_binding
class AdapterTests(unittest.TestCase):
 def fixture(self):
  n={'node_id':'f','node_type':'Fact','case_id':'case-X','local_id':'f','label':'Occupation alleged','description':'Tenant alleges shared occupation.','party_side':None,'record_status':'ALLEGED','court_status':'NOT_ADJUDICATED','ontology_mapping':{'status':'UNKNOWN','concept_id':None,'concept_label':None,'basis':None},'canonical_merge_key':None,'canonical_merge_key_basis':'NONE','source_refs':[{'document_id':'CASE_SOURCE','paragraph_id':'pre-1','exact_quote':'Tenant alleges shared occupation.'}]}
  q=copy.deepcopy(n);q.update(node_id='result',node_type='Conclusion',record_status='RECORDED',court_status='NOT_APPLICABLE',conclusion_kind='DISPOSITION');q['source_refs'][0]['paragraph_id']='post-1'
  c={'schema_version':'prompt2_v5.2_rich_canonical','case_id':'case-X','case_metadata':{'case_name':'Synthetic','decision_date':None,'citations':[]},'nodes':[n,q],'edges':[],'proof_chains':{'evidence_fact_claim':[],'precedent_issue':[],'court_conclusion_issue':[]},'knowledge_gaps':[]}
  p={'origin':'SYNTHETIC_SCHEMA_FIXTURE_NOT_REAL_GROUP_OUTPUT','node_grants':{'f':{'input_allowed':True,'field_zones':{k:'PRE_OUTCOME' for k in ['label','description','record_status','court_status']}},'result':{'input_allowed':True}},'pre_source_ids':['pre-1']};return c,p
 def test_full_canonical_keeps_weak_status_excludes_outcome(self):
  c,p=self.fixture();a=adapt_canonical(c,p);self.assertEqual([n['node_id'] for n in a['nodes']],['f']);self.assertEqual(a['nodes'][0]['record_status'],'ALLEGED');self.assertEqual(c['nodes'][1]['node_id'],'result')
 def test_current_acceptance_not_restored_by_source_locator(self):
  c,p=self.fixture();c['nodes'][0]['court_status']='ACCEPTED';self.assertFalse(adapt_canonical(c,p)['nodes'])
 def test_binding_cannot_create_fact_or_use_post_source(self):
  b={'fact_id':'made-up','condition_id':'c','relation':'SUPPORTS','case_refs':['post-1']};e=check_binding(b,{'facts':[],'pre_source_ids':['pre-1']},[{'id':'c'}]);self.assertIn('UNKNOWN_OR_NEW_FACT_FORBIDDEN',e);self.assertIn('POST_OUTCOME_REF_FORBIDDEN',e)

class RelationGuardTests(unittest.TestCase):
 def test_target_relation_not_restored_by_pre_address(self):
  from legal_bench.rules_verdict_v1.irac_adapter_v1 import legacy_inventory
  source={'segments':[{'id':'pre1'}]}
  proposal={'case_id':'synthetic','facts':[],'objects':[],'needs':[],'relations':[{'id':'r','refs':['pre1'],'court':'TARGET','status':'FOUND','text':'Current merits adoption'}]}
  adapted=legacy_inventory(proposal,source)
  self.assertEqual(adapted['relations'],[])
  self.assertIn('POSSIBLE_TARGET_ADJUDICATION_RELATION',adapted['quarantined'][0]['reasons'])
  self.assertFalse(adapted['source_partition_semantically_certified'])

if __name__=='__main__':unittest.main()
