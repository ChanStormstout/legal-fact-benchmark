#!/usr/bin/env python3
"""Deterministic wiring control, not a trained-model result or new condition."""
import hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.proof_pipeline_diagnostic_v19_8 import OUT,frozen
from scripts import proof_pipeline_contract_v19_8 as entry
from legal_bench.proof_carrying import local_pipeline_v19_8 as pipe,local_checker_v19_8 as checker
from legal_bench.proof_carrying import final_delivery_v19_8_1 as delivery
from legal_bench.proof_carrying.rule_contracts_v19_7 import digest

def main():
    protocol=frozen();entry.save(OUT/'freeze/wiring-acceptance-01.json',{'code_hash':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'control':'Replace all use predictions with UNSUPPORTED only to test propagation; no reference, no model and no score.',
        'processing_version':pipe.VERSION,'new_model_calls':0})
    rows=[]
    for t in protocol['tasks']:
        f,part=entry.context({'case_id':t['case_id'],'part_contract':t['part_contract']});saved=entry.read(OUT/'replay'/t['case_id']/'entry.json')
        p=saved['canonical_P'];changed={f'K{i:03d}':'UNSUPPORTED' for i in range(1,len(p['uses'])+1)}
        after=pipe.apply_connection_decisions(f['case'],f['rules'],p,changed)
        checked=checker.check(f['case'],f['rules'],p,changed,after)
        assert checked['status']=='OK',checked
        prediction={'rows':[{'key':k,'probabilities':[0.,1.,0.]} for k in changed],
            'manifest':{'version':pipe.VERSION,'class_order':list(pipe.LABELS),'input_sha256':digest(saved['learner_inputs'])}}
        final=delivery.task(f['case'],f['rules'],saved,'E',part,prediction,f['full_rules'])
        changes=[]
        for a,b in zip(saved['conditional_audit']['premise_judgments'],after['premise_judgments']):
            if a['conditional_state']!=b['conditional_state'] or a['available_uses']!=b['available_uses']:
                changes.append({'premise':a['premise'],'original_state':a['conditional_state'],'control_state':b['conditional_state'],
                    'original_available_uses':a['available_uses'],'control_available_uses':b['available_uses'],
                    'original_model_state_unchanged':a['model_state']==b['model_state'],'basis_unchanged':a['basis']==b['basis']})
        rows.append({'case_id':t['case_id'],'control_only_not_learning_improvement':True,'checker_status':checked['status'],
            'original_use_and_judgment_text_retained':True,'prediction_to_use_to_component_changes':changes,
            'final_material_assembled_with_prediction_input_hash':final['input_sha256'],'final_answer_generated':False,
            'whole_rule_conclusions_remain_unknown':all(r['conditional_result']=='UNKNOWN' for r in after['conditional_rules']),
            'reasons':'Missing cross-slot identities and/or OPEN_TEXT remain, not silently repaired by usefulness predictions.'})
    entry.save(OUT/'engineering/prediction-wiring.json',{'rows':rows,'purpose':'Verify predicted use labels can change acceptance/coverage and final intermediate material, without replacing model whole premise judgment.',
        'not_model_performance':True,'new_model_calls':0})
if __name__=='__main__':main()
