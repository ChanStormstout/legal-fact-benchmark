"""Partial model-proposed facts and provenance-carrying candidate joins, never verdicts."""
import itertools,json,collections
from .contracts import obj,array,enum,nullable,validate
S=lambda:{'type':'string'}
STATUS=['NARRATED','COURT_FOUND','PARTY_CLAIMED','UNKNOWN']
ROLE_FIELDS={'tenancies':['tenant','landlord','premises'],'transfers':['event','transferor','recipient','premises'],'times':['event'],'consents':['grantor','target','recipient','premises']}
CATEGORIES=list(ROLE_FIELDS)

def refs_schema(ids):return array(enum(ids),4)
def notes_schema(ids):
 return obj({'notes':array(obj({'id':S(),'kind':enum(['SUPPORT','OPPOSITION','RULE_SCOPE','LINK','UNCERTAINTY']),'point':S(),'refs':refs_schema(ids)}),6),'coverage_limits':S()})
def fact_schema(ids):
 refs=refs_schema(ids);mention=nullable(obj({'text':S(),'refs':refs}))
 def row(fields):return obj({'id':S(),**fields,'status':enum(STATUS),'uncertain':array(S(),6),'refs':refs})
 roles=lambda cat:{k:mention for k in ROLE_FIELDS[cat]}
 return obj({'tenancies':array(row({**roles('tenancies'),'value':enum(['YES','NO','UNKNOWN'])}),3),
  'transfers':array(row({**roles('transfers'),'mode':enum(['SUBLET','ASSIGN','PART_WITH_POSSESSION','NONE','UNKNOWN'])}),3),
  'times':array(row({**roles('times'),'event_date':nullable(S()),'after_threshold':enum(['YES','NO','UNKNOWN'])}),3),
  'consents':array(row({**roles('consents'),'form':enum(['WRITTEN','ORAL','UNKNOWN']),'polarity':enum(['YES','NO','UNKNOWN'])}),3),
  'links':array(obj({'left':S(),'right':S(),'relation':enum(['SAME','DIFFERENT','UNKNOWN']),'status':enum(STATUS),'refs':refs}),6),
  'coverage_limits':S()})
def final_schema(ids):
 evidence=obj({'statement':S(),'refs':refs_schema(ids)})
 return obj({'outcome':enum(['SUPPORT_GROUND','OPPOSE_GROUND','UNDETERMINED','UNSUPPORTED']),
  'decisive_facts':array(obj({'statement':S(),'objects':array(S(),4),'status':enum(STATUS),'refs':refs_schema(ids)}),4),
  'rules':array(obj({'rule_id':S(),'scope_and_application':S(),'refs':refs_schema(ids)}),3),
  'support':array(evidence,3),'opposition':array(evidence,3),
  'gaps':obj({'case_facts':array(S(),4),'law_coverage':array(S(),4),'program_coverage':array(S(),4)}),
  'reason':S(),'intermediate_use':S()})

