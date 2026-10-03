"""No model inference: verify real tokenizer transitions after versioned fix."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from transformers import AutoTokenizer
from lmformatenforcer import TokenEnforcer,JsonSchemaParser
from legal_bench.mlx_json_constraint import tokenizer_data
from legal_bench.mlx_json_constraint_v2 import CompositeQuoteEnforcer
from legal_bench.rules_verdict_v1.source_views import write_new
R=Path('outputs/json-constraint-diagnosis-v1')
t=AutoTokenizer.from_pretrained(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),local_files_only=True);data=tokenizer_data(t,t.eos_token_id)
schema={'type':'object','properties':{'point':{'type':'string'},'explanation':{'type':'string'}},'required':['point','explanation'],'additionalProperties':False}
sample=json.loads((R/'offline-audit.json').read_text())['fixture']['json'];ids=t.encode(sample,add_special_tokens=False);old=TokenEnforcer(data,JsonSchemaParser(schema));new=CompositeQuoteEnforcer(data,JsonSchemaParser(schema));recovered=[];invalid=[]
for i,tid in enumerate(ids):
 before=old.get_allowed_tokens(ids[:i]).allowed_tokens;after=new.get_allowed_tokens(ids[:i]).allowed_tokens
 if tid not in before and tid in after:recovered.append({'position':i,'token_id':tid,'text':t.decode([tid])})
 if tid not in after:invalid.append(i)
result={'inference_calls':0,'fixture':sample,'composite_quote_candidates':new.composite_count,'restored_legal_tokens':recovered,'invalid_tokens_after_fix':invalid,'eos_allowed_after_complete':t.eos_token_id in new.get_allowed_tokens(ids).allowed_tokens}
assert not invalid and result['eos_allowed_after_complete']
write_new(R/'offline-fix-audit.json',result);print(json.dumps(result,indent=2))
