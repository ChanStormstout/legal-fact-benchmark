"""Source descriptions independent of legal use. All meanings/verdicts are model outputs."""
import copy
import contracts as C
from common import digest, mint, refs_valid, witness_quotes_valid, save, resolve_witnesses

EXTRACT = '''Read the allowed CASE original, not a proposed legal answer. Extract atomic material source records once. Preserve distinct claims, evidence, trial/appeal findings and reported events. A source's stated position can be faithfully described even if disputed or legally wrong. Record who says it and the event/property/time/procedural scope of THAT statement, not the current question's desired scope. A later court rejecting one argument does not reverse every earlier finding. Never infer no judgment from a withheld target. Use SOURCE_LOCAL_UNNAMED only when the text identifies an unnamed role; preserve that literal role as owner_label. Use UNRESOLVED when attribution cannot be established. The event, date role and procedure are descriptions, not approved rule premises. Do not repeat records per report section. Select exact source witnesses; no legal conclusions of your own. Preserve important counterpositions. List genuine extraction limitations.'''
REVIEW = '''Independently read CASE originals and assess each exact source record. Review the statement's speaker, content, status, actors, property, event, date role and procedural location together. The proposed source record is fallible. Select witnesses supporting every substantive field; reject disagreement and leave insufficient context unresolved. ACCEPT means faithful source description, never acceptance of its merits or legal effect. Do not test the claim against success of the lawsuit. An accurately reported party argument remains a party argument. An unnamed lower court may be identified by its source-local role; never replace it with a guessed named court. Return observed owner/status/content_role, exact object hash and a reason. Do not repair the candidate while reviewing it.'''
EXTRACT += ''' Choose content_role independently of provenance status: ATTRIBUTION reports a person's claim or a prior court's legal position; OBSERVATION describes a recorded occurrence; LEGAL_ASSESSMENT preserves a source's express legal analysis; VIEW_LIMIT describes an actual source limitation. A court reporting another person's claim is not a finding that the claim is true. Preserve participant roles with object IDs and source witnesses. source_owner is the speaker, not the actor. court is the court of the described event, or UNKNOWN; it need not be the court narrating the document. Never change these fields when selecting a later use.'''
REPAIR = EXTRACT + ''' Repair only addressed records and explicitly source-linked omissions. Each addressed record may be kept as a reviewed replacement, split into atomic replacements, or withdrawn with []. additions may contain only genuinely omitted records supported by the indicated allowed passages. No correct replacement or acceptance is supplied. Every replacement and addition is independently reviewed. Preserve opposing positions; do not add a new legal rule.'''

FIELDS=['meaning','owner_label','participant_roles','event_time','procedure']
FINDING_FIELDS=['meaning','source_owner','owner_label','status','content_role','participant_roles','actors','properties','event','time','court','procedure']
SOURCE_POLICY='''Describe and check the supplied original record, not the answer to a lawsuit. A party claim, a prior finding and an open legal question are distinct recordable contents. Reporting a prior finding does not endorse it. Do not require the hidden target outcome to describe visible proceedings. No target question, proposed legal conclusion or executable law is authority for this stage. All readings remain fallible model assessments; never invent a missing identity or acceptance.'''
READ_ORIGINAL='''Read the supplied original CASE passages before seeing any proposed source record. No candidate answer, target question, prior review or object registry is given. Describe the material positions and events in these focus passages, using surrounding originals only to resolve attribution. Separate the speaker from the actor; explicitly identify unnamed plaintiff/defendant roles, parent versus child, court levels, event dates, and who prevailed on WHICH issue in EACH earlier proceeding. Preserve negation and opposing positions. Do not decide the target case or add legal effects. Use only the original's literal role/name when a person is unnamed. Select witnesses for every observation; a citation is not itself evidence of your interpretation. Record missing context explicitly. These observations are fallible model readings, not accepted facts.'''
REVIEW += ''' Compare each candidate against the candidate-blind original reading as well as the originals. For each field select AGREES, CONTRADICTS, or NOT_COVERED; do not silently reconcile conflicting readings. When identifying a problem, give the field, exact counter-witnesses, and the conflict, rather than repeating the candidate's explanation. ACCEPT with a contradiction is invalid. A missing actor identity must be reported, not replaced by an unrelated registered person. A source-local unnamed role is valid. Readings are not a gold answer.'''

