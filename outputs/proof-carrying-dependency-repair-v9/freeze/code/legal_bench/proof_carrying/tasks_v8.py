"""Frozen English-only web tasks; no scores or downstream answers in references."""
import json
from .workflow_v7 import schema

TRANSPORT='Use only the complete attached task. Do not search externally, use other conversations, or add legal materials. Read the entire supplied source. Answer once in English with complete JSON. File tools may read this attachment and create a JSON file. Model review is not human gold or legal approval.'

PROPOSAL='''TASK: reconstruct source-grounded premises for rule applications. This is judgment reconstruction, not prediction. The supplied registry is a scoped research translation, not approved universal law. Distinguish the target court's reasoning, lower findings, opposing opinions, claims, testimony and final disposition. Do not use the final disposition as a premise proving itself. Preserve important counterarguments and qualifications. Record evidence as reported by this judgment, not independently authenticated exhibits. Use rule-slot predicate names only when meaning and roles really match; otherwise use a descriptive new predicate. Unknown identity, time or a missing witness is not negation. The same named role does not establish identity; do not split one event merely because different speakers describe it, or merge different transactions. Keep explicit states relative to the attributed proposition; a recorded allegation is not a proven alleged fact. Produce the facts schema only, no answer, reference labels, ranking or certificate. No minimum count: retain the decisive facts and opposing evidence needed for all registered requests, without filling arrays. Quote exactly a short passage from cited sources; legal-rule text cannot alone establish target-case facts.'''

REFERENCE='''TASK: independently assess candidate uses in this judgment reconstruction. You see source, rule translations, raw fact proposals and deterministically enumerated candidate applications. No ranking, method answers or checker results are supplied. Judge USABLE when the cited source supports using these attributed premises, objects, time and scope for the proposed rule inputs; valid opposition is usable as opposition, not a failed-request negative. UNUSABLE requires an explicit incompatibility or unsupported upgrade, with source explanation. UNRESOLVED includes insufficient source or genuine interpretation disputes; unselected/unmentioned is never a negative. Examine important contrary passages, not only cited fragments. A rule translated from this target judgment is not a universal rule, and a report of a precedent is not verification of that precedent. Separately review each raw premise as an attributed proposition, without editing it. ACCEPT_RESEARCH only for faithful attribution, state, bindings, limitations and evidence use; otherwise HOLD or UNRESOLVED. Review predicate mappings as SAME_MEANING, RELATED_DIFFERENT or NEW_PREDICATE without rewriting facts. For OPEN_TEXT applications, recorded_conclusion TRUE only when this court explicitly made that bounded evaluation for these objects/stage and these premises; otherwise UNKNOWN. This is an external research assumption, never independent legal computation. Return all candidate IDs once; omit no candidate merely because it is bad. No score or rank. No legal approval.'''

REF_SHAPE={
 'premise_reviews':[{'id':'P1','decision':'ACCEPT_RESEARCH','refs':['SRC:1'],'quote':'short exact source passage','reason':'attribution and bindings checked'}],
 'candidate_reviews':[{'id':'APP-identifier','label':'USABLE','refs':['SRC:1'],'quote':'short exact source passage','reason':'why this proposed use is or is not supported','recorded_conclusion':'UNKNOWN','conclusion_refs':[],'conclusion_quote':''}],
 'mapping_reviews':[{'premise':'P1','predicate':'named predicate','relation':'SAME_MEANING','refs':['SRC:1'],'reason':'same proposition scope, not merely similar words'}],
 'authority_treatment':[{'rule_ref':'R1@1','status':'QUALIFIED','refs':['SRC:1'],'reason':'bounded target account, original precedent not inspected'}],
 'decisive_counterarguments':['source-grounded opposing consideration'],
 'coverage_limits':['model reference, not human gold or legal approval']}

def prompt(spec,sources,rules,inventory,kind,facts=None,candidates=None,mappings=None):
    payload={'case':{k:spec[k] for k in ('case_id','name','stage','question')},
        'task':'Reconstruct the selected reasoning without treating outcome as its own premise',
        'registered_requests':[{'id':q['id'],'predicate':q['predicate']} for q in inventory],
        'rule_registry':rules}
    if kind=='reference':payload.update(raw_fact_proposal=facts,candidates=[{k:v for k,v in c.items() if k not in ('simple_features','structural_flags')} for c in candidates],predicate_mapping_candidates=[{'premise':m['premise'],'declared_predicate':m['declared_predicate'],'candidates':[x['predicate'] for x in m['candidates']]} for m in mappings])
    text=TRANSPORT+'\n\n'+(PROPOSAL if kind=='proposal' else REFERENCE)+'\n'+json.dumps(payload,ensure_ascii=False,indent=2)
    text+='\nCOMPLETE ALLOWED SOURCE (document role is supplied, not to be guessed):\n'
    for ref,s in sorted(sources.items(),key=lambda x:(x[1]['document'],x[1].get('original_line',0),x[0])):
        text+='['+ref+'] ['+s['document_role']+' / '+s.get('role','UNSPECIFIED')+'] '+s['text']+'\n'
    text+='\nOUTPUT '+('SCHEMA:\n'+json.dumps(schema('facts')) if kind=='proposal' else 'CONTRACT EXAMPLE (replace synthetic values, use USABLE/UNUSABLE/UNRESOLVED; ACCEPT_RESEARCH/HOLD/UNRESOLVED; authority statuses SUPPORTED/QUALIFIED/CONTRADICTED/UNSUPPORTED/UNRESOLVED):\n'+json.dumps(REF_SHAPE))
    return text+'\nEND_OF_TASK\n'
