"""Complete original-source orchestration; no reference labels in runtime inputs."""
import copy
import json
import time
from pathlib import Path
import contracts as C
import engine as E
import prompts as P
from common import ROOT, REPO, VERSION, digest, read, save, mint, mint_objects, complete_rule_questions, source_payload, prepare_sources, render_text, actionable_omissions, coverage_consistent, refs_valid, witness_registry, witness_payload, derive_allowed_coverage
from retrieval import retrieve,Index,batches,source_window
import report_control as RC
import history_comparison as HC
import resource_plan as RP
import source_records as SR
from common import time_registry
from communication import retrieval_for_report, revision_feedback,visible_schema,feedback_for_stage,report_content,bind_review_addresses

class ResourceStop(RuntimeError): pass

class CallFailure(ResourceStop):
    """Non-retryable call failure; distinct from exhausting a resource budget."""
    def __init__(self,status,halt_reason=None,provider_halted=False):
        super().__init__('API:'+status)
        self.status=status;self.halt_reason=halt_reason;self.provider_halted=provider_halted


def failure_details(exc):
    receipts=getattr(exc,'receipts',[])
    last=receipts[-1] if receipts else {}
    status=getattr(exc,'status',None) or last.get('status')
    if status:return {'stop_reason':status,'failure_stage':last.get('tag'),
        'billing_state':last.get('billing_state'),'dispatch_halt_reason':getattr(exc,'halt_reason',None) or last.get('halt_reason'),
        'provider_halted':getattr(exc,'provider_halted',False),
        'content_status':last.get('content_status',status),'billing_hold':last.get('billing_hold',False),
        'case_blocked':last.get('case_blocked',False),'dispatch_stop':last.get('dispatch_stop',getattr(exc,'provider_halted',False))}
    return {'stop_reason':'RESOURCE_LIMIT' if isinstance(exc,ResourceStop) else 'TECHNICAL_FAILURE'}

