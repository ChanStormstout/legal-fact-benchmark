import copy
import unittest
from legal_bench.rules_verdict_v1.irac_native_schema_v1 import (
    ContractError,validate_input,quote_errors,stage_partition,validate_targets,input_from_case)
from legal_bench.rules_verdict_v1.irac_graph_builder_v1 import build_input_graph

def fixture():
    avail='RETROSPECTIVELY_RECONSTRUCTED_PRE_TARGET';stage='PRE_TARGET_RECORD'
    def ref(s,q):return [{'source_id':s,'quote':q}]
    def row(i,text,s,q,**extra):
        return dict(id=i,text=text,statement_status='DOCUMENT_RECORDED',semantic_stage=stage,
                    court_level='NONE',prospective_availability=avail,source_refs=ref(s,q),**extra)
    sources={
        'LAW:1':dict(text='Exclusive possession is necessary. Mere use is insufficient.',document_id='independent',url='https://example.org/law',semantic_stage=stage,prospective_availability=avail),
        'CASE:1':dict(text='Tenant alleges that Guest merely uses Room. The lower court accepted this account.',document_id='synthetic',url='https://example.org/case',semantic_stage=stage,prospective_availability=avail)}
    data=dict(case_id='synthetic',issue=row('I','Does Guest have exclusive possession?','CASE:1','Tenant alleges that Guest merely uses Room.'),entities=[],rules=[row('R','Exclusive possession test','LAW:1',sources['LAW:1']['text'],independent_source=True,governs_issue_id='I')],conditions=[row('C1','Exclusive possession','LAW:1','Exclusive possession is necessary.',rule_id='R',dependencies=[]),row('C2','Mere use insufficient','LAW:1','Mere use is insufficient.',rule_id='R',dependencies=[dict(condition_id='C1',operator='QUALIFICATION')])],facts=[row('F','Guest merely uses Room','CASE:1','Tenant alleges that Guest merely uses Room.')],evidence=[],relations=[],blind_bindings=[],stage_metadata={},provenance=sources,prospective_availability=avail)
    data['facts'][0]['statement_status']='CLAIMED'
    data['blind_bindings']=[row('B','Candidate relevance','CASE:1','Tenant alleges that Guest merely uses Room.',fact_id='F',condition_id='C1',relation='RELEVANT_TO')]
    data['blind_bindings'][0]['statement_status']='CLAIMED'
    return data

