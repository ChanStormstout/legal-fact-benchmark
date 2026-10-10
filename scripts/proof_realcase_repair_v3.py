"""One bounded, versioned cached replay. Does not call a model or alter v2."""
import copy, datetime, json, subprocess, sys, shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.contracts import read_json, write_once, content_hash, byte_hash
from legal_bench.proof_carrying.realcase_engine import propose
from legal_bench.proof_carrying.realcase_grounding_v3 import source_match

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'outputs/proof-carrying-realcase-v2'
OUT=ROOT/'outputs/proof-carrying-local-repair-v3'
CASES=('789051','1418721','1841885')

def review(record):
    record['review']={'subject_hash':content_hash(record),'decision':'ACCEPT_RESEARCH',
        'actor':'MODEL_ASSISTED_SOURCE_REVIEW','qualified_legal_approval':False}
    return record

def accept(snap,section,key,record,basis):
    snap['reviews'][section][key]={'subject_hash':content_hash(record),'decision':'ACCEPT_RESEARCH',
        'actor':'MODEL_ASSISTED_SOURCE_REVIEW','qualified_legal_approval':False,'basis':basis}

def assessment(snap,prop,sid,lines,scope):
    step=next(s for s in prop['steps'] if s['id']==sid);rule=snap['rules'][step['rule_ref']]
    refs=[f"IK-{snap['case_id']}:L{n}" for n in lines]
    a={'id':'CA-'+snap['case_id']+'-'+sid,'case_id':snap['case_id'],'stage':snap['stage'],
       'step_hash':content_hash(step),'rule_ref':step['rule_ref'],'rule_hash':content_hash(rule),
       'predicate':rule['conclusion_predicate'],'bindings':step['bindings'],'time_scope':step['time_scope'],
       'statement_status':'TARGET_COURT_FINDING','state':'TRUE','refs':refs,
       'quote':' '.join(snap['sources'][r]['text'] for r in refs),'scope':scope,
       'role':'Attributed assessment assumed after model-assisted source review; legal merits are not recomputed.',
       'prior_review':'proof-carrying-realcase-v2/final-source-review.json; independent reference and source lines'}
    snap.setdefault('court_assessments',{})[sid]=review(a)

def revise_sopan(snap,prop):
    old=snap['rules']['R6@1'];r=copy.deepcopy(old);r['version']=2
    r.update(origin='RESEARCH_TRANSLATION',operator='ALL',
        description='Recorded procedural tenancy route and express reservation of merits do not decide those reserved merits.',
        conclusion_text='Continuation of the tenancy issue does not decide the reserved possession or injunction merits; a forcible-possession plea may be raised and considered only insofar as relevant to the continued suit.',
        source_refs=['IK-1841885:L136','IK-1841885:L151'],source_quote=snap['sources']['IK-1841885:L151']['text'],
        unimplemented=['No independent assessment of possession, Section 6 relief or equitable injunction entitlement.'],
        scope_limits=['Restricted to this judgment-stage reconstruction. Relevant pleas may be accepted or rejected; no mandatory full merits adjudication of every claim is inferred.'])
    track=copy.deepcopy(old['slots'][0]);track['required_roles']=['subject','opponent','property']
    reserve={'name':'express_merits_reservation','predicate':'COURT_EXPRESSLY_RESERVED_DISPOSSESSION_MERITS',
        'description':'The court expressly declines a merits view and leaves a plea to trial only if raised and relevant.',
        'expected':'TRUE','allowed_statuses':['TARGET_COURT_FINDING'],
        'required_roles':['subject','opponent','property'],'time_required':False}
    r['slots']=[track,reserve];r['exception_slots']=[]
    s6=next(s for s in prop['steps'] if s['id']=='S6')
    p={'id':'F15-REVIEWED','predicate':reserve['predicate'],
       'text':'The Supreme Court expressly reserved its view on the claimed forcible possession and allowed a relevant plea to be raised and accepted or rejected at trial. This does not decide actual dispossession or equitable entitlement.',
       'bindings':copy.deepcopy(s6['bindings']),'time_scope':None,'statement_status':'TARGET_COURT_FINDING',
       'speaker':'Supreme Court of India','court_level':'Supreme Court','stage':snap['stage'],'state':'TRUE',
       'refs':['IK-1841885:L151'],'quote':snap['sources']['IK-1841885:L151']['text'],
       'limitations':['Source-reviewed maintainer translation, not a new model output or formal legal approval. F11 and all unresolved merits remain unchanged.']}
    snap['premises'][p['id']]=p;snap['rules']['R6@2']=r
    accept(snap,'premises',p['id'],p,'Express reservation L151; no inference of false entitlement.')
    accept(snap,'rules','R6@2',r,'V2 independently flagged R6 overbreadth; L136/L151 support this narrower non-entailment only.')
    snap['scope_reviews']['R6@2']={'subject_hash':content_hash(r),'jurisdiction_compatible':True,
        'stage_compatible':True,'basis':'Same judgment-stage procedural reconstruction; not a new general merits rule.'}
    s6.update(rule_ref='R6@2',inputs=[{'slot':track['name'],'kind':'STEP','id':'S4'},
        {'slot':reserve['name'],'kind':'PREMISE','id':p['id']}],
        explanation='Explicit reservation and the tenancy track support only the distinction between procedural continuation and unresolved merits.')
    next(q for q in prop['requests'] if q['id']=='Q5')['text']=r['conclusion_text']

