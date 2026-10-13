"""Input-derived binding-specific queries and dependency-specific analysis, v2."""
import copy,json,hashlib
from .aligned_graph import build as build_v1,check_refs
from .aligned_anco import project,anco
from .aligned_logic import evaluate

def template_version(t):
 return t["template_id"]+"@"+hashlib.sha256(json.dumps(t,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:12]
def unit_id(case,claim,version,test,binding):
 return '|'.join((str(case),claim,version,test,binding))
def build(material,legacy,template,old_proposal,law,binding_proposal):
 from .graph_builder import reject_supervision
 reject_supervision(binding_proposal)
 g=build_v1(material,legacy,template,old_proposal,law);g['schema_version']='ALIGNED_V2_BINDING_GRAPH';sources=g['source_manifest'];byid={n['id']:n for n in g['nodes']};units=[];audit=[]
 for n in g['nodes']:
  if n['type']=='Test':n['type']='Rule' # original legal proposition remains, but is no longer a prediction query
  if n['origin']=='GIVEN_RULE_STRUCTURE':
   n['text']+='\nLEGAL_CONTEXT '+json.dumps({'scope':template['scope'],'coverage_limits':template['coverage_limits'],'coverage_status':n['features'].get('coverage_status'),'definition':next((x for k in ('claims','elements','tests','burdens','rules') for x in template[k] if x['id']==n['id']),{})},ensure_ascii=False,sort_keys=True)
 # All allowed source content is observable to both methods. No reference enters here.
 for sid,s in material['sources'].items():
  nid='ALLOWED::'+sid;g['nodes'].append(dict(id=nid,type='Evidence',text=s['text'],features={'semantic_stage':s['semantic_stage'],'source_status':'REPORTED_OPINION','coverage_status':'COVERED'},source_grounded=True,source_refs=[{'source_id':sid,'quote':s['text']}],origin='ALLOWED_SOURCE_RECORD',semantic_verified=False));byid[nid]=g['nodes'][-1]
 def edge(a,b,typ,refs):
  if a not in byid or b not in byid:return
  e={'source':a,'target':b,'type':typ,'source_refs':refs,'origin':'MODEL_PROPOSED_BINDING','semantic_verified':False};g['edges'] += [e,dict(e,source=b,target=a,type='INVERSE_'+typ,origin='COMPUTATIONAL_REVERSE')]
 links={l['id']:l for l in old_proposal['links']};viewlinks=[];bs=[];seen=set()
 for b0 in binding_proposal.get('bindings',[]):
  b=copy.deepcopy(b0);bid=b['binding_id'];errors=[]
  if bid in seen:raise ValueError('DUPLICATE_BINDING')
  seen.add(bid)
  errors+=check_refs(b.get('source_refs',[])+b.get('identity_refs',[]),sources)
  for o in b.get('objects',[]):errors+=check_refs(o.get('source_refs',[]),sources)
  if b.get('identity_status')=='ESTABLISHED' and not b.get('identity_refs'):errors.append('IDENTITY_WITHOUT_SOURCE')
  b['automatic_errors']=errors;bs.append(b)
  bn='BINDING::'+bid;node=dict(id=bn,type='Pattern',text=json.dumps(b,ensure_ascii=False,sort_keys=True),features={'source_status':'MODEL_PROPOSAL','coverage_status':'UNKNOWN','binding_status':b.get('identity_status'),'scope_status':b.get('scope_status')},source_refs=b.get('source_refs',[]),source_grounded=bool(b.get('source_refs')) and not errors,origin='INPUT_BINDING_NOT_LABEL',semantic_verified=False);g['nodes'].append(node);byid[bn]=node
  for ref in b.get('source_refs',[])+b.get('identity_refs',[]):edge('ALLOWED::'+ref['source_id'],bn,'EVIDENCE_RECORDS',[ref])
  for claim in b.get('claim_ids',[]):
   if claim not in {c['id'] for c in template['claims']}:audit.append({'binding_id':bid,'reason':'UNKNOWN_CLAIM'});continue
   for test in template['tests']:
    uid=unit_id(material['case_id'],claim,template_version(template),test['id'],bid)
    u={'id':uid,'case_id':str(material['case_id']),'claim_id':claim,'template_version':template_version(template),'test_id':test['id'],'binding_id':bid};units.append(u)
    n=dict(id=uid,type='Test',text=json.dumps({'proposition':test,'binding':b,'rule_scope':template['scope']},ensure_ascii=False,sort_keys=True),features={'polarity':test.get('polarity'),'source_status':test.get('source_status'),'coverage_status':test.get('coverage_status','COVERED' if test.get('source_refs') else 'NOT_COVERED'),'binding_status':b.get('identity_status'),'scope_status':b.get('scope_status')},source_refs=test['source_refs'],source_grounded=bool(test['source_refs']),origin='BINDING_TEST_QUERY',semantic_verified=False);g['nodes'].append(n);byid[uid]=n
    edge(test['id'],uid,'HAS_TEST',test['source_refs']);edge(bn,uid,'PATTERN_MEMBER',b.get('source_refs',[]))
    for lid in b.get('test_links',{}).get(test['id'],[]):
     l=links.get(lid)
     if not l or l['test_id']!=test['id'] or 'PROPOSAL::'+lid not in byid:audit.append({'unit_id':uid,'link':lid,'reason':'INVALID_OR_ISOLATED_LINK'});continue
     edge('PROPOSAL::'+lid,uid,'PROPOSED_'+l['direction'],l['source_refs']);viewlinks.append(dict(l,test_id=uid))
 g['binding_proposal']=binding_proposal;g['bindings']=bs;g['prediction_units']=units;g['v2_audit']=audit
 fids=sorted(n['id'] for n in g['nodes'] if n['type'] in ('Fact','Evidence','Pattern'));v=project(sorted(u['id'] for u in units),fids,viewlinks);a=anco(v['matrix'],n_columns=len(fids));g['anco_view']=v;g['anco']=a
 for n in g['nodes']:n.pop('anco',None)
 for ids,key in ((v['test_ids'],'x'),(v['instance_ids'],'y')):
  for i,nid in enumerate(ids):byid[nid]['anco']={'score':a[key][i] if a[key] is not None else 0.,'valid':a['status']=='CONVERGED','conflict':any(nid in (c['test_id'],c['instance_id']) for c in v['conflicts'])}
 return g

def applicable_restrictions(binding,test):
 return [r for r in binding.get('restrictions',[]) if not r.get('affected_tests') or test in r['affected_tests']]
def effective_state(binding,test,prediction,sources):
 status=prediction.get('status','UNRESOLVED');reasons=[];notes=[]
 for r in applicable_restrictions(binding,test):
  if r['kind']=='NOTE':notes.append(r);continue
  # A limitation of one cited witness does not invalidate other witnesses.
  if r.get('original_ids') and all(i.startswith('LINK:') for i in r['original_ids']) and not r.get('unmapped_scope'):
   notes.append(dict(r,application='LOCAL_LINK_LIMIT_NOT_WHOLE_TEST'));continue
  if r['kind']=='BINDING':continue # restrict the join, not standalone proposition prediction
  errors=check_refs(r.get('source_refs',[]),sources)
  reasons.append({'kind':r['kind'],'fields':r.get('fields',[]),'reason':r['reason'],'origin_ids':r.get('original_ids',[]),'address_errors':errors})
 if binding.get('scope_status')=='INCOMPATIBLE':status='UNSUPPORTED';reasons.append({'kind':'RULE_SCOPE','reason':'INCOMPATIBLE'})
 elif reasons:status='UNRESOLVED'
 return {'status':status,'blocking':reasons,'notes':notes,'prediction_not_proof':True}
def render(g,predictions):
 template=g['legal_structure'];sources=g['source_manifest'];defs={e['id']:e['expression'] for e in template['elements']};units=[];bindings=[]
 for b in g['bindings']:
  for c in template['claims']:
   if c['id'] not in b['claim_ids']:continue
   states={};join=[]
   if b.get('automatic_errors'):join.append({'kind':'SOURCE_ADDRESS','reason':b['automatic_errors']})
   if 'reviewed_join_limits' not in b and (b.get('identity_status')!='ESTABLISHED' or not b.get('identity_refs')):join.append({'kind':'BINDING','reason':b.get('identity_reason','MISSING_SOURCE_WITNESS')})
   if 'reviewed_join_limits' not in b and b.get('scope_status')!='COMPATIBLE':join.append({'kind':'RULE_SCOPE','reason':b.get('scope_reason')})
   for r in b.get('reviewed_join_limits',[]):
    if r['kind']!='NOTE':join.append(r)
   for r in b.get('restrictions',[]):
    if r['kind']=='BINDING' and not (r.get('original_ids') and all(i.startswith('LINK:') for i in r['original_ids'])):join.append({'kind':'BINDING','reason':r['reason'],'affected_tests':r.get('affected_tests',[])})
   for t in template['tests']:
    uid=unit_id(g['case_id'],c['id'],template_version(template),t['id'],b['binding_id']);p=predictions.get(uid,{'status':'UNRESOLVED','probabilities':None});state=effective_state(b,t['id'],p,sources);states[t['id']]=state
    units.append({'unit_id':uid,'binding_id':b['binding_id'],'claim_id':c['id'],'test_id':t['id'],'prediction':p,'program_state':state,'candidate_link_ids':b['test_links'].get(t['id'],[]),'source_semantics_verified':False})
   # Mark only affected tests as unavailable for joins; unrelated tests remain computable.
   joined=copy.deepcopy(states)
   for j in join:
    if j['kind']=='RULE_SCOPE' and not j.get('affected_tests'):continue # retain known test states; gate only legal application
    for tid in j.get('affected_tests') or list(joined):joined[tid]={'status':'UNRESOLVED','reason':j}
   els=[{'element_id':e['id'],'result':evaluate(e['expression'],joined,defs)} for e in template['elements']]
   result=evaluate(c['expression'],joined,defs)
   if any(j['kind']=='RULE_SCOPE' and not j.get('affected_tests') for j in join):result={'status':'UNRESOLVED','pre_scope_result':result,'reason':'RULE_SCOPE_NOT_CONFIRMED','scope_reason':b.get('scope_reason')}
   bindings.append({'binding_id':b['binding_id'],'claim_id':c['id'],'objects':b['objects'],'identity_refs':b['identity_refs'],'join_limits':join,'tests':joined,'elements':els,'result':result,'all_limits_removed':False})
 claims=[]
 for c in template['claims']:
  rows=[b for b in bindings if b['claim_id']==c['id']];ss=[b['result']['status'] for b in rows]
  status='SUPPORTED' if 'SUPPORTED' in ss else 'UNRESOLVED' if not ss or 'UNRESOLVED' in ss else 'UNSUPPORTED' if 'UNSUPPORTED' in ss else 'UNRESOLVED'
  claims.append({'claim_id':c['id'],'status':status,'binding_results':[{k:b[k] for k in ('binding_id','result')} for b in rows],'reason':'Existential support uses a complete bound expression; all enumerated bindings refuted does not prove exhaustive case absence.','burden_failure_inferred':False})
 return {'case_id':g['case_id'],'units':units,'bindings':bindings,'claims':claims,'burdens':template['burdens'],'scope':template['scope'],'coverage_limits':template['coverage_limits'],'attribution':'CANDIDATE_SOURCES_NOT_FAITHFUL_MODEL_EXPLANATION','historical_outcome_scored':False}
