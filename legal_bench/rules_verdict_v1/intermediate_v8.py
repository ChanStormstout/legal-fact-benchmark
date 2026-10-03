"""V8 display-only compression and shared minimal answer contract."""
import json
from .checks_v8 import notes_schema, fact_schema, check_facts, CATEGORIES
from .contracts import obj,array,enum
from .intermediate_v7 import COMMON,FACTS
S=lambda:{'type':'string'}
NOTES='''Stage 1: return notes and coverage_limits. At most six DISTINCT substantive sourced points, each one or two sentences (30-50 English words is a soft target). Each note has id, kind SUPPORT/OPPOSITION/RULE_SCOPE/LINK/UNCERTAINTY, point and refs. Cover decisive support, opposition, statement status, applicable scope, needed connections and critical gaps without repeating the same dispute across notes. Do not write the complete judgment yet. If the record cap omits important content, state it in coverage_limits. Use supplied source IDs, not long quotations. Complete within 3072 tokens.'''
FACTS8=FACTS.replace('2048','3072')+'''
Compression duties: role text is a SHORT literal source mention, never a slash-separated alias inventory or legal analysis. Different names for the same matter need not become duplicate facts. Do not fill arrays just to reach their caps. Propose links only where a current condition connection needs them and a source basis exists; no basis permits no link. Keep distinct counterevidence, conflicting states and unknowns. If a record cap omits important material, disclose it in coverage_limits. No semantic deletion to shorten output.
'''
FINAL='''Stage 2: answer the fixed eviction-ground issue using the complete allowed source and shared law package. Intermediate notes, facts and checks are fallible. Correct intermediate errors directly from the source; program checks are not commands or verified legal conclusions. Interpret only the supplied law within its scope.
Return {outcome, grounds, reason}. outcome is SUPPORT_GROUND, OPPOSE_GROUND, UNDETERMINED or UNSUPPORTED. grounds has at most six rows, each {point, record, case_refs, law_refs, assessment, application_or_gap}. Each row handles ONE decisive proposition or legal interpretation. record preserves relevant objects, both supporting and opposing facts, and their actual statement statuses. case_refs and law_refs use supplied IDs; do not rewrite long quotes. assessment SUPPORTED/REFUTED/UNRESOLVED/UNSUPPORTED evaluates the proposition stated in point, NOT whether eviction succeeds. For example, support for the existence of written landlord consent may defeat the eviction ground. application_or_gap explains the rule's scope and application or concrete missing information. Distinguish uncertain case facts, inadequate supplied law and unimplemented program checks; these are not interchangeable. Do not equate no candidate with absence in reality or failure of one binding with failure of every binding.
reason is one or two sentences synthesizing only these grounds and explicitly stating their LEGAL CONSEQUENCE for the fixed issue. No new unsupported rule. Preserve already known facts even if a decisive gap prevents a conclusion. Do not guess the historical outcome. At most 3072 output tokens; concise but complete sentences, no repetitions. Closed JSON, valid IDs and UNDETERMINED do not establish correctness.
'''
def final_schema(case_ids,law_ids):
 return obj({'outcome':enum(['SUPPORT_GROUND','OPPOSE_GROUND','UNDETERMINED','UNSUPPORTED']), 'grounds':array(obj({'point':S(),'record':S(),'case_refs':array(enum(case_ids),4),'law_refs':array(enum(law_ids),4),'assessment':enum(['SUPPORTED','REFUTED','UNRESOLVED','UNSUPPORTED']),'application_or_gap':S()}),6),'reason':S()})
def source_text(s):return '\n'.join('['+x['id']+'] '+x['text'] for x in s['segments'])
def first_prompt(s,p,arm):return COMMON+'\nSHARED LAW PACKAGE\n'+json.dumps(p,ensure_ascii=False)+'\nCOMPLETE ALLOWED CASE SOURCE\n'+source_text(s)+'\n'+(NOTES if arm=='A' else FACTS8)
def final_prompt(s,p,material):return COMMON+'\nSHARED LAW PACKAGE\n'+json.dumps(p,ensure_ascii=False)+'\nINTERMEDIATE UNVERIFIED\n'+json.dumps(material,ensure_ascii=False,separators=(',',':'))+'\nCOMPLETE ALLOWED CASE SOURCE\n'+source_text(s)+'\n'+FINAL

def compact_checks(full):
 """Lossless distinct checks; proposals live once in separate material. No relevance selection."""
 links=full['link_checks']; lookup={json.dumps(x,sort_keys=True):'L'+str(i+1) for i,x in enumerate(links)}
 def result(r):
  return {k:([lookup[json.dumps(x,sort_keys=True)] for x in v] if k=='links' else v) for k,v in r.items()}
 joins=[];seen={};trace=[]
 for i,x in enumerate(full['all_join_trace']):
  key=json.dumps(x,sort_keys=True)
  if key not in seen:
   seen[key]='J'+str(len(joins)+1);joins.append({'id':seen[key],'left':x['left'],'right':x['right'],'result':result(x['result'])})
  trace.append(seen[key])
 # Call order: two joins per tenancy-transfer pair, then seven per combination.
 offset=2*len(full['tenancy_transfer_checks'])
 pairs=[{'facts':x['facts'],'joins':trace[2*i:2*i+2]} for i,x in enumerate(full['tenancy_transfer_checks'])]
 combos=[{**{k:v for k,v in x.items() if k!='joins'},'joins':trace[offset+7*i:offset+7*i+7]} for i,x in enumerate(full['all_combination_trace'])]
 view={'meaning':'Checks only assess what can be confirmed FROM MODEL PROPOSALS. They do not certify source meaning, whole-case absence or legal outcome. Consent PROPOSED_SUPPORT means proposed absence of written consent in the base formula, not support for consent existence.',
 'record_checks':[{**{k:v for k,v in x.items() if k not in ['roles','source_refs']},'roles':{k:v['state'] for k,v in x['roles'].items()},'full_path':'record_checks/'+str(i)} for i,x in enumerate(full['record_checks'])],
 'link_checks':[{'id':'L'+str(i+1),'proposal_path':'links/'+str(i),'structural_state':x['structural_state'],'semantic_verification':x['semantic_verification']} for i,x in enumerate(links)],
 'joins':joins,'tenancy_transfer_checks':pairs,'combinations':combos,'combination_counts':full['combination_counts'],'rule_configuration':full['rule_configuration'],'coverage_limits':full['coverage_limits'],'final_legal_conclusion':None}
 return view,{'join_occurrences':trace,'omissions':'roles.proposal/source_refs and model_coverage_limits are in unchanged proposal; capped complete display superseded by ALL combinations; link content is in proposal.links; full checks preserved','full_join_count':len(trace)}
