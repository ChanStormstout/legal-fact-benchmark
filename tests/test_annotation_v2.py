import copy
import json
import unittest
import tempfile
from pathlib import Path
from legal_bench.annotation_v2 import VERSION, segment_source, check_segmentation, validate, execution_view, import_files
from legal_bench.core import digest

class AnnotationV2Tests(unittest.TestCase):
    def setUp(self):
        obj=json.loads(Path('outputs/benchmark-pilot-v02/protocol/schema-example.json').read_text())
        self.a=obj['annotation.json']; self.n=obj['review_notes.json']
        self.s={'case_id':'SYNTHETIC_EXAMPLE_ONLY','segments':[{'id':x['segment_id'],'text':x['text']} for x in obj['synthetic_source']]}
    def codes(self,a=None,n=None):
        return {x['code'] for x in validate(a or self.a,n or self.n,self.s)['errors']}
    def test_complete_example_and_quotes(self):
        self.assertTrue(validate(self.a,self.n,self.s)['valid'])
        self.a['assertions'][0]['evidence'][0]['quote']='Invented receipt'
        self.assertIn('unlocated_quote',self.codes())
    def test_exact_segmentation_roundtrip(self):
        parent={'case_id':'x','source_completeness':'VERIFIED_FULL','text_sha256':'h',
                'paragraphs':[{'id':'p1','page':1,'text':('Sentence. Odd OCR- artifact  \n'*100)+'END'}]}
        s=segment_source(parent,70)
        self.assertTrue(check_segmentation(s,parent)['valid'])
        self.assertGreater(len(s['segments']),10)
        s['segments'][0]['text']+='repaired';self.assertFalse(check_segmentation(s,parent)['valid'])
    def test_positive_name_single_polarity(self):
        self.a['predicate_definitions'][0]['id']='NO_COMPENSATION'
        self.a['assertions'][0]['predicate']='NO_COMPENSATION'
        self.assertIn('negative_or_invalid_predicate_name',self.codes())
    def test_reference_and_coverage_fail_closed(self):
        self.a['assertions'][0]['relevance'][0]['unit_id']='missing'
        self.assertIn('relevance_unit',self.codes())
        self.n['coverage'].pop();self.assertIn('coverage_not_exact',self.codes())
    def test_failure_of_proof_not_automatically_negated_or_executable(self):
        original=copy.deepcopy(self.a)
        r=execution_view(self.a,'u1',['a1'])
        self.assertEqual(r['events'],[])
        self.assertEqual(r['excluded'][0]['reason'],'NOT_ADOPTED_FACT_OR_ACT')
        self.assertEqual(self.a,original)
        self.assertEqual(self.a['assertions'][0]['polarity'],'POSITIVE')
    def test_historical_origin_relevance_does_not_require_same_stage(self):
        self.a['stages'].append({'id':'st0','label':'old trial','current':False,'evidence':self.a['stages'][0]['evidence']})
        a=self.a['assertions'][0];a['origin']['stage_id']='st0';a['deciding_court_treatment']['value']='ADOPTED'
        self.assertTrue(validate(self.a,self.n,self.s)['valid'])
        self.assertEqual(execution_view(self.a,'u1',[])['events'],[])
        event=execution_view(self.a,'u1',['a1'])['events'][0]
        self.assertEqual(event['origin']['stage_id'],'st0');self.assertEqual(event['unit_id'],'u1')
        a['scope']={'portion':'upstairs only'}
        self.assertEqual(execution_view(self.a,'u1',['a1'])['events'][0]['unresolved'][-1]['field'],'scope')
    def test_conflict_must_match_positive_proposition_roles_scope(self):
        x=self.a['assertions'][0];y=copy.deepcopy(x);y.update(id='a2',polarity='NEGATIVE')
        self.a['assertions'].append(y)
        rel={'id':'r1','type':'DIRECT_CONTRADICTION','from_id':'a1','to_id':'a2','same_scope_basis':'synthetic same event','evidence':x['evidence']}
        self.a['relations']=[rel];self.assertTrue(validate(self.a,self.n,self.s)['valid'])
        y['roles']={'receiver':'o1','property':'o3'};self.assertIn('conflict_not_same_proposition',self.codes())
        y['roles']=copy.deepcopy(x['roles']);y['scope']={'time':'earlier'};self.assertIn('conflict_scope_unestablished',self.codes())
    def test_headnote_only_rejected_and_treatment_needs_evidence(self):
        self.n['coverage'][0]['category']='HEADNOTE'
        self.assertIn('editorial_or_precedent_only_assertion',self.codes())
        self.n['coverage'][0]['category']='MIXED'
        self.a['assertions'][0]['deciding_court_treatment']={'value':'ADOPTED','evidence':[]}
        self.assertIn('missing_or_invalid_evidence',self.codes())

    def test_import_binds_actual_source_and_prompt_before_persisting(self):
        source=copy.deepcopy(self.s);source['text_sha256']=digest(source['segments'])
        task={'id':'t','case_id':source['case_id'],'source_hash':source['text_sha256'],
              'prompt':'complete context','prompt_sha256':digest(b'complete context')}
        meta={k:'observed' for k in ['conversation_url','model_display','effort_display','submitted_at','retrieved_at']}
        meta['prompt_sha256']=task['prompt_sha256']
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);ap=root/'a.json';np=root/'n.json'
            ap.write_text(json.dumps(self.a));np.write_text(json.dumps(self.n))
            for field,change,message in [('segments',[], 'Source content hash'),
                                         ('case_id','OTHER','Source case')]:
                bad=copy.deepcopy(source);bad[field]=change
                with self.assertRaisesRegex(ValueError,message):
                    import_files(task,bad,ap,np,meta,root/'rejected')
                self.assertFalse((root/'rejected').exists())
            badtask=dict(task,prompt='changed context')
            with self.assertRaisesRegex(ValueError,'Task prompt content hash'):
                import_files(badtask,source,ap,np,meta,root/'rejected')
            result=import_files(task,source,ap,np,meta,root/'accepted')
            self.assertEqual(result['state'],'STRUCTURALLY_VALID_SEMANTIC_REVIEW_PENDING')

    def test_jointly_disposed_current_proceedings_keep_one_primary_unit(self):
        second=copy.deepcopy(self.a['stages'][0]);second.update(id='st_joint',label='contempt petition jointly disposed')
        self.a['stages'].append(second)
        self.assertTrue(validate(self.a,self.n,self.s)['valid'])
        second_unit=copy.deepcopy(self.a['units'][0]);second_unit.update(id='u_joint',stage_id='st_joint',primary=False)
        self.a['units'].append(second_unit)
        self.assertTrue(validate(self.a,self.n,self.s)['valid'])
        second_unit['primary']=True
        self.assertIn('primary_count',self.codes())
        second_unit['primary']=False
        for s in self.a['stages']:s['current']=False
        self.assertIn('current_stage_count',self.codes())

if __name__=='__main__':unittest.main()