class Session:
    def __init__(self,provider,snapshot,cfg,dest,arm):
        self.provider=provider;self.s=snapshot;self.cfg=cfg;self.dest=Path(dest);self.arm=arm;self.receipts=[]
        self.started=time.monotonic();self.prefix='';self.coverage=None;self.focus=[];self.index=Index(snapshot);self.source_text=source_payload(snapshot);self.feedback=None
        self.history_focus=[];self.shared=None;self.current_records={};self.current_record_acceptance={}
        self.source_reading_cache={};self.source_original_reading=None;self.history_failures=[];self.rule_screen={}
        self.revoked=set();self.request_manifest=[];self.record_repair=None;self.history_reading_cache={};self.history_expansions=0;self.history_pairs_started=0;self.history_pair_ids=set();self.reservation_records=[];self.repair_task_ids=set();self.repair_plan=None
    def ask(self,tag,task,schema,extra=None,identity_only=False,source_ids=None,history_only=False):
        tag=self.prefix+tag
        cap=RP.stage_cap(tag,self.cfg)
        final_stage=tag.removeprefix('repair-').startswith(('report','final-review-'))
        suffix=[] if final_stage else RP.final_caps(self.cfg,repair=bool(self.prefix))
        explicit_window=source_ids is not None
        history_stage=tag.removeprefix('repair-').startswith(('analogies-','analogy-review-','report','final-review-'))
        source_only=identity_only or tag.removeprefix('repair-').startswith(('source-record','tasks-inventory'))
        available=[i for i,x in self.s['directory'].items()
                   if (i in (source_ids or []) if history_only else x['domain']=='CASE' if source_only else x['domain']!='HISTORY' or (history_stage and i in self.history_focus))]
        if history_only and (not available or any(self.s['directory'][i]['domain']!='HISTORY' for i in available) or len({self.s['directory'][i]['document_id'] for i in available})!=1):raise ValueError('ISOLATED_HISTORY_READ_REQUIRES_ONE_HISTORY_DOCUMENT')
        limit=self.cfg['source_window_chars'];long=sum(len(self.s['directory'][i]['text']) for i in available)>limit
        if source_ids is None and not long:source_ids=available
        elif source_ids is None:
            # Include all explicit references plus the task ranking. The full original
            # remains in the snapshot and the coverage ledger records every read chunk.
            required=set()
            def collect(x):
                if isinstance(x,str) and x in available:required.add(x)
                elif isinstance(x,dict):
                    for key,v in x.items():
                        if key not in ('coverage','coverage_ledger','read_ids','not_in_this_window','retrieval'):collect(v)
                elif isinstance(x,list):
                    for v in x:collect(v)
            collect(extra or {})
            selected=[i for i in self.index.expand(required) if i in available]
            for i in self.focus+available:
                if i not in available or i in selected:continue
                candidate=list(dict.fromkeys(selected+[k for k in self.index.expand([i]) if k in available]))
                if sum(len(self.s['directory'][k]['text']) for k in candidate)<=limit:selected=candidate
            source_ids=selected
        visible=source_window(self.s,source_ids,limit) if long and not explicit_window else {i:self.source_text[i] for i in source_ids}
        if sum(len(v['text']) for v in visible.values())>limit:raise ResourceStop('EXPLICIT_SOURCE_WINDOW_TOO_LARGE')
        if identity_only:visible={i:v for i,v in visible.items() if v['domain']=='CASE'}
        material={'question':self.s['question'],'question_scope':self.s['scope'],
            'sources':visible,
            'material':extra or {}}
        if history_only:
            material.pop('question');material.pop('question_scope')
            material['assessment_scope']='ONE_HISTORY_DOCUMENT_NO_CURRENT_CASE_OR_PROPOSED_ANALOGY'
        if tag.removeprefix('repair-').startswith('identity-'):
            # Identity evidence must not be evaluated against success of the lawsuit.
            material.pop('question');material.pop('question_scope')
            material['assessment_scope']='SOURCE_MENTION_NAME_AND_OBJECT_TYPE_ONLY'
        if tag.removeprefix('repair-').startswith('source-original-read-'):
            material.pop('question');material.pop('question_scope')
            material['assessment_scope']='ORIGINAL_FIRST_NO_CANDIDATE_OR_REGISTRY_OR_PRIOR_REVIEW'
        source_description=tag.removeprefix('repair-').startswith(('source-record','source-original-read-'))
        if source_description:
            material.pop('question',None);material.pop('question_scope',None)
            material['assessment_scope']='SOURCE_DESCRIPTION_SEPARATE_FROM_TARGET_LEGAL_RESOLUTION'
        material['source_visibility']={'read_ids':list(visible),'not_in_this_window':[i for i in available if i not in visible],
            'coverage_ledger':self.coverage if long else None,'no_absence_inference':True}
        material['history_documents']={v['document_id']:v['metadata']['history_identity']
            for i,v in self.s['directory'].items() if i in visible and v['domain']=='HISTORY' and 'history_identity' in v['metadata']}
        registry=witness_registry(self.s)
        schema=visible_schema(schema,set(self.s['directory'])|set(registry),
            set(visible)|{sid for sid,w in registry.items() if w['ref'] in visible})
        if '"span_id"' in json.dumps(schema):
            material['sources']=witness_payload(visible)
            material['witness_address_policy']='Choose displayed span_id; do not write or paraphrase quotations. Every original character is preserved.'
        if tag.removeprefix('repair-') in ('scopes','scopes-patch','direct-scopes'):
            material['literal_time_choices']={i:r for i,r in time_registry(self.s).items() if r['ref'] in visible}
        if not source_only and not history_only and not tag.removeprefix('repair-').startswith('final-review-'):
            material['frozen_law']={k:v for k,v in self.s['rule_library'].items() if k!='authority_clips'}
            # Original law text appears once, in the program source dictionary.
            material['law_reference_aliases']={}
            for k,v in self.s['directory'].items():
                if v['domain']=='LAW':material['law_reference_aliases'].setdefault(v['original_id'],[]).append(k)
        request={'output_token_cap':cap,'version':VERSION,'implementation_hash':self.cfg.get('implementation_hash','UNFROZEN_ENGINEERING_ONLY'),'snapshot_id':self.s['snapshot_id'],'model':self.cfg['parameters'],
            'model_revision':self.cfg['local_revision'],'policy':P.HISTORY_ONLY if history_only else P.IDENTITY_POLICY if tag.removeprefix('repair-').startswith('identity-') else P.BINDING_POLICY if tag.removeprefix('repair-').startswith('scope-review-') else P.POLICY,'task':task,'material':material,'schema':schema,
            'namespace':self.s['namespace'],'review_policy':'SCOPED_SOURCE_REVIEW_NOT_LEGAL_APPROVAL'}
        if source_description:request['policy']=SR.SOURCE_POLICY
        reason=RP.reserve(self,[cap]+suffix,'dispatch:'+tag,request=request)
        if reason:raise ResourceStop(reason)
        key=digest(request)
        self.request_manifest.append({'tag':tag,'request_hash':key,'source_ids':list(visible),
            'CASE_complete':all(i in visible for i,x in self.s['directory'].items() if x['domain']=='CASE'),
            'missing_CASE_ids':[i for i,x in self.s['directory'].items() if x['domain']=='CASE' and i not in visible],
            'source_hashes':{i:self.s['directory'][i]['text_hash'] for i in visible},
            'stage_input_policy':'ISOLATED_HISTORY' if history_only else 'CASE_ONLY' if source_only else 'CASE_LAW_SELECTED_HISTORY',
            'frozen_law_included':'frozen_law' in material,'schema_hash':digest(schema)})
        save(self.dest/'requests'/f'{tag}.json',{'request_hash':key,**request})
        # Cache identity binds complete source/view/rules/model/prompt/schema and bindings.
        for attempt in range(self.cfg['max_technical_retries']+1):
            try:
                if attempt:
                    reason=RP.reserve(self,[cap]+suffix,'retry:'+tag,request=request)
                    if reason:raise ResourceStop(reason)
                if tag.removeprefix('repair-').startswith('history-'):
                    self.guard_history_call(cap)
                value,receipt=self.provider.call(self.s['case_id'],self.arm,tag,request,attempt)
                receipt={**receipt,'tag':tag};self.receipts.append(receipt);C.validate(value,schema)
                raw_value=C.loads(Path(receipt['raw_response_path']).read_text()) if receipt.get('raw_response_path') else value
                subjects=(extra or {}).get('comparison_registry',{}) if tag.removeprefix('repair-') in ('report','report-revision') else (extra or {}).get('subjects',{})
                consumed,address_mapping=bind_review_addresses(tag,value,subjects,self.s)
                if tag.removeprefix('repair-').startswith('uses-'):
                    records=(extra or {})['source_records']
                    for tid,part in consumed.items():
                        for row in part['uses']:
                            rid=row.pop('source_record_id');rec=records[rid]
                            row.update(source_record_ids=[rid],text=rec['text'],refs=list(rec['refs']),source_owner=rec['source_owner'])
                            address_mapping.append({'operation':'SELECT_EXACT_SOURCE_RECORD','subject':tid,'record_id':rid,'record_hash':digest(rec),'semantic_verdict_unchanged':True})
                save(self.dest/'responses'/f'{tag}-{attempt}.json',{'request_hash':key,'raw_model_value':raw_value,'consumed_model_value':consumed,'program_address_mapping':address_mapping,'semantic_verdicts_changed':False,'receipt':receipt})
                return consumed
            except ResourceStop as exc:
                self.receipts.extend(getattr(exc,'receipts',[]));raise
            except Exception as exc:
                self.receipts.extend(getattr(exc,'receipts',[]))
                save(self.dest/'failures'/f'{tag}-{attempt}.json',{'request_hash':key,'type':type(exc).__name__,'error':str(exc),'answer':None})
                if attempt>=self.cfg['max_technical_retries']:raise
        raise AssertionError('UNREACHABLE')
    def history_usage(self):
        receipts=[r for r in self.receipts if r.get('tag','').removeprefix('repair-').startswith('history-') and not r.get('not_new_model_call')]
        return len(receipts),sum(r.get('resource_charge',r.get('usage',{})).get('completion_tokens',0) for r in receipts)
    def guard_history_call(self,cap):
        if self.cfg.get('capacity_diagnostic'):return
        calls,output=self.history_usage()
        if calls+1>self.cfg['history_max_calls'] or output+cap>self.cfg['history_max_output_tokens']:
            raise ResourceStop('HISTORY_STAGE_BUDGET_NO_DISPATCH')
    def reserve_history_pair(self,cold,expansion=False,pair_id=None):
        if len(self.history_pair_ids)>=self.cfg['history_max_pairs'] and pair_id not in self.history_pair_ids and not expansion:return 'HISTORY_PAIR_COUNT_CAP'
        cfg=self.cfg;caps=([cfg['history_reading_output_tokens']] if cold or expansion else [])+[cfg['history_pair_output_tokens'],cfg['history_review_output_tokens']]
        calls,output=self.history_usage()
        if not cfg.get('capacity_diagnostic') and (calls+len(caps)>cfg['history_max_calls'] or output+sum(caps)>cfg['history_max_output_tokens']):return 'HISTORY_PAIR_BUDGET_NOT_ASSESSED'
        return RP.reserve(self,caps+RP.final_caps(cfg,repair=bool(self.prefix)),'complete-history-pair',optional=True)

    def review_batches(self,tag,task,schema_fn,rows,extra=None,identity_only=False):
        result={};keys=list(rows);size=self.cfg.get('source_use_review_batch_size',1) if tag=='use-review' else self.cfg['review_batch_size']
        for i in range(0,len(keys),size):
            selected=keys[i:i+size]
            source_ids=None
            if tag=='identity':
                refs=[r for k in selected for r in rows[k]['refs']]
                source_ids=[r for r in self.index.expand(refs) if self.s['directory'][r]['domain']=='CASE']
            context=copy.deepcopy(extra or {})
            if tag=='use-review':
                tids={rows[k]['task_id'] for k in selected}
                context['tasks']={k:v for k,v in context['tasks'].items() if k in tids}
                sids={t['scope_id'] for t in context['tasks'].values()}
                context['scopes']={k:v for k,v in context['scopes'].items() if k in sids}
                rids={rid for k in selected for rid in rows[k].get('source_record_ids',[])}
                context['source_records']={k:v for k,v in context['source_records'].items() if k in rids}
                # Original CASE/LAW context is unchanged. Only unrelated proposed
                # answers are removed, so one verdict cannot drift to another use.
            result.update(self.ask(f'{tag}-{i//size}',task,schema_fn(selected),{'subjects':{k:rows[k] for k in selected},**context},identity_only,source_ids))
        return result


def registry_patch(session,kind,rows,objects=None):
    cfg=session.cfg;s=session.s;plan=session.repair_plan
    ids=plan.get(kind.lower()+'_ids',[])
    base=C.objects(s,cfg)['properties']['objects']['items'] if kind=='OBJECTS' else C.scopes(s,objects,cfg)['properties']['scopes']['items']
    capacity=min(cfg.get('max_registry_additions',4),cfg['max_objects' if kind=='OBJECTS' else 'max_scopes']-len(rows))
    schema=C.obj({'replacements':C.keyed(ids,base),'additions':C.arr(base,capacity),'unresolved':C.arr(C.text(180),8)})
    raw=session.ask(kind.lower()+'-patch',(P.OBJECTS if kind=='OBJECTS' else P.SCOPES)+
        ' Repair the addressed registry entries from originals. Preserve their addresses; every changed object has a new version and is reviewed again. Add only source-supported missing entries. Do not copy earlier acceptance or guess a legal answer.',schema,
        {'subjects':{i:rows[i] for i in ids},'existing_registry':rows,'objects':objects or rows,
         'source_linked_repair':feedback_for_stage(session.feedback,kind)},identity_only=kind=='OBJECTS')
    out=copy.deepcopy(rows)
    for ident,row in raw['replacements'].items():
        if kind=='OBJECTS':
            from object_contract import validate_object_shape
            validate_object_shape(row)
            row=copy.deepcopy(row);components=row.pop('components')
            if components and (row['kind']!='PROPERTY' or row['extent']!='HETEROGENEOUS_COLLECTION'):raise ValueError('PROPERTY_COMPONENTS_REQUIRE_DECLARED_COLLECTION')
            children=mint([{**c,'kind':'PROPERTY','parent_object':ident} for c in components],'O')
            if children:row['member_ids']=list(children)
            out.update(children)
        out[ident]=row
    additions=mint_objects(raw['additions'],capacity) if kind=='OBJECTS' else mint(raw['additions'],'X')
    out.update(additions)
    if len(out)>cfg['max_objects' if kind=='OBJECTS' else 'max_scopes']:raise ResourceStop('PATCH_REGISTRY_CAP_NO_TRUNCATION')
    changed={i for i,v in out.items() if i not in rows or digest(v)!=digest(rows[i])}
    save(session.dest/(session.prefix+kind.lower()+'-patch-lineage.json'),{
        'changed':{i:{'old_hash':digest(rows[i]) if i in rows else None,'new_hash':digest(out[i])} for i in sorted(changed)},
        'stable_addresses_are_not_old_versions':True,'unresolved':raw['unresolved']})
    return out,changed,raw['unresolved']


