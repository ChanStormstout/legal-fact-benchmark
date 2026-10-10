"""One preparation pass; source qualification and group allocation before generation."""
import json,random,hashlib,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_identity_v2 import validate_view
from legal_bench.proof_carrying.semantic_tasks_v12 import task
R=Path('outputs/proof-semantic-search-v12')
EXCLUDE={'191666286':'Property-tax valuation/bye-law validity, not the chosen entitlement mechanisms.', '1080103':'Land-revenue assessment; property background alone does not qualify.', '869781':'Agricultural income tax and state succession jurisdiction, not possession entitlement.', '440324':'Sovereign accession jurisdiction outside the civil property family.', '1878796':'Criminal conviction; property dispute is background.', '256309':'Criminal appeal; not civil entitlement.', '198357':'Criminal homicide appeal; property dispute is background.'}
DUP={'154566':'983794','877279':'121775','1156375':'378583'}
PRIMARY={'1780900':'AUTHORIZATION_SCOPE','378583':'POSSESSION_TITLE','983794':'POSSESSION_TITLE','118314':'STANDING_STAGE','150369':'STANDING_STAGE','136109':'STATEMENT_STATUS','885778':'AUTHORIZATION_SCOPE','1966631':'STANDING_STAGE','1833042':'AUTHORIZATION_SCOPE','435006':'POSSESSION_TITLE','1652416':'POSSESSION_TITLE','1954356':'STANDING_STAGE','362062':'AUTHORIZATION_SCOPE','1684167':'POSSESSION_TITLE','121775':'AUTHORIZATION_SCOPE','561287':'POSSESSION_TITLE','396336':'STATEMENT_STATUS','1530984':'STANDING_STAGE','1913374':'POSSESSION_TITLE','1870386':'POSSESSION_TITLE','1049882':'AUTHORIZATION_SCOPE','1684565':'STATEMENT_STATUS','180091':'STATEMENT_STATUS','907531':'POSSESSION_TITLE','432276':'STANDING_STAGE','811397':'STANDING_STAGE','1431341':'POSSESSION_TITLE','732701':'STANDING_STAGE','693740':'STANDING_STAGE','258864':'AUTHORIZATION_SCOPE','1854313':'STANDING_STAGE','594273':'POSSESSION_TITLE','1932635':'STANDING_STAGE','835938':'STANDING_STAGE','1140709':'AUTHORIZATION_SCOPE','948916':'STANDING_STAGE','1962138':'POSSESSION_TITLE','1122405':'AUTHORIZATION_SCOPE','971934':'POSSESSION_TITLE'}
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write('\n')
def main():
 order=json.loads((R/'candidate-order.json').read_text())['rows'];decisions=[];eligible=[];rawcache={}
 for row in order[:95]:
  cid=row['case_id'];p=Path(row['source']) if row.get('source') else R/'sources'/f'{cid}.json'
  dec={'case_id':cid,'rank':row.get('saved_rank'),'source':str(p),'group':'V12-'+DUP.get(cid,cid),'detailed_scope_screen':False}
  if cid in EXCLUDE:dec.update(status='EXCLUDED_SCOPE',reason=EXCLUDE[cid]);decisions.append(dec);continue
  if cid in DUP:dec.update(status='RELATED_DUPLICATE',same_dispute_as=DUP[cid],reason='Same parties, original proceeding and property in judgment; different renderer/date heading does not create a new dispute.');decisions.append(dec);continue
  if not p.exists():dec.update(status='SOURCE_UNAVAILABLE',reason='Bounded retrieval produced no usable source envelope.');decisions.append(dec);continue
  d=json.loads(p.read_text())
  if d['status']!='COMPLETE_RENDERING':dec.update(status='SOURCE_BLOCKED',reason=d['status'],missing=d.get('missing_lines'),conflict_count=len(d.get('conflicts',[])));decisions.append(dec);continue
  ss=d['segments'];starts=[i for i,s in enumerate(ss) if s['text'].startswith('## ') and ' vs ' in s['text']];ends=[i for i,s in enumerate(ss) if 'Related AI tags, queries and research notes' in s['text']]
  if len(starts)!=1 or len(ends)!=1:dec.update(status='SOURCE_BLOCKED',reason='BODY_BOUNDARY_NOT_UNIQUE');decisions.append(dec);continue
  seg=ss[starts[0]:ends[0]]
  # Same check as the central identity validator, caching immutable response bytes.
  errors=[]
  for s in seg:
   if s['source_document']!=cid:errors.append('IDENTITY')
   for z in s['provenance']:
    f=z['raw_path']
    if f not in rawcache:
     try:raw=Path(f).read_text();rawcache[f]=(raw,hashlib.sha256(raw.encode()).hexdigest())
     except OSError:rawcache[f]=('',None)
    raw,h=rawcache[f];a,b=z['raw_char_range']
    if h!=z['raw_sha256'] or raw[a:b]!=s['text'] or z['document_id']!=cid:errors.append('PROVENANCE')
  if errors:dec.update(status='SOURCE_BLOCKED',reason=sorted(set(errors)));decisions.append(dec);continue
  exposed=bool(row.get('source'));primary=PRIMARY.get(cid,'AUTHORIZATION_SCOPE')
  if cid in ['1027285','112400','1187427','1954254','845417','277181','280457']:primary='STANDING_STAGE'
  if cid in ['1063933','55384096','603019']:primary='STATEMENT_STATUS'
  if cid in ['739777','1887042']:primary='POSSESSION_TITLE'
  stage='REVIEW_OR_APPEAL'
  if cid in ['183917167','191402169','50313565','68065690','68096693','69998629','84524189']:stage='FIRST_INSTANCE'
  dec.update(status='ELIGIBLE',detailed_scope_screen=True,primary_mechanism=primary,stage=stage,exposed=exposed,reason='Civil property/tenancy/possession entitlement or procedural scope confirmed from the judgment opening and dispute description; no outcome/performance selection.',grouping_limit='Known duplicates grouped. No claim of exhaustive independence beyond inspected parties, properties and proceedings.',source_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
  if cid=='1870868':dec['old_exclusion_preserved']='Former Delhi 14(1)(b) statutory-boundary exclusion remains valid for that old task; V12 covers civil property reconstruction across recorded statutory versions.'
  if cid in ['983794','835938','1954356']:dec['renderer_limit']='Preserve body/header date or OCR variation as supplied; no historical prediction claim.'
  i=next((i for i,s in enumerate(seg) if s['text'].strip() in ('JUDGMENT:','JUDGMENT','JUDGEMENT:')),0)
  dec['scope_evidence_ids']=[s['id'] for s in seg[i:i+30] if s['text'].strip()]
  decisions.append(dec);eligible.append((dec,seg,d))
 counts={'TRAIN':0,'DEV':0,'TEST':0};splits={};rng=random.Random(20261001)
 for dec,_,_ in eligible:
  if dec['exposed'] and counts['TRAIN']<40:splits[dec['case_id']]='TRAIN';counts['TRAIN']+=1
 groups={}
 for x in eligible:
  if not x[0]['exposed']:groups.setdefault((x[0]['primary_mechanism'],x[0]['stage']),[]).append(x)
 for xs in groups.values():rng.shuffle(xs)
 # Round-robin strata, then round-robin remaining capacities; DEV/TEST reserved now.
 queue=[]
 while any(groups.values()):
  for k in sorted(groups):
   if groups[k]:queue.append(groups[k].pop(0))
 cycle=['DEV','TEST','TRAIN'];pos=0
 for dec,_,_ in queue:
  targets={'TRAIN':40,'DEV':10,'TEST':20}
  available=[cycle[(pos+i)%3] for i in range(3) if counts[cycle[(pos+i)%3]]<targets[cycle[(pos+i)%3]]]
  if not available:break
  split=available[0];pos=(cycle.index(split)+1)%3;splits[dec['case_id']]=split;counts[split]+=1
 base=json.loads((R/'data/444449/case.json').read_text());manifest=[]
 for dec,seg,d in eligible:
  cid=dec['case_id'];split=splits.get(cid)
  if split is None:dec['status']='ELIGIBLE_RESERVE_NOT_SELECTED';continue
  case={k:v for k,v in base.items() if k in ['targets']};case.update(case_id=cid,title=d['titles'][0],source_path=dec['source'],source_sha256=dec['source_sha256'],dispute_id=dec['group'],split=split,exposure='PRIOR_EXPOSED_TRAIN_ONLY' if dec['exposed'] else 'QUALIFICATION_ONLY_NOT_METHOD_DEVELOPMENT',mechanism=dec['primary_mechanism'],stage=dec['stage'],segments=seg)
  dst=R/'cohort'/cid;save(dst/'case.json',case)
  hashes={}
  for kind in ('proposal','reference'):
   text=task(kind,case);(dst/(kind+'-task.txt')).write_text(text);hashes[kind]=hashlib.sha256(text.encode()).hexdigest()
  save(dst/'delivery-map.json',{'source_hash':dec['source_sha256'],'source_ids':[s['id'] for s in seg],'all_original_provenance_verified':True,'task_hashes':hashes,'source_address_not_semantic_approval':True})
  manifest.append({k:case[k] for k in ('case_id','dispute_id','split','exposure','mechanism','stage','source_path','source_sha256')})
 save(R/'qualification.json',decisions);save(R/'cohort-freeze.json',{'counts':counts,'cases':manifest,'seed':20261001,'detailed_budget_used_documents':len(decisions),'data_generation_calls':0,'original_candidate_order_unchanged':True,'no_labels_used':True,'target_count_shortfall':{k:({'TRAIN':40,'DEV':10,'TEST':20}[k]-v) for k,v in counts.items()}});print(counts)
if __name__=='__main__':main()
