"""Fixed cached evaluation. Never calls a model, changes a rule or fixes a result."""
import copy,csv,json,subprocess,sys,shutil,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.proof_carrying.contracts import read_json,write_once,byte_hash,content_hash
from legal_bench.proof_carrying.realcase_engine import propose
from legal_bench.proof_carrying.reconstruction_view_v4 import view,ACCEPTED

ROOT=Path(__file__).resolve().parents[1]
V2=ROOT/'outputs/proof-carrying-realcase-v2'
V3=ROOT/'outputs/proof-carrying-local-repair-v3'
OUT=ROOT/'outputs/proof-carrying-checker-evaluation-v4'
CHECKER=ROOT/'scripts/check_realcase_certificate_v3.py'
CASES=('789051','1418721','1841885')
# Zero-based existing independent-reference rows. They are evaluation-only.
MAP={'789051':{'Q1':[5,7,11,17],'Q2':[9,15,16],'Q3':[18,21],'Q4':[19,20]},
     '1418721':{'Q1':[10,11,12,13,14,16],'Q2':[22,25],'Q3':[24,25,26,27],'Q4':[16,25,27]},
     '1841885':{'Q1':[14,17,18],'Q2':[15,16],'Q3':[11,13,17,19],
               'Q4':[2,3,22],'Q5':[19,21,22,23]}}

def bundle(dst,snap,proposal,meta):
    dst.mkdir(parents=True,exist_ok=False)
    write_once(dst/'snapshot.json',snap);write_once(dst/'certificate.json',propose(snap,proposal))
    write_once(dst/'manifest.json',{'snapshots':{snap['snapshot_id']:{'path':'snapshot.json','sha256':byte_hash(dst/'snapshot.json')}}})
    write_once(dst/'metadata.json',meta)

def prepare():
    assert (OUT/'registration.json').exists()
    refs={}
    for cid in CASES:
        snap=read_json(V3/'cases'/cid/'reviewed-reconstruction/snapshot.json')
        prop=read_json(V2/'runs'/cid/'derivation/parsed.json')
        ref=read_json(V2/'runs'/cid/'reference/parsed.json')
        refs[cid]={}
        for q in prop['requests']:
            selected=[{'reference_index':i,**ref['judgments'][i]} for i in MAP[cid][q['id']]]
            refs[cid][q['id']]={'reference_path':str((V2/'runs'/cid/'reference/parsed.json').relative_to(ROOT)),
                'reference_hash':byte_hash(V2/'runs'/cid/'reference/parsed.json'),'judgments':selected,
                'claim_review':'SUPPORTED_WITH_STATED_LIMITS' if not(cid=='1841885' and q['id']=='Q5') else 'QUALIFIED_CONCLUSION_SUPPORTED_PROOF_TRANSLATION_OVERBROAD',
                'proof_review':'SOURCE_REVIEWED_CONDITIONAL_RECONSTRUCTION' if not(cid=='1841885' and q['id']=='Q5') else 'R6_V1_SUSPENDED_AND_F11_AMBIGUOUS',
                'legal_approval':False,'not_blind':True}
        bundle(OUT/'natural'/cid,snap,prop,{'kind':'NATURAL_CACHED_PROPOSAL','same_snapshot_before_after':True,
            'original_proposal_hash':content_hash(prop),'v3_policy_hash':content_hash(snap),
            'extra_semantic_review_is_not_checker_discovery':True})
    write_once(OUT/'reference-map.json',refs)
    snap=read_json(OUT/'natural/789051/snapshot.json');raw=read_json(OUT/'natural/789051/certificate.json')['proposal']
    variants=[]
    def add(name,p,target,wanted,kind,note,current=None):
        meta={'kind':kind,'name':name,'target':target,'expected_conclusion_handling':wanted,'reason':note,'current':current}
        bundle(OUT/'controlled'/name,snap,p,meta);variants.append(meta)
    p=copy.deepcopy(raw);p['steps'][0]['bindings'][0]['entity']='E2'
    add('wrong_subject',p,'Q1','WITHHOLD','INVALID_TYPED_PROOF','Change the subject without changing the evidence.')
    p=copy.deepcopy(raw);p['steps'][2]['rule_ref']='R3@999'
    add('wrong_rule_version',p,'Q1','WITHHOLD','INVALID_TYPED_PROOF','Unavailable rule version.')
    p=copy.deepcopy(raw);p['requests'][0]['predicate']='PLAINTIFF_OWNS_SUIT_LAND'
    add('typed_ownership_upgrade',p,'Q1','WITHHOLD','INVALID_TYPED_PROOF','Possessory protection does not establish ownership.')
    p=copy.deepcopy(raw);p['requests'][0]['text']='The plaintiff owns the suit land and the defendant has no remaining title rights.'
    add('prose_ownership_upgrade',p,'Q1','WITHHOLD_FALSE_PROSE','UNSUPPORTED_NATURAL_LANGUAGE',
        'Keep the predicate but replace the displayed request prose with an unsupported ownership conclusion. Distinguish typed checking from prose checking.')
    p=copy.deepcopy(raw);p['steps'][1]['inputs']=list(reversed(p['steps'][1]['inputs']))
    add('equivalent_input_order',p,'Q1','RETAIN','VALID_SEMANTIC_INVARIANT','Named-slot order does not change bindings, predicates or rule application. Exact reviewed hash may still require re-review.')
    p=copy.deepcopy(raw);p['steps'][1]['explanation']+=' This sentence describes the same existing step without adding a premise.'
    add('equivalent_explanatory_note',p,'Q1','RETAIN','VALID_SEMANTIC_INVARIANT','Only non-executable explanation changes; no fact, slot, binding or conclusion changes.')
    p=copy.deepcopy(raw);unused=copy.deepcopy(p['steps'][0]);unused['id']='UNUSED';p['steps'].append(unused)
    add('unreferenced_valid_step',p,'Q1','RETAIN','VALID_SEMANTIC_INVARIANT','An unreferenced correct step is not a dependency.')
    add('historical_snapshot_reopen',copy.deepcopy(raw),'Q1','RETAIN','VALID_VERSION_OPERATION','Explicitly reopen the same trusted historical snapshot.',snap['snapshot_id'])
    add('wrong_current_version',copy.deepcopy(raw),'Q1','WITHHOLD','INVALID_VERSION_OPERATION','An old snapshot cannot claim to be an unavailable current snapshot.','UNAVAILABLE-CURRENT')
    write_once(OUT/'protocol.json',{'task':'SAME_CACHED_PROPOSAL_BEFORE_AFTER','cases':list(CASES),
        'natural_requests':13,'controlled':variants,'new_model_calls':0,'human_gold':False,
        'acceptance_policy':'V3 reviewed reconstruction policy is identical before and after; no semantic correction is credited to checker.',
        'baseline':'Unchecked original model assertions, including their caveats, not a new model condition.',
        'separate_layers':['claim source support','proof completeness','review-policy enforcement','typed checking','unverified free-text display'],
        'outcome_dependent_repairs':False,'freeze_scope':'Checker and policy unchanged. Display adapter is frozen and applied uniformly, never repairs submitted prose.',
        'stops':'One cached batch and one source review; no sources/models/training or parameters added. Later defects recorded, not repaired and rerun in this batch.'})
    code=[CHECKER,ROOT/'legal_bench/proof_carrying/realcase_checker_v3.py',ROOT/'legal_bench/proof_carrying/realcase_grounding_v3.py',
        ROOT/'legal_bench/proof_carrying/realcase_engine.py',ROOT/'legal_bench/proof_carrying/realcase_contracts.py',
        ROOT/'legal_bench/proof_carrying/contracts.py',ROOT/'legal_bench/proof_carrying/reconstruction_view_v4.py',
        ROOT/'scripts/proof_checker_evaluation_v4.py',ROOT/'tests/test_reconstruction_view_v4.py']
    materials=[p for d in ['natural','controlled'] for p in (OUT/d).rglob('*.json')]+[OUT/'protocol.json',OUT/'reference-map.json']
    for p in code:
        dest=OUT/'freeze/code'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    write_once(OUT/'freeze/config.json',{'code_hashes':{str(p.relative_to(ROOT)):byte_hash(p) for p in code},
        'material_hashes':{str(p.relative_to(ROOT)):byte_hash(p) for p in materials},'stop_after_one_batch':True})