def retain_evidence(old,tasks,records,affected):
    """Retain only address-valid, explicitly unaffected evidence; no new verdicts."""
    uses={i:copy.deepcopy(u) for i,u in old.get('uses',{}).items()
        if u['task_id'] in tasks and u['task_id'] not in affected
        and all(r in records for r in u.get('source_record_ids',[]))}
    bundles={i:copy.deepcopy(b) for i,b in old.get('bundles',{}).items()
        if b['task_id'] in tasks and b['task_id'] not in affected
        and all(u in uses and uses[u]['task_id']==b['task_id'] for u in b['use_ids']+b['counter_use_ids'])}
    return uses,bundles


def build_shared(session,omissions=None,prior=None,repair_targets=()):
    s=session.s;cfg=session.cfg
    order={'OBJECTS':0,'SCOPES':1,'TASKS':2,'USES':3,'RULE_MAPPING':4}
    earliest=min((order[t] for t in repair_targets if t in order),default=0)
    reused=[];old={};old_reviews={}
    if prior is not None:
        if prior['snapshot_id']!=s['snapshot_id'] or prior.get('implementation_hash')!=cfg.get('implementation_hash') or prior.get('parameters')!=cfg['parameters'] or prior.get('model_revision')!=cfg['local_revision']:
            raise ValueError('REPAIR_PARENT_VERSION_MISMATCH')
        old=prior['proposal'];old_reviews=E.require_review(s,old,prior['reviews'])
    def reuse(name):
        if prior is None or order[name]>=earliest:return False
        reused.append(name);return True
    ensure_coverage(session)
    original_reading=SR.read_originals(session)
    plan=session.repair_plan if prior is not None else None
    if plan:cfg={**cfg,**plan['mapping_caps']}
    changed_objects=set();changed_scopes=set()
    if plan and 'OBJECTS' in repair_targets:
        objects,changed_objects,limits=registry_patch(session,'OBJECTS',old['objects'])
        raw={'unresolved':limits};object_reviews={i:copy.deepcopy(v) for i,v in old_reviews['objects'].items() if i not in changed_objects}
        identities={i:{k:objects[i][k] for k in ('name','kind','refs')} for i in changed_objects}
        object_reviews.update(session.review_batches('identity',P.REVIEW_OBJECTS,lambda ids:C.review_objects(s,ids),identities,identity_only=True))
    elif reuse('OBJECTS'):
        objects=copy.deepcopy(old['objects']);object_reviews=copy.deepcopy(old_reviews['objects'])
        raw={'unresolved':copy.deepcopy(old['object_limitations'])}
    else:
        raw=session.ask('objects',P.OBJECTS,C.objects(s,cfg),{'source_linked_repair':feedback_for_stage(session.feedback,'OBJECTS')},identity_only=True);objects=mint_objects(raw['objects'],cfg['max_objects'])
        identities={i:{k:o[k] for k in ('name','kind','refs')} for i,o in objects.items()}
        object_reviews=session.review_batches('identity',P.REVIEW_OBJECTS,lambda ids:C.review_objects(s,ids),identities,identity_only=True)
    if plan and ('SCOPES' in repair_targets or changed_objects):
        # Scope references keep addresses, but altered values never inherit reviews.
        dependency_ids={i for i,x in old['scopes'].items() if set(x['actors']+x['properties']+[x['court']]+[r['object_id'] for r in x.get('participant_roles',[])])&changed_objects}
        plan['scopes_ids']=sorted(set(plan['scopes_ids'])|dependency_ids)
        scopes,changed_scopes,_=registry_patch(session,'SCOPES',old['scopes'],objects)
        review_ids=changed_scopes|dependency_ids
        scope_reviews={i:copy.deepcopy(v) for i,v in old_reviews['scopes'].items() if i not in review_ids}
        scope_reviews.update(session.review_batches('scope-review',P.REVIEW_SCOPES,lambda ids:C.review_scopes(s,{i:scopes[i] for i in ids},objects),{i:scopes[i] for i in review_ids},{'objects':objects},identity_only=True))
    elif reuse('SCOPES'):

        scopes=copy.deepcopy(old['scopes']);scope_reviews=copy.deepcopy(old_reviews['scopes'])
    else:
        raw_scope=session.ask('scopes',P.SCOPES,C.scopes(s,objects,cfg),{'objects':objects,'source_linked_repair':feedback_for_stage(session.feedback,'SCOPES')})
        scopes=mint(raw_scope['scopes'],'X')
        scope_reviews=session.review_batches('scope-review',P.REVIEW_SCOPES,lambda ids:C.review_scopes(s,{i:scopes[i] for i in ids},objects),scopes,{'objects':objects},identity_only=True)
    if prior is None:
        source_records,record_reviews,record_limits=SR.extract(session,objects)
    else:
        source_records,record_reviews,record_limits=copy.deepcopy(old['source_records']),copy.deepcopy(old_reviews['source_records']),copy.deepcopy(old['source_record_limitations'])
        if plan:
            affected_records=set(plan['record_ids'])|{i for i,r in source_records.items() if set(r['actors']+r['properties']+[r['source_owner'],r['court']]+[x['object_id'] for x in r['participant_roles']])&changed_objects}
            if affected_records or plan['source_omissions']:
                source_records,record_reviews,lineage=SR.repair(session,source_records,record_reviews,objects,affected_records,session.feedback,plan['source_omissions'])
                save(session.dest/'source-record-repair-lineage.json',{'records':lineage,'old_proposal_hash':digest(old),'full_python_recompute':True,'unaffected_reviews_are_reused_not_new_reviews':True})
                changed_records=affected_records|set(source_records)-set(old['source_records'])
                session.repair_task_ids.update(u['task_id'] for u in old['uses'].values() if set(u.get('source_record_ids',[]))&changed_records)
        elif session.record_repair is not None:source_records,record_reviews=session.record_repair
    record_acceptance=SR.qualify(s,source_records,record_reviews)
    if prior is not None and source_records==old['source_records'] and record_reviews==old_reviews['source_records'] and old.get('source_record_coverage'):
        source_coverage=copy.deepcopy(old['source_record_coverage'])
    else:source_coverage=SR.assess_coverage(session,source_records,record_reviews)
    session.current_records=source_records;session.current_record_acceptance=record_acceptance
    scoped_tasks={tid for tid,t in old.get('tasks',{}).items() if t['scope_id'] in changed_scopes or changed_objects and t.get('source_owner') in changed_objects}
    session.repair_task_ids.update(scoped_tasks)
    if plan and set(repair_targets)&{'OBJECTS','SCOPES'}:scoped_tasks.update(session.repair_task_ids)
    if (plan and 'TASKS' not in repair_targets) or reuse('TASKS'):
        tasks=copy.deepcopy(old['tasks']);aliases=copy.deepcopy(old['task_aliases'])
        inventory=copy.deepcopy(old['source_inventory'])
        raw_task={'coverage_limitations':copy.deepcopy(old['coverage_limitations'])}
        task_reviews=copy.deepcopy(old_reviews['tasks']);retrieval=copy.deepcopy(prior['retrieval'])
        if scoped_tasks:
            owner_patch=session.ask('task-owners-patch',
                'Reassess the source-owner restriction of each addressed question from originals and the current identity registry. NONE is appropriate for an open question with no fixed speaker. Do not change its proposition, scope, role or frozen rule. No corrected owner is supplied by the program.',
                C.keyed(scoped_tasks,C.obj({'source_owner':C.enum(C.speakers(objects)+['NONE','UNRESOLVED']),'reason':C.text(200)})),
                {'subjects':{i:tasks[i] for i in scoped_tasks},'objects':objects,'scopes':scopes,'source_linked_repair':session.feedback})
            for tid,row in owner_patch.items():tasks[tid]={**tasks[tid],'source_owner':row['source_owner']}
            task_reviews.update(session.review_batches('task-review',P.REVIEW_TASKS,lambda ids:C.review_tasks(s,ids),{i:tasks[i] for i in scoped_tasks},{'scopes':scopes,'objects':objects}))
        if changed_scopes or changed_objects:
            expanded,_=screen_rule_questions(session,list(tasks.values()),scopes)
            # Registry patches preserve existing task addresses. Content hashes
            # and reviews change, not the IDs used by paths/inventory/retrieval.
            expanded_rows={i:expanded[n] for n,i in enumerate(tasks)}
            expanded_rows.update(mint(expanded[len(tasks):],'T'))
            added_ids=set(expanded_rows)-set(tasks);tasks=expanded_rows
            session.repair_task_ids.update(added_ids);scoped_tasks.update(added_ids)
            task_reviews.update(session.review_batches('task-review-screen',P.REVIEW_TASKS,lambda ids:C.review_tasks(s,ids),
                {i:tasks[i] for i in added_ids},{'scopes':scopes,'objects':objects}))
        else:session.rule_screen=copy.deepcopy(old.get('rule_screen',{}))
        analogies=copy.deepcopy(old.get('analogies',{}));analogy_reviews=copy.deepcopy(old_reviews.get('analogies',{}))
        session.focus=retrieval['selected_ids'];session.history_focus=retrieval['history_selected_ids']
        if scoped_tasks or changed_objects or source_records!=old.get('source_records') or record_reviews!=old_reviews.get('source_records'):
            # Historical readings remain cached; comparison/review uses the new scope and object versions.
            analogies,analogy_reviews=assess_history(session,tasks,scopes,retrieval)
        save(session.dest/(session.prefix+'retrieval-ledger.json'),retrieval)
    else:
        raw_task=make_tasks(session,'tasks',objects,scopes,omissions)
        inventory=raw_task['inventory']
        tasks=mint(raw_task['tasks'],'T')
        tasks,aliases=consolidate_tasks(session,tasks,scopes)
        task_reviews=session.review_batches('task-review',P.REVIEW_TASKS,lambda ids:C.review_tasks(s,ids),tasks,{'scopes':scopes,'objects':objects})
        query_plan=session.ask('retrieval-queries',HC.NEEDS_PROMPT,HC.queries_schema(s,tasks),{'tasks':tasks,'scopes':scopes})
        needs=HC.needs_from(query_plan,tasks,s)
        retrieval=retrieve(s,tasks,cfg['rag_top_k'],query_plan['case_law_queries'],scopes,history_budget(session),needs,cfg)
        retrieval['model_coverage_limits']=query_plan['history_coverage_limits'];session.focus=retrieval['selected_ids']
        session.history_focus=retrieval['history_selected_ids']
        save(session.dest/(session.prefix+'retrieval-plan.json'),retrieval)
        try:
            analogies,analogy_reviews=assess_history(session,tasks,scopes,retrieval)
        finally:
            save(session.dest/(session.prefix+'retrieval-ledger.json'),retrieval)
    current_dependencies={'objects':objects,'scopes':scopes,'tasks':tasks,'source_records':source_records}
    current_reviews={'objects':object_reviews,'scopes':scope_reviews,'tasks':task_reviews,'source_records':record_reviews}
    dependencies_changed=prior is not None and any(old.get(k)!=v or old_reviews.get(k)!=current_reviews[k] for k,v in current_dependencies.items())
    if reuse('USES') and not session.repair_task_ids and not dependencies_changed:
        uses=copy.deepcopy(old['uses']);use_reviews=copy.deepcopy(old_reviews['uses'])
        bundles=copy.deepcopy(old['bundles']);bundle_reviews=copy.deepcopy(old_reviews['bundles'])
    else:
        affected=(session.repair_task_ids & set(tasks)) if plan and 'TASKS' not in repair_targets else session.repair_task_ids if prior is not None and earliest==order['USES'] else set(tasks)
        # Rebuild the dependent evidence transaction when any registry or its
        # review version changes. Old task IDs are not "unaffected" new tasks.
        if dependencies_changed:affected=set(tasks)
        active_tasks={i:t for i,t in tasks.items() if i in affected}
        uses,retained_bundles=retain_evidence(old,tasks,source_records,affected)
        if prior is not None:
            save(session.dest/'repair-evidence-invalidation.json',{'dependency_versions_changed':dependencies_changed,
                'removed_task_ids':sorted(set(old['tasks'])-set(tasks)),
                'invalidated_use_ids':sorted(set(old.get('uses',{}))-set(uses)),
                'invalidated_bundle_ids':sorted(set(old.get('bundles',{}))-set(retained_bundles)),
                'retained_use_ids':sorted(uses),'retained_bundle_ids':sorted(retained_bundles),
                'new_assessments_required':True,'semantic_answers_supplied':False})
        retained_use_reviews={i:copy.deepcopy(old_reviews['uses'][i]) for i in uses}
        remaining=cfg['max_total_uses']-len(uses)
        individual_caps={i:plan['use_caps'].get(i,cfg['max_uses_per_task']) if plan and 'TASKS' not in repair_targets else cfg['max_uses_per_task'] for i in active_tasks}
        remaining=min(remaining,sum(individual_caps.values()))
        allocation=session.ask('use-allocation',P.USE_ALLOCATION,C.obj({'slots':C.arr(C.enum(active_tasks),remaining),
            'limitations':C.arr(C.text(180),8)}),{'tasks':active_tasks,'source_records':source_records,
            'source_record_acceptance':record_acceptance,'maximum_total_uses':remaining,'maximum_by_task':individual_caps}) if active_tasks else {'slots':[],'limitations':[]}
        use_caps={tid:allocation['slots'].count(tid) for tid in active_tasks}
        if any(n>individual_caps[i] for i,n in use_caps.items()):raise ResourceStop('USE_ALLOCATION_PER_TASK_CAP_NO_TRUNCATION')
        save(session.dest/(session.prefix+'use-capacity.json'),{'caps':use_caps,'unallocated_tasks':[i for i,n in use_caps.items() if not n],
            'limitations':allocation['limitations'],'not_coverage_acceptance':True})
        # No generated use is discarded to satisfy this prior model allocation.
        for i in range(0,len(active_tasks),cfg['review_batch_size']):
            ts=dict(list(active_tasks.items())[i:i+cfg['review_batch_size']])
            use_cfg=dict(cfg);use_cfg['source_record_ids']=list(source_records);use_cfg['source_records']=source_records
            use_cfg['per_task_use_caps']={tid:use_caps[tid] for tid in ts}
            raw_uses=session.ask(f'uses-{i}',P.USES,C.uses(s,ts,use_cfg,objects),{'tasks':ts,'objects':objects,'scopes':scopes,'source_records':source_records,'source_record_acceptance':record_acceptance,'retrieval':retrieval_for_report(retrieval),'source_linked_repair':feedback_for_stage(session.feedback,'USES')})
            for tid,row in raw_uses.items():uses.update(mint([{**u,'task_id':tid} for u in row['uses']],'U'))
        use_reviews={**retained_use_reviews,**session.review_batches('use-review',P.REVIEW_USES,lambda ids:C.review_uses(s,ids,objects,uses,source_records,scopes,tasks),{i:u for i,u in uses.items() if u['task_id'] in affected},{'tasks':tasks,'scopes':scopes,'objects':objects,'source_records':source_records})}
        bundles=retained_bundles
        retained_bundle_reviews={i:copy.deepcopy(old_reviews['bundles'][i]) for i in bundles}
        for i in range(0,len(active_tasks),cfg['review_batch_size']):
            ts=dict(list(active_tasks.items())[i:i+cfg['review_batch_size']]);us={k:u for k,u in uses.items() if u['task_id'] in ts}
            raw_bundles=session.ask(f'bundles-{i}',P.BUNDLES,C.bundles(s,ts,us,cfg),{'tasks':ts,'uses':us,'scopes':scopes})
            for tid,row in raw_bundles.items():bundles.update(mint([{**b,'task_id':tid} for b in row['bundles']],'B'))
        bundle_reviews={**retained_bundle_reviews,**session.review_batches('bundle-review',P.REVIEW_BUNDLES,lambda ids:C.review_bundles(s,ids),{i:b for i,b in bundles.items() if b['task_id'] in affected},{'uses':uses,'tasks':tasks,'scopes':scopes})}
    mapping_reused=prior is not None and not (set(repair_targets)&{'OBJECTS','SCOPES','TASKS','RULE_MAPPING'})
    if mapping_reused:
        # These declarations read unchanged raw sources/tasks/scopes/rules, not
        # source-use judgments. Python still fully recomputes their truth/gates.
        applications=copy.deepcopy(old['applications']);app_reviews=copy.deepcopy(old_reviews['applications'])
        paths=copy.deepcopy(old['paths']);path_reviews=copy.deepcopy(old_reviews['paths'])
        burdens=copy.deepcopy(old['burdens']);burden_reviews=copy.deepcopy(old_reviews['burdens'])
        requests=copy.deepcopy(old['requests']);request_reviews=copy.deepcopy(old_reviews['requests'])
        raw_paths={'search_complete':old['search_complete'],'unrepresented_paths':old['unrepresented_paths']}
        reused.append('UNCHANGED_SOURCE_BOUND_RULE_AND_PATH_DECLARATIONS')
    else:
        app_schema=C.applications(s,tasks,scopes,s['rule_library']);applications={};app_reviews={};rules={r['id']:r for r in s['rule_library']['rules']}
        if len(app_schema['properties'])>cfg['max_applications']:raise ResourceStop('DECLARED_APPLICATION_CAP')
        for i in range(0,len(app_schema['properties']),cfg['review_batch_size']):
            props=dict(list(app_schema['properties'].items())[i:i+cfg['review_batch_size']])
            part=session.ask(f'applications-{i}',P.APPLICATIONS,C.obj(props),{'tasks':tasks,'scopes':scopes,'source_linked_repair':feedback_for_stage(session.feedback,'RULE_MAPPING')})
            applications.update(part)
        if applications:
            def review_schema(ids):
                return C.keyed(ids,lambda ident:C.obj({**{k:C.decision(s) for k in ('scope','mapping','time')},
                    **{'date:'+pred:C.decision(s,'CASE') for pred in rules[tasks[ident]['rule_id']].get('date_constraints',{})}}))
            app_reviews=session.review_batches('application-review',P.REVIEW_APPLICATIONS,review_schema,applications,{'tasks':tasks,'scopes':scopes})
        raw_paths=session.ask('paths',P.PATHS,C.paths(s,tasks,scopes,cfg),{'tasks':tasks,'scopes':scopes,'applications':applications,
            'mapping_boundary':'Map declared task relationships using raw CASE and LAW only. Current use judgments and historical comparisons are evaluated downstream; they cannot create rules.'})
        paths=mint(raw_paths['paths'],'P')
        path_reviews=session.review_batches('path-review',P.REVIEW_PATHS,lambda ids:C.keyed(ids,C.decision(s)),paths,{'tasks':tasks,'scopes':scopes,'applications':applications})
        raw_burden=session.ask('burdens',P.BURDENS,C.burdens(s,tasks,scopes,objects,cfg),{'tasks':tasks,'scopes':scopes,'objects':objects})
        burdens=mint(raw_burden['burdens'],'D')
        burden_reviews=session.review_batches('burden-review',P.REVIEW_MAPPINGS,lambda ids:C.legal_mapping_reviews(s,ids),burdens,{'tasks':tasks,'scopes':scopes,'objects':objects})
        raw_requests=session.ask('requests',P.REQUESTS,C.requests(s,tasks,scopes,paths,burdens,cfg),{'tasks':tasks,'scopes':scopes,'paths':paths,'burdens':burdens})
        requests=mint(raw_requests['requests'],'R')
        request_reviews=session.review_batches('request-review',P.REVIEW_MAPPINGS,lambda ids:C.legal_mapping_reviews(s,ids),requests,{'tasks':tasks,'scopes':scopes,'paths':paths,'burdens':burdens})
    proposal={'source_records':source_records,'source_record_limitations':record_limits,'objects':objects,'scopes':scopes,'tasks':tasks,'uses':uses,'bundles':bundles,'applications':applications,'paths':paths,
        'rule_screen':session.rule_screen,
        'search_complete':raw_paths['search_complete'],'unrepresented_paths':raw_paths['unrepresented_paths'],
        'burdens':burdens,'requests':requests,'analogies':analogies,'task_aliases':aliases,'retrieval':retrieval,'source_inventory':inventory,
        'coverage_limitations':raw_task['coverage_limitations'],'object_limitations':raw['unresolved']}
    values={'source_records':record_reviews,'objects':object_reviews,'scopes':scope_reviews,'tasks':task_reviews,'uses':use_reviews,'bundles':bundle_reviews,'applications':app_reviews,'paths':path_reviews,'burdens':burden_reviews,'requests':request_reviews,'analogies':analogy_reviews}
    proposal.update(source_original_reading=original_reading,source_record_coverage=source_coverage)
    E.validate_dependencies(proposal)
    if prior is not None:
        save(session.dest/'repair-reuse.json',{'parent_proposal_hash':digest(old),'parent_review_hash':digest(prior['reviews']),
            'parent_snapshot_id':s['snapshot_id'],'repair_targets':sorted(repair_targets),'reused_stages':reused,
            'reused_are_unchanged_prior_reviews_not_fresh_acceptances':True,
            'new_review_groups':[g for g in values if values[g]!=old_reviews.get(g)]})
    reviews=E.envelope(s,proposal,values)
    shared={'snapshot_id':s['snapshot_id'],'proposal':proposal,'reviews':reviews,'retrieval':retrieval,'receipts':copy.deepcopy(session.receipts),
        'origin':session.provider.kind,'implementation_hash':cfg.get('implementation_hash'),'model_revision':cfg['local_revision'],'parameters':cfg['parameters'],'quality_score':None,'model_proposed_not_reference':True}
    save(session.dest/(session.prefix+'shared.json'),shared)
    session.shared=shared
    return shared


