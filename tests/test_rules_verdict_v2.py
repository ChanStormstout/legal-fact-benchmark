import copy
import unittest
from legal_bench.rules_verdict_v1.extract import demonstration, field_value
from legal_bench.rules_verdict_v1.extract_v2 import objects_schema, facts_schema, answer_schema, import_v2, at_string_limits
from legal_bench.rules_verdict_v1.contracts import validate

class TypedRepair(unittest.TestCase):
    def setUp(self):
        self.source, old = demonstration()
        self.objects={'case_id':'DEMO','objects':old.pop('objects')}
        r=old['records'][0]
        r['roles']={'payer':['o1'],'recipient':None,'premises':['o2'],'contract':None}
        self.facts=old

    def test_complete_record_and_source_preserved(self):
        view=import_v2(self.facts,self.objects,self.source,'w')
        self.assertEqual(view['records'][0]['roles']['payer'],'w:o1')
        self.assertEqual(view['records'][0]['evidence'][0]['quote'], self.source['segments'][0]['text'])

    def test_reference_ids_cannot_be_assertion_ids(self):
        self.facts['relations']=[{'id':'r1','op':'part_of','left':'f1','right':'o2','decision':'SUPPORTED','status':'NARRATED','stage':'claim','context':'MAIN_CASE','reason':'test','evidence':['demo.1']}]
        with self.assertRaises(ValueError): validate(self.facts,facts_schema(self.source,self.objects['objects']))

    def test_organization_cannot_be_property_part(self):
        self.objects['objects'].append({'id':'o3','label':'Firm','kind':'ORGANIZATION','evidence':['demo.1']})
        self.facts['relations']=[{'id':'r1','op':'part_of','left':'o3','right':'o2','decision':'SUPPORTED','status':'NARRATED','stage':'claim','context':'MAIN_CASE','reason':'test','evidence':['demo.1']}]
        with self.assertRaises(ValueError): validate(self.facts,facts_schema(self.source,self.objects['objects']))

    def test_multiple_people_not_distributed_or_dropped(self):
        self.objects['objects'].append({'id':'o3','label':'Alex','kind':'PERSON','evidence':['demo.1']})
        self.facts['records'][0]['roles']['payer']=['o1','o3']
        before=copy.deepcopy(self.facts)
        view=import_v2(self.facts,self.objects,self.source,'w')
        self.assertEqual(len(view['records']),1)
        self.assertIsNone(field_value(view['records'][0],'roles.payer')[0])
        self.assertEqual(field_value(view['records'][0],'roles.premises')[0],'w:o2')
        self.assertEqual(view['multi_role_bindings'][0]['object_ids'],['o1','o3'])
        self.assertEqual(before,self.facts)

    def test_null_known_date_only_blocks_date(self):
        self.facts['records'][0]['known'].append('time')
        view=import_v2(self.facts,self.objects,self.source,'w')
        self.assertEqual(len(view['records']),1)
        self.assertEqual(field_value(view['records'][0],'predicate')[0],'PAY_RENT')
        self.assertIsNone(field_value(view['records'][0],'time')[0])
        self.assertEqual(view['field_isolation'][0]['field'],'time')

    def test_answer_at_field_limit_flagged_separately(self):
        schema=answer_schema(self.source)
        answer={'case_id':'DEMO','outcome':'UNDETERMINED','assessment_status':'UNRESOLVED','reasons':['x'*1200],'evidence':[],'missing':[],'other_combinations':'No other candidates.'}
        validate(answer,schema)
        self.assertEqual(at_string_limits(answer,schema),['$.reasons[0]'])

if __name__=='__main__': unittest.main()
