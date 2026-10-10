"""Single local preparation: contracts, fair enumeration, explicit label migration."""
import sys,json,copy,hashlib,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
from legal_bench.proof_carrying.contracts import content_hash
from legal_bench.proof_carrying.search_v11 import generate,signature
from legal_bench.proof_carrying.selection_v10 import load_contracts,eligibility
from legal_bench.proof_carrying.dependency_v9 import rebind
from legal_bench.proof_carrying.composite_v10 import prepare as composites
from scripts.proof_search_delivery_v11 import OUT as R,BASE,read,save
OLD=Path('outputs/proof-carrying-selection-readiness-v10')

def main():
 registry=read(OLD/'contracts/registry.json');changes=[]
 for h,c in registry.items():
  if c['case_scope']=='1841885' and c['rule_ref']=='R5@1':
   before=copy.deepcopy(c['variables']);c['version']=2;c['variables']['version']=2
   c['variables']['slot_variables']['trust_denial_recorded'].update(subject='opponent',opponent='subject')
   c['variables']['reason']='Claimants allegation subject=plaintiffs; trust denial subject=trust. Same plaintiffs/trust/property/contested transaction, opposite speaker roles. Does not endorse either account.'
   c['variables']['source_refs']=['IK-1841885:L75','IK-1841885:L138','IK-1841885:L151','IK-1841885:L152'];changes.append({'rule_hash':h,'before':before,'after':c['variables'],'review':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_LEGAL_APPROVAL'})
 save(R/'contracts/registry.json',registry);save(R/'contracts/revision.json',changes)
 vec=np.load(BASE/'encoding/candidate/vectors.npz');sim=lambda a,b:float(vec[hashlib.sha256(a.encode()).hexdigest()]@vec[hashlib.sha256(b.encode()).hexdigest()])
 labels=read(BASE/'supervision/labels.json');migrations=[];cost=[]
 # These old criticisms concern repaired bindings or absence of proof, not established wrong uses.
 masked={'APP-30b27eddc307a4c5':'DEPENDENCY_BINDING_REPAIRED','APP-ff18888951f974ca':'ROLE_CONTRACT_REPAIRED','APP-58cd4f884c4ebce8':'UNKNOWN_IS_NOT_NEGATIVE','APP-3b5a7fe5dd64dbbb':'UNKNOWN_IS_NOT_NEGATIVE'}
 for cid in read(R/'protocol.json')['cases']:
  started=time.perf_counter();i=BASE/'inputs'/cid;rules={x['id']+'@'+str(x['version']):x for x in read(i/'rules.json')};facts=read(BASE/'runs'/cid/'proposal/usable.json');sources=read(i/'sources.json');contracts=load_contracts(R/'contracts/registry.json',rules);vc={k:v['variables'] for k,v in contracts.items()}
  generated,audit=generate(facts,list(rules.values()),sim);old=read(BASE/'candidates'/f'{cid}.json');by={signature(c):copy.deepcopy(c) for c in old}
  for c in generated:by.setdefault(signature(c),c)
  made,cc=composites(facts,rules,sources,[d for c in contracts.values() for d in c['decompositions']]);fi={p['id']:p for p in facts['premises']};ext={**fi,**{x['premise']['id']:x['premise'] for x in made}};cs=[];trans=[]
  for c in by.values():
   c['v11_raw_signature']=signature(c)
   for x in c['inputs']:
    for item in made:
     k=item['contract']
     if c['rule_ref']+':'+x['slot']==k['id'] and x['kind']=='PREMISE' and fi[x['id']]['predicate'] in [a['predicate'] for a in k['atoms']]+[k['predicate']]:
      trans.append({'candidate':c['id'],'old':x['id'],'new':item['premise']['id'],'contract_hash':content_hash(k)});x['id']=item['premise']['id'];break
   c=rebind(c,rules[c['rule_ref']],ext,vc[c['rule_ref']]);c['legacy_structural_flags']=c['structural_flags'];cs.append(c)
  erows=eligibility(cs,rules,ext,sources,contracts);er={x['id']:x for x in erows}
  for c in cs:
   c['structural_flags']=er[c['id']]['errors']+er[c['id']]['pending'];c['simple_features']['flags']=len(c['structural_flags'])
  reference=read(OLD/'prepared'/cid/'reference.json');ref={x['id']:x for x in reference['candidate_reviews']};neg={}
  old10={x['id']:x for x in read(OLD/'results/simple'/cid/'eligibility.json')}
  for c in cs:
   k=c['id'];y=labels.get(cid,{}).get(k);reason='NEW_OR_UNREVIEWED_UNKNOWN';target=None
   if y is not None:
    if er[k]['status']=='EXCLUDE_EXPLICIT_CONTRACT_ERROR':reason='ENGINEERING_EXCLUDED_NOT_TRAINED'
    elif y==1:reason='OLD_POSITIVE_NOT_ACTION_LABEL_REQUIRES_COMPLETION_ROUTE'
    elif k in masked:reason=masked[k]
    else:reason='SOURCE_REVIEWED_SPECIFIC_SLOT_NONAPPLICABILITY';target=0;neg[k]={'value':0,'basis':ref[k],'semantic_version':content_hash([rules[c['rule_ref']],contracts[c['rule_ref']],c['inputs'],c['bindings']]),'review':'MODEL_ASSISTED_MIGRATION_NOT_HUMAN_GOLD'}
   migrations.append({'case':cid,'id':k,'old_label':y,'v10_eligibility':old10.get(k,{}).get('status'),'v11_eligibility':er[k]['status'],'status':reason,'action_label':target,'old_reason':ref.get(k,{}).get('reason'),'contract_hash':content_hash(contracts[c['rule_ref']]),'new_signature':signature(c)})
  for name,data in [('variables',vc),('composites',made),('composite-contracts',cc),('candidates',cs),('transformations',trans),('reference',reference),('eligibility',erows),('enumeration',audit),('negative-use-review',neg)]:save(R/'prepared'/cid/(name+'.json'),data)
  cost.append({'case':cid,'seconds':time.perf_counter()-started,'old':len(old),'balanced':len(generated),'union':len(cs),'eligible':sum(e['status']!='EXCLUDE_EXPLICIT_CONTRACT_ERROR' for e in erows)})
 save(R/'label-migration.json',migrations);save(R/'preparation-cost.json',cost)
 print(json.dumps(cost))
if __name__=='__main__':main()
