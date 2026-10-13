#!/usr/bin/env python3
"""Pinned real tokenizer and schema mask replay; no weights or generation."""
import copy,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tests.test_pipeline_contract_v19_7 import fixture
from legal_bench.proof_carrying import local_pipeline_v19_7 as pipe
from scripts.proof_pipeline_contract_v19_7 import OUT,OLD,context,read,save

def run():
 from transformers import AutoTokenizer
 from legal_bench.mlx_json_constraint import tokenizer_data
 from legal_bench.mlx_json_constraint_v19_6 import SchemaMask
 start=time.monotonic();model_path=(ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip()
 tok=AutoTokenizer.from_pretrained(model_path,local_files_only=True);data=tokenizer_data(tok,tok.eos_token_id)
 c,r,x=fixture();sc=pipe.schema(r,c);values=[('valid',x,True)]
 z=copy.deepcopy(x);z['analyses']['R1.P1']['judgments'][0]['components'][0]['component_id']='R99.K1';values.append(('wrong_fixed_component',z,False))
 z=copy.deepcopy(x);z['analyses']['R1.P1']['records'][0]['refs']=['SRC:1','SRC:1'];values.append(('duplicate_source',z,False))
 z=copy.deepcopy(x);z['analyses']['R1.P1']['uses'][0]['records']=['SRC:1'];values.append(('wrong_namespace',z,False))
 z=copy.deepcopy(x);z['analyses']['R1.P1']['uses'][0]['records']=['EV:999'];values.append(('dynamic_existence_import_only',z,True))
 receipts=[]
 for name,value,expected in values:
  ids=tok.encode(json.dumps(value,separators=(',',':')),add_special_tokens=False);mask=SchemaMask(data,sc);prefix=[];blocked=None
  for i,token in enumerate(ids):
   if token not in mask.enforcer.get_allowed_tokens(prefix).allowed_tokens:blocked=i;break
   prefix.append(token)
  ended=blocked is None and tok.eos_token_id in mask.enforcer.get_allowed_tokens(prefix).allowed_tokens
  assert ended==expected,(name,blocked)
  receipts.append({'id':name,'EOS_allowed':ended,'blocked_at':blocked,'tokens':len(ids),'expected':expected})
 capacity=[]
 for task in read(OLD/'freeze/protocol.json')['tasks']:
  f,part=context(task);prompt=pipe.proposal_prompt(f['case'],f['rules'],part)
  rendered=tok.apply_chat_template([{'role':'user','content':prompt}],tokenize=False,add_generation_prompt=True,enable_thinking=False)
  count=len(tok.encode(rendered));assert count+16384+256<=65536
  capacity.append({'case_id':task['case_id'],'input_tokens_local_tokenizer':count,'reserved_output':16384,'template_margin':256,'total':count+16384+256,'no_source_truncation':True})
 result={'status':'PASS','model_loaded':False,'model_calls':0,'tokenizer_revision':'8b2b98c00a6b4d291155e4890773ca8f769aee53','receipts':receipts,'capacity':capacity,'elapsed_seconds':time.monotonic()-start,'provider_decoder_not_this_local_mask':True}
 save(OUT/'engineering/tokenizer-replay.json',result);print(json.dumps(result))
if __name__=='__main__':run()