def findings_schema(s):
    return C.arr(C.obj({'field':C.enum(FINDING_FIELDS),
        'finding':C.enum(['CONTRADICTED','INSUFFICIENT_CONTEXT','MISSING_IDENTITY','REVIEW_DISAGREEMENT']),
        'witnesses':C.arr(C.witness(s,'CASE'),3,1),'conflict':C.text(180)}),8)

def blind_schema(s,focus):
    return C.obj({'observations':C.arr(C.obj({'speaker_label':C.text(100),
        'content':C.text(240),'participants':C.arr(C.obj({'name_or_role':C.text(80),'role':C.text(80)}),6),
        'event':C.text(120),'time':C.text(80),'procedure_and_court':C.text(120),
        'witnesses':C.arr(C.witness(s,'CASE'),4,1)}),max(16,4*len(focus))),
        'source_dispositions':C.keyed(focus,C.enum(['READ_WITH_OBSERVATIONS','NO_RELEVANT_STATEMENT','INSUFFICIENT_CONTEXT']))})

def record_schema(s,objects):
    return C.obj({'text':C.text(350),'source_owner':C.enum(C.speakers(objects)+['SOURCE_LOCAL_UNNAMED','UNRESOLVED']),
        'owner_label':C.text(100),'status':C.enum(['PARTY_CLAIM','COURT_RECORDED','REPORTED_EVIDENCE','LIMITATION','UNRESOLVED']),
        'content_role':C.enum(['ATTRIBUTION','OBSERVATION','LEGAL_ASSESSMENT','VIEW_LIMIT']),
        'participant_roles':C.arr(C.obj({'object_id':C.enum(objects),'role':C.text(80),'witnesses':C.arr(C.witness(s,'CASE'),2,1)}),8),
        'actors':C.picks([i for i,o in objects.items() if o['kind'] in ('PARTY','PERSON','ORGANIZATION')],8),
        'properties':C.picks([i for i,o in objects.items() if o['kind']=='PROPERTY'],8),
        'event':C.text(180),'time':C.text(100),'date_role':C.enum(['EVENT_DATE','JUDGMENT_DATE','CASE_IDENTIFIER','UNRESOLVED','NOT_STATED']),
        'procedure':C.text(180),'court':C.enum([i for i,o in objects.items() if o['kind']=='COURT']+['UNKNOWN']),
        'court_position':C.enum(['REPORTING_COURT','LOWER_COURT','PARTY_ACCOUNT','OTHER','UNRESOLVED']),
        'refs':C.picks(C.source_refs(s,'CASE'),8,1),'witnesses':C.arr(C.witness(s,'CASE'),6,1)})

def extraction_schema(s,objects,cfg):
    return C.obj({'records':C.arr(record_schema(s,objects),cfg['max_source_records']), 'limitations':C.arr(C.text(200),8)})

def review_schema(s,rows,objects,reading):
    return C.keyed(rows,lambda rid:C.obj({'object_hash':C.enum([digest(rows[rid])]),
        'observed_owner':C.enum(C.speakers(objects)+['SOURCE_LOCAL_UNNAMED','UNRESOLVED']),
        'observed_content_role':C.enum(['ATTRIBUTION','OBSERVATION','LEGAL_ASSESSMENT','VIEW_LIMIT','UNRESOLVED']),
        'observed_status':C.enum(['PARTY_CLAIM','COURT_RECORDED','REPORTED_EVIDENCE','LIMITATION','UNRESOLVED']),
        'field_checks':C.keyed(['meaning','owner_label','participant_roles','event_time','procedure'],C.enum(['SUPPORTED','CONTRADICTED','UNRESOLVED'])),
        'reading_alignment':C.keyed(FIELDS,C.enum(['AGREES','CONTRADICTS','NOT_COVERED'])),
        'reading_ids':C.picks(reading,8,1),'field_findings':findings_schema(s),
        **C.source_decision(s,'CASE')['properties']}))

