#!/usr/bin/env python3
"""Bounded V20 pipeline. No resume retries, no reference access in inference.
prepare -> acceptance -> freeze -> P -> Q -> web-label import -> encode -> fit -> finals -> score.
"""
import argparse,copy,datetime,hashlib,json,os,random,subprocess,sys,time,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from legal_bench.proof_carrying import source_verification_v20_2 as core
from legal_bench.proof_carrying.schema_contract_v19_6 import loads,validate
from legal_bench.proof_carrying.rule_contracts_v19_8 import attach
from legal_bench.proof_carrying.capacity_v19_8_1 import capacity
from legal_bench.proof_carrying.local_schedule_v19 import run as schedule,checkpoint,state
from legal_bench.proof_carrying.source_verification_check_v20_2 import check as application_check
from legal_bench.proof_carrying.local_evaluation_v20_2 import LABELS,blind_order,local_metrics,semantic_metrics,equal_dispute_summary,CLAIM_RULE
OUT=ROOT/'outputs/proof-source-verification-repair-v20-2'
PARENT=ROOT/'outputs/proof-source-verification-v20/continuation-01';BASE=ROOT/'outputs/proof-local-pipeline-v19'
from legal_bench.proof_carrying.artifact_state_v20_2 import (composition, execution_context, freeze_files, verify_files, paused, terminal_parts, digest)
from legal_bench.proof_carrying.scoring_v20_2 import (local_answer, score_manifest, validate_score, evaluation_row)
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
 if (OUT/'preparation/repair-plan.json').exists():return read(OUT/'preparation/repair-plan.json')
 prior=read(PARENT/'freeze/protocol.json');verify_files(ROOT,prior)
 OUT.mkdir(parents=True,exist_ok=True)
 preserved=[]
 for area in ('preparation','local','private/references'):
  for src in sorted((PARENT/area).rglob('*')):
   if not src.is_file():continue
   rel=src.relative_to(PARENT);dest=OUT/rel;dest.parent.mkdir(parents=True,exist_ok=True)
   if dest.exists() and dest.read_bytes()!=src.read_bytes():raise ValueError('INCOMPATIBLE_PARENT_CACHE:'+str(rel))
   if not dest.exists():shutil.copyfile(src,dest)
   preserved.append({'original':str(src.relative_to(ROOT)),'copy':str(dest.relative_to(ROOT)),'sha256':sha(src)})
 # The copied old plan must not masquerade as this version's protocol.
 plan={k:copy.deepcopy(prior[k]) for k in ('TRAIN','DEV','slots','coverage','reference_manifest')}
 plan.update(version=core.VERSION,no_TEST_or_SEALED=True,parent_protocol=str((PARENT/'freeze/protocol.json').relative_to(ROOT)),
             reuse_policy='Byte-identical old calls; new deterministic processing only; old producer version and costs retained')
 # Parent plan is preserved separately; current plan is written under a new name.
 save(OUT/'preparation/repair-plan.json',plan);save(OUT/'preserved-parent-cache.json',preserved)
 return plan

def frozen():
 cfg=read(OUT/'freeze/protocol.json');verify_files(ROOT,cfg)
 return cfg

def freeze():
 gate=read(OUT/'engineering/tests-gate.json')
 if gate['status']!='PASS':raise ValueError('ENGINEERING_GATE')
 plan=prepare();prior=read(PARENT/'freeze/protocol.json')
 entries=['scripts/proof_source_verification_v20_2.py','scripts/proof_semantic_encode_v13.py',
          'scripts/proof_source_verification_accept_v20_2.py','tests/test_source_verification_v20_2.py']
 prepared=[str(p.relative_to(ROOT)) for area in ('preparation','local','private/references') for p in (OUT/area).rglob('*') if p.is_file()]
 configurations=['outputs/gnn-irac-aligned-v2/text-cache/encoder.json',
                 'outputs/local-qwen-pattern-eval-v3/environment/model-path.txt',
                 '.runtime/proof-semantic-v12-model/config.json']
 manifest=freeze_files(ROOT,OUT,entries,prepared,configurations)
 keys=('runtime','generation_seconds','stage_seconds','per_call_seconds','training_seconds','training_dispatch_order',
       'graph_fit_cap_seconds','web_calls','fits','seed','retries','training_runtime')
 cfg={**plan,**{k:copy.deepcopy(prior[k]) for k in keys},**manifest,'frozen_at':utc(),
      'constraint_revision':prior['constraint_revision'],'original_generation_contract_unchanged':True,
      'execution_state':'PAUSED_ENGINEERING_REPAIR_ONLY','staged_freeze':'composition snapshots, inputs and score tasks bind hashes before use'}
 save(OUT/'freeze/protocol.json',cfg);return cfg