def finish(session,p,analysis,accepted=None,computed=None,revision_start=0):
    supports=list(p['uses'])+list(p['bundles'])+list(p['paths'])+list(p.get('requests',{}))+list(p.get('analogies',{}))
    if accepted is None:raise ValueError('V14_ENTRY_IS_PROJECT_C_ONLY_BASELINE_A0_REMAINS_SEPARATE')
    schema=RC.selection_schema(session.s,p,accepted,computed)
    material={'objects':p['objects'],'scopes':p['scopes'],'tasks':p['tasks'],'fallible_analysis':analysis,
        'support_registry_ids':supports,'authority_boundary':'Use original sources. Program traces are not legal authority.',
        'comparison_registry':{i:{k:h[k] for k in ('history_refs','case_refs','authority_refs')} for i,h in p.get('analogies',{}).items()},
        'revision_feedback':session.feedback}
    material['reviewed_record_catalog']=RC.catalog(session.s,p,accepted,computed)
    material['comparison_registry']={i:{**h,'report_eligible':accepted['analogies'][i]['report_eligible'],
        'eligibility_reasons':accepted['analogies'][i]['reasons'],'allowed_report_item_ids':RC.comparison_routes(p,h)}
        for i,h in p.get('analogies',{}).items()}
    material['report_dependencies']=RC.report_dependencies(p)
    material['eligible_record_routes']=RC.eligible_records(p,material['reviewed_record_catalog'])
    material['source_inventory']=p['source_inventory']
    material.pop('fallible_analysis',None)
    material['computation_limits']={k:computed.get(k) for k in ('rule_coverage','task_states','rules','paths','requests','conditional_not_actual')}
    selection=session.ask('report',P.REPORT_SELECTION,schema,material)
    report=RC.compile_report(session.s,p,session.shared['reviews'],accepted,computed,selection)
    save(session.dest/(session.prefix+'report-selection.json'),selection)
    checks=[];unchanged_review=None;revision_effect=None
    for revision in range(revision_start,session.cfg['max_report_revisions']+1):
        review=unchanged_review if unchanged_review is not None else final_review(session,p,report,revision)
        review_reused=unchanged_review is not None;unchanged_review=None
        check=E.check_report(session.s,p,report,review,accepted,computed,session.shared['reviews']);checks.append(check)
        save(session.dest/'reports'/f'{session.prefix}{revision}.json',{'report':report,'review':review,'check':check,'exact_unchanged_report_review_reused':review_reused})
        if check['internal_pass'] or revision==session.cfg['max_report_revisions']:break
        omissions=actionable_omissions(review['whole_source_coverage'],session.s)
        correctable={i:v for i,v in {**review['items'],**review.get('comparisons',{})}.items() if v.get('revision_class')=='ALLOWED_SOURCE_ERROR' and refs_valid(v.get('revision_refs',[]),session.s)}
        mechanical=[p for p in check['problems'] if any(r not in ('FINAL_SOURCE_REVIEW_NOT_ACCEPTED','COVERAGE_CLASSIFICATION_INCONSISTENT') for r in p['reasons'])]
        save(session.dest/'reports'/f'{session.prefix}{revision}-revision-routing.json',{'actionable':omissions,'correctable_items':correctable,'mechanical_errors':mechanical,'all_model_classifications':review['whole_source_coverage']['omissions'],'classification_consistent':coverage_consistent(review['whole_source_coverage'],session.s),'semantic_judgments_not_filled_by_program':True})
        mechanical_upstream=E.mechanical_repair_questions(session.s,p,accepted,check,review)
        if not omissions and not correctable and not mechanical and not mechanical_upstream:break
        plan=RP.repair_plan(session,p,report,review,correctable,omissions,mechanical_upstream)
        if plan['targets'] and session.s['namespace']=='ACTUAL':
            reason=RP.reserve(session,RP.repair_caps(session,p,set(plan['targets']),set(plan['affected_tasks']),plan),'complete-dependency-ordered-repair',optional=True)
            save(session.dest/'repair-plan.json',{**plan,'reservation_reason':reason,'no_semantic_answers_supplied':True})
            if reason:
                save(session.dest/'repair-budget-stop.json',{'reason':reason,'targets':plan['targets'],'draft_preserved':True,'no_rebuild_dispatched':True})
                revision_effect={'route':'REPAIR_NOT_DISPATCHED_BUDGET','content_changed':False,'reason':reason};break
            session.feedback=revision_feedback(report,review,check,p)
            session.feedback['initial_source_record_reviews']=copy.deepcopy(session.shared['reviews']['values']['source_records'])
            session.feedback['mechanical_source_questions']=mechanical_upstream
            save(session.dest/'revision-feedback.json',session.feedback)
            session.repair_task_ids=set(plan['affected_tasks']);session.repair_plan=plan;session.prefix='repair-'
            old_report=report
            result=project(session,prior=session.shared,repair_targets=set(plan['targets']),omissions=omissions,revision_start=1)
            after=read(session.dest/'final-report.json')
            result['revision_effect']={'route':'DEPENDENCY_ORDERED_ONCE','content_changed':report_content(old_report)!=report_content(after),
                'old_hash':digest(old_report),'new_hash':digest(after),'not_independent_quality_improvement':True}
            save(session.dest/'revision-effect.json',result['revision_effect'])
            return result
        # One bounded WHOLE REPORT revision. No repaired intermediates/acceptances.
        prior=report
        reason=RP.reserve(session,RP.final_caps(session.cfg,True),'complete-report-revision-suffix',optional=True)
        if reason:
            revision_effect={'route':'REPAIR_NOT_DISPATCHED_BUDGET','content_changed':False,'reason':reason};break
        selection=session.ask('report-revision',P.REPORT_SELECTION,schema,{**material,'revision_feedback':revision_feedback(report,review,check,p)})
        report=RC.compile_report(session.s,p,session.shared['reviews'],accepted,computed,selection)
        save(session.dest/'report-revision-selection.json',selection)
        revision_effect={'route':'REPORT_ONCE','content_changed':report_content(prior)!=report_content(report),
            'old_hash':digest(prior),'new_hash':digest(report),'not_independent_quality_improvement':True}
        save(session.dest/'revision-effect.json',revision_effect)
        if report==prior:unchanged_review=review
    if p.get('retrieval'):
        ranked=set(p['retrieval']['selected_ids']);used={r for u in p['uses'].values() for r in u['refs']}
        cited={r for item in list(report['items'].values())+list(report.get('comparisons',{}).values()) if item['include'] for r in item['refs']}
        save(session.dest/'retrieval-utilization.json',{'ranked_ids':sorted(ranked),'use_ids':sorted(used),'report_ids':sorted(cited),
            'used_outside_rank':sorted(used-ranked),'ranked_not_reported':sorted(ranked-cited),
            'critical_retrieval_recall':None,'reason':'No held-out critical-source reference; missing vs misread requires final source adjudication.'})
    lineage={}
    for rid,record in p.get('source_records',{}).items():
        lineage[rid]={'record_hash':digest(record),'source_refs':record['refs'],
            'source_hashes':{i:session.s['directory'][i]['text_hash'] for i in record['refs']},
            'review_hash':digest(session.shared['reviews']['values'].get('source_records',{}).get(rid,{})),
            'eligibility':accepted.get('source_records',{}).get(rid),
            'dependent_uses':[uid for uid,u in p['uses'].items() if rid in u.get('source_record_ids',[])],
            'report_items':[tid for tid,item in report['items'].items() if rid in item['support_ids']]}
    save(session.dest/'source-report-lineage.json',{'snapshot_id':session.s['snapshot_id'],'records':lineage,'all_model_request_hashes':[r.get('pipeline_request_hash') for r in session.receipts],'semantic_quality':None})
    save(session.dest/'final-report.json',report)
    path=session.dest/'final-report.txt'
    if path.exists():raise ValueError('FINAL_REPORT_ALREADY_EXISTS')
    path.write_text(render_text(report))
    partial=bool(session.history_failures)
    save(session.dest/'pipeline-completeness.json',{'core_chain_complete':True,'history_failures':session.history_failures,
        'full_chain_complete':not partial,'quality_score':None,'no_failed_history_used':True})
    return {'candidate_available':any(x['include'] for x in report['items'].values()),'complete_chain':not partial,'core_chain_complete':True,
        'internal_pass':checks[-1]['internal_pass'],'independent_quality_score':None,'report_hash':digest(report),
        'stop_reason':'PARTIAL_REPORT_HISTORY_FAILURE' if partial else 'INTERNAL_PASS_NOT_INDEPENDENT_ACCEPTANCE' if checks[-1]['internal_pass'] else 'REPAIR_NOT_DISPATCHED_BUDGET' if revision_effect and revision_effect['route']=='REPAIR_NOT_DISPATCHED_BUDGET' else 'REVISION_NO_CONTENT_CHANGE' if revision_effect and not revision_effect['content_changed'] else 'BOUNDED_REPORT_REVIEW_FINISHED',
        'revision_effect':revision_effect,'check':checks[-1],'legal_approval':False}


