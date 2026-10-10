"""Explicit, versioned macro-slot decompositions; no embedding equivalence approval."""
import itertools,copy
from .contracts import content_hash
from .grounding_v9 import source_match

# Each atom is part of the OLD slot description, not a new legal antecedent.
DECOMPOSITIONS={
 ('74028','R1@2','record_P5'):[
 ('high_court_prima_facie_termination_assessment',['LOWER_COURT_FINDING']),
 ('high_court_possession_at_filing_assessment',['LOWER_COURT_FINDING']),
 ('high_court_interim_restoration_order',['PROCEDURAL_RECORD'])],
 ('74028','R1@2','record_P6'):[
 ('conceded_structure_change',['TARGET_COURT_FINDING']),
 ('prima_facie_entitlement_to_revoke',['TARGET_COURT_FINDING'])],
}

def prepare(case,facts,rules,sources):
    made=[];contracts=[];byid={p['id']:p for p in facts['premises']}
    for (cid,rid,slot),atoms in DECOMPOSITIONS.items():
        if cid!=case:continue
        rule=rules[rid];sc=next(s for s in rule['slots'] if s['name']==slot)
        contract={'id':rid+':'+slot,'case':case,'rule_hash':content_hash(rule),'slot':slot,'predicate':sc['predicate'],'description':sc['description'],'atoms':[{'predicate':p,'statuses':ss} for p,ss in atoms],'shared_roles':sc['required_roles'],'court_level':'High Court' if slot=='record_P5' else 'Supreme Court','source_document':case,'semantic_review':'MAINTAINER_SOURCE_REVIEW_NOT_LEGAL_APPROVAL','event_scope':'Same target-judgment reported interlocutory proceeding; separate described issue dates remain in components; no event-identity inference from names','max_combinations':4,'source_anchors':[['IK-74028:L86','IK-74028:L87'],['IK-74028:L87','IK-74028:L122','IK-74028:L123'],['IK-74028:L88','IK-74028:L89']] if slot=='record_P5' else [['IK-74028:L117','IK-74028:L118'],['IK-74028:L118','IK-74028:L119']]}
        contracts.append(contract)
        pools=[[p for p in byid.values() if p['predicate']==pred and p['statement_status'] in statuses] for pred,statuses in atoms]
        for parts in itertools.islice(itertools.product(*pools),4):
            if not parts:continue
            maps=[{b['role']:b['entity'] for b in p['bindings']} for p in parts]
            if any(any(not m.get(role) or m[role]!=maps[0].get(role) for m in maps) for role in sc['required_roles']):continue
            # Court identity and source document are checked, not just same party strings.
            if any(p['court_level']!=contract['court_level'] or any(sources.get(r,{}).get('document')!=case for r in p['refs']) for p in parts):continue
            q=copy.deepcopy(parts[0]);q.update(id='COMPOSITE-'+content_hash([contract,[p['id'] for p in parts]])[:16],predicate=sc['predicate'],text='Explicit coverage of the old slot: '+sc['description'],bindings=[{'role':k,'entity':maps[0][k]} for k in sc['required_roles']],time_scope=None,refs=list(dict.fromkeys(r for p in parts for r in p['refs'])),quote='\n'.join(p['quote'] for p in parts),state='TRUE' if all(p['state']=='TRUE' for p in parts) else 'CONFLICTED' if any(p['state']=='CONFLICTED' for p in parts) else 'UNKNOWN',limitations=[x for p in parts for x in p['limitations']]+['Composite is coverage of attributed records, not new independent legal finding.'])
            made.append({'premise':q,'components':[p['id'] for p in parts],'contract':contract})
    return made,contracts

def validate_record(item,snap):
    c=item['contract'];p=item['premise'];rule=snap['rules'].get(c['id'].rsplit(':',1)[0]);issues=[]
    if not rule or c['rule_hash']!=content_hash(rule):return ['COMPOSITE_RULE_CHANGED']
    if c['semantic_review']!='MAINTAINER_SOURCE_REVIEW_NOT_LEGAL_APPROVAL':issues.append('COMPOSITE_REVIEW_MISSING')
    parts=[snap['premises'].get(x) for x in item['components']]
    if len(parts)!=len(c['atoms']) or any(x is None for x in parts):return ['COMPOSITE_INCOMPLETE']
    for index,(atom,part) in enumerate(zip(c['atoms'],parts)):
        if not set(part['refs']) & set(c['source_anchors'][index]):issues.append('COMPOSITE_STAGE_SOURCE_NOT_COVERED')
        rev=snap['reviews']['premises'].get(part['id'],{})
        if part['predicate']!=atom['predicate'] or part['statement_status'] not in atom['statuses']:issues.append('COMPOSITE_ATOM_MISMATCH')
        if rev.get('subject_hash')!=content_hash(part) or rev.get('decision')!='ACCEPT_RESEARCH':issues.append('COMPOSITE_COMPONENT_NOT_ACCEPTED:'+part['id'])
        if source_match(part,snap['sources'])['error']:issues.append('COMPOSITE_COMPONENT_SOURCE:'+part['id'])
        if part['court_level']!=c['court_level'] or any(snap['sources'][r]['document']!=c['source_document'] for r in part['refs']):issues.append('COMPOSITE_COURT_OR_DOCUMENT')
        pb={b['role']:b['entity'] for b in part['bindings']};ob={b['role']:b['entity'] for b in p['bindings']}
        if any(not pb.get(k) or pb[k]!=ob.get(k) for k in c['shared_roles']):issues.append('COMPOSITE_OBJECT_MISMATCH')
    if p['state']=='TRUE' and any(x['state']!='TRUE' for x in parts):issues.append('COMPOSITE_STATE_UPGRADE')
    return issues
