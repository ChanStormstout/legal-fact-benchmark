"""Read-only accounting of actual history requests, decisions and final citations."""
from common import read,save

def write_usage(dest,snapshot,shared=None):
    history={i:x for i,x in snapshot['directory'].items() if x['domain']=='HISTORY'}
    shown=set();ranked=set();selected=set();assessments=[];eligibility=[]
    for path in sorted((dest/'requests').glob('*.json')):
        shown.update(set(read(path)['material']['sources'])&set(history))
    for path in sorted(dest.glob('*retrieval-ledger.json')):
        ledger=read(path);selected.update(ledger['history_selected_ids'])
        for row in ledger.get('need_ledger',{}).values():
            ranked.update(h['id'] for q in row['queries'].values() for h in q['hits'])
        for angles in ledger['tasks'].values():
            for domains in angles.values():ranked.update(h['id'] for h in domains.get('HISTORY',{}).get('hits',[]))
    for path in sorted(dest.glob('*history-assessment.json')):
        assessments.append({'stage':path.name,**read(path)})
    if shared:
        ledger=shared.get('retrieval',{});selected.update(ledger.get('history_selected_ids',[]))
        for angles in ledger.get('tasks',{}).values():
            for domains in angles.values():ranked.update(h['id'] for h in domains.get('HISTORY',{}).get('hits',[]))
        assessments.append({'stage':'shared-counted-model-work','analogies':shared['proposal'].get('analogies',{}),'reviews':shared['reviews']['values'].get('analogies',{})})
    for path in sorted(dest.glob('*computation.json')):
        eligibility.append({'stage':path.name,'analogies':read(path).get('accepted',{}).get('analogies',{})})
    final=read(dest/'final-report.json') if (dest/'final-report.json').exists() else None
    citations=[]
    if final:
        for tid,item in final['items'].items():
            refs=set(item['refs'])&set(history)
            if item['include'] and refs:citations.append({'task_id':tid,'text':item['text'],'kind':item['kind'],'history_refs':sorted(refs),'support_ids':item['support_ids']})
        for hid,item in final.get('comparisons',{}).items():
            refs=set(item['refs'])&set(history)
            if item['include'] and refs:citations.append({'comparison_id':hid,'text':item['text'],'kind':'ANALOGY','history_refs':sorted(refs),'support_ids':[hid]})
    cited={r for row in citations for r in row['history_refs']}
    used=ranked|shown|selected|cited
    save(dest/'history-usage.json',{'catalog_documents':len({s['document_id'] for s in history.values()}),
        'source_map':{i:{k:s[k] for k in ('original_id','document_id','origin_group','locator','text_hash')} for i,s in history.items() if i in used},
        'ranked_history':sorted(ranked),'selected_history':sorted(selected),'actually_shown_in_this_arm_requests':sorted(shown),
        'need_runs':[read(p) for p in sorted(dest.glob('*retrieval-ledger.json'))],
        'partial_pair_events':[{"file":str(p.relative_to(dest)),"record":read(p)} for p in sorted(dest.glob('*history-events/*.json'))],
        'model_assessments':assessments,'program_eligibility':eligibility,'final_history_items':citations,
        'comparison_dispositions':{i:{k:x.get(k) for k in ('include','disposition','reason','report_item_id','permitted_use','need_id','selected_claims')} for i,x in (final or {}).get('comparisons',{}).items()},
        'selected_not_cited':sorted(selected-cited),'final_report_present':final is not None,
        'critical_retrieval_misses':None,'semantic_correctness':None,'reason':'Requires final original-source adjudication; model ACCEPT is not correctness.',
        'shared_model_work_charged':shared is not None,'history_never_current_fact':True})
