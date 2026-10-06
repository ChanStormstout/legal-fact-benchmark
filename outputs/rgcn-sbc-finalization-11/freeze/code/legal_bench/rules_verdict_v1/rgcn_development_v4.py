"""V10: same graph semantics; explicit unresolved alignment in numeric channel."""
"""Case-isolated sourced proposal graphs; no relevance labels in feature path."""
import hashlib,re,json,math
import numpy as np
TYPES=['need','fact','object','relation','authority','condition','alignment']
SPEAKERS=['LANDLORD','TENANT','THIRD_PARTY','COURT','NARRATOR','UNKNOWN']
STATES=['CLAIMED','FOUND','REPORTED','DISPUTED','UNKNOWN','ADOPTED','ENACTED','REJECTED','RESERVED']
COURTS=['TRIAL','APPELLATE','TARGET','NONE','UNKNOWN']
POLARITY=['POSITIVE','NEGATIVE','UNKNOWN']
SCOPES=['DIRECT','ANALOGY','INCOMPATIBLE','UNKNOWN']
RELATIONS=['need_fact','role_ACTOR','role_RECIPIENT','role_PROPERTY','role_DOCUMENT','role_SUBJECT','role_OBJECT','relation_left','relation_right','contains','requires_AND','requires_OR','requires_SINGLE','requires_QUALIFIES','requires_UNKNOWN','depends_on','align_need','align_fact','align_relation','align_condition','uncertain_need','uncertain_condition']
EDGE_TYPES=RELATIONS+[r+':reverse' for r in RELATIONS]
WIDTH=32+len(TYPES)+len(SPEAKERS)+len(STATES)+len(COURTS)+len(POLARITY)+len(SCOPES)+2
Z_NAMES=['need_coverage','base_coverage','exception_coverage','counter_coverage','limitation_coverage','scope_direct','scope_analogy','scope_incompatible','scope_unknown','unknown_alignment_fraction','court_found_fraction','party_claim_fraction','negative_fraction','unknown_fact_fraction','relation_fraction','text_cosine','bm25_reciprocal_rank','dependency_fraction']
def tokens(s):return re.findall(r'[a-z0-9]+',s.lower())
def hashtext(s,n=32):
 x=np.zeros(n,dtype=np.float32)
 for t in tokens(s):
  h=hashlib.sha256(t.encode()).digest();x[int.from_bytes(h[:2],'big')%n]+=1 if h[2]%2 else -1
 return x/max(float(np.linalg.norm(x)),1.)
def feature(n):
 # All meaningful status and restrictions are active numeric inputs, not side metadata.
 text=' '.join(str(n.get(k,'')) for k in ['text','stage','logic','kind','unknown','date_scope','procedure_scope','jurisdiction','act','limitations'])
 out=list(hashtext(text))
 for key,vals in [('type',TYPES),('speaker',SPEAKERS),('status',STATES),('court',COURTS),('polarity',POLARITY),('scope',SCOPES)]:out.extend(float(n.get(key)==v) for v in vals)
 out.extend([float(bool(n.get('unknown'))),float(n.get('uncertain',False))]);return out

from .source_location_v3 import quote_supported_address