def prepare():
    assert (OUT/'registration.json').exists()
    for cid in CASES:
        original=read_json(OLD/'cases'/cid/'snapshots/S1.json')
        original_prop=read_json(OLD/'runs'/cid/'derivation/parsed.json')
        for track in ('engine-only','reviewed-reconstruction'):
            snap=copy.deepcopy(original);prop=copy.deepcopy(original_prop)
            snap['snapshot_id']=cid+'-LOCAL-V3-'+track
            snap['documents']=[{'path':str(OLD/'sources'/f'{cid}.json'),'sha256':byte_hash(OLD/'sources'/f'{cid}.json')}]
            # Re-evaluate ONLY location holds. Both earlier semantic reviews must already accept.
            decisions=read_json(OLD/'cases'/cid/'source-review-S1.json')
            restored=[]
            for key,r in snap['rules'].items():
                prev=snap['reviews']['rules'][key]
                if (prev.get('local_source_issue')=='QUOTE_NOT_LOCATED' and
                    prev.get('web_review',{}).get('decision')=='ACCEPT_AS_RESEARCH_TRANSLATION' and
                    decisions['rules'].get(key)=='ACCEPT_RESEARCH' and not source_match(r,snap['sources'])['error']):
                    accept(snap,'rules',key,r,'Earlier semantic accept retained; reversible renderer whitespace location repaired.')
                    restored.append(key)
            if track=='reviewed-reconstruction':
                if cid=='789051': assessment(snap,prop,'S2',[106,107],'Settled-possession protection in this recorded judgment, not ownership confirmation or a universal automatic test.')
                if cid=='1418721':
                    assessment(snap,prop,'S2',[85],'Court joint evidence assessment of the collectively identified suit properties, not independent authentication of exhibits.')
                    assessment(snap,prop,'S5',[100,101],'Court rejection of this alternative adverse-possession ground, not proof that possession never existed.')
                if cid=='1841885':
                    assessment(snap,prop,'S2',[134,135],'Court classification of the tenancy subject as civil-adjudicable, not proof that the asserted tenancy exists.')
                    p=snap['premises']['F8'];r=snap['rules']['R5@1']
                    snap['role_mappings']={'S5:trust_denial_recorded':review({
                        'id':'MAP-1841885-S5-F8','case_id':cid,'stage':snap['stage'],'rule_ref':'R5@1',
                        'rule_hash':content_hash(r),'premise_id':'F8','premise_hash':content_hash(p),'slot':'trust_denial_recorded',
                        'roles':{'subject':'opponent','opponent':'subject','property':'property','transaction':'transaction'},
                        'refs':['IK-1841885:L138'],'quote':snap['sources']['IK-1841885:L138']['text'],
                        'basis':'Two speakers dispute the same taking. Preserve F8 speaker/claim status; map only the rule-slot participant perspective. No entity merge.'})}
                    revise_sopan(snap,prop)
            dst=OUT/'cases'/cid/track
            write_once(dst/'snapshot.json',snap);write_once(dst/'proposal.json',prop)
            write_once(dst/'certificate.json',propose(snap,prop))
            write_once(dst/'manifest.json',{'snapshots':{snap['snapshot_id']:{'path':'snapshot.json','sha256':byte_hash(dst/'snapshot.json')}}})
            write_once(dst/'lineage.json',{'parent_snapshot':str(OLD/'cases'/cid/'snapshots/S1.json'),
                'parent_snapshot_hash':content_hash(original),'raw_proposal_hash':content_hash(original_prop),
                'same_model_proposal':prop==original_prop,'restored_location_holds':restored,
                'policy_changes':{'court_assessments':snap.get('court_assessments',{}),'role_mappings':snap.get('role_mappings',{})},
                'rule_translation_change':cid=='1841885' and track=='reviewed-reconstruction',
                'legal_approval':False,'new_model_calls':0})
    paths=[ROOT/p for p in ['scripts/proof_realcase_repair_v3.py','scripts/check_realcase_certificate_v3.py',
        'legal_bench/proof_carrying/realcase_checker_v3.py','legal_bench/proof_carrying/realcase_grounding_v3.py',
        'legal_bench/proof_carrying/realcase_engine.py','legal_bench/proof_carrying/realcase_contracts.py',
        'legal_bench/proof_carrying/contracts.py','tests/test_proof_realcase_v3.py']]
    for p in paths:
        dest=OUT/'freeze/code'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    mats=list((OUT/'cases').rglob('*.json'))
    write_once(OUT/'freeze/config.json',{'code_hashes':{str(p.relative_to(ROOT)):byte_hash(p) for p in paths},
        'material_hashes':{str(p.relative_to(ROOT)):byte_hash(p) for p in mats},'case_order':list(CASES),
        'tracks':['engine-only','reviewed-reconstruction'],'new_model_calls':0,'legal_approval':False,
        'evaluation':'Local engineering and explicitly reviewed reconstruction assumptions, not new model accuracy. Preserve unsupported evaluation separately from unknown facts. Compare every old request, including uncompleted ones.',
        'stop':'One uniform cached replay; no model retry, new sources, training or publication.'})

