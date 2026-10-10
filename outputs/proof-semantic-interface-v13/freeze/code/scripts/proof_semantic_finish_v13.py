#!/usr/bin/env python3
"""Deterministic V13 delivery, explicit closed gates, no model initialization."""
import sys,json,hashlib,collections,datetime,subprocess,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.proof_semantic_run_v13 import save,run
from scripts.proof_semantic_apply_v13 import apply
from legal_bench.proof_carrying.semantic_interface_v13 import adapt
from legal_bench.proof_carrying.semantic_data_v12 import prior
ROOT=Path('outputs/proof-semantic-interface-v13')
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    rows=read(ROOT/'final-audit-03/final-supervision.json');audit=read(ROOT/'final-audit-03/data-task-audit.json');train=[r for r in rows if r['split']=='TRAIN' and r['valid'] and r['label'] in ('USABLE','UNUSABLE','UNRESOLVED')]
    results=[];all_predictions=[];details=[]
    for path in sorted((ROOT/'final-model-inputs-03').glob('*/model-information-fullcontext.json')):
        cid=path.parent.name;case=read(Path('outputs/proof-semantic-search-v12/cohort')/cid/'case.json')
        assert case['split'] in ('TRAIN','DEV')
        if case['split']!='DEV':continue
        proposal_path=ROOT/'final-audit-03/dev-restored'/cid/'proposal.json'
        if not proposal_path.exists():proposal_path=ROOT/'inputs-v13-02'/cid/'proposal.json'
        p=read(proposal_path);snapshot,candidates,requests=adapt(case,p);ps={pr['id']:pr for rule in p['rules'] for pr in rule['premises']};queries=[{'id':u['id'],'premise_family':ps[u['rule_premise']].get('family','UNSPECIFIED')} for u in p['uses']];predictions=[{'key':cid+'::'+z['id'],**z} for z in prior(train,queries)];all_predictions+=predictions
        # Baseline inference includes unlabelled candidates. Reference is not
        # consulted for objects, rules, truth or candidate selection.
        d=ROOT/'baselines-final'/cid;save(d/'prior-predictions.json',predictions);run(apply(snapshot,predictions),candidates,requests,d/'TRAIN_LABEL_PRIOR')
        raw_path=ROOT/'final-audit-03/dev-restored'/cid/'raw-P/checked.json'
        if not raw_path.exists():raw_path=ROOT/'final-replays-02'/cid/'raw-P/checked.json'
        raw=read(raw_path);after=read(d/'TRAIN_LABEL_PRIOR/checked.json')
        results.append({'case_id':cid,'requests':len(raw['requests']),'RAW_P':dict(collections.Counter(x['answer'] for x in raw['requests'])),'TRAIN_LABEL_PRIOR':dict(collections.Counter(x['answer'] for x in after['requests'])),'changed_requests':[x['id'] for x,y in zip(raw['requests'],after['requests']) if x['answer']!=y['answer']]})
        search=read(raw_path.parent/'search.json');steps={x['id']:x for x in search['steps']};rootids={x['step'] for req in raw['requests'] for x in req['alternatives']}
        for sid in sorted(rootids):
            st=steps[sid];check=raw['steps'][sid];r=snapshot['rules'][st['rule_ref']]
            details.append({'case_id':cid,'step_id':sid,'rule_ref':st['rule_ref'],'operator':r['operator'],'state':check['state'],'errors':check['errors'],'pending':check['pending'],'bindings':st['bindings'],'premises':[{'slot':x['slot'],'input_kind':x['kind'],'raw_use_id':snapshot['model_uses'].get(st['candidate_id']+'::'+x['slot'],{}).get('raw_use_id'),'P_use_label':snapshot['model_uses'].get(st['candidate_id']+'::'+x['slot'],{}).get('label'),'P_whole_premise_state':snapshot['model_uses'].get(st['candidate_id']+'::'+x['slot'],{}).get('premise_state'),'unmapped_roles':snapshot['contracts'][st['rule_ref']].get('unmapped_roles',{}).get(x['slot'],{})} for x in st['inputs']]})
    save(ROOT/'baseline-chain-summary.json',results);save(ROOT/'root-path-diagnostic.json',details)
    save(ROOT/'baselines-final/all-DEV-prior-predictions.json',all_predictions)
    initial=read(ROOT/'startup.json');integrity=[{'path':p,'before':digest,'after':sha(p),'unchanged':sha(p)==digest} for p,digest in initial['source_hashes'].items()];assert all(x['unchanged'] for x in integrity);save(ROOT/'historical-code-integrity-final.json',integrity)
    # Strictly preserve every original TRAIN row, including masked references.
    old=read(Path('outputs/proof-semantic-search-v12/continuation-02/supervision-35/rows.json'));new={r['key']:r for r in rows};assert all(all(new[r['key']][k]==v for k,v in r.items()) for r in old if r['split']=='TRAIN')
    save(ROOT/'engineering-acceptance.json',{'status':'PASS_BOUNDED_CONTRACT_NOT_LEGAL_VALIDATION','actual_entry_tests':'engineering-tests-final-entry-05.txt','tests':7,'old_code_hashes_preserved':len(integrity),'TRAIN_original_fields_unchanged':True,'actual_numerical_input_receipt':'model-input-acceptance.json','actual_CE_tokenizer_receipt':'encoding-final-02/CE-tokenizer-receipt.json','V13_fits':0,'test_sealed_read':False,'limits':['Ambiguous role descriptions remain unmapped locally.','Non-finite/free-text relation kinds remain preserved but untyped.','No neural forward or fit is claimed by numerical input preparation.']})
    save(ROOT/'training-decision.json',{'training_authorized_by_frozen_gates':False,'status':'NOT_STARTED_GATES_CLOSED','answer':None,'actual_new_fits':0,'data_gate':audit['gates'],'reasons':['NO_REAL_CLOSED_OR_USE_SENSITIVE_ROOT_PATH','LABEL_PRODUCTION_AND_SCOPE_HOMOGENEITY_NOT_CERTIFIED','DEV_AUTHORIZATION_AND_STANDING_EACH_ONE_EVALUABLE_DISPUTE'],'methods':{k:{'status':'NOT_STARTED','answer':None,'weights':None} for k in ('Flat','RGCN','CrossEncoder')},'do_not_reuse_V12_weights_as_V13':True,'baseline_chain_summary':'baseline-chain-summary.json','no_parameter_search':True})
    freeze=ROOT/'freeze';code=sorted(set(list(Path('legal_bench/proof_carrying').glob('*v13.py'))+list(Path('scripts').glob('*v13.py'))+[Path('tests/test_proof_semantic_v13.py')]))
    hashes={}
    for p in code:
        dest=freeze/'code'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes());hashes[str(p)]=sha(p)
    material=[]
    for path in sorted((ROOT/'final-model-inputs-03').glob('*/model-information-fullcontext.json')):
        cid=path.parent.name;c=Path('outputs/proof-semantic-search-v12/cohort')/cid/'case.json';material.append({'case_id':cid,'split':read(c)['split'],'case_file_sha256':sha(c),'actual_input_sha256':sha(path),'input_path':str(path)})
    save(freeze/'materials.json',material)
    save(freeze/'config.json',{'version':'V13-final-interface-1','HEAD':initial['head'],'source_hashes':hashes,'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'task':'JUDGMENT_REASONING_RECONSTRUCTION_USE_REVIEW','training_authorized_by_frozen_gates':False,'gate_policy_sha256':sha(ROOT/'final-gate-policy.json'),'final_data_audit':'final-audit-03/data-task-audit.json','final_labels_sha256':sha(ROOT/'final-audit-03/final-supervision.json'),'input_directory':'final-model-inputs-03','encoding_directory':'encoding-final-03','learner_bundle':'learner-bundle-final','raw_P_and_explanations_visible':True,'prediction_changes_only_use_label':True,'generations':13,'generations_max':21,'retries':0,'TEST_SEALED_read':False,'TRAIN_reannotated':False,'fits':0,'original_training_config':'training-settings-original.json','stopping_reason':'Finite DEV queue completed; failed review null; downstream gate not satisfied. No next iteration.'})
    print(json.dumps({'completed':True,'V13_new_fits':0,'DEV_evaluable':audit['DEV_evaluable_disputes'],'DEV_input_pool':len(results),'requests':sum(x['requests'] for x in results),'old_hashes_preserved':len(integrity)}))
if __name__=='__main__':main()
