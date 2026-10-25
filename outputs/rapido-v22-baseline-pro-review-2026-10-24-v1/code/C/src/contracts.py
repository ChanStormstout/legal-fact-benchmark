"""One schema for decoder and consumer; identifiers only from program registries."""
from common import source_refs, witness_registry, time_registry, SCOPE_FIELDS, SPEAKER_KINDS
from schema_contract import validate, loads
from object_contract import object_schema

def obj(p): return {'type': 'object', 'properties': p, 'required': list(p), 'additionalProperties': False}
def text(n=500, empty=False):
    # V8 optional-text minLength=0 was associated with all single-character reports.
    # Omitted report items now use the explicit OMITTED marker, never an empty string.
    # Six real V6 failures stalled immediately after a string reached maxLength.
    # Concision is an instruction, not a forced mid-sentence decoder boundary.
    # The same schema reaches decoder and validator; token/call budgets still apply.
    return {'type': 'string', 'minLength': 1,
        'description': f'Write a complete concise statement, normally within {n} characters. Finish the thought and close the string naturally; do not copy a long passage or pad.'}
def enum(v): return {'type': 'string', 'enum': list(v)}
def arr(s, hi=8, lo=0, unique=False): return {'type': 'array', 'items': s, 'minItems': lo, 'maxItems': hi, 'uniqueItems': unique}
def picks(ids, hi=8, lo=0): return arr(enum(ids) if ids else text(), hi if ids else 0, lo if ids else 0, True)
def boolean(): return {'type': 'boolean'}
def keyed(ids, schema): return obj({i: schema(i) if callable(schema) else schema for i in ids})
def decision(s, domain=None, capacity=6): return obj({'decision': enum(['ACCEPT','REJECT','UNRESOLVED']), 'reason': text(260), 'refs': picks(source_refs(s,domain),capacity)})
STATE = enum(['TRUE','FALSE','UNKNOWN','CONFLICTED'])
SECTIONS = ['SUMMARY','GROUND','COUNTERARGUMENT','LIMITATION']
PLAN_GROUPS = SECTIONS + ['PROOF']
KINDS = ['FACT','ATTRIBUTION','LEGAL','PROCEDURE','DERIVED']

# One model choice, deterministically expanded. Never change a semantic verdict.
USE_MODES = {}
for role,statuses,purposes in [
    ('ATTRIBUTION',['PARTY_CLAIM','COURT_RECORDED'],['REPORT_ASSERTION','PARTIAL_SUPPORT','PARTIAL_OPPOSITION','BACKGROUND']),
    ('OBSERVATION',['REPORTED_EVIDENCE','COURT_RECORDED'],['REPORT_ASSERTION','PARTIAL_SUPPORT','PARTIAL_OPPOSITION','BACKGROUND','ESTABLISH_OCCURRENCE','RECONSTRUCT_COURT_PREMISE']),
    ('LEGAL_ASSESSMENT',['REPORTED_EVIDENCE','COURT_RECORDED'],['REPORT_ASSERTION','PARTIAL_SUPPORT','PARTIAL_OPPOSITION','BACKGROUND']),
    ('VIEW_LIMIT',['LIMITATION'],['REPORT_ASSERTION','BACKGROUND']),
    ('HYPOTHESIS',['HYPOTHETICAL'],['REPORT_ASSERTION','BACKGROUND','PARTIAL_SUPPORT','PARTIAL_OPPOSITION'])]:
    for status in statuses:
        for purpose in purposes:
            USE_MODES[':'.join((role,status,purpose))]={'content_role':role,'status':status,'purpose':purpose}

def speakers(objects):
    return [i for i,o in (objects or {}).items() if o['kind'] in SPEAKER_KINDS]

def source_decision(s, domain=None):
    return obj({'source_meaning':text(320),'witnesses':arr(witness(s,domain),3),
        'reason':text(240),'refs':picks(source_refs(s,domain),12),
        'decision':enum(['ACCEPT','REJECT','UNRESOLVED'])})

def report_tasks(tasks):
    return {i:t for i,t in tasks.items() if t.get('role','REPORT')=='REPORT'}

def witness(s, domain=None):
    return obj({'span_id':enum(witness_registry(s,domain))})

def review_objects(s,ids):
    return keyed(ids,obj({'identity_witnesses':arr(witness(s,'CASE'),3),
        'observed_kind':enum(['PARTY','PERSON','COURT','ORGANIZATION','PROPERTY','EVENT','OTHER','UNRESOLVED']),
        'reason':text(260),'decision':enum(['ACCEPT','REJECT','UNRESOLVED'])}))

