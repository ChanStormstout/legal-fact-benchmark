import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_reference_addresses_v19 import typed_fixture
from legal_bench.proof_carrying import local_pipeline_v19_compact as pipe
from legal_bench.proof_carrying.repetition_v19_compact import ExpansionGuard
from legal_bench.proof_carrying.string_guard_v19_compact import StringGuard
from legal_bench.rules_verdict_v1.repetition_v9 import RepetitionAbort
from scripts import proof_local_compact_v19 as entry

def fixture():
    c,r,x=typed_fixture()
    for unit in x['analyses']:
        for rec in unit['records']:rec['proposition']=rec.pop('text')
    return c,r,x

class CompactProposal(unittest.TestCase):
    def test_actual_entry_local_failure_and_restoration(self):
        c,r,x=fixture();unit=x['analyses'][0]
        unit['uses'].append(copy.deepcopy(unit['uses'][0]));unit['uses'][0]['records']=['EV:144']
        unit['judgments'][0]['uses']=['USE:1','USE:2'];unit['judgments'][0]['components'][0]['alternatives']=[['USE:1'],['USE:2']]
        pipe.validate(x,pipe.schema(r,c))
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);part=out/'local/SYN/P01'
            entry.save(part/'run.json',{'run_status':'OK'});entry.save(part/'parsed.json',x);entry.save(part/'production-version.json',{'version':pipe.VERSION})
            cfg={'local_generation_slots':[{'role':'P','case_id':'SYN','dest':'local/SYN/P01','part':{'id':'P01','source_ids':[s['id'] for s in c['segments']]}}]}
            with patch.object(entry,'OUT',out),patch.object(entry,'fixture',lambda cid:{'case':c,'rules':r}),patch.object(entry,'protocol',lambda:cfg),patch.object(entry,'annotation_task',lambda cid:None):result=entry.consolidate('SYN')
            audit=entry.read(out/'local/SYN/P/offline-audit.json')
            self.assertEqual(audit['checks'][0]['disposition'],'STRUCTURAL_INVALID')
            self.assertEqual(audit['checks'][1]['disposition'],'CONDITIONALLY_AVAILABLE_USE')
            self.assertEqual(result['answer']['records'][0]['text'],unit['records'][0]['proposition'])
            chosen=int(unit['records'][0]['refs'][0].split(':')[1])-1
            self.assertEqual(result['answer']['records'][0]['restored_source'][0]['text'],c['segments'][chosen]['text'])
            self.assertEqual(entry.read(part/'parsed.json'),x)
            self.assertEqual(entry.read(out/'local/SYN/P/independent-check.json')['status'],'OK')

    def test_source_text_not_premise_truth_and_opposition_preserved(self):
        c,r,x=fixture();u=x['analyses'][0];u['judgments'][0]['complete']=False
        u['uses'].append(copy.deepcopy(u['uses'][0]));u['uses'][1]['direction']='OPPOSE'
        t,_=pipe.convert(x,c,pipe.VERSION);self.assertEqual(pipe.independent_import(x,t,c,pipe.VERSION)['status'],'OK')
        p,_=pipe.merge_parts([('P01',t)]);a=pipe.apply_connection_decisions(c,r,p)
        self.assertEqual(a['premise_judgments'][0]['conditional_state'],'UNKNOWN')
        self.assertEqual(len(a['checks']),2)
        self.assertEqual(p['uses'][1]['direction'],'OPPOSE')

    def test_wrong_namespace_rejected_not_guessed(self):
        c,r,x=fixture();x['analyses'][0]['uses'][0]['records']=['SRC:1']
        with self.assertRaises(ValueError):pipe.validate(x,pipe.schema(r,c))
        t,_=pipe.convert(x,c,pipe.VERSION);self.assertEqual(t['analyses'][0]['uses'][0]['records'],[0]);self.assertEqual(len(t['analyses'][0]['records']),1)

    def test_reuse_stage_escape_and_nested_chunks(self):
        c,r,x=fixture();u=x['analyses'][0];rec=u['records'][0]
        rec['proposition']='A qualified statement with escaped "quotes", newline\n and \\ path. '+('A different fact. '*25)
        u['records']=[rec,{**rec,'stage':'different stage'},{**rec,'court_level':'different court'}]
        u['uses'].append(copy.deepcopy(u['uses'][0]));u['uses'][1]['direction']='OPPOSE'
        s=json.dumps(x);g=ExpansionGuard()
        for i in range(0,len(s),7):g.feed(s[i:i+7])
        self.assertIsNone(g.hit)
        g=ExpansionGuard();g.feed('{"analyses":[{"premise":"P","records":[{"proposition":"incomplete \\')
        self.assertIsNone(g.hit)

    def test_cumulative_exact_expansion_not_similarity(self):
        rec={'proposition':'A factual qualification. '*18,'status':'CLAIM','stage':'trial','court_level':'Trial','refs':['SRC:1']}
        records=[rec];current=rec['proposition']
        for i in range(3):
            current+=' Additional stated qualification '+str(i)+'.';records.append({**rec,'proposition':current})
        s=json.dumps({'analyses':[{'premise':'P','records':records}]});g=ExpansionGuard()
        with self.assertRaises(RepetitionAbort):
            for i in range(0,len(s),13):g.feed(s[i:i+13])
        self.assertEqual(g.hit['kind'],'CUMULATIVE_RECORD_PREFIX_EXPANSION')
        # Same long source reused in separate premise units has separate scope.
        g=ExpansionGuard();g.feed(json.dumps({'analyses':[{'premise':str(i),'records':[rec]} for i in range(4)]}));self.assertIsNone(g.hit)

    def test_source_address_list_repeat_and_new_field_string_guard(self):
        g=ExpansionGuard()
        with self.assertRaises(RepetitionAbort):g.feed('{"records":[{"refs":["SRC:1","SRC:1","SRC:1"')
        self.assertEqual(g.hit['kind'],'REPEATED_SOURCE_ADDRESS_IN_ONE_LIST')
        g=StringGuard()
        with self.assertRaises(RepetitionAbort):g.feed(json.dumps({'proposition':'abcdefghijklmnop'*20}))

    def test_actual_runner_abort_saves_raw_tokens_null_and_cost(self):
        from legal_bench.proof_carrying.local_runtime_v19_compact import Runner,SETTINGS
        from types import SimpleNamespace
        runner=Runner.__new__(Runner);runner.settings=dict(SETTINGS);runner.versions={};runner.model_config_hash='synthetic';runner.loaded_seconds=0
        runner.render=lambda prompt:'<think>\n\n</think>';runner.tokenizer=SimpleNamespace(encode=lambda t:[1]);runner.model=None;runner.processor=None
        raw='{"analyses":[{"premise":"P","records":[{"proposition":"'+('exactloop'*50)+'"'
        def stream(*args,**kwargs):
            yield SimpleNamespace(text=raw,token_ids=[1,2,3],token=None,generation_tokens=3,prompt_tokens=1,finish_reason=None)
        with tempfile.TemporaryDirectory() as d,patch('mlx_vlm.generate.stream_generate',stream):
            result=runner.run('synthetic',{},Path(d),16384,60,'NONE')
            self.assertEqual(result['run_status'],'REPETITION_ABORT');self.assertEqual(result['output_tokens'],3)
            self.assertEqual((Path(d)/'raw-response.txt').read_text(),raw)
            self.assertTrue((Path(d)/'token-ids.json').exists());self.assertGreater(result['elapsed_seconds'],0)
            self.assertFalse((Path(d)/'parsed.json').exists())
            # This is the real scheduler's formal answer policy, not repaired JSON.
            entry.save(Path(d)/'formal-answer.json',{'answer':None,'status':result['run_status']})
            self.assertIsNone(entry.read(Path(d)/'formal-answer.json')['answer'])

if __name__=='__main__':unittest.main()
