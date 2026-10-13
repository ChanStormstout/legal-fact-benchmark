#!/usr/bin/env python3
"""Concentrated recovery entry acceptance, using deterministic stream fixtures only."""
import copy,hashlib,json,sys,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import proof_local_comparison_v18_recovery as entry
from legal_bench.proof_carrying import local_pipeline_v18_recovery as pipe
from legal_bench.proof_carrying.local_annotation_v18_recovery import CONTRACT,label_admissibility
from legal_bench.proof_carrying.local_runtime_v18_recovery import Runner,SETTINGS
from legal_bench.proof_carrying.local_checker_v18 import check
from tests.test_local_comparison_v18 import fixture


def main():
 old=entry.BASE/'continuation-01';out=entry.OUT;results=[]
 c,r,p=fixture();a=pipe.apply_connection_decisions(c,r,p)
 assert a['conditional_rules'][0]['conditional_result']=='TRUE' and check(r,a)['traces'][0]['status']=='CONDITIONAL_TRACE_RECOMPUTED'
 p2=copy.deepcopy(p);p2['premises'][0]['complete']=False
 assert pipe.apply_connection_decisions(c,r,p2)['conditional_rules'][0]['conditional_result']=='UNKNOWN'
 p3=copy.deepcopy(p);p3['uses'].append(copy.deepcopy(p['uses'][0]));p3['uses'][1]['bindings'][0]['object']=999;p3['premises'][0]['uses']=[1,2]
 assert pipe.apply_connection_decisions(c,r,p3)['conditional_rules'][0]['conditional_result']=='TRUE'
 assert pipe.apply_connection_decisions(c,r,p,{'K001':'UNSUPPORTED'})['conditional_rules'][0]['conditional_result']=='UNKNOWN'
 results.append('use prediction changes downstream availability; not truth; invalid alternative local')
 label={'connection_id':'K001','label':'UNSUPPORTED','basis':'Wrong object; this is a clear rejection, not interpretive dispute.','refs':['S1','SUPPLEMENT'],'quote':'text','mandatory_basis_refs':['S1'],'dispute':False,'input_coverage_limited':False,'outside_packet_dependencies':[]}
 assert label_admissibility(label,{'S1'},{})['supervised']
 for change,reason in [({'dispute':True},'GENUINE_REFERENCE_DISPUTE_RETAINED'),({'mandatory_basis_refs':['SUPPLEMENT']},'INDISPENSABLE_INPUT_COVERAGE_LIMITED'),({'outside_packet_dependencies':['X']},'INDISPENSABLE_INPUT_COVERAGE_LIMITED')]:
  assert label_admissibility({**label,**change},{'S1'},{})['reason']==reason
 legacy=copy.deepcopy(label);legacy.pop('mandatory_basis_refs')
 assert not label_admissibility(legacy,{'S1'},{})['supervised']
 results.append('clear negative retained; supplementary references tolerated; essential gaps/disputes/ambiguous legacy not guessed')
 # Real model tokenizer and repaired constraint constructor, no weights/model forward pass.
 tok=entry.tokenizer();from legal_bench.mlx_json_constraint import tokenizer_data
 runner=Runner.__new__(Runner);runner.settings=dict(SETTINGS);runner.tokenizer=tok
 runner.constraint_data=tokenizer_data(tok,getattr(tok,'eos_token_ids',tok.eos_token_id))
 runner.loaded_seconds=0;runner.versions={'deterministic_entry_fixture':True};runner.model_config_hash='fixture-not-model-run'
 runner.model=types.SimpleNamespace();runner.processor=tok
 runner.render=lambda s:entry.render(tok,s)
 raw=pipe.compact_json(p);ids=tok.encode(raw,add_special_tokens=False);captured=[]
 import importlib
 module=importlib.import_module('mlx_vlm.generate');original=module.stream_generate
 def stream(*args,**kwargs):
  captured.append({k:v for k,v in kwargs.items() if k!='logits_processors'})
  assert kwargs['max_tokens']==16384 and kwargs['enable_thinking'] is False and len(kwargs['logits_processors'])==1
  yield types.SimpleNamespace(text=raw,token_ids=ids,token=None,generation_tokens=len(ids),prompt_tokens=24,finish_reason='stop')
 module.stream_generate=stream
 try:
  dest=out/'engineering/synthetic-entry-results';res=runner.run('Synthetic deterministic entry fixture.',pipe.schema(r),dest,16384,1,'FIXED')
  assert res['run_status']=='OK' and res['effective_max_tokens']==16384 and res['settings']['total_budget']==65536
  assert res['required_total_tokens']==res['prompt_tokens']+16384+256
  assert (dest/'token-ids.json').exists() and (dest/'raw-response.txt').exists()
 finally:module.stream_generate=original
 results.append('actual Runner.run sees 65536/context,16384/output, unchanged mask/guard and saves result; stream mocked, no LLM call')
 # Existing source encoding certificate reused because semantic graph/CE/E5 implementations unchanged.
 certificate=entry.read(old/'engineering/integration-acceptance.json');assert certificate['status']=='PASS'
 cov=entry.read(old/'engineering/actual-encoding/coverage-audit.json');assert cov['status']=='PASS'
 real=entry.fixture('396336')['case'];segment=real['segments'][0]
 p['records'][0].update(text=segment['text'],refs=[segment['id']]);p['objects'][0].update(refs=[segment['id']]);p['uses'][0]['witnesses'][0].update(refs=[segment['id']],quote=segment['text'][:100])
 data=pipe.learner_inputs(real,r,p);assert segment['text'] in data['ce_pairs'][0]['right']
 assert segment['text'] in data['graph']['nodes'][-2]['text'] or any(segment['text'] in n['text'] for n in data['graph']['nodes'])
 assert data['relation_counts']['SUPPORT']==1
 results.append('real source present in all-method graph and CE inputs; prior actual encoding certificate reused')
 entry.save(out/'freeze/annotation-contract.json',CONTRACT)
 entry.save(out/'engineering/integration-acceptance.json',{'status':'PASS','checks':results,'old34_checks_and_tokenizer_certificate_reused':True,'prior_certificate_path':str((old/'engineering/integration-acceptance.json').relative_to(ROOT)),'sha256':entry.sha(old/'engineering/integration-acceptance.json'),'new_generation_calls':0,'new_training':0,'legal_semantics_proved':False,'deterministic_entry_stream':True})
 print('RECOVERY_ACTUAL_ENTRY_PASS')
if __name__=='__main__':main()