def merged(cid,role):
 cfg=frozen();f=fixture(cid)
 return composition(ROOT,OUT,cid,role,cfg['slots'],f,merge_raw)

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
     prior=merged(f['case']['case_id'],'P')['answer']
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
 if paused(OUT):return 'PAUSED'
 cfg=frozen();slots=[s for s in cfg['slots'] if s['role']==phase] if phase in ('P','Q') else [s for s in cfg['slots'] if s['role'] in 'ABCDEFG']
 if phase=='P':
  done=[read(OUT/s['dest']/'run.json')['run_status'] for s in slots if (OUT/s['dest']/'run.json').exists()]
  if len(done)>1 and done[-1]==done[-2] and done[-1] in ('OUTPUT_TRUNCATED','REPETITION_ABORT'):
   return 'STOPPED_BY_FROZEN_RULE'
 from legal_bench.proof_carrying.local_runtime_v20_1 import Runner,SETTINGS
 if cfg['runtime']!=SETTINGS:raise ValueError('RUNTIME_CHANGED')
 runner=None
 def perform(s,d):
  nonlocal runner
  cid=s['case_id'];f=fixture(cid);method=s['role'];p=None;q=None;context=None
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
   pw=merged(cid,'P') if method in 'CDEFG' else None;qw=merged(cid,'Q') if method in 'DEFG' else None
   p=pw['answer'] if pw else None;q=qw['answer'] if qw else None;pred=None;prior=None
   context=execution_context(pw,qw) if qw else {'P':{k:pw[k] for k in ('status','parts','snapshot_sha256')}} if pw else None
   if method=='B':
    a=OUT/'local'/cid/'A/formal-answer.json';prior=read(a)['answer'] if a.exists() else None
   if method in 'EFG':
    path=OUT/'training'/ {'E':'Flat','F':'CrossEncoder','G':'RGCN'}[method]/'all-candidate-predictions.json'
    if not path.exists():return fail(d,'SKIPPED_TRAINING_DEPENDENCY')
    manifest=read(path.with_name('input-manifest.json'))
    if manifest.get('version')!=core.VERSION:raise ValueError('PREDICTION_VERSION_CHANGED')
    verify_model_inputs(manifest['model_input_hashes'])
    if manifest['input_hash']!=sha(OUT/'encoding/pairs.json') or manifest['prediction_hash']!=sha(path):raise ValueError('STALE_PREDICTIONS')
    prior_input=read(OUT/'encoding/material-manifest.json')['cases'].get(cid)
    fresh_pool=core.candidates(f['case'],f['rules'],p,q,context)
    fresh_input=core.common_inputs(f['case'],f['rules'],fresh_pool)
    if prior_input!={'composition_sha256':digest(context),'common_input_sha256':fresh_input['input_sha256']}:
     raise ValueError('PREDICTION_COMPOSITION_CHANGED')
    pred={v['key'].split('::',1)[1]:LABELS[max(range(3),key=lambda j:v['probabilities'][j])] for v in read(path) if v['key'].startswith(cid+'::')}
   try:task=core.final_task(f['case'],f['rules'],method,p,q,pred,prior,execution=context)
   except ValueError as exc:return fail(d,'SKIPPED_DEPENDENCY:'+str(exc))
   save(d/'task-trace.json',task['trace']);save(d/'presentation.json',task['presentation_audit']);prompt=task['prompt'];schema=task['schema']
   if task['trace']:
    checked=application_check(p,q,task['trace'],f['rules'],context);save(d/'application-check.json',checked)
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
  if method=='Q' and answer is not None:
   audit=core.candidates(f['case'],rules,p,answer)
   save(d/'verification-coverage.json',audit['verification_coverage'])
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

