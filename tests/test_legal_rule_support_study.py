import json
import tempfile
import unittest
from pathlib import Path

from legal_bench.rules_verdict_v1 import legal_rule_support_study as v


class StudyTests(unittest.TestCase):
    def unit(self, key, text='tenant consent assignment', dependencies=()):
        return dict(id=key, text=text, source={'document_id':'fictional','url':'https://example.invalid'},
                    version_status='FICTIONAL_ONLY', scope='fictional', date='2000-01-01',
                    status='PROVISIONAL', coverage_limit='Not complete law', dependencies=list(dependencies))

    def test_config_is_effective_and_actual_renderer_counts_metadata(self):
        units=[self.unit('A'),self.unit('B')]
        cfg=dict(v.PRIMARY_CONFIG, max_legal_characters=len(v.render(units[:1])))
        with tempfile.TemporaryDirectory() as tmp:
            result=v.retrieve_arms(units, {}, 'consent', tmp, cfg)
        self.assertEqual(len(result['selected']['A']['units']),1)
        self.assertLessEqual(result['selected']['A']['legal_characters'],cfg['max_legal_characters'])
        self.assertEqual(result['selected']['A']['legal_characters'],len(v.render(result['selected']['A']['units'])))
        for field in ['scope','date','status','version_status','coverage_limit']:
            self.assertIn(field,json.loads(v.render(units))[0])

    def test_atomic_dependency_missing_cycle_dedupe_and_mandatory_failure(self):
        units=[self.unit('A',dependencies=['B']),self.unit('B',dependencies=['A'])]
        result=v.select([{'id':'A'},{'id':'B'}],units,v.PRIMARY_CONFIG)
        self.assertEqual(result['selected_ids'],['A','B'])
        self.assertEqual(result['decisions'][1]['decision'],'ALREADY_DELIVERED')
        self.assertTrue(result['decisions'][0]['cycles'])
        self.assertEqual(v.select([{'id':'A'}],units[:1],v.PRIMARY_CONFIG)['decisions'][0]['decision'],'MISSING_REQUIRED_SOURCE')
        cfg=dict(v.PRIMARY_CONFIG,max_legal_characters=1)
        self.assertEqual(v.select([],units,cfg,mandatory=['A'])['run_status'],'BUDGET_ASSEMBLY_ERROR')
        self.assertEqual(v.select([{'id':'A'}],units,cfg)['selected_ids'],[])
        with self.assertRaises(ValueError):v.registry([units[0],units[0]])

    def test_reversible_whitespace_and_exact_slice(self):
        text='a \n\t b c'; loc=v.locate_quote(text,'a b')
        self.assertEqual(loc['status'],'WHITESPACE_ONLY')
        norm,_=v.normalize_whitespace(text[loc['raw_start']:loc['raw_end']])
        self.assertEqual(norm,'a b')
        self.assertEqual(v.locate_quote(text,'a d')['status'],'UNLOCATED')
        u=self.unit('A',text); s=v.exact_slice(u,2,7,'A2')
        self.assertEqual(s['text'],u['text'][2:7]);self.assertEqual(s['source']['parent_start'],2)

    def test_description_index_only_body_and_final_has_no_study_sidecar(self):
        u=self.unit('A'); descriptions={'G':[dict(legal_unit_id='A',description='consent',evidence='secrettrigger')],
                                      'L':[dict(legal_unit_id='A',description='consent',review='secrettrigger')]}
        with tempfile.TemporaryDirectory() as tmp:
            result=v.retrieve_arms([u],descriptions,'secrettrigger',tmp)
            self.assertEqual(result['route_traces']['G']['description'],[])
            self.assertEqual(result['route_traces']['L']['description'],[])
        source=dict(case_id='synthetic',segments=[dict(id='C',text='Allowed text.')],reference='SECRET_REFERENCE')
        prompt=v.prompt(source,[u],'Fictional question')
        self.assertNotIn('SECRET_REFERENCE',prompt);self.assertNotIn('secrettrigger',prompt)
        self.assertIn(v.legacy.FINAL,prompt)

    def test_order_identity_sharing_is_case_and_repeat_scoped(self):
        units=[self.unit('A'),self.unit('B')]
        a=v.select([{'id':'A'},{'id':'B'}],units,v.PRIMARY_CONFIG)
        b=v.select([{'id':'B'},{'id':'A'}],units,v.PRIMARY_CONFIG)
        self.assertEqual(v.render(a['units']),v.render(b['units']))
        key=v.shared_key('C',0,'same',{'mode':'High'})
        self.assertNotEqual(key,v.shared_key('C',1,'same',{'mode':'High'}))
        self.assertNotEqual(key,v.shared_key('Other',0,'same',{'mode':'High'}))

    def test_delivery_denominator_and_dispute_sensitivity(self):
        units=[self.unit('F'),self.unit('X','x'*21000)]
        refs=[dict(id='r1',unit_ids=['F'],role='CONTROLLING_CANDIDATE',status='VERIFIED_SOURCE_ANCHORED'),
              dict(id='r2',unit_ids=['X'],role='EXPLANATORY',status='VERIFIED_SOURCE_ANCHORED'),
              dict(id='r3',unit_ids=['X'],role='CONTRARY',status='DISPUTED')]
        result=v.delivery(refs,['F'],['F'],units)
        self.assertEqual(result['denominator'],1);self.assertEqual(result['rate'],0)
        self.assertFalse(result['rows'][1]['reachable']);self.assertEqual(len(result['symmetric_sensitivity']),2)
        self.assertIsNone(v.delivery(refs[:1],['F'],['F'],units)['rate'])


if __name__=='__main__':unittest.main()
