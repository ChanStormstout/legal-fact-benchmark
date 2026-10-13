"""F01-F10 regression tests. Neural transport is replaced, never invoked."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.test_source_verification_v20 import setup
from tests.test_pipeline_diagnostic_v19_8 import final_answer
from scripts import proof_source_verification_v20_2 as entry
from legal_bench.proof_carrying import source_verification_v20_2 as core
from legal_bench.proof_carrying.source_verification_check_v20_2 import check
from legal_bench.proof_carrying.artifact_state_v20_2 import (composition,execution_context,freeze_files,verify_files,digest)
from legal_bench.proof_carrying.local_evaluation_v20_2 import local_metrics
from legal_bench.proof_carrying.local_runtime_v20_1 import SETTINGS
from legal_bench.proof_carrying.scoring_v20_2 import validate_score,local_answer


def write(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value))


def wrappers():
    c,r,p,q=setup();c.update(case_id='SYN',split='DEV',dispute_id='SYN')
    def wrap(answer,role):
        return {'answer':answer,'status':'ALL_PARTS_READABLE','snapshot_sha256':digest(answer),
                'parts':[{'part':role+'01','premise_ids':[p['id'] for z in r for p in z['premises']],
                          'readable':True,'run_status':'OK'}]}
    return c,r,p,q,wrap(p,'P'),wrap(q,'Q')


class Application(unittest.TestCase):
    def test_merged_invalid_dependency_is_local_and_checked(self):
        for ref in ('EV:999','INVALID_LOCAL:EV:999'):
            c,r,p,q=setup();before=copy.deepcopy(q)
            p['analyses']['R1.P1']['uses'][0]['records']=[ref]
            original=copy.deepcopy(p)
            labels={d['id']:'SUPPORTED' for d in core.candidates(c,r,p,q)['candidates']}
            result=core.apply(c,r,p,q,labels)
            self.assertEqual(result['applied_proposals']['P']['analyses']['R1.P1']['uses'][0]['self_assessment'],'UNRESOLVED')
            self.assertEqual(result['applied_proposals']['Q']['analyses']['R1.P1']['uses'][0]['self_assessment'],'SUPPORTED')
            self.assertEqual(check(p,q,result,r)['status'],'OK')
            self.assertEqual(p,original);self.assertEqual(q,before)
            result['applied_proposals']['P']['analyses']['R1.P1']['uses'][0]['self_assessment']='SUPPORTED'
            self.assertEqual(check(p,q,result,r)['status'],'REJECTED')

    def test_counterevidence_supports_rejection_but_not_positive_support(self):
        c,r,p,q=setup();q['verdicts'][0].update(label='UNSUPPORTED',refs=[],counter_refs=['SRC:1'])
        pool=core.candidates(c,r,p,q);d=pool['candidates'][0]
        self.assertEqual(d['proposed_label'],'UNSUPPORTED');self.assertEqual(d['verification_state'],'REVIEWED')
        q['verdicts'][0]['label']='SUPPORTED';pool=core.candidates(c,r,p,q);d=pool['candidates'][0]
        self.assertIsNone(d['proposed_label']);self.assertEqual(d['verification_state'],'QUARANTINED')
        self.assertEqual(d['verification_refs'],['SRC:1'])
        self.assertIn('SUPPORT_WITHOUT_SUPPORTING_SOURCE',d['quarantine_reasons'])

    def test_not_checked_and_explicit_unresolved_are_separate(self):
        c,r,p,q=setup();q['verdicts']=[]
        pool=core.candidates(c,r,p,q)
        self.assertTrue(all(d['proposed_label'] is None for d in pool['candidates']))
        self.assertEqual(pool['verification_coverage']['reviewed'],0)
        first=pool['candidates'][0]['id'];q['verdicts']=[{'declaration':first,'label':'UNRESOLVED','refs':[],'counter_refs':[],'reason':'Synthetic insufficient source.'}]
        pool=core.candidates(c,r,p,q)
        self.assertEqual(pool['verification_coverage']['reviewed'],1)
        self.assertEqual(pool['verification_coverage']['explicit_unresolved'],1)
        result=core.apply(c,r,p,q);self.assertEqual(check(p,q,result,r)['status'],'OK')
        result['pool']['verification_coverage']['reviewed']=999
        self.assertEqual(check(p,q,result,r)['status'],'REJECTED')

    def test_duplicate_verdict_does_not_vote_or_drop_sources(self):
        c,r,p,q=setup();q['verdicts'].append(copy.deepcopy(q['verdicts'][0]))
        pool=core.candidates(c,r,p,q);d=pool['candidates'][0]
        self.assertIsNone(d['proposed_label']);self.assertEqual(d['verification_refs'],['SRC:1'])
        self.assertEqual(d['verification_state'],'QUARANTINED')

    def test_execution_failures_reach_final_view_but_not_classifier_features(self):
        c,r,p,q,pw,qw=wrappers();pw['parts'][0].update(readable=False,run_status='OUTPUT_TRUNCATED')
        qw['parts'][0].update(readable=False,run_status='INPUT_TOO_LONG')
        context=execution_context(pw,qw)
        pool=core.candidates(c,r,p,q,context);data=core.common_inputs(c,r,pool)
        self.assertNotIn('verification_state',json.dumps(data['graph']))
        self.assertNotIn('verifier_reason',json.dumps(data['graph']))
        task=core.final_task(c,r,'D',p,q,execution=context)
        self.assertIn('OUTPUT_TRUNCATED',task['prompt']);self.assertIn('INPUT_TOO_LONG',task['prompt'])
        self.assertEqual(check(p,q,task['trace'],r,context)['status'],'OK')
        self.assertEqual(check(p,q,task['trace'],r,{})['status'],'REJECTED')

    def test_learners_cannot_use_null_or_missing_predictions(self):
        c,r,p,q=setup();labels={d['id']:'SUPPORTED' for d in core.candidates(c,r,p,q)['candidates']}
        labels[next(iter(labels))]=None
        with self.assertRaises(ValueError):core.apply(c,r,p,q,labels)
        labels.pop(next(iter(labels)))
        with self.assertRaises(ValueError):core.apply(c,r,p,q,labels)


class Snapshots(unittest.TestCase):
    def test_partial_snapshot_refreshes_without_overwriting_history(self):
        c,r,p,q,pw,qw=wrappers();f={'case':c,'rules':r}
        slots=[{'case_id':'SYN','role':'Q','part':{'id':name,'rule_ids':['R1']},'dest':'local/SYN/'+name} for name in ('Q01','Q02')]
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);write(out/'local/SYN/Q01/run.json',{'run_status':'OK'});write(out/'local/SYN/Q01/formal-answer.json',{'answer':q})
            first=composition(out,out,'SYN','Q',slots,f,entry.merge_raw)
            write(out/'local/SYN/Q02/run.json',{'run_status':'OK'});write(out/'local/SYN/Q02/formal-answer.json',{'answer':q})
            second=composition(out,out,'SYN','Q',slots,f,entry.merge_raw)
            self.assertEqual(first['status'],'PARTIAL');self.assertEqual(second['status'],'ALL_PARTS_READABLE')
            self.assertNotEqual(first['snapshot_sha256'],second['snapshot_sha256'])
            self.assertEqual(len(list((out/'assembled/SYN/Q').glob('*.json'))),2)
            self.assertEqual(composition(out,out,'SYN','Q',slots,f,entry.merge_raw),second)
            self.assertEqual(len(second['answer']['supplement']['analyses']['R1.P1']['records']),2)

    def test_global_assembly_requires_terminal_q_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(entry,'OUT',Path(tmp)),patch.object(entry,'frozen',return_value={'slots':[{'role':'Q','dest':'local/SYN/Q01'}]}):
            with self.assertRaisesRegex(ValueError,'STAGE_DEPENDENCY_NOT_TERMINAL'):entry.assemble_inputs()
            self.assertFalse((Path(tmp)/'inputs').exists())

    def test_nested_function_import_and_config_are_frozen(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'pkg').mkdir();(root/'pkg/__init__.py').write_text('')
            (root/'main.py').write_text('def child():\n from pkg import hidden\n return hidden.value\n')
            (root/'pkg/hidden.py').write_text('value=1\n');(root/'encoder.json').write_text('{}')
            manifest=freeze_files(root,root/'out',['main.py'],[],['encoder.json'])
            self.assertIn('pkg/hidden.py',manifest['code_hashes']);self.assertTrue(verify_files(root,manifest))
            (root/'pkg/hidden.py').write_text('value=2\n')
            with self.assertRaisesRegex(ValueError,'FROZEN_DEPENDENCY_CHANGED'):verify_files(root,manifest)


class Metrics(unittest.TestCase):
    def setUp(self):
        self.rows=[{'key':'a','label':'SUPPORTED','dispute_id':'d1','request_id':'Q1'},
                   {'key':'b','label':'UNSUPPORTED','dispute_id':'d2','request_id':'Q1'}]

    def test_missing_duplicate_and_empty_predictions(self):
        result=local_metrics([{'key':'a','label':'SUPPORTED'}],self.rows)
        self.assertEqual(result['missing_predictions'],['b']);self.assertIsNone(result['macro_f1_all_three'])
        with self.assertRaisesRegex(ValueError,'DUPLICATE_PREDICTION_KEY'):local_metrics([{'key':'a','label':'SUPPORTED'}]*2,self.rows)
        result=local_metrics([],self.rows);self.assertEqual(result['scored_connections'],0);self.assertIsNone(result['macro_f1_all_three'])
        self.assertIsNone(local_metrics([],[])['macro_f1_all_three'])

    def test_probability_validation_and_complete_positive(self):
        for values in ([1,0],[float('nan'),0,0],[2,0,0],[.1,.1,.1]):
            with self.assertRaisesRegex(ValueError,'INVALID_PROBABILITIES'):local_metrics([{'key':'a','probabilities':values}],self.rows)
        result=local_metrics([{'key':'a','probabilities':[1,0,0]},{'key':'b','probabilities':[0,1,0]}],self.rows)
        self.assertEqual(result['status'],'COMPLETE');self.assertTrue(result['comparison_eligible'])
        self.assertEqual(result['scored_connections'],2)


class Dispatcher(unittest.TestCase):
    def test_pause_protects_every_neural_entry_without_actor_construction(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);write(out/'PAUSE_REQUESTED.json',{})
            with patch.object(entry,'OUT',out),patch.object(entry.subprocess,'run',side_effect=AssertionError('No dispatch')),patch.object(entry,'frozen',side_effect=AssertionError('No execution setup')):
                for stage in ('P','Q','final'):self.assertEqual(entry.run_generation(stage),'PAUSED')
                self.assertEqual(entry.fit(),'PAUSED');self.assertEqual(entry.fit_one('Flat',10),'PAUSED');self.assertEqual(entry.encode(),'PAUSED')

    def test_p_stop_survives_reentry(self):
        slots=[{'case_id':'SYN','role':'P','dest':'local/SYN/'+p,'part':{'id':p}} for p in ('P01','P02','P03')]
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            for slot in slots[:2]:write(out/slot['dest']/'run.json',{'run_status':'OUTPUT_TRUNCATED'})
            with patch.object(entry,'OUT',out),patch.object(entry,'frozen',return_value={'slots':slots}):
                self.assertEqual(entry.run_generation('P'),'STOPPED_BY_FROZEN_RULE')
            self.assertFalse((out/'local/SYN/P03').exists())

    def test_actual_current_dispatch_all_final_methods_and_saved_failures(self):
        c,r,p,q,pw,qw=wrappers();f={'case':c,'rules':r};context=execution_context(pw,qw)
        pool=core.candidates(c,r,p,q,context);data=core.common_inputs(c,r,pool)
        slots=[{'case_id':'SYN','role':m,'dest':'local/SYN/'+m,'output_tokens':8192} for m in 'ABCDEFG']
        cfg={'slots':slots,'runtime':SETTINGS,'stage_seconds':{'final':50},'TRAIN':[],'DEV':['SYN']}
        class Transport:
            calls=[]
            def __init__(self,*args):pass
            def run(self,prompt,schema,dest,*args):
                self.calls.append(dest.name);answer=final_answer()
                write(dest/'start.json',{'mock':True});write(dest/'parsed.json',answer)
                dest.joinpath('raw-response.txt').write_text(json.dumps(answer));write(dest/'token-ids.json',[])
                write(dest/'run.json',{'run_status':'OK','elapsed_seconds':1});return {'run_status':'OK'}
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            for name in ('pairs','graphs','plans','inference-rows','encoding'):write(out/'encoding'/(name+'.json'),{})
            write(out/'encoding/material-manifest.json',{'cases':{'SYN':{'composition_sha256':digest(context),'common_input_sha256':data['input_sha256']}}})
            write(out/'supervision/fitting-rows.json',[]);(out/'encoding/vectors.npz').write_bytes(b'SYNTHETIC_NOT_EMBEDDINGS')
            with patch.object(entry,'OUT',out):
                inputs=entry.model_input_hashes()
                for kind in ('Flat','CrossEncoder','RGCN'):
                    pred=[{'key':'SYN::'+d['id'],'probabilities':[1,0,0]} for d in pool['candidates']]
                    dest=out/'training'/kind;write(dest/'all-candidate-predictions.json',pred)
                    write(dest/'input-manifest.json',{'version':core.VERSION,'model_input_hashes':inputs,'input_hash':entry.sha(out/'encoding/pairs.json'),'prediction_hash':entry.sha(dest/'all-candidate-predictions.json')})
                with patch.object(entry,'frozen',return_value=cfg),patch.object(entry,'fixture',return_value=f),patch.object(entry,'merged',side_effect=lambda cid,role:pw if role=='P' else qw),patch.object(entry,'tokenizer',return_value=None),patch.object(entry,'measured',return_value={'fits':True}),patch('legal_bench.proof_carrying.local_runtime_v20_1.Runner',Transport):
                    self.assertEqual(entry.run_generation('final'),'FINISHED')
                self.assertEqual(Transport.calls,list('ABCDEFG'))
                for method in 'ABCDEFG':self.assertIsNotNone(entry.read(out/'local/SYN'/method/'formal-answer.json')['answer'])


class Scoring(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.out=Path(self.tmp.name)
        self.c,self.r,self.p,self.q,self.pw,self.qw=wrappers();self.f={'case':self.c,'rules':self.r}
        self.cfg={'DEV':['SYN'],'training_dispatch_order':['Flat','RGCN','CrossEncoder']}
        write(self.out/'private/references/SYN/checklist.json',{'key_items':[{'id':'K1'}]})
        for method in 'ABCDEFG':
            write(self.out/'local/SYN'/method/'run.json',{'run_status':'OK'})
            write(self.out/'local/SYN'/method/'formal-answer.json',{'answer':final_answer(),'status':'OK'})
        with patch.object(entry,'OUT',self.out),patch.object(entry,'frozen',return_value=self.cfg),patch.object(entry,'fixture',return_value=self.f):entry.score_tasks()

    def reply(self,name='score-1'):
        task=self.out/'web/tasks/SYN'/name
        manifest=entry.read(task.with_suffix('.manifest.json'))
        answers=[]
        for aid in manifest['expected_answer_ids']:
            answers.append({'answer_id':aid,'technical_status':'OK','answer':None,'key_items':[{'id':'K1','status':'CORRECTLY_HANDLED'}],
                            'substantive_judgements':[{'id':'C1','status':'SUPPORTED','major':False}],'overall':'COMPLETE_AND_SOURCED'})
        path=self.out/'web/replies/SYN'/(name+'.json');write(path,{'answers':answers})
        write(path.with_name(name+'-receipt.json'),{'thinking':'Extra High','model_visible':'SYNTHETIC_TEST_ONLY','task_sha256':entry.sha(task.with_suffix('.txt')),
              'manifest_sha256':entry.sha(task.with_suffix('.manifest.json')),'reply_sha256':entry.sha(path)})
        return path

    def validate(self,name='score-1'):
        mapping=entry.read(self.out/'private/blinding/SYN.json')
        return validate_score(self.out,'SYN',name,self.f,mapping,self.out/'private/references/SYN/checklist.json')

    def test_valid_complete_score_roundtrip(self):
        self.reply();self.reply('score-2');result,ids=self.validate();self.assertEqual(len(result),4)
        with patch.object(entry,'OUT',self.out),patch.object(entry,'frozen',return_value=self.cfg),patch.object(entry,'fixture',return_value=self.f):
            summary=entry.evaluate()
        self.assertEqual(summary['A']['completion_rate'],1);self.assertEqual(summary['A']['key_coverage'],1)

    def test_receipt_task_answer_and_model_mismatches_are_rejected(self):
        path=self.reply();receipt=path.with_name('score-1-receipt.json');original=entry.read(receipt)
        for key,value in [('thinking','High'),('model_visible',''),('task_sha256','bad'),('manifest_sha256','bad'),('reply_sha256','bad')]:
            write(receipt,{**original,key:value})
            with self.assertRaisesRegex(ValueError,'SCORE_RECEIPT_MISMATCH'):self.validate()
        write(receipt,original)
        mapping=entry.read(self.out/'private/blinding/SYN.json')
        affected=mapping[entry.read(self.out/'web/tasks/SYN/score-1.manifest.json')['expected_answer_ids'][0]]
        write(self.out/'local/SYN'/affected/'formal-answer.json',{'answer':None,'status':'OUTPUT_TRUNCATED'})
        with self.assertRaisesRegex(ValueError,'SCORE_INPUT_CHANGED'):self.validate()

    def test_score_ids_are_exact_and_cannot_be_moved_between_batches(self):
        path=self.reply();body=entry.read(path);body['answers']=body['answers'][:-1];write(path,body)
        receipt=path.with_name('score-1-receipt.json');record=entry.read(receipt);record['reply_sha256']=entry.sha(path);write(receipt,record)
        with self.assertRaisesRegex(ValueError,'MISSING_OR_EXTRA'):self.validate()

    def test_local_failure_cannot_become_completed_through_score(self):
        write(self.out/'local/SYN/A/run.json',{'run_status':'OUTPUT_TRUNCATED'})
        write(self.out/'local/SYN/A/formal-answer.json',{'answer':None,'status':'OUTPUT_TRUNCATED'})
        # Build a fresh task containing the real failure, then forge only review status.
        for path in (self.out/'web/tasks/SYN').iterdir():path.unlink()
        with patch.object(entry,'OUT',self.out),patch.object(entry,'frozen',return_value=self.cfg),patch.object(entry,'fixture',return_value=self.f):entry.score_tasks()
        self.reply();self.reply('score-2')
        with patch.object(entry,'OUT',self.out),patch.object(entry,'frozen',return_value=self.cfg),patch.object(entry,'fixture',return_value=self.f):summary=entry.evaluate()
        self.assertEqual(summary['A']['completed_tasks'],0);self.assertIsNone(summary['A']['key_coverage'])
        current=entry.read(self.out/'checkpoints/final-evaluation/latest.json')
        final=entry.read(self.out/'checkpoints/final-evaluation'/current['path'])
        self.assertTrue(final['rejected_scores']);self.assertEqual(final['failures'][0]['reason'],'OUTPUT_TRUNCATED')

