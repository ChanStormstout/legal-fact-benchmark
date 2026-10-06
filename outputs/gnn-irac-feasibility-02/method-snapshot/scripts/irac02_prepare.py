"""Bounded IRAC repair preparation, immutable historical inputs, no training."""
import json,hashlib,subprocess,datetime,sys
from pathlib import Path
R=Path('outputs/gnn-irac-feasibility-02');OLD=Path('outputs/gnn-irac-feasibility-01');PARENT='43d8b774e70479250584367bcc9856d080adaa25'
IDS=['308216','38604742','1106992','1497837','1859043','111425525','758831','1381386']
def rd(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(n,v):
 p=R/n;p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists(),p;p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def task(n,instruction,data):
 p=R/'tasks'/f'{n}.txt';p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_text(instruction+'\nMATERIAL\n'+json.dumps(data,ensure_ascii=False,indent=2)+'\nEND_OF_TASK '+n+'\n')
def integrity():
 rows=[]
 raw=subprocess.check_output(['git','ls-tree','-r',PARENT,'outputs/rgcn-sbc-finalization-11','outputs/gnn-irac-feasibility-01'],text=True)
 for line in raw.splitlines():
  meta,path=line.split('\t');expected=meta.split()[2];b=Path(path).read_bytes();actual=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest();rows.append({'path':path,'parent_blob':expected,'current_blob':actual,'sha256':hashlib.sha256(b).hexdigest(),'unchanged':actual==expected})
 return {'parent':PARENT,'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'branch':subprocess.check_output(['git','branch','--show-current'],text=True).strip(),'all_unchanged':all(x['unchanged'] for x in rows),'files':rows}
if __name__=='__main__':
 put('parent-integrity.json',integrity());put('fixed-case-manifest.json',rd(OLD/'case-manifest.json'))
 put('protocol.json',{'parent':PARENT,'case_ids':IDS,'scope':'Three blockers only: independent decisive tests, blind bindings, unified stage gate','rule_tests_added_per_case_max':2,'ordinary_High_calls_max':16,'expected_calls':14,'technical_retry_max':2,'semantic_retry':0,'training':False,'new_legal_answers':False,'sealed_read':False,'no_commit_no_push':True,'sequence':['stage review 2','rule-only proposal 2','rule review 2','rule/condition and stage freezes','blind bindings 4','blind freeze','target reconstruction 2','final review 2'],'readiness':{'GO':'6+ READY without systemic blocker','CONDITIONAL_GO':'4-5 READY with one limited engineering gap','NO_GO':'<4 READY or systemic rule/stage/binding blocker'},'reference_role':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD','time':datetime.datetime.now(datetime.timezone.utc).isoformat()})
 policy={'allowed':['PRE_TARGET_RECORD','PRIOR_COURT_FINDING','TARGET_STAGE_PARTY_ARGUMENT'],'forbidden':['TARGET_COURT_REASONING','TARGET_DISPOSITION','AMBIGUOUS'],'availability':['DIRECT_PRE_TARGET_SOURCE','RETROSPECTIVELY_RECONSTRUCTED_PRE_TARGET','UNKNOWN'],'all_record_types':True,'unknown_is_not_false':True,'no_promotion_of_prior_findings':True,'source_ref_gate':'Every referenced target passage must itself be allowed; mixed passage excludes record, no semantic rewrite.'};put('stage-policy.json',policy)
 cases=[]
 for cid in IDS:
  x=rd(OLD/'inputs'/f'{cid}.json');inv=x['existing_inventory'];g=rd(OLD/'interface-export-v2/input-graphs'/f'{cid}.json');records=[]
  for kind in ['facts','objects','relations','issue_needs_context_not_application_targets','quarantined']:
   for i,rec in enumerate(inv.get(kind,[])):
    ident=rec.get('id',str(i+1)) if isinstance(rec,dict) else str(i+1)
    records.append({'record_id':kind+':'+ident,'kind':kind,'original':rec})
  for s in x['pre_outcome_source']['segments']:records.append({'record_id':'source:'+s['id'],'kind':'SourcePassage','original':{k:v for k,v in s.items() if k in ['id','text','source_document','source_segment_id','start','end']}})
  for i,n in enumerate(g['nodes']):
   if n.get('type') not in ['SourcePassage','Fact','Object']:records.append({'record_id':'graph-node:'+n.get('id',str(i)),'kind':'GraphNode','original':n})
  for i,e in enumerate(g['edges']):records.append({'record_id':'graph-edge:'+str(i),'kind':'GraphEdge','original':e})
  records.append({'record_id':'metadata','kind':'Sidecar','original':{k:v for k,v in g.items() if k not in ['nodes','edges']}})
  case={'case_id':cid,'fixed_issue':x['fixed_issue'],'records':records,'source_lookup':[{k:s[k] for k in ['id','text']} for s in x['pre_outcome_source']['segments']]};put('stage-candidates/'+cid+'.json',case);cases.append(case)
 for j in range(2):
  task('S-'+str(j+1),'''Independently review semantic stage of EVERY record in these four existing historical development inventories. No external search, no new fact extraction or legal answer. Return complete JSON code block (downloadable JSON also welcome): {cases:[{case_id,records:[{record_id,semantic_stage,input_allowed,prospective_availability,source_refs,reason}],gaps:[string]}]}. One output row per exact input record_id, including graph edges, metadata, source passages, objects, issue fields and quarantined records. Allowed semantic stages PRE_TARGET_RECORD, PRIOR_COURT_FINDING, TARGET_STAGE_PARTY_ARGUMENT; forbidden TARGET_COURT_REASONING, TARGET_DISPOSITION, AMBIGUOUS. input_allowed must correspond. Classify semantic provenance, not merely event time or node type. Target court's own evidence appraisal/finding/decision is forbidden even when its description concerns past facts. Reported neutral historical facts/party allegations/prior findings may remain retrospective input, retaining original court/status; never upgrade lower findings. Mixed source passages carrying target reasoning should be excluded whole (no editing). Graph edges also need semantic provenance and allowed endpoints, not a not_a_target_label flag. Metadata leakage/audits and inherited partition assertions are engineering records, not input facts: exclude AMBIGUOUS if unsuitable. Source_refs must cite supplied original source IDs, not fabricated ones. Almost all records are reconstructed from the final judgment: use RETROSPECTIVELY_RECONSTRUCTED_PRE_TARGET for allowed ones unless direct pre-target original is actually provided; UNKNOWN otherwise. Keep uncertain interpretation AMBIGUOUS and explain. Do not inspect/derive target labels or rewrite records. Each reason brief but specific.''',cases[j*4:j*4+4])
 print('Prepared stage tasks',[(p.name,p.stat().st_size) for p in (R/'tasks').glob('*')])
