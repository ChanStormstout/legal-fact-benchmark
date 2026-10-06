"""Bounded DEV contract repair preparation; no training, SEALED body or rankings."""
import sys,json,hashlib,random,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.rgcn09_labels import INSTRUCTIONS,model_material
from legal_bench.rules_verdict_v1 import legal_material_v10 as material
R=Path('outputs/rgcn-dev-contract-repair-10');B=Path('outputs/rgcn-data-expansion-09');D=Path('outputs/rgcn-ranking-development-06');T=B/'main-training-01';I=B/'continuation-03/imports/final-01'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
 p=R/p;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError(p)
 p.write_text(x if isinstance(x,str) else json.dumps(x,ensure_ascii=False,indent=2)+'\n')
conditions=read(B/'continuation-01/freeze/source-condition-proposals.json');pool=read(B/'authority-pool/laws.json');split=read(B/'continuation-03/split-manifest.json')['cases'];cfg=read(T/'protocol.json')['config'];dev=cfg['dev_ids'];train=cfg['train_ids']
save('protocol.json',{'dev':dev,'train':train,'sealed_ids':[x['case_id'] for x in split if x['split']=='SEALED_TEST'],'pool':30,'seed':20261006,'preparation_calls_planned':22,'preparation_calls_max':24,'semantic_retry':0,'legal_answers':0,'training_fits':6,'training_settings':cfg,'input_alignment_review_labels_not_visible':True,'method_ranking_not_visible_to_preparation':True,'train_sample':24,'special_sample':8,'stop_on_systematic_semantic_mismatch':True,'no_class_or_architecture_search':True,'all180_dev_slots_have_status_required':True,'old_ranking_reevaluation_before_new_training':True})
save('sources-laws.json',pool);save('source-conditions.json',conditions);save('split-manifest.json',split)
ledger=[]
def task(tid,role,instr,data):
 text=instr+'\nMATERIAL\n'+json.dumps(data,ensure_ascii=False)+'\nEND_OF_INPUT '+tid+'\n'
 save('tasks/'+tid+'.txt',text);ledger.append({'task_id':tid,'role':role,'path':str(R/'tasks'/ (tid+'.txt')),'sha256':hashlib.sha256(text.encode()).hexdigest(),'characters':len(text),'status':'PREPARED'})
prefix=(D/'tasks/GRAPH01.txt').read_text().split('MATERIAL')[0].replace('TASK GRAPH01','TASK V10-DEV-ALIGNMENT').replace('all14','all30').replace('All14','All30')
# Keep complete examples/enum definitions already used; no held-case facts or labels added.
align_instr=prefix+'\nSUPPLEMENT: use the fixed needs/objects/facts/relations unchanged, no full re-extraction. Return ONLY {case_id,alignments,coverage_limits}, exactly30 alignments using the interface above. Reassess old14 and new16 under the shared source-condition proposals. No usefulness labels, scores, model rankings or target conclusions are supplied. Empty links with UNKNOWN mean unresolved/unprocessed; NONE or INCOMPATIBLE requires a concrete source-grounded reason. Never infer identity from role labels. Old fact omissions/unsupported assertions can be noted as coverage limits, not silently corrected. Supply short exact law_quote strings. Output a downloadable full JSON file and one complete JSON code block if feasible; no extra narrative.\n'
label_instr=INSTRUCTIONS+'\nCORE standard: absence would leave an explicit important issue or substantive limit/counterargument insufficiently discussed; importance is not support for one party. Some factual conditions can be unknown while an authority is clearly useful. UNKNOWN is for indeterminate usefulness, not mechanically for every unknown fact. Every30 candidate needs one coarse state; no unmarked positions. Prior NO_USE is not supplied as truth. Preserve opposing arguments, lower findings and stated source limits. Output a downloadable JSON.\n'
samples={x['case_id']:x for x in read(D/'sources/samples.json')}
for cid in dev:
 case=read(D/'sources'/ (cid+'.json'));save('dev-sources/'+cid+'.json',case)
 proposal=next(read(f) for f in (D/'parsed').glob('GRAPH*.json') if str(read(f)['case_id'])==cid);save('dev-fixed/'+cid+'.json',proposal)
 rejected=next(read(f) for f in (D/'parsed').glob('GREV*.json') if str(read(f)['case_id'])==cid);save('dev-old-review/'+cid+'.json',rejected)
 fixed={k:proposal[k] for k in ('case_id','needs','objects','facts','relations')};view,laws=model_material(case,pool)
 data={'case_id':cid,'question':samples[cid]['question'],'case':view,'authority_candidates':[material.payload(u) for u in pool]}
 task('ALIGN-'+cid,'INPUT_NO_LABELS',align_instr,dict(data,fixed_graph_input=fixed,source_condition_proposals=conditions))
 task('LABEL-'+cid,'REFERENCE_PREPARATION',label_instr,dict(data,annotation_target_ids=[u['id'] for u in pool]))
