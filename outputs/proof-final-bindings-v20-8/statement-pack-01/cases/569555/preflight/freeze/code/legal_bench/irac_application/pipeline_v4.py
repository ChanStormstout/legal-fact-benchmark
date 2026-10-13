"""Sparse proposal import, exact address catalogue, reversible display, declared-use checks."""
import copy,json,hashlib
from collections import Counter
from .hybrid_v3 import analyze as declared_checks,source_errors,para

def catalogue(template):
 return {t['id']:[b['id'] for b in t.get('branches',[])] or [''] for t in template['tests']}
def address_ok(x,cat):return x.get('test_id') in cat and x.get('branch_id') in cat[x['test_id']]
def digest(x):return hashlib.sha256(x.encode()).hexdigest()

def display(material):
 """Remove exact text containment ONLY inside same document/parent line; preserve aliases/ranges."""
 sources=material['sources']; mapping={};chosen=[]
 for sid,s in sources.items():
  matches=[(oid,o) for oid,o in sources.items() if o.get('document_id')==s.get('document_id') and para(oid)==para(sid) and s['text'] in o['text']]
  oid,o=sorted(matches,key=lambda z:(-len(z[1]['text']),z[0]))[0]
  start=o['text'].index(s['text']);mapping[sid]={'display_id':oid,'char_range':[start,start+len(s['text'])],'parent_address':para(sid),'original_text_sha256':digest(s['text'])}
  if oid not in chosen:chosen.append(oid)
 rows=[]
 for oid in chosen:
  s=sources[oid];rows.append({'source_id':oid,'aliases':{k:v['char_range'] for k,v in mapping.items() if v['display_id']==oid and k!=oid},'document_id':s['document_id'],'stage':s.get('semantic_stage'),'text':s['text']})
 return {'case_id':material['case_id'],'target_stage':material['target_stage'],'target_court':material['target_court'],'records':rows},mapping

def import_proposal(value,template,sources,cid):
 cat=catalogue(template);q=[];missing=[];out={'bindings':[],'evidence':[],'limitations':[],'conditions':[],'coverage_limits':[]}
 def reject(kind,i,record,why):q.append({'kind':kind,'position':i,'record':copy.deepcopy(record),'reason':why})
 if not isinstance(value,dict) or not isinstance(value.get('bindings'),list) or not isinstance(value.get('evidence'),list):
  return {'status':'STRUCTURE_ERROR','usable':False,'raw_proposal':value,'quarantine':[],'missing':[],'projection':out}
 claims={c['id'] for c in template['claims'] if c.get('expression',{}).get('op')!='UNSUPPORTED'}
 bidcounts=Counter(b.get('id') for b in value['bindings'] if isinstance(b,dict) and isinstance(b.get('id'),str))
 def refsvalid(refs):return isinstance(refs,list) and bool(refs) and all(isinstance(r,str) for r in refs) and not source_errors(refs,sources,cid)
 for i,b in enumerate(value['bindings']):
  if not isinstance(b,dict) or not all(isinstance(b.get(k),str) for k in ['id','objects','event','stage']) or bidcounts[b['id']]!=1 or not refsvalid(b.get('refs')) or not isinstance(b.get('claim_ids'),list) or not b['claim_ids'] or not set(b['claim_ids'])<=claims:
   reject('binding',i,b,'INVALID_BINDING_STRUCTURE_SOURCE_OR_CLAIM');continue
  out['bindings'].append(copy.deepcopy(b))
 bids={b['id'] for b in out['bindings']};eids=Counter(e.get('id') for e in value['evidence'] if isinstance(e,dict) and isinstance(e.get('id'),str))
 for i,e in enumerate(value['evidence']):
  if not isinstance(e,dict) or not all(isinstance(e.get(k),str) for k in ['id','binding_id','record','statement_status']) or eids[e['id']]!=1 or e['binding_id'] not in bids or not refsvalid(e.get('refs')) or e['statement_status'] not in ['PARTY_CLAIM','DENIAL','ADMISSION','TESTIMONY','PRIOR_COURT_FINDING','RECORDED_DOCUMENT','UNKNOWN'] or not isinstance(e.get('uses'),list):
   reject('evidence',i,e,'INVALID_RECORD_STRUCTURE_SOURCE_OR_BINDING');continue
  retained=copy.deepcopy(e);retained['uses']=[]
  for j,u in enumerate(e['uses']):
   if not isinstance(u,dict) or not address_ok(u,cat) or u.get('direction') not in ['SUPPORT','OPPOSE','UNKNOWN'] or u.get('use') not in ['CONDITION_INFERENCE','RECORD_EXISTENCE','PROVEN_FACT','TARGET_ACCEPTANCE']:
    reject('use',f'{i}/{j}',u,'INVALID_TEST_BRANCH_OR_USE; parent record retained');continue
   retained['uses'].append(copy.deepcopy(u))
  out['evidence'].append(retained)
 valid_e={e['id'] for e in out['evidence']}
 for kind in ['conditions','limitations']:
  values=value.get(kind,[])
  if not isinstance(values,list):reject(kind,None,values,'INVALID_ARRAY');continue
  for i,x in enumerate(values):
   valid=isinstance(x,dict) and address_ok(x,cat) and x.get('binding_id') in bids and isinstance(x.get('evidence_ids'),list) and set(x['evidence_ids'])<=valid_e and all(e['binding_id']==x['binding_id'] for e in out['evidence'] if e['id'] in x['evidence_ids'])
   if kind=='conditions':valid=valid and x.get('assessment') in ['SUPPORTED','REFUTED','UNRESOLVED','UNSUPPORTED'] and isinstance(x.get('gap'),str)
   else:valid=valid and isinstance(x.get('id'),str) and refsvalid(x.get('refs')) and x.get('effect') in ['USE_BLOCK','PROPOSITION_BLOCK','NOTE','SCOPE_UNMAPPED'] and x.get('use') in ['CONDITION_INFERENCE','RECORD_EXISTENCE','PROVEN_FACT','TARGET_ACCEPTANCE'] and isinstance(x.get('reason'),str)
   if not valid:
    reject(kind,i,x,'INVALID_LOCAL_STRUCTURE_ADDRESS_OR_REFERENCE')
    # A malformed restriction must not silently release a matching declared use.
    if kind=='limitations' and isinstance(x,dict) and x.get('effect')!='NOTE':
     for e in out['evidence']:
      if e['binding_id']!=x.get('binding_id') or not isinstance(x.get('evidence_ids'),list) or e['id'] not in x['evidence_ids']:continue
      for u in e['uses']:
       if u['test_id']==x.get('test_id') and u['branch_id']==x.get('branch_id') and u['use']==x.get('use'):
        out['limitations'].append({'id':f'import-unmapped-{i}-{e["id"]}','evidence_ids':[e['id']],'binding_id':e['binding_id'],'test_id':u['test_id'],'branch_id':u['branch_id'],'use':u['use'],'effect':'SCOPE_UNMAPPED','reason':'Importer could not validate declared restriction; no semantic repair.','refs':[]})
    continue
   # Legacy binary predictions are retained only in raw_proposal, never converted into evidence states.
   fields=['binding_id','test_id','branch_id','assessment','evidence_ids','gap'] if kind=='conditions' else ['id','evidence_ids','binding_id','test_id','branch_id','use','effect','reason','refs']
   out[kind].append({k:copy.deepcopy(x[k]) for k in fields})
 out['coverage_limits']=[x for x in value.get('coverage_limits',[]) if isinstance(x,str)] if isinstance(value.get('coverage_limits',[]),list) else []
 for b in out['bindings']:
  for tid,branches in cat.items():
   for branch in branches:
    if not any(x['binding_id']==b['id'] and x['test_id']==tid and x['branch_id']==branch for x in out['conditions']):
     missing.append({'binding_id':b['id'],'test_id':tid,'branch_id':branch,'status':'NOT_PRODUCED','reason':'No valid model condition row; not a model UNKNOWN or negative judgment.'})
 usable=bool(out['bindings'] and (out['evidence'] or out['conditions']))
 return {'status':'PARTIAL' if usable and (q or missing) else 'OK' if usable else 'NO_USABLE_PROPOSAL','usable':usable,'raw_proposal':value,'projection':out,'quarantine':q,'missing':missing,'catalogue':cat,'semantic_certification':False}