def review_conflicts(v,s):
    reasons=[]
    findings=v.get('field_findings',[])
    if v.get('decision')=='ACCEPT' and (findings or any(x!='SUPPORTED' for x in v.get('field_checks',{}).values())):
        reasons.append('ACCEPT_WITH_CONTRADICTORY_FIELD_FINDINGS')
    if v.get('decision')=='REJECT' and not findings:reasons.append('REJECTION_WITHOUT_ACTIONABLE_FIELD_EVIDENCE')
    if any(not witness_quotes_valid(f.get('witnesses',[]),s,'CASE') for f in findings):reasons.append('FIELD_FINDING_WITHOUT_CASE_WITNESS')
    return reasons

def qualify(s,records,reviews,revoked=()):
    result={}
    for rid,row in records.items():
        v=reviews.get(rid,{});why=[]
        if rid in revoked or 'source_records:'+rid in revoked:why.append('SOURCE_RECORD_REVOKED')
        if v.get('object_hash')!=digest(row):why.append('SOURCE_RECORD_REVIEW_VERSION_MISMATCH')
        if v.get('decision')!='ACCEPT':why.append('SOURCE_RECORD_REVIEW_'+v.get('decision','MISSING'))
        why.extend(review_conflicts(v,s))
        if any(v.get('reading_alignment',{}).get(k)!='AGREES' for k in FIELDS):why.append('INDEPENDENT_READING_DISAGREEMENT_OR_INCOMPLETE')
        reading=v.get('independent_reading',{})
        if not v.get('reading_ids') or any(i not in reading for i in v.get('reading_ids',[])):why.append('INDEPENDENT_READING_NOT_BOUND')
        if reading and v.get('reading_hash')!=digest(reading):why.append('INDEPENDENT_READING_VERSION_MISMATCH')
        for observation in reading.values():
            if not witness_quotes_valid(observation.get('witnesses',[]),s,'CASE'):why.append('INDEPENDENT_READING_WITHOUT_SOURCE')
        reading_refs={w['ref'] for i in v.get('reading_ids',[]) for w in resolve_witnesses(reading.get(i,{}).get('witnesses',[]),s) if w}
        if not set(row['refs'])<=reading_refs:why.append('INDEPENDENT_READING_MISSES_CITED_SOURCE')
        if row['source_owner']=='UNRESOLVED' or row['status']=='UNRESOLVED':why.append('SOURCE_ATTRIBUTION_UNRESOLVED')
        if v.get('observed_owner')!=row['source_owner'] or v.get('observed_status')!=row['status'] or v.get('observed_content_role')!=row['content_role']:why.append('SOURCE_RECORD_ATTRIBUTION_DISAGREEMENT')
        if any(v.get('field_checks',{}).get(k)!='SUPPORTED' for k in ('meaning','owner_label','participant_roles','event_time','procedure')):why.append('SOURCE_RECORD_FIELDS_NOT_VERIFIED')
        if row['status']=='PARTY_CLAIM' and row['content_role']!='ATTRIBUTION':why.append('PARTY_CLAIM_ROLE_MISMATCH')
        if row['status']=='LIMITATION' and row['content_role']!='VIEW_LIMIT':why.append('LIMITATION_ROLE_MISMATCH')
        if any(not witness_quotes_valid(x['witnesses'],s,'CASE',row['refs']) for x in row['participant_roles']):why.append('PARTICIPANT_ROLE_WITHOUT_SOURCE')
        if not refs_valid(row['refs'],s,'CASE') or not set(row['refs'])<=set(v.get('refs',[])):why.append('SOURCE_RECORD_REFS_NOT_REVIEWED')
        if not witness_quotes_valid(row['witnesses'],s,'CASE',row['refs']):why.append('SOURCE_RECORD_WITNESS_MISSING')
        if not witness_quotes_valid(v.get('witnesses',[]),s,'CASE',v.get('refs',[])):why.append('SOURCE_RECORD_REVIEW_WITNESS_MISSING')
        result[rid]={'report_eligible':not why,'reasons':why,'record_hash':digest(row),'legal_approval':False,'premise_approval':False}
    return result

