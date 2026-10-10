"""Ranked applications -> bounded derivation -> independent checker -> all request slots."""
import copy,json,subprocess,sys,html
from pathlib import Path
from .contracts import read_json,content_hash,byte_hash
from .workflow_v7 import write_once,text_once
from .workflow_v8 import import_derivation,complete_requests,fact_source_check
from .realcase_engine import propose
from .realcase_grounding_v4 import step_semantic_hash
from .candidates_v8 import select

def compile_derivation(candidates,selected,rules,requests,reference):
    chosen=[c for key in selected for c in candidates if c['id']==key]
    by_rule={}
    for c in chosen:by_rule.setdefault(c['rule_ref'],c)
    steps=[];notes=[]
    for c in chosen:
        inputs=[]
        for i in c['inputs']:
            if i['kind']=='PREMISE':inputs.append(i)
            elif i['kind']=='RULE_DEPENDENCY':
                dep=by_rule.get(i['id'])
                if dep:inputs.append({'slot':i['slot'],'kind':'STEP','id':dep['id']})
                else:notes.append('BUDGET_OR_CANDIDATE_DEPENDENCY_MISSING:'+c['id']+':'+i['slot'])
        steps.append({'id':c['id'],'rule_ref':c['rule_ref'],'bindings':c['bindings'],'time_scope':c['time_scope'],
            'inputs':inputs,'proposed_state':'TRUE','explanation':'Candidate reconstruction claim; not a legal finding. Independent checker must re-evaluate prerequisites.'})
    qs=[];missing=[]
    for q in requests:
        compatible=[c for c in chosen if rules[c['rule_ref']]['conclusion_predicate']==q['predicate']]
        if compatible:
            qs.append({**q,'step_id':compatible[0]['id'],'proposed_state':'TRUE'})
        else:missing.append(q['id'])
    # Counterarguments are attached from source reference only AFTER ranking for audit,
    # never to feature graph or ranking. Raw proposal limitations are also preserved elsewhere.
    return {'steps':steps,'requests':qs,'counterarguments':reference.get('decisive_counterarguments',[]),
        'gaps':notes+['NO_SELECTED_APPLICATION:'+q for q in missing]},missing

def research_policy(old_policy,facts,rules,sources,reference,steps,spec):
    policy=copy.deepcopy(old_policy)
    policy['reviews']['premises']={};policy['court_assessments']={};policy['role_mappings']={};policy['role_views']={}
    policy['formal_approval']=None;policy['policy_version']='V8_EXTERNAL_MODEL_REFERENCE_RESEARCH_ONLY'
    issues=[]
    def grounded(r,refskey='refs',quotekey='quote'):
        refs=r.get(refskey,[]);q=r.get(quotekey,'')
        return refs and all(x in sources for x in refs) and bool(q) and any(q in sources[x]['text'] for x in refs)
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

def run_case(root,cid,method,scores):
    root=Path(root);dest=root/'results'/method/cid
    if dest.exists():raise FileExistsError('RESULT_EXISTS_NO_REINTERPRETATION')
    inp=root/'inputs'/cid;spec=read_json(inp/'spec.json');facts=read_json(root/'runs'/cid/'proposal/usable.json')
    rules={r['id']+'@'+str(r['version']):r for r in read_json(inp/'rules.json')};sources=read_json(inp/'sources.json');requests=read_json(inp/'requests.json')
    candidates=read_json(root/'candidates'/(cid+'.json'));selection=select(candidates,scores,read_json(root/'protocol.json')['candidate_budget'])
    reference=read_json(root/'runs'/cid/'reference/usable.json') if (root/'runs'/cid/'reference/usable.json').exists() else {}
    deriv,missing=compile_derivation(candidates,selection['selected'],rules,requests,reference)
    imported=import_derivation(deriv,requests)
    for q in imported['request_slots']:
        if q['id'] in missing:q.update(technical_status='NOT_SELECTED',failure_stage='MATERIAL_BUDGET',reason=['NO_SELECTED_RULE_APPLICATION'],answer=None)
    policy,issues=research_policy(read_json(Path('outputs/proof-carrying-pipeline-v7/inputs')/cid/'policy.json'),facts,rules,sources,reference,deriv['steps'],spec)
    snap={'snapshot_id':cid+'-'+method+'-'+content_hash(selection)[:12],'case_id':cid,'stage':spec['stage'],'jurisdiction':spec['jurisdiction'],
        'sources':sources,'documents':[{'path':d['path'],'sha256':d['sha256']} for d in read_json(inp/'documents.json')],
        'entities':{e['id']:e for e in facts['entities']},'premises':{p['id']:p for p in facts['premises']},'rules':rules,**policy}
    for name,data in [('ranking',{'scores':scores,**selection}),('snapshot',snap),('derivation',deriv),('import',imported),('policy-issues',issues)]:write_once(dest/(name+'.json'),data)
    if deriv['requests']:
        cert=propose(snap,deriv);write_once(dest/'certificate.json',cert);write_once(dest/'manifest.json',{'snapshots':{snap['snapshot_id']:{'path':'snapshot.json','sha256':byte_hash(dest/'snapshot.json')}}})
        argv=[sys.executable,'scripts/check_realcase_certificate_v4.py',str(dest/'certificate.json'),'--manifest',str(dest/'manifest.json')]
        result=subprocess.run(argv,capture_output=True,text=True,timeout=120)
        text_once(dest/'checker-stdout.txt',result.stdout);text_once(dest/'checker-stderr.txt',result.stderr)
        write_once(dest/'invocation.json',{'argv':argv,'returncode':result.returncode,'independent_process':True})
        try:checked=json.loads(result.stdout)
        except ValueError:checked={'status':'TECHNICAL_FAILURE','answer':None,'reason':'CHECKER_OUTPUT_INVALID'}
    else:checked={'status':'COMPLETED','requests':[],'steps':{},'reason':'NO_SELECTED_REQUEST_APPLICATION'}
    write_once(dest/'checker-result.json',checked);complete=complete_requests(imported,checked);write_once(dest/'analysis.json',complete)
    body='<h1>'+html.escape(cid+' / '+method)+'</h1><p>Research reconstruction. Legal approval pending. Rankings are not proof.</p>'
    for q in complete['requests']:body+='<h2>'+html.escape(q['id'])+'</h2><pre>'+html.escape(json.dumps(q,indent=2,ensure_ascii=False))+'</pre>'
    body+='<h2>Decisive counterarguments</h2><pre>'+html.escape(json.dumps(deriv['counterarguments'],indent=2))+'</pre><h2>Source links</h2>'
    for ref,s in sources.items():body+='<details id="'+html.escape(ref)+'"><summary>'+html.escape(ref)+'</summary><p>'+html.escape(s['text'])+'</p></details>'
    text_once(dest/'index.html','<!doctype html><meta charset="utf-8"><title>Checked development analysis</title>'+body)
    return complete
