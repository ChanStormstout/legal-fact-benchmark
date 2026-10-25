"""Dispatch reservations, not token predictions or legal-coverage guarantees."""
from common import save
import json

STAGE_CAPS={'source-original-read':8192,'source-record-coverage':8192,'source-records':8192,'source-record-review':3072,'source-record-repair':6144,'source-record-additions':6144,'objects':4096,'identity':2048,'scopes':3072,'scope-review':4096,
    'task-owners-patch':2048,'tasks-inventory':4096,'tasks':4096,'task-equivalence':1024,'merge-review':1024,
    'task-review':4096,'retrieval-queries':3072,'uses':6144,'use-review':4096,'use-allocation':1024,
    'bundles':4096,'bundle-review':4096,'applications':3072,'application-review':3072,
    'paths':4096,'path-review':3072,'burdens':2048,'burden-review':2048,
    'requests':3072,'request-review':3072}


def stage_cap(tag,cfg):
    if cfg.get('capacity_diagnostic'):return cfg['diagnostic_output_tokens']
    t=tag.removeprefix('repair-')
    if t.startswith(('history-reading-','history-context-')):return cfg['history_reading_output_tokens']
    if t.startswith('history-compare-'):return cfg['history_pair_output_tokens']
    if t.startswith('history-review-'):return cfg['history_review_output_tokens']
    if t.startswith('final-review-'):return cfg['final_review_output_tokens']
    if t in ('report','report-revision'):return cfg['report_output_tokens']
    matches=[(k,v) for k,v in STAGE_CAPS.items() if t==k or t.startswith(k+'-')]
    return max(matches,key=lambda x:len(x[0]))[1] if matches else cfg['parameters']['max_tokens']


def usage(session):
    # Includes failed requests and technical retries. Cache hits have zero charge.
    return {'calls':sum(not r.get('not_new_model_call',False) for r in session.receipts),
        **{k:sum(r.get('resource_charge',r.get('usage',{})).get(k,0) for r in session.receipts)
            for k in ('prompt_tokens','completion_tokens')}}


def wire_input_bound(request,cfg):
    from communication import request_wire
    wire=request_wire(request,cfg)
    # Conservative byte-BPE planning allowance, not hosted usage/billing truth.
    return len(json.dumps(wire,ensure_ascii=False,separators=(',',':')).encode('utf-8'))+4096

def reserve(session,caps,label,optional=False,request=None):
    if session.cfg.get('capacity_diagnostic'):
        record={'label':label,'admitted':True,'optional':optional,'budget_enforced':False,
            'wire_max_tokens_omitted':False,'explicit_output_capacity':session.cfg['diagnostic_output_tokens'],'usage_so_far':usage(session),
            'boundary':'Only the separately authorized two-case diagnostic; provider context and technical guards remain.'}
        number=len(session.reservation_records);session.reservation_records.append(record)
        save(session.dest/'budget-reservations'/f'{number:03d}.json',record)
        return None
    u=usage(session);cfg=session.cfg
    known=wire_input_bound(request,cfg) if request else None
    prior=max([r.get('wire_input_planning_bound',0) or 0 for r in session.reservation_records]+[65536])
    future=max(prior,known or 0)
    reserve={'calls':len(caps),'completion_tokens':sum(caps),
        'prompt_tokens':(known if known is not None else future)*bool(caps)+future*max(0,len(caps)-1)}
    limits={'calls':cfg['max_calls_per_arm'],'prompt_tokens':cfg['max_input_tokens_per_arm'],
        'completion_tokens':cfg['max_output_tokens_per_arm']}
    reasons=[k.upper()+'_SUFFIX_RESERVATION' for k in limits if u[k]+reserve[k]>limits[k]]
    if known is not None and known+request['output_token_cap']>cfg['context_length']:
        reasons.append('CONSERVATIVE_WIRE_CONTEXT_BOUND_EXCEEDED')
    # Provider ledgers may include shared charges not present in Session receipts.
    provider=session.provider
    if hasattr(provider,'cost') and hasattr(provider,'spent'):
        if provider.spent+provider.cost(reserve)>cfg['maximum_new_usd']+1e-10:reasons.append('USD_SUFFIX_RESERVATION')
    record={'wire_input_planning_bound':known,'future_request_envelope':future,'label':label,'usage':u,'required_future':reserve,'limits':limits,'admitted':not reasons,
        'reasons':reasons,'optional':optional,'all_input_units_preserved':True,
        'assumption':'Current serialized request byte allowance plus maximum observed request envelope for future stages. Planning estimate only; provider retains independent full-context single-call guard and charges actual or conservative failure usage. Every dispatch is rechecked; no completion guarantee.'}
    number=len(session.reservation_records);session.reservation_records.append(record)
    save(session.dest/'budget-reservations'/f'{number:03d}.json',record)
    return ','.join(reasons) if reasons else None


