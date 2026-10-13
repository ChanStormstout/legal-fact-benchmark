import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_local_pipeline_v19 import fixture
from legal_bench.proof_carrying import local_pipeline_v19_refs as pipe
from legal_bench.proof_carrying.reference_addresses_v19 import convert, audit
from legal_bench.proof_carrying.local_checker_v19_refs import check, check_import
from scripts import proof_local_refs_v19 as entry


def typed_fixture():
    c,r,x=fixture()
    source={s['id']:'SRC:'+str(i) for i,s in enumerate(c['segments'],1)}
    def walk(v):
        if isinstance(v,dict):
            for k,value in v.items():
                if k=='refs':v[k]=[source[a] for a in value]
                else:walk(value)
        elif isinstance(v,list):
            for value in v:walk(value)
    walk(x)
    for unit in x['analyses']:
        for use in unit['uses']:
            use['records']=['EV:'+str(a) for a in use['records']]
            for b in use['bindings']:b['object']='OBJ:'+str(b['object'])
            for w in use['witnesses']:w.pop('quote',None)
        for j in unit['judgments']:
            for b in j['bindings']:b['object']='OBJ:'+str(b['object'])
            for field in ('uses','opposition_uses'):j[field]=['USE:'+str(a) for a in j[field]]
            for comp in j['components']:comp['alternatives']=[['USE:'+str(a) for a in z] for z in comp['alternatives']]
    return c,r,x