def project(session,shared=None,revoked=(),omissions=None,revision_start=0,prior=None,repair_targets=()):
    shared=shared or build_shared(session,omissions,prior,repair_targets)
    if shared['snapshot_id']!=session.s['snapshot_id']:raise ValueError('SHARED_SOURCE_VIEW_MISMATCH')
    if shared.get('implementation_hash')!=session.cfg.get('implementation_hash') or shared.get('parameters')!=session.cfg['parameters'] or shared.get('model_revision')!=session.cfg['local_revision']:raise ValueError('SHARED_METHOD_OR_MODEL_VERSION_MISMATCH')
    ensure_coverage(session)
    session.shared=shared
    p=shared['proposal'];reviews=shared['reviews']
    session.history_focus=shared.get('retrieval',{}).get('history_selected_ids',[])
    session.focus=shared.get('retrieval',{}).get('selected_ids',[])
    semantic_inputs=json.dumps({'uses':p['uses'],'bundles':p['bundles'],'applications':p['applications'],
        'paths':p['paths'],'analogies':p.get('analogies',{}),'burdens':p.get('burdens',{}),'requests':p.get('requests',{}),'model_reviews':reviews['values']},ensure_ascii=False,separators=(',',':'))
    if session.arm=='B':
        analysis={'same_model_information':semantic_inputs,
            'policy':'Reason over the same fallible information without program derivation. Read originals and disagree when warranted.'}
        return finish(session,p,analysis,revision_start=revision_start)
    session.revoked.update(revoked)
    accepted=E.inspect(session.s,p,reviews,session.revoked)
    computed=E.compute(session.s,p,reviews,accepted,session.cfg)
    save(session.dest/(session.prefix+'computation.json'),{'accepted':accepted,'computed':computed,'proposal_hash':digest(p),'snapshot_id':session.s['snapshot_id']})
    report_inputs={'qualified_source_uses':{i:u for i,u in p['uses'].items() if accepted['uses'][i]['report_eligible']},
        'qualified_comparisons':{i:h for i,h in p.get('analogies',{}).items() if accepted['analogies'][i]['report_eligible']},
        'compact_computation':E.compact(p,accepted,computed),
        'rejected_use_diagnostics':{i:{'task_id':u['task_id'],'reasons':u.get('report_reasons',[])} for i,u in accepted['uses'].items() if not u['report_eligible']}}
    return finish(session,p,report_inputs,accepted,computed,revision_start)