def run():
    cfg=read_json(OUT/'freeze/config.json')
    for p,h in {**cfg['code_hashes'],**cfg['material_hashes']}.items():
        if byte_hash(ROOT/p)!=h:raise ValueError('FROZEN_CHANGE:'+p)
    dirs=[OUT/'natural'/cid for cid in CASES]+[OUT/'controlled'/v['name'] for v in read_json(OUT/'protocol.json')['controlled']]
    rows=[]
    for dst in dirs:
        meta=read_json(dst/'metadata.json');cert=read_json(dst/'certificate.json');snap=read_json(dst/'snapshot.json')
        cmd=[sys.executable,str(CHECKER),str(dst/'certificate.json'),'--manifest',str(dst/'manifest.json')]
        if meta.get('current'):cmd+=['--current',meta['current']]
        tick=time.monotonic();p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True)
        (dst/'stdout.txt').write_text(p.stdout);(dst/'stderr.txt').write_text(p.stderr)
        write_once(dst/'invocation.json',{'argv':cmd,'exit_code':p.returncode,'seconds':time.monotonic()-tick})
        result=json.loads(p.stdout);write_once(dst/'check.json',result)
        display=view(snap,cert,result) if result['status']=='COMPLETED' else {'requests':[],'technical_failure':result}
        write_once(dst/'display.json',display)
        original={q['id']:q for q in cert['proposal']['requests']}
        for q in result.get('requests',[]):
            rows.append({'case':snap['case_id'],'variant':dst.name,'kind':meta['kind'],'request':q['id'],
                'before_model_state':original[q['id']]['proposed_state'],'after_state':q['answer'],'after_status':q['draft_status'],
                'accepted_conditional_trace':q['draft_status'] in ACCEPTED,'errors':q['errors'],'gaps':q.get('gaps',[]),
                'semantic_assumptions':q.get('semantic_assumptions',[]),'source_refs':q.get('source_refs',[]),
                'submitted_prose_checked':False})
    write_once(OUT/'all-results.json',rows)
    with (OUT/'all-results.csv').open('x') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
        w.writerows({k:json.dumps(v) if isinstance(v,list) else v for k,v in r.items()} for r in rows)

if __name__=='__main__':{'prepare':prepare,'run':run}[sys.argv[1]]()
