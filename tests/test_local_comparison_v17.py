import copy
import unittest
from legal_bench.proof_carrying.local_pipeline_v17 import audit, learner_inputs, final_prompt, reviewer_material, proposal_schema, FINAL_SCHEMA
from legal_bench.proof_carrying.local_evaluation_v17 import semantic_metrics, local_metrics, equal_dispute_summary, blind_order
from legal_bench.proof_carrying.local_pipeline_v17 import validate

def fixture():
    case={'case_id':'SYN','dispute_id':'SYN','targets':[{'id':'Q1','question':'reconstruct'}],
          'segments':[{'id':'SYN:L1','source_document':'SYN','original_line':1,'text':'Mira alleged return on Friday.'},
                      {'id':'SYN:L2','source_document':'SYN','original_line':2,'text':'At trial the court found Mira retained the key on Saturday.'}]}
    rule={'id':'R1','operator':'ALL','conclusion':'Trial retained control','premises':[{'id':'R1.P1','text':'The trial court found retained control.','variables':{'tenant':'person'}}]}
    conn={'premise_id':'R1.P1','records':[1],'objects':[{'role':'tenant','object':'Mira','type':'person','refs':['SYN:L2'],'basis':'Expressly named in source.'}],
          'direction':'SUPPORT','proposed_connection':'The trial court found Mira retained the key.', 'self_assessment':'SUPPORTED',
          'whole_premise_state':'TRUE','whole_premise_complete':True,'stage':'trial',
          'witnesses':[{'refs':['SYN:L2'],'quote':'Mira retained the key on Saturday.','necessity':'REQUIRED'}],
          'opposition_records':[],'gaps':[],'explanation':'Attributed trial finding, not independent title proof.'}
    p={'records':[{'text':'The trial court found retained control.','statement_status':'COURT_FINDING','stage':'trial','refs':['SYN:L2']}],
       'connections':[conn],'coverage_limits':[]}
    return case,[rule],p

class InterfaceTests(unittest.TestCase):
    def test_schema_and_real_entry_functions_share_contract(self):
        import scripts.proof_local_comparison_v17 as entry
        c,r,p=fixture();validate(p,proposal_schema(r))
        self.assertIs(entry.audit,audit)
        self.assertIs(entry.final_prompt,final_prompt)
        self.assertEqual(audit(c,r,p)['conditional_rules'][0]['conditional_result'],'TRUE')
        self.assertEqual(audit(c,r,p)['approval'],'NOT_GRANTED')
    def test_supported_partial_and_background_not_whole_truth(self):
        c,r,p=fixture();p['connections'][0]['whole_premise_complete']=False
        self.assertEqual(audit(c,r,p)['checks'][0]['conditional_premise_state'],'UNKNOWN')
        p['connections'][0].update(whole_premise_complete=True,direction='CONTEXT')
        self.assertEqual(audit(c,r,p)['conditional_rules'][0]['conditional_result'],'UNKNOWN')
    def test_types_not_variable_mappings_and_different_mentions_not_merged(self):
        c,r,p=fixture();p['connections'].append(copy.deepcopy(p['connections'][0]))
        p['connections'][1]['objects'][0]['object']='Other person'
        g=learner_inputs(c,r,p)['graph']
        self.assertEqual(sum(n['kind']==4 for n in g['nodes']),2)
        self.assertNotIn('person',audit(c,r,p)['checks'][0]['objects_model_proposed'])
    def test_local_required_failure_does_not_swallow_records_or_other_branch(self):
        c,r,p=fixture();p['connections'].append(copy.deepcopy(p['connections'][0]))
        p['connections'][0]['witnesses'][0]['refs']=['OTHER:L2']
        a=audit(c,r,p);self.assertEqual(a['checks'][0]['conditional_premise_state'],'UNKNOWN')
        self.assertEqual(a['checks'][1]['conditional_premise_state'],'TRUE')
        self.assertEqual(a['raw_records_retained'],1)
    def test_supplementary_quote_failure_not_whole_failure(self):
        c,r,p=fixture();p['connections'][0]['witnesses'].append({'refs':['SYN:L2'],'quote':'Invented wording','necessity':'SUPPLEMENTARY'})
        a=audit(c,r,p);self.assertTrue(a['checks'][0]['warnings']);self.assertEqual(a['checks'][0]['conditional_premise_state'],'TRUE')
    def test_open_text_not_claimed_executed_and_opposition_encoded(self):
        c,r,p=fixture();r[0]['operator']='OPEN_TEXT';p['connections'][0]['direction']='OPPOSE'
        a=audit(c,r,p);self.assertTrue(a['conditional_rules'][0]['not_executed'])
        g=learner_inputs(c,r,p);self.assertTrue(any(e[2]==6 for e in g['graph']['edges']))
        self.assertIn('Mira retained the key',g['ce_pairs'][0]['right'])
        self.assertIn('actual_restored_source',next(n for n in g['graph']['nodes'] if n['id']=='C:K01')['text'])
    def test_self_assessment_hidden_from_annotator(self):
        c,r,p=fixture();v=reviewer_material(p)
        self.assertNotIn('self_assessment',v['connections'][0]);self.assertNotIn('explanation',v['connections'][0]);self.assertIn('self_assessment',p['connections'][0])
    def test_final_must_answer_and_prompt_retains_unapproved_semantics(self):
        with self.assertRaises(Exception):validate({'request_id':'Q1','conclusion':'','grounds':[],'counterarguments':[],'gaps':[],'assumptions':[],'connection_handling':[]},FINAL_SCHEMA)
        c,r,p=fixture();prompt=final_prompt(c,r,{'proposal':p,'program_checks':audit(c,r,p)})
        self.assertIn('not independent approval',prompt);self.assertIn('Mira alleged return',prompt)