def objects(s,cfg):
    return obj({'objects': arr(object_schema(source_refs(s,'CASE'),text),cfg['max_objects']),
                'unresolved': arr(text(250),8)})

def scopes(s,objects,cfg):
    return obj({'scopes': arr(obj({'actors': picks([i for i,o in objects.items() if o['kind'] in ('PARTY','PERSON','ORGANIZATION')],8),
        'participant_roles':arr(obj({'object_id':enum(objects),'role':text(80),'witnesses':arr(witness(s,'CASE'),2,1)}),8),
        'properties': picks([i for i,o in objects.items() if o['kind']=='PROPERTY'],8), 'time_choice':enum(list(time_registry(s))+['UNKNOWN']), 'stage':text(160),
        'court': enum([i for i,o in objects.items() if o['kind']=='COURT']+['UNKNOWN']), 'request':text(350),
        'jurisdiction':text(120),'procedure':text(160),
        'record_level':enum(['CURRENT_PROCEEDING','PRIOR_PROCEEDING','PARTY_ACCOUNT','UNRESOLVED']),
        'refs': picks(source_refs(s,'CASE'),6,1)}),cfg['max_scopes'],1)})

def task_counts(cfg):
    return obj({'counts':obj({section:{'type':'integer','enum':list(range(0 if section=='PROOF' else 1,cfg['max_tasks']-2))} for section in PLAN_GROUPS}),
        'coverage_limitations':arr(text(260),8)})

def tasks(s,scopes,library,cfg,counts=None,objects=None):
    # A selected executable rule is a derivation request, never an unrelated LEGAL
    # label that silently prevents constructing its application. This binds a
    # question to a rule; applicability and every premise still require assessment.
    modes=[k+':NONE' for k in KINDS]+['DERIVED:'+r['id'] for r in library['rules']]
    item=obj({'proposition': {**text(450),'description':'An open question to assess from sources. Do not embed an assumed answer, speaker, court holding or legal effect in the question.'}, 'scope_id':enum(scopes), 'kind_rule':enum(modes),'role':enum(['REPORT','PROOF']),
        'source_owner':enum(speakers(objects)+['NONE','UNRESOLVED']),
        'rule_condition':enum(['NONE']+[r['id']+':'+p for r in library['rules'] for p in r['predicates']]),
        'effect':enum(['DESCRIPTIVE','SUPPORT','CONTROLLING_GATE','CONTROLLING_BAR','EXCEPTION']), 'section':enum(SECTIONS), 'importance':enum(['IMPORTANT','CONTEXT']), 'burden_holder':text(140),
        'standard':text(350), 'authority_refs':picks(source_refs(s,'LAW'),6),
        'question_basis_refs':picks(source_refs(s,'CASE'),6), 'why_required':text(240)})
    if counts is None:
        slots=arr(item,cfg['max_tasks'],1)
    else:
        if set(counts)!=set(PLAN_GROUPS) or any(int(n)<(0 if k=='PROOF' else 1) for k,n in counts.items()) or sum(int(n) for n in counts.values())>cfg['max_tasks']:
            raise ValueError('TASK_PLAN_EXCEEDS_FIXED_CAPACITY')
        slots=obj({section+'_'+str(n+1):obj({**item['properties'],
                    'section':enum(['GROUND' if section=='PROOF' else section]),
                    'role':enum(['PROOF' if section=='PROOF' else 'REPORT'])})
                   for section in PLAN_GROUPS for n in range(int(counts[section]))})
    return obj({'tasks':slots,'coverage_limitations':arr(text(260),8)})

def uses(s,tasks,cfg,objects=None):
    # Original wording, attribution and citations are selected once by record ID.
    # Model still assesses target-relative purpose/state, never a program default.
    choices=[rid+'|'+mode for rid,rec in cfg.get('source_records',{}).items()
             for mode,m in USE_MODES.items() if m['status']==rec['status'] and m['content_role']==rec['content_role']]
    return keyed(tasks, lambda tid: obj({'uses':arr(obj({
        'source_record_mode':enum(choices) if choices else text(),
        'state':STATE,'contribution':text(250),'limitations':arr(text(160),4)}),
        cfg.get('per_task_use_caps',{}).get(tid,cfg['max_uses_per_task']) if choices else 0)}))


