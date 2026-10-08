"""Import local input organization; prepare isolated binding-level references."""
import json,sys,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.irac_application.aligned_v2_runtime import atomic_json
from legal_bench.irac_application.aligned_v2 import build,unit_id
R=Path('outputs/gnn-irac-aligned-v2');O=Path('outputs/gnn-irac-aligned-v1')
def read(p):return json.loads(p.read_text())
REF='''Independent MATERIAL-SUPPORT reference task. Use only the full allowed sources, supplied law/template and neutral object arrangements below. No external search. You have not been given model predictions, proposed signed edges or prior reference labels. Do not predict the target historical verdict or require the target court to have discussed a proposition. Preserve prior court findings at their stated level without automatically accepting them as a final target determination. Distinguish party allegation, admission, denial, recorded document and prior finding. Evaluate each template test FOR EACH identified binding and claim, not the case as a whole. Distinct arrangements must not share a broadcast answer. Status SUPPORTED/REFUTED evaluates the literal test proposition, not eviction. A clearly supported lower-stage finding can support a proposition within that stage while retaining dispute/opposition. Explain evidence conflict and level. UNRESOLVED needs a specifically decisive factual, identity or interpretation gap; missing irrelevant information is not a reason. UNSUPPORTED is legal coverage or expressivity inadequacy, not an adverse label. If no reliable judgment can be formed use UNRATED. Do not manufacture negative evidence from absence or invent burden rules. Review all allowed material, not just the binding's cited passages; preserve meaningful opposing evidence. The neutral binding description is a fallible input-derived identification aid, not established truth. If it conflates objects or cannot be identified, flag that rather than accepting it. Return one complete JSON code block, no follow-up and no final full legal answer.
Contract: {"cases":[{"case_id":string,"tests":[{"claim_id":string,"binding_id":string,"test_id":string,"status":"SUPPORTED"|"REFUTED"|"UNRESOLVED"|"UNSUPPORTED"|"UNRATED","source_refs":[{"source_id":string,"quote":string}],"law_refs":[{"source_id":string,"quote":string}],"objects":string,"statement_status":string,"opposition":string,"opposition_refs":[{"source_id":string,"quote":string}],"gap_reason":string,"coverage_status":"COVERED"|"PARTIAL"|"NOT_COVERED","rationale":string}]}]}. Include every test exactly once per supplied binding/claim. Short exact quotes; quote must occur literally in the provided source. Empty evidence is permitted for genuine missing information, but explain what was searched. No missing fields, no ellipses. All answers are model-generated source-reviewed references, not human gold.
Complete fictional example: source X says 'The tenant admitted occupying Room R. The controller found no written permission.' Rule Y says 'Test T asks whether written permission exists.' Binding B1 is tenant/Room R. Output {"cases":[{"case_id":"DEMO","tests":[{"claim_id":"CLAIM","binding_id":"B1","test_id":"T","status":"REFUTED","source_refs":[{"source_id":"X","quote":"The controller found no written permission."}],"law_refs":[{"source_id":"Y","quote":"Test T asks whether written permission exists."}],"objects":"tenant; Room R","statement_status":"PRIOR_FOUND","opposition":"No contrary permission evidence supplied.","opposition_refs":[],"gap_reason":"","coverage_status":"COVERED","rationale":"The prior finding refutes the written-permission proposition at the supplied procedural level; it is not elevated to an unseen final ruling."}]}]}.
'''
def prepare():
 for f in sorted((R/'web').glob('input-[0-9][0-9].json')):
  batch=[]
  for c in read(f)['cases']:
   cid=str(c['case_id']);payload=read(R/'input-payloads'/f'{cid}.json');original={x['id'] for x in payload['old_limitations']};mapped={i for b in c['bindings'] for r in b['restrictions'] for i in r['original_ids']};unassigned={x['original_id'] for x in c['unassigned_limitations']};missing=sorted(original-mapped-unassigned)
   if missing: c=copy.deepcopy(c);c['import_unmapped_limitations']=missing
   # Keep raw unchanged. Missing mappings conservatively restrict the proposition,
   # but do not guess free-text meaning. Record this as an import dependency.
   derived=copy.deepcopy(c)
   for b in derived['bindings']:
    for item in missing+[x['original_id'] for x in c['unassigned_limitations']]:b['restrictions'].append({'original_ids':[item],'kind':'PROPOSITION','affected_tests':[],'fields':[],'unmapped_scope':True,'reason':'UNRESOLVED_LIMITATION_MAPPING:'+item,'source_refs':[]})
   for reviewfile in sorted((R/'web').glob('join-review-[0-9][0-9].json')):
    rc=next((x for x in read(reviewfile)['cases'] if str(x['case_id'])==cid),None)
    if not rc:continue
    reviewed={x['binding_id']:x for x in rc['bindings']}
    for b in derived['bindings']:
     if b['binding_id'] not in reviewed:continue
     v=reviewed[b['binding_id']];b['original_identity_scope']={k:b[k] for k in ('identity_status','identity_reason','identity_refs','scope_status','scope_reason')}
     for k in ('identity_status','identity_reason','identity_refs','scope_status','scope_reason'):b[k]=v[k]
     b['reviewed_join_limits']=v['join_limits'];b['dependency_review_source']=str(reviewfile);b['dependency_review_reason']=v['review_reason']
   atomic_json(R/'bindings'/f'{cid}.json',derived)
   g=build(read(R/'sources'/f'{cid}.json'),read(O/'inputs'/f'{cid}-legacy-facts.json'),payload['template'],payload['old_input_proposal'],payload['law'],derived)
   atomic_json(R/'graphs'/f'{cid}.json',g)
   neutral=[{'binding_id':b['binding_id'],'claim_ids':b['claim_ids'],'objects':b['objects']} for b in c['bindings']]
   batch.append({'case_id':cid,'allowed_sources':payload['allowed_sources'],'law':payload['law'],'template':payload['template'],'bindings':neutral})
  k=f.stem.replace('input','reference');dest=R/'tasks'/f'{k}.txt'
  if not dest.exists():dest.write_text(REF+'\n'+json.dumps({'cases':batch},ensure_ascii=False))
  print(f.stem,[(c['case_id'],len(c['bindings'])) for c in batch])
if __name__=='__main__':prepare()