def run():
    cfg=read_json(OUT/'freeze/config.json')
    for path,h in {**cfg['code_hashes'],**cfg['material_hashes']}.items():
        if byte_hash(ROOT/path)!=h:raise ValueError('FROZEN_CHANGED:'+path)
    summary=[]
    for cid in CASES:
        old=read_json(OLD/'cases'/cid/'runs/S1/check.json')
        for track in cfg['tracks']:
            dst=OUT/'cases'/cid/track
            cmd=[sys.executable,str(ROOT/'scripts/check_realcase_certificate_v3.py'),str(dst/'certificate.json'),'--manifest',str(dst/'manifest.json')]
            started=datetime.datetime.now(datetime.timezone.utc)
            proc=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
            (dst/'stdout.txt').write_text(proc.stdout);(dst/'stderr.txt').write_text(proc.stderr)
            write_once(dst/'invocation.json',{'argv':cmd,'exit_code':proc.returncode,'seconds':(datetime.datetime.now(datetime.timezone.utc)-started).total_seconds(),'independent_process':True})
            result=json.loads(proc.stdout);write_once(dst/'check.json',result)
            lines=['# Conditional reconstruction', '', 'Model-assisted source review; no qualified legal approval. Court assessment assumptions are not independently recomputed legal conclusions.', '']
            snap=read_json(dst/'snapshot.json')
            for q in result['requests']:
                lines += [f"## {q['id']}: {q['text']}",f"Status: {q['draft_status']}; answer: {q['answer']}",
                    'Semantic assumptions: '+json.dumps(q.get('semantic_assumptions',[])),
                    'Uncomputed operations: '+json.dumps(q.get('uncomputed',[])),
                    'Errors: '+json.dumps(q['errors']), 'Gaps: '+json.dumps(q.get('gaps',[]))]
                for ref in q.get('source_refs',[]):lines.append(f"[{ref}] {snap['sources'][ref]['text']}")
                oq=next(x for x in old['requests'] if x['id']==q['id'])
                summary.append({'case':cid,'track':track,'request':q['id'],'old_status':oq['draft_status'],
                    'new_status':q['draft_status'],'answer':q['answer'],'assumptions':q.get('semantic_assumptions',[]),
                    'errors':q['errors'],'gaps':q.get('gaps',[]),'not_model_performance':True})
            lines+=['## Preserved opposition and unresolved records']
            for p in snap['premises'].values():
                lines.append(f"{p['id']} [{snap['reviews']['premises'][p['id']]['decision']}] {p['state']} {p['statement_status']}: {p['text']} Limitations: {json.dumps(p['limitations'])}")
            (dst/'explanation.md').write_text('\n\n'.join(lines)+'\n')
    write_once(OUT/'comparison.json',summary)

if __name__=='__main__':
    {'prepare':prepare,'run':run}[sys.argv[1]]()
