"""V18 baselines, blind review and transfer accounting. No model generation.
References are accepted only in evaluation assembly, never inference construction.
"""
import collections,json,math
from .local_evaluation_v17 import LABELS,CLAIM_RULE,blind_order,local_metrics,semantic_metrics,equal_dispute_summary,hash_value

def prior_predictions(train,dev):
    def distribution(rows):
        groups=collections.defaultdict(list)
        for r in rows:groups[r['dispute_id']].append(r['label'])
        if not groups:return None
        return [sum(v.count(label)/len(v) for v in groups.values())/len(groups) for label in LABELS]
    global_prior=distribution(train);families=collections.defaultdict(list)
    for r in train:families[r['premise_family']].append(r)
    if global_prior is None:return []
    return [{'key':r['key'],'probabilities':distribution(families[r['premise_family']]) or global_prior,
             'basis':'EXACT_FAMILY_TRAIN_PRIOR' if r['premise_family'] in families else 'GLOBAL_DISPUTE_WEIGHTED_TRAIN_PRIOR',
             'family':r['premise_family'],'no_DEV_label_read':True} for r in dev]

def local_report(rows,predictions):
    dev=[r for r in rows if r['split']=='DEV'];train=[r for r in rows if r['split']=='TRAIN'];keys={r['key'] for r in dev}
    allpred={'RawP':[{'key':r['key'],'label':r['P_self_assessment']} for r in dev],
             'TrainPrior':prior_predictions(train,dev),**predictions};result={}
    for name,pp in allpred.items():
        pp=[r for r in pp if r['key'] in keys]
        result[name]={}
        for subset,rr in [('all_scorable',dev),('structurally_valid',[r for r in dev if r['structurally_valid']])]:
            kk={r['key'] for r in rr};pr=[r for r in pp if r['key'] in kk]
            by_dispute=[]
            for d in sorted({r['dispute_id'] for r in rr}):
                dr=[r for r in rr if r['dispute_id']==d];dk={r['key'] for r in dr}
                by_dispute.append({'dispute_id':d,'metrics':local_metrics([p for p in pr if p['key'] in dk],dr)})
            means={k:sum(v)/len(v) if (v:=[x['metrics'][k] for x in by_dispute if x['metrics'][k] is not None]) else None for k in ('macro_f1_observed_classes','error_allow_rate','error_block_rate','hierarchical_nll')}
            result[name][subset]={'connection_confusion':local_metrics(pr,rr),'per_dispute':by_dispute,'equal_dispute_means':means,
                                  'missing_predictions':sorted(kk-{r['key'] for r in pr})}
    return {'methods':result,'unit':'DISPUTE; connections not independent cases','labels':LABELS,'baseline_contract':'RawP is same source-use label; prior exact-family or declared global fallback'}

REVIEW_INSTRUCTION='''Evaluate the complete answers against only the supplied allowed original source and the frozen common checklist. No search, other conversations or new facts. Names of methods are hidden; content may reveal method, so blinding is incomplete. References are model-generated and source-reviewed, not human gold. Do not treat CHECK/PASS or open interpretation as legal correctness/failure. Assess the answer in its qualified scope. Correct source-grounded uncertainty may count as correctly handled. Check decisive source content beyond the answer's citations. A new claim absent from the checklist is evaluated against the source, not automatically wrong. Keep genuine interpretation disputes separate. Technical failures have null formal answers and no semantic score. Cite exact source words and IDs for decisive errors. Return one complete English JSON in the response body, not only a download link. Do not repair or regenerate tested answers.\n'''
REVIEW_FORMAT={'answers':[{'answer_id':'ANSWER_01','technical_status':'OK','key_items':[{'id':'KEY001','status':'CORRECTLY_HANDLED','basis':'source-based explanation','refs':['source id']}],
 'substantive_judgements':[{'id':'J001','text':'one distinct proposition','status':'SUPPORTED','major':False,'basis':'source-based explanation','refs':['source id'],'quote':'exact source words'}],
 'overall':'PARTIAL','decisive_changes':[]}], 'reference_disagreements':[]}