def bundles(s,tasks,uses,cfg):
    def one(tid):
        ids=[i for i,u in uses.items() if u['task_id']==tid]
        return obj({'bundles':arr(obj({'use_ids':picks(ids,12,1),'state':STATE,
            'proof_status':enum(['SATISFIED','NOT_SATISFIED','UNRESOLVED','CONTESTED']),
            'complete':boolean(),'components':arr(obj({'condition':text(200),'use_ids':picks(ids,8,1),'covered':boolean()}),8),
            'missing':arr(text(220),8),'reason':text(500),'alternative_explanation':text(300),
            'counter_use_ids':picks(ids,12),'sufficiency_authority_refs':picks(source_refs(s,'LAW'),6),
            'origin_assessment':text(250)}),cfg['max_bundles_per_task'])})
    return keyed(tasks,one)

def applications(s,tasks,scopes,library):
    out={}
    rules={r['id']:r for r in library['rules']}
    for tid,t in tasks.items():
        if t['kind']!='DERIVED' or t['rule_id']=='NONE': continue
        rule=rules[t['rule_id']];sid=t['scope_id']
        same=[i for i,x in tasks.items() if x['scope_id']==sid and i!=tid and x['kind']!='ATTRIBUTION']
        out[tid]=obj({'selected':boolean(),'premises':keyed(rule['predicates'],lambda pred:enum(
            [i for i in same if tasks[i].get('rule_condition')==rule['id']+':'+pred]+['UNKNOWN'])),
            'applicability':enum(['APPLICABLE','INAPPLICABLE','UNRESOLVED']),
            'predicate_intervals':keyed(rule.get('date_constraints',{}),obj({'from':text(10),'to':text(10),'refs':picks(source_refs(s,'CASE'),4)})),
            'event_interval':obj({'from':text(10),'to':text(10),'refs':picks(source_refs(s,'CASE'),4)}),
            'reason':text(260)})
    return obj(out)

def paths(s,tasks,scopes,cfg):
    return obj({'paths':arr(obj({'name':text(200),'scope_id':enum(scopes),'conclusion_task':enum(tasks),
        'supports':picks(tasks,10),'alternatives':picks(tasks,10),
        'gates':picks(tasks,8),'blockers':picks(tasks,8),
        'exceptions':arr(obj({'blocker_task':enum(tasks),'exception_task':enum(tasks),'authority_refs':picks(source_refs(s,'LAW'),4,1)}),6),
        'authority_refs':picks(source_refs(s,'LAW'),6),'reason':text(350)}),cfg['max_paths']),
        'search_complete':boolean(),'unrepresented_paths':arr(text(240),8)})

def review_uses(s,ids,objects=None,uses=None,records=None,scopes=None,tasks=None):
    # Observed values are chosen by the reviewer, never echoed by the adapter.
    # Descriptive reporting and executable premise use have separate verdicts.
    attribution=obj({**source_decision(s,'CASE')['properties'],
        'observed_owner':enum(speakers(objects)+['NONE','UNDECLARED','UNRESOLVED','SOURCE_LOCAL_UNNAMED']),
        'observed_status':enum(['PARTY_CLAIM','COURT_RECORDED','REPORTED_EVIDENCE','LIMITATION','HYPOTHETICAL','UNRESOLVED']),
        'owner_relation':enum(['MATCH','MISMATCH','UNRESOLVED'])})
    binding=obj({**source_decision(s,'CASE')['properties'],
        'observed_actors':picks([i for i,o in (objects or {}).items() if o['kind'] in ('PARTY','PERSON','ORGANIZATION')],8),
        'observed_properties':picks([i for i,o in (objects or {}).items() if o['kind']=='PROPERTY'],8),
        'record_event':text(240),'scope_relation':enum(['MATCH','MISMATCH','UNRESOLVED'])})
    def one(uid):
        u=uses[uid];record=records[u['source_record_ids'][0]];scope=scopes[tasks[u['task_id']]['scope_id']]
        from common import digest
        dimensions=keyed(['actors','properties','time','procedure','court','request'],obj({
            'relation':enum(['MATCH','TRANSFER_SUPPORTED','NOT_REQUIRED','MISMATCH','UNRESOLVED']),
            'reason':text(160),'case_witnesses':arr(witness(s,'CASE'),2), 'law_witnesses':arr(witness(s,'LAW'),2)}))
        target_roles=[str(i) for i in range(len(scope['participant_roles']))]
        bridge=obj({'source_hash':enum([digest(record)]),'target_hash':enum([digest(scope)]),
            'dimensions':dimensions,
            'roles':keyed([str(i) for i in range(len(record['participant_roles']))],obj({
                'target_role':enum(target_roles+['NOT_REQUIRED','UNRESOLVED']),
                'decision':enum(['ACCEPT','REJECT','UNRESOLVED']),'reason':text(160),
                'witnesses':arr(witness(s,'CASE'),2)}))})
        return obj({'attribution':attribution,'binding':binding,'scope_bridge':bridge,
            'use':source_decision(s,'CASE'),'report':source_decision(s,'CASE')})
    return keyed(ids,one)

