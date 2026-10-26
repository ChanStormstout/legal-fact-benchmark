"""Batch-level propositions with program-resolved source references.

No generated quote strings, row-level repetition requirement, or redundant review
verdict vector. Original model records and review decisions remain auditable.
"""
import copy
from pathlib import Path
import source_v8 as base
from schema_contract import validate
VERSION='BATCH_SOURCE_REFERENCES_V9'
digest=base.digest;save=base.save;obj=base.obj;arr=base.arr;enum=base.enum;text=base.text;empty=base.empty
POLICY=base.POLICY
READ='''Read the supplied original judgment. Extract the focus entries as ONE BATCH of
attributed propositions. All originals are supplied for context. Do not produce a record for
every physical line. A wrapped sentence becomes one proposition with every needed source ID.
Produce each proposition once; a different speaker, court, status, event, scope or condition
can require a separate record. Do not repeat an entire sentence once per source fragment.

Return records, unresolved omissions, and actual source conflicts. A header containing a
court name, party, date or citation has extractable SOURCE_METADATA. Layout alone needs no
record. Keep both adopted and rejected arguments, attributing each correctly. Separate an
editorial headnote, party statement, lower-court finding, quoted precedent, and current holding.
Read antecedents: the person receiving property is not necessarily the person asserting it.
Do not invent roles, names, evidence or allegations. Unknown attribution fields are null.

Represent the substantive proposition, not 'the court narrated a sentence'. For 'A denies B
paid C', the kind is DENIAL, speaker A, subject B, relation paid, object C. An open 'whether'
question is OPEN_QUESTION, not a positive legal argument. Execution of a lease is OCCURRENCE;
whether it binds someone is LEGAL_EFFECT. Rejection of legal force does not deny execution.
A later holding does not erase earlier objections. Do not turn missing allegations into facts
that were affirmatively disproved. Record the actual event time separately from statement time.

Preserve negations, conditions, exceptions, limitations, and burdens in qualifications attached
to the proposition. Historical legal views differ from the current court's adopted rule.
Each record and qualification selects source_ids from the originals. No rewritten quotes,
offsets, record IDs, inferred source text or assertion-specific answer keys. The program
attaches the selected original text verbatim. Selection is not proof: your interpretation must
actually follow from those sources in context. Record unresolved ambiguity rather than guessing.
Omissions are unresolved material gaps, not a list of every blank line. All material propositions
in the focus should be captured even if unfavorable to the eventual result.'''
REVIEW='''Check each addressed candidate against the originals, including every component:
attribution, substantive proposition, procedural/time scope, conditions, evidence meaning and
record kind. Source existence alone is insufficient. Use one action per program-owned target:
KEEP if the whole record is supported; REPLACE with complete corrected records for identified
errors; WITHDRAW if it should not be retained; UNRESOLVED if source support cannot be decided.
KEEP has no issues or new_records. Other actions identify specific issues. Only REPLACE has
new_records. There is no second verdict or per-component pass/fail vector to contradict this
action. Explain what the source says and why the action follows, using selected source_ids.
Check source IDs actually support the stated speaker and legal status, not just vocabulary.
Add any materially omitted propositions once. Preserve unresolved gaps explicitly. Corrected
and added records will be labelled as review proposals, not independently accepted facts.
Do not request another model call, invent a legal answer, or repeat correct records as changes.'''

def plan(sources):return base.plan(sources)
def refs(sources):return {**arr(enum(sources),1),'uniqueItems':True}
def record_schema(sources):
    schema=copy.deepcopy(base.record_schema(sources));p=schema['properties']
    p.pop('evidence');p['source_ids']=refs(sources);schema['required']=list(p)
    p['proposition']['properties']['object']={'anyOf':[text(),{'type':'null'}]}
    q=p['qualifications']['items'];q['properties'].pop('evidence');q['properties']['source_ids']=refs(sources);q['required']=list(q['properties'])
    return schema

def gap_schema(sources):return obj({'source_ids':refs(sources),'reason':text()})
def reading_schema(sources):return obj({'records':arr(record_schema(sources)),
    'unresolved_omissions':arr(gap_schema(sources)),'conflicts':arr(gap_schema(sources))})
def reading_request(sources,focus):return {'policy':POLICY,'task':READ,'sources':sources,'focus_source_ids':focus,
    'qualification_cues':base.cues(sources,focus),'schema':reading_schema(sources)}

def wrap(record,sources,focus,state):
    problems=[]
    if not set(record['source_ids'])&set(focus):problems.append('NO_FOCUS_SOURCE_SUPPORT')
    ids=list(dict.fromkeys(record['source_ids']+[sid for q in record['qualifications'] for sid in q['source_ids']]))
    return {'record':copy.deepcopy(record),'hash':digest(record),'state':'UNRESOLVED' if problems else state,
            'source_text_by_id':{sid:sources[sid] for sid in ids},'reference_resolution':'PROGRAM_VERBATIM_NOT_SEMANTIC_ACCEPTANCE','structural_issues':problems}

def initial_packet(sources,focus,value):
    validate(value,reading_schema(sources))
    result={'source_hash':digest(sources),'focus':list(focus),'records':{f'R{i:04d}':wrap(r,sources,focus,'UNREVIEWED') for i,r in enumerate(value['records'])},
        'unresolved_omissions':value['unresolved_omissions'],'conflicts':value['conflicts']}
    result['snapshot_hash']=digest(result);return result