def assemble_case(cid):
 f=fixture(cid);pw=merged(cid,'P');qw=merged(cid,'Q');p=pw['answer'];q=qw['answer']
 if p is None or q is None:return {'case_id':cid,'status':'P_Q_UNAVAILABLE','execution':execution_context(pw,qw)}
 context=execution_context(pw,qw);pool=core.candidates(f['case'],f['rules'],p,q,context)
 data=core.common_inputs(f['case'],f['rules'],pool);trace=core.apply(f['case'],f['rules'],p,q,execution=context)
 check=application_check(p,q,trace,f['rules'],context)
 if check['status']!='OK':raise ValueError('APPLICATION_CHECK:'+core.compact(check))
 key=digest(context);dest=OUT/'inputs'/cid/key
 for name,value in [('pool',pool),('common',data),('D-trace',trace),('application-check',check),('execution',context)]:save(dest/(name+'.json'),value)
 return {'case_id':cid,'status':'READY','snapshot':key,'path':str(dest.relative_to(OUT)),
         'candidates':len(pool['candidates']),'source_coverage':data['coverage'],'verification_coverage':pool['verification_coverage']}

def assemble_inputs():
 cfg=frozen();terminal_parts(OUT,cfg['slots'],'Q')
 texts={};graphs={};plans={};pairs={};rows=[];coverage=[];case_inputs={}
 for cid in cfg['TRAIN']+cfg['DEV']:
  result=assemble_case(cid);coverage.append(result)
  if result['status']!='READY':continue
  f=fixture(cid);dest=OUT/result['path'];pool=read(dest/'pool.json');data=read(dest/'common.json')
  case_inputs[cid]={'composition_sha256':result['snapshot'],'common_input_sha256':data['input_sha256']}
  # Stable convenience files are frozen only after all Q positions are terminal.
  for name in ('pool','common','D-trace','application-check','execution'):save(OUT/'inputs'/cid/(name+'.json'),read(dest/(name+'.json')))
  graphs[cid]=data['graph'];plans[cid]={'graph':[]}
  for n in data['graph']['nodes']:
   h=hashlib.sha256(n['text'].encode()).hexdigest();texts[h]=n['text'];plans[cid]['graph'].append({'node':n['id'],'part_sha256':[h]})
  for pair in data['ce_pairs']:
   key=cid+'::'+pair['id'];pairs[key]=pair;d=next(x for x in pool['candidates'] if x['id']==pair['id'])
   rows.append({'key':key,'case_id':cid,'dispute_id':cid,'original_dispute_id':f['case']['dispute_id'],'request_id':'Q1','use_id':pair['id'],'kind':d['kind'],'split':f['case']['split']})
  task=ANNOTATION+'\nDECLARATION IDS AND CLAIMS:\n'+core.compact([{'id':d['id'],'kind':d['kind'],'claim':d['claim']} for d in pool['candidates']])+'\nCOMMON SOURCE, RULE AND RELATION BLOCKS:\n'+core.compact(data['ce_pairs'][0]['shared_material_blocks'] if data['ce_pairs'] else [])
  text(OUT/'web/tasks'/cid/'labels.txt',task);save(OUT/'web/tasks'/cid/'manifest.json',{'kind':'LABELS','case_id':cid,'task_sha256':hashlib.sha256(task.encode()).hexdigest(),'required_mode':'Extra High','one_generation':True})
 for name,value in [('texts',texts),('graphs',graphs),('plans',plans),('pairs',pairs),('inference-rows',rows)]:save(OUT/'encoding'/(name+'.json'),value)
 save(OUT/'encoding/material-manifest.json',{'version':core.VERSION,'cases':case_inputs})
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