def review_bundles(s,ids):
    return keyed(ids,obj({k:decision(s) for k in ['alignment','binding','whole','counterevidence','standard']}))

def report(s,tasks,support_ids=(),analogies=None,objects=None,computed=None,accepted=None,uses=None):
    def eligible_uses(tid):
        return [i for i,v in (accepted or {}).get('uses',{}).items() if v['task_id']==tid and v['report_eligible']]
    def support_choices(tid):
        if accepted is None:return list(support_ids)
        return eligible_uses(tid)+[i for i,v in (computed or {}).get('paths',{}).items() if v['task_id']==tid and v['state']=='CONDITIONS_MET_IN_DECLARED_SCOPE']+[i for i,v in (computed or {}).get('requests',{}).items() if v['task_id']==tid]
    def kinds(tid):
        result=['ATTRIBUTED','FACTUAL','CONDITIONAL','DERIVED','UNKNOWN']
        if computed is not None:
            ready=any(p['task_id']==tid and p['state']=='CONDITIONS_MET_IN_DECLARED_SCOPE' for p in computed.get('paths',{}).values())
            ready=ready or any(p['task_id']==tid and p['outcome']!='UNRESOLVED' and not p['conditional'] for p in computed.get('requests',{}).values())
            if not ready:result.remove('DERIVED')
        if accepted is not None:
            qualified=[(uses or {})[i] for i in eligible_uses(tid)]
            if not qualified:result=[k for k in result if k not in ('ATTRIBUTED','FACTUAL')]
            elif not any(u['content_role']=='OBSERVATION' and u['status'] not in ('PARTY_CLAIM','HYPOTHETICAL','LIMITATION') for u in qualified):result.remove('FACTUAL')
        return result
    return obj({'items':keyed(report_tasks(tasks),lambda tid:obj({'include':boolean(),'section':enum([tasks[tid]['section']]),'text':text(1200,True),
        'kind':enum(kinds(tid)),
        'attributed_to':enum(list(dict.fromkeys([(uses or {})[i]['source_owner'] for i in eligible_uses(tid)]))+['NONE','UNRESOLVED'] if accepted is not None else speakers(objects)+['NONE','UNRESOLVED']),
        'consequence_scope':enum(['DESCRIPTION','LOCAL_ARGUMENT','REQUEST','REMEDY'] if computed is not None else ['DESCRIPTION','LOCAL_ARGUMENT','REQUEST','REMEDY','WHOLE_CASE']),
        'outcome':enum(['DESCRIPTION','SUPPORTED_IN_DECLARED_SCOPE','NOT_ESTABLISHED','PROCEDURALLY_UNAVAILABLE','BLOCKED','UNRESOLVED']),
        'refs':picks(source_refs(s,'CASE')+source_refs(s,'LAW'),18),'support_ids':picks(support_choices(tid),12)})),
        'comparisons':keyed(analogies or {},lambda hid:obj({
            'disposition':enum((['USED'] if accepted is None or accepted.get('analogies',{}).get(hid,{}).get('report_eligible') else [])+['NOT_RELEVANT','REDUNDANT','UNRESOLVED','REJECTED']),
            'text':text(900,True),
            'reason':text(300)}))})

REPAIR_TARGETS=['REPORT','OBJECTS','SCOPES','TASKS','SOURCE_RECORDS','USES','RULE_MAPPING','NO_ALLOWED_REPAIR']

