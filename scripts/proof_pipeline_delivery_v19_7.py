#!/usr/bin/env python3
"""Post-batch material assembly and descriptive counts; no model calls."""
import json,sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import proof_pipeline_contract_v19_7 as e
from legal_bench.proof_carrying import local_pipeline_v19_7 as p
from legal_bench.proof_carrying.local_checker_v19_6 import _typed
from legal_bench.proof_carrying.reference_addresses_v19 import audit as references
from legal_bench.proof_carrying.rule_contracts_v19_7 import digest

def run():
 cfg=e.read(e.OUT/'freeze/protocol.json');rows=[];source_maps=[];finals=[]
 for t in cfg['tasks']:
  f,part=e.context(t);view={**f['case'],'segments':[s for s in f['case']['segments'] if s['id'] in part['source_ids']]}
  pair=[]
  for version,root in [('V19_6',e.OLD),('V19_7',e.OUT)]:
   d=root/'runs'/t['case_id']/t['part'];a=e.read(d/'entry-audit.json');raw=e.read(d/'parsed.json');run=e.read(d/'run.json')
   rs=references(_typed(raw,'V19_6'),view,'V19_4')
   bad=[x for x in rs if x['namespace'] in ['EV','OBJ','USE'] and x['status']!='VALID']
   pair.append({'production_version':version,'run_status':run['run_status'],'input_tokens':run['usage']['prompt_tokens'],
     'output_tokens':run['usage']['completion_tokens'],'elapsed_seconds':run['elapsed_seconds'],
     'listed_price_token_cost_usd':run['listed_price_token_cost_usd'],
     'contract_status':a['contract_status'],'analyzed':len([u for u in raw['analyses'].values() if u['analysis_status']=='ANALYZED']),
     'explicit_not_analyzed':a['coverage']['explicit_not_analyzed'],'missing_analysis':a['coverage']['missing'],
     'raw_dynamic_invalid_fields':len(bad),'invalid_namespace_counts':dict(Counter(z['namespace'] for z in bad)),
     'raw_invalid_refs':bad,'records_retained':len(a['canonical_P']['records']),
     'uses':dict(Counter(z['disposition'] for z in a['conditional_audit']['checks'])),
     'missing_role_judgments':sum(bool(z['missing_roles']) for z in a['role_coverage']),
     'declared_types':dict(Counter(z['status'] for u in a['conditional_audit']['checks'] for z in u['type_compatibility'])),
     'model_states':dict(Counter(j['state'] for u in raw['analyses'].values() for j in u['judgments'])),
     'conditional_states':dict(Counter(j['conditional_state'] for j in a['conditional_audit']['premise_judgments'])),
     'raw_object_links':len(raw['object_links']),
     'encoding_status':a['learner_inputs']['common_material_manifest']['encoding_status'],
     'semantic_score_not_computed':True})
  rows.append({'case_id':t['case_id'],'part':t['part'],'versions':pair,'not_same_raw_P_and_not_independent_test':True})
  a=e.read(e.OUT/'runs'/t['case_id']/t['part']/'entry-audit.json')
  source_maps.append({'case_id':t['case_id'],'raw_to_conditional':[{'judgment_id':j['id'],'premise':j['premise'],
    'model_state':j['model_state'],'conditional_state':j['conditional_state'],'errors':j['errors'],
    'unapproved_semantics':True,'components':j['components'],'binding':j['binding'],
    'necessary_limits':j['necessary_limits']} for j in a['conditional_audit']['premise_judgments']],
    'rules':a['conditional_audit']['conditional_rules'],'enumeration_coverage':a['conditional_audit']['rule_coverage']})
  # Full real-case source and original complete law pack are assembled after P.
  # No generated final answer is claimed; E/F/G require actual new predictions.
  for method in ['A','C','D']:
   task=p.final_task(f['case'],f['rules'],a,method,full_rules=f['full_rules'])
   dest=e.OUT/'engineering/final-fixture'/t['case_id']/method
   e.save(dest/'task.json',task);e.text(dest/'prompt.txt',task['prompt']);e.save(dest/'schema.json',task['schema'])
   finals.append({'case_id':t['case_id'],'method':method,'input_sha256':task['input_sha256'],
      'complete_case_segments':len(task['source_ids']),'original_full_rules':len(f['full_rules']),
      'proposal_rules_in_checks':len(f['rules']),'prompt_characters':len(task['prompt']),
      'new_version_actual_assembly':True,'LLM_final_generated':False})
 e.save(e.OUT/'comparison.json',{'cases':rows,'scope':'Two exposed P development tasks; descriptive counts, not legal-accuracy estimate'})
 e.save(e.OUT/'source-to-conditional-trace.json',source_maps)
 e.save(e.OUT/'full-pipeline-delivery.json',{'version':p.VERSION,'actual_real_P_generations':2,
   'real_final_preparation':finals,'A_G_saved_final_entry_acceptance':'MOCKED_RUNNER_ONLY',
   'learner_encoding':'NOT_RUN','training':0,'new_final_answers':0,
   'E_F_G_future_predictions_require_current_version_and_input_hash':True})
 e.save(e.OUT/'cost-summary.json',{'calls':2,'retries':0,'new_input_tokens':sum(r['versions'][1]['input_tokens'] for r in rows),
    'new_output_tokens':sum(r['versions'][1]['output_tokens'] for r in rows),
    'new_observed_generation_seconds':sum(r['versions'][1]['elapsed_seconds'] for r in rows),
    'new_listed_price_token_cost_usd':sum(r['versions'][1]['listed_price_token_cost_usd'] for r in rows),
    'old_generation_seconds':sum(r['versions'][0]['elapsed_seconds'] for r in rows),
    'old_listed_price_token_cost_usd':sum(r['versions'][0]['listed_price_token_cost_usd'] for r in rows),
    'actual_invoice_not_retrieved':True,'local_generation':0,'web_review':0,'training':0,'final_LLM':0})
 assert all(e.sha(ROOT/n)==h for n,h in cfg['code_hashes'].items())
 assert all(e.sha(ROOT/n)==h for n,h in cfg['preserved_hashes'].items())
 assert all(e.sha(ROOT/n)==h for n,h in cfg['contract_hashes'].items())
 e.save(e.OUT/'preservation.json',{'code_hashes':len(cfg['code_hashes']),'preserved_files':len(cfg['preserved_hashes']),
    'rule_contracts':len(cfg['contract_hashes']),'all_unchanged':True,'reporting_script_sha256':e.sha(Path(__file__))})
 print(json.dumps({'cases':rows,'final_preparations':finals,'cost':e.read(e.OUT/'cost-summary.json')},ensure_ascii=False))
if __name__=='__main__':run()
