"""Cached reference decisions plus unified quote location; no automatic semantic approval."""
import copy
from .contracts import content_hash
from .workflow_v8 import fact_source_check
from .grounding_v9 import source_match, step_semantic_hash
def research_policy(old_policy,facts,rules,sources,reference,steps,spec):
    policy=copy.deepcopy(old_policy)
    policy['reviews']['premises']={};policy['court_assessments']={};policy['role_mappings']={};policy['role_views']={}
    policy['formal_approval']=None;policy['policy_version']='V8_EXTERNAL_MODEL_REFERENCE_RESEARCH_ONLY'
    issues=[]
    def grounded(r,refskey='refs',quotekey='quote'):
        refs=r.get(refskey,[]);q=r.get(quotekey,'')
        return not source_match({'refs':refs,'quote':q},sources)['error']
    counts={}
    for r in reference.get('premise_reviews',[]):counts[r.get('id')]=counts.get(r.get('id'),0)+1
    pidx={p['id']:p for p in facts['premises']}
    for r in reference.get('premise_reviews',[]):
        p=pidx.get(r.get('id'))
        if p and counts[r['id']]==1 and r.get('decision')=='ACCEPT_RESEARCH' and grounded(r) and fact_source_check(p,sources).startswith('ADDRESS_AND_ROLE_VALID'):
            policy['reviews']['premises'][p['id']]={'decision':'ACCEPT_RESEARCH','subject_hash':content_hash(p),
                'actor':'INDEPENDENT_WEB_MODEL_SOURCE_REFERENCE','qualified_legal_approval':False,'basis':r['reason'],'refs':r['refs']}
        else:issues.append({'stage':'PREMISE_ACCEPTANCE','record':r.get('id'),'reason':'MISSING_UNACCEPTED_OR_SOURCE_UNVERIFIED'})
    refs={r['id']:r for r in reference.get('candidate_reviews',[]) if isinstance(r,dict) and 'id' in r}
    for s in steps:
        r=refs.get(s['id']);rule=rules[s['rule_ref']]
        if rule['operator']!='OPEN_TEXT' or not r or r.get('recorded_conclusion')!='TRUE':continue
        if not grounded(r,'conclusion_refs','conclusion_quote') or any(sources[x]['document_role']!='TARGET' or sources[x].get('role')=='DISPOSITION_ONLY' for x in r['conclusion_refs']):
            issues.append({'stage':'COURT_ASSESSMENT','record':s['id'],'reason':'CONCLUSION_REFERENCE_UNVERIFIED'});continue
        policy['court_assessments'][s['id']]={'id':'ASSESS-'+s['id'],'case_id':spec['case_id'],'stage':spec['stage'],
            'rule_ref':s['rule_ref'],'rule_hash':content_hash(rule),'predicate':rule['conclusion_predicate'],
            'bindings':s['bindings'],'time_scope':s['time_scope'],'statement_status':'TARGET_COURT_FINDING','state':'TRUE',
            'refs':r['conclusion_refs'],'quote':r['conclusion_quote'],'text':r['reason'],
            'step_semantic_hash':step_semantic_hash(s),'review':{'decision':'ACCEPT_RESEARCH','actor':'MODEL_ASSISTED_SOURCE_REVIEW','qualified_legal_approval':False}}
        record=policy['court_assessments'][s['id']]
        record['review']['subject_hash']=content_hash({k:v for k,v in record.items() if k!='review'})
    return policy,issues