OMISSION_CLASSES={
    'ACTIONABLE_ALLOWED_OMISSION':('ALLOWED_SOURCE_OMISSION','ALLOWED_RECORD'),
    'CORRECTABLE_ALLOWED_ERROR':('CORRECTABLE_ERROR','ALLOWED_RECORD'),
    'UNAVAILABLE_ALLOWED_RECORD':('UNAVAILABLE','ALLOWED_RECORD'),
    'UNAVAILABLE_HIDDEN_OUTCOME':('UNAVAILABLE','HIDDEN_TARGET_OUTCOME'),
    'UNAVAILABLE_HIDDEN_REASONING':('UNAVAILABLE','HIDDEN_TARGET_REASONING'),
    'UNAVAILABLE_OUTSIDE_SOURCES':('UNAVAILABLE','OUTSIDE_ALLOWED_SOURCES'),
    'PROHIBITED_HIDDEN_OUTCOME':('PROHIBITED','HIDDEN_TARGET_OUTCOME'),
    'PROHIBITED_HIDDEN_REASONING':('PROHIBITED','HIDDEN_TARGET_REASONING'),
    'PROHIBITED_OUTSIDE_SOURCES':('PROHIBITED','OUTSIDE_ALLOWED_SOURCES')}

def omission(s):
    return obj({'question':text(260),'refs':picks(source_refs(s),6),
        'importance':enum(['IMPORTANT','CONTEXT']),
        'finding_class':enum(OMISSION_CLASSES),'basis':text(300),
        'repair_target':enum(REPAIR_TARGETS)})


def review_scopes(s,rows,objects):
    registry=witness_registry(s,'CASE')
    def one(sid):
        source_ids=set(rows[sid]['refs'])
        source_ids.update(registry[w['span_id']]['ref'] for w in rows[sid].get('time_witnesses',[]))
        for oid in rows[sid]['actors']+rows[sid]['properties']+[rows[sid]['court']]:
            source_ids.update(objects.get(oid,{}).get('refs',[]))
        choices=[w for w,r in registry.items() if r['ref'] in source_ids]
        return obj({part:obj({'source_event':text(220),
            'witnesses':arr(obj({'span_id':enum(choices)}),4,1),
            'reason':text(260),'decision':enum(['ACCEPT','REJECT','UNRESOLVED']),
            **({'event_relation':enum(['MATCH','MISMATCH','UNRESOLVED']),
                'time_role':enum(['EVENT_DATE','CASE_IDENTIFIER_YEAR','OTHER_EVENT_DATE','UNKNOWN'])} if part=='time' else {})}) for part in SCOPE_FIELDS})
    return keyed(rows,one)


def review_analogies(s,rows):
    def one(hid):
        document=rows[hid]['document_id']
        view={**s,'directory':{i:r for i,r in s['directory'].items() if r['domain']!='HISTORY' or r['document_id']==document}}
        return obj({'history':source_decision(view,'HISTORY'), 'current':source_decision(view,'CASE'),
            'comparison':decision(view,capacity=24), 'law':decision(view,'LAW')})
    return keyed(rows,one)