def bridge_check(s,record,scope,review):
    """Validate the model's source-to-target assessment, never infer it from IDs."""
    reasons=[]
    if review.get('source_hash')!=digest(record) or review.get('target_hash')!=digest(scope):reasons.append('BRIDGE_VERSION_MISMATCH')
    for key in ('actors','properties','time','procedure','court','request'):
        row=review.get('dimensions',{}).get(key,{})
        relation=row.get('relation')
        if relation not in ('MATCH','TRANSFER_SUPPORTED','NOT_REQUIRED') or not row.get('reason','').strip():reasons.append('UNVERIFIED_SCOPE_TRANSFER:'+key)
        if relation in ('MATCH','TRANSFER_SUPPORTED') and not witness_quotes_valid(row.get('case_witnesses',[]),s,'CASE'):reasons.append('SCOPE_TRANSFER_WITHOUT_CASE:'+key)
        if relation=='TRANSFER_SUPPORTED' and not witness_quotes_valid(row.get('law_witnesses',[]),s,'LAW'):reasons.append('SCOPE_TRANSFER_WITHOUT_LAW:'+key)
    for n,role in enumerate(record['participant_roles']):
        r=review.get('roles',{}).get(str(n),{});target=r.get('target_role')
        if r.get('decision')!='ACCEPT' or not r.get('reason','').strip():reasons.append('UNVERIFIED_PARTICIPANT_ROLE:'+str(n));continue
        if target=='NOT_REQUIRED':continue  # Explicit model judgment; source fact remains unchanged.
        if target is None or not target.isdigit() or int(target)>=len(scope['participant_roles']):reasons.append('UNRESOLVED_PARTICIPANT_ROLE:'+str(n));continue
        if scope['participant_roles'][int(target)]['object_id']!=role['object_id']:reasons.append('PARTICIPANT_OBJECT_MISMATCH:'+str(n))
        if not witness_quotes_valid(r.get('witnesses',[]),s,'CASE'):reasons.append('PARTICIPANT_MAPPING_WITHOUT_SOURCE:'+str(n))
    return {'accepted':not reasons,'reasons':reasons,'source_scope':{k:record[k] for k in ('actors','properties','participant_roles','event','time','procedure','court')},
        'target_scope_hash':digest(scope),'review':review,'semantic_assessor':'MODEL_NOT_PROGRAM'}

def read_originals(session):
    """Read every allowed CASE passage before any candidate exists; cache only originals."""
    if session.source_original_reading is not None:return session.source_original_reading
    source_ids=[i for i,v in session.s['directory'].items() if v['domain']=='CASE']
    combined={'observations':{},'source_dispositions':{},'reading_keys':[],
        'snapshot_id':session.s['snapshot_id'],'candidate_blind':True,'legal_approval':False}
    size=session.cfg.get('source_read_batch_size',6)
    for n in range(0,len(source_ids),size):
        focus=source_ids[n:n+size]
        cache_key=digest({'focus':focus,'sources':{i:v for i,v in session.s['directory'].items() if v['domain']=='CASE'},
            'prompt':READ_ORIGINAL,'policy':SOURCE_POLICY,'schema':blind_schema(session.s,focus),
            'model':session.cfg['parameters'],'revision':session.cfg['local_revision']})
        if cache_key not in session.source_reading_cache:
            raw=session.ask(f'source-original-read-{n//size}',READ_ORIGINAL,blind_schema(session.s,focus),
                {'focus_source_ids':focus},identity_only=True)
            session.source_reading_cache[cache_key]={'observations':mint(raw['observations'],'OR'),'source_dispositions':raw['source_dispositions']}
        part=session.source_reading_cache[cache_key]
        combined['observations'].update(copy.deepcopy(part['observations']))
        combined['source_dispositions'].update(part['source_dispositions']);combined['reading_keys'].append(cache_key)
    session.source_original_reading=combined
    save(session.dest/'source-first-reading.json',combined)
    return combined


