import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.runtime import Runner
from legal_bench.rules_verdict_v1.rule_extract_v2 import schema,prompt
from legal_bench.rules_verdict_v1.source_views import write_new,digest
root=Path('outputs/rules-verdict-v2')
# Selected by chronological availability, before inspecting target method results.
cid='69305';source=json.loads(Path('outputs/local-qwen-pattern-eval-v3/sources/69305.json').read_text())
conf=json.loads((root/'protocol/config-candidate.json').read_text())
files=['legal_bench/rules_verdict_v1/rule_extract_v2.py','legal_bench/rules_verdict_v1/runtime.py','legal_bench/rules_verdict_v1/contracts.py','scripts/extract_historical_rules_v2.py']
write_new(root/'freeze/rule-extraction-v1.json',{'files':{p:digest(Path(p).read_bytes()) for p in files},'source_case':cid,'source_hash':digest(source),'target_outputs_included':False,'max_calls':1,'max_cards':3,'max_tokens':4096})
runner=Runner(Path('outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),conf)
result=runner.run(prompt(source),schema(source),root/'runs/rule-extraction-v1/69305',4096)
print(json.dumps(result,ensure_ascii=False),flush=True)
