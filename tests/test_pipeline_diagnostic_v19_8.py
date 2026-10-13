import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_pipeline_contract_v19_7 import fixture
from scripts import proof_pipeline_contract_v19_8 as entry
from legal_bench.proof_carrying import local_pipeline_v19_8 as pipe,final_delivery_v19_8 as delivery
from legal_bench.proof_carrying.local_schedule_v19 import state
from legal_bench.proof_carrying.presentation_v19_8 import pack,unpack
from legal_bench.proof_carrying.rule_contracts_v19_7 import digest


def process(c,r,x):
    return entry.process_saved(c,r,part(c,r),json.dumps(x),pipe.schema(r,c),'V19_7','OK')
def part(c,r):return {'id':'P01','rule_ids':[z['id'] for z in r],'source_ids':[z['id'] for z in c['segments']]}
def pair():
    c,r,x=fixture();p=copy.deepcopy(r[0]['premises'][0]);p['id']='R1.P2'
    p['input_contract']['components'][0]['id']='R1.P2.K1';r[0]['premises'].append(p)
    r[0]['slot_variables'][p['id']]={'tenant':'R1::tenant'}
    x['analyses'][p['id']]=copy.deepcopy(x['analyses']['R1.P1'])
    x['analyses'][p['id']]['judgments'][0]['components'][0]['component_id']='R1.P2.K1'
    return c,r,x
class Tokenizer:
    def apply_chat_template(self,*args,**kwargs):return [1]*10
CFG={'context_budget':65536,'max_output_tokens':8192,'template_margin':256}
def final_answer():
    return {'request_id':'Q1','conclusion':'Mock only; no legal evaluation.',
        'grounds':[{'point':'Mock','statement_status_and_stage':'synthetic','case_refs':[], 'rule_refs':[], 'explanation':'Mock'}],
        'counterarguments':[],'gaps':[],'assumptions':[],'connection_handling':[]}

