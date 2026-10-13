#!/usr/bin/env python3
"""One joint deterministic acceptance; no neural generation or reference edits."""
import copy,json,sys,time,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.proof_source_verification_v20 import OUT,save,text,read,fixture,sha
from legal_bench.proof_carrying import source_verification_v20 as m
from tests.test_source_verification_v20 import setup
from legal_bench.proof_carrying.source_verification_check_v20 import check

def main():
 result=subprocess.run([sys.executable,'-m','unittest','tests.test_source_verification_v20','tests.test_pipeline_diagnostic_v19_8','tests.test_final_capacity_v19_8_1','-q'],cwd=ROOT,text=True,capture_output=True)
 text(OUT/'engineering/tests.txt',result.stdout+result.stderr)
 if result.returncode:raise RuntimeError(result.stderr)
 from transformers import AutoTokenizer
 from legal_bench.mlx_json_constraint import tokenizer_data
 from legal_bench.mlx_json_constraint_v19_6 import SchemaMask
 tok=AutoTokenizer.from_pretrained((ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),local_files_only=True);data=tokenizer_data(tok,tok.eos_token_id)
 c,r,p,q=setup();sc=m.q_schema(r,c);mask=SchemaMask(data,sc);ids=tok.encode(m.compact(q),add_special_tokens=False);prefix=[]
 for i,token in enumerate(ids):
  if token not in mask.enforcer.get_allowed_tokens(prefix).allowed_tokens:raise ValueError('Q_TOKENIZER_BLOCKED:'+str(i))
  prefix.append(token)
 assert tok.eos_token_id in mask.enforcer.get_allowed_tokens(prefix).allowed_tokens
 save(OUT/'engineering/tokenizer-replay.json',{'status':'PASS','tokens':len(ids),'EOS_allowed':True,'model_loaded':False,'model_calls':0})
 replays=[]
 for cid,pid in [('1954254','P01'),('1187427','P02')]:
  f=fixture(cid);path=ROOT/'outputs/proof-pipeline-contract-v19-7/runs'/cid/pid/'parsed.json';raw=read(path)
  rules=[r for r in f['rules'] if any(p['id'] in raw['analyses'] for p in r['premises'])]
  empty={'analyses':{k:{'analysis_status':'NOT_ANALYZED','records':[],'objects':[],'uses':[],'judgments':[],'limits':[]} for k in raw['analyses']},'object_links':[],'coverage_limits':[]}
  # Mechanical identity passthrough control, NOT a new semantic reference.
  q={'supplement':empty,'verdicts':[{'declaration':d['id'],'label':'SUPPORTED','refs':d['refs'][:1],'counter_refs':[],'reason':'DETERMINISTIC_PASSTHROUGH_CONTROL_NOT_A_SEMANTIC_LABEL'} for d in m.declarations(raw,'P',rules)],'coverage_limits':[]}
  x=m.apply(f['case'],rules,raw,q);assert check(raw,q,x,rules)['status']=='OK'
  save(OUT/'engineering/replay'/cid/'passthrough-control.json',x)
  replays.append({'case_id':cid,'old_P_hash':sha(path),'control':'ALL_DECLARATIONS_SUPPORTED_IS_SYNTHETIC_NOT_MODEL_RESULT','records_retained':len(x['canonical']['records']),'routes':len(x['audit']['conditional_rules']),'labels_for_training':False})
 save(OUT/'engineering/cache-replay.json',replays)
 save(OUT/'engineering/acceptance.json',{'status':'PASS','scope':'SOURCE_ADDRESSES_LOCAL_APPLICATION_FEATURE_VISIBILITY_FINAL_ENTRY_AND_SAVING','tests_log':'engineering/tests.txt','tokenizer':'engineering/tokenizer-replay.json','cache_replays':replays,'semantic_success':False,'model_calls':0})
 print('ACCEPTANCE PASS')
if __name__=='__main__':main()
