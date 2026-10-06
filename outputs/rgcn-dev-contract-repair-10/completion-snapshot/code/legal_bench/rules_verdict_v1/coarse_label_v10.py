"""Versioned row validation: whitespace-only locators; semantic level stays separate."""
from .authority_use_v10 import normalize
from .source_location_v3 import locate_all
FIELDS={'unit_id','category','reason','case_refs','law_quote'}
def inspect(payload,case,units):
 if str(payload.get('case_id'))!=str(case['case_id']):raise ValueError('CASE_ID_MISMATCH')
 by={u['id']:u for u in units};refs={s['id'] for s in case['segments']};seen=set();slots={};locations={}
 for row in payload.get('uses',[]):
  uid=row.get('unit_id')
  try:
   if uid not in by or uid in seen:raise ValueError('UNKNOWN_OR_DUPLICATE_AUTHORITY')
   seen.add(uid)
   if set(row)!=FIELDS:raise ValueError('COARSE_FIELDS_ONLY')
   cat=normalize(row['category'])
   if not row['reason'] or not isinstance(row['case_refs'],list) or any(x not in refs for x in row['case_refs']):raise ValueError('INVALID_REASON_OR_CASE_LOCATOR')
   loc=locate_all(by[uid]['text'],row['law_quote']);locations[uid]=loc
   if cat!='UNKNOWN' and (not row['case_refs'] or not loc['matches']):raise ValueError('KNOWN_USE_REQUIRES_VALID_LOCATORS')
   slots[uid]={'state':'UNKNOWN' if cat=='UNKNOWN' else 'KNOWN','record':row,'canonical_category':cat,'semantic_quality':'MODEL_PROPOSAL_LOCATOR_CHECKED_NOT_GOLD'}
  except (ValueError,TypeError) as exc:
   if uid in by:slots[uid]={'state':'ISOLATED','record':row,'reason':str(exc)}
 for uid in by:
  if uid not in slots:slots[uid]={'state':'UNPROCESSED','reason':'NO_COMPLETE_RECORD'}
 return {'case_id':case['case_id'],'slots':slots,'locations':locations,'all_candidate_positions':len(slots),'semantic_certified':False}
