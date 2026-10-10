#!/usr/bin/env python3
"""One frozen cached replay. No LLM, embeddings, training or old weight scoring."""
import sys,json,copy,subprocess,hashlib,html
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.contracts import content_hash,byte_hash
from legal_bench.proof_carrying.dependency_v9 import rebind,compile_routes,select_closed
from legal_bench.proof_carrying.composite_v10 import prepare as composites,validate_record
from legal_bench.proof_carrying.policy_v9 import research_policy
from legal_bench.proof_carrying.contracts_v10 import propose
from legal_bench.proof_carrying.grounding_v9 import source_match
from legal_bench.proof_carrying.selection_v10 import load_contracts,eligibility,revise_addresses,oracle_frontier
BASE=Path('outputs/proof-carrying-graph-integration-v8');OUT=Path('outputs/proof-carrying-selection-readiness-v10')
def read(p):return json.loads(p.read_text())
def save(p,d):
    if p.exists():raise FileExistsError(p)
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')

def aggregate(requests,checked,qmap):
    out=[]
    for q in requests:
        alternatives=[r for r in checked.get('requests',[]) if qmap.get(r['id'])==q['id']]
        usable=[r for r in alternatives if not r.get('errors') and r.get('answer') is not None]
        states={r['answer'] for r in usable}
        # A valid route survives an invalid sibling; an explicit conflict remains visible.
        state='CONFLICTED' if 'CONFLICTED' in states or {'TRUE','FALSE'}<=states else 'TRUE' if 'TRUE' in states else 'UNKNOWN' if 'UNKNOWN' in states else None
        out.append({**q,'answer':state,'alternatives':alternatives,'coverage':'CHECKED_ALTERNATIVES' if alternatives else 'NO_ROUTE_WITHIN_BUDGET','formal_status':'APPROVAL_PENDING','semantic_certification':False})
    return out

def prepare_case(cid):
    i=BASE/'inputs'/cid;rules={r['id']+'@'+str(r['version']):r for r in read(i/'rules.json')};facts=read(BASE/'runs'/cid/'proposal/usable.json');sources=read(i/'sources.json');contracts=load_contracts(OUT/'contracts/registry.json',rules);vc={k:v['variables'] for k,v in contracts.items()}
    made,cc=composites(facts,rules,sources,[d for c in contracts.values() for d in c['decompositions']]);fi={p['id']:p for p in facts['premises']};cs=[];transform=[]
    for c in read(BASE/'candidates'/f'{cid}.json'):
        c=copy.deepcopy(c)
        for x in c['inputs']:
            for item in made:
                k=item['contract'];pred=fi.get(x['id'],{}).get('predicate')
                if c['rule_ref']+':'+x['slot']==k['id'] and x['kind']=='PREMISE' and pred in [a['predicate'] for a in k['atoms']]+[k['predicate']]:
                    transform.append({'candidate':c['id'],'slot':x['slot'],'old_premise':x['id'],'new_composite':item['premise']['id'],'reason':'Versioned complete old-slot coverage, not E5 equivalence'})
                    x['id']=item['premise']['id'];break
        ext={**fi,**{x['premise']['id']:x['premise'] for x in made}}
        cs.append(rebind(c,rules[c['rule_ref']],ext,vc[c['rule_ref']]))
    return rules,facts,sources,vc,made,cc,cs,transform

