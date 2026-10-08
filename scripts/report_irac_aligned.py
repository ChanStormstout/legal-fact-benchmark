#!/usr/bin/env python3
"""Summarize frozen predictions and web outputs without relabeling or retraining."""
import sys,json,csv,collections,statistics,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.irac_application.aligned_tasks import ROOT,put
from legal_bench.irac_application.aligned_train import metrics
from legal_bench.irac_application.aligned_graph import check_refs
LABELS=['SUPPORTED','REFUTED','UNRESOLVED']
def main():
    manifest=json.loads((ROOT/'input-manifest.json').read_text());ids=[str(x['case_id']) for x in manifest];byid={str(x['case_id']):x for x in manifest};rows=[];runs=[];prior=[]
    for p in sorted((ROOT/'training-recovered').glob('*.json')):
        d=json.loads(p.read_text());runs.append({k:d[k] for k in ('method','fold','seed','seconds_observed','status','training_artifact_status')})
        rows += [dict(x,method=d['method'],seed=d['seed'],fold=d['fold']) for x in d['rows']]
    for p in sorted((ROOT/'training').glob('prior-*.json')):prior+=json.loads(p.read_text())['rows']
    summary={'prior':metrics(prior),'methods':{},'training_runs':runs,'interpretation':'Recovered saved predictions only; original runs remain artifact-write failures; no checkpoint/loss-history reconstruction.'}
    for method in sorted({r['method'] for r in rows}):
        byseed={s:metrics([r for r in rows if r['method']==method and r['seed']==s]) for s in sorted({r['seed'] for r in rows if r['method']==method})};summary['methods'][method]={'by_seed':byseed,'mean_dispute_agreement':statistics.mean(m['dispute_mean_correct'] for m in byseed.values()),'mean_probability_loss':statistics.mean(m['dispute_balanced_probability_loss'] for m in byseed.values())}
    web=[];comparison=[];reference_counts=collections.Counter();masked=[]
    for cid in ids:
        ref=json.loads((ROOT/'references-admitted-v2'/f'{cid}.json').read_text());rr={t['test_id']:t for t in ref['tests']};runp=ROOT/'web'/f'baseline-{cid}-run.json'
        if not runp.exists() or json.loads(runp.read_text())['status']=='RUNNING':raise ValueError('WEB_RUN_PENDING:'+cid)
        run=json.loads(runp.read_text());answerp=ROOT/'web'/f'baseline-{cid}.json';answer=json.loads(answerp.read_text()) if answerp.exists() else None;ans={t['test_id']:t for t in answer['tests']} if answer else {}
        mat=json.loads((ROOT/'sources'/f'{cid}.json').read_text());sources=dict(mat['sources']);sources.update({x['source_id']:x for x in json.loads((ROOT/'sources'/f"{mat['family']}-law.json").read_text())})
        audit=[];judgments=[]
        for tid,t in rr.items():
            if t['supervision_mask']:reference_counts[t['status']]+=1
            else:masked.append({'case_id':cid,'test_id':tid,'reason':t.get('admission_reason')})
            prediction=ans.get(tid);state=prediction.get('status') if prediction else None
            err=check_refs(prediction.get('support_refs',[])+prediction.get('opposition_refs',[]),sources) if prediction else ['NO_COMPLETE_ANSWER']
            audit.append({'test_id':tid,'errors':err,'semantic_correctness_established':False})
            if t['supervision_mask']:judgments.append({'test_id':tid,'reference':t['status'],'prediction':state,'same':state==t['status']})
            model_status={}
            for m in summary['methods']:
                found=[r for r in rows if r['package_id']==cid and r['test_id']==tid and r['method']==m];model_status[m]=[LABELS[max(range(3),key=lambda j:r['probabilities'][j])] for r in sorted(found,key=lambda r:r['seed'])]
            comparison.append({'case_id':cid,'test_id':tid,'reference':t['status'],'mask':t['supervision_mask'],'web':state,'models':model_status})
        web.append(dict(case_id=cid,technical_status=run['status'],format_processing=(ROOT/'web'/f'baseline-{cid}-format-processing.json').exists(),answer_available=bool(answer),claim=answer.get('claim_analysis') if answer else None,judgments=judgments,source_address_audit=audit,url=run['url']))
    summary.update(reference_counts=dict(reference_counts),masked_count=len(masked),web=web,web_dispute_agreement=statistics.mean(sum(t['same'] for t in x['judgments'])/len(x['judgments']) for x in web if x['judgments']),web_planned=17,web_completed_answers=sum(x['answer_available'] for x in web),reference_groups=sum(bool(x['judgments']) for x in web))
    put(ROOT/'analysis/comparison.json',summary);put(ROOT/'analysis/test-comparison.json',comparison);put(ROOT/'analysis/masked-reference-rows.json',masked)
    with (ROOT/'analysis/test-comparison.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['case_id','test_id','reference','mask','web','Flat','Flat-ANCO','R-GCN','R-GCN-ANCO'])
        for x in comparison:w.writerow([x['case_id'],x['test_id'],x['reference'],x['mask'],x['web']]+['|'.join(x['models'][m]) for m in ('Flat','Flat-ANCO','R-GCN','R-GCN-ANCO')])
    prompts=[]
    for p in sorted((ROOT/'submitted').glob('*.json')):
        d=json.loads(p.read_text());prompts.append({'task':p.stem,'characters':len(d.get('prompt','')),'sha256':hashlib.sha256(d.get('prompt','').encode()).hexdigest(),'matches_saved_task':d.get('prompt')==(ROOT/'tasks'/(p.stem+'.txt')).read_text() if (ROOT/'tasks'/(p.stem+'.txt')).exists() else None})
    put(ROOT/'analysis/cost.json',dict(web_tasks=len(list((ROOT/'web').glob('*-run.json'))),local_fit_attempts=len(runs),extra_fit_attempts=0,fit_plus_prediction_seconds=sum(r['seconds_observed'] for r in runs),fit_history_peak_memory='NOT_SAVED_DUE_TO_EXPORT_FAILURE',web_tokens_and_exact_generation_seconds='NOT_EXPOSED',encoder=json.loads((ROOT/'text-cache/encoding.json').read_text())|{'audit':'see text-cache/encoding.json'},submissions=prompts))
    print(json.dumps({k:summary[k] for k in ('reference_counts','masked_count','web_planned','web_completed_answers','web_dispute_agreement')},indent=2))
if __name__=='__main__':main()
