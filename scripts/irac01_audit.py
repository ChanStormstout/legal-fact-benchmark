"""Address/contract audit and two fixed source-review packages; never edits proposals."""
import json,hashlib,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.irac_contract_v1 import validate
from legal_bench.rules_verdict_v1.irac_adapter_v1 import check_binding
from legal_bench.rules_verdict_v1.source_location_v3 import locate_all
R=pathlib.Path('outputs/gnn-irac-feasibility-01')
def read(p):return json.loads(p.read_text())
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
ids=read(R/'protocol.json')['case_ids'];schema=read(R/'irac-task-schema.json'); audits=[]; packages=[]
for cid in ids:
 i=read(R/'inputs'/f'{cid}.json');t=read(R/'target-construction'/f'{cid}.json');p=read(R/'web'/f'P-{cid}.raw.json');lin=read(R/'lineage'/f'{cid}.json')
 rules={u['id']:u for u in i['oracle_rule_material']};facts={f['id']:f for f in i['existing_inventory']['facts']};tm={s['id']:s['text'] for s in t['full_historical_source']}
 a={'case_id':cid,'schema_errors':validate(p,schema),'input_hash_unchanged':sha(R/'inputs'/f'{cid}.json')==lin['input_sha256'],'conditions':[],'bindings':[],'target_quotes':[]}
 for c in p['conditions']:
  errors=[];u=rules.get(c['rule_id']);loc=locate_all(u['text'],c['exact_rule_quote']) if u else {'status':'NO_RULE'}
  if loc['status'] not in ('EXACT','WHITESPACE_ONLY'):errors.append('RULE_QUOTE_NOT_LOCATED')
  if not set(c['law_refs'])<=set(rules):errors.append('INVALID_LAW_REF')
  if any(d['condition_id'] not in {x['id'] for x in p['conditions']} for d in c['dependencies']):errors.append('INVALID_DEPENDENCY')
  a['conditions'].append({'id':c['id'],'errors':errors,'quote_location':loc})
 for b in p['bindings']:
  errors=check_binding(b,i['existing_inventory'],p['conditions']);f=facts.get(b['fact_id'])
  if f:
   for old,new in [('status','statement_status'),('court','court'),('stage','stage')]:
    if b[new]!=f[old]:errors.append('CHANGED_'+old.upper())
  if not b['input_candidate'] or b['target_only']:errors.append('BINDING_NOT_INPUT_CANDIDATE')
  a['bindings'].append({'id':b['id'],'errors':errors})
 for target in p['element_targets']+[p['issue_target']]:
  for ref in target['target_refs']:
   loc=locate_all(tm.get(ref['id'],''),ref['quote']);a['target_quotes'].append({'condition_id':target.get('condition_id','ISSUE'),'ref':ref['id'],'location':loc})
 write(R/'audit'/f'{cid}.json',a);audits.append(a)
 write(R/'targets'/f'{cid}.json',{'case_id':cid,'usage':'TARGET_ONLY_MODEL_PROPOSAL_NOT_HUMAN_GOLD','element_targets':p['element_targets'],'issue_target':p['issue_target'],'gaps':p['gaps'],'proposal_sha256':sha(R/'web'/f'P-{cid}.raw.json')})
 write(R/'bindings'/f'{cid}.json',{'case_id':cid,'usage':'POST_AWARE_PROPOSED_BINDINGS_RESEARCH_ONLY_NOT_ADMITTED_FEATURES','input_candidate_proposals':p['bindings'],'target_witnesses':p['element_targets'],'audit':a['bindings']})
 # deterministic display removes repeated raw engineering metadata; all source text and semantic values retained
 cleanrules=[{k:v for k,v in u.items() if k!='source'}|{'source':{k:v for k,v in u['source'].items() if k!='raw_provenance'}} for u in i['oracle_rule_material']]
 packages.append({'case_id':cid,'issue':i['fixed_issue'],'stage':i['stage'],'input_source':[{'id':s['id'],'text':s['text']} for s in i['pre_outcome_source']['segments']],'existing_inventory':i['existing_inventory'],'rules':cleanrules,'target_source':[{'id':s['id'],'text':s['text']} for s in t['full_historical_source']],'proposal':p,'automatic_audit':{'schema_errors':a['schema_errors'],'input_hash_unchanged':a['input_hash_unchanged'],'conditions':[{'id':x['id'],'errors':x['errors'],'quote_status':x['quote_location']['status']} for x in a['conditions']],'bindings':a['bindings'],'target_quotes':[{'condition_id':x['condition_id'],'ref':x['ref'],'quote_status':x['location']['status']} for x in a['target_quotes']]}})
