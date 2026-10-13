"""V19_2 mechanical addresses and exact/discontinuous witnesses, no semantic acceptance."""
import copy,re
from .quote_locator_v16 import source_match
VERSION='V19_SOURCE_2'
def catalog(case):
 rows=[{'address':s['id'],'document':s['source_document'],'position':s.get('original_line'),'text':s['text']} for s in case['segments']]
 for i,row in enumerate(rows,1):row['choice']=i
 return rows
def resolve(ref,case):
 rows=catalog(case);exact=[s for s in rows if s['address']==ref]
 if exact:return {'original':ref,'resolved':ref,'status':'EXACT','basis':exact}
 if type(ref) is int:
  if 1<=ref<=len(rows):return {'original':ref,'resolved':rows[ref-1]['address'],'status':'FROZEN_SOURCE_DIRECTORY_INDEX','basis':[rows[ref-1]]}
  return {'original':ref,'resolved':None,'status':'SOURCE_DIRECTORY_INDEX_INVALID'}
 if not isinstance(ref,str):return {'original':ref,'resolved':None,'status':'INVALID_ADDRESS'}
 m=re.fullmatch(r'(?:(IK-\d+):)?(L\d+)',ref)
 if not m:return {'original':ref,'resolved':None,'status':'UNMAPPED_ADDRESS'}
 matches=[s for s in rows if re.fullmatch(r'(IK-\d+):'+re.escape(m[2])+r'(?::[^:]+)*',s['address']) and (not m[1] or s['address'].split(':')[0]==m[1])]
 unique={s['address'] for s in matches}
 if len(unique)==1:return {'original':ref,'resolved':matches[0]['address'],'status':'UNIQUE_ALLOWED_DOCUMENT_LINE','basis':matches}
 return {'original':ref,'resolved':None,'status':'AMBIGUOUS_ADDRESS' if matches else 'OUTSIDE_ALLOWED_ADDRESS','candidates':sorted(unique)}
def convert(raw,case,new_contract=False):
 p=copy.deepcopy(raw);ledger=[]
 def walk(v,path):
  if isinstance(v,dict):
   for k,x in list(v.items()):
    if k=='refs' and isinstance(x,list):
     maps=[resolve(r,case) for r in x];v[k]=[r['resolved'] if r['resolved'] else r['original'] for r in maps];ledger.extend({'path':path+'/refs/'+str(i),**r,'version':VERSION} for i,r in enumerate(maps))
    else:walk(x,path+'/'+k)
  elif isinstance(v,list):
   for i,x in enumerate(v):walk(x,path+'/'+str(i))
 walk(p,'')
 src={s['id']:s for s in case['segments']}
 for ui,unit in enumerate(p['analyses']):
  for vi,use in enumerate(unit['uses']):
   for field,size in [('records',len(unit['records']))]:
    for value in use[field]:
     if type(value) is not int or not 1<=value<=size:ledger.append({'path':'analyses/'+str(ui)+'/uses/'+str(vi)+'/'+field,'original':value,'status':'LOCAL_REFERENCE_INVALID','valid_size':size,'version':VERSION})
   for binding in use['bindings']:
    value=binding['object']
    if type(value) is not int or not 1<=value<=len(unit['objects']):ledger.append({'path':'analyses/'+str(ui)+'/uses/'+str(vi)+'/bindings','original':value,'status':'LOCAL_REFERENCE_INVALID','valid_size':len(unit['objects']),'version':VERSION})
   if new_contract:
    witnesses=[]
    for w in use['witnesses']:
     for ref in w['refs']:
      witnesses.append({**w,'refs':[ref],'quote':src[ref]['text'] if ref in src else '', 'witness_origin':'CODE_RESTORED_SOURCE_ANCHOR','semantic_approval':False})
    use['witnesses']=witnesses
  for j in unit['judgments']:
   j['limit_scope_audit']=[{'kind':'UNMAPPED_LEGACY_NOTE','original':x,'effect':'SCOPE_UNRESOLVED_NOT_FALSE'} if isinstance(x,str) else copy.deepcopy(x) for x in j.get('necessary_limits',[])]
 return p,ledger

def witness_location(w,src):
 ordinary=source_match(w,src)
 if not ordinary.get('error'):return {**ordinary,'complete_quote_verified':True}
 # Recover only literal disjoint pieces at their declared locations; no missing words inserted.
 quote=w.get('quote');refs=w.get('refs',[])
 if ordinary.get('error')!='QUOTE_NOT_LOCATED' or not isinstance(quote,str) or not re.search(r'\.{3}|…',quote):return ordinary
 fragments=[x.strip() for x in re.split(r'\.{3}|…+',quote) if x.strip()]
 if len(fragments)<2:return ordinary
 locations=[];last=None
 for fragment in fragments:
  loc=source_match({'quote':fragment,'refs':refs},src)
  if loc.get('error'):return ordinary
  spans=loc.get('original_spans',[])
  if not spans:return ordinary
  start=(src[spans[0]['ref']].get('original_line',10**12),spans[0]['start']);end=(src[spans[-1]['ref']].get('original_line',10**12),spans[-1]['end'])
  if last is not None and start<last:return ordinary
  last=end
  locations.append({'quote':fragment,'location':loc})
 return {'error':None,'mode':'SEPARATE_EXACT_QUOTED_FRAGMENTS','fragments':locations,'original_quote':quote,'complete_quote_verified':False,'semantic_verified':False,'omitted_text_restored':False}
