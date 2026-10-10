"""Bounded entry-level mutation audit; never edits proposals or frozen snapshots.

Real-record variants exercise a narrow accepted Rame premise chain. Separately
labelled synthetic fixtures cover operations the actual legal registry does not
use (time comparison and ANY/exception). They are not legal-error observations.
"""
import argparse, copy, json, os, subprocess, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.contracts import read_json,write_once,byte_hash,content_hash
from legal_bench.proof_carrying.realcase_engine import propose
from tests.test_proof_realcase_v2 import fixture
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/proof-carrying-realcase-v2'
CHECKER=ROOT/'scripts/check_realcase_certificate_v2_1.py'

def repin(s):
    for category in ('rules','premises'):
        for k,v in s[category].items():
            s['reviews'][category][k]={'subject_hash':content_hash(v),'decision':'ACCEPT_RESEARCH',
              'actor':'MUTATION_FIXTURE_ONLY_NOT_SOURCE_REVIEW','qualified_legal_approval':False}
    s['scope_reviews']={k:{'subject_hash':content_hash(v),'jurisdiction_compatible':True,
        'stage_compatible':True,'basis':'Fixture only'} for k,v in s['rules'].items()}

def main():
    audit=OUT/'mutation-audit';audit.mkdir(exist_ok=False)
    source=read_json(OUT/'cases/789051/snapshots/S1.json')
    b=source['premises']['F1']['bindings']
    d={'steps':[{'id':'T1','rule_ref':'R1@1','bindings':b,'time_scope':None,
         'inputs':[{'slot':'possession_established','kind':'PREMISE','id':'F1'},
                   {'slot':'ownership_not_proved','kind':'PREMISE','id':'F2'}],
         'proposed_state':'TRUE','explanation':'Narrow entry-level mutation seed; not a new model answer.'}],
       'requests':[{'id':'Q1','step_id':'T1','predicate':source['rules']['R1@1']['conclusion_predicate'],
         'text':source['rules']['R1@1']['conclusion_text'],'proposed_state':'TRUE'}],
       'counterarguments':['Title remains unproved, not adjudged false.'],
       'gaps':['Qualified approval pending; synthetic changes do not count as natural errors.']}
    specs=[]
    def add(name,s,p,expect,provenance='CONSTRUCTED_VARIANT_ON_REAL_RECORDS',current=None):
        specs.append((name,copy.deepcopy(s),copy.deepcopy(p),expect,provenance,current))
    add('narrow_valid',source,d,'TRUE')
    x=copy.deepcopy(d);x['steps'][0]['bindings']=[{'role':'subject','entity':'E2'},{'role':'property','entity':'E3'}]
    add('wrong_subject',source,x,'INVALID')
    x=copy.deepcopy(d);x['steps'][0]['rule_ref']='R1@999';add('wrong_rule_version',source,x,'INVALID')
    x=copy.deepcopy(d);x['requests'][0]['predicate']='PLAINTIFF_IS_OWNER';add('conclusion_upgrade',source,x,'INVALID')
    x=copy.deepcopy(d);x['steps'][0]['inputs'][0]={'slot':'possession_established','kind':'STEP','id':'T1'};add('self_cycle',source,x,'INVALID')
    x=copy.deepcopy(d);x['steps'][0]['inputs'][0]['id']='MISSING';x['steps'][0]['proposed_state']='UNKNOWN';x['requests'][0]['proposed_state']='UNKNOWN';add('missing_premise',source,x,'UNKNOWN')
    s=copy.deepcopy(source);s['premises']['F1']['statement_status']='PARTY_CLAIM';repin(s);add('statement_upgrade',s,d,'INVALID')
    s=copy.deepcopy(source);s['premises']['F1']['refs']=['IK-789051:L114'];s['premises']['F1']['quote']=source['sources']['IK-789051:L114']['text'];s['premises']['F1']['statement_status']='TARGET_DISPOSITION';repin(s);add('disposition_as_fact',s,d,'INVALID')
    s=copy.deepcopy(source);s['premises']['F1']['refs']+=['IK-789051:L66'];repin(s);add('valid_same_source_expansion',s,d,'TRUE')
    s=copy.deepcopy(source);s['premises']['UNUSED']=dict(s['premises']['F1'],id='UNUSED',text='Synthetic unused copy, not another independent witness.');repin(s);add('irrelevant_record',s,d,'TRUE')
    add('historical_reopen',source,d,'TRUE',current=source['snapshot_id'])
    add('stale_as_current',source,d,'TECHNICAL_FAILURE',current='789051-S2')
    # Synthetic time and disjunction; no new actual legal premise or rule asserted.
    s,p=fixture();repin(s);add('synthetic_cross_step',s,p,'TRUE','SYNTHETIC_REGRESSION')
    x=copy.deepcopy(p);x['steps'][0]['time_scope']='Tuesday';add('synthetic_wrong_time',s,x,'INVALID','SYNTHETIC_REGRESSION')
    s2=copy.deepcopy(s);r=s2['rules']['R1@1'];r['operator']='ANY';r['slots'].append(dict(r['slots'][0],name='independent_missing'));repin(s2)
    add('synthetic_independent_or',s2,p,'TRUE','SYNTHETIC_REGRESSION')
    r['slots'].append(dict(r['slots'][0],name='exception',predicate='EXCEPTION'));r['exception_slots']=['exception'];repin(s2)
    x=copy.deepcopy(p)
    for t in x['steps']:t['proposed_state']='UNKNOWN'
    x['requests'][0]['proposed_state']='UNKNOWN';add('synthetic_exception_missing',s2,x,'UNKNOWN','SYNTHETIC_REGRESSION')
    add('synthetic_omitted_exception_claim_true',s2,p,'INVALID','SYNTHETIC_REGRESSION')
    rows=[]
    for name,s,p,expect,provenance,current in specs:
        folder=audit/name;folder.mkdir()
        # Source bytes and scope remain independently checked; only path packaging changes.
        for doc in s['documents']:
            original=(OUT/'cases/789051'/doc['path']).resolve()
            doc['path']=os.path.relpath(original,folder)
        write_once(folder/'snapshot.json',s)
        write_once(folder/'manifest.json',{'snapshots':{s['snapshot_id']:{'path':'snapshot.json','sha256':byte_hash(folder/'snapshot.json')}}})
        write_once(folder/'certificate.json',propose(s,p))
        cmd=[sys.executable,str(CHECKER),str(folder/'certificate.json'),'--manifest',str(folder/'manifest.json')]
        if current:cmd+=['--current',current]
        run=subprocess.run(cmd,text=True,capture_output=True,cwd=ROOT)
        (folder/'stdout.txt').write_text(run.stdout);(folder/'stderr.txt').write_text(run.stderr)
        write_once(folder/'invocation.json',{'argv':cmd,'exit_code':run.returncode,'checker_sha256':byte_hash(CHECKER)})
        result=json.loads(run.stdout);write_once(folder/'result.json',result)
        if result.get('answer','no') is None and result.get('status')!='COMPLETED':actual='TECHNICAL_FAILURE'
        else:
            q=result['requests'][0];actual='INVALID' if q['draft_status']=='INVALID' else q['answer']
        rows.append({'name':name,'category':provenance,'expected':expect,'actual':actual,'pass':actual==expect,
          'path':str(folder.relative_to(OUT)),'legal_approval':False})
    write_once(audit/'summary.json',{'cases':rows,'passed':sum(r['pass'] for r in rows),'count':len(rows),
      'natural_model_errors':0,'claims':'Engineering behavior only. Missing approval is not an invalid-derivation detection.'})
    print(json.dumps({'passed':sum(r['pass'] for r in rows),'count':len(rows)}))
if __name__=='__main__':main()