def review_schema(sources,packet):
    issue=obj({'aspect':enum(base.CHECKS),'explanation':text()});r=record_schema(sources)
    branches=[]
    for action in ['KEEP','REPLACE','WITHDRAW','UNRESOLVED']:
        branches.append(obj({'action':enum([action]),'issues':empty(issue) if action=='KEEP' else arr(issue,1),
            'source_ids':refs(sources),'source_basis':text(),'new_records':arr(r,1) if action=='REPLACE' else empty(r)}))
    return obj({'by_target':obj({key:{'anyOf':branches} for key in packet['records']}),
        'additions':arr(r),'unresolved_gaps':arr(gap_schema(sources)),'conflicts':arr(gap_schema(sources))})

def review_request(sources,packet):
    return {'policy':POLICY,'task':READ+'\n'+REVIEW,'sources':sources,'focus_source_ids':packet['focus'],
       'candidates':{k:{'record':v['record'],'hash':v['hash'],'state':v['state'],'structural_issues':v['structural_issues']} for k,v in packet['records'].items()},
       'unresolved_omissions':packet['unresolved_omissions'],'qualification_cues':base.cues(sources,packet['focus']),
       'request_snapshot_hash':packet['snapshot_hash'],'schema':review_schema(sources,packet)}

def apply_review(sources,packet,value,bound_hash):
    if bound_hash!=packet['snapshot_hash'] or digest({k:v for k,v in packet.items() if k!='snapshot_hash'})!=bound_hash:raise ValueError('STALE_REVIEW_SNAPSHOT')
    if digest(sources)!=packet['source_hash']:raise ValueError('SOURCE_SNAPSHOT_CHANGED')
    validate(value,review_schema(sources,packet));active={};retired={};events=[];pending=[]
    for key,row in value['by_target'].items():
        old=packet['records'][key];action=row['action'];problem=None
        if row['source_basis'].strip().lower().rstrip('.!') in base.GENERIC:problem='GENERIC_REVIEW_BASIS'
        if action=='KEEP' and old['structural_issues']:problem='SOURCE_SUPPORT_SCOPE_MISMATCH'
        if action=='REPLACE' and any(r==old['record'] for r in row['new_records']):problem='UNCHANGED_REPLACEMENT'
        if action=='UNRESOLVED' or problem:
            active[key]={**copy.deepcopy(old),'state':'UNRESOLVED'};pending.append({'target':key,'reason':problem or 'MODEL_UNRESOLVED'})
        elif action=='KEEP':active[key]={**copy.deepcopy(old),'state':'MODEL_REVIEW_SUPPORTED'}
        else:
            retired[key]=old
            for i,r in enumerate(row['new_records']):active[f'{key}.r{i}']=wrap(r,sources,packet['focus'],'REVISION_NOT_INDEPENDENTLY_REVIEWED')
        events.append({'target':key,**copy.deepcopy(row),'before_hash':old['hash'],'application_problem':problem})
    for i,r in enumerate(value['additions']):active[f'A{i:04d}']=wrap(r,sources,packet['focus'],'ADDITION_NOT_INDEPENDENTLY_REVIEWED')
    for key,r in active.items():
        if r['state']!='MODEL_REVIEW_SUPPORTED':pending.append({'target':key,'reason':r['state']})
    if not active:pending.append({'reason':'EMPTY_BATCH_NO_SEMANTIC_COMPLETENESS_CLAIM'})
    pending += [{'reason':'MODEL_UNRESOLVED_GAP','gap':g} for g in value['unresolved_gaps']]
    return {'records':active,'retired_records':retired,'events':events,'pending':pending,
        'unresolved_gaps':value['unresolved_gaps'],'conflicts':packet['conflicts']+value['conflicts'],
        'source_hash':packet['source_hash'],'input_snapshot_hash':bound_hash,'program_semantic_acceptance':False}

def run(sources,ask,destination):
    dest=Path(destination)
    if dest.exists():raise ValueError('EXISTING_ATTEMPT_NOT_REPEATED')
    dest.mkdir(parents=True);groups=plan(sources);save(dest/'plan.json',groups);completed=[];calls=0;stage=None
    try:
        for i,focus in enumerate(groups):
            d=dest/f'batch-{i:03d}';stage=f'reading-{i:03d}';req=reading_request(sources,focus);save(d/'reading-request.json',req)
            calls+=1;value=ask(stage,copy.deepcopy(req));save(d/'reading-response.json',value);packet=initial_packet(sources,focus,value);save(d/'initial.json',packet)
            stage=f'review-{i:03d}';req=review_request(sources,packet);save(d/'review-request.json',req);calls+=1
            value=ask(stage,copy.deepcopy(req));save(d/'review-response.json',value);result=apply_review(sources,packet,value,req['request_snapshot_hash']);save(d/'reviewed.json',result);completed.append(result)
        records={f'B{i:03d}.{k}':v for i,b in enumerate(completed) for k,v in b['records'].items()}
        save(dest/'source-records.json',{'version':VERSION,'records':records,'batches':completed,'source_hash':digest(sources),'technical_complete':True,'semantic_quality':None,'downstream_enabled':False})
        outcome={'technical_complete':True,'completed_batches':len(completed),'expected_batches':len(groups),'logical_calls':calls,'record_count':len(records),
            'record_states':{state:sum(r['state']==state for r in records.values()) for state in sorted({r['state'] for r in records.values()})},'semantic_quality':None,'full_C_run':False}
        save(dest/'outcome.json',outcome);return outcome
    except Exception as exc:
        save(dest/'outcome.json',{'technical_complete':False,'failed_stage':stage,'error':type(exc).__name__+':'+str(exc),'completed_batches':len(completed),'expected_batches':len(groups),'logical_calls':calls,'answer':None,'semantic_quality':None});raise
