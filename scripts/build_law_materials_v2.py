"""Build historical-text BM25 development indexes, retaining every scope exclusion."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.law_materials_v2 import units_from_judgment,eligible_units
from legal_bench.rules_verdict_v1.authority_index import build,search
from legal_bench.rules_verdict_v1.source_views import write_new

root=Path('outputs/rules-verdict-v2')
sample=json.loads((root/'protocol/sample.json').read_text())
dates={'661475':'1973-05-22','69305':'1989-08-08','1134266':'2004-08-13'}
units=[]
for c in sample['development']:
 source=json.loads(Path(c['source_path']).read_text())
 units.extend(units_from_judgment(source,dates[c['case_id']]))
write_new(root/'authorities/judgment-units.json',units)
query='tenant subletting assignment parting possession landlord consent writing appeal Delhi Rent Control Act'
results=[]
for cid in sample['format_check_cases']:
 eligible,excluded=eligible_units(units,cid,dates[cid])
 p=root/'authorities/indexes'/(cid+'.sqlite')
 manifest=build(eligible,p)
 ranking=search(p,query,limit=50) if eligible else []
 result={'target_case_id':cid,'target_date':dates[cid],'query':query,'query_origin':'TASK_ONLY_NOT_REFERENCE_OR_MODEL_OUTCOME','eligible_units':len(eligible),'excluded':excluded,'all_ranked_candidates':ranking,'selected_ids':[r['id'] for r in ranking[:8]],'method':'BM25_ONLY','scope':'THREE_EXPOSED_HISTORICAL_JUDGMENTS_NOT_COMPLETE_LEGAL_CORPUS','relevance_scored':False,'index_manifest':manifest}
 write_new(root/'runs/law-materials-v1/retrieval'/(cid+'.json'),result)
 results.append({'case_id':cid,'eligible_units':len(eligible),'ranked':len(ranking),'selected_ids':result['selected_ids']})
print(json.dumps(results,indent=2))
