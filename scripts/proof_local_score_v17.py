#!/usr/bin/env python3
"""Post-batch scoring and prediction/answer trace under the frozen contract.
Never supplies reference content to a tested method. No model calls.
"""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.proof_local_comparison_v17 import OUT,DEV,CONDITIONS,read,save,fixture,assert_frozen
from legal_bench.proof_carrying.local_evaluation_v17 import semantic_metrics,equal_dispute_summary,local_metrics,LABELS

def main():
    protocol=assert_frozen();by_method={m:[] for m in CONDITIONS};traces=[];issues=[]
    for cid in DEV:
        mapping=protocol['evaluation']['blind_evaluation']['order'][cid]
        ref=read(OUT/'private/frozen-references'/cid/'checklist.json')
        reviewfile=OUT/'web/evaluation'/cid/'parsed.json'
        if reviewfile.exists():
            review=read(reviewfile);scored=semantic_metrics(review,ref,expected_ids=mapping)
            if review.get('reference_disagreements'):issues.append({'case_id':cid,'reference_disagreements':review['reference_disagreements'],'uniform_source_review_required':True,'original_review_preserved':str(reviewfile)})
        else:scored={};issues.append({'case_id':cid,'reason':'SEMANTIC_REVIEW_MISSING','answer_failure_not_inferred':True})
        for neutral,condition in mapping.items():
            runfile=OUT/'local'/cid/condition/'run.json'
            if not runfile.exists():status='NOT_STARTED'
            else:status=read(runfile)['run_status']
            value=scored.get(neutral,{'key_coverage':None,'unsupported_rate':None,'major_error_case':None,'overall':None})
            by_method[condition].append({**value,'case_id':cid,'request_id':'Q1','dispute_id':fixture(cid)['case']['dispute_id'],
                'technical_status':status,'neutral_id':neutral,'semantic_review_present':neutral in scored})
    rows=read(OUT/'freeze/training-rows.json');devrows=[r for r in rows if r['split']=='DEV'];keys={r['key'] for r in devrows}
    local=[]
    for name in ('Flat','CrossEncoder','RGCN'):
        predfile=OUT/'training'/name/'all-candidate-predictions.json';condition={'Flat':'E','CrossEncoder':'F','RGCN':'G'}[name]
        if not predfile.exists():
            local.append({'method':name,'status':'FAILED_OR_INCOMPLETE','metrics':None});continue
        preds=read(predfile);local.append({'method':name,'metrics':local_metrics([r for r in preds if r['key'] in keys],devrows),
            'all_candidate_predictions':len(preds),'labeled_DEV_predictions':sum(r['key'] in keys for r in preds)})
        for pr in preds:
            cid,connid=pr['key'].split('::');proposal=read(OUT/'local'/cid/'P/parsed.json');conn=proposal['connections'][int(connid[1:])-1]
            label=LABELS[max(range(3),key=lambda i:pr['probabilities'][i])]
            finalfile=OUT/'local'/cid/condition/'formal-answer.json';answer=read(finalfile)['answer'] if finalfile.exists() else None
            handling=[r for r in answer.get('connection_handling',[]) if r['connection_id']==connid] if answer else []
            traces.append({'case_id':cid,'connection_id':connid,'method':name,'P_label':conn['self_assessment'],
                'review_label':label,'changed':label!=conn['self_assessment'],'model_probabilities':pr['probabilities'],
                'source_evidence_original_unchanged':True,'program_structural_audit_unchanged':True,
                'final_material_consequence':'ADDITIONAL_FALLIBLE_CONNECTION_REVIEW; NO_SEMANTIC_APPROVAL_OR_SOURCE_DELETION',
                'final_reported_handling':handling,'final_effect':'REQUIRES_CONCENTRATED_SOURCE_REVIEW_NOT_INFERRED_FROM_LABEL_OR_ADOPTION',
                'common_interface_fix_attributed_to_model':False})
    summaries={method:equal_dispute_summary(v,len(DEV)) for method,v in by_method.items()}
    save(OUT/'full-answer-metrics.json',{'by_method':summaries,'per_request':by_method,
        'reference_status':'MODEL_GENERATED_SOURCE_REVIEWED_NOT_HUMAN_GOLD','no_composite_score':True,
        'limited_reference_coverage':True,'decisive_review_pending':bool(issues)})
    save(OUT/'local-classification-metrics.json',local)
    save(OUT/'prediction-to-answer-trace.json',traces)
    save(OUT/'evaluation-disagreements.json',issues)
    costs=[]
    for cid in protocol['TRAIN']+list(DEV):
        for path in (OUT/'local'/cid).glob('*/run.json'):
            r=read(path);costs.append({'case_id':cid,'role':path.parent.name,'status':r['run_status'],
                'input_tokens':r.get('prompt_tokens_actual',r.get('prompt_tokens')),'output_tokens':r.get('output_tokens'),
                'elapsed_seconds':r.get('elapsed_seconds'),'peak_memory_gb':r.get('peak_mlx_memory_gb'),'technical_answer_null':r['run_status']!='OK'})
    save(OUT/'cost.json',{'local_runs':costs,'local_planned_slots':110,
        'local_completed':sum(r['status']=='OK' for r in costs),'web_observable_tokens':'UNAVAILABLE_NOT_ESTIMATED',
        'train_fits':{name:read(OUT/'training'/name/'run.json') if (OUT/'training'/name/'run.json').exists() else read(OUT/'training'/name/'failure.json') if (OUT/'training'/name/'failure.json').exists() else {'status':'NOT_STARTED'} for name in ('Flat','CrossEncoder','RGCN')}})
    print(json.dumps(summaries,indent=2))

if __name__=='__main__':main()
