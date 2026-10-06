"""Single coarse category contract; unknown/isolated never supply a negative."""
CLASSES=['CORE','BACKGROUND','IRRELEVANT']
ALIASES={'CORE':'CORE','DIRECT':'CORE','EXCEPTION_COUNTER':'CORE','BACKGROUND':'BACKGROUND','IRRELEVANT':'IRRELEVANT','UNKNOWN':'UNKNOWN','UNRESOLVED':'UNKNOWN'}
def normalize(category, *, no_use_review=None):
 if category=='NO_USE':
  if no_use_review not in (None,'IRRELEVANT','UNKNOWN'):raise ValueError('INVALID_NO_USE_REVIEW')
  return no_use_review or 'UNKNOWN'
 if category not in ALIASES:raise ValueError('UNRECOGNIZED_CATEGORY: '+str(category))
 return ALIASES[category]
def targets(rows,unit_ids):
 result=[];seen=set()
 for row in rows:
  uid=row['unit_id']
  if uid in seen:raise ValueError('DUPLICATE_USE')
  seen.add(uid)
  if uid not in unit_ids:raise ValueError('UNKNOWN_UNIT')
  category=normalize(row['category'],no_use_review=row.get('no_use_review'))
  if category!='UNKNOWN':result.append((unit_ids.index(uid),CLASSES.index(category)))
 return result
