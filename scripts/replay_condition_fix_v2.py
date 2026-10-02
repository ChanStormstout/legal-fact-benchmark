"""One affected-arm diagnostic replay after rejecting an invalid translation."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import write_new,digest
from legal_bench.rules_verdict_v1.runtime import Runner
from legal_bench.rules_verdict_v1.extract_v2 import answer_schema,at_string_limits
r=Path('outputs/rules-verdict-v2');old=r/'runs/legal-development-v1';out=r/'runs/legal-development-v2'
traces=json.loads((r/'runs/condition-diagnostic-v2/results.json').read_text())['results']
prompt=(old/'A2-prompt.txt').read_text()+'\nDETERMINISTIC CONDITION-TRANSLATION DIAGNOSTICS. No condition has an approved semantic translation. All are UNSUPPORTED; these results provide no negative evidence. Do not infer no lease from a deed not being registered. The local rule cards are unverified model interpretations: judge them from the same supplied historical sources.\n'+json.dumps(traces,ensure_ascii=False)
scope=json.loads((old/'output-scope.json').read_text());config=json.loads((r/'protocol/config-candidate.json').read_text())
write_new(out/'freeze.json',{'role':'SAME_EXPOSED_CASE_AFFECTED_ARM_REPLAY_AFTER_PROGRAM_TRANSLATION_FIX','max_new_calls':1,'same_sources_hash':digest(scope),'prompt_hash':digest(prompt.encode()),'reused_methods':{a:{'path':str(old/a),'raw_hash':digest((old/a/'raw-response.txt').read_bytes())} for a in ['A1','A2']},'reason':'Reject unreviewed predicate-hint compilation; unregistered lease is not a negative LEASE assertion.','no_model_or_reference_or_source_change':True,'code_hashes':{p:digest(Path(p).read_bytes()) for p in ['scripts/replay_condition_fix_v2.py','legal_bench/rules_verdict_v1/translation_gate_v2.py','legal_bench/rules_verdict_v1/runtime.py']}})
runner=Runner(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),config)
result=runner.run(prompt,answer_schema(scope),out/'A3',4096)
answer=json.loads((out/'A3/parsed.json').read_text()) if result['run_status']=='OK' else None
write_new(out/'complete.json',{'run_status':result['run_status'],'answer':answer,'string_caps':at_string_limits(answer,answer_schema(scope)) if answer else [],'whole_rule_execution':'UNSUPPORTED','whole_pipeline_validated':False,'A1_A2_reused_from':str(old)})
print(json.dumps(answer,ensure_ascii=False),flush=True)
