import unittest
from legal_bench.pair_extraction_v9 import pairs,pair_source,type_prompt
from legal_bench.core import read

class PairExtractionTests(unittest.TestCase):
    def test_no_group_invented_from_a_single_respondent(self):
        t=[x for x in read('outputs/local-qwen-pattern-eval-v3/tasks.json')['tasks'] if x['task_id']=='52a7d11461a492d0']
        outputs={'LEASE_PROPERTY':{'facts':[{'status':'NARRATED','polarity':'POSITIVE','roles':{'tenant':'T'}}]},'FILE_EVICTION':{'facts':[{'status':'NARRATED','polarity':'POSITIVE','roles':{'respondent':'T'}}]}}
        self.assertEqual(pairs(outputs,[{'label':'T','kind':'PERSON'}],t),[])

    def test_context_collects_original_neighbor_without_rewriting(self):
        s={'segments':[{'id':str(i),'text':'original'+str(i)} for i in range(5)]}
        selected=pair_source(s,[{'label':'R','evidence':['2']},{'label':'B','evidence':['2']}],{},'R','B')
        self.assertEqual(selected['segments'],s['segments'][:4])

    def test_synthetic_facts_removed_from_semantic_prompt(self):
        source={'case_id':'X','segments':[{'id':'s','text':'Actual judgment.'}]}
        prompt=type_prompt(source,[],'FILE_EVICTION','same case')
        self.assertNotIn('two occupants',prompt)
        self.assertNotIn('SYNTHETIC',prompt)
        self.assertIn('Actual judgment.',prompt)
