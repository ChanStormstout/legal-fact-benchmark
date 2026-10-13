#!/usr/bin/env python3
"""Bounded V20 pipeline. No resume retries, no reference access in inference.
prepare -> acceptance -> freeze -> P -> Q -> web-label import -> encode -> fit -> finals -> score.
"""
import argparse,copy,datetime,hashlib,json,os,random,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from legal_bench.proof_carrying import source_verification_v20 as core
from legal_bench.proof_carrying.schema_contract_v19_6 import loads,validate
from legal_bench.proof_carrying.rule_contracts_v19_8 import attach
from legal_bench.proof_carrying.capacity_v19_8_1 import capacity
from legal_bench.proof_carrying.local_schedule_v19 import run as schedule,checkpoint,state
from legal_bench.proof_carrying.source_verification_check_v20 import check as application_check
from legal_bench.proof_carrying.local_evaluation_v17 import LABELS,blind_order,local_metrics,semantic_metrics,equal_dispute_summary,CLAIM_RULE
OUT=ROOT/'outputs/proof-source-verification-v20/continuation-01';BASE=ROOT/'outputs/proof-local-pipeline-v19'
SEED=20261001

def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);s=json.dumps(x,ensure_ascii=False,indent=2)+'\n'
 if p.exists() and p.read_text()!=s:raise ValueError('IMMUTABLE_RECORD:'+str(p))
 if not p.exists():p.write_text(s)
def text(p,s):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists() and p.read_text()!=s:raise ValueError('IMMUTABLE_TEXT:'+str(p))
 if not p.exists():p.write_text(s)
