"""Lossless raw-proposal adapter. No reference, labels or semantic repair.
Compound evidence remains an explicit bundle, never a fabricated quotation.
"""
from itertools import product
from .contracts import content_hash

def adapt(case,proposal):
 if not isinstance(proposal,dict) or any(not isinstance(proposal.get(k),list) for k in ('facts','rules','uses','targets')):
  raise ValueError('UNREADABLE_PROPOSAL_INTERFACE')
 sources={s['id']:{**s,'document':s['source_document'],'document_role':'TARGET'} for s in case['segments']}
 facts={};rules={};contracts={};quarantine=[];premise_index={}
 for f in proposal['facts']:
  if not isinstance(f,dict) or not f.get('id') or f['id'] in facts:
   quarantine.append({'kind':'FACT_ID','record':f});continue
  facts[f['id']]={**f,'bindings':[{'role':k,'entity':v} for k,v in f.get('bindings',{}).items()]}
 for r in proposal['rules']:
  try:
   rr=r['id']+'@'+str(r['version'])
   if rr in rules:raise ValueError('DUPLICATE_RULE')
   slots=[];mapping={}
   for p in r['premises']:
    if p['id'] in premise_index:raise ValueError('DUPLICATE_PREMISE_ID')
    slots.append({'name':p['id'],'predicate':p['text'],'allowed_statuses':p['allowed_statuses'],'expected':p.get('expected','TRUE')})
    mapping[p['id']]=p['variables']
   # Exceptions are executable only when explicitly named as premise IDs.
   exceptions=r.get('exceptions',[])
   valid_exceptions=all(isinstance(e,str) and e in mapping for e in exceptions)
   rule={'id':r['id'],'version':r['version'],'description':r['description'],'refs':r['source_refs'],'quote':r['source_quote'],'operator':r['operator'] if valid_exceptions else 'OPEN_TEXT','slots':slots,'conclusion_predicate':r['conclusion'],'exception_slots':exceptions if valid_exceptions else [],'jurisdiction':r.get('jurisdiction'),'stage':r.get('stage'),'limits':r.get('limits',[]),'raw_exceptions':exceptions}
   rules[rr]=rule;contracts[rr]={'rule_hash':content_hash(rule),'slot_variables':mapping}
   for p in r['premises']:premise_index[p['id']]=(rr,p)
  except (KeyError,TypeError,ValueError) as e:quarantine.append({'kind':'RULE_INTERFACE','record':r,'error':str(e)})
 uses={};byrule={};alluses={}
 for u in proposal['uses']:
  try:
   if u['id'] in alluses:raise ValueError('DUPLICATE_USE')
   alluses[u['id']]=u
   rr,p=premise_index[u['rule_premise']]
   if not isinstance(u['bindings'],dict) or not isinstance(u['evidence_ids'],list) or not u['evidence_ids']:raise ValueError('USE_INTERFACE')
   if any(i not in facts for i in u['evidence_ids']):raise ValueError('DANGLING_EVIDENCE')
   byrule.setdefault(rr,{}).setdefault(p['id'],[]).append(u)
  except (KeyError,TypeError,ValueError) as e:quarantine.append({'kind':'USE_INTERFACE','record':u,'error':str(e)})
 candidates=[];adapter_limits=[]
 # Uses can join only on explicitly supplied rule-variable bindings. Unknown is not equal.
 for rr,r in rules.items():
  pools=[byrule.get(rr,{}).get(s['name'],[None]) for s in r['slots']]
  count=0
  for combo in product(*pools):
   if count>=10000:adapter_limits.append({'rule_ref':rr,'kind':'CANDIDATE_CONSTRUCTION_INCOMPLETE'});break
   count+=1;binding={};conflict=False
   for u in combo:
    if not u:continue
    for var,val in u['bindings'].items():
     if val is not None and binding.get(var) is not None and binding[var]!=val:conflict=True
     elif val is not None:binding[var]=val
   if conflict:continue
   cid='C-'+content_hash({'rule':rr,'uses':[u['id'] if u else None for u in combo]})[:24];inputs=[]
   for slot,u in zip(r['slots'],combo):
    name=slot['name']
    if not u:
     deps=[key for key,other in rules.items() if other['conclusion_predicate']==slot['predicate']]
     # Exact proposition only. Ambiguous multiple rule alternatives remain unformalized.
     inputs.append({'slot':name,'kind':'RULE_DEPENDENCY' if len(deps)==1 else 'MISSING','id':deps[0] if len(deps)==1 else ''});continue
    ids=u['evidence_ids'];kind='PREMISE' if len(ids)==1 else 'BUNDLE'
    inputs.append({'slot':name,'kind':kind,'id':ids[0] if len(ids)==1 else 'BUNDLE-'+content_hash(ids)[:24],**({'evidence_ids':ids} if len(ids)>1 else {})})
    uses[cid+'::'+name]={'label':u['use_judgment'],'premise_state':u['premise_state'],'premise_judgment_basis':u['basis'],'raw_use_id':u['id'],'opposition':u.get('opposition',[]),'gaps':u.get('gaps',[])}
   candidates.append({'id':cid,'rule_ref':rr,'bindings':[{'role':k,'entity':v} for k,v in sorted(binding.items())],'inputs':inputs})
 requests=[]
 for target in proposal['targets']:
  if target.get('id') not in {q['id'] for q in case['targets']}:quarantine.append({'kind':'UNKNOWN_TARGET','record':target});continue
  for rid in target.get('rule_ids',[]):
   for rr,r in rules.items():
    if r['id']==rid:requests.append({'id':target['id']+'::'+rid,'predicate':r['conclusion_predicate'],'target_id':target['id'],'model_limited_conclusion':target.get('limited_conclusion')})
 snapshot={'case_id':case['case_id'],'premises':facts,'rules':rules,'contracts':contracts,'sources':sources,'model_uses':uses,'relations':proposal.get('relations',[]),'coverage_limits':proposal.get('coverage_limits',[])+adapter_limits,'entities':[],'quarantine':quarantine,'raw_proposal':proposal,'missing_targets':[q['id'] for q in case['targets'] if q['id'] not in {x['target_id'] for x in requests}],'input_track':'RAW_MODEL_PROPOSALS_NO_REFERENCE'}
 return snapshot,candidates,requests
