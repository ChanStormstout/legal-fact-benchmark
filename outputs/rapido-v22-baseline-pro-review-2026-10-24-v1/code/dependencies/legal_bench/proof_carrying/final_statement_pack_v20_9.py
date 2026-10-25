"""Source-reviewed complete statements with explicit bindings and coverage.

The new source statements are development annotations, not automatic-extraction
accuracy or human gold. A fresh source review gates the exact proposed pack; final
ordering cannot add/delete text, and whole-answer review remains independent.
"""
import json
from . import final_bindings_v20_8 as core
from . import final_source_guard_v20_7 as guard
from .artifact_state_v20_2 import digest
from .schema_contract_v19_6 import validate,loads

VERSION='V20_9_TYPED_STATEMENT_PACK_1'
ROLES=('LANDLORD','TENANT','SUBTENANT','HEAD_TENANT','TRANSFEREE',
       'ISSUING_COURT','REPORTING_COURT','NOTICE_AUTHORITY')
SECTIONS=('SUMMARY','GROUND','COUNTERARGUMENT','LIMITATION')


def pack_schema(case,frame):
    actor_ids=[a['id'] for a in frame['actors']]
    property_ids=[p['id'] for p in frame['properties']]
    event_ids=[e['id'] for e in frame['events']]
    refs=[s['id'] for s in case['segments'] if s['text'].strip()]
    record=guard.obj({'id':{'type':'string','pattern':r'^S[0-9]{2,3}$'},
        'section':guard.enum(SECTIONS),'text':guard.text(),'status':guard.text(),'stage':guard.text(),
        'actor_ids':guard.array(guard.enum(actor_ids)),
        'property_ids':guard.array(guard.enum(property_ids)),
        'event_ids':guard.array(guard.enum(event_ids)),
        'refs':guard.array({'$ref':'#/$defs/source_id'},1),
        'role_bindings':guard.array(guard.obj({'role':guard.enum(ROLES),'actor_id':guard.enum(actor_ids)}))})
    schema=guard.obj({'records':guard.array(record,4,128)})
    schema['$defs']={'source_id':guard.enum(refs)}
    return schema


def check_pack(case,frame,pack):
    validate(pack,pack_schema(case,frame))
    ids=[r['id'] for r in pack['records']]
    if len(ids)!=len(set(ids)):raise ValueError('PACK_DUPLICATE_ID')
    if set(r['section'] for r in pack['records'])!=set(SECTIONS):raise ValueError('PACK_MISSING_REQUIRED_SECTION')
    actors={a['id']:a for a in frame['actors']}
    for r in pack['records']:
        if r['section']!='LIMITATION' and not r['actor_ids']:raise ValueError('PACK_UNBOUND_SUBSTANTIVE_STATEMENT')
        for b in r['role_bindings']:
            # Reporting provenance is distinct from the people who performed the
            # described act. A reporting court need not be a primary actor.
            if b['role']!='REPORTING_COURT' and b['actor_id'] not in r['actor_ids']:
                raise ValueError('PACK_ROLE_OUTSIDE_STATEMENT_ACTORS')
            kind=actors[b['actor_id']]['kind']
            if b['role'].endswith('COURT') and kind!='COURT':raise ValueError('PACK_COURT_ROLE_MISMATCH')
            if b['role']=='NOTICE_AUTHORITY' and kind!='OTHER':raise ValueError('PACK_AUTHORITY_ROLE_MISMATCH')
    return True


def pack_review_task(case,frame,pack,conditional_rules):
    check_pack(case,frame,pack)
    bindings={'version':VERSION,'source_sha256':digest(case['segments']),
              'frame_sha256':digest(frame),'pack_sha256':digest(pack),
              'conditional_sha256':digest(conditional_rules)}
    verdict=guard.obj({'label':guard.enum(guard.LABELS),'refs':guard.array({'$ref':'#/$defs/source_id'}),'reason':guard.text()})
    schema=guard.obj({**{k:guard.enum([v]) for k,v in bindings.items()},
                      'verdicts':guard.obj({r['id']:verdict for r in pack['records']})})
    schema['$defs']={'source_id':guard.enum([s['id'] for s in case['segments'] if s['text'].strip()])}
    payload={'bindings':bindings,'frame':frame,'proposed_statements':pack['records'],
             'conditional_computation':conditional_rules,
             'source':[{'id':s['id'],'text':s['text']} for s in case['segments']]}
    prompt='''Independently verify every EXACT proposed statement, including all actor,
property, event and role bindings, adopted/reported/dissent status and scope. Read
the complete source; the proposal is not authority and does not approve itself.
Historical court reasoning is distinct from the conditional interpreter's state.
Do not require an executable certificate for a accurately attributed historical
account, and do not convert a reported finding into a certified factual premise.
Check conditions versus conduct, contested dates, contrary legal accounts, actual
remand destination and limits of the disposition. A method limitation must match
the supplied computation record; a claimed source absence must be checked against
the ENTIRE source. Definite error = UNSUPPORTED, insufficient/ambiguous = UNRESOLVED.
Do not repair, guess or silently accept missing bindings. Require relevant nonblank
refs for SUPPORTED/UNSUPPORTED. Return a complete strict JSON CODE BLOCK matching
the schema, short reasons, no downloadable file. This is model source review,
not human gold or legal approval.\n'''
    prompt+=json.dumps(payload,ensure_ascii=False,separators=(',',':'))
    prompt+='\nOUTPUT SCHEMA:\n'+json.dumps(schema,separators=(',',':'))
    return {'bindings':bindings,'schema':schema,'prompt':prompt}


