import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_contract_integrity_v19_6 import fixture as old_fixture
from scripts import proof_pipeline_contract_v19_7 as entry
from legal_bench.proof_carrying import local_pipeline_v19_7 as pipe, local_checker_v19_7 as check
from legal_bench.proof_carrying.rule_contracts_v19_7 import VERSION, attach, digest
from legal_bench.proof_carrying.schema_contract_v19_6 import validate


def fixture():
    c,r,x = old_fixture(); r=copy.deepcopy(r)
    contract={'version':VERSION,'rules':{}}
    for rule in r:
        contract['rules'][rule['id']]={'original_rule_sha256':digest(rule),'slot_variables':{},'premises':{}}
        rc=contract['rules'][rule['id']]
        for p in rule['premises']:
            rc['slot_variables'][p['id']]={k:rule['id']+'::'+k for k in p['variables']}
            rc['premises'][p['id']]={'fixed_proposition':p['text'],'role_types':{k:'PARTY' for k in p['variables']},
                'required_roles':list(p['variables']),'optional_roles':[],'target_kind':'CASE_FACT',
                'components':[{'id':p['id']+'.K1','text':p['text']}], 'whole_basis_statuses':p.get('allowed_statuses',[])}
    r=attach(r,contract)
    for pid,u in x['analyses'].items():
        for ob in u['objects']: ob['type']='PERSON'
        for j in u['judgments']:
            j['basis_mode']='ASSESS_FIXED_PROPOSITION'
            for comp in j['components']:comp.pop('description');comp['component_id']=pid+'.K1'
    return c,r,x


def process(c,r,x):
    part={'id':'P01','rule_ids':[a['id'] for a in r],'source_ids':[s['id'] for s in c['segments']]}
    return entry.process_saved(c,r,part,json.dumps(x),pipe.schema(r,c),pipe.VERSION,'OK')


