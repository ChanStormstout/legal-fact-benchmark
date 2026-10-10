"""Immutable real-case preparation, web ingress and independent local execution."""
import argparse, copy, datetime, json, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.realcase_contracts import *
from legal_bench.proof_carrying.realcase_tasks import CASES,KINDS,prompt
from legal_bench.proof_carrying.realcase_engine import propose,explanation
from legal_bench.proof_carrying.realcase_checker_v2_1 import inspect_sources
from legal_bench.rules_verdict_v1.source_identity_v2 import parse_responses,merge_windows,declare_body,validate_view,validate_submission

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/proof-carrying-realcase-v2'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def text_once(p,text):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:f.write(text)
def parsed(cid,kind):return read_json(OUT/'runs'/cid/kind/'parsed.json')
def assert_frozen():
    f=read_json(OUT/'freeze/interface-01/config.json')
    for p,h in {**f['code_hashes'],**f['material_hashes']}.items():
        if byte_hash(ROOT/p)!=h:raise ValueError('FROZEN_FILE_CHANGED:'+p)

def prepare_sources():
    assert (OUT/'registration.json').exists()
    rs=[]
    for p in sorted((OUT/'sources/raw').glob('*.txt')):rs+=parse_responses(p.read_text(),str(p.relative_to(ROOT)))
    docs=merge_windows(rs); audit={}
    for cid,c in CASES.items():
        d=declare_body(docs[cid],*c['body'],'Header through final disposition; related AI tags and site navigation excluded. Full rendered body checked, not original certified court copy.')
        view={'case_id':cid,'segments':[s for s in d['segments'] if c['body'][0]<=s['original_line']<=c['body'][1]]}
        mapping=validate_view(view,d)
        write_once(OUT/'sources'/f'{cid}.json',d)
        write_once(OUT/'sources'/f'{cid}-map.json',mapping)
        text_once(OUT/'sources'/f'{cid}.txt','\n'.join('['+s['id']+'] '+s['text'] for s in view['segments'])+'\n')
        audit[cid]={'identity':d['titles'],'url':d['url'],'body_coverage':d['body_coverage'],
            'source_status':d['status'],'original_exhibits_obtained':False,'certified_court_copy_obtained':False,
            'cited_precedent_originals_obtained':False,'cited_rule_status':'TARGET_JUDGMENT_REPORT_ONLY'}
    write_once(OUT/'source-audit.json',audit)

def task(cid,kind):
    assert_frozen();path=OUT/'tasks'/cid/kind
    if (path/'task.txt').exists():return path
    attachments={}
    if kind!='rules':attachments['rules']=parsed(cid,'rules')
    if kind=='derivation':attachments['facts']=parsed(cid,'facts')
    document=read_json(OUT/'sources'/f'{cid}.json')
    text=prompt(cid,kind,document,attachments)
    view={'case_id':cid,'segments':[s for s in document['segments'] if CASES[cid]['body'][0]<=s['original_line']<=CASES[cid]['body'][1]]}
    audit=validate_submission(text,view,document)
    text_once(path/'task.txt',text);write_once(path/'schema.json',schemas(kind));write_once(path/'delivery.json',audit)
    write_once(path/'manifest.json',{'case':cid,'kind':kind,'built_at':now(),'sha256':byte_hash(path/'task.txt'),
        'bytes':len(text.encode()),'characters':len(text),'attachments_hash':content_hash(attachments),
        'independent_reference':kind=='reference','sees_model_facts':kind=='derivation',
        'sees_checker_or_reference':False})
    return path

