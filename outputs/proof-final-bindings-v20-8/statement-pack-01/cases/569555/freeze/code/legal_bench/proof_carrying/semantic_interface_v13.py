"""Versioned input-only V13 adapter. No reference lookup or semantic repairs."""
import copy, json, re, hashlib
from .semantic_import_v12 import adapt as legacy_adapt
from .semantic_features_v12 import graph as legacy_graph, ce_pairs as legacy_pairs, REL
from .contracts import content_hash
TYPES={'person','property','document','event','date','court','organization','organisation','entity','land','premises','instrument','transaction','time','boolean','string','number','object','legal_person'}
SIGNS={'SUPPORT':'SUPPORT','SUPPORTS':'SUPPORT','OPPOSE':'OPPOSE','OPPOSES':'OPPOSE','UNRESOLVED':'UNRESOLVED'}

def adapt(case,proposal):
 snapshot,candidates,requests=legacy_adapt(case,proposal)
 bypremise={}
 for u in proposal['uses']:bypremise.setdefault(u.get('rule_premise'),set()).update(u.get('bindings',{}))
 for r in proposal['rules']:
  rr=r['id']+'@'+str(r['version'])
  if rr not in snapshot['contracts']:continue
  rc=snapshot['contracts'][rr];rc.update(role_types={},unmapped_roles={},mapping_provenance={})
  for p in r['premises']:
   pid=p['id'];mapping={};types={};unknown={};provenance={};known=bypremise.get(pid,set())
   for role,value in p.get('variables',{}).items():
    if isinstance(value,str) and value.lower() in TYPES:
     types[role]=value
     if role in known:mapping[role]=role;provenance[role]='EXPLICIT_SAME_ROLE_USE_VARIABLE_ADDRESS_NOT_IDENTITY_PROOF'
     elif value in known:mapping[role]=value;provenance[role]='EXPLICIT_LEGACY_VARIABLE_ADDRESS_WITH_TYPE_LIKE_NAME';types.pop(role,None)
     else:unknown[role]={'type':value,'reason':'NO_EXPLICIT_SAME_ROLE_VARIABLE'}
    elif isinstance(value,str) and value in known:mapping[role]=value;provenance[role]='EXPLICIT_SYMBOLIC_VARIABLE'
    else:unknown[role]={'raw':value,'reason':'AMBIGUOUS_OR_UNDECLARED_VARIABLE'}
   rc['slot_variables'][pid]=mapping;rc['role_types'][pid]=types;rc['unmapped_roles'][pid]=unknown;rc['mapping_provenance'][pid]=provenance
 snapshot['interface_version']='V13';snapshot['identity_policy']='EXACT_PROPOSED_BINDINGS_WITH_SOURCE_CHECK_NOT_SEMANTIC_IDENTITY_APPROVAL'
 return snapshot,candidates,requests

def position(segment):
 if isinstance(segment.get('start'),int):return (0,segment['start'])
 if isinstance(segment.get('original_line'),int):return (1,segment['original_line'])
 m=re.search(r':L(\d+)(?:\D|$)',segment.get('id',''))
 return (1,int(m.group(1))) if m else (2,segment.get('id',''))

def recover(case,refs):
 segments=case['segments'];index={s['id']:s for s in segments};groups={}
 for s in segments:groups.setdefault(s['source_document'],[]).append(s)
 for rows in groups.values():rows.sort(key=lambda s:(position(s),s['id']))
 selected={};limits=[]
 for ref in refs:
  s=index.get(ref)
  if s is None:limits.append({'ref':ref,'reason':'SOURCE_ID_NOT_RECOVERED'});continue
  rows=groups[s['source_document']];i=next(i for i,x in enumerate(rows) if x['id']==ref)
  window=rows[max(0,i-1):i+2] if position(s)[0]!=2 else [s]
  if position(s)[0]==2:limits.append({'ref':ref,'reason':'POSITION_UNKNOWN_NO_ADJACENT_CONTEXT'})
  for x in window:selected[(x['id'],content_hash(x['text']))]=x
 recovered=[]
 for s in sorted(selected.values(),key=lambda x:(x['source_document'],position(x),x['id'])):
  chunks=[{'start':i,'end':min(i+3000,len(s['text'])),'text':s['text'][i:i+3000]} for i in range(0,len(s['text']),3000)]
  recovered.append({'id':s['id'],'source_document':s['source_document'],'original_position':list(position(s)),'text':s['text'],'sha256':hashlib.sha256(s['text'].encode()).hexdigest(),'chunks':chunks,'metadata':{k:v for k,v in s.items() if k!='text'}})
 return {'segments':recovered,'limits':limits,'requested_refs':list(dict.fromkeys(refs)),'scope':'CITED_SEGMENTS_AND_FIXED_ADJACENT_CONTEXT_NOT_FULL_JUDGMENT'}

def relation_map(proposal):
 facts={f['id'] for f in proposal['facts']};rows=[]
 for rel in proposal.get('relations',[]):
  sign=SIGNS.get(rel.get('sign') or rel.get('type') or rel.get('relation'))
  a=rel.get('from');b=rel.get('to');valid=bool(sign and isinstance(a,str) and isinstance(b,str) and a in facts and b in facts)
  rows.append({'raw':rel,'encoded':valid,'sign':sign if valid else None,'from':a,'to':b,'reason':None if valid else 'NO_EXPLICIT_SUPPORTED_SIGN_OR_EXACT_FACT_ENDPOINTS'})
 for u in proposal['uses']:
  for value in u.get('opposition',[]):
   valid=isinstance(value,str) and value in facts
   rows.append({'raw':{'original_field':'uses.'+u['id']+'.opposition','value':value,'premise':u['rule_premise'],'bindings':u.get('bindings',{})},'encoded':valid,'sign':'OPPOSE' if valid else None,'from':value if valid else None,'to':None,'to_use':u['id'],'reason':None if valid else 'OPPOSITION_NOT_AN_EXPLICIT_EXISTING_FACT_ID','proposal_only':True})
 return rows