def check_facts(data,source):
 """Source-address recovery, local fields and proposed joins. No semantic certification."""
 validate(data,fact_schema([s['id'] for s in source['segments']]))
 source_map={s['id']:s['text'] for s in source['segments']};restored={};records={};roles={};checks=[]
 counts=collections.Counter(f['id'] for cat in CATEGORIES for f in data[cat])
 def refs_ok(refs):
  for sid in refs:
   if sid in source_map:restored[sid]=source_map[sid]
  return bool(refs) and all(s in source_map for s in refs)
 for cat in CATEGORIES:
  for f in data[cat]:
   known=refs_ok(f['refs']);issue=[]
   if counts[f['id']]!=1:issue.append('DUPLICATE_FACT_ID')
   if not known:issue.append('MISSING_OR_INVALID_SOURCE_ADDRESS')
   rs={}
   for k in ROLE_FIELDS[cat]:
    m=f[k];address=bool(m and refs_ok(m['refs']));anchor=bool(address and m['text'] and any(m['text'] in source_map[s] for s in m['refs']))
    rs[k]={'state':'CANDIDATE_SOURCE_MENTION' if anchor else 'UNRESOLVED','proposal':m}
    if counts[f['id']]==1:roles[f['id']+'.'+k]=rs[k]
   prop='value' if cat=='tenancies' else 'mode' if cat=='transfers' else 'after_threshold' if cat=='times' else 'polarity'
   blockers=list(issue)
   allowed_uncertainty=set(ROLE_FIELDS[cat])|{'proposition','status','binding',prop,'event_date','form'}
   if set(f['uncertain'])-allowed_uncertainty:blockers.append('UNKNOWN_UNCERTAINTY_SCOPE')
   if f['status'] not in ['NARRATED','COURT_FOUND']:blockers.append('UNACCEPTED_OR_UNKNOWN_STATEMENT_STATUS')
   if any(x in f['uncertain'] for x in ['proposition','status',prop]):blockers.append('PROPOSITION_OR_VALUE_UNCERTAIN')
   if f[prop]=='UNKNOWN':blockers.append('VALUE_UNKNOWN')
   if cat=='consents' and (f['form']!='WRITTEN' or 'form' in f['uncertain']):blockers.append('WRITTEN_SCOPE_NOT_ESTABLISHED')
   for k in ROLE_FIELDS[cat]:
    if k in f['uncertain'] or 'binding' in f['uncertain']:rs[k]['state']='UNRESOLVED'
   # This signal is what the proposed statement says, not that it is true.
   positive=f[prop]=='NO' if cat=='consents' else f[prop] in (['SUBLET','ASSIGN','PART_WITH_POSSESSION'] if cat=='transfers' else ['YES'])
   signal='UNRESOLVED' if blockers else 'PROPOSED_SUPPORT' if positive else 'PROPOSED_OPPOSITION'
   row={'id':f['id'],'category':cat,'signal':signal,'blockers':blockers,'roles':rs,'source_refs':f['refs'],'epistemic_status':'MODEL_PROPOSED_NOT_VERIFIED'}
   checks.append(row)
   if counts[f['id']]==1:records[f['id']]=row
 link_checks=[]
 for l in data['links']:
  located=refs_ok(l['refs']);valid=l['left'] in roles and l['right'] in roles and located
  link_checks.append({**l,'structural_state':'ADDRESSED_MODEL_PROPOSAL' if valid else 'UNRESOLVED_REFERENCE','semantic_verification':False})
 join_trace=[]
 def original_join(left,right):
  a,b=roles.get(left),roles.get(right)
  if not a or not b or a['state']=='UNRESOLVED' or b['state']=='UNRESOLVED':return {'state':'UNRESOLVED','basis':'MISSING_OR_UNCERTAIN_MENTION'}
  relevant=[l for l in link_checks if {l['left'],l['right']}=={left,right} and l['structural_state']=='ADDRESSED_MODEL_PROPOSAL' and l['status'] in ['NARRATED','COURT_FOUND']]
  values={l['relation'] for l in relevant}
  if 'SAME' in values and 'DIFFERENT' in values:return {'state':'UNRESOLVED','basis':'CONFLICTING_MODEL_LINKS','links':relevant}
  if 'DIFFERENT' in values:return {'state':'PROPOSED_DIFFERENT','basis':'SOURCE_ADDRESSED_MODEL_LINK','links':relevant}
  if 'SAME' in values:return {'state':'PROPOSED_SAME','basis':'SOURCE_ADDRESSED_MODEL_LINK','links':relevant}
  if 'UNKNOWN' in values:return {'state':'UNRESOLVED','basis':'MODEL_LINK_UNRESOLVED'}
  ma,mb=a['proposal'],b['proposal'];shared=set(ma['refs'])&set(mb['refs'])
  # Same paragraph or ID alone never licenses a join. A unique exact mention is only a candidate.
  anchors=[s for s in sorted(shared) if ma['text']==mb['text'] and ma['text'] and source_map[s].count(ma['text'])==1]
  if anchors:return {'state':'PROPOSED_SAME','basis':'SAME_UNIQUE_SOURCE_MENTION_CANDIDATE','refs':anchors}
  return {'state':'UNRESOLVED','basis':'NO_SOURCE_ADDRESSED_COREFERENCE'}
 def join(left,right):
  result=original_join(left,right)
  join_trace.append({'left':left,'right':right,'result':result})
  return result
 pair_checks=[]
 for t in data['tenancies']:
  for x in data['transfers']:
   joins=[join(t['id']+'.tenant',x['id']+'.transferor'),join(t['id']+'.premises',x['id']+'.premises')]
   pair_checks.append({'facts':[t['id'],x['id']],'kind':'TENANCY_TRANSFER','joins':joins})
 # Candidate full combinations only, not legal effects; missing values never match.
 combination_trace=[];complete=[];complete_count=0;combination_count=0;unresolved_count=0;opposed_count=0
 for t,x,d,c in itertools.product(*(data[k] for k in CATEGORIES)):
  combination_count+=1
  pairs=[(t['id']+'.tenant',x['id']+'.transferor'),(t['id']+'.premises',x['id']+'.premises'),(d['id']+'.event',x['id']+'.event'),(c['id']+'.target',x['id']+'.event'),(c['id']+'.grantor',t['id']+'.landlord'),(c['id']+'.recipient',x['id']+'.recipient'),(c['id']+'.premises',x['id']+'.premises')]
  js=[join(a,b) for a,b in pairs];rs=[records.get(f['id'],{}) for f in [t,x,d,c]]
  trace={'facts':[f['id'] for f in [t,x,d,c]],'joins':js,'condition_signals':[r.get('signal') for r in rs]}
  if any(j['state']=='PROPOSED_DIFFERENT' for j in js) or any(r.get('signal')=='PROPOSED_OPPOSITION' for r in rs):
   opposed_count+=1;trace['state']='OPPOSED_PROPOSED_COMBINATION'
  elif all(j['state']=='PROPOSED_SAME' for j in js) and all(r.get('signal')=='PROPOSED_SUPPORT' for r in rs):
   trace['state']='COMPLETE_MODEL_PROPOSED_COMBINATION_NOT_LEGAL_CONCLUSION'
   complete_count+=1
   if len(complete)<4:complete.append({'facts':[f['id'] for f in [t,x,d,c]],'joins':js,'status':'COMPLETE_MODEL_PROPOSED_COMBINATION_NOT_LEGAL_CONCLUSION'})
  else:
   unresolved_count+=1;trace['state']='UNRESOLVED_PROPOSED_COMBINATION'
  combination_trace.append(trace)
 result={'all_join_trace':join_trace,'all_combination_trace':combination_trace,'record_checks':checks,'link_checks':link_checks,'tenancy_transfer_checks':pair_checks,
   'combination_counts':{'enumerated':combination_count,'complete_model_proposed':complete_count,'unresolved':unresolved_count,'opposed_candidates_not_whole_case_negatives':opposed_count},
   'complete_proposed_combinations':complete,'display_cap_complete':4,
   'rule_configuration':'RESEARCHER_CONFIGURED_BASE_CONDITION_TRANSLATION_NOT_LEARNED_RULE; NO_RULE_ID_GATE',
   'coverage_limits':['Source existence and exact mention do not establish meaning or co-reference.','Model statement status and threshold classification may be wrong; date arithmetic is not independently verified.','Document admissibility, corporate succession, statutory version and exceptions are not executed.','Empty combinations are not absence in reality.'],
   'model_coverage_limits':data['coverage_limits'],'final_legal_conclusion':None}
 return result,restored