def freeze():
    assert not (OUT/'freeze/config.json').exists()
    paths=list((ROOT/'legal_bench/proof_carrying').glob('*.py'))
    paths += [ROOT/p for p in ('scripts/proof_realcase_v2.py','scripts/check_realcase_certificate.py','tests/test_proof_realcase_v2.py',
        'legal_bench/rules_verdict_v1/source_identity_v2.py','legal_bench/rules_verdict_v1/contracts.py',
        'legal_bench/irac_application/aligned_v2_runtime.py','legal_bench/irac_application/contract_v5.py')]
    code={str(p.relative_to(ROOT)):byte_hash(p) for p in paths}
    for p in paths:
        dst=OUT/'freeze/code'/p.relative_to(ROOT);dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
    mats={str(p.relative_to(ROOT)):byte_hash(p) for p in (OUT/'sources').rglob('*') if p.is_file()}
    cfg={'version':'REALCASE_V2','frozen_at':now(),'code_hashes':code,'material_hashes':mats,
        'task':'RECONSTRUCTION_NOT_PREDICTION','order':[(c,k) for c in CASES for k in KINDS],
        'max_web_tasks':15,'max_per_case':5,'semantic_retries':0,'models':'visible ordinary High; exact model unavailable unless shown',
        'new_local_model_calls':0,'legal_approval':'PENDING_QUALIFIED_REVIEW','reference':'MODEL_ASSISTED_NOT_HUMAN_GOLD',
        'rule_policy':'Only accepted source-reviewed translations; OPEN_TEXT remains unimplemented; target-adopted precedent account is not verification of original precedent.',
        'premise_policy':'Attributed judicial findings and procedural records accepted provisionally after source review; parties remain claims; disposition comparison-only; non-proof is not falsity.',
        'evaluation':['source fidelity and decisive opposition','before/after same cached proposal','valid preservation and invalid rejection','approval gaps separate','graph teaching interface only'],
        'mutation_plan':['wrong object','wrong time','statement upgrade','missing rule version','omitted exception','cycle','conclusion type upgrade','valid same-source substitution','irrelevant addition','independent OR','historical snapshot reopen'],
        'stops':'15 tasks maximum; no semantic retry, no training or new cohort runs; calibration preparation bounded separately; no legal approval fabricated; no commit/push',
        'dynamic_tasks':'Frozen assembler; later rules/facts inserted verbatim JSON with hashes; reference cannot see facts/derivation/checker'}
    write_once(OUT/'freeze/config.json',cfg)
    for c in CASES:task(c,'rules')
    write_once(OUT/'progress.json',{'status':'FROZEN','slots':[{'case':c,'kind':k,'status':'NOT_SUBMITTED'} for c in CASES for k in KINDS]})

def ingest(cid,kind):
    assert_frozen();d=OUT/'runs'/cid/kind;raw=(d/'raw-response.txt').read_text();s=raw.strip();ops=[]
    if s.startswith('```') and s.endswith('```'):
        s=s.split('\n',1)[1].rsplit('```',1)[0].strip();ops.append('REMOVE_OUTER_FENCE_ONLY')
    result={'status':'OK','answer':None,'format_operations':ops,'semantic_verified':False,'raw_sha256':byte_hash(d/'raw-response.txt')}
    try:
        v=json.loads(s);validate(v,schemas(kind))
        write_once(d/'parsed.json',v);result['answer_path']=str((d/'parsed.json').relative_to(OUT));result['answer']=v
    except (ValueError,TypeError,KeyError) as exc:result.update(status='FORMAT_ERROR',reason=str(exc))
    write_once(d/'result.json',result)
    return {k:v for k,v in result.items() if k!='answer'}