class NativeTests(unittest.TestCase):
    def test_valid_fixture(self):self.assertEqual(validate_input(fixture()),[])
    def test_target_field_forbidden(self):
        x=fixture();x['element_targets']=[];self.assertTrue(any('FORBIDDEN' in e for e in validate_input(x)))
    def test_target_change_no_input_hash_change(self):
        x={'input':fixture(),'target':{'element_targets':[{'status':'SATISFIED'}]}}
        a=build_input_graph(input_from_case(x))['graph_hash'];x['target']['element_targets'][0]['status']='DEFEATED'
        self.assertEqual(a,build_input_graph(input_from_case(x))['graph_hash'])
    def test_target_stage_excluded(self):
        x=fixture();r=x['facts'][0];r['semantic_stage']='TARGET_COURT_REASONING'
        admitted,excluded=stage_partition([r],x['provenance']);self.assertFalse(admitted);self.assertTrue(excluded)
    def test_target_disposition_source_excluded(self):
        x=fixture();x['provenance']['CASE:1']['semantic_stage']='TARGET_DISPOSITION';self.assertTrue(validate_input(x))
    def test_prior_finding_preserved_not_promoted(self):
        x=fixture();r=x['facts'][0];r.update(statement_status='PRIOR_FOUND',semantic_stage='PRIOR_COURT_FINDING',court_level='RENT_CONTROLLER');x['blind_bindings'][0].update(statement_status='PRIOR_FOUND',semantic_stage='PRIOR_COURT_FINDING',court_level='RENT_CONTROLLER')
        g=build_input_graph(x);self.assertEqual(next(n for n in g['nodes'] if n['id']=='F')['features']['court_level'],'RENT_CONTROLLER')
    def test_prior_not_target_accepted(self):
        x=fixture();x['facts'][0].update(statement_status='PRIOR_FOUND',semantic_stage='PRIOR_COURT_FINDING',court_level='TARGET');self.assertIn('PRIOR_FINDING_PROMOTED',validate_input(x))
    def test_dangling_blocks_graph(self):
        x=fixture();x['facts'][0]['entity_ids']=['excluded']
        with self.assertRaises(ContractError):build_input_graph(x)
    def test_cascading_endpoint_exclusion(self):
        x=fixture();f=x['facts'][0];ent=copy.deepcopy(f);ent.update(id='E',semantic_stage='TARGET_DISPOSITION');f['entity_ids']=['E'];admitted,excluded=stage_partition([f,ent],x['provenance']);self.assertEqual(admitted,[]);self.assertTrue(any('DEPENDENCY_ENDPOINT_EXCLUDED' in r['reasons'] for r in excluded))
    def test_binding_nonexistent_fact(self):
        x=fixture();x['blind_bindings'][0]['fact_id']='NEW';self.assertIn('BINDING_FACT_NOT_ADMITTED',validate_input(x))
    def test_binding_cannot_change_status(self):
        x=fixture();x['blind_bindings'][0]['statement_status']='ADMITTED';self.assertIn('BINDING_CHANGED_STATEMENT_STATUS',validate_input(x))
    def test_separate_contiguous_quotes(self):
        x=fixture();sources=x['provenance'];self.assertEqual(quote_errors([{'source_id':'LAW:1','quote':'Exclusive possession is necessary.'},{'source_id':'LAW:1','quote':'Mere use is insufficient.'}],sources),[])
        self.assertTrue(quote_errors([{'source_id':'LAW:1','quote':'Exclusive possession\nMere use is insufficient.'}],sources))
    def test_independent_rule_required(self):
        x=fixture();x['rules'][0]['independent_source']=False;self.assertTrue(any('INDEPENDENT_RULE' in e for e in validate_input(x)))
    def test_target_judgment_not_independent_rule(self):
        x=fixture();x['provenance']['LAW:1']['document_id']='synthetic';self.assertIn('TARGET_JUDGMENT_CANNOT_BE_INPUT_RULE',validate_input(x))
    def test_unknown_not_false(self):
        x=fixture();x['facts'][0]['statement_status']='UNKNOWN';x['blind_bindings'][0]['statement_status']='UNKNOWN';g=build_input_graph(x);self.assertEqual(next(n for n in g['nodes'] if n['id']=='F')['features']['statement_status'],'UNKNOWN')
    def test_burden_not_fact_false(self):
        x=fixture();t={'element_targets':[dict(condition_id='C1',status='DEFEATED',basis_kind='BURDEN_NOT_CARRIED',fact_truth='FALSE',target_refs=[{'source_id':'CASE:1','quote':'Tenant alleges that Guest merely uses Room.'}])],'issue_target':dict(status='NOT_SUPPORTED',target_refs=[{'source_id':'CASE:1','quote':'Tenant alleges that Guest merely uses Room.'}],procedural_scope='synthetic',reasoning='burden',derivative_or_de_novo='de_novo',unresolved_element_relationship='not decided')};self.assertIn('BURDEN_IS_NOT_FACT_FALSE',validate_targets(t,{'C1','C2'},x['provenance']))
    def test_graph_api_rejects_case_envelope(self):
        with self.assertRaises(ContractError):build_input_graph({'input':fixture(),'target':{}})
    def test_no_identity_edge_invented(self):
        g=build_input_graph(fixture());self.assertEqual(len(g['edges']),4);self.assertFalse(any(e['type']=='FACT_RELATES_TO_ENTITY' for e in g['edges']))
    def test_binding_provenance_must_be_original(self):
        x=fixture();x['blind_bindings'][0]['source_refs']=[{'source_id':'CASE:1','quote':'The lower court accepted this account.'}];self.assertIn('BINDING_REF_NOT_IN_RECORD_PROVENANCE',validate_input(x))
    def test_stage_sidecar_cannot_hide_target(self):
        x=fixture();x['stage_metadata']={'court_adopted':True};self.assertIn('STAGE_METADATA_NOT_INPUT_SAFE',validate_input(x))
    def test_relation_endpoint_types_checked(self):
        x=fixture();r=copy.deepcopy(x['facts'][0]);r.update(id='REL',source_record_id='F',target_record_id='C1',relation='EVIDENCE_SUPPORTS_FACT');x['relations']=[r];self.assertIn('RELATION_ENDPOINT_TYPES_INVALID',validate_input(x))
    def test_prior_court_edge_cannot_promote_allegation(self):
        x=fixture();ent=copy.deepcopy(x['facts'][0]);ent['id']='COURT';x['entities']=[ent];r=copy.deepcopy(ent);r.update(id='REL',source_record_id='COURT',target_record_id='F',relation='PRIOR_COURT_FOUND_FACT');x['relations']=[r];self.assertIn('PRIOR_COURT_EDGE_NOT_SUPPORTED_BY_FACT_STATUS',validate_input(x))
    def test_malformed_issue_has_explicit_error(self):
        x=fixture();x['issue']='bad';self.assertEqual(validate_input(x),['ISSUE_REQUIRED'])
    def test_missing_id_has_explicit_error(self):
        x=fixture();del x['facts'][0]['id'];self.assertIn('RECORD_ID_REQUIRED:facts',validate_input(x))

if __name__=='__main__':unittest.main()