def history_budget(session):
    size=sum(len(x['text']) for x in session.s['directory'].values() if x['domain']!='HISTORY')
    limit=session.cfg['source_window_chars']
    return min(session.cfg.get('history_window_chars',20000), max(0,limit-size)) if size<=limit else session.cfg.get('history_window_chars',20000)


def assess_history(session,tasks,scopes,retrieval):
    return HC.assess(session,tasks,scopes,retrieval)


def screen_rule_questions(session,rows,scopes):
    """Evaluate public frozen rule candidates; no rule applicability is filled in."""
    rules={r['id']:r for r in session.s['rule_library']['rules']}
    obligation_ids=sorted({o for t in rows if t.get('role','REPORT')=='REPORT' for o in t.get('obligation_ids',[])})
    schema=C.keyed(rules,C.obj({'assessment':C.enum(['ASSESS_CONDITIONS','NOT_APPLICABLE','LAW_INSUFFICIENT','UNRESOLVED']),
        'report_obligation_ids':C.picks(obligation_ids,len(obligation_ids)),
        'scope_ids':C.picks(scopes,len(scopes)), 'case_refs':C.picks(C.source_refs(session.s,'CASE'),8),
        'law_refs':C.picks(C.source_refs(session.s,'LAW'),8),'reason':C.text(200)}))
    judged=session.ask('rule-screen',
        'Review every frozen rule candidate against the original question, report obligations, CASE and supplied LAW. Explicitly distinguish rules worth assessing by their conditions from rules outside this case, missing historical authority, and unresolved applicability. Selecting ASSESS_CONDITIONS does not establish the rule, any premise, or a remedy. Identify the exact relevant scopes and source references. Do not map a later statute to an earlier event without supported temporal applicability. Do not choose NONE silently or invent rules for missing law.',schema,
        {'report_questions':[t for t in rows if t.get('role','REPORT')=='REPORT'],'scopes':scopes,'frozen_rule_candidates':rules}) if rules else {}
    session.rule_screen=judged
    selected={(rid,sid) for rid,v in judged.items() if v['assessment']=='ASSESS_CONDITIONS' for sid in v['scope_ids']}
    result=copy.deepcopy(rows);added=[]
    for rid,sid in sorted(selected):
        if any(t['kind']=='DERIVED' and t['rule_id']==rid and t['scope_id']==sid for t in result):continue
        r=rules[rid];assessment=judged[rid]
        effect='CONTROLLING_GATE' if r.get('effect') in ('PROCEDURAL_GATE','EVIDENCE_GATE') else 'CONTROLLING_BAR' if r.get('effect') in ('PROCEDURAL_BAR','SUBSTANTIVE_BAR','GUARD') else 'SUPPORT'
        task={'proposition':'Under this scope, does frozen rule '+rid+' establish: '+r['consequence'],
            'scope_id':sid,'kind':'DERIVED','rule_id':rid,'role':'PROOF','rule_condition':'NONE','source_owner':'NONE',
            'effect':effect,'section':'GROUND','importance':'CONTEXT','burden_holder':'UNRESOLVED',
            'standard':r.get('scope','Scope requires model review'),'authority_refs':assessment['law_refs'],
            'question_basis_refs':assessment['case_refs'],'why_required':'Model selected frozen rule for condition assessment, not acceptance',
            'question_origin':'MODEL_SCREENED_FROZEN_RULE_QUESTION','obligation_ids':[],
            'informs_obligation_ids':assessment['report_obligation_ids']}
        result.append(task);added.append(task)
    result,conditions=complete_rule_questions(result,session.s,session.cfg['max_tasks'],selected)
    for t in result:t.setdefault('obligation_ids',[])
    save(session.dest/(session.prefix+'rule-screen.json'),{'dispositions':judged,'selected_rule_scopes':sorted(selected),
        'created_rule_questions':added,'created_condition_questions':conditions,'no_premise_or_applicability_answers_supplied':True})
    return result,added+conditions


