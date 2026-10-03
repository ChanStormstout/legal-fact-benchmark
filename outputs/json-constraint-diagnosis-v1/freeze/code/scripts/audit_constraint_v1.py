"""No inference. Replay V9 token histories, inspect terminators, force known valid JSON."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.mlx_json_constraint import tokenizer_data,SchemaMask
from legal_bench.rules_verdict_v1.source_views import write_new
from transformers import AutoTokenizer
from lmformatenforcer import TokenEnforcer,JsonSchemaParser
R=Path('outputs/json-constraint-diagnosis-v1');OLD=Path('outputs/rules-verdict-v9-final-examples')
tok=AutoTokenizer.from_pretrained(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),local_files_only=True)
data=tokenizer_data(tok,tok.eos_token_id);quotes=tok.encode('"',add_special_tokens=False)
rows=[]
for a in ['A','B']:
 ids=json.loads((OLD/'runs'/a/'token-ids.json').read_text());schema=json.loads((OLD/'runs'/a/'schema.json').read_text());e=TokenEnforcer(data,JsonSchemaParser(schema));steps=[];bad=[]
 for i in range(len(ids)+1):
  allowed=e.get_allowed_tokens(ids[:i]).allowed_tokens
  if i<len(ids) and ids[i] not in allowed:bad.append(i)
  if i in [0,1,10,20,40,60,80,len(ids)] or (i>0 and tok.decode(ids[:i]).endswith('.')):
   steps.append({'generated_tokens':i,'tail':tok.decode(ids[:i])[-160:],'allowed_count':len(allowed),'standalone_quote_id':quotes,'standalone_quote_allowed':len(quotes)==1 and quotes[0] in allowed,'eos_allowed':tok.eos_token_id in allowed})
 raw=(OLD/'runs'/a/'raw-response.txt').read_text()
 rows.append({'method':a,'decoded_sampled_ids_equals_raw':tok.decode(ids)==raw,'invalid_generated_token_indices':bad,'checkpoints':steps})
# Legal-looking complete fixture but no inference or new reference answer.
schema={'type':'object','properties':{'point':{'type':'string'},'explanation':{'type':'string'}},'required':['point','explanation'],'additionalProperties':False}
sample=json.dumps({'point':'A stated claim.','explanation':'The statement is alleged; its truth is not established.'});ids=tok.encode(sample,add_special_tokens=False);e=TokenEnforcer(data,JsonSchemaParser(schema));bad=[]
for i,t in enumerate(ids):
 if t not in e.get_allowed_tokens(ids[:i]).allowed_tokens:bad.append({'i':i,'token':t,'decoded':tok.decode([t])})
end=e.get_allowed_tokens(ids).allowed_tokens
write_new(R/'offline-audit.json',{'rows':rows,'fixture':{'json':sample,'bad':bad,'eos_after_complete':tok.eos_token_id in end},'quote_token':quotes,'inference_calls':0})
print(json.dumps({'quote_token':quotes,'methods':[{ 'method':x['method'],'bad':x['invalid_generated_token_indices'],'last':x['checkpoints'][-1]} for x in rows],'fixture_bad':bad,'eos':tok.eos_token_id in end},indent=2))