def report_review(s,tasks,analogies=None,objects=None,report=None,inventory=None):
    from source_records import findings_schema
    item=obj({'body_meaning':text(400),'substantive_text':boolean(),
        'witnesses':arr(witness(s),3),'reviewed_refs':picks(source_refs(s),18),
        'reason':text(250),'serious_error':boolean(),
        'important_content_complete':boolean(),
        'revision_class':enum(['ALLOWED_SOURCE_ERROR','NO_CORRECTION_REQUIRED','UNAVAILABLE_OR_PROHIBITED']),
        'revision_refs':picks(source_refs(s),6),'repair_target':enum(REPAIR_TARGETS),
        'content_role':enum(['ATTRIBUTION','OBSERVATION','LEGAL_CONCLUSION','CONDITIONAL','VIEW_LIMIT','COMPARISON']),
        'source_owner':enum(speakers(objects)+['NONE','UNRESOLVED','MULTIPLE_SOURCE_RECORDS','SOURCE_LOCAL_UNNAMED']),
        'error_types':picks(['ATTRIBUTION','BINDING','PROCEDURE','UNSUPPORTED_REASON','VIEW_LIMIT_AS_REAL_WORLD_EVENT','UNQUALIFIED_LEGAL_EFFECT','OMISSION','OTHER'],8),
        'decision':enum(['ACCEPT','REJECT','UNRESOLVED'])})
    def comparison(hid):
        fields=dict(item['properties']);included=(report or {}).get('comparisons',{}).get(hid,{}).get('include',True)
        fields['history_meaning']=text(350)
        hv={**s,'directory':{i:r for i,r in s['directory'].items() if r['domain']=='HISTORY' and r['document_id']==analogies[hid]['document_id']}}
        fields['history_witnesses']=arr(witness(hv,'HISTORY'),3)
        fields['current_meaning']=text(350)
        fields['case_witnesses']=arr(witness(s,'CASE'),3)
        if not included:fields['decision']=enum(['OMISSION_JUSTIFIED','OMISSION_UNJUSTIFIED','OMISSION_UNRESOLVED'])
        # Read the historical source before inspecting the proposed similarity.
        ordered={k:fields[k] for k in ['history_meaning','history_witnesses','current_meaning','case_witnesses']}
        ordered.update({k:v for k,v in fields.items() if k not in ordered})
        return obj(ordered)
    def main_item(tid):
        props=dict(item['properties'])
        cap=max(18,len((report or {}).get('items',{}).get(tid,{}).get('refs',[])))
        props['reviewed_refs']=picks(source_refs(s),cap)
        return obj(props)
    rendered={segment['source_use_id']:segment for item in (report or {}).get('items',{}).values()
              for segment in item.get('segments',[]) if 'source_use_id' in segment}
    return obj({'items':keyed(report_tasks(tasks),main_item), 'comparisons':keyed(analogies or {},comparison),
        'source_records':keyed(rendered,obj({**source_decision(s,'CASE')['properties'],
            'field_findings':findings_schema(s),
            'observed_content_role':enum(['ATTRIBUTION','OBSERVATION','LEGAL_ASSESSMENT','VIEW_LIMIT','UNRESOLVED']),
            'observed_owner':enum(speakers(objects)+['NONE','UNDECLARED','UNRESOLVED','SOURCE_LOCAL_UNNAMED']),
            'observed_status':enum(['PARTY_CLAIM','COURT_RECORDED','REPORTED_EVIDENCE','LIMITATION','HYPOTHETICAL','UNRESOLVED'])})),
        'whole_source_coverage':obj({'reason':text(400),
            'obligations':keyed((inventory or {}).get('obligations',{}),obj({
                'status':enum(['COMPLETE','PARTIAL','ABSENT','UNRESOLVED']),
                'report_item_ids':picks(report_tasks(tasks),12),
                'answer_record_ids':picks(sorted({rid for item in (report or {}).get('items',{}).values() for rid in item.get('support_ids',[])}),16),
                'answer_relation':enum(['DIRECT_RECORD','CONDITIONAL_DERIVATION','EXPLAINS_UNRESOLVED','DOES_NOT_ANSWER']),
                'refs':picks(source_refs(s,'CASE'),8),
                'reason':text(260),'repair_target':enum(REPAIR_TARGETS)})),
            'omissions':arr(omission(s),12)}),
        'source_disagreements':arr(text(250),8)})

# V2 interfaces share generation/validation contracts. All legal mappings are
# proposed and source-reviewed by the experimental provider, never filled by code.
def queries(tasks):
    return keyed(tasks,obj({k:text(350) for k in ('SUPPORT','OPPOSITION','EXCEPTION')}))

def scan(s,ids):
    return obj({'read_ids':picks(ids,len(ids),len(ids)),
        'issues':arr(obj({'question':text(300),'refs':picks(ids,5,1),'category':enum(['SUPPORT','OPPOSITION','EXCEPTION','SCOPE','UNKNOWN'])}),24),
        'unresolved':arr(text(240),8)})

def consolidate(tasks):
    return obj({'groups':arr(obj({'canonical':enum(tasks),'duplicates':picks(tasks,12,1),'reason':text(300)}),len(tasks))})

def burdens(s,tasks,scopes,objects,cfg):
    return obj({'burdens':arr(obj({'scope_id':enum(scopes),'task_id':enum(tasks),
        'holder':enum(objects),'shifted_holder':enum(list(objects)+['NONE']),
        'shifted_task_id':enum(list(tasks)+['NONE']),
        'trigger_tasks':picks(tasks,8),'shift_trigger_tasks':picks(tasks,8),
        'record_complete_task':enum(tasks),
        'failure_effect':enum(['PATH_UNAVAILABLE','REQUEST_NOT_ESTABLISHED']),
        'authority_refs':picks(source_refs(s,'LAW'),6,1),'standard':text(350),'reason':text(350)}),cfg['max_burdens'])})