# Preserve original TRAIN labels and quality; only reversible quote-location restoration may follow.
accepted=[]
for cid in train:
 lab=read(T/'labels'/ (cid+'.json'));save('train-original-labels/'+cid+'.json',lab)
 for row in lab['uses']:
  if cid=='125596702':continue
  quality='OLD_SOURCE_REVIEWED' if cid in train[:10] and not row['unit_id'].startswith('LAW:V09:') else 'NEW_SINGLE_PASS_ANCHOR_CHECKED'
  accepted.append(dict(case_id=cid,quality=quality,record=row))
rng=random.Random(20261006);selected=[]
for quality in ['OLD_SOURCE_REVIEWED','NEW_SINGLE_PASS_ANCHOR_CHECKED']:
 for cat in ['CORE','BACKGROUND','IRRELEVANT']:
  normalized={'DIRECT':'CORE','EXCEPTION_COUNTER':'CORE'}
  options=[x for x in accepted if x['quality']==quality and normalized.get(x['record']['category'],x['record']['category'])==cat]
  rng.shuffle(options)
  used=set()
  for x in options:
   if x['case_id'] in used:continue
   selected.append(x);used.add(x['case_id'])
   if len(used)==4:break
assert len(selected)==24
save('train-review-sample.json',{'seed':20261006,'rows':selected,'rule':'four different cases per old/new x three classes, deterministic shuffle; no model performance used; high-missing and mechanism coverage reported','mechanism_metadata':{x['case_id']:x.get('mechanism','OLD_NO_UNIFIED_MECHANISM') for x in split if x['split']=='TRAIN'},'sample_case_counts':{c:sum(x['case_id']==c for x in selected) for c in sorted({x['case_id'] for x in selected})}})
review_instr='''This is a bounded source review, not a legal answer or model comparison. Use only provided allowed source and authority text. No external search or target final judgment. Each row is a proposed use label, not verified truth. Check statement attribution, court stage, object scope, authority prerequisites/counterarguments and coarse usefulness. Location success is not semantic correctness. Return one downloadable JSON plus complete JSON code block: {"reviews":[{"case_id":"EXAMPLE","unit_id":"LAW:EXAMPLE","decision":"SUPPORTED","reason":"The allowed tenant claim makes the supplied control rule material, without treating the claim as a finding.","case_refs":["EXAMPLE:L1"],"law_quote":"Control must be assessed.","suggested_category":"CORE"}],"systematic_issues":[],"coverage_limits":[]}. decision is SUPPORTED, QUALIFIED, CORRECTION_NEEDED or UNRESOLVED. suggested_category is CORE,BACKGROUND,IRRELEVANT,UNKNOWN; do not reconstruct verdict. Cover every supplied sample once, preserve specific disagreement. Unsupported quote snippets remain problems, no ellipsis filling. Never use label disagreement alone to claim systematic error; describe repeating semantic mechanism if present.'''
for i in range(3):
 batch=selected[i*8:(i+1)*8];cases={}
 for row in batch:
  cid=row['case_id'];p=Path('outputs/rgcn-ranking-diagnostic-07/pilot/sources')/(cid+'.json') if cid in train[:10] else B/'continuation-01/freeze/allowed'/(cid+'.json');cases[cid]=model_material(read(p),[])[0]
 task('TRAIN-REVIEW-'+str(i+1),'SOURCE_REVIEW',review_instr,{'samples':batch,'case_sources':cases,'authorities':[material.payload(u) for u in pool]})
special=read(T/'labels/125596702.json')['uses'];task('TRAIN-SPECIAL-125596702','SOURCE_REVIEW',review_instr,{'samples':[{'case_id':'125596702','quality':'DUPLICATE_PROVENANCE_PARTIAL_LABELS','record':x} for x in special],'case_sources':{'125596702':model_material(read(B/'continuation-01/freeze/allowed/125596702.json'),[])[0]},'authorities':[material.payload(u) for u in pool]})
save('prepared-task-ledger.json',ledger)
save('task-freeze.json',{'files':{str(p):sha(p) for p in (R/'tasks').glob('*.txt')},'source_hashes':{str(p):sha(p) for p in list((R/'dev-sources').glob('*.json'))+[B/'authority-pool/laws.json',B/'continuation-01/freeze/source-condition-proposals.json']},'pending_review_tasks':6,'total_planned':22,'not_seen_rankings':True})
print([(x['task_id'],x['characters']) for x in ledger])
