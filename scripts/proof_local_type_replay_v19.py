#!/usr/bin/env python3
"""Frozen cached-P replay for shared type contract. No generation or references."""
import collections,json,sys,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts import proof_local_types_v19 as entry
from legal_bench.proof_carrying import local_pipeline_v19_repair as prior
from legal_bench.proof_carrying import local_pipeline_v19_types as pipe
from legal_bench.proof_carrying.local_checker_v19_types import check
PARENT=ROOT/'outputs/proof-local-pipeline-v19/continuation-01'
read,save=entry.read,entry.save

def replay():
 result=[];rows=[];unmapped=collections.Counter();mapped_conflicts=collections.Counter()
 for path in sorted((PARENT/'local').glob('*/P/merged.json')):
  cid=path.parents[1].name;p=read(path)['answer'];f=read(PARENT/'preparation/inputs'/cid/'fixture.json')
  if p is None:continue
  old=read(path.parent/'offline-audit.json');new=pipe.apply_connection_decisions(f['case'],f['rules'],p);ind=check(f['case'],f['rules'],p,None,new)
  if ind['status']!='OK':raise ValueError('INDEPENDENT_CHECK:'+cid+':'+str(ind['errors']))
  items=[]
  for a,b in zip(old['checks'],new['checks']):
   type_rows=b['type_compatibility'];pending=any(t['status']=='UNMAPPED_DESCRIPTION' for t in type_rows);conflict=any(t['status']=='EXPLICIT_TYPE_CONFLICT' for t in type_rows)
   had='OBJECT_TYPE_MISMATCH' in a['errors']
   status='STILL_REJECTED' if b['errors'] else 'TYPE_UNRESOLVED_CONNECTION_RETAINED' if pending else 'RESTORED_COMPATIBLE' if had else 'UNCHANGED_MAPPED'
   for t in type_rows:
    pair=(str(t['actual']['raw']),str(t['expected']['raw']))
    if t['status']=='UNMAPPED_DESCRIPTION':unmapped[pair]+=1
    if t['status']=='EXPLICIT_TYPE_CONFLICT':mapped_conflicts[pair]+=1
   row={'case_id':cid,'connection':b['connection_id'],'classification':status,'old_type_rejection':had,'type_pending':pending,'confirmed_type_conflict':conflict,'old_disposition':a['disposition'],'new_disposition':b['disposition'],'old_errors':a['errors'],'new_errors':b['errors'],'type_compatibility':type_rows,'old_full_basis':a['full_basis_eligible'],'new_full_basis':b['full_basis_eligible'],'P_label':b['P_label'],'no_reference_used':True,'semantic_correctness_not_proved':True}
   items.append(row);rows.append(row)
  save(entry.OUT/'replay'/cid/'before.json',old);save(entry.OUT/'replay'/cid/'after.json',new);save(entry.OUT/'replay'/cid/'independent.json',ind);save(entry.OUT/'replay'/cid/'connections.json',items)
  data=pipe.learner_inputs(f['case'],f['rules'],p);save(entry.OUT/'inputs'/cid/'learner-inputs.json',data)
  result.append({'case_id':cid,'uses':len(items),'classification':dict(collections.Counter(x['classification'] for x in items)), 'old_structurally_valid':sum(not x['errors'] for x in old['checks']),'new_structurally_valid':sum(not x['errors'] for x in new['checks']),'old_available':sum(x['disposition']=='CONDITIONALLY_AVAILABLE_USE' for x in old['checks']),'new_available':sum(x['disposition']=='CONDITIONALLY_AVAILABLE_USE' for x in new['checks']),'old_premise_states':dict(collections.Counter(x['conditional_state'] for x in old['premise_judgments'])),'new_premise_states':dict(collections.Counter(x['conditional_state'] for x in new['premise_judgments'])),'old_rule_states':dict(collections.Counter(x['conditional_result'] for x in old['conditional_rules'])),'new_rule_states':dict(collections.Counter(x['conditional_result'] for x in new['conditional_rules'])),'cached_P_sha256':entry.sha(path),'new_input_sha256':entry.sha(entry.OUT/'inputs'/cid/'learner-inputs.json'),'independent_status':ind['status']})
 save(entry.OUT/'replay-summary.json',{'cases':result,'connections':len(rows),'classification':dict(collections.Counter(x['classification'] for x in rows)), 'old_exact_type_rejections':sum(x['old_type_rejection'] for x in rows),'recovered_from_type_rejection':dict(collections.Counter(x['classification'] for x in rows if x['old_type_rejection'])),'unmapped_pairs':[{'actual':a,'expected':b,'count':n} for (a,b),n in sorted(unmapped.items())],'explicit_conflict_pairs':[{'actual':a,'expected':b,'count':n} for (a,b),n in sorted(mapped_conflicts.items())],'model_gain':False,'legal_analysis_success':False,'references_used':False})
 print(json.dumps({'cases':len(result),'connections':len(rows),'classification':dict(collections.Counter(x['classification'] for x in rows))}))
if __name__=='__main__':
 if '--coverage' in sys.argv:
  from scripts import proof_local_replay_v19_repair as encoder_audit
  encoder_audit.OUT=entry.OUT
  encoder_audit.cached_coverage()
 else:replay()
