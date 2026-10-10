import copy,json,tempfile,unittest
from pathlib import Path
from legal_bench.proof_carrying.workflow_v8 import *
from legal_bench.proof_carrying.candidates_v8 import generate,graph,select
from legal_bench.proof_carrying.delivery_v8 import compile_derivation
OLD=Path('outputs/proof-carrying-pipeline-v7')

class Integration(unittest.TestCase):
    def setUp(self):
        self.cid='840688';self.base=OLD/'inputs'/self.cid
        self.der=read_json(self.base/'derivation.json');self.requests=fixed_requests(self.der)
    def test_missing_request_preserved(self):
        malformed=copy.deepcopy(self.der);malformed['requests'][0].pop('proposed_state')
        imported=import_derivation(malformed,self.requests)
        final=complete_requests(imported,{'status':'COMPLETED','requests':[{'id':'Q-S2','answer':'TRUE'}]})
        self.assertEqual(len(final['requests']),2);self.assertIsNone(final['requests'][0]['answer'])
        self.assertFalse(final['all_slots_technically_complete']);self.assertEqual(final['requests'][1]['technical_status'],'OK')
    def test_changed_request_predicate_rejected(self):
        der=copy.deepcopy(self.der);der['requests'][0]['predicate']='DIFFERENT'
        self.assertEqual(import_derivation(der,self.requests)['request_slots'][0]['technical_status'],'CONTRACT_ERROR')
    def test_history_uses_frozen_not_live(self):
        self.assertEqual(verify_history(OLD/'cases'/self.cid)['status'],'VERIFIED_FROZEN_BYTES')
    def test_frozen_real_entry(self):
        with tempfile.TemporaryDirectory() as d:
            result=replay_history(OLD/'cases'/self.cid,Path(d)/'replay.json')
            self.assertEqual(result['returncode'],0);self.assertEqual(json.loads(result['stdout'])['status'],'COMPLETED')
    def test_source_identity_and_foreign_fact(self):
        spec=read_json(self.base/'spec.json');sources=read_json(self.base/'sources.json')
        restored,docs=source_roles(self.cid,sources,spec['documents'])
        p=read_json(self.base/'facts.json')['premises'][0]
        self.assertTrue(fact_source_check(p,restored).startswith('ADDRESS_AND_ROLE_VALID'))
        for s in restored.values():s['document_role']='PRECEDENT'
        self.assertEqual(fact_source_check(p,restored),'FOREIGN_SOURCE_CANNOT_ESTABLISH_TARGET_FACT')
    def test_multi_document_not_body_citations(self):
        with tempfile.TemporaryDirectory() as folder:
            docs=[];sources={}
            for did,role in [('target','TARGET'),('other','PRECEDENT')]:
                p=Path(folder)/(did+'.json');seg={'id':did+':1','original_line':1,'text':'Mentions another case and https://example.com/doc/other, still this document.'}
                p.write_text(json.dumps({'document_id':did,'segments':[seg]}));docs.append({'path':str(p),'sha256':byte_hash(p),'role':role})
                sources[seg['id']]={**seg,'document':did,'url':'https://example.com/'+did}
            restored,_=source_roles('target',sources,docs);self.assertEqual(restored['other:1']['document_role'],'PRECEDENT')
    def test_candidate_generation_label_blind_and_downstream(self):
        facts=read_json(self.base/'facts.json');rules=read_json(self.base/'rules.json')['rules'];src=read_json(self.base/'sources.json')
        for s in src.values():s['document_role']='TARGET'
        cs=generate(facts,rules,src,lambda a,b:float(a==b));self.assertGreater(len(cs),len(rules))
        g=graph(facts,rules,src,cs,self.requests);self.assertFalse(g['labels_in_input'])
        a=select(cs,{c['id']:float(i) for i,c in enumerate(cs)},1)
        b=select(cs,{c['id']:-float(i) for i,c in enumerate(cs)},1)
        self.assertNotEqual(a['selected'],b['selected'])
        da,_=compile_derivation(cs,a['selected'],{r['id']+'@'+str(r['version']):r for r in rules},self.requests,{})
        db,_=compile_derivation(cs,b['selected'],{r['id']+'@'+str(r['version']):r for r in rules},self.requests,{})
        self.assertNotEqual(da['steps'][0]['id'],db['steps'][0]['id'])
    def test_revision_is_local(self):
        snap=read_json(OLD/'cases'/self.cid/'snapshot.json');idx=reverse_index(snap,self.der)
        impact=revision_impact(idx,['premise:P1']);self.assertIn('premise:P1',impact['affected']);self.assertTrue(impact['unchanged'])
        self.assertFalse(impact['semantic_change_inherits_approval'])

if __name__=='__main__':unittest.main()

class DeliveryEntry(unittest.TestCase):
    def test_actual_run_case_preserves_all_slots(self):
        from legal_bench.proof_carrying.delivery_v8 import run_case
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);cid='840688';inp=root/'inputs'/cid;inp.mkdir(parents=True)
            source=Path('outputs/proof-carrying-graph-integration-v8/inputs')/cid
            for p in source.glob('*.json'):(inp/p.name).write_bytes(p.read_bytes())
            facts=read_json(OLD/'inputs'/cid/'facts.json');rules=read_json(inp/'rules.json');sources=read_json(inp/'sources.json')
            cs=generate(facts,rules,sources,lambda a,b:float(a==b))
            write_once(root/'runs'/cid/'proposal/usable.json',facts)
            write_once(root/'runs'/cid/'reference/usable.json',{'premise_reviews':[],'candidate_reviews':[]})
            write_once(root/'candidates'/(cid+'.json'),cs);write_once(root/'protocol.json',{'candidate_budget':1})
            result=run_case(root,cid,'Engineering',{c['id']:float(i) for i,c in enumerate(cs)})
            self.assertEqual(len(result['requests']),2)
            self.assertTrue(any(x['technical_status']=='NOT_SELECTED' for x in result['requests']))
            self.assertTrue((root/'results/Engineering'/cid/'index.html').exists())
            invocation=read_json(root/'results/Engineering'/cid/'invocation.json')
            self.assertTrue(invocation['independent_process']);self.assertEqual(invocation['returncode'],0)
