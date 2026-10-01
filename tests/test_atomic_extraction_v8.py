import unittest
from legal_bench.atomic_extraction_v8 import type_schema,convert
from legal_bench.compact_output_v3 import validate_shape

class AtomicExtractionTests(unittest.TestCase):
    def setUp(self):
        self.source={'case_id':'X','segments':[{'id':'s1','text':'A rents a room; the start date is unclear.'}]}
        self.registry=[{'id':'o1','label':'A','kind':'PERSON','resolved':True,'evidence':['s1']},{'id':'o2','label':'Room','kind':'PROPERTY','resolved':True,'evidence':['s1']}]
        self.record={'explanation':'The passage identifies a tenant and room.','status':'NARRATED','polarity':'POSITIVE','roles':{'landlord':None,'tenant':'A','property':'Room','agreement':None},'evidence':['s1'],'unknown':[{'affects':['roles.landlord'],'reason':'Not identified','evidence':['s1']}]}

    def test_missing_role_remains_null_not_declared_known(self):
        data,_=convert({'LEASE_PROPERTY':{'facts':[self.record],'overflow':False}}, {}, self.registry,self.source,[])
        event=data['events'][0]
        self.assertIsNone(event['roles']['landlord'])
        self.assertNotIn('roles.landlord',[f['field'] for f in event['known_fields']])
        self.assertEqual(event['roles']['tenant'],'o1')
        self.assertEqual(event['evidence'][0]['quote'],self.source['segments'][0]['text'])

    def test_wrong_label_is_not_repaired(self):
        self.record['roles']['tenant']='Someone else'
        with self.assertRaises(ValueError):
            validate_shape({'facts':[self.record],'overflow':False},type_schema(self.source,self.registry,'LEASE_PROPERTY'))

    def test_whole_proposition_block_is_preserved(self):
        self.record['unknown']=[{'affects':['*'],'reason':'Statement scope unclear','evidence':['s1']}]
        data,_=convert({'LEASE_PROPERTY':{'facts':[self.record],'overflow':False}}, {},self.registry,self.source,[])
        self.assertEqual(data['events'][0]['unresolved'][0]['affects'],['*'])
        self.assertNotIn('roles.tenant',[f['field'] for f in data['events'][0]['known_fields']])
