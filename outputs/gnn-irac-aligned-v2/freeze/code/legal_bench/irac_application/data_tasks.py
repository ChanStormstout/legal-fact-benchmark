"""Self-contained, separately scoped annotation tasks and deterministic imports."""
import copy,json,hashlib,re
from pathlib import Path
from .input_partition import partition,isolate_records,AVAIL
from .rule_templates import attach,validate_template
from .graph_builder import build_graph
from .target_adapter import adapt_targets
from legal_bench.rules_verdict_v1.irac_native_schema_v1 import validate_input,quote_errors

def save(path,x):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(x,ensure_ascii=False,indent=2))
def sources(root,family):return {s['source_id']:{k:v for k,v in s.items() if k!='source_id'} for s in json.loads((root/'law-sources'/f'{family}.json').read_text())}
INPUT_PROMPT='''Construct INPUT records only from the approved spans and given rule template below. The target court's reasoning is withheld. No external search or memories. Do not predict condition states, supports/defeats, verdict or target adoption. Return the complete JSON inline in ONE code block; a downloadable input-XX.json is optional, not a replacement for visible JSON. {cases:[{case_id,issue,entities:[],facts:[],evidence:[],relations:[],coverage_limits:[]}]}.
Every record, including issue/entities/relations, uses {id,text,statement_status,semantic_stage,court_level,party_side,polarity,source_refs:[{source_id,quote}]}. Use ONE status from CLAIMED/DENIED/ADMITTED/PRIOR_FOUND/DOCUMENT_RECORDED/UNKNOWN; stage PRE_TARGET_RECORD/PRIOR_COURT_FINDING/TARGET_STAGE_PARTY_ARGUMENT; court_level NONE/RENT_CONTROLLER/ARC/ARCT/TRIBUNAL/HIGH_COURT/SUPREME_COURT/UNKNOWN, prior findings never TARGET. party_side CLAIMANT/RESPONDENT/NEUTRAL/UNKNOWN; polarity POSITIVE/NEGATIVE/UNKNOWN. Copy source stage accurately. Source_refs quotes independently contiguous; multiple refs allowed; never compose fragments into one quote. Unknown fields remain UNKNOWN or [], not guesses. No whole-case completeness requirement. Keep 4-12 task-relevant atomic facts including opposing accounts, denials, material limitations and documented lower court findings. No forced quota. Entities identity only; unsupported attributes need not be filled. Event text stays in facts, not actor fields. Fact entity_ids list only IDs supported by the same supplied source; no string-similarity identity guesses. Evidence may specify supports_fact_ids; documentary existence is not the truth of every alleged statement. Each relation requires id and common fields plus source_record_id,target_record_id,relation (PARTY_ASSERTS_FACT/PRIOR_COURT_FOUND_FACT/FACT_RELATES_TO_ENTITY/EVIDENCE_SUPPORTS_FACT). No extra relation types. Issue is a neutral question, not a condition result, and cites an approved span establishing the controversy. Rules/conditions will be attached deterministically, don't duplicate or reword them.
Complete SYNTHETIC teaching example, not a target answer:
Approved source Z1: "Owner alleges Guest occupies the room. Tenant denies giving Guest exclusive possession." stage PRE_TARGET_RECORD. Output {"cases":[{"case_id":"SYNTHETIC-Z","issue":{"id":"I","text":"Whether alleged guest occupancy amounted to transfer of possession","statement_status":"CLAIMED","semantic_stage":"PRE_TARGET_RECORD","court_level":"NONE","party_side":"CLAIMANT","polarity":"UNKNOWN","source_refs":[{"source_id":"Z1","quote":"Owner alleges Guest occupies the room."}]},"entities":[{"id":"E1","text":"Owner","statement_status":"DOCUMENT_RECORDED","semantic_stage":"PRE_TARGET_RECORD","court_level":"NONE","party_side":"CLAIMANT","polarity":"UNKNOWN","source_refs":[{"source_id":"Z1","quote":"Owner"}]},{"id":"E2","text":"Guest","statement_status":"DOCUMENT_RECORDED","semantic_stage":"PRE_TARGET_RECORD","court_level":"NONE","party_side":"NEUTRAL","polarity":"UNKNOWN","source_refs":[{"source_id":"Z1","quote":"Guest"}]}],"facts":[{"id":"F1","text":"Owner alleges Guest occupies the room","statement_status":"CLAIMED","semantic_stage":"PRE_TARGET_RECORD","court_level":"NONE","party_side":"CLAIMANT","polarity":"POSITIVE","entity_ids":["E1","E2"],"source_refs":[{"source_id":"Z1","quote":"Owner alleges Guest occupies the room."}]},{"id":"F2","text":"Tenant denies giving Guest exclusive possession","statement_status":"DENIED","semantic_stage":"PRE_TARGET_RECORD","court_level":"NONE","party_side":"RESPONDENT","polarity":"NEGATIVE","entity_ids":["E2"],"source_refs":[{"source_id":"Z1","quote":"Tenant denies giving Guest exclusive possession."}]}],"evidence":[],"relations":[{"id":"REL1","text":"Owner asserts alleged occupancy","statement_status":"CLAIMED","semantic_stage":"PRE_TARGET_RECORD","court_level":"NONE","party_side":"CLAIMANT","polarity":"POSITIVE","source_record_id":"E1","target_record_id":"F1","relation":"PARTY_ASSERTS_FACT","source_refs":[{"source_id":"Z1","quote":"Owner alleges Guest occupies the room."}]}],"coverage_limits":["Occupancy is alleged, not target-court confirmed; exclusive possession is disputed."]}]}.
Use only current case IDs and current approved source IDs, not Z1. Preserve original unknowns; no silent semantic repair.'''
TARGET_PROMPT='''Construct SUPERVISION separately: predict what the specified TARGET court substantively decided about each GIVEN condition. No external search, no simulated model predictions. Return the complete JSON inline in ONE code block; downloadable target-XX.json is optional. {cases:[{case_id,element_targets:[{condition_id,status,basis_kind,substantive_adjudication,input_sufficient,explicit_evidentiary_unresolved,fact_truth,target_refs:[{source_id,quote}],reason}],procedural_outcome_separate,coverage_limits:[]}]}.
status SATISFIED, DEFEATED, UNRESOLVED or null. DEFEATED means legal condition not established, not automatic false fact. basis_kind FACT_ACCEPTED/FACT_FALSE/BURDEN_NOT_CARRIED/INSUFFICIENT_RECORD/LEGAL_INTERPRETATION/AMBIGUOUS_REASONING/NOT_DECIDED. No alternatives joined in one string. If not substantively decided, status null, basis NOT_DECIDED, substantive_adjudication false. Explicitly adopted lower court application can support a target; mere appeal dismissal/restoration cannot silently assign all elements. UNRESOLVED only where TARGET actually analyzes and explicitly leaves the condition evidentially undetermined; set explicit_evidentiary_unresolved true. Reviewer uncertainty, missing annotation, incomplete material, legal issue not reached are not observed UNRESOLVED targets. Unknown truth stays UNKNOWN, burden failure not FALSE. An affirmative finding of consent can defeat lack-of-consent only where that polarity is the GIVEN condition. Do not invert condition polarity to fit outcome. No overall win/lose labels.
Read complete target source including arguments, lower court treatment, actual target reasoning. References exact separate contiguous quotes, never join passages. Check the separately frozen INPUT record to determine input_sufficient: if the historic finding relies on decisive unavailable evidence, false with reason, even if target outcome is clear. This flag controls loss only and NEVER adds target findings to the input. Save every condition including unobserved ones. Stage-specific application, not predicted final outcome; model reference not human gold.'''
REVIEW_PROMPT='''One concentrated source review, no external search or new full extraction. Return the complete JSON inline in ONE code block; downloadable review-XX.json is optional. {cases:[{case_id,input_review:[{record_id,decision:"SUPPORTED",reason}],target_review:[{condition_id,decision:"SUPPORTED",substantive_adjudication:true,input_sufficient:true,explicit_evidentiary_unresolved:false,reason}],partition_review:[{source_id,decision:"SUPPORTED",reason}],important_omissions:[],association:[],scope_review:"SUPPORTED"}]}. Decisions SUPPORTED/QUALIFIED/UNSUPPORTED/DISPUTED. Check original full source, separately partitioned input, given template and proposed targets. Verify INPUT spans exclude target endorsement/reasoning/outcome; neutral historical descriptions or clearly attributed earlier findings allowed, including unambiguously separable subspans. Don't promote reported claims. Enumerate input_review for EVERY issue/entity/fact/evidence/relation record, including those supported; enumerate partition_review for EVERY admitted case-span source_id; given-law sources are independently reviewed and need not be repeated. target_review enumerates all six conditions, including NOT_DECIDED. scope_review is one of SUPPORTED/QUALIFIED/UNSUPPORTED/DISPUTED. No record is presumed certified merely by address validation. Input record is a proposal, not truth-certified. Conditions need explicit substantive decisions or adoption, not appeal outcome. NOT_DECIDED stays unobserved, NOT UNRESOLVED. Check decisive input availability, polarity and burden, each quote independently. Disagreement unresolved => DISPUTED/mask, not repeated attempts until READY. Rule template only promises supplied scope, not entire case coverage. Identify known same dispute links, preserve uncertainty otherwise. Don't replace original model contents; proposed semantic corrections only described, not silently applied. Partial safe records and reliable targets remain usable even if other rows fail. If record references an unsafe entity, local dependency closure removes it. Source review is model assisted, not human gold.'''