def final_task(case,old_task,bridge,frame,frame_review,pack,pack_review):
    base=core.final_task(case,old_task,bridge,frame,frame_review)
    rt=pack_review_task(case,frame,pack,bridge['conditional_rules'])
    validate(pack_review,rt['schema'])
    if any(v['label']!='SUPPORTED' or not v['refs'] for v in pack_review['verdicts'].values()):
        raise ValueError('PACK_NOT_SOURCE_REVIEW_ACCEPTED')
    verification=core.clone(base['verification_task'])
    book=verification['claim_registry']
    frame_ids={u['row']['id']:'F'+k for k,u in core.frame_units(frame).items()}
    for r in pack['records']:
        if r['id'] in book['accepted']:raise ValueError('PACK_CLAIM_ID_COLLISION')
        origin='/'.join((str(case['case_id']),digest(case['segments'])[:16],VERSION,digest(pack)[:16],r['id']))
        book['accepted'][r['id']]={'id':r['id'],'kind':'TYPED_FINAL_STATEMENT',
            'claim':core.clone(r),'source_refs':pack_review['verdicts'][r['id']]['refs'],
            'dependencies':sorted({frame_ids[x] for x in r['actor_ids']+r['property_ids']+r['event_ids']+[b['actor_id'] for b in r['role_bindings']]}),
            'origin_declaration_id':origin,
            'acceptance':'MODEL_SOURCE_REVIEW_NOT_LEGAL_APPROVAL'}
        book['declaration_aliases'][origin]=r['id']
    verification['registry_sha256']=digest(book)
    full=guard.final_schema(case,book)
    # Preserve the already checked frame extensions and finite identities.
    full['properties']['case_frame']=core.clone(base['verification_task']['schema']['properties']['case_frame'])
    full['$defs']['rule_address']=core.clone(base['verification_task']['schema']['$defs']['rule_address'])
    for field in ('grounds','counterarguments'):full['properties'][field]['maxItems']=len(pack['records'])
    full['properties']['gaps']['maxItems']=len(pack['records'])
    full['properties']['gaps']['items'].pop('maxLength',None)
    verification['schema']=full
    ids=[r['id'] for r in pack['records']]
    schema=guard.obj({'record_order':guard.array(guard.enum(ids),len(ids),len(ids))})
    prompt='''Order the supplied source-reviewed statements to make the historical
reconstruction clear. Output ONLY record_order containing every actual statement
ID exactly once. Do not write new prose, facts or conclusions. Sections, text,
attribution, concrete bindings and limitations are fixed reviewed inputs. Code
will render them verbatim within their sections. Complete source is unchanged.
This is a source reconstruction, not an executable legal certificate.\n'''
    prompt+='\nFIXED REQUEST:\n'+json.dumps(old_task['review_context']['request'])
    ordering_frame=core.clone(frame)
    for r in ordering_frame['actors']+ordering_frame['properties']:
        r.pop('origin_object_ids',None)
    prompt+='\nREVIEWED FRAME (original identity-link audit saved separately):\n'+json.dumps(ordering_frame,separators=(',',':'))
    prompt+='\nREVIEWED STATEMENTS:\n'+json.dumps(pack,separators=(',',':'))
    prompt+='\nCOMPLETE ALLOWED SOURCE:\n'+'\n'.join(s['id']+'\n'+s['text'] for s in case['segments'])
    prompt+='\nOUTPUT SCHEMA:\n'+json.dumps(schema,separators=(',',':'))
    verification['prompt']=prompt
    verification['review_context']['render_policy']={'version':VERSION,'all_reviewed_records_required':True,'prose_immutable':True}
    verification['input_sha256']=digest({k:verification[k] for k in ('prompt','schema','review_context')})
    proxy=core.clone(base);proxy['verification_task']=verification;proxy['prompt']=prompt
    proxy['schema']=core.clone(full);del proxy['schema']['properties']['case_frame'];proxy['schema']['required']=list(proxy['schema']['properties'])
    proxy['input_sha256']=digest({k:v for k,v in proxy.items() if k!='input_sha256'})
    task={'version':VERSION,'prompt':prompt,'schema':schema,'pack':core.clone(pack),
          'pack_review_sha256':digest(pack_review),'frame':core.clone(frame),
          'source_sha256':digest(case['segments']),'review_proxy':proxy,'source_input_truncated':False}
    task['input_sha256']=digest(task)
    return task


