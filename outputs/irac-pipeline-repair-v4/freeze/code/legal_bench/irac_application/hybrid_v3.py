"""Evidence-use checks, independent of historical identifiers or learned probabilities."""
import copy, json, re
from .aligned_logic import evaluate

STATES=('SUPPORTED','REFUTED','UNRESOLVED','UNSUPPORTED')

def branches(template):
 t=copy.deepcopy(template)
 for test in t['tests']:
  if test['id']=='DRC_BONA_FIDE-C03':
   refs=test['source_refs']; base=test['id']
   test['branches']=[{'id':base+'/SELF','text':'Occupation by the landlord himself.','source_refs':refs},
    {'id':base+'/FAMILY','text':'Occupation by a member of the landlord family.','source_refs':refs},
    {'id':base+'/DEPENDENT','text':'That family member is dependent on the landlord.','source_refs':refs}]
   test['branch_expression']={'op':'OR','args':[{'op':'REF','id':base+'/SELF','source_refs':refs},{'op':'AND','args':[{'op':'REF','id':base+'/FAMILY','source_refs':refs},{'op':'REF','id':base+'/DEPENDENT','source_refs':refs}],'source_refs':refs}],'source_refs':refs}
   test['branch_origin']='RESEARCHER_EXPANSION_OF_GIVEN_TEXT; not case-specific; ownership remains separate'
 return t

def para(s):
 # Address normalization only; not a semantic judgment or document boundary parser.
 m=re.match(r'(IK-[^:]+:L\d+)',s)
 return m.group(1) if m else s

def source_errors(refs,sources,case_id=None):
 errors=[]
 for sid in refs:
  if sid not in sources:errors.append({'source_id':sid,'reason':'MISSING_ADDRESS'});continue
  doc=sources[sid].get('document_id')
  if case_id and sid.startswith('IK-'+str(case_id)+':') and str(doc)!=str(case_id):errors.append({'source_id':sid,'reason':'DOCUMENT_ID_MISMATCH'})
 return errors

def analyze(proposal,template,sources,case_id):
 """Actual pipeline entry: never infer meaning from free text or LINK/COMBO names."""
 bindings={b['id']:b for b in proposal['bindings']}; tests={t['id']:t for t in template['tests']}
 traces=[]; audit=[]; restored={}; limits=proposal['limitations']; evidence=proposal['evidence']
 duplicate_ids=[e['id'] for e in evidence if sum(x['id']==e['id'] for x in evidence)>1]
 for e in evidence:
  errors=source_errors(e['refs'],sources,case_id)
  b=bindings.get(e['binding_id']);binding_errors=[]
  if b is None:binding_errors.append('UNKNOWN_BINDING')
  elif not b['refs'] or source_errors(b['refs'],sources,case_id):binding_errors.append('BINDING_WITHOUT_VALID_SOURCE_ADDRESS')
  if not e['refs']:errors.append({'reason':'NO_SOURCE'})
  if e['id'] in duplicate_ids:errors.append({'reason':'DUPLICATE_EVIDENCE_ID'})
  for sid in e['refs']:
   if sid in sources:restored[sid]=sources[sid]
  for u in e['uses']:
   known=u['test_id'] in tests
   legal_branches=[x['id'] for x in tests.get(u['test_id'],{}).get('branches',[])]
   if u['branch_id'] and u['branch_id'] not in legal_branches:known=False
   blocked=[];unmapped=[];notes=[]
   for l in limits:
    if l['binding_id']!=e['binding_id'] or l['test_id']!=u['test_id']:continue
    if l['branch_id']!=u['branch_id']:continue
    if l['use']!=u['use']:continue
    if l['evidence_ids'] and e['id'] not in l['evidence_ids']:continue
    if l['effect']=='NOTE':notes.append(l['id']);continue
    if l['effect']=='SCOPE_UNMAPPED' or (not l['evidence_ids'] and l['effect']!='PROPOSITION_BLOCK'):
     unmapped.append(l['id']);continue
    if source_errors(l['refs'],sources,case_id):unmapped.append(l['id']);continue
    blocked.append(l['id'])
   # Prior findings may support a stage-qualified analysis; they never certify target acceptance.
   if e['statement_status']=='PRIOR_COURT_FINDING' and u['use']=='TARGET_ACCEPTANCE':blocked.append('PRIOR_FINDING_NOT_TARGET_ACCEPTANCE')
   if e['statement_status'] in ('PARTY_CLAIM','DENIAL','TESTIMONY','UNKNOWN') and u['use']=='PROVEN_FACT':blocked.append('STATEMENT_NOT_ESTABLISHED_FACT')
   if not known:blocked.append('UNKNOWN_TEST_OR_BRANCH')
   if errors or binding_errors:blocked.append('INVALID_ADDRESS_OR_BINDING')
   status='BLOCKED' if blocked else 'UNRESOLVED_MAPPING' if unmapped else 'USABLE_AS_MODEL_PROPOSED'
   traces.append({'evidence_id':e['id'],'binding_id':e['binding_id'],'test_id':u['test_id'],'branch_id':u['branch_id'],'use':u['use'],'direction':u['direction'],'statement_status':e['statement_status'],'record_retained':e['record'],'refs':e['refs'],'record_address_valid':not errors,'address_errors':errors+binding_errors,'use_status':status,'blocked_by':blocked,'mapping_questions':unmapped,'notes':notes,'independence_group':sorted(set(para(s) for s in e['refs'])),'semantic_truth_verified':False})
 for l in limits:
  if not any(l['id'] in x['blocked_by']+x['mapping_questions']+x['notes'] for x in traces):audit.append({'limitation_id':l['id'],'reason':'NO_MATCHING_DECLARED_USE; retained, not applied globally'})
 rows=[];conditions=[]
 for bid,b in bindings.items():
  states={};branch_results={}
  for tid,t in tests.items():
   keys=[v['id'] for v in t.get('branches',[])] or ['']
   local={}
   for branch in keys:
    uses=[x for x in traces if x['binding_id']==bid and x['test_id']==tid and x['branch_id']==branch and x['use'] in ('CONDITION_INFERENCE','PROVEN_FACT')]
    usable=[x for x in uses if x['use_status']=='USABLE_AS_MODEL_PROPOSED']
    signs={x['direction'] for x in usable}; conflict='SUPPORT' in signs and 'OPPOSE' in signs
    state='UNRESOLVED' if conflict or not (signs&{'SUPPORT','OPPOSE'}) else 'SUPPORTED' if 'SUPPORT' in signs else 'REFUTED'
    local[branch or tid]={'status':state,'supports':[x['evidence_id'] for x in usable if x['direction']=='SUPPORT'],'opposes':[x['evidence_id'] for x in usable if x['direction']=='OPPOSE'],'conflict':conflict,'pending_uses':[x['evidence_id'] for x in uses if x['use_status']!='USABLE_AS_MODEL_PROPOSED' or x['direction']=='UNKNOWN'],'basis':'DECLARED_USE_ONLY_NOT_VERIFIED_PROOF; no majority vote; shared paragraphs not independent votes'}
   result=evaluate(t['branch_expression'],local) if t.get('branch_expression') else local[tid]
   if t.get('branch_expression'):branch_results[tid]=local
   states[tid]=result
   declared=[x for x in proposal['conditions'] if x['binding_id']==bid and x['test_id']==tid]
   conditions.append({'binding_id':bid,'test_id':tid,'model_predictions':declared,'program_assessment':result,'branches':local if t.get('branches') else {},'prediction_not_overwritten':True})
  defs={x['id']:x['expression'] for x in template['elements']}
  rows.append({'binding_id':bid,'event':b['event'],'objects':b['objects'],'stage':b['stage'],'tests':states,'branches':branch_results,'claims':[{'claim_id':c['id'],'result':evaluate(c['expression'],states,defs)} for c in template['claims'] if c['id'] in b['claim_ids']]})
 return {'case_id':str(case_id),'evidence_use_checks':traces,'conditions':conditions,'bindings':rows,'unapplied_limits':audit,'source_recovery':restored,'coverage_limits':template['coverage_limits']+proposal['coverage_limits'],'burdens':template['burdens'],'scope':template['scope'],'legal_truth_verified':False,'scope_of_checks':'Source addresses and declared within-binding uses/boolean combinations only; no claim of semantic or identity proof. UNKNOWN is not negative; no burden failure inferred.'}