def model_input_hashes():
 names=['encoding/pairs.json','encoding/graphs.json','encoding/plans.json','encoding/inference-rows.json',
        'encoding/material-manifest.json','supervision/fitting-rows.json','encoding/vectors.npz','encoding/encoding.json']
 return {name:sha(OUT/name) for name in names}

def verify_model_inputs(hashes):
 for name,expected in hashes.items():
  if sha(OUT/name)!=expected:raise ValueError('MODEL_INPUT_CHANGED:'+name)

def fit_one(kind,seconds):
 if paused(OUT):return 'PAUSED'
 cfg=frozen();inputs=model_input_hashes();rows=read(OUT/'supervision/fitting-rows.json');infer=read(OUT/'encoding/inference-rows.json');out=OUT/'training'/kind
 from legal_bench.proof_carrying.local_fit_v20_2 import fit_graph,fit_ce
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
 verify_model_inputs(inputs)
 if pred.exists():save(out/'input-manifest.json',{'version':core.VERSION,'model_input_hashes':inputs,'input_hash':sha(OUT/'encoding/pairs.json'),'supervision_hash':sha(OUT/'supervision/fitting-rows.json'),'prediction_hash':sha(pred),'official_DEV_in_training':False})

def fit():
 if paused(OUT):return 'PAUSED'
 cfg=frozen()
 if not read(OUT/'supervision/gate.json')['can_fit']:return 'NO_VALID_SUPERVISION'
 for kind in cfg['training_dispatch_order']:
  if paused(OUT):return 'PAUSED'
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
  mapping=blind_order(cid,list('ABCDEFG'),SEED);save(OUT/'private/blinding'/(cid+'.json'),mapping)
  for index,part in enumerate((list(mapping.items())[:4],list(mapping.items())[4:]),1):
   name='score-'+str(index);actuals={aid:local_answer(OUT,cid,method) for aid,method in part}
   f=fixture(cid)
   prompt='Evaluate these neutral answers against only the allowed source, rules and frozen checklist. English JSON in the response body; no external search. '+CLAIM_RULE+'\nReturn {"answers":[{"answer_id":"exact supplied ID","technical_status":"exact supplied local status","answer":null,"key_items":[{"id":"every checklist item","status":"CORRECTLY_HANDLED|OMITTED|INCORRECT","reason":"with source refs"}],"substantive_judgements":[{"id":"unique","status":"SUPPORTED|CONFIRMED_ERROR_OR_UNSUPPORTED|DISPUTED|UNEVALUABLE","major":false,"reason":"with source refs"}],"overall":"COMPLETE_AND_SOURCED|PARTIAL|MAJOR_ERROR|DISPUTED_OR_UNEVALUABLE"}]}. Include every supplied ID once. A technical failure remains the supplied status and null, with no semantic success score.\nSOURCE AND RULES:\n'+core.compact(f)+'\nFROZEN CHECKLIST:\n'+core.compact(read(ref))+'\nANSWERS:\n'+core.compact(actuals)
   text(OUT/'web/tasks'/cid/(name+'.txt'),prompt)
   save(OUT/'web/tasks'/cid/(name+'.manifest.json'),score_manifest(cid,name,prompt,f,ref,mapping,actuals))
 return 'READY'

