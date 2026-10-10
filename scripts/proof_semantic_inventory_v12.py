import json,re,sqlite3,hashlib
from pathlib import Path
R=Path('outputs/proof-semantic-search-v12')
def save(n,x):
 p=R/n
 if p.exists():raise FileExistsError(p)
 p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
deny=set(json.loads((R/'sealed-denylist.json').read_text())['ids']);old=set(json.loads((R/'candidate-order-local.json').read_text())['old_eight_excluded']);local=json.loads((R/'local-source-inventory.json').read_text());li={x['case_id']:x for x in local}
patterns={'POSSESSION_TITLE':r'possess|ownership|title to|owner of','AUTHORIZATION_SCOPE':r'licen[cs]|lease|tenan|consent|authori[sz]','STATEMENT_STATUS':r'testimon|witness|admi[st]|document|alleg','STANDING_STAGE':r'injunction|interim|maintainab|locus|necessary part|implead'}
db=sqlite3.connect('file:outputs/benchmark-pilot/data/cases.sqlite?mode=ro',uri=True);rows=[];locmeta={}
# doc_id denial is applied in SQL, before raw_json enters Python.
query='select doc_id,line_number,title,url,raw_json from cases where doc_id not in ('+','.join('?' for _ in deny)+') order by line_number'
for cid,rank,title,url,raw in db.execute(query,tuple(deny)):
 cid=str(cid).replace('case_','')
 if cid in deny or cid in old:continue
 d=json.loads(raw);t=' '.join(str(d.get(k,'')) for k in ['facts','issues'])
 hits={k:bool(re.search(v,t,re.I)) for k,v in patterns.items()}
 if cid in li:locmeta[cid]={'rank':rank,'hits':hits}
 if re.search(r'land|property|premises|possession|tenan|lease',t,re.I) and sum(hits.values())>=2:
  rows.append({'case_id':cid,'saved_rank':rank,'title':title,'url':url,'mechanism_locators':[k for k,v in hits.items() if v],'status':'METADATA_LOCATOR_ONLY','local_source':li.get(cid,{}).get('source'),'metadata_sha256':hashlib.sha256(raw.encode()).hexdigest()})
ordered=sorted(local,key=lambda x:(locmeta.get(x['case_id'],{}).get('rank',10**12),int(x['case_id'])))
fixed=[{**x,'saved_rank':locmeta.get(x['case_id'],{}).get('rank'),'mechanism_locators':[k for k,v in locmeta.get(x['case_id'],{}).get('hits',{}).items() if v]} for x in ordered]
fixed += [x for x in rows if x['case_id'] not in li]
save('candidate-order.json',{'max_detailed':150,'order':'existing original sources first in saved database rank (otherwise doc ID); then unseen locator candidates in database order; no verdict/model filtering','rows':fixed[:150],'metadata_hit_count':len(rows),'local_sources':len(local),'metadata_is_not_original':True})
print('candidates',len(fixed[:150]),'local',len(local));print([(x['case_id'],x.get('saved_rank')) for x in fixed[:45]])
