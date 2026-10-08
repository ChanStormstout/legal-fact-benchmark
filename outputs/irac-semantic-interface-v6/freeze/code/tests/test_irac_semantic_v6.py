import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import irac_semantic_v6 as entry
from legal_bench.irac_application.semantic_v6 import process, catalogue, validate_final, legacy_projection
from legal_bench.irac_application.semantic_v6_tasks import prompt, schema


def fixture():
    m = {'case_id': 'test', 'sources': {'S1': {'text': 'Allegation.', 'document_id': 'test'},
                                      'S2': {'text': 'Finding on another account.', 'document_id': 'test'}}}
    law = [{'source_id': 'L1', 'text': 'Fictional rule.', 'document_id': 'law'}]
    def ref(key): return {'op': 'REF', 'id': key, 'source_refs': ['L1']}
    t = {'tests': [{'id': 'T', 'text': 'The required proposition.', 'branches': []}],
         'elements': [], 'claims': [{'id': 'C', 'expression': ref('T')}], 'coverage_limits': []}
    p = {'records': [{'text': 'An attributed claim.', 'statement_status': 'PARTY_CLAIM', 'refs': ['S1']},
                     {'text': 'Prior finding, target status contested.', 'statement_status': 'PRIOR_COURT_FINDING', 'refs': ['S2']}],
         'arrangements': [{'description': 'Persons X and Y; facility F; arrangement Z.', 'refs': ['S1']}],
         'conditions': [{'arrangement': 1, 'condition': 'T', 'assessment': 'UNRESOLVED',
                         'evidence': [{'record': 1, 'role': 'SUPPORT', 'connection': 'Relevant but not necessarily sufficient.'},
                                      {'record': 2, 'role': 'OPPOSE', 'connection': 'Contrary prior account.'}],
                         'law_refs': ['L1'], 'explanation': 'Weigh both records under the rule.', 'gaps': []}],
         'limitations': [], 'coverage_limits': []}
    return m, t, law, p


class FakeRunner:
    def __init__(self, value, status='OK'):
        self.value, self.status = value, status

    def run(self, text, sc, out, **kwargs):
        out = Path(out)
        entry.save(out / 'schema.json', sc)
        (out / 'prompt.txt').write_text(text)
        (out / 'raw-response.txt').write_text(json.dumps(self.value))
        entry.save(out / 'start.json', {'fake': True})
        meta = {'run_status': self.status, 'schema_mask_calls': 1, 'offline_replay': True, 'elapsed_seconds': 0}
        entry.save(out / 'run.json', meta)
        return meta