def make_graph(proposal,laws,source,units,rejected=()):
 """Only proposals, source-only laws and original source. No labels argument."""
 refs={s['id']:s['text'] for s in source['segments']};unitmap={u['id']:u for u in units};rejected=set(rejected)
 nodes=[];edges=[];pending=[];index={};quarantine=[]
 def add(k,typ,data,**extra):
  if k in index:raise ValueError('DUPLICATE_ID '+k)
  index[k]=len(nodes);nodes.append(dict(data,id=k,type=typ,**extra));return k
 def edge(a,r,b):
  if a not in index or b not in index:raise ValueError('DANGLING_EDGE')
  if r not in RELATIONS:raise ValueError('UNKNOWN_EDGE_TYPE '+r)
  edges.append([a,r,b])
 def valid(x,quote=False):
  ok=x.get('refs') and all(k in refs for k in x['refs'])
  if quote:ok=ok and bool(x.get('quote')) and any(quote_supported_address(x['quote'],refs[k]) for k in x['refs'])
  return bool(ok)
 for x in proposal['needs']:
  if valid(x) and x['id'] not in rejected:add(x['id'],'need',x)
  else:quarantine.append([x['id'],'NEED_SOURCE'])
 for x in proposal['objects']:
  if valid(x) and x['id'] not in rejected:add(x['id'],'object',x)
  else:quarantine.append([x['id'],'OBJECT_SOURCE'])
 for x in proposal['facts']:
  if not valid(x,True) or x['id'] in rejected:quarantine.append([x['id'],'FACT_SOURCE_OR_REVIEW']);continue
  add(x['id'],'fact',x)
  for role in x.get('roles',[]):
   if role['object_id'] in index:edge(x['id'],'role_'+role['role'],role['object_id'])
   else:pending.append([x['id'],'missing object',role])
  # Shared source location is only a need/record retrieval link, never identity.
  for need in proposal['needs']:
   if need['id'] in index and set(need['refs'])&set(x['refs']):edge(need['id'],'need_fact',x['id'])
 for x in proposal.get('relations',[]):
  if not valid(x,True) or x['id'] in rejected:quarantine.append([x['id'],'RELATION_SOURCE_OR_REVIEW']);continue
  add(x['id'],'relation',dict(x,text=x['relation']+' '+x['text']))
  if x.get('unknown') or x.get('status')=='UNKNOWN' or x.get('polarity')=='UNKNOWN':
   pending.append([x['id'],'UNCERTAIN_ENDPOINT_RELATION_NO_ASSERTED_EDGE']);continue
  # A relation assertion mediates two directed roles; never add left->right shortcut.
  for key,r in [('left','relation_left'),('right','relation_right')]:
   if x[key] in index:edge(x['id'],r,x[key])
 for u in units:add(u['id'],'authority',dict(text=u['text'],scope='UNKNOWN',date_scope=u.get('date',''),limitations=[u.get('coverage_limit','')]))
 for law in laws:
  uid=law['unit_id']
  for x in law['conditions']:
   cid=uid+'::'+x['id']
   if cid in rejected or not x.get('quote') or not quote_supported_address(x['quote'],unitmap[uid]['text']):quarantine.append([cid,'LAW_SOURCE_OR_REVIEW']);continue
   add(cid,'condition',dict(x,status=law['adoption'],jurisdiction=law['jurisdiction'],act=law['act'],date_scope=law['date_scope'],procedure_scope=law['procedure_scope'],limitations=law['limitations']))
   edge(uid,'contains',cid)
  for x in law['conditions']:
   if x.get('parent') and uid+'::'+x['id'] in index and uid+'::'+x['parent'] in index:edge(uid+'::'+x['parent'],'requires_'+x['logic'],uid+'::'+x['id'])
 for u in units:
  for dep in u.get('dependencies',[]):edge(u['id'],'depends_on',dep)
 validlinks={u['id']:[] for u in units}
 effective_alignments=[dict(a,scope='UNKNOWN',original_scope=a['scope'],scope_mask_reason='review rejected at least one unit alignment; no semantic replacement') if any(k.startswith(a['unit_id']+'::alignment') for k in rejected) else dict(a) for a in proposal['alignments']]
 for a in effective_alignments:
  uid=a['unit_id']
  if uid not in unitmap:raise ValueError('UNKNOWN_AUTHORITY')
  for j,x in enumerate(a['links']):
   aid=uid+'::alignment'+str(j);cid=uid+'::'+x['condition_id']
   if aid in rejected or x['need_id'] not in index or cid not in index or not x.get('law_quote') or not quote_supported_address(x['law_quote'],unitmap[uid]['text']) or not x.get('case_refs') or not all(k in refs for k in x['case_refs']):quarantine.append([aid,'ALIGNMENT_SOURCE_OR_REVIEW']);continue
   if any(f not in index for f in x['fact_ids']+x.get('relation_ids',[])):
    quarantine.append([aid,'ALIGNMENT_DEPENDENCY_EXCLUDED_OR_MISSING']);continue
   uncertain=x['state']=='UNKNOWN' or a['state'] in ['UNKNOWN','INCOMPATIBLE']
   add(aid,'alignment',dict(text=x['reason'],kind=x['kind'],scope=a['scope'],uncertain=uncertain,unknown=['candidate only, not satisfaction'] if uncertain else []))
   if uncertain:
    edge(aid,'uncertain_need',x['need_id']);edge(aid,'uncertain_condition',cid)
   else:
    edge(aid,'align_need',x['need_id']);edge(aid,'align_condition',cid)
    for f in x['fact_ids']:
     if f in index:edge(aid,'align_fact',f)
    for rel in x.get('relation_ids',[]):
     if rel in index:edge(aid,'align_relation',rel)
   validlinks[uid].append(dict(x,aid=aid,uncertain=uncertain))
 return dict(case_id=proposal['case_id'],nodes=nodes,edges=edges,pending=pending,quarantine=quarantine,validlinks=validlinks,alignments=effective_alignments,scope='ALLOWED_INPUT_ONLY_MODEL_PROPOSALS_NOT_VERIFIED')