def prepare_inputs(root):
 root=Path(root);inventory=json.loads((root/'candidate-inventory.json').read_text());byid={r['case_id']:r for r in inventory};selected=[];audit=[]
 for p in sorted((root/'web').glob('screen-*.json')):
  if not re.fullmatch(r'screen-\d\d.json',p.name):continue
  for row in json.loads(p.read_text())['cases']:
   ident=row['case_id'];family=row.get('family');reason=[]
   if row['decision']=='REJECT':reason.append('SCREEN_REJECT')
   if family not in ['DRC_SUBLETTING','DRC_BONA_FIDE']:reason.append('CURRENT_INDEPENDENT_TEMPLATE_NOT_AVAILABLE')
   if not (root/'templates'/f'{family}.json').exists():reason.append('TEMPLATE_NOT_YET_READY')
   # Main templates are DRC1958, and bona-fide residential version pre2008 only.
   scope=json.dumps(row.get('law_scope',''))
   law_audit=json.loads((root/'scope-selection.json').read_text()).get(ident,{})
   if law_audit.get('decision')!='COMPATIBLE':reason.append('GIVEN_TEMPLATE_SCOPE_NOT_CONFIRMED:'+law_audit.get('reason','NO_SCOPE_REVIEW'))
   if reason:audit.append(dict(case_id=ident,reasons=reason,screen=row));continue
   doc=json.loads(Path(byid[ident]['source_path']).read_text());approved,pa=partition(doc,row.get('allowed_spans',[]))
   if not approved:audit.append(dict(case_id=ident,reasons=['NO_LOCATED_SAFE_INPUT_SPAN'],screen=row));continue
   selected.append(dict(case_id=ident,family=family,target_stage=row['target_stage'],target_court=row['target_court'],source_path=byid[ident]['source_path'],group_id=byid[ident]['group_id'],association=byid[ident]['association'],screen=row,sources=approved,span_audit=pa))
 selected=selected[:24]
 save(root/'construction-manifest.json',selected);save(root/'screen-import-audit.json',audit)
 for i in range(0,len(selected),2):
  name='input-%02d'%(i//2+1);rows=[]
  for r in selected[i:i+2]:
   rows.append(dict(case_id=r['case_id'],target_stage=r['target_stage'],family=r['family'],allowed_sources=r['sources'],given_template=json.loads((root/'templates'/f"{r['family']}.json").read_text())))
  (root/'tasks'/f'{name}.txt').write_text(INPUT_PROMPT.replace('input-XX',name)+'\n'+json.dumps(rows,ensure_ascii=False)+'\nEND_OF_TASK '+name)
 return selected

def import_inputs(root):
 root=Path(root);manifest=json.loads((root/'construction-manifest.json').read_text());byid={r['case_id']:r for r in manifest};audits=[]
 for p in sorted((root/'web').glob('input-*.json')):
  if not re.fullmatch(r'input-\d\d.json',p.name):continue
  for row in json.loads(p.read_text())['cases']:
   ident=row['case_id'];m=byid[ident];template=json.loads((root/'templates'/f"{m['family']}.json").read_text());ss=copy.deepcopy(m['sources']);ss.update(sources(root,m['family']));local,excluded=isolate_records(row,ss);issue=copy.deepcopy(row['issue']);issue.setdefault('prospective_availability',AVAIL)
   rule,conditions=attach(template,issue['id'])
   inp=dict(case_id=ident,issue=issue,**local,rules=[rule],conditions=conditions,blind_bindings=[],stage_metadata={'policy_version':'APPLICATION_V1_EXPLICIT_SPANS'},provenance=ss,prospective_availability=AVAIL)
   errors=validate_input(inp);audit=dict(case_id=ident,excluded=excluded,errors=errors,coverage_limits=row.get('coverage_limits',[]));audits.append(audit)
   if not errors:
    save(root/'inputs'/f'{ident}.json',inp);save(root/'graphs'/f'{ident}.json',build_graph(inp));save(root/'packages'/f'{ident}.json',dict(package_id=ident,group_id=m['group_id'],family=m['family'],target_stage=m['target_stage'],target_court=m['target_court'],association=m['association'],condition_templates={c['id']:template['template_id']+':'+c['id'] for c in conditions},given_rule_oracle_selection=True,exposed_development=True))
 save(root/'input-import-audit.json',audits)
 return audits

def prepare_targets(root):
 root=Path(root);manifest=json.loads((root/'construction-manifest.json').read_text());selected=[r for r in manifest if (root/'inputs'/f"{r['case_id']}.json").exists()]
 for i in range(0,len(manifest),2):
  batch=manifest[i:i+2]
  if not all((root/'inputs'/f"{m['case_id']}.json").exists() for m in batch):continue
  name='target-%02d'%(i//2+1);rows=[]
  for m in batch:
   doc=json.loads(Path(m['source_path']).read_text());rows.append(dict(case_id=m['case_id'],target_stage=m['target_stage'],target_court=m['target_court'],full_source=dict(document_id=doc['document_id'],url=doc.get('url'),segments=[dict(source_id=s['id'],text=s['text']) for s in doc['segments']]),given_template=json.loads((root/'templates'/f"{m['family']}.json").read_text()),frozen_input=json.loads((root/'inputs'/f"{m['case_id']}.json").read_text())))
  (root/'tasks'/f'{name}.txt').write_text(TARGET_PROMPT.replace('target-XX',name)+'\n'+json.dumps(rows,ensure_ascii=False)+'\nEND_OF_TASK '+name)
 return selected

def prepare_reviews(root):
 root=Path(root);manifest=json.loads((root/'construction-manifest.json').read_text());target_rows={}
 for p in sorted((root/'web').glob('target-??.json')):
  for row in json.loads(p.read_text())['cases']:target_rows[row['case_id']]=row
 selected=[r for r in manifest if (root/'inputs'/f"{r['case_id']}.json").exists() and r['case_id'] in target_rows]
 for i in range(0,len(selected),4):
  name='review-%02d'%(i//4+1);rows=[]
  for m in selected[i:i+4]:
   doc=json.loads(Path(m['source_path']).read_text());rows.append(dict(case_id=m['case_id'],target_stage=m['target_stage'],target_court=m['target_court'],full_source=dict(document_id=doc['document_id'],url=doc.get('url'),segments=[dict(source_id=s['id'],text=s['text']) for s in doc['segments']]),given_template=json.loads((root/'templates'/f"{m['family']}.json").read_text()),input=json.loads((root/'inputs'/f"{m['case_id']}.json").read_text()),partition_audit=m['span_audit'],proposed_targets=target_rows[m['case_id']]))
  (root/'tasks'/f'{name}.txt').write_text(REVIEW_PROMPT.replace('review-XX',name)+'\n'+json.dumps(rows,ensure_ascii=False)+'\nEND_OF_TASK '+name)
 return selected

def admit_reviewed(root):
 """Source safety independently of labels, then supervision-only local masks."""
 root=Path(root);manifest=json.loads((root/'construction-manifest.json').read_text());meta={x['case_id']:x for x in manifest};refs={};reviews={};audits=[]
 for p in sorted((root/'web').glob('target-??.json')):
  for x in json.loads(p.read_text())['cases']:refs[x['case_id']]=x
 for p in sorted((root/'web').glob('review-??.json')):
  for x in json.loads(p.read_text())['cases']:reviews[x['case_id']]=x
 for ident,m in meta.items():
  input_path=root/'inputs'/f'{ident}.json'
  if not input_path.exists():continue
  inp=json.loads(input_path.read_text());initial=copy.deepcopy(inp)
  # Preserve unreviewed input too: source-review gate is local, not a label gate.
  rev=reviews.get(ident,{});ir={r['record_id']:r for r in rev.get('input_review',[])};pr={r['source_id']:r for r in rev.get('partition_review',[])}
  quarantined=[];bad_sources=set()
  for sid in m['sources']:
   if pr.get(sid,{}).get('decision') not in {'SUPPORTED','QUALIFIED'}:bad_sources.add(sid)
  for kind in ('entities','facts','evidence','relations'):
   for row in initial[kind]:
    bad=ir.get(row['id'],{}).get('decision') not in {'SUPPORTED','QUALIFIED'} or any(ref['source_id'] in bad_sources for ref in row['source_refs'])
    if bad:quarantined.append(dict(kind=kind,original=row,reason='INPUT_SOURCE_REVIEW_UNSUPPORTED_OR_MISSING'))
   inp[kind]=[x for x in initial[kind] if x['id'] not in {q['original']['id'] for q in quarantined}]
  ss={sid:s for sid,s in inp['provenance'].items() if sid not in bad_sources}
  local,closure=isolate_records(inp,ss);inp.update(local);quarantined+=closure
  issue_bad=ir.get(inp['issue']['id'],{}).get('decision') not in {'SUPPORTED','QUALIFIED'} or any(x['source_id'] in bad_sources for x in inp['issue']['source_refs'])
  inp['provenance']=ss;errors=validate_input(inp)
  # No target-class/target-review decisions have been used to modify input.
  save(root/'input-before-source-review'/f'{ident}.json',initial)
  save(root/'graph-before-source-review'/f'{ident}.json',build_graph(initial))
  input_admitted=not issue_bad and not errors
  if input_admitted:
   save(root/'inputs'/f'{ident}.json',inp);save(root/'graphs'/f'{ident}.json',build_graph(inp))
  else:
   save(root/'input-quarantine'/f'{ident}.json',dict(input=initial,reason='ISSUE_OR_INPUT_CONTRACT_SOURCE_UNSAFE',errors=errors,issue_bad=issue_bad))
   # Keep original and graph; a sidecar admission list prevents training on unsafe graphs.
  proposal=copy.deepcopy(refs.get(ident,{'element_targets':[]}));tr={r['condition_id']:r for r in rev.get('target_review',[])}
  template_review=json.loads((root/'template-review-audit.json').read_text());rule_review=next(x['review'] for x in template_review if x['family']==m['family']);cr={r['condition_id']:r for r in rule_review['conditions']}
  for row in proposal['element_targets']:
   review=tr.get(row['condition_id'],{});row['source_review']=review.get('decision','MISSING')
   # The reviewer may veto proposed reliability; cannot promote an unsupported proposal.
   for field in ('substantive_adjudication','input_sufficient','explicit_evidentiary_unresolved'):
    row[field]=row.get(field) is True and review.get(field) is True
   if cr.get(row['condition_id'],{}).get('decision') not in {'SUPPORTED','QUALIFIED'}:row['source_review']='RULE_CONDITION_NOT_ADMITTED'
   if not input_admitted or rev.get('scope_review') not in {'SUPPORTED','QUALIFIED'}:row['input_sufficient']=False
  doc=json.loads(Path(m['source_path']).read_text());ss_target={s['id']:{'text':s['text']} for s in doc['segments']}
  adapted=adapt_targets([c['id'] for c in inp['conditions']],proposal,ss_target)
  save(root/'targets'/f'{ident}.json',dict(original_proposal=refs.get(ident),reviewed_proposal=proposal,adapted_targets=adapted,review=rev,reference_kind='MODEL_GENERATED_SOURCE_REVIEWED_NOT_HUMAN_GOLD'))
  audits.append(dict(case_id=ident,input_admitted=input_admitted,input_removed=quarantined,unsafe_sources=sorted(bad_sources),issue_bad=issue_bad,errors=errors,scope_review=rev.get('scope_review'),reviewed=bool(rev),supervised_conditions=sum(r['supervision_mask'] for r in adapted),mask_reasons={r['condition_id']:r['mask_reasons'] for r in adapted if not r['supervision_mask']}))
 save(root/'source-review-admission.json',audits);return audits