class SemanticV6Tests(unittest.TestCase):
    def check(self, p, m=None, t=None, law=None):
        base = fixture()
        # Exercise production completion/save/import, not an unused helper.
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);(out/'raw-response.txt').write_text(json.dumps(p))
            result=entry.finish_attempt({'run_status':'OK','offline_replay':True},out,'P',m or base[0],t or base[1],law or base[2])
            self.assertIsNotNone(result['prediction'])
            return entry.read(out/'import.json'),entry.read(out/'checks-full.json')

    def test_relevance_is_not_satisfaction_and_conflicts_not_votes(self):
        m,t,l,p=fixture()
        p['conditions'][0]['evidence']=p['conditions'][0]['evidence'][:1]
        imp,c=self.check(p)
        self.assertEqual(c['conditions'][0]['program_input_state']['status'],'UNRESOLVED')
        p['conditions'][0]['assessment']='REFUTED'
        _,c=self.check(p)
        self.assertEqual(c['conditions'][0]['program_input_state']['status'],'REFUTED')
        self.assertEqual(c['conditions'][0]['evidence_use_summary']['support'],['U1.1'])
        p['conditions'][0]['evidence'] += fixture()[3]['conditions'][0]['evidence'][1:]*3
        _,c=self.check(p)
        self.assertTrue(c['conditions'][0]['evidence_use_summary']['conflicting_directions'])
        self.assertEqual(c['conditions'][0]['program_input_state']['reason'],'EXPLICIT_MODEL_JUDGMENT_NOT_VERIFIED')

    def test_model_summary_without_evidence_not_computable_truth(self):
        p=fixture()[3];p['conditions'][0].update(assessment='SUPPORTED',evidence=[])
        _,c=self.check(p)
        self.assertEqual(c['conditions'][0]['model_assessment'],'SUPPORTED')
        self.assertEqual(c['conditions'][0]['program_input_state']['status'],'UNRESOLVED')

    def test_law_only_fact_use_isolated_record_retained(self):
        p=fixture()[3];p['records'][0]['refs']=['L1'];p['conditions'][0]['assessment']='SUPPORTED'
        imp,c=self.check(p)
        self.assertEqual(len(imp['records']),2)
        self.assertIn('LEGAL_SOURCE_CANNOT_PROVE_TARGET_CASE_FACT',c['evidence_use_checks'][0]['reasons'])
        self.assertEqual(c['evidence_use_checks'][1]['status'],'PROPOSED_CONNECTION')

    def test_source_roles_not_model_ids(self):
        m,t,l,p=fixture();m['sources']['S1']['document_id']='foreign'
        with self.assertRaisesRegex(ValueError,'DOCUMENT_ID_CONFLICT'):process(p,t,m,l)
        m=fixture()[0];l[0]['source_id']='S1'
        with self.assertRaisesRegex(ValueError,'COLLISION'):process(p,t,m,l)

    def test_shared_record_local_errors_preserve_other_uses(self):
        p=fixture()[3];p['arrangements'].append(copy.deepcopy(p['arrangements'][0]))
        p['conditions'].append(copy.deepcopy(p['conditions'][0]));p['conditions'][1]['arrangement']=2
        p['conditions'][0]['evidence'][0]['record']=12
        imp,c=self.check(p)
        self.assertEqual(len(imp['records']),2)
        self.assertEqual(c['evidence_use_checks'][0]['status'],'ISOLATED')
        self.assertEqual(c['evidence_use_checks'][2]['status'],'PROPOSED_CONNECTION')
        p['conditions'][0]['arrangement']=0
        _,c=self.check(p)
        self.assertEqual(c['evidence_use_checks'][2]['status'],'PROPOSED_CONNECTION')

    def test_restriction_matrix_and_nonpropagation(self):
        p=fixture()[3];p['conditions'][0]['assessment']='SUPPORTED'
        p['arrangements'].append(copy.deepcopy(p['arrangements'][0]))
        p['conditions'].append(copy.deepcopy(p['conditions'][0]));p['conditions'][1]['arrangement']=2
        limit={'arrangement':1,'condition':'T','records':[1],'effect':'EVIDENCE_USE_BLOCK','reason':'Only this use.','refs':['S1']}
        p['limitations']=[limit]
        _,c=self.check(p)
        self.assertEqual(c['evidence_use_checks'][0]['status'],'PENDING_LOCAL_RESTRICTION')
        self.assertEqual(c['evidence_use_checks'][1]['status'],'PROPOSED_CONNECTION')
        self.assertEqual(c['evidence_use_checks'][2]['status'],'PROPOSED_CONNECTION')
        limit.update(records=[],effect='CONDITION_PENDING')
        for refs in (['S1'],['INVALID']):
            limit['refs']=refs;_,c=self.check(p)
            self.assertEqual(c['conditions'][0]['program_input_state']['status'],'UNRESOLVED')
            self.assertEqual(c['conditions'][1]['program_input_state']['status'],'SUPPORTED')
        limit['arrangement']=0;_,c=self.check(p)
        self.assertEqual(c['restriction_coverage'][0]['reason'],'UNMAPPED_RESTRICTION_NO_GLOBAL_BLOCK')

    def test_boolean_branches_polarity_and_no_case_absence(self):
        m,t,l,p=fixture();refs=['L1']
        t['tests'][0].update(branches=[{'id':'T/X','text':'X.'},{'id':'T/Y','text':'Y.'}],
            branch_expression={'op':'OR','args':[{'op':'REF','id':'T/X','source_refs':refs},{'op':'REF','id':'T/Y','source_refs':refs}],'source_refs':refs})
        p['conditions'][0].update(condition='T/X',assessment='SUPPORTED')
        p['conditions'].append(copy.deepcopy(p['conditions'][0]));p['conditions'][1]['condition']='T/Y'
        p['limitations']=[{'arrangement':1,'condition':'T/X','records':[],'effect':'CONDITION_PENDING','reason':'X pending.','refs':['INVALID']}]
        _,c=self.check(p,t=t)
        self.assertEqual(c['combinations'][0]['tests']['T']['status'],'SUPPORTED')
        t['claims'][0]['expression']={'op':'NOT','arg':t['claims'][0]['expression'],'source_refs':refs}
        _,c=self.check(p,t=t)
        self.assertEqual(c['combinations'][0]['claims'][0]['result']['status'],'REFUTED')
        self.assertTrue(c['combinations'][0]['does_not_prove_other_arrangements_absent'])
        t['tests'][0]['branch_expression']['op']='AND';_,c=self.check(p,t=t)
        self.assertEqual(c['combinations'][0]['tests']['T']['status'],'UNRESOLVED')

    def test_catalogue_pair_roundtrip_and_replay(self):
        for cid in entry.CASES:
            m,t,l,sm=entry.inputs(cid);cat=catalogue(t)
            self.assertEqual(len(cat),len(set((a['test_id'],a['branch_id']) for a in cat.values())))
            old=entry.read('outputs/irac-contract-repair-v5/continuation-01/runs/'+cid+'/P/result.json')['prediction']
            imp,c=process(legacy_projection(old,t),t,m,l)
            self.assertEqual(len(imp['records']),len(old['evidence']))
            self.assertTrue(imp['usable'])

    def test_actual_entry_partial_and_B_only_raw_proposal(self):
        cid='112400';m,t,l,sm=entry.inputs(cid)
        p={'records':[{'text':'Fixture record.', 'statement_status':'UNKNOWN','refs':[next(iter(m['sources']))]}],
           'arrangements':[],'conditions':[],'limitations':[],'coverage_limits':[]}
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'P';text=prompt('proposal',m,t,l,sm);sc=schema('proposal',m,t,l)
            meta,result=entry.execute_slot(FakeRunner(p),out,cid,'P',text,sc,12)
            self.assertEqual(result['prediction'],p)
            self.assertEqual(len(entry.read(out/'evidence-records.json')),1)
            b,bs,inter=entry.final_task(cid,result['prediction'])
            actual=json.loads(b.split('INTERMEDIATE MATERIAL:\n\n')[1].split('\n\nCOMPLETE ALLOWED CASE MATERIAL:')[0])
            self.assertEqual(actual,{'proposal':p})
            self.assertTrue(entry.delivery(b,m,l,sm)['passed'])

    def test_missing_local_array_preserves_records_and_raw(self):
        p=fixture()[3];p.pop('conditions')
        imp,c=self.check(p)
        self.assertEqual(imp['raw_proposal'],p)
        self.assertEqual(len(imp['records']),2)
        self.assertEqual(c['conditions'],[])

    def test_batch_failure_blocks_dependencies_only(self):
        from scripts import irac_semantic_v6_run as batch
        calls=[]
        class BatchFake:
            versions={};loaded_seconds=0;model_config_hash='synthetic'
            def __init__(self,*a,**kw):pass
            def run(self,text,sc,out,**kw):
                cid,stage=out.parent.name,out.name;calls.append((cid,stage))
                val={'records':[],'arrangements':[],'conditions':[],'limitations':[],'coverage_limits':[]} if stage=='P' else {'answers':[]}
                status='OUTPUT_TRUNCATED' if cid=='112400' and stage=='P' else 'OK'
                return FakeRunner(val,status).run(text,sc,out,**kw)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            entry.save(root/'freeze/config.json',{'code_hashes':{},'material_hashes':{},'engineering_gate':{'E':'PASS'},'settings':{}})
            for cid in entry.CASES:
                m,t,l,sm=entry.inputs(cid)
                for st in ('A','P'):
                    d=root/'freeze/tasks'/cid/st;d.mkdir(parents=True)
                    stage='proposal' if st=='P' else 'final'
                    (d/'prompt.txt').write_text(prompt(stage,m,t,l,sm))
                    entry.save(d/'schema.json',schema(stage,m,t,l))
            with patch.object(batch,'R',root),patch('legal_bench.rules_verdict_v1.runtime_constraint_diag_v1.Runner',BatchFake):batch.run()
            self.assertEqual(calls,[('112400','A'),('112400','P'),('188721101','A'),('188721101','P'),('188721101','B')])
            self.assertEqual(entry.read(root/'runs/112400/B/result.json')['run_status'],'SKIPPED')
            self.assertEqual(entry.read(root/'runs/188721101/B/result.json')['run_status'],'FORMAT_ERROR')

    def test_actual_entry_final_empty_missing_duplicate_failed_null(self):
        cid='112400';m,t,l,sm=entry.inputs(cid)
        original=entry.read('outputs/irac-contract-repair-v5/continuation-01/runs/'+cid+'/A/result.json')['prediction']
        for value,ok in [(original,True),({'answers':[]},False),({'answers':original['answers']*2},False)]:
            with tempfile.TemporaryDirectory() as td:
                text,sc,_=entry.final_task(cid)
                _,res=entry.execute_slot(FakeRunner(value),td,cid,'A',text,sc,10)
                self.assertEqual(res['prediction'] is not None,ok)
                self.assertEqual(json.loads((Path(td)/'raw-response.txt').read_text()),value)
        value=copy.deepcopy(original);value['answers'][0]['conditions']=[]
        with self.assertRaises(ValueError):validate_final(value,schema('final',m,t,l),t)
        with tempfile.TemporaryDirectory() as td:
            text,sc,_=entry.final_task(cid)
            _,r=entry.execute_slot(FakeRunner(original,'OUTPUT_TRUNCATED'),td,cid,'A',text,sc,10)
            self.assertIsNone(r['prediction'])


if __name__=='__main__':unittest.main()