write(R/'automatic-audit.json',audits)
intro='''INDEPENDENT SOURCE REVIEW, not new extraction or legal prediction. Read all cases through END. No external search, no other chats. This is model-assisted reference review, not human gold. Do not revise the proposals, invent missing input facts, or force a success quota. Check all eight chain dimensions for each case: issue; sourced rule; faithful conditions and logical dependencies; input facts actually in allowed source; statement/court/stage status; target finding actually from TARGET court reasoning; leakage into input or binding; issue/element logical consistency. Quotes must address the correct source and the target court, not a quoted prior case or lower finding. Do not infer every element from final dismissal/allowance. Defeated burden is not fact false. Unknown is acceptable only with a concrete unresolved reason. Existing input inventory is weak local data, not an actual upstream canonical artifact. All candidate bindings were proposed with post-outcome access: evaluate evidence and do not certify them as an independently blinded pre-outcome generation method. Flag law timing/analogical scope, but distinguish limitations of retrospective data construction from a missing controlling legal test; historical snapshot uncertainty alone need not prove the statutory condition unavailable. Count a complete usable chain only if meaningful sourced conditions, input witnesses, and target application (including justified unresolved labels) can be audited without replacing or inventing records. An issue outcome alone is insufficient. An explicit OR branch with retained-control distinction matters; missing decisive test can make chain partial. Return one complete JSON code block and optional downloadable JSON. Root {"batch_id": "R-01", "reference_status": "MODEL_ASSISTED_NOT_HUMAN_GOLD", "cases": [ ... ]}. Each case: {"case_id": string, "chain_status":"USABLE" or "GAP", "review_status":"SUPPORTED" or "DISPUTED" or "UNRESOLVED", "dimensions": {"issue": status, "rule": status, "conditions": status, "input_fact": status, "statement_status": status, "application_target": status, "leakage": status, "conclusion_consistency": status}, "findings":[{"dimension": string, "object_ids": [string], "source_refs":[string], "quote":string, "reason": string, "severity":"BLOCKING" or "LIMITATION"}], "usable_condition_ids":[string], "reason":string}. Dimension statuses SUPPORTED/DISPUTED/UNRESOLVED. No ellipses. Preserve genuinely competing interpretations and report gaps. Review all four cases, no wholesale reannotation.\n'''
for idx in range(2):
 bid=f'R-0{idx+1}';p=R/'tasks-readable'/f'{bid}.txt';p.write_text(intro.replace('"R-01"',json.dumps(bid))+'\n'+json.dumps(packages[idx*4:(idx+1)*4],ensure_ascii=False,indent=2)+'\nEND_OF_REVIEW '+bid+'\n')
write(R/'review-task-freeze.json',{'batches':[{'id':f'R-0{k+1}','case_ids':ids[k*4:(k+1)*4],'path':str(R/'tasks-readable'/f'R-0{k+1}.txt'),'sha256':sha(R/'tasks-readable'/f'R-0{k+1}.txt')} for k in range(2)],'model_calls':2,'semantic_retry':0,'no_changes_to_input_or_proposal':True})
print([(a['case_id'],len(a['schema_errors']),sum(bool(x['errors']) for x in a['bindings']),sum(x['location']['status']=='UNLOCATED' for x in a['target_quotes'])) for a in audits])
print([(p.name,p.stat().st_size) for p in (R/'tasks-readable').glob('R-*')])