def alignment_unknown_fraction(alignment, links):
 # NONE/INCOMPATIBLE are model-proposed determinations, not missing annotations.
 if not links:
  return float(alignment.get('state') in ('UNKNOWN','CANDIDATE') or alignment.get('scope')=='UNKNOWN')
 return sum(l['uncertain'] for l in links)/len(links)

def numeric(graph,ranking,units):
 nodes=graph['nodes'];idx={n['id']:i for i,n in enumerate(nodes)};n=len(nodes)
 adj=np.zeros((len(EDGE_TYPES),n,n),np.float32)
 for a,r,b in graph['edges']:
  adj[EDGE_TYPES.index(r),idx[b],idx[a]]=1;adj[EDGE_TYPES.index(r+':reverse'),idx[a],idx[b]]=1
 adj/=np.maximum(adj.sum(axis=2,keepdims=True),1)
 x=np.array([feature(z) for z in nodes],np.float32)
 pools=[];z=[];ranks={a['id']:i for i,a in enumerate(ranking,1)};needs=[v for v in nodes if v['type']=='need'];nn=max(1,len(needs));am={a['unit_id']:a for a in graph['alignments']}
 for u in units:
  uid=u['id'];ln=graph['validlinks'][uid];certain=[l for l in ln if not l['uncertain']];a=am[uid]
  pool=[]
  for typ in ['need','fact','object','relation','authority','condition','alignment']:
   ids=[i for i,v in enumerate(nodes) if v['type']==typ and (typ in ['need','fact','object','relation'] or (v['id']==uid if typ=='authority' else v['id'].startswith(uid+'::')))]
   row=np.zeros(n,np.float32)
   if ids:row[ids]=1/len(ids)
   pool.append(row)
  pools.append(pool)
  fs={f for l in certain for f in l['fact_ids'] if f in idx};fns=[nodes[idx[f]] for f in fs];den=max(1,len(fns))
  cov=lambda kind:len({l['need_id'] for l in certain if kind is None or l['kind']==kind})/nn
  querytext=' '.join(v.get('text','') for v in needs)
  z.append([cov(None),cov('BASE'),cov('EXCEPTION'),cov('COUNTER'),cov('LIMITATION')]+[float(a['scope']==s) for s in SCOPES]+[alignment_unknown_fraction(a,ln),sum(v.get('status')=='FOUND' for v in fns)/den,sum(v.get('status')=='CLAIMED' for v in fns)/den,sum(v.get('polarity')=='NEGATIVE' for v in fns)/den,sum(bool(v.get('unknown')) for v in fns)/den,len({rel for l in certain for rel in l.get('relation_ids',[]) if rel in idx})/max(1,len([v for v in nodes if v['type']=='relation'])),float(hashtext(querytext)@hashtext(u['text'])),1/ranks.get(uid,15),len(u.get('dependencies',[]))/len(units)])
 return dict(x=x,adj=adj,pools=np.array(pools,np.float32),z=np.array(z,np.float32))

def fixed_scores(z):return z[:,0]+.5*(z[:,2]+z[:,3]+z[:,4])+z[:,5]+.25*z[:,6]-.5*z[:,7]+.1*z[:,16]