def make_tasks(session,tag,objects,scopes,omissions=None,analysis=None):
    """Model chooses cardinality before prose; no max-length array to pad.

    Counts are not legal truth. All generated rows and exact duplicates remain
    auditable. Exact copies share one content-addressed obligation; semantically
    different bindings, standards, sections or adverse positions never auto-merge.
    """
    extra={'objects':objects,'scopes':scopes,'analysis':analysis,
           'source_linked_omission_questions':omissions or [],'coverage':session.coverage,
           'source_linked_repair':feedback_for_stage(session.feedback,'TASKS'),
           'previous_obligations':session.feedback.get('previous_obligations',{}) if session.feedback else {},
           'total_task_cap':session.cfg['max_tasks']}
    raw_inventory=session.ask(tag+'-inventory',P.SOURCE_INVENTORY,C.source_inventory(session.s,scopes,session.cfg),
        {'objects':objects,'scopes':scopes,'total_task_cap':session.cfg['max_tasks'],
         'source_linked_repair':feedback_for_stage(session.feedback,'TASKS')},identity_only=True)
    inventory_rows=[row for section in C.SECTIONS for row in raw_inventory['obligations'][section]]
    if len(inventory_rows)>session.cfg['max_tasks']-4:raise ResourceStop('INVENTORY_CAP_EXCEEDED_NO_TRUNCATION')
    inventory={**raw_inventory,'obligations':mint(inventory_rows,'Q')}
    save(session.dest/(session.prefix+'source-inventory.json'),inventory)
    schema=C.inventory_tasks(session.s,scopes,session.s['rule_library'],session.cfg,inventory,objects)
    raw=session.ask(tag,P.TASKS,schema,{**extra,'source_inventory':inventory})
    rows,created=screen_rule_questions(session,list(raw['tasks'].values()),scopes)
    for row in created:row['obligation_ids']=[]
    # complete_rule_questions returns distinct copies; add IDs to its output too.
    for row in rows:row.setdefault('obligation_ids',[])
    save(session.dest/(session.prefix+tag+'-rule-questions.json'),{'created_questions':created,'case_answers_supplied':False,'assessments_require_provider':True})
    unique=mint(rows,'T')
    save(session.dest/(session.prefix+tag+'-cardinality.json'),
         {'raw_count':len(raw['tasks']),'program_rule_question_count':len(created),'exact_unique_count':len(unique),
          'exact_duplicate_count':len(rows)-len(unique),'semantic_equivalence_not_inferred':True})
    return {'tasks':list(unique.values()),'inventory':inventory,
            'coverage_limitations':list(dict.fromkeys(raw_inventory['coverage_limitations']+raw['coverage_limitations']))}



