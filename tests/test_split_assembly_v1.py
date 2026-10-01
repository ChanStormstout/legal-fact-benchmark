import copy,unittest
from legal_bench.split_assembly_v1 import assemble
from legal_bench.field_pipeline_v2 import import_declared,execute_declared

class SplitAssemblyTests(unittest.TestCase):
    def test_over20_keeps_events_and_replays_sources(self):
        source={'text_sha256':'synthetic-fixture-hash','url':'synthetic:fixture','case_id':'X','segments':[{'id':'s','text':'Synthetic actor A with property P.'}]}
        registry=[{'id':'a','label':'A','kind':'PERSON','resolved':True,'evidence':['s']},{'id':'p','label':'P','kind':'PROPERTY','resolved':True,'evidence':['s']}]
        outputs={}
        for typ,roles in [('OWN_PROPERTY',{'owner':'A','property':'P'}),('SUBLET_PROPERTY',{'tenant':'A','subtenant':None,'property':'P'}),('LEASE_PROPERTY',{'landlord':None,'tenant':'A','property':'P','agreement':None})]:
            fact={'explanation':'Synthetic execution fixture, not legal evidence','status':'NARRATED','polarity':'POSITIVE','roles':roles,'evidence':['s'],'unknown':[]}
            outputs[typ]={'facts':[copy.deepcopy(fact) for _ in range(8)],'overflow':False}
        outputs['FILE_EVICTION']={'facts':[{'explanation':'Synthetic filing','status':'NARRATED','polarity':'POSITIVE','roles':{'filer':'A','respondent':None,'property':'P'},'evidence':['s'],'unknown':[]}],'overflow':False}
        before=copy.deepcopy(outputs)
        data,_=assemble(outputs,{},registry,source,[])
        self.assertEqual(len(data['events']),25)
        self.assertEqual(len({e['id'] for e in data['events']}),25)
        self.assertEqual(outputs,before)
        self.assertTrue(all(e['evidence'][0]['quote']==source['segments'][0]['text'] for e in data['events']))
        view=import_declared(data,source)
        result=execute_declared(view,{'edges':[]},{'atoms':[{'var':'x','type':'OWN_PROPERTY','status':'NARRATED'}],'constraints':[]})
        self.assertEqual(result['status'],'MATCH')
