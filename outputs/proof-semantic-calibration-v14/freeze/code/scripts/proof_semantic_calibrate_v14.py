#!/usr/bin/env python3
"""One frozen two-path local calibration batch; no training/model/web imports.

Reviews and overlays are supplied data. No reference is passed to raw-P replay.
Label flips are dependency controls, never learned performance.
"""
import sys
import copy
import json
import hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.proof_semantic_run_v13 import run as run_v13
from scripts.proof_semantic_run_v14 import run, save
from legal_bench.proof_carrying.semantic_calibration_v14 import apply_overlay
from legal_bench.proof_carrying.contracts import content_hash

ROOT = Path('outputs/proof-semantic-calibration-v14')
def read(p): return json.loads(Path(p).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    config = read(ROOT/'freeze/config.json')
    for p, digest in config['source_hashes'].items():
        if sha(p) != digest: raise ValueError('FROZEN_CODE_CHANGED:'+p)
    for p, digest in config['material_hashes'].items():
        if sha(p) != digest: raise ValueError('FROZEN_MATERIAL_CHANGED:'+p)
    if (ROOT/'path-comparison.json').exists():
        print('Existing completed batch preserved; no replay repeated.'); return
    rows = []
    for item in read(ROOT/'freeze/path-selection.json')['paths']:
        cid = item['case_id']; selected = item['selected']; d=ROOT/'inputs'/cid
        snapshot = read(d/'original-snapshot.json')
        candidates = [c for c in read(d/'original-candidates.json') if c['id']==selected['candidate_id']]
        requests = [q for q in read(d/'original-requests.json') if q['id']==selected['request']['id']]
        if len(candidates)!=1 or len(requests)!=1: raise ValueError('SELECTED_PATH_MISSING')
        dest=ROOT/'paths'/cid
        run_v13(snapshot,candidates,requests,dest/'A-original-P')
        raw=read(dest/'A-original-P/checked.json')
        # Same original P under the explicit V14 contract, still no calibration.
        rs=copy.deepcopy(snapshot);rs['input_track']='ORIGINAL_P_WITH_EXPLICIT_USE_CONTRACT_NO_CALIBRATION'
        contract_raw=run(rs,candidates,requests,{},dest/'A-contract-replay')
        overlay=read(d/'overlay.json'); policy=read(d/'policy.json')
        s,cs,changes=apply_overlay(snapshot,candidates,overlay)
        s['input_track']='SOURCE_CALIBRATED_NOT_AUTOMATIC_NOT_LEARNER_SCORE'
        save(dest/'calibration-ledger.json', changes)
        after=run(s,cs,requests,policy,dest/'B-source-calibrated')
        # Verify no proposal, use label, rule meaning, null quote or opposition
        # was silently rewritten by this overlay.
        preserved = {'raw_proposal': s['raw_proposal']==snapshot['raw_proposal'],
                     'premises':s['premises']==snapshot['premises'],
                     'model_uses':s['model_uses']==snapshot['model_uses'],
                     'relations':s.get('relations')==snapshot.get('relations'),
                     'operators':all(s['rules'][k]['operator']==v['operator'] for k,v in snapshot['rules'].items()),
                     'predicates_and_slots':all(s['rules'][k]['slots']==v['slots'] and s['rules'][k]['conclusion_predicate']==v['conclusion_predicate'] for k,v in snapshot['rules'].items())}
        if not all(preserved.values()): raise ValueError('ORIGINAL_SEMANTICS_REWRITTEN')
        save(dest/'preservation.json',preserved)
        steps={st['id']:st for st in read(dest/'B-source-calibrated/search.json')['steps']}
        chain=[]
        for key, result in after['external_receipt_checks'].items():
            sid,slot=key.split('::');receipt=overlay['premises'][slot]
            uid=receipt['raw_use_id']; original=next(u for u in snapshot['raw_proposal']['uses'] if u['id']==uid)
            chain.append({'slot':slot,'proposition':receipt['predicate'],
                'sources':result['witnesses'],'records':[snapshot['premises'][f] for f in receipt['original_evidence_ids']],
                'binding_checks':receipt['binding_witnesses'], 'candidate_bindings':steps[sid]['bindings'],
                'use_model_node':{'use_id':uid,'P_label':original['use_judgment'],'declared_function':overlay['use_declarations'][uid],'responsibility':'Eligibility for this function; not whole-premise truth.'},
                'P_premise_node':{'state':original.get('premise_state'),'basis':original.get('premise_judgment_basis',original.get('basis'))},
                'external_semantic_node':{'receipt':receipt,'accepted_state':result['state'],'semantic_independently_verified':False},
                'independent_engineering_check':{'errors':result['errors'],'pending':result['pending'],'what_was_checked':'Exact source addresses, reviewed receipt version, role/value consistency, declared component witnesses and concrete function, not their legal meaning.'},
                'rule_node':{'rule_ref':selected['rule_ref'],'operator':s['rules'][selected['rule_ref']]['operator'],'formula_source':s['rules'][selected['rule_ref']],'formal_legal_approval':False}})
        save(dest/'trace.json',{'request':requests[0],'nodes':chain,'composition_result':after['requests'][0],
              'opposition_retained':s.get('relations',[]),'all_original_records':list(s['premises']),
              'limits':'One existing local path; not a reconstruction or proof of every claim in the judgment.'})
        controls=[]
        for slot, receipt in overlay['premises'].items():
            changed=copy.deepcopy(s)
            k=selected['candidate_id']+'::'+slot
            changed['model_uses'][k]['label']='UNUSABLE'
            control=run(changed,cs,requests,policy,ROOT/'controls'/cid/receipt['raw_use_id'])
            controls.append({'use_id':receipt['raw_use_id'],'original_P_label':snapshot['model_uses'][k]['label'],
                             'control_label':'UNUSABLE','before':after['requests'][0]['answer'],'after':control['requests'][0]['answer'],
                             'is_real_model_gain':False,'conditional_on_source_calibrated_other_gates':True,
                             'retained_records':control['all_original_records'],'path':str(ROOT/'controls'/cid/receipt['raw_use_id'])})
        save(dest/'learning-placement.json',{'eligibility_controls':controls,
            'P_only_cannot_supply_source_calibration':True,'main_real_barriers':[z for st in raw['steps'].values() for z in st.get('pending',[])],
            'does_not_show_any_use_prediction_was_corrected':True})
        rows.append({'case_id':cid,'request':requests[0]['id'],'rule_ref':selected['rule_ref'],
                     'original_P_result':raw['requests'][0]['answer'],'explicit_contract_raw_result':contract_raw['requests'][0]['answer'],
                     'source_calibrated_result':after['requests'][0]['answer'],
                     'raw_pending':[z for st in raw['steps'].values() for z in st.get('pending',[])],
                     'calibrated_pending':[z for st in after['steps'].values() for z in st.get('pending',[])],
                     'calibrated_errors':[z for st in after['steps'].values() for z in st.get('errors',[])],
                     'formal_legal_approval':False,'learned_model_gain':False,'preserved':preserved,
                     'control_effects':controls, 'trace':str(dest/'trace.json'), 'ledger':str(dest/'calibration-ledger.json')})
    save(ROOT/'path-comparison.json',rows)
    print(json.dumps(rows,ensure_ascii=False))

if __name__=='__main__': main()
