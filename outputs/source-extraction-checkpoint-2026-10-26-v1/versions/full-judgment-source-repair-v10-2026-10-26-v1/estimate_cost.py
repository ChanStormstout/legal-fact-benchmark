"""Plan from actual receipts plus measured full-document requests; no API calls."""
import json
import statistics
import environment as env
from prepare import load
from source_v8 import save
from inspection import measure, TOKENIZER


def main():
    from tokenizers import Tokenizer
    tok=Tokenizer.from_file(str(TOKENIZER));cfg=load(env.HERE/'protocol.json')
    cohort=load(env.HERE/'private/preparation/cohort.json')['selected']
    measurements=load(env.HERE/'private/offline-whole-document-review/request-measurements.json')
    old=[]
    for p in sorted((env.V9/'private/run-v1/transport/1251841/ROLE/calls').glob('*/receipt.json')):
        rc=load(p);w=load(p.parent/'request.json')
        if rc.get('status')=='OK' and rc.get('usage'):
            old.append({'path':str(p),'tag':rc['tag'],'input':rc['usage']['prompt_tokens'],
                'output':rc['usage']['completion_tokens'],'seconds':rc['elapsed_seconds'],
                'local_input':measure(w)['message_content_tokens_local']})
    calibration=statistics.mean(r['input']/r['local_input'] for r in old)
    anchor=cohort[0];by_stage={}
    for stage in ['reading','review']:
        r=[x for x in old if x['tag'].startswith(stage)]
        by_stage[stage]={'output_per_call':statistics.mean(x['output'] for x in r),
            'input_per_call':statistics.mean(x['input'] for x in r)}
    elapsed_per_output=sum(x['seconds'] for x in old)/sum(x['output'] for x in old)
    replay=[]
    root=env.HERE/'private/offline-whole-document-review/chain/responses'
    for m in measurements['complete_cached_record_replay']:
        response=load(root/(m['stage']+'.json'))
        replay.append({**m,'output_tokens':len(tok.encode(json.dumps(response,separators=(',',':'),ensure_ascii=False),add_special_tokens=False).ids)})
    # Simulated response length is only an engineering scale estimate. It is not
    # evidence that a future model will produce the projected content or length.
    r_read=[r for r in replay if r['stage'].startswith(('reading-','independent-'))]
    r_recon=[r for r in replay if r['stage'].startswith('whole-document-reconcile-')]
    r_final=[r for r in replay if r['stage'].startswith('whole-document-final-review-')]
    anchor_source_tokens=len(tok.encode(json.dumps(load(env.HERE/'private/preparation/inputs/1251841.json')['sources']),add_special_tokens=False).ids)
    old_lw=[]
    for p in sorted((env.V8/'private/run-v1/transport/1251841/LW/calls').glob('*/receipt.json')):
        r=load(p)
        if r.get('status')=='OK':old_lw.append(r)
    rows=[]
    for c in cohort:
        cid=c['case_id'];first=[r for r in measurements['planned_first_readings'] if r['case_id']==cid]
        v9first=[r for r in first if r['stage'].startswith('V9-reading-')]
        v10first=[r for r in first if r['stage'].startswith(('primary-','independent-'))]
        source_tokens=len(tok.encode(json.dumps(load(env.HERE/'private/preparation/inputs'/f'{cid}.json')['sources']),add_special_tokens=False).ids)
        source_ratio=source_tokens/anchor_source_tokens
        density_ratio=(c['source_chars']/c['v10_batches'])/(anchor['source_chars']/anchor['v10_batches'])
        n=c['v9_planned_calls']//2
        inp=sum(r['message_content_tokens_local'] for r in v9first)*calibration
        inp+=inp+n*(by_stage['review']['input_per_call']-by_stage['reading']['input_per_call'])
        out=n*(by_stage['reading']['output_per_call']+by_stage['review']['output_per_call'])
        rows.append({'case_id':cid,'arm':'V9','calls':c['v9_planned_calls'],'input_tokens_estimate':inp,'output_tokens_estimate':out})
        inp=sum(r['message_content_tokens_local'] for r in v10first)*calibration
        for group in [r_recon,r_final]:
            overhead=statistics.mean(max(0,r['message_content_tokens_local']-anchor_source_tokens) for r in group)
            inp+=c['v10_review_groups']*(source_tokens+overhead*density_ratio)*calibration
        out=len(v10first)*statistics.mean(r['output_tokens'] for r in r_read)*density_ratio
        out+=c['v10_review_groups']*sum(statistics.mean(r['output_tokens'] for r in g) for g in [r_recon,r_final])*density_ratio
        rows.append({'case_id':cid,'arm':'V10','calls':c['v10_planned_calls'],'input_tokens_estimate':inp,'output_tokens_estimate':out})
        rows.append({'case_id':cid,'arm':'LW','calls':4,
            'input_tokens_estimate':sum(r['usage']['prompt_tokens'] for r in old_lw)*source_ratio,
            'output_tokens_estimate':sum(r['usage']['completion_tokens'] for r in old_lw)*source_ratio})
    for row in rows:
        row['cost_usd_estimate']=(row['input_tokens_estimate']*cfg['prices']['input']+row['output_tokens_estimate']*cfg['prices']['output'])/1e6
        row['seconds_estimate']=row['output_tokens_estimate']*elapsed_per_output
    totals={arm:{'calls':sum(r['calls'] for r in rows if r['arm']==arm),
                 'usd':sum(r['cost_usd_estimate'] for r in rows if r['arm']==arm),
                 'hours':sum(r['seconds_estimate'] for r in rows if r['arm']==arm)/3600}
            for arm in cfg['arms']}
    total=sum(r['cost_usd_estimate'] for r in rows);hours=sum(r['seconds_estimate'] for r in rows)/3600
    result={'status':'PLANNING_ESTIMATE_NOT_AUTHORIZATION_OR_INVOICE','cases':rows,'arms':totals,
        'central_usd':total,'planning_range_usd':[total*.7,total*1.8],
        'central_hours':hours,'planning_range_hours':[hours*.7,hours*1.8],
        'planned_logical_calls':sum(r['calls'] for r in rows),
        'input_token_calibration_reported_over_local':calibration,'observed_V9_receipts':old,
        'prices_from_frozen_prior_protocol':cfg['prices'],'price_currently_reverified':False,
        'unknown_usage_reserve_per_dispatch_usd':((262144-65536)*.17+65536*.25)/1e6,
        'assumptions':['No failures or retries in central estimate; upper range allows moderate inflation, not a guarantee.',
            'V10 response scale uses mechanically projected old records, not new model behavior.',
            'Long-document LW later stages scale with source size; no completed long-document comparator evidence.',
            'Latency inferred from prior same-model output throughput; service load and structured decoding can change.',
            'Annotation/review labor and any separately authorized annotation calls are excluded.',
            'Not an estimate for twelve whole-C reports or an A0 experiment.'],
        'new_model_calls':0}
    save(env.HERE/'COST_ESTIMATE.json',result)
    print(json.dumps({k:result[k] for k in ['central_usd','planning_range_usd','central_hours','planned_logical_calls','arms']}))


if __name__=='__main__':main()