def compact(checks):
 # Proposal already appears once in model input; trace never silently filters opposition.
 return {k:v for k,v in checks.items() if k not in ('source_recovery',)}

def legacy_replay(g,predictions):
 """Do not invent missing witness attribution, branch labels, or binary GNN scores."""
 from .aligned_v2 import render
 old=render(g,predictions); template=branches(g['legal_structure']);links={x['id']:x for x in g['proposal']['links']};by={b['binding_id']:b for b in g['bindings']}
 units=[]
 for u in old['units']:
  b=by[u['binding_id']];tid=u['test_id'];records=[]
  restrictions=b.get('restrictions',[])+b.get('reviewed_join_limits',[])
  for lid in b.get('test_links',{}).get(tid,[]):
   l=links.get(lid)
   if not l:continue
   refparas={para(x['source_id']) for x in l['source_refs'] if x['source_id'].startswith('IK-'+str(g['case_id'])+':')}
   limited=[];unmapped=[];notes=[]
   for r in restrictions:
    if r.get('affected_tests') and tid not in r['affected_tests']:continue
    if r['kind']=='NOTE':notes.append(r);continue
    rparas={para(x['source_id']) for x in r.get('source_refs',[]) if x['source_id'].startswith('IK-'+str(g['case_id'])+':')}
    if not rparas:unmapped.append(r)
    elif refparas&rparas:limited.append(r)
   records.append({'link_id':lid,'record':l['proposition'],'direction':l['direction'],'source_refs':l['source_refs'],'record_retained':True,'target_acceptance_inferred':False,'limitations_for_this_source_use':limited,'unmapped_limits':unmapped,'notes':notes,'use_assessment':'LEGACY_USE_DETAIL_UNAVAILABLE' if limited or unmapped else 'CANDIDATE_USE_RETAINED_NOT_VERIFIED'})
  # GNN probabilities survive unchanged. In v2 they had no per-witness/branch prediction.
  raw=u['prediction']; isbranch=any(t['id']==tid and t.get('branches') for t in template['tests'])
  units.append({'unit_id':u['unit_id'],'test_id':tid,'binding_id':u['binding_id'],'claim_id':u['claim_id'],'raw_prediction':raw,'v2_program_state':u['program_state'],'v3_prediction_preserved':raw,'evidence_records':records,'restriction_application':'SOURCE_USE_AUDIT_ONLY; no ID prefix controls effect','replay_status':'BRANCH_DETAIL_UNAVAILABLE' if isbranch else 'WITNESS_ATTRIBUTION_UNAVAILABLE','branch_predictions':None,'v3_proof_state':'UNRESOLVED','reason':'Old aggregate prediction is not an attributed evidence assessment; retain it without claiming new proof.'})
 return {'case_id':g['case_id'],'units':units,'old_claims':old['claims'],'new_claims':[{'claim_id':c['id'],'status':'UNRESOLVED','reason':'LEGACY_WITNESS_OR_BRANCH_DETAIL_UNAVAILABLE; no invented sublabels'} for c in template['claims']],'legal_structure':template,'new_model_calls':0,'probabilities_changed':False}