class ReferenceAddresses(unittest.TestCase):
    def execute(self,x,c,r):
        p0,ledger=convert(x,c,'V19_4')
        self.assertEqual(check_import(x,p0,c,'V19_4')['status'],'OK')
        p,_=pipe.merge_parts([('P01',p0)])
        result=pipe.apply_connection_decisions(c,r,p)
        self.assertEqual(check(c,r,p,None,result)['status'],'OK')
        return p,result,ledger

    def test_schema_valid_and_fully_ending(self):
        c,r,x=typed_fixture();pipe.validate(x,pipe.schema(r,c))
        p,a,l=self.execute(x,c,r)
        self.assertEqual(a['conditional_rules'][0]['conditional_result'],'TRUE')
        self.assertEqual(a['raw_records_retained'],1)
        self.assertFalse(a['checks'][0]['semantic_verified']) if 'semantic_verified' in a['checks'][0] else self.assertFalse(a.get('semantic_approval',False))

    def test_schema_blocks_cross_namespace_bare_number_and_zero(self):
        for value in ('SRC:1','OBJ:1','USE:1','EV:0',0,1):
            c,r,x=typed_fixture();x['analyses'][0]['uses'][0]['records']=[value]
            with self.assertRaises(ValueError):pipe.validate(x,pipe.schema(r,c))
        c,r,x=typed_fixture();x['analyses'][0]['records'][0]['refs']=['EV:1']
        with self.assertRaises(ValueError):pipe.validate(x,pipe.schema(r,c))

    def test_nonexistent_dynamic_reference_local_only(self):
        c,r,x=typed_fixture();u=x['analyses'][0];u['uses'].append(copy.deepcopy(u['uses'][0]));u['uses'][0]['records']=['EV:144'];u['judgments'][0]['uses']=['USE:1','USE:2'];u['judgments'][0]['components'][0]['alternatives']=[['USE:1'],['USE:2']]
        # Pattern valid does not mean dynamically declared item exists.
        pipe.validate(x,pipe.schema(r,c));p,a,l=self.execute(x,c,r)
        self.assertEqual(len(p['records']),1)
        self.assertEqual(a['checks'][0]['disposition'],'STRUCTURAL_INVALID')
        self.assertEqual(a['checks'][1]['disposition'],'CONDITIONALLY_AVAILABLE_USE')
        self.assertEqual(a['conditional_rules'][0]['conditional_result'],'TRUE')
        self.assertIn('NONEXISTENT_LOCAL_REFERENCE',{v['status'] for v in l})

    def test_illegal_import_not_guessed_or_globalized(self):
        c,r,x=typed_fixture();x['analyses'][0]['uses'][0]['records']=['SRC:1']
        p,a,l=self.execute(x,c,r)
        self.assertEqual(p['uses'][0]['records'],[0]);self.assertEqual(len(p['records']),1)
        self.assertEqual(a['premise_judgments'][0]['conditional_state'],'UNKNOWN')
        self.assertEqual(x['analyses'][0]['uses'][0]['records'],['SRC:1'])

    def test_object_and_use_namespaces_not_interchangeable(self):
        c,r,x=typed_fixture();x['analyses'][0]['uses'][0]['bindings'][0]['object']='EV:1'
        p,a,l=self.execute(x,c,r);self.assertEqual(a['checks'][0]['disposition'],'STRUCTURAL_INVALID')
        c,r,x=typed_fixture();x['analyses'][0]['judgments'][0]['components'][0]['alternatives']=[['EV:1']]
        p,a,l=self.execute(x,c,r);self.assertEqual(a['checks'][0]['disposition'],'CONDITIONALLY_AVAILABLE_USE');self.assertEqual(a['premise_judgments'][0]['conditional_state'],'UNKNOWN')

    def test_legacy_zero_and_144_unchanged(self):
        c,r,x=fixture();x['analyses'][0]['uses'][0]['records']=[144];x['analyses'][0]['judgments'][0]['uses']=[0,1]
        before=copy.deepcopy(x);t,l=convert(x,c,'V19_1');self.assertEqual(x,before);self.assertEqual(t['analyses'][0]['uses'][0]['records'],[144]);self.assertEqual(check_import(x,t,c,'V19_1')['status'],'OK')
        p,_=pipe.merge_parts([('P01',t)]);a=pipe.apply_connection_decisions(c,r,p);self.assertEqual(p['uses'][0]['records'],[0]);self.assertEqual(len(p['records']),1);self.assertEqual(a['checks'][0]['disposition'],'STRUCTURAL_INVALID')
        self.assertIn('ZERO_REFERENCE',{v['status'] for v in audit(x,c,'V19_1')})

    def test_independent_import_detects_wrong_remap(self):
        c,r,x=typed_fixture();t,l=convert(x,c,'V19_4');t['analyses'][0]['uses'][0]['records']=[2]
        self.assertEqual(check_import(x,t,c,'V19_4')['status'],'REJECTED')

    def test_multi_source_restored_as_separate_fragments(self):
        c,r,x=typed_fixture();w=x['analyses'][0]['uses'][0]['witnesses'][0];w['refs']=[s['choice'] for s in pipe.source_directory(c)]
        t,l=convert(x,c,'V19_4');self.assertEqual(check_import(x,t,c,'V19_4')['status'],'OK');self.assertEqual(len(t['analyses'][0]['uses'][0]['witnesses']),len(c['segments']))

    def test_real_entry_consolidation_preserves_bad_use_and_valid_alternative(self):
        c,r,x=typed_fixture();u=x['analyses'][0];u['uses'].append(copy.deepcopy(u['uses'][0]));u['uses'][0]['records']=['EV:999'];u['judgments'][0]['uses']=['USE:1','USE:2'];u['judgments'][0]['components'][0]['alternatives']=[['USE:1'],['USE:2']]
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);part=out/'local/SYN/P01';entry.save(part/'run.json',{'run_status':'OK'});entry.save(part/'parsed.json',x);entry.save(part/'production-version.json',{'version':'V19_4'})
            cfg={'local_generation_slots':[{'role':'P','case_id':'SYN','dest':'local/SYN/P01','part':{'id':'P01','source_ids':[s['id'] for s in c['segments']]}}]}
            with patch.object(entry,'OUT',out),patch.object(entry,'fixture',lambda cid:{'case':c,'rules':r}),patch.object(entry,'protocol',lambda:cfg),patch.object(entry,'annotation_task',lambda cid:None):m=entry.consolidate('SYN')
            a=entry.read(out/'local/SYN/P/offline-audit.json');self.assertEqual(a['raw_records_retained'],1);self.assertEqual(a['checks'][0]['disposition'],'STRUCTURAL_INVALID');self.assertEqual(a['checks'][1]['disposition'],'CONDITIONALLY_AVAILABLE_USE')
            self.assertEqual(entry.read(out/'local/SYN/P/independent-check.json')['status'],'OK');self.assertTrue((out/'inputs/SYN/learner-inputs.json').exists());self.assertEqual(entry.read(part/'parsed.json'),x)

    def test_real_entry_dispatch_uses_typed_schema_and_safe_pause(self):
        from legal_bench.proof_carrying.local_runtime_v19_refs import SETTINGS
        c,r,x=typed_fixture();part={'id':'P01','rule_ids':[z['id'] for z in r],'source_ids':[s['id'] for s in c['segments']]}
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);prep=out/'preparation';entry.text(prep/'inputs/SYN/P01-prompt.txt',pipe.proposal_prompt(c,r,part));entry.save(prep/'inputs/SYN/P01-schema.json',pipe.schema(r,c))
            slots=[{'role':'P','case_id':'SYN','dest':'local/SYN/P01','part':part,'max_tokens':16384},{'role':'P','case_id':'SYN','dest':'local/SYN/P02','part':{**part,'id':'P02'},'max_tokens':16384}]
            cfg={'runtime_settings':SETTINGS,'first_DEV':'SYN','local_generation_slots':slots,'P_seconds_cap':86400,'final_seconds_cap':43200,'per_call_seconds_cap':3600}
            class SavedTransport:
                def run(self,prompt,schema,dest,*args):
                    pipe.validate(x,schema);entry.text(dest/'prompt.txt',prompt);entry.save(dest/'schema.json',schema);entry.save(dest/'parsed.json',x);entry.save(dest/'run.json',{'run_status':'OK','elapsed_seconds':0,'model_called':False});entry.save(out/'PAUSE_REQUESTED.json',{'reason':'SYNTHETIC_SAVED_BOUNDARY'});return {'run_status':'OK'}
            with patch.object(entry,'OUT',out),patch.object(entry,'PREP',prep),patch.object(entry,'fixture',lambda cid:{'case':c,'rules':r}),patch.object(entry,'assert_frozen',lambda:cfg),patch.object(entry,'protocol',lambda:cfg),patch.object(entry,'annotation_task',lambda cid:None):self.assertEqual(entry.run_local('P',SavedTransport()),'PAUSED')
            self.assertEqual(entry.read(out/'local/SYN/P01/production-version.json')['version'],'V19_4');self.assertFalse((out/'local/SYN/P02/start.json').exists())


if __name__=='__main__':unittest.main()