def review(session,records,objects):
    original=read_originals(session)
    out={};size=session.cfg['source_record_batch_size'];keys=list(records)
    for n in range(0,len(keys),size):
        subset={i:records[i] for i in keys[n:n+size]}
        focus=sorted({ref for row in subset.values() for ref in row['refs']})
        reading={i:v for i,v in original['observations'].items() if set(focus)&
            {w['ref'] for w in resolve_witnesses(v['witnesses'],session.s) if w}}
        independent={'observations':reading,'source_dispositions':{i:original['source_dispositions'][i] for i in focus},
            'original_reading_hash':digest(original)}
        cache_key=digest(independent)
        judged=session.ask(f'source-record-review-{n//size}',REVIEW,review_schema(session.s,subset,objects,reading),
            {'subjects':subset,'objects':objects,'candidate_blind_reading':independent},identity_only=True)
        for rid,row in judged.items():
            row.update(independent_reading=reading,reading_hash=digest(reading),reading_cache_key=cache_key)
        out.update(judged)
        save(session.dest/(session.prefix+'source-review-evidence')/(str(n//size)+'.json'),
            {'read_before_candidate_comparison':True,'reading':independent,'reviews':judged,'same_model_not_independent_expert':True})
    return out

def extract(session,objects):
    original=read_originals(session)
    raw=session.ask('source-records',EXTRACT,extraction_schema(session.s,objects,session.cfg),
        {'objects':objects,'original_first_reading':original,'reading_is_fallible_not_accepted':True},identity_only=True)
    records=mint(raw['records'],'SR')
    return records,review(session,records,objects),raw['limitations']

def repair(session,records,old_reviews,objects,ids,feedback,omissions=()):
    from communication import feedback_for_stage
    scoped_feedback=feedback_for_stage(feedback,'SOURCE_RECORDS')
    subjects={i:records[i] for i in sorted(ids)}
    raw={};keys=list(subjects);size=session.cfg['source_record_batch_size']
    for offset in range(0,len(keys),size):
        subset={i:subjects[i] for i in keys[offset:offset+size]}
        schema=C.keyed(subset,C.obj({'replacements':C.arr(record_schema(session.s,objects),session.cfg['max_source_record_splits']), 'reason':C.text(200)}))
        # Withdrawal stays legal, but the independent source coverage below will
        # retain any resulting content gap. Deletion never establishes recovery.
        raw.update(session.ask(f'source-record-repair-{offset//size}',REPAIR+''' A supported earlier ruling or claim must remain describable even when the legal outcome is unresolved. Fix the fields and source witnesses that disagree. Withdraw only an unsupported or redundant record; if an uncertainty cannot be resolved, preserve it explicitly as unverified instead of silently erasing the source content.''',schema,
            {'subjects':subset,'objects':objects,'original_first_reading':read_originals(session),'source_linked_feedback':scoped_feedback},identity_only=True))
    new={i:copy.deepcopy(r) for i,r in records.items() if i not in subjects};rv={i:copy.deepcopy(v) for i,v in old_reviews.items() if i not in subjects}
    added={};lineage={}
    for rid,item in raw.items():
        replacement=mint(item['replacements'],'SR')
        new.update(replacement);added.update(replacement)
        lineage[rid]={'new_ids':list(replacement),'action':'REPLACE' if replacement else 'WITHDRAW','reason':item['reason'],'old_hash':digest(records[rid])}
    if omissions:
        capacity=min(session.cfg['max_source_record_additions'],session.cfg['max_source_records']-len(new))
        if capacity<0:raise ValueError('SOURCE_RECORD_CAP_EXCEEDED_NO_TRUNCATION')
        extra=session.ask('source-record-additions',REPAIR,C.obj({'additions':C.arr(record_schema(session.s,objects),capacity), 'limitations':C.arr(C.text(160),8)}),
            {'objects':objects,'existing_records':new,'source_linked_omissions':list(omissions),
             'original_first_reading':read_originals(session),'source_linked_feedback':scoped_feedback},identity_only=True)
        additions=mint(extra['additions'],'SR');added.update(additions);new.update(additions)
        lineage['ADDITIONS']={'new_ids':list(additions),'action':'ADD_SOURCE_LINKED_OMISSIONS','limitations':extra['limitations']}
    if len(new)>session.cfg['max_source_records']:
        from runner import ResourceStop
        raise ResourceStop('REPAIRED_SOURCE_RECORD_CAP_NO_TRUNCATION')
    rv.update(review(session,added,objects))
    for rid,item in lineage.items():
        if rid in records:
            item['content_changed']=set(item['new_ids'])!={rid}
            item['unchanged_after_requested_repair']=not item['content_changed']
            item['independent_semantic_improvement']=None
    return new,rv,lineage


COVERAGE='''Check source-description coverage, independently of whether a legal outcome can be decided. For EACH allowed CASE passage assess whether its material claims, recorded events and prior judicial positions are faithfully represented by the supplied records. COMPLETE requires selected records that cover its material content, including adverse positions. MISSING/PARTIAL concern omitted visible contents; UNRESOLVED concerns a source-reading dispute, not a withheld final judgment. NO_RECORDABLE_CONTENT is allowed for genuinely non-substantive passages, never solely because the target outcome is unavailable. The original-first reading is fallible: explicitly REJECT it with original witnesses if it misreads the passage. Do not assume an empty record registry means the original is empty. Choose only existing record IDs; do not supply legal answers or accept records in this coverage check.'''

def assess_coverage(session,records,reviews):
    original=read_originals(session);s=session.s
    ids=[i for i,v in s['directory'].items() if v['domain']=='CASE']
    schema=C.keyed(ids,C.obj({'status':C.enum(['COMPLETE','PARTIAL','MISSING','NO_RECORDABLE_CONTENT','UNRESOLVED']),
        'record_ids':C.picks(records,session.cfg['max_source_records']),
        'reading_relation':C.enum(['AGREES','REJECTS','UNRESOLVED']),
        'witnesses':C.arr(C.witness(s,'CASE'),4,1),'reason':C.text(240)}))
    judgments=session.ask('source-record-coverage',COVERAGE,schema,
        {'records':records,'record_qualification':qualify(s,records,reviews),
         'original_first_reading':original},identity_only=True)
    result={'snapshot_id':s['snapshot_id'],'records_hash':digest(records),'reviews_hash':digest(reviews),
        'original_reading_hash':digest(original),'judgments':judgments,'semantic_assessor':'MODEL_NOT_PROGRAM'}
    result['gaps']=coverage_gaps(s,records,reviews,original,result)
    result['complete']=not result['gaps']
    save(session.dest/(session.prefix+'source-record-coverage.json'),result)
    return result

def coverage_gaps(s,records,reviews,original,coverage):
    """Check identity/coverage contracts, without manufacturing semantic judgments."""
    accepted=qualify(s,records,reviews);gaps=[]
    valid=(coverage.get('snapshot_id')==s['snapshot_id'] and coverage.get('records_hash')==digest(records)
        and coverage.get('reviews_hash')==digest(reviews) and coverage.get('original_reading_hash')==digest(original))
    for sid,source in s['directory'].items():
        if source['domain']!='CASE':continue
        v=coverage.get('judgments',{}).get(sid,{});reasons=[];rids=v.get('record_ids',[])
        if not valid:reasons.append('STALE_SOURCE_COVERAGE')
        witness_refs={w['ref'] for w in resolve_witnesses(v.get('witnesses',[]),s) if w}
        if sid not in witness_refs:reasons.append('COVERAGE_WITHOUT_LOCAL_WITNESS')
        if v.get('status')=='COMPLETE':
            if not rids or any(i not in records or sid not in records[i]['refs'] or not accepted.get(i,{}).get('report_eligible') for i in rids):
                reasons.append('COVERAGE_WITHOUT_QUALIFIED_RECORD')
        elif v.get('status')=='NO_RECORDABLE_CONTENT':
            if original.get('source_dispositions',{}).get(sid)=='READ_WITH_OBSERVATIONS' and v.get('reading_relation')!='REJECTS':
                reasons.append('UNRESOLVED_ORIGINAL_READING_DISAGREEMENT')
        else:reasons.append('SOURCE_DESCRIPTION_'+v.get('status','UNASSESSED'))
        if v.get('reading_relation')=='UNRESOLVED':reasons.append('SOURCE_READING_UNRESOLVED')
        if reasons:gaps.append({'source_id':sid,'refs':[sid],'reasons':reasons,'model_reason':v.get('reason'),
            'question':'Reassess and recover the material source description in this allowed passage; a hidden final outcome does not erase visible claims or earlier rulings.'})
    return gaps