def requests(s,tasks,scopes,paths,burdens,cfg):
    return obj({'requests':arr(obj({'scope_id':enum(scopes),'conclusion_task':enum(tasks),
        'level':enum(['REQUEST','REMEDY']),'name':text(250),
        'grounds':arr(obj({'all_paths':picks(paths,12,1),'reason':text(240)}),8,1),
        'gates':picks(tasks,12),'blockers':picks(tasks,12),'burden_ids':picks(burdens,12),
        'exceptions':arr(obj({'blocker_task':enum(tasks),'exception_task':enum(tasks),'authority_refs':picks(source_refs(s,'LAW'),6,1)}),8),
        'authority_refs':picks(source_refs(s,'LAW'),6,1),'coverage_complete':boolean(),
        'missing_grounds':arr(text(240),8),'reason':text(400)}),cfg['max_requests'])})

def legal_mapping_reviews(s,ids):
    return keyed(ids,obj({k:decision(s) for k in ('scope','law','coverage')}))

def analogies(s,tasks,cfg,candidates):
    # Every actually selected document gets an explicit disposition. A negative or
    # unresolved judgment is valid; no positive comparison or citation is forced.
    return obj({'analogies':keyed(candidates,lambda cid:obj({
        'task_id':enum(tasks),
        'history_refs':picks(candidates[cid]['history_refs'],len(candidates[cid]['history_refs']),len(candidates[cid]['history_refs'])),
        'case_refs':picks(source_refs(s,'CASE'),6),'similarities':text(350),'differences':text(350),
        'orientation':enum(['SUPPORT','OPPOSITION','EXCEPTION','NOT_USEFUL','UNRESOLVED']),
        'scope_comparison':keyed(['actors','property','time','procedure','request'],obj({
            'assessment':enum(['COMPARABLE','DIFFERENT','UNKNOWN']),'reason':text(180)})),
        'law_status':enum(['NOT_INVOKED','SUPPORTED_BY_FROZEN_LAW','UNRESOLVED','INAPPLICABLE']),
        'limited_use':text(350),'authority_refs':picks(source_refs(s,'LAW'),6)}))})


def review_tasks(s,ids):
    return keyed(ids,obj({'assumptions':source_decision(s,'CASE'),
        'question':decision(s,'CASE'),'law':decision(s,capacity=12)}))


def source_inventory(s,scopes,cfg):
    # Generation matches the retained V20 four-section requirement. Content is
    # still assessed by the model; the program creates no summary or filler.
    def group(section):
        return arr(obj({
        'question':text(280),'scope_id':enum(scopes),'section':enum([section]),
        'importance':enum(['IMPORTANT','CONTEXT']),
        'answerability':enum(['KNOWN_RECORD','OPEN_QUESTION']),
        'refs':picks(source_refs(s,'CASE'),8,1)}),cfg['max_tasks']-7,1)
    return obj({'obligations':keyed(SECTIONS,group),
        'source_dispositions':keyed(source_refs(s,'CASE'),obj({
            'relevance':enum(['IMPORTANT','CONTEXT','UNRESOLVED']), 'reason':text(140)})),
        'coverage_limitations':arr(text(260),8)})


def inventory_tasks(s,scopes,library,cfg,inventory,objects):
    base=tasks(s,scopes,library,cfg,objects=objects)['properties']['tasks']['items']['properties']
    return obj({'tasks':keyed(inventory['obligations'],lambda oid:obj({**base,
        'proposition':enum([inventory['obligations'][oid]['question']]),
        'scope_id':enum([inventory['obligations'][oid]['scope_id']]),
        'section':enum([inventory['obligations'][oid]['section']]),
        'importance':enum([inventory['obligations'][oid]['importance']]),
        'role':enum(['REPORT']), 'obligation_ids':picks([oid],1,1),
        'question_basis_refs':picks(inventory['obligations'][oid]['refs'],len(inventory['obligations'][oid]['refs']),len(inventory['obligations'][oid]['refs']))})),
        'coverage_limitations':arr(text(260),8)})


def history_reading(s,refs):
    view={**s,'directory':{i:r for i,r in s['directory'].items() if i in refs}}
    return obj({**{k:text(400) for k in ('issue','actors_property','proceeding','recorded_position','uncertainty')},
        'source_coverage':keyed(refs,lambda ref:obj({'meaning':text(200),
            'witnesses':arr(obj({'span_id':enum([i for i,w in witness_registry(view,'HISTORY').items() if w['ref']==ref])}),2,1)}))})