class PipelineContract(unittest.TestCase):
    def test_actual_saved_entry_and_all_three_checks(self):
        c,r,x=fixture();a=process(c,r,x)
        self.assertEqual(a['contract_status'],'CONTRACT_VALID')
        for name in ('independent_import','independent_merge','independent_check'):self.assertEqual(a[name]['status'],'OK')
        self.assertEqual(a['conditional_audit']['premise_judgments'][0]['conditional_state'],'TRUE')
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);entry.save(d/'run.json',{'run_status':'OK'});entry.text(d/'raw-response.txt',json.dumps(x));entry.save(d/'schema.json',pipe.schema(r,c))
            part={'id':'P01','rule_ids':[r[0]['id']],'source_ids':[s['id'] for s in c['segments']]}
            self.assertEqual(entry.accept_saved_output(c,r,part,d)['contract_status'],'CONTRACT_VALID')
            self.assertEqual(entry.read(d/'formal-answer.json')['answer'],x)

    def conversion_fault(self,kind):
        c,r,x=fixture()
        if kind=='limit':
            x['analyses']['R1.P1']['judgments'][0]['necessary_limits']=[{'kind':'BLOCK_SCOPE','component':'WHOLE_JUDGMENT','reason':'Missing prerequisite','refs':['SRC:1']}]
        original=pipe.convert
        def corrupt(*args):
            value,ledger=original(*args)
            if kind=='limit': value['analyses'][0]['judgments'][0]['necessary_limits'][0]['kind']='NOTE'
            else:value['analyses'][0]['uses'][0]['witnesses'][0]['quote']=value['analyses'][0]['uses'][0]['witnesses'][0]['quote'][:8]
            return value,ledger
        with patch.object(pipe,'convert',corrupt):a=process(c,r,x)
        self.assertEqual(a['contract_status'],'IMPORT_REJECTED');self.assertIsNone(a['formal_answer'])

    def test_limit_downcast_is_rejected_through_entry(self):self.conversion_fault('limit')
    def test_witness_shortening_is_rejected_through_entry(self):self.conversion_fault('witness')

    def test_merge_deletion_rejected_through_entry(self):
        c,r,x=fixture();original=pipe.merge_parts
        def corrupt(*args):
            p,ledger=original(*args);p['records'].pop();return p,ledger
        with patch.object(pipe,'merge_parts',corrupt):a=process(c,r,x)
        self.assertEqual(a['contract_status'],'MERGE_REJECTED');self.assertIsNone(a['formal_answer'])

    def test_all_traces_deleted_or_duplicate_rejected_through_entry(self):
        c,r,x=fixture();original=pipe.apply_connection_decisions
        for operation in ('delete','duplicate','alter'):
            def corrupt(*args):
                a=original(*args)
                if operation=='delete':a['conditional_rules']=[]
                elif operation=='duplicate':a['conditional_rules']+=copy.deepcopy(a['conditional_rules'])
                else:a['conditional_rules'][0]['not_executed']=True
                return a
            with patch.object(pipe,'apply_connection_decisions',corrupt):a=process(c,r,x)
            self.assertEqual(a['contract_status'],'CHECK_REJECTED',operation)

    def test_component_and_basis_correspondence(self):
        c,r,x=fixture();x['analyses']['R1.P1']['judgments'][0]['basis_mode']='PARTIAL_FACT_ONLY'
        a=process(c,r,x);self.assertEqual(a['conditional_audit']['premise_judgments'][0]['conditional_state'],'UNKNOWN')
        x['analyses']['R1.P1']['judgments'][0]['components'][0]['component_id']='R2.P1.K1'
        with self.assertRaises(ValueError):validate(x,pipe.schema(r,c))

    def test_objection_report_not_legal_effect_and_opposition_retained(self):
        c,r,x=fixture();p=r[0]['premises'][0];p['input_contract']['target_kind']='LEGAL_APPLICABILITY'
        p['input_contract']['whole_basis_statuses']=['COURT_FINDING']
        u=x['analyses'][p['id']];u['records'][0]['status']='PARTY_CLAIM';u['uses'][0]['direction']='OPPOSE'
        u['judgments'][0]['basis_mode']='REPORT_STATEMENT_ONLY'
        a=process(c,r,x);self.assertEqual(len(a['canonical_P']['records']),1)
        self.assertEqual(a['conditional_audit']['checks'][0]['disposition'],'CONDITIONALLY_AVAILABLE_USE')
        self.assertFalse(a['conditional_audit']['checks'][0]['full_basis_eligible'])
        self.assertEqual(a['conditional_audit']['premise_judgments'][0]['conditional_state'],'UNKNOWN')
        self.assertEqual(len(a['conditional_audit']['raw_opposition_retained']),1)

    def test_dynamic_bad_reference_local_independent_alternative_preserved(self):
        c,r,x=fixture();u=x['analyses']['R1.P1'];u['uses'].append(copy.deepcopy(u['uses'][0]));u['uses'][0]['records']=['EV:999']
        j=u['judgments'][0];j['uses']=['USE:1','USE:2'];j['components'][0]['alternatives']=[['USE:1'],['USE:2']]
        a=process(c,r,x);self.assertEqual(a['contract_status'],'CONTRACT_VALID')
        self.assertEqual(a['conditional_audit']['checks'][0]['disposition'],'STRUCTURAL_INVALID')
        self.assertEqual(a['conditional_audit']['checks'][1]['disposition'],'CONDITIONALLY_AVAILABLE_USE')
        self.assertEqual(a['conditional_audit']['premise_judgments'][0]['conditional_state'],'TRUE')
        self.assertEqual(len(a['canonical_P']['records']),1)

    def test_type_conflict_rejected_unknown_retained(self):
        c,r,x=fixture();x['analyses']['R1.P1']['objects'][0]['type']='PROPERTY'
        a=process(c,r,x);self.assertEqual(a['conditional_audit']['checks'][0]['disposition'],'STRUCTURAL_INVALID')
        x['analyses']['R1.P1']['objects'][0]['type']='UNMAPPED';a=process(c,r,x)
        self.assertEqual(a['conditional_audit']['checks'][0]['disposition'],'CONDITIONALLY_AVAILABLE_USE')
        self.assertEqual(a['conditional_audit']['checks'][0]['type_coverage'],'PENDING')

    def test_shared_variables_join_only_with_explicit_identity(self):
        c,r,x=fixture();p=copy.deepcopy(r[0]['premises'][0]);p['id']='R1.P2'
        p['input_contract']['components'][0]['id']='R1.P2.K1';r[0]['premises'].append(p)
        r[0]['slot_variables']['R1.P2']={'tenant':'R1::tenant'}
        x['analyses']['R1.P2']=copy.deepcopy(x['analyses']['R1.P1'])
        x['analyses']['R1.P2']['judgments'][0]['components'][0]['component_id']='R1.P2.K1'
        a=process(c,r,x)
        self.assertEqual(a['conditional_audit']['rule_coverage'][0]['incompatible_routes'],1)
        self.assertEqual(a['conditional_audit']['conditional_rules'],[])
        x['object_links']=[{'left_premise':'R1.P1','left_object':'OBJ:1','right_premise':'R1.P2','right_object':'OBJ:1','refs':['SRC:3'],'identity_basis':'Explicit same named tenant in the same source assertion.'}]
        a=process(c,r,x);self.assertEqual(a['conditional_audit']['conditional_rules'][0]['conditional_result'],'TRUE')
        self.assertEqual(a['independent_check']['status'],'OK')

    def test_distinct_declared_variables_not_forced_equal(self):
        c,r,x=fixture();p=copy.deepcopy(r[0]['premises'][0]);p['id']='R1.P2';p['input_contract']['components'][0]['id']='R1.P2.K1'
        r[0]['premises'].append(p);r[0]['slot_variables']['R1.P2']={'tenant':'R1::different_actor'}
        x['analyses']['R1.P2']=copy.deepcopy(x['analyses']['R1.P1']);x['analyses']['R1.P2']['judgments'][0]['components'][0]['component_id']='R1.P2.K1'
        a=process(c,r,x);self.assertEqual(len(a['conditional_audit']['conditional_rules']),1)
        self.assertEqual(a['independent_check']['status'],'OK')

    def test_open_text_remains_unexecuted_and_prediction_not_truth(self):
        c,r,x=fixture();r[0]['operator']='OPEN_TEXT';a=process(c,r,x)
        self.assertTrue(a['conditional_audit']['conditional_rules'][0]['not_executed'])
        self.assertEqual(a['conditional_audit']['conditional_rules'][0]['conditional_result'],'UNKNOWN')
        decisions={'K001':'UNSUPPORTED'};audit=pipe.apply_connection_decisions(c,r,a['canonical_P'],decisions)
        self.assertEqual(audit['premise_judgments'][0]['conditional_state'],'UNKNOWN')
        self.assertEqual(check.check(c,r,a['canonical_P'],decisions,audit)['status'],'OK')

    def test_full_final_actual_entry_A_through_G_and_save(self):
        c,r,x=fixture();a=process(c,r,x)
        pred={'rows':[{'key':'K001','probabilities':[1.0,0.0,0.0]}],
              'manifest':{'version':pipe.VERSION,'input_sha256':digest(a['learner_inputs']),'class_order':['SUPPORTED','UNSUPPORTED','UNRESOLVED']}}
        final={'request_id':'Q1','conclusion':'Conditional limited finding only.','grounds':[{'point':'Attributed fact.','statement_status_and_stage':'Trial finding.','case_refs':['SYN:L1'],'rule_refs':['R1'],'explanation':'Given premise, not independently proved semantics.'}], 'counterarguments':[], 'gaps':[], 'assumptions':['Unapproved semantic premises.'],'connection_handling':[]}
        with tempfile.TemporaryDirectory() as d:
            for method in 'ABCDEFG':
                task=pipe.final_task(c,r,a,method,{'prior_answer':final} if method=='B' else pred if method in 'EFG' else None)
                self.assertEqual(task['version'],pipe.VERSION)
                self.assertIn(c['segments'][0]['text'],task['prompt'])
                value=entry.final_run(c,r,a,method,Path(d)/method,lambda t:(json.dumps(final),{'run_status':'OK','execution':'MOCK_NOT_MODEL'}),{'prior_answer':final} if method=='B' else pred if method in 'EFG' else None)
                self.assertIsNotNone(value['answer']);self.assertFalse(value['legal_approval'])
            pred['manifest']['version']='V19_4'
            with self.assertRaises(ValueError):pipe.final_task(c,r,a,'G',pred)

    def test_failed_empty_final_and_uncertain_submission_are_not_success(self):
        c,r,x=fixture();a=process(c,r,x);task=pipe.final_task(c,r,a,'A')
        self.assertIsNone(pipe.accept_final(task,'{}','OK')['answer'])
        self.assertIsNone(pipe.accept_final(task,'','TIMEOUT')['answer'])
        with tempfile.TemporaryDirectory() as d:
            entry.save(Path(d)/'start.json',{'unknown':True})
            with self.assertRaises(ValueError):entry.final_run(c,r,a,'A',d,lambda t:None)


if __name__=='__main__': unittest.main()
