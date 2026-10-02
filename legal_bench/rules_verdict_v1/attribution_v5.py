"""Source-bound attribution records. Structural admission is not semantic approval."""
import json
from .contracts import obj,array,enum,string
ROLES=['NARRATOR','PARTY','COUNSEL','COURT','UNKNOWN']
def schema(source,targets):
    ev=obj({'segment_id':enum(s['id'] for s in source['segments']),'quote':string(900)})
    item=obj({'status':enum(['NARRATED','PARTY_CLAIMED','COURT_FOUND','UNKNOWN']),
      'origin':obj({'role':enum(ROLES),'side':enum(['APPELLANT','RESPONDENT','NOT_APPLICABLE','UNKNOWN']),
        'mention':string(120),'identity_evidence':array(ev,2)}),
      'attribution_evidence':array(ev,2),
      'finding_level':enum(['LOWER_COURT','CURRENT_COURT','BOTH','NOT_SHOWN','UNKNOWN']),
      'finding_evidence':array(ev,2)})
    return obj({t['id']:item for t in targets})
def prompt(source,targets):
    return '''For each target classify its source attribution, not truth or the final verdict. Return the JSON schema.
Use PARTY_CLAIMED for allegations/submissions, COURT_FOUND for an explicit finding of this proposition, NARRATED for unembedded background, UNKNOWN if unresolved. Keep origin (who makes the proposition) separate from the judgment's author or the judge reporting it. An explicit lower court finding counts as LOWER_COURT even when the current court's endorsement is not shown. A later eviction outcome alone is not a finding of this exact proposition.
origin.role is NARRATOR, PARTY, COUNSEL, COURT or UNKNOWN. side refers to the side represented in this proceeding, not whether landlord/tenant. When uncertain use UNKNOWN. NARRATOR and COURT use NOT_APPLICABLE side. No free-form names or combined identities: origin.mention must be ONE exact contiguous mention copied from identity_evidence, and identify just the source of this proposition. Prefer the local role phrase (e.g. 'Counsel for the appellants') over resolving a person's name. For NARRATOR use empty mention and empty identity_evidence; for UNKNOWN likewise. For a pronoun/learned counsel, include the earlier source passage resolving its role when available. Do not merge opposing lawyers.
attribution_evidence must contain the wording that places this proposition in narration, a claim or finding, including its introduction. A quote of only the embedded proposition may omit the attribution. Each evidence quote must be an exact substring of ONE supplied segment. finding_evidence must contain explicit court finding language for this target when finding_level is LOWER_COURT/CURRENT_COURT/BOTH; otherwise empty. NOT_SHOWN means no explicit finding in this supplied scope, not that the proposition is false. COURT_FOUND with NOT_SHOWN is inconsistent; use UNKNOWN if unresolved.
Synthetic complete example: given segment s1 'Counsel for the claimant argued that the roof leaked.' and target X 'the roof leaked', output {"X":{"status":"PARTY_CLAIMED","origin":{"role":"COUNSEL","side":"UNKNOWN","mention":"Counsel for the claimant","identity_evidence":[{"segment_id":"s1","quote":"Counsel for the claimant argued that the roof leaked."}]},"attribution_evidence":[{"segment_id":"s1","quote":"Counsel for the claimant argued that the roof leaked."}],"finding_level":"NOT_SHOWN","finding_evidence":[]}}. Use actual IDs below, not this example.
TARGETS\n'''+json.dumps(targets,ensure_ascii=False)+'\nCOMPLETE PROVIDED SCOPE (same allowed segments as previous run, not full judgment)\n'+json.dumps(source,ensure_ascii=False)
def check(row,source):
    """Reject unlocatable or internally inconsistent fields; never infer semantics."""
    seg={s['id']:s['text'] for s in source['segments']};errors=[]
    for field,ev in [('attribution_evidence',row['attribution_evidence']),('identity_evidence',row['origin']['identity_evidence']),('finding_evidence',row['finding_evidence'])]:
        if any(not e['quote'] or e['quote'] not in seg.get(e['segment_id'],'') for e in ev): errors.append(field+':UNLOCATABLE')
    if not row['attribution_evidence']: errors.append('MISSING_ATTRIBUTION_EVIDENCE')
    origin=row['origin'];role=origin['role'];status=row['status'];level=row['finding_level']
    if role in ['NARRATOR','UNKNOWN']:
        if origin['mention'] or origin['identity_evidence']: errors.append('UNBOUND_NARRATOR_OR_UNKNOWN')
    elif not origin['mention'] or not any(origin['mention'] in e['quote'] for e in origin['identity_evidence']): errors.append('MENTION_NOT_BOUND')
    allowed={'NARRATED':['NARRATOR'],'PARTY_CLAIMED':['PARTY','COUNSEL'],'COURT_FOUND':['COURT'],'UNKNOWN':ROLES}
    if role not in allowed[status]: errors.append('STATUS_ORIGIN_CONFLICT')
    if role in ['NARRATOR','COURT'] and origin['side']!='NOT_APPLICABLE': errors.append('SIDE_ROLE_CONFLICT')
    if status=='COURT_FOUND' and level not in ['LOWER_COURT','CURRENT_COURT','BOTH']: errors.append('FINDING_LEVEL_UNRESOLVED')
    if level in ['LOWER_COURT','CURRENT_COURT','BOTH']:
        if not row['finding_evidence']: errors.append('MISSING_FINDING_WITNESS')
    elif row['finding_evidence']: errors.append('UNRESOLVED_LEVEL_WITH_WITNESS')
    return {'structural_status':'QUARANTINED' if errors else 'STRUCTURALLY_ADMISSIBLE','errors':errors,'semantic_support':'NOT_ESTABLISHED_BY_CHECKER'}