def verify_task(task,case):
    if task['version']!=VERSION or digest({k:v for k,v in task.items() if k!='input_sha256'})!=task['input_sha256']:
        raise ValueError('STATEMENT_TASK_CHANGED')
    core.verify_task(task['review_proxy'],case)


def render(task,plan,case):
    verify_task(task,case);validate(plan,task['schema'])
    bank={r['id']:r for r in task['pack']['records']}
    groups={s:[] for s in SECTIONS}
    for key in plan['record_order']:groups[bank[key]['section']].append(bank[key])
    def row(r,counter=False):
        common={'point':r['status']+'; '+r['stage']+' ['+r['id']+']','claim_ids':[r['id']],
                'actor_ids':r['actor_ids'],'property_ids':r['property_ids'],'event_ids':r['event_ids']}
        if counter:return {**common,'refs':r['refs'],'treatment':r['text']}
        return {**common,'statement_status_and_stage':r['status']+'; '+r['stage'],
                'case_refs':r['refs'],'rule_refs':[],'explanation':r['text']}
    answer={'request_id':'Q1','result_status':'SOURCE_RECONSTRUCTION',
            'conclusion':' '.join(r['status'].replace('_',' ').capitalize()+' ('+r['stage']+'): '+r['text'] for r in groups['SUMMARY']),
            'conclusion_claim_ids':[r['id'] for r in groups['SUMMARY']],
            'grounds':[row(r) for r in groups['GROUND']],
            'counterarguments':[row(r,True) for r in groups['COUNTERARGUMENT']],
            'gaps':[r['text'] for r in groups['LIMITATION']],
            'assumptions':[],'connection_handling':[],'case_frame':core.clone(task['frame'])}
    validate(answer,task['review_proxy']['verification_task']['schema'])
    check=guard.inspect_candidate(task['review_proxy']['verification_task'],answer)
    if check['status']!='OK':raise ValueError(str(check['errors']))
    return answer


def review_task(task,plan,case):
    answer=render(task,plan,case)
    rt=core.review_task(task['review_proxy'],{k:v for k,v in answer.items() if k!='case_frame'},case)
    # Limitations carry their own exact reviewed statements, though the legacy
    # display field is only a string array. Include these declarations explicitly.
    start=rt['prompt'].index('{"bindings":');end=rt['prompt'].index('\nOUTPUT SCHEMA:\n',start)
    payload=json.loads(rt['prompt'][start:end]);bank=task['review_proxy']['verification_task']['claim_registry']['accepted']
    for r in task['pack']['records']:payload['reviewed_claims']['accepted'][r['id']]=bank[r['id']]
    rt['prompt']=rt['prompt'][:start]+json.dumps(payload,ensure_ascii=False,separators=(',',':'))+rt['prompt'][end:]
    return rt


def accept_final(task,raw,technical_status,*,case,review=None):
    if technical_status!='OK':return {'version':VERSION,'answer':None,'technical_status':technical_status,'contract_status':'GENERATION_FAILED','legal_approval':False}
    try:
        answer=render(task,loads(raw),case)
        result=core.accept_final(task['review_proxy'],json.dumps({k:v for k,v in answer.items() if k!='case_frame'}),'OK',case=case,review=review)
        result.update(version=VERSION,typed_statements_source_reviewed=True,source_pack_is_development_annotation_not_automatic_extraction_score=True)
        return result
    except (ValueError,KeyError,TypeError) as exc:return {'version':VERSION,'answer':None,'contract_status':'STATEMENT_PACK_REJECTED','error':str(exc),'legal_approval':False}
