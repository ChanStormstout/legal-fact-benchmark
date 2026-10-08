"""Local source-address and unit admission; never repairs semantic content."""
import json,sys,collections,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.irac_application.aligned_v2_runtime import atomic_json
from legal_bench.irac_application.aligned_graph import check_refs
from legal_bench.irac_application.aligned_v2 import unit_id,template_version
R=Path('outputs/gnn-irac-aligned-v2');STATES=['SUPPORTED','REFUTED','UNRESOLVED']
def read(p):return json.loads(p.read_text())
def main():
 totals=collections.Counter()
 for f in sorted((R/'web').glob('reference-[0-9][0-9].json')):
  for c in read(f)['cases']:
   cid=str(c['case_id']);g=read(R/'graphs'/f'{cid}.json');sources=g['source_manifest'];expected={u['id']:u for u in g['prediction_units']};rows={};duplicates=set()
   for item in c['tests']:
    uid=unit_id(cid,item.get('claim_id',''),template_version(g['legal_structure']),item.get('test_id',''),item.get('binding_id',''))
    if uid in rows:duplicates.add(uid)
    rows[uid]=item
   out=[]
   for uid,u in expected.items():
    row=copy.deepcopy(rows.get(uid,{}));errors=[]
    if not row:errors.append('MISSING_REFERENCE')
    if uid in duplicates:errors.append('DUPLICATE_REFERENCE')
    for k in ['source_refs','law_refs','opposition_refs']:errors+=check_refs(row.get(k,[]),sources)
    if row.get('status') not in STATES:errors.append('UNRATED_OR_UNSUPPORTED')
    if row.get('status') in STATES[:2] and not row.get('source_refs'):errors.append('DEFINITE_WITHOUT_CASE_SOURCE')
    if row.get('status')=='UNRESOLVED' and not row.get('gap_reason'):errors.append('UNKNOWN_WITHOUT_KEY_GAP')
    row.update(unit_id=uid,supervision_mask=not errors,admission_errors=errors,reference_role='MODEL_GENERATED_SOURCE_REVIEW_NOT_HUMAN_GOLD',semantic_certification=False);out.append(row);totals['all_units']+=1;totals['admitted' if not errors else 'masked']+=1
    if not errors:totals[row['status']]+=1
   atomic_json(R/'references'/f'{cid}.json',{'case_id':cid,'tests':out,'unexpected_units':sorted(set(rows)-set(expected)),'raw_path':str(f),'old_case_labels_broadcast':False})
 atomic_json(R/'reference-admission.json',dict(totals));print(dict(totals))
if __name__=='__main__':main()