def evaluate():
 cfg=frozen();supervised=read(OUT/'supervision/rows.json') if (OUT/'supervision/rows.json').exists() else []
 dev=[r for r in supervised if r['split']=='DEV'];train=[r for r in supervised if r['split']=='TRAIN'];local={}
 prior={label:sum(r['label']==label for r in train)/len(train) if train else 0 for label in LABELS}
 if train:local['TRAIN_PRIOR']=local_metrics([{'key':r['key'],'probabilities':[prior[l] for l in LABELS]} for r in dev],dev)
 copyq=[];copyp=[];keys={r['key'] for r in dev}
 for cid in cfg['DEV']:
  path=OUT/'inputs'/cid/'pool.json'
  if not path.exists():continue
  for d in read(path)['candidates']:
   key=cid+'::'+d['id']
   if key not in keys:continue
   copyq.append({'key':key,'label':d['proposed_label']})
   if d['origin']=='P' and d['kind']=='EVIDENCE_USE':
    p=merged(cid,'P')['answer'];pid,ref=d['id'].split('/')[1:3];n=int(ref.split(':')[1]);copyp.append({'key':key,'label':p['analyses'][pid]['uses'][n-1]['self_assessment']})
 local['COPY_Q']=local_metrics(copyq,dev)
 local['COPY_P_SYNONYMOUS_USE_ONLY']=local_metrics(copyp,[r for r in dev if r['key'] in {x['key'] for x in copyp}])
 for kind in cfg['training_dispatch_order']:
  path=OUT/'training'/kind/'all-candidate-predictions.json'
  if path.exists():
   try:local[kind]=local_metrics([v for v in read(path) if v['key'] in keys],dev)
   except ValueError as exc:local[kind]={'status':'INVALID_PREDICTION_RECORD','error':str(exc),'macro_f1_all_three':None}
 checkpoint(OUT,'local-metrics',local)
 rows=[];failures=[];rejected_scores=[]
 for cid in cfg['DEV']:
  path=OUT/'private/blinding'/(cid+'.json');mapping=read(path) if path.exists() else {}
  ref=OUT/'private/references'/cid/'checklist.json';scores={};seen=set()
  for name in ('score-1','score-2'):
   reply=OUT/'web/replies'/cid/(name+'.json')
   if not reply.exists():continue
   try:
    result,ids=validate_score(OUT,cid,name,fixture(cid),mapping,ref)
    if seen.intersection(ids):raise ValueError('DUPLICATE_ANSWER_ACROSS_SCORE_BATCHES')
    scores.update(result);seen.update(ids)
   except (ValueError,KeyError,TypeError,FileNotFoundError) as exc:rejected_scores.append({'case_id':cid,'batch':name,'error':str(exc)})
  reverse={v:k for k,v in mapping.items()}
  for method in 'ABCDEFG':
   actual=local_answer(OUT,cid,method);metrics=scores.get(reverse.get(method))
   rows.append(evaluation_row(cid,fixture(cid)['case']['dispute_id'],method,actual,metrics))
   if actual['answer'] is None:failures.append({'case_id':cid,'method':method,'reason':actual['technical_status']})
 summary={m:equal_dispute_summary([r for r in rows if r['method']==m],len(cfg['DEV'])) for m in 'ABCDEFG'}
 checkpoint(OUT,'final-evaluation',{'rows':rows,'summary':summary,'failures':failures,'rejected_scores':rejected_scores,'not_human_gold':True,'no_weighted_winner':True})
 return summary

def encode():
 if paused(OUT):return 'PAUSED'
 frozen()
 return subprocess.run([str(ROOT/'.runtime/irac-e5-v1/bin/python3'),str(ROOT/'scripts/proof_semantic_encode_v13.py'),str(OUT/'encoding')],check=True)

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','freeze','P','Q','inputs','labels','encode','fit','fit-one','final','score-tasks','evaluate']);ap.add_argument('--kind');ap.add_argument('--seconds',type=float);args=ap.parse_args();a=args.action
 if a=='prepare':print(core.compact(prepare())[:300])
 elif a=='freeze':print(freeze()['frozen_at'])
 elif a in ('P','Q','final'):run_generation(a)
 elif a=='inputs':assemble_inputs()
 elif a=='labels':print(labels())
 elif a=='encode':encode()
 elif a=='fit':print(fit())
 elif a=='fit-one':fit_one(args.kind,args.seconds)
 elif a=='score-tasks':score_tasks()
 elif a=='evaluate':print(evaluate())
