"""Report every frozen question; agreement is not legal accuracy."""
import collections
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.conditions_v3 import evidence_ok, execute
from legal_bench.rules_verdict_v1.source_views import write_new, digest

ROOT=Path('outputs/rules-verdict-v3')
def read(p):return json.loads(Path(p).read_text())


def report():
    protocol=read(ROOT/'protocol/tasks.json')
    references={(r['case_id'],r['question_id']):r for r in read(ROOT/'references/condition-reference-v3.json')['answers']}
    rows=[];runs=[]
    for cid in protocol['cases']:
        source=read(ROOT/'sources'/(cid+'-allowed.json'))
        for method in ['A','B']:
            folder=ROOT/'runs'/cid/method
            meta=read(folder/'run.json');raw_status=meta['run_status']
            recovery=ROOT/'format-recovery'/cid
            if method=='B' and (recovery/'recovery.json').exists():
                meta=dict(meta,run_status=read(recovery/'recovery.json')['effective_run_status'],original_run_status=raw_status)
            runs.append({'case_id':cid,'method':method,**meta})
            answers=[]
            if meta['run_status']=='OK':
                answers=read(folder/'parsed.json')['answers'] if method=='A' else read(recovery/'execution.json')
            for q in protocol['questions']:
                candidates=[a for a in answers if a['question_id']==q['id']]
                ref=references[cid,q['id']]
                a=candidates[0] if len(candidates)==1 else None
                runstatus=meta['run_status'] if meta['run_status']!='OK' else 'OK' if a is not None else 'FORMAT_ERROR'
                status=a['answer_status'] if runstatus=='OK' else None
                evidence=a.get('evidence',[]) if a else []
                if a and method=='B':
                    evidence=[e for side in ['support','opposition'] for w in a[side] for atom in w['atoms'] for e in atom['evidence']]
                comparison='TECHNICAL_FAILURE' if runstatus!='OK' else 'STATUS_AGREEMENT_ONLY' if status==ref['answer_status'] else 'STATUS_DISAGREEMENT'
                rows.append({'case_id':cid,'question_id':q['id'],'method':method,
                    'reference_status':ref['answer_status'],'answer_status':status,'run_status':runstatus,
                    'original_run_status':raw_status,'comparison':comparison,'evidence_located':evidence_ok(evidence,source) if evidence else None,
                    'binding_and_entailment_verified':False,
                    'uncertainty_origin':'METHOD_INCOMPLETE_RELATIVE_REFERENCE' if status=='UNKNOWN' and ref['answer_status']!='UNKNOWN' else 'REFERENCE_ALSO_UNKNOWN' if status=='UNKNOWN' else None,
                    'answer':a,'reference':ref})
    stats={}
    for method in ['A','B']:
        subset=[r for r in rows if r['method']==method]
        stats[method]={'status_agreement':sum(r['comparison']=='STATUS_AGREEMENT_ONLY' for r in subset),
            'questions':len(subset),'technical_failures':sum(r['run_status']!='OK' for r in subset),
            'by_reference':{s:dict(collections.Counter(str(r['answer_status']) for r in subset if r['reference_status']==s)) for s in ['SUPPORTED','REFUTED','UNKNOWN','CONFLICT']}}
    discrepancies=[r for r in rows if r['comparison']=='STATUS_DISAGREEMENT']
    def priority(r):
        return (0 if r['answer_status']=='SUPPORTED' else 1 if r['reference_status']=='SUPPORTED' else 2,
            protocol['cases'].index(r['case_id']),r['question_id'],r['method'])
    # A pair reviewed once even if both methods disagree: at most three case-question pairs.
    selected=[];seen=set()
    for row in sorted(discrepancies,key=priority):
        key=(row['case_id'],row['question_id'])
        if key not in seen: selected.append({'case_id':key[0],'question_id':key[1]});seen.add(key)
        if len(selected)==3:break
    write_new(ROOT/'results/rows.json',rows)
    write_new(ROOT/'results/audit-selection.json',{'rule':'False support first, then missed reference support, then other discrepancy; fixed case order, question id, method. Deduplicate case-question.','max_pairs':3,'selected':selected})
    summary={'role':'EXPOSED_DEVELOPMENT_CONDITION_DIAGNOSIS','cases':len(protocol['cases']),
        'questions':len(references),'methods':stats,'reference_counts':dict(collections.Counter(r['answer_status'] for r in references.values())),
        'local_calls':len(runs),'web_reference_calls':1,'retries':0,
        'original_format_failures':sum(r.get('original_run_status',r['run_status'])=='FORMAT_ERROR' for r in runs),
        'format_recovery_applied_uniformly':True,
        'generation_seconds':sum(r.get('elapsed_seconds',0) for r in runs),
        'peak_mlx_memory_gb':max(r.get('peak_mlx_memory_gb',0) for r in runs),
        'no_overall_accuracy_claim':True,'full_legal_rule_or_verdict_evaluated':False,
        'Q2_positive_coverage':0,'runs':[{'case_id':r['case_id'],'method':r['method'],'run_status':r['run_status'],
            'input_tokens':r.get('prompt_tokens_actual',r['prompt_tokens']),'output_tokens':r.get('output_tokens'),
            'seconds':r.get('elapsed_seconds')} for r in runs]}
    write_new(ROOT/'summary.json',summary)
    with (ROOT/'results/table.csv').open('x') as f:
        fields=['case_id','question_id','method','reference_status','answer_status','run_status','comparison','evidence_located','uncertainty_origin']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r[k] for k in fields} for r in rows)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':report()