def snapshot(cid, decisions, name='S1'):
    """Source decisions separately recorded; no automatic semantic approval from quote matches."""
    assert_frozen();facts=parsed(cid,'facts');rules=parsed(cid,'rules');refs=parsed(cid,'rule_review')
    d=read_json(OUT/'sources'/f'{cid}.json');out=OUT/'cases'/cid
    review=read_json(decisions);sources={s['id']:{'text':s['text'],'url':d['url'],'document':cid,
        'role':'DISPOSITION_ONLY' if s['original_line']==CASES[cid]['body'][1] else 'JUDGMENT_TEXT',
        'original_line':s['original_line']} for s in d['segments'] if CASES[cid]['body'][0]<=s['original_line']<=CASES[cid]['body'][1]}
    rr=unique(refs['reviews'],'rule_id');rulemap={r['id']+'@'+str(r['version']):r for r in rules['rules']}
    prem=unique(facts['premises']);ents=unique(facts['entities'])
    audit={'rules':{},'premises':{},'quarantined':[]}
    for key,r in rulemap.items():
        rev=rr.get(r['id']);err=inspect_sources(r,sources)
        accepted=bool(rev and rev['decision']=='ACCEPT_AS_RESEARCH_TRANSLATION' and not err and review['rules'].get(key)=='ACCEPT_RESEARCH')
        audit['rules'][key]={'subject_hash':content_hash(r),'decision':'ACCEPT_RESEARCH' if accepted else 'SUSPEND',
            'web_review':rev,'local_source_issue':err,'actor':'MODEL_ASSISTED_SOURCE_REVIEW','qualified_legal_approval':False}
    for key,p in prem.items():
        err=inspect_sources(p,sources)
        accepted=not err and review['premises'].get(key)=='ACCEPT_RESEARCH'
        audit['premises'][key]={'subject_hash':content_hash(p),'decision':'ACCEPT_RESEARCH' if accepted else 'SUSPEND',
            'local_source_issue':err,'actor':'MODEL_ASSISTED_SOURCE_REVIEW','qualified_legal_approval':False}
    documents=[{'path':f'../../sources/{cid}.json', 'sha256':byte_hash(OUT/'sources'/f'{cid}.json')}]
    snap={'snapshot_id':cid+'-'+name,'case_id':cid,'stage':CASES[cid]['stage'],'jurisdiction':'India',
        'sources':sources,'documents':documents,'entities':ents,'premises':prem,'rules':rulemap,'reviews':audit,
        'scope_reviews':{k:{'subject_hash':content_hash(r),'jurisdiction_compatible':review.get('scope',{}).get(k,{}).get('jurisdiction_compatible',False),'stage_compatible':review.get('scope',{}).get(k,{}).get('stage_compatible',False),'basis':review.get('scope',{}).get(k,{}).get('basis','MISSING'),'actor':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_LEGAL_APPROVAL'} for k,r in rulemap.items()},
        'decision_record_hash':byte_hash(decisions),'formal_approval':'PENDING','policy_version':'MODEL_SOURCE_REVIEW_RECONSTRUCTION_V1'}
    write_once(out/'snapshots'/f'{name}.json',snap)
    public={'snapshots':{snap['snapshot_id']:{'path':f'snapshots/{name}.json','sha256':byte_hash(out/'snapshots'/f'{name}.json')}}}
    write_once(out/f'manifest-{name}.json',public)
    return snap

def run(cid,name='S1'):
    assert_frozen();out=OUT/'cases'/cid;snap=read_json(out/'snapshots'/f'{name}.json')
    cert=propose(snap,parsed(cid,'derivation'));dst=out/'runs'/name
    write_once(dst/'certificate.json',cert)
    cmd=[sys.executable,str(ROOT/'scripts/check_realcase_certificate_v2_1.py'),str(dst/'certificate.json'),'--manifest',str(out/f'manifest-{name}.json')]
    p=subprocess.run(cmd,text=True,capture_output=True,cwd=ROOT)
    text_once(dst/'checker-stdout.txt',p.stdout);text_once(dst/'checker-stderr.txt',p.stderr)
    write_once(dst/'invocation.json',{'argv':cmd,'exit_code':p.returncode,'independent_process':True,'time':now()})
    try:r=json.loads(p.stdout)
    except ValueError:r={'status':'RUN_LOG_ERROR','answer':None}
    write_once(dst/'check.json',r)
    text_once(dst/'explanation.md',explanation(r,snap,cert))
    from legal_bench.proof_carrying.review_priority_v2 import order
    write_once(out/'review-order.json',order(parsed(cid,'facts')))
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['task','ingest','snapshot','run']);p.add_argument('args',nargs='*');a=p.parse_args()
    f={'sources':prepare_sources,'freeze':freeze,'task':task,'ingest':ingest,'snapshot':snapshot,'run':run}[a.action]
    result=f(*a.args)
    if result is not None:print(json.dumps(result,default=str,ensure_ascii=False,indent=2))
