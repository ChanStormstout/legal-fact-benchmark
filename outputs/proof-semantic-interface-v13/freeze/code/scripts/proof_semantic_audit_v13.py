#!/usr/bin/env python3
"""Final bounded dataset/gate audit. Existing TRAIN labels unchanged; no TEST reads."""
import sys,json,hashlib,collections,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.semantic_data_v12 import validate_use
from legal_bench.proof_carrying.semantic_interface_v13 import adapt,inputs
from scripts.proof_semantic_run_v13 import run,save
ROOT=Path('outputs/proof-semantic-interface-v13');OLD=Path('outputs/proof-semantic-search-v12/continuation-02');CLASSES={'USABLE','UNUSABLE','UNRESOLVED'}
def read(p):return json.loads(Path(p).read_text())
def main():
 dest=ROOT/(sys.argv[1] if len(sys.argv)>1 else '.');old=read(OLD/'supervision-35/rows.json');rows=[copy.deepcopy(r) for r in old];inventory=read(ROOT/'dev-inventory.json');new=[];baselines={};coverage={};route_rows=[];priors={};glob=collections.Counter();errors=[]
 for r in rows:r['review_production_mode']='V12_P_SELF_ASSESSMENT_VISIBLE';r['historical_label_unchanged']=True
 for item in inventory:
  cid=item['case']['case_id'];w=ROOT/'web'/cid;p=w/'proposal/resolved.json';rev=w/'review/resolved.json'
  if (w/'proposal/address-v13/resolved.json').exists():p=w/'proposal/address-v13/resolved.json'
  if (w/'review/address-v13/resolved.json').exists():rev=w/'review/address-v13/resolved.json'
  if cid in {r['case_id'] for r in old if r['split']=='DEV'}:continue
  if not p.exists():p=OLD/'generated'/cid/'proposal/resolved-address-v2.json'
  if not p.exists():p=OLD/'generated'/cid/'proposal/resolved.json'
  if not p.exists():continue
  case=read(Path('outputs/proof-semantic-search-v12/cohort')/cid/'case.json');assert case['split']=='DEV';proposal=read(p);reviews=read(rev).get('use_reviews',[]) if rev.exists() else [];ri={}
  for rv in reviews:ri.setdefault(rv.get('use_id'),[]).append(rv)
  ps={pr['id']:(r,pr) for r in proposal['rules'] for pr in r['premises']};sources={s['id']:{**s,'document':s['source_document']} for s in case['segments']};feat=inputs(case,proposal);ids=set(feat['graph']['ids']);new.extend([cid]);d=dest/'dev-restored'/cid;d.mkdir(parents=True,exist_ok=True);snap,cs,qs=adapt(case,proposal)
  for n,x in [('case.json',case),('proposal.json',proposal),('snapshot.json',snap),('candidates.json',cs),('requests.json',qs),('model-information-fullcontext.json',feat)]:save(d/n,x)
  for u in proposal['uses']:
   rr,pr=ps.get(u.get('rule_premise'),({},{}));rs=ri.get(u['id'],[]);rv=rs[0] if len(rs)==1 else {}
   row={'key':cid+'::'+u['id'],'id':u['id'],'use_id':u['id'],'dispute_id':case['dispute_id'],'case_id':cid,'split':'DEV','request_id':u['request_id'],'rule_ref':rr.get('id','')+'@'+str(rr.get('version','')),'premise':pr.get('text'),'premise_family':pr.get('family','UNSPECIFIED'),'evidence_ids':u.get('evidence_ids'),'bindings':u.get('bindings'),'label':rv.get('label','UNLABELED'),'basis':rv.get('basis'),'refs':rv.get('refs',[]),'quote':rv.get('quote',''),'mechanism':case['mechanism'],'synthetic':False,'source_sha256':case['source_sha256'],'proposal_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'review_sha256':hashlib.sha256(rev.read_bytes()).hexdigest() if rev.exists() else None,'proposal_dir':str(d),'reference_kind':'MODEL_GENERATED_SOURCE_REVIEW_NOT_HUMAN_GOLD','review_production_mode':'V13_P_LABEL_AND_BASIS_BLIND' if rev.exists() else 'MISSING_OR_TECHNICALLY_FAILED_REVIEW_NULL','historical_label_unchanged':False}
   err=validate_use(row,sources) if isinstance(row.get('quote'),str) else ['QUOTE_NOT_A_STRING']
   if len(rs)>1:err.append('DUPLICATE_REVIEW')
   if not rs:err.append('NO_REFERENCE_LABEL_TECHNICAL_FAILURE_OR_NOT_GENERATED')
   if u['id'] not in ids:err.append('INPUT_USE_NOT_REPRESENTABLE')
   row.update(valid=not err,errors=err);rows.append(row)
  run(snap,cs,qs,d/'raw-P')
  oracle=copy.deepcopy(snap);labels={r['use_id']:r['label'] for r in rows if r['case_id']==cid and r['valid'] and r['label'] in CLASSES}
  for u in oracle['model_uses'].values():
   if u['raw_use_id'] in labels:u['label']=labels[u['raw_use_id']]
  oracle['diagnostic_reference_use_labels_only']=True;run(oracle,cs,qs,d/'oracle-use-only')
 for r in rows:
  if r['split'] not in ('TRAIN','DEV'):raise ValueError('TEST_IN_AUDIT')
  if not r['valid'] or r['label'] not in CLASSES:continue
  if r['split']=='TRAIN':glob[r['label']]+=1;priors.setdefault(r['premise_family'],collections.Counter())[r['label']]+=1
  k=(r['split'],r['mechanism']);c=coverage.setdefault(k,{'disputes':set(),'labels':collections.Counter()});c['disputes'].add(r['dispute_id']);c['labels'][r['label']]+=1
 for r in rows:
  if not r['valid'] or r['label'] not in CLASSES:continue
  cid=r['case_id'];p=dest/'dev-restored'/cid/'proposal.json'
  if not p.exists():p=ROOT/'inputs-v13-02'/cid/'proposal.json'
  proposal=read(p);u=next(x for x in proposal['uses'] if x['id']==r['use_id']);b=baselines.setdefault(r['split'],{'n':0,'RAW_P_agree':0,'PRIOR_agree':0,'RAW_P_disagreements':[],'unseen_families':0});b['n']+=1;b['RAW_P_agree']+=u['use_judgment']==r['label'];counts=priors.get(r['premise_family'],glob);pred=sorted(counts,key=lambda k:(-counts[k],k))[0];b['PRIOR_agree']+=pred==r['label'];b['unseen_families']+=r['premise_family'] not in priors
  if u['use_judgment']!=r['label']:b['RAW_P_disagreements'].append({'key':r['key'],'P':u['use_judgment'],'reference':r['label'],'mechanism':r['mechanism'],'refs':r['refs'],'basis':r['basis']})
 # Audit only already prepared real DEV routes; no artificial reference bindings or truth.
 dev_ids=sorted({r['case_id'] for r in rows if r['split']=='DEV' and r['valid'] and r['label'] in CLASSES})
 for cid in dev_ids:
  d=dest/'dev-restored'/cid
  if d.exists():snapshot=read(d/'snapshot.json');paths=[d/'raw-P/checked.json',d/'oracle-use-only/checked.json']
  else:
   snapshot=read(ROOT/'final-replays-02'/cid/'snapshot.json');paths=[ROOT/'final-replays-02'/cid/'raw-P/checked.json',ROOT/'final-replays-02'/cid/'oracle-use-only/checked.json']
  a,b=map(read,paths);use_only=[]
  for sid,st in a['steps'].items():
   pending=st.get('pending',[])
   if not st['errors'] and pending and all('MODEL_USE_UNRESOLVED_OR_REJECTED' in p for p in pending):use_only.append(sid)
  changed=[{'request':x['id'],'P':x['answer'],'oracle':y['answer']} for x,y in zip(a['requests'],b['requests']) if x['answer']!=y['answer']]
  root_ids={z['step'] for req in a['requests'] for z in req['alternatives']}
  root_changes=[{'step':sid,'P':a['steps'][sid]['state'],'oracle':b['steps'][sid]['state']} for sid in root_ids if a['steps'][sid]['state']!=b['steps'][sid]['state']]
  closed_roots=[sid for sid in root_ids if any(not result['steps'][sid]['errors'] and result['steps'][sid]['state'] in ('TRUE','FALSE','CONFLICTED') for result in (a,b))]
  route_rows.append({'case_id':cid,'requests':len(a['requests']),'RAW_P_states':dict(collections.Counter(x['answer'] for x in a['requests'])),'oracle_states':dict(collections.Counter(x['answer'] for x in b['requests'])),'oracle_changed_requests':changed,'oracle_changed_root_step_states':root_changes,'usable_closed_root_steps':closed_roots,'only_use_gate_pending_steps_diagnostic_not_sufficient_for_gate':use_only,'operators':dict(collections.Counter(r['operator'] for r in snapshot['rules'].values())),'other_pending':dict(collections.Counter(p.split(':')[1] if ':' in p else p for st in a['steps'].values() for p in st.get('pending',[])))})
 cov=[{'split':s,'mechanism':m,'disputes':len(c['disputes']),'labels':dict(c['labels'])} for (s,m),c in sorted(coverage.items())];mechs={r['mechanism'] for r in rows if r['split']=='TRAIN' and r['valid'] and r['label'] in CLASSES};devmechs={r['mechanism'] for r in rows if r['split']=='DEV' and r['valid'] and r['label'] in CLASSES};route_signal=any(x['oracle_changed_requests'] or x['oracle_changed_root_step_states'] or x['usable_closed_root_steps'] for x in route_rows)
 gates={'common_interface_tests':'SEE_ENGINEERING_RECEIPT','DEV_all_four_mechanisms':mechs<=devmechs,'labels':'INTENDED_USE_CONTRACT_PRESERVED; OLD_P_VISIBLE_AND_NEW_BLIND_REFERENCE_MODES_DIFFER','real_downstream_use_class_influence':route_signal,'copy_space_disputes':len({x['key'].split('::')[0] for x in baselines['DEV']['RAW_P_disagreements']})};gateopen=bool(mechs<=devmechs and route_signal and gates['copy_space_disputes']>=2)
 # Even if these data checks pass, actual full encoding and resource gates remain required.
 audit={'TRAIN_labels_byte_source_unchanged':True,'TRAIN_disputes':len({r['dispute_id'] for r in rows if r['split']=='TRAIN' and r['valid'] and r['label'] in CLASSES}),'DEV_evaluable_disputes':len(dev_ids),'new_DEV_disputes':new,'coverage':cov,'baselines':baselines,'routes':route_rows,'gates':gates,'data_gates_open':gateopen,'training_started':False,'test_sealed_read':False,'reference_kind':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD','warning':'Reference replacement is diagnostic, not learner performance. Agreement is not legal truth. No learning model changes bindings, rule operator or premise truth.'}
 save(dest/'final-supervision.json',rows);save(dest/'data-task-audit.json',audit);print(json.dumps({k:audit[k] for k in ('TRAIN_disputes','DEV_evaluable_disputes','data_gates_open','gates')},indent=2))
if __name__=='__main__':main()
