"""Readable conditional analysis from predictions; verification claims remain narrow."""
from .aligned_logic import evaluate,combine_bound
from .aligned_graph import check_refs

def render(graph, predictions):
    template=graph['legal_structure'];proposal=graph['proposal'];sources=graph['source_manifest']
    tests=[];states={}
    for test in template['tests']:
        tid=test['id'];p=predictions.get(tid)
        links=[l for l in proposal.get('links',[]) if l.get('test_id')==tid]
        grounds=[]
        for link in links:
            grounds.append(dict(proposal_id=link['id'],direction=link['direction'],binding=link.get('binding',[]),limitations=link.get('limitations',[]),references=[dict(r,recovered_text=sources.get(r['source_id'],{}).get('text'),address_located=r['source_id'] in sources and r.get('quote','') in sources[r['source_id']]['text']) for r in link.get('source_refs',[])],semantic_verified=False))
        status=p['status'] if p else 'UNRESOLVED';states[tid]=dict(status=status,reason='MODEL_PREDICTION_NOT_PROOF' if p else 'NO_PREDICTION')
        tests.append(dict(test_id=tid,proposition=test['text'],prediction=p,candidate_grounds=grounds,checks=['source addresses only','no automatic identity from matching roles or IDs'],semantic_verified=False))
    definitions={i['id']:i['expression'] for i in template['elements']};elements=[];claims=[]
    for item in template['elements']:
        candidate=evaluate(item['expression'],states,definitions)
        elements.append(dict(element_id=item['id'],text=item['text'],candidate_logic=candidate,binding_requirements=item.get('binding_requirements',[]),binding_status='UNRESOLVED_UNLESS_EXPLICITLY_REVIEWED',verified_result=False))
    linkmap={l['id']:l for l in proposal.get('links',[])}
    combinations=[]
    for c in proposal.get('combinations',[]):
        selected=[linkmap[x] for x in c.get('test_links',[]) if x in linkmap]
        errors=[];roles={};witness_refs=[]
        if len(selected)!=len(c.get('test_links',[])):errors.append('INVALID_LINK_REFERENCE')
        for l in selected:
            for b in l.get('binding',[]):roles.setdefault(b['role'],[]).append((l['id'],b.get('entity_id')))
        for role,members in roles.items():
            if len(members)<2:continue
            covered=False
            for w in c.get('identity_witnesses',[]):
                wm={(m['link_id'],m.get('entity_id')) for m in w.get('members',[]) if m['role']==role}
                if set(members)<=wm and w.get('source_refs') and not check_refs(w['source_refs'],sources):covered=True;witness_refs+=w['source_refs']
            if not covered:errors.append('NO_EXPLICIT_IDENTITY_WITNESS:'+role)
        if c.get('scope_status')!='COMPATIBLE':errors.append('RULE_SCOPE_NOT_ESTABLISHED')
        if c.get('limitations'):errors.append('PROPOSED_COMBINATION_HAS_LIMITATIONS')
        refs=[r for l in selected for r in l.get('source_refs',[])]+witness_refs
        errors+=check_refs(refs,sources)
        combinations.append(dict(binding_id=c['id'],binding_source_refs=refs,identity_checks_complete=bool(selected) and not errors,tests={l['test_id']:states[l['test_id']] for l in selected if l['test_id'] in states},checks=errors,semantic_verified=False))
    for item in template['claims']:
        bound=combine_bound(item['expression'],combinations,definitions)
        claims.append(dict(claim_id=item['id'],text=item['text'],conditional_combination=bound,status=bound['status'],reason='Conditional on model test predictions and explicitly proposed source-linked bindings; address checks do not establish their semantic correctness.',verified_result=False))
    return dict(case_id=graph['case_id'],tests=tests,elements=elements,claims=claims,burdens=template['burdens'],scope=template['scope'],coverage_limits=template['coverage_limits'],semantic_status='EXPERIMENTAL_MODEL_ANALYSIS_NOT_LEGAL_PROOF',historical_prediction='SEPARATE_NOT_SCORED_HERE')