def run_arm(provider,snapshot,cfg,dest,arm,shared=None,revoked=(),parent_snapshot=None):
    if arm not in ('C','C-H0'):raise ValueError('PROJECT_ENTRY_C_ONLY_BASELINE_A0_IS_SEPARATE')
    dest=Path(dest)
    if (dest/'outcome.json').exists() or (dest/'started.json').exists():raise ValueError('EXISTING_ATTEMPT_PRESERVED_NO_AUTO_RESUME')
    identity={'case_id':snapshot['case_id'],'version':VERSION,'snapshot_id':snapshot['snapshot_id'],'config_hash':digest(cfg),'arm':arm,'same_intermediate_shared':shared is not None}
    save(dest/'started.json',identity);session=Session(provider,snapshot,cfg,dest,arm)
    try:
        if snapshot['namespace']=='HYPOTHETICAL':
            if arm!='C' or parent_snapshot is None or shared is None:raise ValueError('HYPOTHETICAL_REQUIRES_C_AND_FROZEN_PARENT_SHARED')
            result=hypothetical(session,parent_snapshot,shared)
        else:result=project(session,shared,revoked)
    except Exception as exc:
        result={'candidate_available':False,'complete_chain':False,'answer':None,'independent_quality_score':None,
            **failure_details(exc),'error':str(exc),'error_type':type(exc).__name__}
    result.update(identity,elapsed_monotonic_seconds=time.monotonic()-session.started,receipt_count=len(session.receipts),
        execution_kind=provider.kind,paid_api_calls=sum(bool(r.get("api_dispatch")) for r in session.receipts),legal_approval=False,
        shared_resource_receipts=copy.deepcopy(shared['receipts']) if shared is not None else [])
    save(dest/'request-source-manifest.json',{'requests':session.request_manifest,'semantic_sufficiency_not_proven_by_visibility':True})
    save(dest/'outcome.json',result)
    from history_audit import write_usage
    write_usage(dest,snapshot,shared)
    return result


def ensure_coverage(session):
    if session.coverage is not None:return
    target_ids=[i for i,s in session.s['directory'].items() if s['domain']!='HISTORY']
    if sum(len(session.s['directory'][i]['text']) for i in target_ids)<=session.cfg['source_window_chars']:return
    rows=[]
    for n,ids in enumerate(batches(session.s,session.cfg['source_scan_chars'],target_ids)):
        row=session.ask('coverage-'+str(n),P.SCAN,C.scan(session.s,ids),source_ids=ids)
        if set(row['read_ids'])!=set(ids):raise ValueError('COVERAGE_CHUNK_NOT_READ')
        if any(not set(x['refs'])<=set(ids) for x in row['issues']):raise ValueError('COVERAGE_UNSEEN_REFERENCE')
        rows.append(row)
    session.coverage=rows
    save(session.dest/'coverage-ledger.json',{'source_snapshot':session.s['snapshot_id'],'batches':rows,'all_chunks_read':True,
        'not_semantic_completeness':True})

def consolidate_tasks(session,tasks,scopes):
    if len(tasks)<2:return tasks,{}
    groups=session.ask('task-equivalence',P.CONSOLIDATE,C.consolidate(tasks),{'tasks':tasks,'scopes':scopes})['groups']
    rows=mint(groups,'M');reviews=session.review_batches('merge-review',P.REVIEW_MERGES,lambda ids:C.keyed(ids,C.decision(session.s)),rows,{'tasks':tasks})
    aliases={};used=set()
    for ident,g in rows.items():
        canonical=g['canonical']; members=set(g['duplicates'])-{canonical};base=tasks[canonical]
        if canonical in used or members&used:continue
        fields=('scope_id','kind','rule_id','effect','burden_holder','standard','section','role','rule_condition','source_owner','obligation_ids')
        compatible=all(all(tasks[x][k]==base[k] for k in fields) and (tasks[x]['importance']!='IMPORTANT' or base['importance']=='IMPORTANT') for x in members)
        if compatible and __import__('common').review_ok(reviews[ident],session.s):
            aliases.update({x:canonical for x in members});used|=members|{canonical}
    save(session.dest/(session.prefix+'task-consolidation.json'),{'original_tasks':tasks,'proposals':rows,'reviews':reviews,'aliases':aliases})
    return {i:t for i,t in tasks.items() if i not in aliases},aliases

def final_review(session,p,report,revision):
    addresses={i:{k:t[k] for k in ('scope_id','section','importance')} for i,t in C.report_tasks(p['tasks']).items()}
    extra={'exact_report':report,'report_addresses':addresses,
        'objects':{i:{k:o[k] for k in ('name','kind','refs')} for i,o in p['objects'].items()},'scopes':p['scopes'],
        'source_inventory':p['source_inventory']}
    # No task propositions, expected conclusions, prior model reviews or analogy narratives.
    if session.coverage is None:
        raw=session.ask(f'final-review-{revision}',P.FINAL_REVIEW,C.report_review(session.s,p['tasks'],p.get('analogies',{}),p['objects'],report,p['source_inventory']),extra)
        raw['whole_source_coverage']['inventory_check']=RC.coverage_status(raw['whole_source_coverage'],report,p['source_inventory'],session.s)
        return derive_allowed_coverage(raw,session.s)
    raise ResourceStop('V14_WHOLE_SOURCE_FINAL_REVIEW_WINDOW_UNSUPPORTED_NO_TRUNCATION')


def hypothetical(session,parent,shared):
    if parent['namespace']!='ACTUAL' or shared['snapshot_id']!=parent['snapshot_id'] or session.s.get('parent')!=parent['snapshot_id']:
        raise ValueError('HYPOTHESIS_PARENT_MISMATCH')
    if shared.get('origin','').startswith('SYNTHETIC') and not session.provider.kind.startswith('SYNTHETIC'):
        raise ValueError('SYNTHETIC_PARENT_FORBIDDEN_IN_MODEL_RUN')
    if shared.get('implementation_hash')!=session.cfg.get('implementation_hash') or shared.get('model_revision')!=session.cfg['local_revision'] or shared.get('parameters')!=session.cfg['parameters']:raise ValueError('HYPOTHESIS_PARENT_CONFIG_MISMATCH')
    session.shared=shared
    session.history_focus=shared['retrieval']['history_selected_ids']
    session.focus=shared['retrieval']['selected_ids']
    p=shared['proposal'];reviews=shared['reviews'];a=E.inspect(parent,p,reviews)
    baseline=E.compute(parent,p,reviews,a,session.cfg)
    assumptions=session.s.get('assumptions',{})
    if not isinstance(assumptions,dict) or not assumptions:raise ValueError('EXPLICIT_TASK_ASSUMPTIONS_REQUIRED')
    for tid,state in assumptions.items():
        if tid not in p['tasks'] or baseline['task_states'][tid]!='UNKNOWN':raise ValueError('HYPOTHESIS_CANNOT_REPLACE_KNOWN_FACT')
        if not __import__('common').task_review_ok(reviews['values']['tasks'].get(tid,{}),parent,p['tasks'][tid]) or not a['scopes'].get(p['tasks'][tid]['scope_id']):
            raise ValueError('HYPOTHESIS_SCOPE_UNACCEPTED')
        # A rejected/unfinished assessment is not permission to flip contrary evidence.
        opposing=[u for u in p['uses'].values() if u['task_id']==tid and u['state'] in ('TRUE','FALSE','CONFLICTED')]
        if any(u['state']=='CONFLICTED' or u['state']!=state for u in opposing):raise ValueError('HYPOTHESIS_CONTRADICTS_RECORDED_EVIDENCE')
    computed=E.compute(parent,p,reviews,a,session.cfg,assumptions)
    computed.update(snapshot_id=session.s['snapshot_id'],parent_snapshot_id=parent['snapshot_id'],namespace='HYPOTHETICAL',conditional_not_actual=True)
    save(session.dest/'hypothetical-computation.json',{'computed':computed,'actual_baseline':baseline,'parent_shared_hash':digest(shared),
        'prior_acceptances_are_parent_evidence_not_new_reviews':True})
    ensure_coverage(session)
    analysis={'compact_computation':E.compact(p,a,computed),'explicit_assumptions':assumptions,
        'same_model_information':json.dumps({'uses':p['uses'],'paths':p['paths'],'requests':p.get('requests',{})},ensure_ascii=False,separators=(',',':')),
        'instructions':'This is a conditional branch. No actual new evidence or new acceptance of parent judgments.'}
    return finish(session,p,analysis,a,computed)