class DiagnosticPipeline(unittest.TestCase):
    def test_actual_saved_entry_unchanged_P(self):
        c,r,x=fixture();a=process(c,r,x);self.assertEqual(a['contract_status'],'CONTRACT_VALID')
        self.assertEqual(a['formal_answer'],x);self.assertFalse(a['semantic_approval'])
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);entry.save(d/'run.json',{'run_status':'OK'});entry.text(d/'raw-response.txt',json.dumps(x));entry.save(d/'schema.json',pipe.schema(r,c))
            self.assertEqual(entry.accept_saved_output(c,r,part(c,r),d)['contract_status'],'CONTRACT_VALID')

    def test_postcompute_fidelity_through_actual_entry(self):
        c,r,x=fixture();original=pipe.apply_connection_decisions
        faults=[('checks','binding',{'R1::tenant':999}),('checks','direction','OPPOSE'),
                ('checks','applied_label','UNSUPPORTED'),('checks','locations',[]),('checks','scope_checks',[]),
                ('premise_judgments','basis','Invented'),('premise_judgments','gaps',['Invented']),
                ('premise_judgments','model_state','FALSE'),('premise_judgments','components',[])]
        for collection,key,value in faults:
            with self.subTest(key=key):
                def corrupt(*args):
                    a=original(*args);a[collection][0][key]=value;return a
                with patch.object(pipe,'apply_connection_decisions',corrupt):a=process(c,r,x)
                self.assertEqual(a['contract_status'],'CHECK_REJECTED');self.assertIsNone(a['formal_answer'])

    def test_full_count_and_route_fidelity(self):
        c,r,x=fixture();original=pipe.apply_connection_decisions
        for field in ('premise_judgments','conditional_rules'):
            def corrupt(*args):
                a=original(*args);a[field]=[];return a
            with patch.object(pipe,'apply_connection_decisions',corrupt):a=process(c,r,x)
            self.assertEqual(a['contract_status'],'CHECK_REJECTED')

    def test_closed_empty_status_policy_retains_use_not_truth(self):
        c,r,x=fixture();r[0]['premises'][0]['input_contract']['whole_basis_statuses']=[]
        a=process(c,r,x);audit=a['conditional_audit'];self.assertEqual(a['independent_check']['status'],'OK')
        self.assertEqual(audit['checks'][0]['disposition'],'CONDITIONALLY_AVAILABLE_USE')
        self.assertFalse(audit['checks'][0]['full_basis_eligible'])
        self.assertEqual(audit['premise_judgments'][0]['conditional_state'],'UNKNOWN')

    def test_false_one_refuted_necessary_component(self):
        c,r,x=fixture();rc=r[0]['premises'][0]['input_contract'];rc['components'].append({'id':'R1.P1.K2','text':'A second necessary synthetic condition.'})
        u=x['analyses']['R1.P1'];u['uses'][0]['direction']='OPPOSE';j=u['judgments'][0];j['state']='FALSE'
        # FALSE may name the one refuted necessary component; K2 stays unassessed.
        a=process(c,r,x);self.assertEqual(a['contract_status'],'CONTRACT_VALID')
        self.assertEqual(a['conditional_audit']['premise_judgments'][0]['conditional_state'],'FALSE')
        self.assertEqual(len(a['conditional_audit']['premise_judgments'][0]['components']),1)

    def test_false_not_derived_from_support_and_true_not_from_opposition(self):
        c,r,x=fixture();j=x['analyses']['R1.P1']['judgments'][0];j['state']='FALSE'
        a=process(c,r,x);self.assertEqual(a['conditional_audit']['premise_judgments'][0]['conditional_state'],'UNKNOWN')
        j['state']='TRUE';x['analyses']['R1.P1']['uses'][0]['direction']='OPPOSE'
        a=process(c,r,x);self.assertEqual(a['conditional_audit']['premise_judgments'][0]['conditional_state'],'UNKNOWN')

    def test_missing_identity_retained_not_merged_and_explicit_link_restores(self):
        c,r,x=pair();a=process(c,r,x);t=a['conditional_audit']['conditional_rules'][0]
        self.assertEqual(t['conditional_result'],'UNKNOWN');self.assertEqual(t['join_status'],'IDENTITY_PENDING')
        self.assertEqual(len(t['binding_candidates']['R1::tenant']),2)
        x['object_links']=[{'left_premise':'R1.P1','left_object':'OBJ:1','right_premise':'R1.P2','right_object':'OBJ:1',
            'refs':['SRC:3'],'identity_basis':'Synthetic explicit identity statement.'}]
        a=process(c,r,x);self.assertEqual(a['conditional_audit']['conditional_rules'][0]['conditional_result'],'TRUE')
        self.assertEqual(a['independent_check']['status'],'OK')

    def test_type_conflict_still_rejected(self):
        c,r,x=fixture();x['analyses']['R1.P1']['objects'][0]['type']='PROPERTY'
        a=process(c,r,x);self.assertEqual(a['conditional_audit']['checks'][0]['disposition'],'STRUCTURAL_INVALID')
        self.assertEqual(a['conditional_audit']['premise_judgments'][0]['conditional_state'],'UNKNOWN')

    def test_independent_any_branch_not_poisoned_and_exception_retained(self):
        c,r,x=pair();r[0]['operator']='ANY';x['analyses']['R1.P2']['judgments'][0]['complete']=False
        a=process(c,r,x);t=a['conditional_audit']['conditional_rules'][0]
        self.assertEqual(t['conditional_result'],'TRUE');self.assertEqual(t['winning_branch_inputs'],['J001'])
        self.assertEqual(a['independent_check']['status'],'OK')
        r[0]['exceptions']=['An unevaluated exception remains.']
        a=process(c,r,x);self.assertEqual(a['conditional_audit']['conditional_rules'][0]['conditional_result'],'UNKNOWN')

    def test_local_bad_use_preserves_record_and_other_alternative(self):
        c,r,x=fixture();u=x['analyses']['R1.P1'];u['uses'].append(copy.deepcopy(u['uses'][0]));u['uses'][0]['records']=['EV:999']
        j=u['judgments'][0];j['uses']=['USE:1','USE:2'];j['components'][0]['alternatives']=[['USE:1'],['USE:2']]
        a=process(c,r,x);self.assertEqual(a['contract_status'],'CONTRACT_VALID');self.assertEqual(len(a['canonical_P']['records']),1)
        self.assertEqual(a['conditional_audit']['checks'][0]['disposition'],'STRUCTURAL_INVALID')
        self.assertEqual(a['conditional_audit']['premise_judgments'][0]['conditional_state'],'TRUE')

    def test_report_not_upgraded_and_open_not_executed(self):
        c,r,x=fixture();x['analyses']['R1.P1']['judgments'][0]['basis_mode']='REPORT_STATEMENT_ONLY'
        a=process(c,r,x);self.assertEqual(a['conditional_audit']['premise_judgments'][0]['conditional_state'],'UNKNOWN')
        r[0]['operator']='OPEN_TEXT';a=process(c,r,x);self.assertTrue(a['conditional_audit']['conditional_rules'][0]['not_executed'])

    def test_type_word_not_variable_and_error_saved(self):
        c,r,x=fixture();r[0]['slot_variables']['R1.P1']['tenant']='PERSON';a=process(c,r,x)
        self.assertEqual(a['contract_status'],'PROCESSING_ERROR');self.assertIsNone(a['formal_answer'])

    def test_lossless_pool_and_invalid_alias_refused(self):
        x={'a':'Long unchanged string. '*40,'b':['Long unchanged string. '*40],'opposition':'Keep me.'}
        p=pack(x);self.assertEqual(unpack(p),x);self.assertEqual(len(p['exact_text_pool']),1)
        p['material']['a']={'$exact_text':'TXT:999'}
        with self.assertRaises(ValueError):unpack(p)

    def test_actual_all_final_methods_and_prediction_provenance(self):
        c,r,x=fixture();a=process(c,r,x)
        prediction={'rows':[{'key':'K001','probabilities':[1.,0.,0.]}],
            'manifest':{'version':pipe.VERSION,'input_sha256':digest(a['learner_inputs']),'class_order':list(pipe.LABELS)}}
        for method in 'ABCDEFG':
            pp={'case_id':c['case_id'],'prior_answer':final_answer()} if method=='B' else prediction if method in 'EFG' else None
            with tempfile.TemporaryDirectory() as d:
                result=entry.final_run(c,r,a,method,part(c,r),d,lambda t:(json.dumps(final_answer()),{'run_status':'OK','mock':True}),pp,tokenizer=Tokenizer(),config=CFG)
                self.assertEqual(result['run_status'],'OK',method);self.assertIsNotNone(result['answer'])
                self.assertTrue(json.loads((Path(d)/'task.json').read_text())['presentation_audit']['exact_roundtrip'])
        prediction['manifest']['version']='V19_7'
        with self.assertRaises(ValueError):delivery.task(c,r,a,'E',part(c,r),prediction)

    def test_failure_receipt_and_no_resend(self):
        c,r,x=fixture();a=process(c,r,x);calls=[]
        def broken(t):calls.append(1);raise RuntimeError('Synthetic runner failure')
        with tempfile.TemporaryDirectory() as d:
            result=entry.final_run(c,r,a,'A',part(c,r),d,broken,tokenizer=Tokenizer(),config=CFG)
            self.assertIsNone(result['answer']);self.assertEqual(state(d),'ACTUAL_TECHNICAL_FAILURE')
            self.assertEqual(json.loads((Path(d)/'run.json').read_text())['phase'],'RUNNER')
            entry.final_run(c,r,a,'A',part(c,r),d,broken,tokenizer=Tokenizer(),config=CFG)
            self.assertEqual(len(calls),1)

    def test_preparation_and_capacity_fail_before_dispatch(self):
        c,r,x=fixture();a=process(c,r,x)
        for method,cfg in [('B',CFG),('A',{**CFG,'context_budget':1})]:
            with tempfile.TemporaryDirectory() as d:
                result=entry.final_run(c,r,a,method,part(c,r),d,lambda t:self.fail('No runner dispatch'),tokenizer=Tokenizer(),config=cfg)
                self.assertIsNone(result['answer']);self.assertTrue((Path(d)/'run.json').exists())
                self.assertFalse((Path(d)/'start.json').exists())

    def test_acceptance_error_keeps_actual_raw_and_receipt(self):
        c,r,x=fixture();a=process(c,r,x)
        with tempfile.TemporaryDirectory() as d:
            with patch.object(pipe,'accept_final',side_effect=[RuntimeError('Synthetic acceptance error'),{'answer':None,'technical_status':'TECHNICAL_FAILURE'}]):
                result=entry.final_run(c,r,a,'A',part(c,r),d,lambda t:('Actual mock text',{'run_status':'OK','observed_cost':None}),tokenizer=Tokenizer(),config=CFG)
            self.assertIsNone(result['answer']);self.assertEqual((Path(d)/'raw-response.txt').read_text(),'Actual mock text')
            self.assertEqual(json.loads((Path(d)/'runner-receipt.json').read_text())['run_status'],'OK')
            self.assertEqual(json.loads((Path(d)/'run.json').read_text())['phase'],'ACCEPTANCE')

    def test_safe_pause_boundary_no_next_dispatch(self):
        calls=[]
        with tempfile.TemporaryDirectory() as d:
            def perform(slot,dest):
                calls.append(slot['dest']);entry.save(dest/'run.json',{'run_status':'OK'});entry.save(dest/'formal-answer.json',{'answer':None,'mock':True});entry.save(Path(d)/'PAUSE_REQUESTED.json',{'requested':True})
                return {'run_status':'OK'}
            out=entry.saved_batch(d,[{'dest':'one'},{'dest':'two'}],perform)
            self.assertEqual(out,'PAUSED');self.assertEqual(calls,['one'])

if __name__=='__main__':unittest.main()
