"""Real tokenizer fixture replay only, no model load or generation."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from transformers import AutoTokenizer
from lmformatenforcer import JsonSchemaParser
from legal_bench.mlx_json_constraint import tokenizer_data
from legal_bench.mlx_json_constraint_v2 import CompositeQuoteEnforcer
from scripts.irac_pipeline_v4 import R,inputs,save,read
from legal_bench.irac_application.pipeline_v4_tasks import schema
from legal_bench.irac_application.pipeline_v4 import catalogue
p=Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip();tok=AutoTokenizer.from_pretrained(p,local_files_only=True);data=tokenizer_data(tok,tok.eos_token_id)
rows=[]
for cid in ['112400','188721101']:
 m,t,l=inputs(cid);cat=catalogue(t);sid=next(iter(m['sources']));tid=next(iter(cat));bid=cat[tid][0]
 sample={'bindings':[{'id':'b1','claim_ids':[t['claims'][0]['id']],'objects':'SYNTHETIC tokenizer fixture','event':'synthetic event','stage':'synthetic review','refs':[sid]}],'evidence':[{'id':'e1','binding_id':'b1','record':'Fixture ends with a composite quote.','statement_status':'UNKNOWN','refs':[sid],'uses':[{'test_id':tid,'branch_id':bid,'direction':'UNKNOWN','use':'RECORD_EXISTENCE'}]}],'limitations':[],'conditions':[],'coverage_limits':['Synthetic syntax only; no case assertion.']}
 sc=schema('proposal',m,t,l);text=json.dumps(sample);ids=tok.encode(text,add_special_tokens=False);mask=CompositeQuoteEnforcer(data,JsonSchemaParser(sc))
 for i,token in enumerate(ids):assert token in mask.get_allowed_tokens(ids[:i]).allowed_tokens,(cid,i)
 assert tok.eos_token_id in mask.get_allowed_tokens(ids).allowed_tokens
 rows.append({'schema_case':cid,'tokens':len(ids),'all_allowed':True,'eos':True,'synthetic_not_case_answer':True})
root=Path('outputs/json-constraint-diagnosis-v1');sc=read(root/'prepared/schema.json');ids=read(root/'runs/FIXED/token-ids.json');mask=CompositeQuoteEnforcer(data,JsonSchemaParser(sc))
for i,token in enumerate(ids):assert token in mask.get_allowed_tokens(ids[:i]).allowed_tokens,i
assert tok.decode(ids,skip_special_tokens=True)==(root/'runs/FIXED/raw-response.txt').read_text()
rows.append({'existing_fixed_token_replay':True,'tokens':len(ids),'raw_exact':True})
save(R/'engineering/real-tokenizer.json',{'passed':True,'model_calls':0,'tokenizer_path_revision':Path(p).name,'rows':rows});print('REAL_TOKENIZER_PASS',len(rows))