def fixture(cid):return read(OUT/'preparation'/cid/'fixture.json')
def tokenizer():
 from transformers import AutoTokenizer
 path=(ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip()
 return AutoTokenizer.from_pretrained(path,local_files_only=True)
def measured(prompt,tok,output):return capacity({'prompt':prompt},tok,{'max_output_tokens':output,'template_margin':256,'context_budget':65536})

def prepare():
 if (OUT/'preparation/plan.json').exists():return read(OUT/'preparation/plan.json')
 prior=read(BASE/'freeze/protocol.json');tok=tokenizer();slots=[];coverage=[]
 for cid in prior['TRAIN']+prior['DEV']:
  f=read(BASE/'preparation/inputs'/cid/'fixture.json')
  if f['case']['split'] not in ('TRAIN','DEV'):raise ValueError('FORBIDDEN_SPLIT')
  if sha(ROOT/f['case']['source_path'])!=f['case']['source_sha256']:raise ValueError('SOURCE_HASH_CHANGED')
  path=ROOT/'outputs/proof-pipeline-contract-v19-7/contracts'/ (cid+'.json')
  # Existing explicit contracts apply only when their rule hashes match.
  contract=read(path) if path.exists() else {'rules':{}}
  f['rules']=[attach([r],{**contract,'rules':{r['id']:contract['rules'][r['id']]}})[0] if r['id'] in contract['rules'] else core.adapt_rules([r])[0] for r in f['rules']]
  save(OUT/'preparation'/cid/'fixture.json',f)
  rules=f['rules'];existing=[s for s in prior['local_generation_slots'] if s['role']=='P' and s['case_id']==cid]
  for old in existing:
   part=old['part'];selected=[r for r in rules if r['id'] in part['rule_ids']]
   case={**f['case'],'segments':[s for s in f['case']['segments'] if s['id'] in part['source_ids']]}
   prompt=core.core.proposal_prompt(f['case'],rules,part);schema=core.core.schema(selected,case)
   cap=measured(prompt,tok,16384);task={'case_id':cid,'role':'P','part':part,'dest':'local/'+cid+'/'+part['id'],'output_tokens':16384,'capacity':cap}
   text(OUT/'preparation'/cid/(part['id']+'-prompt.txt'),prompt);save(OUT/'preparation'/cid/(part['id']+'-schema.json'),schema);slots.append(task)
  # Two ordered groups at most, based only on frozen rule order, never results.
  middle=(len(rules)+1)//2
  groups=[rules[:middle],rules[middle:]] if len(rules)>1 else [rules]
  for i,group in enumerate(groups,1):
   if group:slots.append({'case_id':cid,'role':'Q','part':{'id':f'Q{i:02d}','rule_ids':[r['id'] for r in group]},'dest':f'local/{cid}/Q{i:02d}','output_tokens':16384,'capacity':'CHECK_AFTER_P_NO_TRUNCATION'})
  coverage.append({'case_id':cid,'split':f['case']['split'],'source_units':len(f['case']['segments']),'rules':len(rules),
                   'unmapped_shared_contracts':[r['id'] for r in rules if r.get('unmapped_shared_variable_contract')],
                   'P_cache':'PRIOR_GENERATION_CONTRACT_INCOMPATIBLE; historic output retained, all planned P generated once'})
 # Existing fixed request-level reference checklists, not training inputs.
 refs=[]
 for cid in prior['DEV']:
  src=BASE/'private/frozen-references'/cid/'checklist.json'
  if src.exists():
   ref=read(src);save(OUT/'private/references'/cid/'checklist.json',ref)
   refs.append({'case_id':cid,'old_path':str(src.relative_to(ROOT)),'old_hash':sha(src),'status':'REUSED_FIXED_Q1_CHECKLIST_NOT_RUNTIME_INPUT'})
  else:refs.append({'case_id':cid,'status':'REFERENCE_TASK_REQUIRED'})
 finals=[]
 # Latin rotation of non-B methods; B remains after A within each case.
 for i,cid in enumerate(prior['DEV']):
  order=list('CDEFG');order=order[i%5:]+order[:i%5];order=['A','B']+order
  finals += [{'case_id':cid,'role':m,'dest':f'local/{cid}/{m}','output_tokens':8192} for m in order]
 slots += finals
 assert sum(s['role']=='P' for s in slots)<=87 and sum(s['role']=='Q' for s in slots)<=80 and len(finals)<=70
 plan={'version':core.VERSION,'TRAIN':prior['TRAIN'],'DEV':prior['DEV'],'slots':slots,'coverage':coverage,
       'reference_manifest':refs,'no_TEST_or_SEALED':True,'old_costs_separate':True}
 save(OUT/'preparation/plan.json',plan);return plan

def frozen():
 cfg=read(OUT/'freeze/protocol.json')
 for f,h in cfg['code_hashes'].items():
  if sha(ROOT/f)!=h:raise ValueError('FROZEN_CODE_CHANGED:'+f)
 for f,h in cfg.get('prepared_hashes',{}).items():
  if sha(ROOT/f)!=h:raise ValueError('FROZEN_MATERIAL_CHANGED:'+f)
 return cfg

def freeze():
 gate=read(OUT/'engineering/acceptance.json')
 if gate['status']!='PASS':raise ValueError('ENGINEERING_GATE')
 plan=prepare();files=sorted([*ROOT.glob('legal_bench/proof_carrying/*.py'),*ROOT.glob('legal_bench/mlx_json_constraint*.py'),ROOT/'scripts/proof_source_verification_v20_1.py',ROOT/'scripts/proof_pipeline_contract_v19_8.py',ROOT/'scripts/proof_semantic_encode_v13.py',ROOT/'scripts/proof_source_verification_accept_v20_1.py',ROOT/'tests/test_constraint_viability_v20_1.py',ROOT/'tests/test_source_verification_v20.py'])
 hashes={str(p.relative_to(ROOT)):sha(p) for p in files}
 for p in files:text(OUT/'freeze/code'/p.relative_to(ROOT),p.read_text())
 from legal_bench.proof_carrying.local_runtime_v20_1 import SETTINGS
 cfg={**plan,'constraint_revision':'V20_1_VIABLE_UNIQUE_ENUM','parent_protocol':'outputs/proof-source-verification-v20/freeze/protocol.json','reuse_policy':'All pre-pause successful P must pass exact-token replay under repaired constraint; old failures preserved and not retried; costs included in original stage totals','frozen_at':utc(),'code_hashes':hashes,'runtime':SETTINGS,'generation_seconds':129600,'stage_seconds':{'P':43200,'Q':43200,'final':43200},
      'per_call_seconds':3600,'training_seconds':86400,'training_dispatch_order':['Flat','RGCN','CrossEncoder'],'graph_fit_cap_seconds':14400,'web_calls':70,'fits':3,'seed':SEED,'retries':0,
      'graph_information':'identical complete source and relationship blocks for Flat/CrossEncoder/RGCN; reverse edges computational only',
      'training_runtime':{'Flat':'.runtime/qwen35-v1/bin/python3','CrossEncoder':'.runtime/proof-semantic-v12/bin/python3','RGCN':'.runtime/qwen35-v1/bin/python3','encoder':'.runtime/irac-e5-v1/bin/python3'},
      'P_stop':'two consecutive same REPETITION_ABORT or OUTPUT_TRUNCATED in fixed P order stop P only, save available parts; no retries',
      'input_policy':'P/Q full allowed source within predetermined parts; learners identical restored citation+Q witness+counterevidence+one adjacent unit packets; no label/reason features',
      'contract_limits':'Generic adaptation never infers shared variables or decomposes legal meaning; explicit contracts retained; unknown joins not claimed checked',
      'references':'MODEL_GENERATED_SOURCE_REVIEWED_NOT_HUMAN_GOLD; DEV forbidden in runtime',
      'review':{'mode':'Extra High','model':'RECORD_VISIBLE_AT_SUBMISSION','max_labels':40,'max_reference':10,'max_scores':20},
      'prepared_hashes':{str(p.relative_to(ROOT)):sha(p) for p in (OUT/'preparation').rglob('*') if p.is_file()},
      'staged_freeze':'TRAIN labels fixed before fit; dynamic Q and final inputs hashed before dispatch; DEV checklists fixed before answers'}
 save(OUT/'freeze/protocol.json',cfg);return cfg

def merged(cid,role):
 path=OUT/'assembled'/cid/(role+'.json')
 if path.exists():return read(path)
 cfg=frozen();f=fixture(cid);parts=[];statuses=[]
 for s in cfg['slots']:
  if s['case_id']!=cid or s['role']!=role:continue
  d=OUT/s['dest'];statuses.append({'part':s['part']['id'],'state':state(d)})
  if (d/'formal-answer.json').exists() and read(d/'formal-answer.json')['answer'] is not None:
   parts.append((s,read(d/'formal-answer.json')['answer']))
 if not parts:result={'answer':None,'status':'NO_READABLE_PART','parts':statuses}
 else:
  result={'answer':merge_raw(f,parts,role),'status':'ALL_PARTS_READABLE' if len(parts)==len(statuses) else 'PARTIAL','parts':statuses}
 save(path,result);return result

def merge_raw(f,parts,role):
 """Deterministic addresses and offsets only; missing refs stay invalid."""
 base={'analyses':{},'object_links':[],'coverage_limits':[]};verdicts=[]
 global_ids={s['id']:'SRC:'+str(i) for i,s in enumerate(f['case']['segments'],1)}
 for slot,value in parts:
  link_offset=len(base['object_links'])
  raw=copy.deepcopy(value['supplement'] if role=='Q' else value)
  allowed=slot['part'].get('source_ids',list(global_ids));local={f'SRC:{i}':global_ids[s['id']] for i,s in enumerate([s for s in f['case']['segments'] if s['id'] in allowed],1)}
  def source_map(x):
   if isinstance(x,list):return [source_map(v) for v in x]
   if isinstance(x,dict):return {k:([local.get(z,'INVALID_SOURCE:'+str(z)) for z in v] if k=='refs' else local.get(v,'INVALID_SOURCE:'+str(v)) if k=='source' else source_map(v)) for k,v in x.items()}
   return x
  raw=source_map(raw);offsets={}
  for pid,u in raw['analyses'].items():
   target=base['analyses'].setdefault(pid,{'analysis_status':'NOT_ANALYZED','records':[],'objects':[],'uses':[],'judgments':[],'limits':[]})
   offsets[pid]={'EV':len(target['records']),'OBJ':len(target['objects']),'USE':len(target['uses'])}
   def shift(v,prefix):
    import re
    m=re.fullmatch(prefix+r':([1-9][0-9]*)',v)
    # Verify existence against this part BEFORE offset; invalid stays invalid.
    count=len(u[{'EV':'records','OBJ':'objects','USE':'uses'}[prefix]])
    return prefix+':'+str(int(m[1])+offsets[pid][prefix]) if m and int(m[1])<=count else 'INVALID_LOCAL:'+v
   for row in u['uses']+u['judgments']:
    row['role_objects']={k:shift(v,'OBJ') if v!='UNMAPPED' else v for k,v in row['role_objects'].items()}
   for row in u['uses']:row['records']=[shift(v,'EV') for v in row['records']]
   for row in u['judgments']:
    for field in ('uses','opposition_uses'):row[field]=[shift(v,'USE') for v in row[field]]
    for comp in row['components']:comp['alternatives']=[[shift(v,'USE') for v in bundle] for bundle in comp['alternatives']]
   for field in ('records','objects','uses','judgments','limits'):target[field]+=u[field]
   if u['analysis_status']=='ANALYZED':target['analysis_status']='ANALYZED'
  for link in raw['object_links']:
   for side in ('left','right'):
    pid=link[side+'_premise'];ref=link[side+'_object']
    try:
     n=int(ref.split(':')[1]);count=len(raw['analyses'][pid]['objects'])
     link[side+'_object']='OBJ:'+str(n+offsets[pid]['OBJ']) if 0<n<=count else 'INVALID_LOCAL:'+ref
    except (ValueError,KeyError,IndexError):link[side+'_object']='INVALID_LOCAL:'+ref
   base['object_links'].append(link)
  base['coverage_limits']+=raw['coverage_limits']
  if role=='Q':
   # Q groups have disjoint premise scopes by preparation; no label-guided merging.
   for v in value['verdicts']:
    z=copy.deepcopy(v)
    if z['declaration'].startswith('Q/LINK:'):
     try:z['declaration']='Q/LINK:'+str(int(z['declaration'].split(':')[1])+link_offset)
     except ValueError:pass
    elif z['declaration'].startswith('P/LINK:'):
     prior=read(OUT/'assembled'/f['case']['case_id']/'P.json')['answer']
     ids=set(raw['analyses']);mapping=[i for i,link in enumerate(prior['object_links'],1) if link['left_premise'] in ids and link['right_premise'] in ids]
     try:
      n=int(z['declaration'].split(':')[1]);z['declaration']='P/LINK:'+str(mapping[n-1]) if 0<n<=len(mapping) else 'P/INVALID_LINK'
     except ValueError:z['declaration']='P/INVALID_LINK'
    z['refs']=[local.get(x,'INVALID_SOURCE:'+x) for x in z['refs']];z['counter_refs']=[local.get(x,'INVALID_SOURCE:'+x) for x in z['counter_refs']];verdicts.append(z)
 if role=='Q':return {'supplement':base,'verdicts':verdicts,'coverage_limits':[x for _,v in parts for x in v['coverage_limits']]}
 return base

def fail(dest,reason):
 result={'run_status':reason,'answer':None,'model_called':False};save(dest/'run.json',result);save(dest/'formal-answer.json',{'answer':None,'status':reason});return result

def run_generation(phase):
 cfg=frozen();slots=[s for s in cfg['slots'] if s['role']==phase] if phase in ('P','Q') else [s for s in cfg['slots'] if s['role'] in 'ABCDEFG']
 from legal_bench.proof_carrying.local_runtime_v20_1 import Runner,SETTINGS
 if cfg['runtime']!=SETTINGS:raise ValueError('RUNTIME_CHANGED')
 runner=None
 def perform(s,d):
  nonlocal runner
  cid=s['case_id'];f=fixture(cid);method=s['role'];p=None;q=None
  used=sum(read(OUT/z['dest']/'run.json').get('elapsed_seconds',0) or 0 for z in cfg['slots'] if (z['role'] if z['role'] in ('P','Q') else 'final')==phase and (OUT/z['dest']/'run.json').exists())
  remaining=cfg['stage_seconds'][phase]-used
  if remaining<=0:return fail(d,'STAGE_BUDGET_EXHAUSTED')
  if method=='P':
   prompt=(OUT/'preparation'/cid/(s['part']['id']+'-prompt.txt')).read_text();schema=read(OUT/'preparation'/cid/(s['part']['id']+'-schema.json'))
  elif method=='Q':
   p=merged(cid,'P')['answer']
   if p is None:return fail(d,'SKIPPED_P_DEPENDENCY')
   rules=[r for r in f['rules'] if r['id'] in s['part']['rule_ids']];ids={v['id'] for r in rules for v in r['premises']}
   p={'analyses':{k:v for k,v in p['analyses'].items() if k in ids},'object_links':[v for v in p['object_links'] if v['left_premise'] in ids and v['right_premise'] in ids],'coverage_limits':p['coverage_limits']}
   prompt=core.verification_prompt(f['case'],rules,p);schema=core.q_schema(rules,f['case'])
  else:
   p=merged(cid,'P')['answer'] if method in 'CDEFG' else None;q=merged(cid,'Q')['answer'] if method in 'DEFG' else None;pred=None;prior=None
   if method=='B':
    a=OUT/'local'/cid/'A/formal-answer.json';prior=read(a)['answer'] if a.exists() else None
   if method in 'EFG':
    path=OUT/'training'/ {'E':'Flat','F':'CrossEncoder','G':'RGCN'}[method]/'all-candidate-predictions.json'
    if not path.exists():return fail(d,'SKIPPED_TRAINING_DEPENDENCY')
    manifest=read(path.with_name('input-manifest.json'))
    if manifest['input_hash']!=sha(OUT/'encoding/pairs.json') or manifest['prediction_hash']!=sha(path):raise ValueError('STALE_PREDICTIONS')
    pred={v['key'].split('::',1)[1]:LABELS[max(range(3),key=lambda j:v['probabilities'][j])] for v in read(path) if v['key'].startswith(cid+'::')}
   try:task=core.final_task(f['case'],f['rules'],method,p,q,pred,prior)
   except ValueError as exc:return fail(d,'SKIPPED_DEPENDENCY:'+str(exc))
   save(d/'task-trace.json',task['trace']);save(d/'presentation.json',task['presentation_audit']);prompt=task['prompt'];schema=task['schema']
   if task['trace']:
    checked=application_check(p,q,task['trace'],f['rules']);save(d/'application-check.json',checked)
    if checked['status']!='OK':raise ValueError('APPLICATION_CHECK_FAILED')
  # Dynamic input is checked without changing the frozen method.
  cap=measured(prompt,tokenizer(),s['output_tokens']);save(d/'capacity.json',cap)
  if not cap['fits']:
   text(d/'prompt.txt',prompt);save(d/'schema.json',schema);return fail(d,'INPUT_TOO_LONG')
  if runner is None:runner=Runner((ROOT/'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt').read_text().strip(),SETTINGS)
  meta=runner.run(prompt,schema,d,s['output_tokens'],min(3600,remaining),'FIXED')
  answer=read(d/'parsed.json') if meta['run_status']=='OK' else None
  if method in 'ABCDEFG' and answer is not None:answer=core.core.accept_final(task,(d/'raw-response.txt').read_text(),'OK')['answer']
  formal_status=meta['run_status'] if answer is not None or meta['run_status']!='OK' else 'FINAL_CONTRACT_REJECTED'
  if answer is not None and method=='P':
   # Complete actual import/check path; source semantics deliberately not judged.
   from scripts.proof_pipeline_contract_v19_8 import process_saved
   audit=process_saved(f['case'],f['rules'],s['part'],(d/'raw-response.txt').read_text(),schema,'V19_8',meta['run_status']);save(d/'entry-audit.json',audit)
   if audit.get('contract_status') in ('PROCESSING_ERROR','IMPORT_REJECTED','MERGE_REJECTED','CHECK_REJECTED'):
    save(d/'formal-answer.json',{'answer':None,'status':audit['contract_status'],'semantics_reviewed':False})
    raise ValueError('SYSTEMATIC_ENTRY_ERROR:'+audit['contract_status'])
  save(d/'formal-answer.json',{'answer':answer,'status':formal_status,'semantics_reviewed':False})
  return meta
 def after(s,result):
  if phase!='P':return False
  done=[read(OUT/z['dest']/'run.json')['run_status'] for z in slots if (OUT/z['dest']/'run.json').exists()]
  stop=len(done)>1 and done[-1]==done[-2] and done[-1] in ('OUTPUT_TRUNCATED','REPETITION_ABORT')
  checkpoint(OUT,'P-progress',{'completed':len(done),'OK':done.count('OK'),'failures':len(done)-done.count('OK'),'consecutive_stop':stop})
  return stop
 result=schedule(OUT,slots,perform,after=after)
 checkpoint(OUT,'phase-'+phase,{'status':result,'at':utc()});print(result,flush=True)
 if phase in ('P','Q') and result in ('FINISHED','STOPPED_BY_FROZEN_RULE','STOPPED'):
  for cid in cfg['TRAIN']+cfg['DEV']:merged(cid,phase)
 return result

ANNOTATION='''Verify each exact semantic declaration against the supplied source blocks and fixed rules. English JSON in the response body only; no external search, no other conversation, no download-only output. Reference labels are model-generated, not human gold. Return {"labels":[{"id":"exact declaration ID","label":"SUPPORTED|UNSUPPORTED|UNRESOLVED","refs":["SRC:n"],"dispute":false,"requires_unseen_source":false,"reason":"precise source-grounded reason"}],"limitations":[]}.
SUPPORTED confirms this exact object/attribution/use/basis claim within its scope; lawful opposition can be supported. UNSUPPORTED needs a definite source, object, direction, attribution or scope error. Missing information is UNRESOLVED, not negative. A party claim does not establish its truth, relevant evidence need not suffice for a whole premise, and hypothetical events are not actual events. dispute=true only means a reasoned unresolved disagreement about your reference judgement; it does not mean disagreement with P, opposition direction or disputed litigation. Mark requires_unseen_source only if the label NEEDS source outside these blocks, not merely because additional context could help. No self-assessment or verifier verdict is provided. Do not supply corrected objects as runtime inputs.'''

def assemble_inputs():
 cfg=frozen();texts={};graphs={};plans={};pairs={};rows=[];coverage=[]
 for cid in cfg['TRAIN']+cfg['DEV']:
  f=fixture(cid);p=merged(cid,'P')['answer'];q=merged(cid,'Q')['answer']
  if p is None or q is None:coverage.append({'case_id':cid,'status':'P_Q_UNAVAILABLE'});continue
  pool=core.candidates(f['case'],f['rules'],p,q);data=core.common_inputs(f['case'],f['rules'],pool);trace=core.apply(f['case'],f['rules'],p,q)
  check=application_check(p,q,trace,f['rules'])
  if check['status']!='OK':raise ValueError('APPLICATION_CHECK')
  save(OUT/'inputs'/cid/'pool.json',pool);save(OUT/'inputs'/cid/'common.json',data);save(OUT/'inputs'/cid/'D-trace.json',trace)
  graphs[cid]=data['graph'];plans[cid]={'graph':[]}
  for n in data['graph']['nodes']:
   h=hashlib.sha256(n['text'].encode()).hexdigest();texts[h]=n['text'];plans[cid]['graph'].append({'node':n['id'],'part_sha256':[h]})
  for pair in data['ce_pairs']:
   key=cid+'::'+pair['id'];pairs[key]=pair;d=next(x for x in pool['candidates'] if x['id']==pair['id'])
   rows.append({'key':key,'case_id':cid,'dispute_id':cid,'original_dispute_id':f['case']['dispute_id'],'request_id':'Q1','use_id':pair['id'],'kind':d['kind'],'split':f['case']['split']})
  # The model gets exactly the same blocks as learners, but no Q labels/reasons.
  task=ANNOTATION+'\nDECLARATION IDS AND CLAIMS:\n'+core.compact([{'id':d['id'],'kind':d['kind'],'claim':d['claim']} for d in pool['candidates']])+'\nCOMMON SOURCE, RULE AND RELATION BLOCKS:\n'+core.compact(data['ce_pairs'][0]['shared_material_blocks'] if data['ce_pairs'] else [])
  text(OUT/'web/tasks'/cid/'labels.txt',task);save(OUT/'web/tasks'/cid/'manifest.json',{'kind':'LABELS','case_id':cid,'task_sha256':hashlib.sha256(task.encode()).hexdigest(),'required_mode':'Extra High','one_generation':True})
  coverage.append({'case_id':cid,'status':'READY','candidates':len(pool['candidates']),'source_coverage':data['coverage']})
 for name,value in [('texts',texts),('graphs',graphs),('plans',plans),('pairs',pairs),('inference-rows',rows)]:save(OUT/'encoding'/(name+'.json'),value)
 save(OUT/'data-coverage.json',coverage);return coverage

def labels():
 cfg=frozen();pool={r['key']:r for r in read(OUT/'encoding/inference-rows.json')};good=[];excluded=[]
 for cid in cfg['TRAIN']+cfg['DEV']:
  path=OUT/'web/replies'/cid/'labels.json'
  if not path.exists():continue
  receipt=read(path.with_name('receipt.json'))
  if receipt.get('thinking')!='Extra High' or not receipt.get('model_visible') or receipt.get('task_sha256')!=sha(OUT/'web/tasks'/cid/'labels.txt'):raise ValueError('WEB_PROVENANCE_MISMATCH')
  body=read(path);seen=set();duplicates={x['id'] for x in body['labels'] if x['id'] in seen or seen.add(x['id'])}
  data=read(OUT/'inputs'/cid/'common.json');visible={s['choice'] for s in data['source_mapping']}
  for v in body['labels']:
   key=cid+'::'+v['id'];reason=None
   if key not in pool or v['id'] in duplicates:reason='INVALID_OR_DUPLICATE_DECLARATION'
   elif v['label'] not in LABELS:reason='LABEL_CONTRACT'
   elif v.get('dispute') or v.get('requires_unseen_source'):reason='DISPUTED_OR_NECESSARY_SOURCE_NOT_VISIBLE'
   elif not v.get('refs') or any(ref not in visible for ref in v['refs']):reason='SOURCE_NOT_IN_ACTUAL_PACKET'
   if reason:excluded.append({'key':key,'reason':reason,'raw':v})
   else:good.append({**pool[key],'label':v['label'],'reference_path':str(path.relative_to(ROOT)),'reference_hash':sha(path)})
 save(OUT/'supervision/rows.json',good);save(OUT/'supervision/excluded.json',excluded)
 # Internal holdout is chosen by dispute hash before fitting, never official DEV.
 groups=sorted({r['case_id'] for r in good if r['split']=='TRAIN'},key=lambda x:hashlib.sha256((str(SEED)+x).encode()).hexdigest())
 val=set(groups[:max(1,len(groups)//5)]) if len(groups)>1 else set()
 fitting=[{**r,'split':'DEV' if r['case_id'] in val else 'TRAIN'} for r in good if r['split']=='TRAIN']
 train=[r for r in fitting if r['split']=='TRAIN'];gate=len({r['case_id'] for r in train})>=2 and {'SUPPORTED','UNSUPPORTED'}.issubset({r['label'] for r in train}) and bool(val)
 save(OUT/'supervision/fitting-rows.json',fitting);save(OUT/'supervision/gate.json',{'can_fit':gate,'internal_validation':sorted(val),'train_disputes':len(groups),'official_DEV_not_used_for_early_stop':True,'labels':len(good),'reason':None if gate else 'NO_VALID_MULTIDISPUTE_POSITIVE_NEGATIVE_TRAIN_OR_INTERNAL_HOLDOUT'})
 return gate

def fit_one(kind,seconds):
 cfg=frozen();rows=read(OUT/'supervision/fitting-rows.json');infer=read(OUT/'encoding/inference-rows.json');out=OUT/'training'/kind
 from legal_bench.proof_carrying.local_fit_v19 import fit_graph,fit_ce
 deadline=time.monotonic()+seconds
 if kind=='CrossEncoder':fit_ce(SEED,read(OUT/'encoding/pairs.json'),rows,out,deadline,inference_rows=infer)
 else:
  import numpy as np,mlx.core as mx
  from legal_bench.proof_carrying.semantic_model_inputs_v13 import graph_arrays
  gs=read(OUT/'encoding/graphs.json');plans=read(OUT/'encoding/plans.json');vectors=np.load(OUT/'encoding/vectors.npz');data={}
  for cid,g in gs.items():
   d=graph_arrays(g,plans[cid],vectors);data[cid]={**d,**{k:mx.array(d[k]) for k in ('x','adj','edges')}}
  fit_graph(kind,SEED,data,rows,out,deadline,inference_rows=infer)
 pred=out/'all-candidate-predictions.json'
 if pred.exists():save(out/'input-manifest.json',{'input_hash':sha(OUT/'encoding/pairs.json'),'supervision_hash':sha(OUT/'supervision/fitting-rows.json'),'prediction_hash':sha(pred),'official_DEV_in_training':False})

def fit():
 cfg=frozen()
 if not read(OUT/'supervision/gate.json')['can_fit']:return 'NO_VALID_SUPERVISION'
 for kind in cfg['training_dispatch_order']:
  out=OUT/'training'/kind
  if out.exists():continue
  used=sum(read(p).get('seconds',0) for p in (OUT/'training').glob('*/dispatch.json'))
  remaining=cfg['training_seconds']-used
  if remaining<=0:return 'TRAINING_BUDGET_EXHAUSTED'
  runtime='.runtime/proof-semantic-v12/bin/python3' if kind=='CrossEncoder' else '.runtime/qwen35-v1/bin/python3'
  allotted=min(remaining,cfg['graph_fit_cap_seconds']) if kind in ('Flat','RGCN') else remaining
  dispatch_start=time.monotonic()
  result=subprocess.run([str(ROOT/runtime),str(Path(__file__)), 'fit-one', '--kind',kind,'--seconds',str(allotted)])
  elapsed=time.monotonic()-dispatch_start
  save(out/'dispatch.json',{'kind':kind,'allotted_seconds':allotted,'seconds':elapsed,'returncode':result.returncode})
  if result.returncode and not (out/'failure.json').exists():
   save(out/'failure.json',{'status':'TECHNICAL_FAILURE','stage':'FIT_PROCESS','returncode':result.returncode,'seconds':elapsed,'answer':None})
 return 'FITS_FINISHED'

def score_tasks():
 cfg=frozen()
 for cid in cfg['DEV']:
  ref=OUT/'private/references'/cid/'checklist.json'
  if not ref.exists():continue
  mapping=blind_order(cid,list('ABCDEFG'),SEED);save(OUT/'private/blinding'/ (cid+'.json'),mapping)
  for part in (list(mapping.items())[:4],list(mapping.items())[4:]):
   answers=[]
   for neutral,method in part:
    path=OUT/'local'/cid/method/'formal-answer.json';a=read(path) if path.exists() else {'answer':None,'status':'NOT_STARTED'}
    answers.append({'answer_id':neutral,'answer':a['answer'],'technical_status':'OK' if a['answer'] is not None else a.get('status','TECHNICAL_FAILURE')})
   prompt='Evaluate these neutral answers against only the allowed source, rules and frozen checklist. English JSON in the response body. Do not search. Do not infer method from style. '+CLAIM_RULE+'\nReturn {"answers":[{"answer_id":"...","technical_status":"OK or supplied failure","answer":null,"key_items":[{"id":"every checklist item","status":"CORRECTLY_HANDLED|OMITTED|INCORRECT","reason":"with source refs"}],"substantive_judgements":[{"id":"unique","status":"SUPPORTED|CONFIRMED_ERROR_OR_UNSUPPORTED|DISPUTED|UNEVALUABLE","major":false,"reason":"with source refs"}],"overall":"COMPLETE_AND_SOURCED|PARTIAL|MAJOR_ERROR|DISPUTED_OR_UNEVALUABLE"}]}. Technical failures remain null; do not count them as UNKNOWN or correct abstention. Unlisted assertions require checking source, not automatic rejection.\nSOURCE AND RULES:\n'+core.compact(fixture(cid))+'\nFROZEN CHECKLIST:\n'+core.compact(read(ref))+'\nANSWERS:\n'+core.compact(answers)
   name='score-1' if part[0][0]==list(mapping)[0] else 'score-2';text(OUT/'web/tasks'/cid/(name+'.txt'),prompt)
 return 'READY'

def evaluate():
 cfg=frozen();supervised=read(OUT/'supervision/rows.json') if (OUT/'supervision/rows.json').exists() else []
 dev=[r for r in supervised if r['split']=='DEV'];local={};train=[r for r in supervised if r['split']=='TRAIN']
 prior={label:sum(r['label']==label for r in train)/len(train) if train else 0 for label in LABELS}
 if train:local['TRAIN_PRIOR']=local_metrics([{'key':r['key'],'probabilities':[prior[l] for l in LABELS]} for r in dev],dev)
 copyq=[];copyp=[]
 for cid in cfg['DEV']:
  pool=OUT/'inputs'/cid/'pool.json'
  if not pool.exists():continue
  for d in read(pool)['candidates']:
   key=cid+'::'+d['id']
   if key not in {r['key'] for r in dev}:continue
   copyq.append({'key':key,'label':d['proposed_label']})
   # Original P has synonymous support labels only for evidence-use claims.
   if d['origin']=='P' and d['kind']=='EVIDENCE_USE':
    p=merged(cid,'P')['answer'];pid,ref=d['id'].split('/')[1:3];n=int(ref.split(':')[1]);v=p['analyses'][pid]['uses'][n-1]['self_assessment']
    copyp.append({'key':key,'label':v})
 local['COPY_Q']=local_metrics(copyq,dev);local['COPY_P_SYNONYMOUS_USE_ONLY']=local_metrics(copyp,[r for r in dev if r['key'] in {x['key'] for x in copyp}])
 for kind in cfg['training_dispatch_order']:
  path=OUT/'training'/kind/'all-candidate-predictions.json'
  if path.exists():local[kind]=local_metrics([v for v in read(path) if v['key'] in {r['key'] for r in dev}],dev)
 checkpoint(OUT,'local-metrics',local)
 rows=[];failures=[]
 for cid in cfg['DEV']:
  mapping_path=OUT/'private/blinding'/(cid+'.json');mapping=read(mapping_path) if mapping_path.exists() else {}
  ref=OUT/'private/references'/cid/'checklist.json';scores={}
  if ref.exists():
   for part in ('score-1','score-2'):
    path=OUT/'web/replies'/cid/(part+'.json')
    if path.exists():scores.update(semantic_metrics(read(path),read(ref)))
  reverse={v:k for k,v in mapping.items()}
  for method in 'ABCDEFG':
   path=OUT/'local'/cid/method/'formal-answer.json';answer=read(path) if path.exists() else {'answer':None,'status':'NOT_STARTED'}
   metrics=scores.get(reverse.get(method),{});status='OK' if answer['answer'] is not None else answer.get('status','TECHNICAL_FAILURE')
   rows.append({'case_id':cid,'dispute_id':fixture(cid)['case']['dispute_id'],'method':method,'technical_status':status,'semantic_evaluation':'SOURCE_REVIEWED' if metrics else 'NOT_EVALUATED',**metrics})
   if answer['answer'] is None:failures.append({'case_id':cid,'method':method,'reason':status})
 summary={m:equal_dispute_summary([r for r in rows if r['method']==m],len(cfg['DEV'])) for m in 'ABCDEFG'}
 checkpoint(OUT,'final-evaluation',{'rows':rows,'summary':summary,'failures':failures,'not_human_gold':True,'no_weighted_winner':True})
 return summary

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','freeze','P','Q','inputs','labels','encode','fit','fit-one','final','score-tasks','evaluate']);ap.add_argument('--kind');ap.add_argument('--seconds',type=float);args=ap.parse_args();a=args.action
 if a=='prepare':print(core.compact(prepare())[:300])
 elif a=='freeze':print(freeze()['frozen_at'])
 elif a in ('P','Q','final'):run_generation(a)
 elif a=='inputs':assemble_inputs()
 elif a=='labels':print(labels())
 elif a=='encode':subprocess.run([str(ROOT/'.runtime/irac-e5-v1/bin/python3'),str(ROOT/'scripts/proof_semantic_encode_v13.py'),str(OUT/'encoding')],check=True)
 elif a=='fit':print(fit())
 elif a=='fit-one':fit_one(args.kind,args.seconds)
 elif a=='score-tasks':score_tasks()
 elif a=='evaluate':print(evaluate())