class EvaluationTests(unittest.TestCase):
    def test_disputes_and_no_claim_denominator_not_zero_error(self):
        ref={'key_items':[{'id':'K1'}]}
        review={'answers':[{'answer_id':'ANSWER_01','technical_status':'OK','key_items':[{'id':'K1','status':'OMITTED'}],
                           'substantive_judgements':[{'id':'J1','status':'DISPUTED','major':True}], 'overall':'DISPUTED_OR_UNEVALUABLE'}]}
        m=semantic_metrics(review,ref)['ANSWER_01'];self.assertIsNone(m['unsupported_rate']);self.assertIsNone(m['major_error_case']);self.assertEqual(m['key_coverage'],0)
    def test_failure_is_null_and_checklist_duplicates_rejected(self):
        ref={'key_items':[{'id':'K1'}]};v={'answers':[{'answer_id':'x','technical_status':'FAILED','answer':None}]}
        self.assertIsNone(semantic_metrics(v,ref)['x']['key_coverage'])
        v['answers'][0]['answer']='UNKNOWN'
        with self.assertRaises(ValueError):semantic_metrics(v,ref)
    def test_major_error_and_macro_counts(self):
        rows=[{'key':str(i),'label':label,'dispute_id':'d','request_id':'Q1'} for i,label in enumerate(('SUPPORTED','UNSUPPORTED','UNRESOLVED'))]
        m=local_metrics([{'key':'0','label':'UNRESOLVED'},{'key':'1','label':'SUPPORTED'},{'key':'2','label':'UNRESOLVED'}],rows)
        self.assertEqual(m['error_allow_rate'],1);self.assertEqual(m['error_block_rate'],0)
        self.assertEqual(m['unresolved_predictions_by_gold']['SUPPORTED'],1)
    def test_equal_dispute_aggregation_completion_and_reproducible_blinding(self):
        rows=[{'dispute_id':'a','technical_status':'OK','key_coverage':1,'unsupported_rate':0,'major_error_case':False},
              {'dispute_id':'a','technical_status':'OK','key_coverage':1,'unsupported_rate':0,'major_error_case':False},
              {'dispute_id':'b','technical_status':'OK','key_coverage':0,'unsupported_rate':1,'major_error_case':True},
              {'dispute_id':'c','technical_status':'FAILED','key_coverage':None,'unsupported_rate':None,'major_error_case':None}]
        m=equal_dispute_summary(rows,4);self.assertEqual(m['key_coverage'],.5);self.assertEqual(m['completion_rate'],.75)
        self.assertEqual(blind_order('x','ABCDEFG'),blind_order('x','ABCDEFG'))

if __name__=='__main__':unittest.main()
