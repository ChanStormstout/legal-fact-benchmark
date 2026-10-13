#!/usr/bin/env python3
"""Deterministic pinned tokenizer/constraint replay, never loads or runs an LLM."""
import copy,json,sys,time,importlib.metadata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import proof_local_refs_v19 as entry
from tests.test_reference_addresses_v19 import typed_fixture
from legal_bench.proof_carrying import local_pipeline_v19_refs as pipe

def run():
    from legal_bench.mlx_json_constraint import tokenizer_data
    from legal_bench.mlx_json_constraint_v2 import SchemaMask
    t=time.perf_counter();tok=entry.tokenizer();eos=tok.eos_token_id;data=tokenizer_data(tok,eos)
    c,r,x=typed_fixture();u=x['analyses'][0]
    u['uses'].append(copy.deepcopy(u['uses'][0]));u['uses'][1]['direction']='OPPOSE'
    u['judgments'][0]['uses']=['USE:1','USE:2'];u['judgments'][0]['opposition_uses']=['USE:2']
    u['judgments'][0]['necessary_limits']=[{'kind':'NOTE','component':'COMP:1','reason':'Synthetic explanation, not a blocker.','refs':[u['records'][0]['refs'][0]]},{'kind':'STAGE_SCOPE','component':'WHOLE_JUDGMENT','reason':'Attributed trial finding only.','refs':[]}]
    schema=pipe.schema(r,c);pipe.validate(x,schema)
    cases=[('legal_full_JSON',x,True)]
    for name,value in [('source_in_record','SRC:1'),('bare_integer',1),('zero_ordinal','EV:0'),('object_in_record','OBJ:1'),('use_in_record','USE:1')]:
        z=copy.deepcopy(x);z['analyses'][0]['uses'][0]['records']=[value];cases.append((name,z,False))
    z=copy.deepcopy(x);z['analyses'][0]['uses'][0]['records']=['EV:999'];cases.append(('syntactically_legal_dynamic_missing_import_rejects',z,True))
    receipts=[]
    for name,value,expected in cases:
        text=json.dumps(value,separators=(',',':'));ids=tok.encode(text,add_special_tokens=False)
        mask=SchemaMask(data,schema);prefix=[];blocked=None
        for i,token in enumerate(ids):
            if token not in mask.enforcer.get_allowed_tokens(prefix).allowed_tokens:
                blocked={'position':i,'token_id':token,'text':tok.decode([token]),'prefix_tail':tok.decode(prefix[-24:])};break
            prefix.append(token)
        ending=False
        if blocked is None:
            allowed=mask.enforcer.get_allowed_tokens(prefix).allowed_tokens
            ending=any(e in allowed for e in (eos if isinstance(eos,list) else [eos]))
        ok=blocked is None and ending
        if ok!=expected:raise ValueError('DETERMINISTIC_CONSTRAINT_REPLAY_MISMATCH:'+name+':'+str(blocked))
        receipts.append({'name':name,'token_count':len(ids),'expected_acceptance':expected,'complete_JSON_and_EOS_allowed':ok,'rejected_at':blocked,'model_called':False})
    record={'status':'PASS','model_generation_calls':0,'model_loaded':False,'tokenizer_revision':entry.read(entry.ROOT/'outputs/proof-local-pipeline-v19/continuation-02/freeze/protocol.json')['local_model']['revision'],'constraint_version':importlib.metadata.version('lm-format-enforcer'),'constraint':'actual runtime SchemaMask/CompositeQuoteEnforcer','receipts':receipts,'dynamic_reference_existence_is_import_only':True,'elapsed_seconds':time.perf_counter()-t}
    entry.save(entry.OUT/'engineering/tokenizer-constraint-replay.json',record)
    print(json.dumps(record,indent=2))

if __name__=='__main__':run()