def process(value,template,sources,cid):
 imp=import_proposal(value,template,sources,cid)
 if not imp['usable']:return imp,None
 checks=declared_checks(imp['projection'],template,sources,cid)
 checks['import_missing']=imp['missing'];checks['import_quarantine']=imp['quarantine']
 for c in checks['conditions']:
  c['model_assessments']=c.pop('model_predictions');c['assessment_not_overwritten']=c.pop('prediction_not_overwritten')
  c['model_output_status']='PRODUCED' if c['model_assessments'] else 'NOT_PRODUCED'
  c['program_placeholder_origin']='MISSING_DECLARED_USABLE_EVIDENCE' if not c['model_assessments'] else 'DECLARED_EVIDENCE_USE_AGGREGATION'
 return imp,checks

def compact(checks):
 # Lossless ID-referenced dedup of entire repeated dict/list blocks. No semantic filtering.
 pool={};seen={}
 def intern(x):
  if isinstance(x,dict): v={k:intern(z) for k,z in x.items()}
  elif isinstance(x,list):v=[intern(z) for z in x]
  else:return x
  key=json.dumps(v,sort_keys=True,ensure_ascii=False)
  if len(key)<180:return v
  if key not in seen:
   ref=f'check{len(pool)+1}';seen[key]=ref;pool[ref]=v
  return {'$check_ref':seen[key]}
 # Source originals already in common case block; raw prose proposal already supplied once.
 view={k:v for k,v in checks.items() if k not in ['source_recovery','coverage_limits','burdens','scope']}
 for x in view.get('evidence_use_checks',[]):
  x=x # no in-place changes to full traces
 view=copy.deepcopy(view)
 for x in view.get('evidence_use_checks',[]):x.pop('record_retained',None)
 root=intern(view)
 return {'basis':'MODEL_PROPOSED_NOT_LEGAL_VERIFICATION','root':root,'records':pool,'omitted_fields':'source_recovery/common sources; coverage_limits/burdens/scope in common law+proposal; record_retained in proposal by evidence_id. Full file retained.'}

def expand_compact(view):
 def visit(x):
  if isinstance(x,dict) and set(x)=={'$check_ref'}:return visit(view['records'][x['$check_ref']])
  if isinstance(x,dict):return {k:visit(v) for k,v in x.items()}
  if isinstance(x,list):return [visit(v) for v in x]
  return x
 return visit(view['root'])
