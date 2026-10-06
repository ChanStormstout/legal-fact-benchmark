"""Freeze stage-reviewed immutable records; no semantic repair or target reads."""
import sys,json,datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.irac_gate_v2 import admit_record,ALLOWED
from irac02_prepare import R,OLD,IDS,rd,put,sha
reviews={c['case_id']:c for n in ['S-1','S-2'] for c in rd(R/'web'/f'{n}.raw.json')['cases']}
for cid in IDS:
 cand=rd(R/'stage-candidates'/f'{cid}.json');rev=reviews[cid];rs={x['record_id']:x for x in rev['records']};expected={x['record_id'] for x in cand['records']};assert expected==set(rs) and len(rs)==len(rev['records']),(cid,'coverage')
 for g in rs.values():assert g['input_allowed']==(g['semantic_stage'] in ALLOWED),g
 sg={k.split('source:',1)[1]:v for k,v in rs.items() if k.startswith('source:')};inv=rd(OLD/'inputs'/f'{cid}.json')['existing_inventory'];admitted={};exclusions=[]
 for kind in ['facts','objects','relations']:
  admitted[kind]=[]
  for rec in inv[kind]:
   value,errors=admit_record(rec,rs[kind+':'+rec['id']],sg)
   if errors:exclusions.append({'record_id':kind+':'+rec['id'],'errors':errors})
   else:admitted[kind].append(value)
 src=rd(OLD/'inputs'/f'{cid}.json')['pre_outcome_source'];admitted['sources']=[{'id':s['id'],'text':s['text'],'source_document':s['source_document']} for s in src['segments'] if sg[s['id']]['input_allowed']]
 # Raw graph record admission is audited separately; no legacy flags copied to input.
 graph_audit=[]
 for r in cand['records']:
  original=r['original'] if isinstance(r['original'],dict) else {};original=original.get('record',original)
  if r['record_id'].startswith('graph-') or r['record_id']=='metadata':
   _,errors=admit_record(original,rs[r['record_id']],sg);graph_audit.append({'record_id':r['record_id'],'input_allowed':not errors,'errors':errors})
 out={'case_id':cid,'records':rev['records'],'review_gaps':rev.get('gaps',[]),'source_gate_exclusions':exclusions,'graph_gate_audit':graph_audit,'admitted_inventory':admitted,'facts_unmodified':True,'source_review_not_human_gold':True};put('stage-partition/'+cid+'.json',out)
 print(cid,'facts',len(admitted['facts']),'relations',len(admitted['relations']),'excluded',len(exclusions),'sources',len(admitted['sources']))
put('stage-partition-freeze.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':{str(R/'stage-partition'/f'{c}.json'):sha(R/'stage-partition'/f'{c}.json') for c in IDS},'raw_review_hashes':{str(R/'web'/f'{n}.raw.json'):sha(R/'web'/f'{n}.raw.json') for n in ['S-1','S-2']},'binding_not_yet_generated':True,'policy_sha256':sha(R/'stage-policy.json')})