def final_caps(cfg,repair=False):
    if cfg.get('capacity_diagnostic'):return []
    caps=[cfg['report_output_tokens'],cfg['final_review_output_tokens']]
    return caps if repair else caps+caps


def repair_plan(session,p,report,review,correctable,omissions,mechanical):
    """Only route observed errors; this computes dependencies, not their answers."""
    rows=list(omissions)+list(mechanical)+[dict(v,basis={'task_id':i}) for i,v in correctable.items()]
    targets={x.get('repair_target') for x in rows}-{'REPORT','NO_ALLOWED_REPAIR',None}
    records=set();affected=set();object_ids=set();scope_ids=set();source_omissions=[]
    import source_records as SR
    accepted_records=SR.qualify(session.s,p['source_records'],session.shared['reviews']['values']['source_records'])
    for rid,v in session.shared['reviews']['values']['source_records'].items():
        if v.get('decision')=='REJECT' or not accepted_records.get(rid,{}).get('report_eligible'):records.add(rid)
    for rid,v in review.get('source_records',{}).items():
        if rid in p['source_records'] and (v.get('decision')=='REJECT' or v.get('field_findings') or SR.review_conflicts(v,session.s) or v.get('observed_owner')!=p['source_records'][rid]['source_owner'] or v.get('observed_status')!=p['source_records'][rid]['status'] or v.get('observed_content_role')!=p['source_records'][rid]['content_role']):records.add(rid)
    for reviews in (session.shared['reviews']['values']['source_records'],review.get('source_records',{})):
        for rid,v in reviews.items():
            if rid not in p['source_records']:continue
            for finding in v.get('field_findings',[]):
                if finding['field'] in ('source_owner','owner_label','participant_roles','actors','court'):
                    targets.add('OBJECTS');records.add(rid)
                    rec=p['source_records'][rid]
                    object_ids.update(i for i in rec['actors']+[rec['source_owner'],rec['court']] if i in p['objects'])
    for row in rows:
        target=row.get('repair_target');basis=row.get('basis',{});basis=basis if isinstance(basis,dict) else {}
        refs=set(row.get('revision_refs') or row.get('refs',[]))
        tids={basis['task_id']} if basis.get('task_id') in p['tasks'] else set()
        if basis.get('use_id') in p['uses']:tids.add(p['uses'][basis['use_id']]['task_id'])
        if basis.get('scope_id') in p['scopes']:
            scope_ids.add(basis['scope_id']);tids.update(i for i,t in p['tasks'].items() if t['scope_id']==basis['scope_id'])
        if basis.get('source_record_id') in p['source_records']:
            rid=basis['source_record_id'];records.add(rid)
            tids.update(u['task_id'] for u in p['uses'].values() if rid in u.get('source_record_ids',[]))
            tids.update(i for i,x in report['items'].items() if rid in x.get('support_ids',[]))
        if basis.get('inventory_obligation'):tids.update(i for i,t in p['tasks'].items() if basis['inventory_obligation'] in t.get('obligation_ids',[]))
        if not tids and not basis:tids={i for i,t in p['tasks'].items() if set(t['question_basis_refs'])&refs}
        affected.update(tids)
        if target=='OBJECTS' and basis.get('observed_owner',basis.get('final_observed_owner'))!='UNDECLARED':object_ids.update(i for i,o in p['objects'].items() if set(o['refs'])&refs)
        if target=='SCOPES':scope_ids.update(p['tasks'][i]['scope_id'] for i in tids)
        if target=='SOURCE_RECORDS':
            records.update(i for i,r in p['source_records'].items() if set(r['refs'])&refs)
            # Missing content can reside in an unrendered record, need splitting,
            # or be absent. The model must decide from originals, not a filled answer.
            if row in omissions or basis.get('inventory_obligation') or basis.get('source_coverage_gap'):
                source_omissions.append({'question':row.get('question',row.get('reason','Reassess the addressed original passage.')),'refs':sorted(refs)})
    if 'OBJECTS' in targets:
        records.update(i for i,r in p['source_records'].items() if set(r['actors']+r['properties']+[r['source_owner'],r['court']])&object_ids)
    # A phrase repeated by several checks is one recovery request, not multiple
    # additions. The raw judgments remain in their original review artifacts.
    source_omissions=list({tuple(x['refs']):x for x in source_omissions}.values())
    if records or source_omissions:targets.add('SOURCE_RECORDS')
    affected.update(u['task_id'] for u in p['uses'].values() if set(u.get('source_record_ids',[]))&records)
    affected.update(i for i,t in p['tasks'].items() if t['scope_id'] in scope_ids)
    if targets & {'SOURCE_RECORDS','OBJECTS','SCOPES','TASKS'}:targets.add('USES')
    if targets & {'OBJECTS','SCOPES','TASKS'}:targets.add('RULE_MAPPING')
    if targets & {'SOURCE_RECORDS','OBJECTS','SCOPES','TASKS'}:affected=set(p['tasks'])
    use_caps={i:min(session.cfg['max_uses_per_task'],sum(u['task_id']==i for u in p['uses'].values())+2) for i in affected}
    mapping_caps={k:min(session.cfg[k],len(p[group])+session.cfg['max_registry_additions']) for k,group in [('max_applications','applications'),('max_paths','paths'),('max_burdens','burdens'),('max_requests','requests')]}
    return {'use_caps':use_caps,'mapping_caps':mapping_caps,'targets':sorted(targets),'record_ids':sorted(records),'source_omissions':source_omissions,
        'affected_tasks':sorted(affected),'objects_ids':sorted(object_ids),'scopes_ids':sorted(scope_ids),
        'order':['OBJECTS','SCOPES','SOURCE_RECORDS','TASKS','USES','RULE_MAPPING','REPORT'],
        'whole_source_snapshot_retained':True}


