"""Frozen input-independent group split; validation cannot exhaust a fit stratum."""
import random,collections

def split(packages,seed=20261007):
 bygroup=collections.defaultdict(list)
 for p in packages:bygroup[p['group_id']].append(p)
 rng=random.Random(seed);families=collections.defaultdict(list)
 for gid,ps in bygroup.items():
  fs={p['family'] for p in ps}
  if len(fs)!=1:raise ValueError('CROSS_FAMILY_DISPUTE_REQUIRES_EXPLICIT_GROUP_STRATUM')
  families[next(iter(fs))].append(gid)
 groups=bygroup
 k=2 if any(len(g)<3 for g in families.values()) else 3
 buckets=[[] for _ in range(k)];features={}
 for gid,ps in bygroup.items():
  features[gid]={(p['family'],u['test_id'],y) for p in ps for u,y,m in zip(p.get('units',[]),p.get('labels',[]),p.get('mask',[])) if m}
 totals=collections.Counter(x for fs in features.values() for x in fs);counts=[collections.Counter() for _ in range(k)]
 for family in sorted(families):
  order=sorted(families[family]);rng.shuffle(order)
  order.sort(key=lambda g:-sum(1/totals[x] for x in features[g]))
  family_counts=[0]*k
  for g in order:
   options=list(range(k));rng.shuffle(options)
   choice=min(options,key=lambda i:(family_counts[i],sum(counts[i][x]/totals[x] for x in features[g]),len(buckets[i])))
   buckets[choice].append(g);family_counts[choice]+=1;counts[choice].update(features[g])
 out=[]
 for f in range(k):
  test=sorted(buckets[f]);fit=sorted(set(groups)-set(test));out.append({'fold':f,'fit_groups':fit,'validation_groups':[],'test_groups':test,'early_stopping':False,'epochs':100,'reason':'Fixed 100 epochs; do not take scarce family/state groups for validation. Never tune on held-out results.'})
 return out

def coverage(packages,folds):
 rows=[];scope=[]
 for fold in folds:
  fit=[p for p in packages if p['group_id'] in fold['fit_groups']];test=[p for p in packages if p['group_id'] in fold['test_groups']]
  def labels(ps):
   d=collections.defaultdict(lambda:collections.defaultdict(set))
   for p in ps:
    for u,y,m in zip(p['units'],p['labels'],p['mask']):
     if m:d[(p['family'],u['test_id'])][y].add(p['group_id'])
   return d
  fl,tl=labels(fit),labels(test)
  for p in test:
   for u,y,m in zip(p['units'],p['labels'],p['mask']):
    key=(p['family'],u['test_id']);varied=len(fl[key])>=2 and len(tl[key])>=2
    admitted=m and varied and y in fl[key]
    scope.append({'fold':fold['fold'],'unit_id':u['id'],'scope':'PRIMARY_CASE_VARIATION' if admitted else 'COVERAGE_OUTSIDE_DIAGNOSTIC' if m else 'MASKED','reason':'Primary requires same-test variation in fit and holdout and its target state seen in fit; fixed before predictions.'})
  for part,ps in [('fit',fit),('test',test)]:
   ls=labels(ps);rows.append({'fold':fold['fold'],'partition':part,'packages':len(ps),'supervised_groups':len({p['group_id'] for p in ps if any(p['mask'])}),'families':dict(collections.Counter(p['family'] for p in ps)),'states':{str(y):len({p['group_id'] for p in ps if any(m and z==y for z,m in zip(p['labels'],p['mask']))}) for y in range(3)},'by_test':{str(k):{str(y):sorted(g) for y,g in v.items()} for k,v in ls.items()}})
 return {'rows':rows,'evaluation_scope':scope,'primary_count':sum(x['scope']=='PRIMARY_CASE_VARIATION' for x in scope)}