def blind_tasks(cid,case,rules,reference,answers):
    from .local_pipeline_v18 import source_text,directory
    mapping=blind_order(cid,list('ABCDEFG'));items=[]
    for neutral,method in mapping.items():
        row=answers[method]
        items.append({'answer_id':neutral,'technical_status':row['status'],'answer':row['answer']})
    tasks=[]
    for i,chunk in enumerate((items[:4],items[4:]),1):
        task=REVIEW_INSTRUCTION+'\nJUDGEMENT SPLITTING RULE:\n'+CLAIM_RULE+'\nFIXED REQUEST:\n'+json.dumps(next(q for q in case['targets'] if q['id']=='Q1'))+'\nGIVEN RULES:\n'+json.dumps(directory(rules),ensure_ascii=False)+'\nCOMPLETE ALLOWED SOURCE:\n'+source_text(case)+'\nFROZEN COMMON CHECKLIST:\n'+json.dumps(reference,ensure_ascii=False)+'\nNEUTRAL ANSWERS:\n'+json.dumps(chunk,ensure_ascii=False)+'\nOUTPUT CONTRACT:\n'+json.dumps(REVIEW_FORMAT)+'\nExactly one row for each submitted answer ID; all checklist IDs once for successful answers. key item statuses: CORRECTLY_HANDLED, OMITTED, INCORRECT, DISPUTED. substantive statuses: SUPPORTED, CONFIRMED_ERROR_OR_UNSUPPORTED, DISPUTED, UNEVALUABLE. overall: COMPLETE_AND_SOURCED, PARTIAL, MAJOR_ERROR, DISPUTED_OR_UNEVALUABLE. For a technical failure return answer:null, same technical_status, key_items:[], substantive_judgements:[], overall:null. Include concrete source-based decisive_changes, not changes inferred from classifier names.'
        tasks.append({'part':i,'text':task,'expected_ids':[r['answer_id'] for r in chunk],'has_evaluable_answer':any(r['technical_status']=='OK' for r in chunk),'sha256':hash_value(task)})
    return mapping,tasks

def validate_review(review,reference,expected,answers):
    if not isinstance(review,dict) or not isinstance(review.get('answers'),list):raise ValueError('REVIEW_INTERFACE_INVALID')
    for row in review['answers']:
        if row['answer_id'] not in answers:raise ValueError('UNKNOWN_REVIEW_ANSWER')
        if row['technical_status']!=answers[row['answer_id']]['status']:raise ValueError('TECHNICAL_STATUS_CHANGED_BY_REVIEWER')
        if row['technical_status']=='OK':
            for item in row['key_items']:
                if item['status'] not in ('CORRECTLY_HANDLED','OMITTED','INCORRECT','DISPUTED'):raise ValueError('KEY_STATUS_INVALID')
    return semantic_metrics(review,reference,expected)

def transfer_trace(cid,method,p,audit,baseline,answer,source_review=None):
    old={c['connection_id']:c for c in baseline['checks']};out=[]
    for c in audit['checks']:
        before=old[c['connection_id']]
        handling=[h for h in (answer or {}).get('connection_handling',[]) if h.get('connection_id')==c['connection_id']]
        out.append({'case_id':cid,'method':method,'connection_id':c['connection_id'],'P_label':c['P_label'],'model_label':c['applied_label'],
                    'label_changed':c['P_label']!=c['applied_label'],'old_disposition':before['disposition'],'new_disposition':c['disposition'],
                    'audit_changed':before['disposition']!=c['disposition'],'premises_affected':[j for j in audit['premise_judgments'] if c['connection_id'] in j['available_uses']+j['pending_uses'] or c['connection_id'] in j['blocked_uses']],
                    'final_reported_handling':handling,'full_answer_source_review':source_review,'effect':'PENDING_SOURCE_REVIEW' if source_review is None else 'SOURCE_REVIEW_RECORDED_NOT_CAUSAL_PROOF',
                    'common_interface_fix_attributed_to_model':False,'source_original_unchanged':True})
    return out
