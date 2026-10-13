"""Input-only feature specification. Never reads labels or reference answers."""
import json,hashlib
REL=('FACT_APPLICATION','RULE_APPLICATION','RULE_DEPENDENCY','REQUEST_APPLICATION','OBJECT_FACT','SUPPORT','OPPOSE','UNRESOLVED')
def text(value):return json.dumps(value,sort_keys=True,ensure_ascii=False)
def graph(case,proposal):
 nodes=[];edges=[];index={};uses=[];quarantine=[]
 def add(key,body,kind):
  if key in index:raise ValueError('DUPLICATE_INPUT_NODE:'+key)
  index[key]=len(nodes);nodes.append({'id':key,'text':text(body),'kind':kind})
 for f in proposal['facts']:add('F:'+f['id'],f,0)
 premises={}
 for r in proposal['rules']:
  for p in r['premises']:
   add('R:'+p['id'],{'premise':p,'rule':{k:v for k,v in r.items() if k!='premises'}},1);premises[p['id']]=p
 for q in case['targets']:add('Q:'+q['id'],q,3)
 for u in proposal['uses']:
  if u.get('rule_premise') not in premises or 'Q:'+u.get('request_id','') not in index or any('F:'+k not in index for k in u.get('evidence_ids',[])):
   quarantine.append(u.get('id'));continue
  add('C:'+u['id'],u,2);uses.append(u['id']);edges.append(('R:'+u['rule_premise'],'C:'+u['id'],1));edges.append(('C:'+u['id'],'Q:'+u['request_id'],3))
  for fid in u['evidence_ids']:edges.append(('F:'+fid,'C:'+u['id'],0))
 # Entity mentions are local, proposed identities; no cross-case identity inference.
 for f in proposal['facts']:
  for role,entity in f.get('bindings',{}).items():
   if entity is None:continue
   key='E:'+text(entity)
   if key not in index:add(key,{'proposed_entity':entity},4)
   edges.append((key,'F:'+f['id'],4))
 for rel in proposal.get('relations',[]):
  if rel.get('sign') not in REL[5:]:continue
  a='F:'+rel.get('from','');b='F:'+rel.get('to','')
  if a in index and b in index:edges.append((a,b,REL.index(rel['sign'])))
 es=[(index[a],index[b],r) for a,b,r in edges];es += [(b,a,r+len(REL)) for a,b,r in list(es)]
 return {'nodes':nodes,'edges':es,'candidate_indices':[index['C:'+k] for k in uses],'request_indices':{q['id']:index['Q:'+q['id']] for q in case['targets']},'ids':uses,'quarantine':quarantine,'reference_used':False}
def ce_pairs(case,proposal):
 fs={f['id']:f for f in proposal['facts']};ps={p['id']:(p,r) for r in proposal['rules'] for p in r['premises']};out=[]
 for u in proposal['uses']:
  if u.get('rule_premise') not in ps or any(k not in fs for k in u.get('evidence_ids',[])):continue
  p,r=ps[u['rule_premise']]
  out.append({'id':u['id'],'request_id':u['request_id'],'left':text({'request':next((q for q in case['targets'] if q['id']==u['request_id']),None),'premise':p,'rule':r}), 'right':text({'evidence':[fs[k] for k in u['evidence_ids']],'proposed_use':u,'relations':proposal.get('relations',[]),'coverage_limits':proposal.get('coverage_limits',[])})})
 return out
