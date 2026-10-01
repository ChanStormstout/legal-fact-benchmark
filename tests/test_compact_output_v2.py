import unittest,json,copy
from legal_bench.compact_output_v2 import examples,convert,schema,validate_shape
from legal_bench.core import read
from legal_bench.field_pipeline_v2 import import_declared,execute_declared
from legal_bench.typed_relations import import_edges

class CompactTests(unittest.TestCase):
    def setUp(self):
        self.tasks=read('outputs/local-qwen-pattern-eval-v2/tasks.json')['tasks']
        self.source={'case_id':'DEMO','url':'synthetic:format-test','text_sha256':'demo','segments':[{'id':'demo.s001','text':'Landlord L sought eviction of Tenant T from Room R. Tenant T had leased Room R from Landlord L.\nQuoted: "Q"\t\\ and \u0001 control.'}]}
        self.b,self.a=examples(self.tasks)
    def test_quote_expansion_preserves_controls_and_content(self):
        b,log=convert(self.b,self.source,'B',self.tasks)
        self.assertEqual(b['events'][0]['evidence'][0]['quote'],self.source['segments'][0]['text'])
        self.assertEqual(json.loads(json.dumps(b))['events'][0]['evidence'][0]['quote'],self.source['segments'][0]['text'])
        self.assertEqual(len(log),2)
    def test_missing_field_not_filled(self):
        del self.b['events'][0]['polarity']
        with self.assertRaises(ValueError):convert(self.b,self.source,'B',self.tasks)
    def test_missing_citation_never_invented(self):
        self.b['events'][0]['evidence']=['absent']
        with self.assertRaises(ValueError):convert(self.b,self.source,'B',self.tasks)
    def test_declarations_not_inferred(self):
        self.b['events'][0]['known']=[]
        b,_=convert(self.b,self.source,'B',self.tasks)
        self.assertEqual(b['events'][0]['known_fields'],[])
        self.assertIsNone(b['events'][0]['time'])
        self.assertFalse(b['events'][0]['scope_parsed'])
    def test_example_enters_executor_without_expected_match(self):
        b,_=convert(self.b,self.source,'B',self.tasks);v=import_declared(b,self.source)
        reg=import_edges(v,self.source,b,{'group_ids':[],'parent_pairs':[]})
        self.assertEqual(len(v['events']),2)
        for t in self.tasks:self.assertEqual(execute_declared(v,reg,t['query'])['status'],'NOT_FOUND')
    def test_uncertainty_remains(self):
        self.b['events'][0]['unknown']=[{'affects':['polarity'],'reason':'conflicting assertions','evidence':['demo.s001']}]
        b,_=convert(self.b,self.source,'B',self.tasks)
        self.assertEqual(b['events'][0]['unresolved'][0]['affects'],['polarity'])
    def test_schema_rejects_pipe_placeholder(self):
        self.b['events'][0]['status']='NARRATED|COURT_FOUND'
        with self.assertRaises(ValueError):validate_shape(self.b,schema(self.source,'B',self.tasks))
    def test_direct_answers_complete(self):
        a,_=convert(self.a,self.source,'A',self.tasks)
        self.assertEqual({x['task_id'] for x in a['answers']},{t['task_id'] for t in self.tasks})

if __name__=='__main__':unittest.main()