def run_case(cid,condition,prepared):
    rules,facts,sources,vc,made,cc,cs,transform=copy.deepcopy(prepared);i=BASE/'inputs'/cid;spec=read(i/'spec.json');requests=read(i/'requests.json');reference=read(OUT/'prepared'/cid/'reference.json');oldranking=read(BASE/'results/Simple'/cid/'ranking.json');order=oldranking['ranking']
    contracts=load_contracts(OUT/'contracts/registry.json',rules)
    ext={p['id']:p for p in facts['premises']};ext.update({x['premise']['id']:x['premise'] for x in made})
    eligibility_rows=eligibility(cs,rules,ext,sources,contracts)
    allowed={x['id'] for x in eligibility_rows if x['status']!='EXCLUDE_EXPLICIT_CONTRACT_ERROR'}
    cs=[c for c in cs if c['id'] in allowed];order=[k for k in order if k in allowed]
    selection=select_closed(cs,order,rules,requests) if condition=='simple' else {'selected':order,'budget':None,'gaps':[],'purpose':'EVALUATION_ONLY_ENUMERATION_NOT_DELIVERY'}
    fi={p['id']:p for p in facts['premises']};deriv,origins,qmap=compile_routes(cs,selection['selected'],rules,requests,fi,vc)
    deriv['counterarguments']=reference.get('decisive_counterarguments',[])
    # Reuse recorded court-conclusion decisions, never candidate USABLE as proof.
    ref=copy.deepcopy(reference);idx={r['id']:r for r in reference.get('candidate_reviews',[])}
    ref['candidate_reviews']=[{**idx[k],'id':sid} for sid,k in origins.items() if k in idx]
    policy,issues=research_policy(read(Path('outputs/proof-carrying-pipeline-v7/inputs')/cid/'policy.json'),facts,rules,sources,ref,deriv['steps'],spec)
    snap={'snapshot_id':cid+'-V10-'+condition,'case_id':cid,'stage':spec['stage'],'jurisdiction':spec['jurisdiction'],'sources':sources,'documents':[{'path':d['path'],'sha256':d['sha256']} for d in read(i/'documents.json')],'entities':{e['id']:e for e in facts['entities']},'premises':fi,'rules':rules,**policy,'variable_contracts':vc,'coverage_contracts':{k:v['coverage'] for k,v in contracts.items()},'composites':{}}
    for item in made:
        p=item['premise'];errs=['COMPONENT_REVIEW_MISSING:'+k for k in item['components'] if snap['reviews']['premises'].get(k,{}).get('decision')!='ACCEPT_RESEARCH'];snap['premises'][p['id']]=p;snap['composites'][p['id']]=item
        if not errs:snap['reviews']['premises'][p['id']]={'decision':'ACCEPT_RESEARCH','subject_hash':content_hash(p),'actor':'EXPLICIT_COMPONENT_COVERAGE_RESEARCH_ASSUMPTION','basis':item['contract']}
        else:issues.append({'stage':'COMPOSITE','record':p['id'],'errors':errs})
    dest=OUT/'results'/condition/cid
    for name,data in [('eligibility',eligibility_rows),('selection',selection),('derivation',deriv),('snapshot',snap),('policy-issues',issues),('route-origin',origins),('request-map',qmap)]:save(dest/(name+'.json'),data)
    if deriv['requests']:
        cert=propose(snap,deriv);save(dest/'certificate.json',cert);save(dest/'manifest.json',{'snapshots':{snap['snapshot_id']:{'path':'snapshot.json','sha256':byte_hash(dest/'snapshot.json')}}})
        argv=[sys.executable,'scripts/check_realcase_certificate_v10.py',str(dest/'certificate.json'),'--manifest',str(dest/'manifest.json')];p=subprocess.run(argv,capture_output=True,text=True,timeout=120)
        (dest/'stdout.txt').write_text(p.stdout);(dest/'stderr.txt').write_text(p.stderr);save(dest/'invocation.json',{'argv':argv,'returncode':p.returncode})
        if p.returncode:raise RuntimeError(p.stderr)
        checked=json.loads(p.stdout)
        if checked.get('status')!='COMPLETED':raise RuntimeError('CHECKER_CONTRACT_FAILED:'+str(checked))
    else:checked={'requests':[],'steps':{}}
    save(dest/'checked.json',checked)
    if condition=='pool':save(dest/'oracle.json',oracle_frontier(checked,qmap,origins))
    ans=aggregate(requests,checked,qmap)
    save(dest/'analysis.json',{'requests':ans,'counterarguments':deriv['counterarguments'],'all_raw_relations':facts['relations'],'all_raw_limitations':facts.get('limitations',[]),'selection_gaps':selection['gaps'],'not_legal_approval':True})
    (dest/'index.html').write_text('<!doctype html><meta charset="utf-8"><h1>'+cid+' / '+condition+'</h1><p>Research reconstruction; all alternative routes retained, legal approval pending.</p><pre>'+html.escape(json.dumps(ans,ensure_ascii=False,indent=2))+'</pre><h2>Counterarguments</h2><pre>'+html.escape(json.dumps(deriv['counterarguments'],ensure_ascii=False,indent=2))+'</pre>')
    return {'case':cid,'condition':condition,'true':sum(q['answer']=='TRUE' for q in ans),'unknown':sum(q['answer']=='UNKNOWN' for q in ans),'null':sum(q['answer'] is None for q in ans),'conflicted':sum(q['answer']=='CONFLICTED' for q in ans),'requests':len(ans),'selected':selection['selected'],'alternative_checks':len(checked.get('requests',[]))}

def main():
    cases=read(BASE/'protocol.json')['case_order']
    if sys.argv[1]=='prepare':
        for cid in cases:
            rules,facts,src,vc,made,cc,cs,t=prepare_case(cid)
            reference,ledger=revise_addresses(read(BASE/'runs'/cid/'reference/usable.json'),src)
            save(OUT/'prepared'/cid/'reference.json',reference);save(OUT/'prepared'/cid/'reference-address-revision.json',ledger)
            for name,value in [('variables',vc),('composites',made),('composite-contracts',cc),('candidates',cs),('transformations',t)]:save(OUT/'prepared'/cid/(name+'.json'),value)
    elif sys.argv[1]=='run':
        frozen=read(OUT/'freeze.json')
        assert all(byte_hash(Path(p))==h for p,h in frozen['method_hashes'].items())
        assert all(byte_hash(Path(p))==h for p,h in frozen['input_hashes'].items())
        rows=[]
        for cid in cases:
            prepared=prepare_case(cid)
            for cond in ['simple','pool']:rows.append(run_case(cid,cond,prepared))
        save(OUT/'comparison.json',rows)
        print(json.dumps(rows))
if __name__=='__main__':main()
