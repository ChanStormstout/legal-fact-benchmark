"""Source-scoped use labels, hierarchy weighting, non-leaky training gate."""
from collections import Counter,defaultdict
from .grounding_v9 import source_match
LABELS=('USABLE','UNUSABLE','UNRESOLVED')
def validate_use(row,sources):
 errors=[]
 for k in ('id','dispute_id','request_id','rule_ref','premise','evidence_ids','bindings','label','basis'):
  if k not in row:errors.append('MISSING:'+k)
 if row.get('label') not in (*LABELS,'UNLABELED'):errors.append('LABEL')
 if row.get('label')!='UNLABELED':
  if not row.get('basis'):errors.append('LABEL_WITHOUT_BASIS')
  loc=source_match(row,sources)
  if loc['error']:errors.append(loc['error'])
 return errors

def training_gate(rows,qc):
 train=[r for r in rows if r.get('split')=='TRAIN' and r.get('valid') is True and r.get('label') in LABELS and not r.get('synthetic')]
 groups={r['dispute_id'] for r in train};by={k:{r['dispute_id'] for r in train if r['label']==k} for k in LABELS}
 mech={r.get('mechanism') for r in train};types=defaultdict(lambda:defaultdict(set))
 for r in train:types[r['premise_family']][r['label']].add(r['dispute_id'])
 varied=[k for k,v in types.items() if v.get('USABLE') and v.get('UNUSABLE') and len(v['USABLE']|v['UNUSABLE'])>=2]
 reasons=[]
 assignments=defaultdict(set)
 for row in rows:assignments[row['dispute_id']].add(row.get('split'))
 if any(len(v)>1 for v in assignments.values()):reasons.append('DISPUTE_SPLIT_LEAKAGE')
 supervised=[r for r in rows if r.get('split')=='TRAIN' and r.get('valid') is True and r.get('label') in LABELS]
 if supervised and sum(bool(r.get('synthetic')) for r in supervised)/len(supervised)>.2:reasons.append('SYNTHETIC_ABOVE_20_PERCENT')
 if not any(r.get('split')=='DEV' and r.get('valid') is True and r.get('label') in LABELS for r in rows):reasons.append('NO_VALID_DEV_SUPERVISION')
 if len(groups)<30:reasons.append('TRAIN_DISPUTES_BELOW_30')
 for k in LABELS[:2]:
  if len(by[k])<15:reasons.append(k+'_DISPUTES_BELOW_15')
 if not varied:reasons.append('NO_CROSS_CASE_LABEL_VARIATION')
 required={'POSSESSION_TITLE','AUTHORIZATION_SCOPE','STATEMENT_STATUS','STANDING_STAGE'}
 if not required<=mech:reasons.append('MECHANISM_COVERAGE_INCOMPLETE')
 if qc.get('audited')!=100 or qc.get('major_errors',100)>5 or qc.get('systemic_errors') is not False:reasons.append('QC_NOT_PASSED')
 if qc.get('input_label_isolation') is not True:reasons.append('INPUT_LABEL_ISOLATION_NOT_CONFIRMED')
 return {'open':not reasons,'reasons':reasons,'train_disputes':len(groups),'label_disputes':{k:len(v) for k,v in by.items()},'valid_real_rows':len(train),'varied_families':varied,'legal_approval':False}

def hierarchical_weights(rows):
 """Each supervised dispute equal, then each request equal, then each valid use equal."""
 counts=Counter((r['dispute_id'],r['request_id']) for r in rows);groups=defaultdict(set)
 for d,q in counts:groups[d].add(q)
 return [1/(len(groups)*len(groups[r['dispute_id']])*counts[(r['dispute_id'],r['request_id'])]) for r in rows]

def prior(train,queries):
 counts=defaultdict(Counter)
 for r in train:
  if r.get('valid') and r['label'] in LABELS:counts[r['premise_family']][r['label']]+=1
 allc=sum(counts.values(),Counter())
 result=[]
 for q in queries:
  c=counts.get(q['premise_family']) or allc;n=sum(c.values())
  result.append({'id':q['id'],'probabilities':[(c[k]/n if n else 1/3) for k in LABELS],'origin':'TRAIN_LABEL_PRIOR_NOT_SOURCE_TRUTH'})
 return result
