import copy
import unittest
from tests import test_typed_relations as fixtures
from legal_bench.field_pipeline_v2 import import_declared,execute_declared,value
from legal_bench.typed_relations import import_edges

class DeclaredFieldTests(unittest.TestCase):
    def setUp(self):
        f=fixtures.TypedRelationTests();f.setUp();self.f=f
        for e in f.ann['events']:
            e['known_fields']=[{'field':k,'value':e[k],'evidence':[f.ev]} for k in ['type','status','polarity']]
            e['known_fields'] += [{'field':'roles.'+k,'value':v,'evidence':[f.ev]} for k,v in e['roles'].items()]
            e['scope_dependencies']=[]
    def data(self):
        f=self.f;v=import_declared(f.ann,f.source);r=import_edges(v,f.source,f.reply,f.target);return v,r
    def test_known_payment_excluded_before_unknown_scope(self):
        e=copy.deepcopy(self.f.ann['events'][1]);e.update(id='rent',type='PAY_RENT',polarity='NEGATIVE',roles={'payer':'T'},scope={'period':'unclear'},scope_parsed=False)
        e['known_fields']=[{'field':'type','value':'PAY_RENT','evidence':[self.f.ev]}]
        e['scope_dependencies']=[{'scope_key':'period','affects':['time'],'evidence':[self.f.ev],'reason':'UNPARSED_PERIOD'}]
        self.f.ann['events']=[e];v,r=self.data();x=execute_declared(v,r,self.f.q)
        self.assertEqual(x['status'],'NOT_FOUND');self.assertTrue(all(d['decision']=='EXCLUDE' for d in x['candidate_decisions']))
        self.assertEqual(value(v['events'][0],'type')[0],'PAY_RENT');self.assertIsNone(value(v['events'][0],'polarity')[0]);self.assertIsNone(value(v['events'][0],'time')[0])
    def test_date_only_uncertainty_preserves_nontemporal_match(self):
        e=self.f.ann['events'][1];e['scope']={'period':'unclear'};e['scope_parsed']=False
        e['scope_dependencies']=[{'scope_key':'period','affects':['time'],'reason':'unknown period','evidence':[self.f.ev]}]
        v,r=self.data();self.assertEqual(execute_declared(v,r,self.f.q)['status'],'MATCH');self.assertIsNone(value(v['events'][1],'time')[0]);self.assertFalse(v['events'][1]['scope_parsed'])
    def test_unknown_type_still_candidate(self):
        e=self.f.ann['events'][1];e['type']='UNKNOWN';e['known_fields']=[k for k in e['known_fields'] if k['field']!='type']
        v,r=self.data();x=execute_declared(v,r,self.f.q);self.assertEqual(x['status'],'UNKNOWN');self.assertTrue(any(d['decision']=='KEEP_UNKNOWN' for d in x['candidate_decisions']))
    def test_unknown_whole_proposition_retains_type_but_blocks_occurrence(self):
        e=self.f.ann['events'][1];e['scope']={'qualifier':'unclear'};e['scope_parsed']=False
        v,r=self.data();self.assertEqual(value(v['events'][1],'type')[0],'OCCUPY_PROPERTY');self.assertIsNone(value(v['events'][1],'status')[0]);self.assertEqual(execute_declared(v,r,self.f.q)['status'],'UNKNOWN')
    def test_explicit_type_block_overrides_type_claim(self):
        e=self.f.ann['events'][1];e['unresolved']=[{'field':'type','affects':['type'],'reason':'subject not certain','evidence':[self.f.ev]}]
        v,r=self.data();self.assertIsNone(value(v['events'][1],'type')[0])
    def test_missing_relation_remains_unknown_other_pair_can_match(self):
        v,r=self.data();r['edges']=[];self.assertEqual(execute_declared(v,r,self.f.q)['status'],'UNKNOWN')
        e=copy.deepcopy(self.f.ann['events'][1]);e['id']='wrong';e['roles']['property']='C'
        for k in e['known_fields']:
            if k['field']=='roles.property':k['value']='C'
        self.f.ann['events'].insert(0,e);v,r=self.data();x=execute_declared(v,r,self.f.q);self.assertEqual(x['status'],'MATCH');self.assertTrue(x['uncertain_bindings'])
    def test_record_identity_cannot_be_unknown_or_self_pair(self):
        e=self.f.ann['events'][0];e['scope']={'condition':'unclear'};e['scope_parsed']=False
        v,r=self.data();q={'atoms':[{'var':'x','type':'LEASE_PROPERTY','status':'ANY'},{'var':'y','type':'LEASE_PROPERTY','status':'ANY'}],'constraints':[{'op':'different','left':'x.id','right':'y.id'}]}
        self.assertEqual(execute_declared(v,r,q)['status'],'NOT_FOUND')

if __name__=='__main__':unittest.main()