def inputs(case,proposal):
 # All three methods read the same full raw relations and restored evidence.
 # The graph topology is additional propagation, not additional supervision.
 p=copy.deepcopy(proposal);audit=relation_map(p);p['relations']=[{'from':r['from'],'to':r['to'],'sign':r['sign']} for r in audit if r['encoded'] and not r.get('to_use')]
 g=legacy_graph(case,p)
 # A repeated entity string is a proposed mention, not established identity.
 # Scope entity nodes by record and role; explicit P relations remain separate.
 retained=[(i,n) for i,n in enumerate(g['nodes']) if n['kind']!=4]
 remap={old:i for i,(old,n) in enumerate(retained)}
 g['nodes']=[n for _,n in retained]
 g['edges']=[(remap[a],remap[b],rel) for a,b,rel in g['edges'] if a in remap and b in remap]
 g['candidate_indices']=[remap[i] for i in g['candidate_indices']]
 g['request_indices']={k:remap[v] for k,v in g['request_indices'].items()}
 fact_indices={n['id'][2:]:i for i,n in enumerate(g['nodes']) if n['id'].startswith('F:')}
 for f in proposal['facts']:
  for role,entity in f.get('bindings',{}).items():
   if entity is None or entity=='':continue
   i=len(g['nodes']);g['nodes'].append({'id':'E:'+f['id']+':'+role,'kind':4,'text':json.dumps({'proposed_entity':entity,'record':f['id'],'role':role,'refs':f.get('refs',[]),'identity':'LOCAL_MENTION_NOT_VERIFIED_COREFERENCE'},sort_keys=True,ensure_ascii=False)})
   j=fact_indices[f['id']];g['edges'].extend([(i,j,4),(j,i,4+len(REL))])
 g['entity_identity_policy']='RECORD_AND_ROLE_SCOPED_MENTIONS_NO_STRING_IDENTITY_MERGE'
 node_index={n['id']:i for i,n in enumerate(g['nodes'])}
 for row in audit:
  if row['encoded'] and row.get('to_use'):
   a=node_index.get('F:'+row['from']);b=node_index.get('C:'+row['to_use'])
   if a is not None and b is not None:g['edges'].extend([(a,b,6),(b,a,6+len(REL))])
 pairs=legacy_pairs(case,proposal);pairindex={x['id']:x for x in pairs};facts={f['id']:f for f in proposal['facts']};ps={x['id']:(x,r) for r in proposal['rules'] for x in r['premises']};material={}
 for u in proposal['uses']:
  if u['id'] not in pairindex:continue
  _,r=ps[u['rule_premise']];refs=[ref for fid in u['evidence_ids'] for ref in facts[fid].get('refs',[])]+r.get('source_refs',[])
  m=recover(case,refs);material[u['id']]=m
  shared={'restored_source':m,'raw_relations':proposal.get('relations',[]),'relation_encoding_audit':audit,'coverage_limits':proposal.get('coverage_limits',[])}
  pairindex[u['id']]['right']=json.dumps({'legacy_P_material':json.loads(pairindex[u['id']]['right']),**shared},sort_keys=True,ensure_ascii=False)
  node=next(n for n in g['nodes'] if n['id']=='C:'+u['id']);node['text']=json.dumps({'proposal':u,'same_information_pair':pairindex[u['id']]},sort_keys=True,ensure_ascii=False)
 # Explicit exact dependency edges, only with resolved role maps.
 snapshot,_,_=adapt(case,proposal);nodeindex={n['id']:i for i,n in enumerate(g['nodes'])};dependency=[]
 for rr,r in snapshot['rules'].items():
  for slot in r['slots']:
   sources=[sr for sr,rv in snapshot['rules'].items() if rv['conclusion_predicate']==slot['predicate']]
   if len(sources)!=1 or snapshot['contracts'][rr]['unmapped_roles'].get(slot['name']):continue
   if not snapshot['contracts'][rr]['slot_variables'].get(slot['name']):continue
   for childslot in snapshot['rules'][sources[0]]['slots']:
    a=nodeindex.get('R:'+childslot['name']);b=nodeindex.get('R:'+slot['name'])
    if a is not None and b is not None:dependency.extend([(a,b,2),(b,a,2+len(REL))])
 g['edges']+=dependency;g['interface_version']='V13';g['relation_audit']=audit;g['material_ids']=list(material)
 union={}
 for m in material.values():
  for seg in m['segments']:union[(seg['id'],seg['sha256'])]=seg
 shared_case={'case_questions':case['targets'],'P_facts':proposal['facts'],'P_rules':proposal['rules'],'P_uses':proposal['uses'],'raw_relations':proposal.get('relations',[]),'coverage_limits':proposal.get('coverage_limits',[]),'restored_source':[{'id':seg['id'],'document':seg['source_document'],'position':seg['original_position'],'text':seg['text']} for seg in sorted(union.values(),key=lambda seg:(seg['source_document'],seg['original_position'],seg['id']))]}
 # Flat/R-GCN already consume this union across all their nodes and triples.
 # CE must also receive the peer-case information; selected evidence alone is weaker.
 for pair in pairs:pair['shared_case_context_ref']='case:'+case['case_id']
 return {'graph':g,'ce_pairs':pairs,'materials':material,'shared_case_context':shared_case,'information_contract':'IDENTICAL_RAW_P_RULES_RELATIONS_RESTORED_SEGMENTS; GRAPH_ADDS_TYPED_PROPAGATION','reference_used':False,'rule_dependency_edges':len(dependency)}
