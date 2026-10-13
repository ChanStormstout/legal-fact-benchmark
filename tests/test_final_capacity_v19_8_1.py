import json,tempfile,unittest
from pathlib import Path
from tests.test_pipeline_diagnostic_v19_8 import fixture,process,part,CFG,final_answer
from scripts import proof_pipeline_contract_v19_8_1 as entry
from legal_bench.proof_carrying.capacity_v19_8_1 import token_ids
from legal_bench.proof_carrying.presentation_v19_8_1 import pack,unpack
from legal_bench.proof_carrying.local_schedule_v19 import state
class MappingTokenizer:
    def apply_chat_template(self,*args,**kwargs):return {'input_ids':list(range(100)),'attention_mask':[1]*100}
class FinalCapacity(unittest.TestCase):
    def test_tokenizer_shapes_count_ids_not_fields(self):
        self.assertEqual(len(token_ids({'input_ids':list(range(100)),'attention_mask':[1]*100})),100)
        self.assertEqual(token_ids([[1,2,3]]),[1,2,3]);self.assertEqual(token_ids([1,2,3]),[1,2,3])
        for value in ({'attention_mask':[1]},[],[[1],[2]],{'input_ids':['x']}):
            with self.assertRaises(ValueError):token_ids(value)
    def test_lossless_nested_pool_and_missing_ref(self):
        repeated={'fact':'Explicit counterevidence '*40,'values':[1,2,3]};x={'a':repeated,'b':repeated,'unresolved':False}
        y=pack(x);self.assertEqual(unpack(y),x)
        self.assertLess(len(json.dumps(y)),len(json.dumps(x)))
        y['material']['a']={'$exact_value':'BAD'}
        with self.assertRaises(ValueError):unpack(y)
    def test_corrected_actual_final_entry_capacity_guard(self):
        c,r,x=fixture();a=process(c,r,x)
        with tempfile.TemporaryDirectory() as d:
            result=entry.final_run(c,r,a,'D',part(c,r),d,lambda t:self.fail('Budget cannot dispatch'),tokenizer=MappingTokenizer(),config={**CFG,'context_budget':99})
            self.assertIsNone(result['answer']);self.assertEqual(result['run_status'],'INPUT_TOO_LONG')
            self.assertEqual(json.loads((Path(d)/'capacity.json').read_text())['input_tokens'],100)
            self.assertFalse((Path(d)/'start.json').exists())
    def test_corrected_final_entry_receipt_and_alias_roundtrip(self):
        c,r,x=fixture();a=process(c,r,x)
        with tempfile.TemporaryDirectory() as d:
            result=entry.final_run(c,r,a,'D',part(c,r),d,lambda t:(json.dumps(final_answer()),{'run_status':'OK','mock':True}),tokenizer=MappingTokenizer(),config=CFG)
            self.assertIsNotNone(result['answer']);self.assertEqual(state(d),'COMPLETED')
            task=json.loads((Path(d)/'task.json').read_text());self.assertTrue(task['presentation_audit']['exact_roundtrip'])
            self.assertEqual(task['delivery_version'],'V19_8_FINAL_DELIVERY_2')
if __name__=='__main__':unittest.main()