def repair_caps(session,p,targets,affected,plan=None):
    """Reserve bounded actual registry repairs instead of a maximum-sized rebuild.

    Generated additions/splits use explicit caps; no generated rows are truncated.
    The reservation is a planning bound, never a promise of semantic completion.
    """
    if session.cfg.get('capacity_diagnostic'):return []
    cfg=session.cfg;b=cfg['review_batch_size'];ceil=lambda n,size=b:(n+size-1)//size
    plan=plan or {};caps=[]
    if 'OBJECTS' in targets:
        count=len(plan.get('objects_ids',p['objects']))+min(cfg['max_registry_additions'],cfg['max_objects']-len(p['objects']))
        caps += [4096]+[2048]*ceil(count)
    if targets & {'SCOPES','OBJECTS'}:
        count=len(plan.get('scopes_ids',p['scopes']))+min(cfg['max_registry_additions'],cfg['max_scopes']-len(p['scopes']))
        caps += [3072]+[4096]*ceil(count)
    if 'SOURCE_RECORDS' in targets:
        n=len(plan.get('record_ids',[]));added=cfg['max_source_record_additions'] if plan.get('source_omissions') else 0
        caps += [6144]*ceil(n,cfg['source_record_batch_size'])+([6144] if added else [])
        caps += [3072]*ceil(min(cfg['max_source_records'],n*cfg['max_source_record_splits']+added),cfg['source_record_batch_size'])
        caps += [STAGE_CAPS['source-record-coverage']]
    if 'TASKS' in targets:
        caps += [4096,4096,1024]+[1024]*ceil(cfg['max_tasks'])+[4096]*ceil(cfg['max_tasks'])+[3072]
        count=cfg['max_tasks']
    else:
        count=len(affected)
        if targets & {'SCOPES','OBJECTS'}:caps += [2048]+[4096]*ceil(count)
    if targets & {'TASKS','SCOPES','OBJECTS'}:
        remaining=max(0,cfg['history_max_calls']-session.history_usage()[0])
        caps += [max(cfg['history_reading_output_tokens'],cfg['history_pair_output_tokens'],cfg['history_review_output_tokens'])]*remaining
    if 'USES' in targets and count:
        retained=sum(u['task_id'] not in affected for u in p['uses'].values()) if 'TASKS' not in targets else 0
        use_count=min(cfg['max_total_uses']-retained,sum(plan.get('use_caps',{}).values()) if plan and 'TASKS' not in targets else count*cfg['max_uses_per_task'])
        caps += [1024]+[6144]*ceil(count)+[4096]*ceil(use_count,cfg['source_use_review_batch_size'])
        caps += [4096]*ceil(count)+[4096]*ceil(count*cfg['max_bundles_per_task'])
    if 'RULE_MAPPING' in targets:
        bounds=plan.get('mapping_caps',cfg)
        count=bounds['max_applications']
        caps += [3072]*ceil(count)*2+[4096]+[3072]*ceil(bounds['max_paths'])
        caps += [2048]+[2048]*ceil(bounds['max_burdens'])+[3072]+[3072]*ceil(bounds['max_requests'])
    return caps+final_caps(cfg,True)
