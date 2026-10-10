"""Independent v4 reconstruction checker. Never imports the proposing engine or its evaluator.

All legal translations remain assumptions unless separately approved. This verifies
typed dependencies and an explicit finite calculus, not the meaning of source text.
"""
import re
from pathlib import Path
from .contracts import content_hash, read_json, byte_hash
from .realcase_contracts import schemas, validate, unique, binding_map, STATES

from .realcase_grounding_v4 import source_match, role_view, court_assessment

def inspect_sources(record, sources):
    return source_match(record, sources)['error']

def combine(operator, ordinary, exceptions):
    # Each value is whether that antecedent has the explicitly expected state.
    if operator == 'OPEN_TEXT': return 'UNKNOWN'
    if operator == 'ALL':
        v = ('FALSE' if 'FALSE' in ordinary else 'CONFLICTED' if 'CONFLICTED' in ordinary
             else 'UNKNOWN' if 'UNKNOWN' in ordinary or not ordinary else 'TRUE')
    elif operator == 'ANY':
        v = ('TRUE' if 'TRUE' in ordinary else 'CONFLICTED' if 'CONFLICTED' in ordinary
             else 'UNKNOWN' if 'UNKNOWN' in ordinary or not ordinary else 'FALSE')
    else: raise ValueError('UNSUPPORTED_OPERATOR')
    if 'TRUE' in exceptions: return 'FALSE'
    if v == 'FALSE': return 'FALSE'
    if 'CONFLICTED' in exceptions: return 'CONFLICTED'
    if 'UNKNOWN' in exceptions: return 'UNKNOWN'
    return v

def check_payload(cert, snap):
    """Internal worker; public CLI loads independently hash-pinned local files."""
    if cert['snapshot_sha256'] != content_hash(snap): raise ValueError('SNAPSHOT_HASH_MISMATCH')
    if cert['snapshot_id'] != snap['snapshot_id']: raise ValueError('SNAPSHOT_ID_MISMATCH')
    if cert['case_id'] != snap['case_id'] or cert['stage'] != snap['stage']: raise ValueError('CASE_OR_STAGE_MISMATCH')
    prop = cert['proposal']; validate(prop, schemas('derivation'))
    steps = unique(prop['steps']); requests = unique(prop['requests'])
    if not requests: raise ValueError('EMPTY_REQUESTS')
    rules, facts = snap['rules'], snap['premises']
    outputs, visiting = {}, set()
    def run(sid):
        if sid in outputs: return outputs[sid]
        if sid in visiting: raise ValueError('DEPENDENCY_CYCLE')
        if sid not in steps: raise ValueError('DANGLING_STEP')
        visiting.add(sid); s = steps[sid]
        row={'id':sid,'status':'VALID_UNDER_ASSUMPTIONS','state':None,'errors':[], 'gaps':[],
             'dependencies':[], 'semantic_assumptions':[], 'uncomputed':[], 'source_checks':[], 'sources':[], 'approval':'PENDING', 'model_proposed_state':s['proposed_state']}
        rule=rules.get(s['rule_ref']); bm=binding_map(s['bindings'])
        if any(not e or e not in snap['entities'] for e in bm.values()): row['errors'].append('UNKNOWN_ENTITY')
        if rule is None:
            row['errors'].append('RULE_VERSION_UNAVAILABLE')
        else:
            row['predicate']=rule['conclusion_predicate']; row['bindings']=s['bindings']; row['time_scope']=s['time_scope']
            row['statement_status']='DERIVED'; row['sources']+=rule['source_refs']
            scope=snap.get('scope_reviews',{}).get(s['rule_ref'])
            if not scope or scope.get('subject_hash')!=content_hash(rule):
                row['gaps'].append('RULE_SCOPE_REVIEW_MISSING_OR_STALE')
            elif not scope.get('jurisdiction_compatible') or not scope.get('stage_compatible'):
                row['errors'].append('RULE_SCOPE_MISMATCH')
            rev=snap['reviews']['rules'].get(s['rule_ref'])
            if not rev or rev['subject_hash'] != content_hash(rule): row['errors'].append('RULE_REVIEW_MISSING_OR_STALE')
            elif rev['decision'] != 'ACCEPT_RESEARCH': row['gaps'].append('RULE_SEMANTICS_NOT_ACCEPTED')
            match=source_match(rule,snap['sources']); row['source_checks'].append({'record':s['rule_ref'],**match})
            source_error=match['error']
            if source_error: row['errors'].append(source_error)
            slots=unique(rule['slots'],'name'); inputs=unique(s['inputs'],'slot')
            if set(inputs)-set(slots): row['errors'].append('UNDECLARED_INPUT_SLOT')
            if not set(rule['exception_slots']) <= set(slots): row['errors'].append('EXCEPTION_CONTRACT')
            vals={}
            for slot, contract in slots.items():
                inp=inputs.get(slot)
                if not inp:
                    vals[slot]='UNKNOWN'; row['gaps'].append('MISSING_SLOT:'+slot); continue
                row['dependencies'].append(inp)
                if inp['kind']=='STEP':
                    p=run(inp['id'])
                    row['semantic_assumptions'] += p.get('semantic_assumptions',[])
                    row['uncomputed'] += p.get('uncomputed',[])
                    if p['errors'] or p['state'] is None:
                        vals[slot]='UNKNOWN'; row['errors'].append('DEPENDENCY_INVALID:'+inp['id']); continue
                else:
                    p=facts.get(inp['id'])
                    if not p:
                        vals[slot]='UNKNOWN'; row['gaps'].append('PREMISE_UNAVAILABLE:'+inp['id']); continue
                    rev=snap['reviews']['premises'].get(inp['id'])
                    if not rev or rev['subject_hash']!=content_hash(p) or rev['decision']!='ACCEPT_RESEARCH':
                        vals[slot]='UNKNOWN'; row['gaps'].append('PREMISE_NOT_ACCEPTED:'+inp['id']); continue
                    match=source_match(p,snap['sources']); row['source_checks'].append({'record':inp['id'],**match})
                    source_error=match['error']
                    if source_error: row['errors'].append(source_error+':'+inp['id'])
                    if p['statement_status'] in ('TARGET_DISPOSITION','LEGAL_RULE') or all(snap['sources'][r]['role']=='DISPOSITION_ONLY' for r in p['refs'] if r in snap['sources']):
                        row['errors'].append('DISPOSITION_OR_RULE_AS_FACT:'+inp['id'])
                    if p['statement_status'] not in contract['allowed_statuses']:
                        row['errors'].append('STATEMENT_STATUS_UPGRADE:'+inp['id'])
                row['sources']+=p.get('refs',p.get('sources',[]))
                if p.get('predicate') != contract['predicate']: row['errors'].append('PREDICATE_UPGRADE:'+slot)
                pb=binding_map(p.get('bindings',[]))
                if inp['kind']=='PREMISE':
                    pb, mapping_error, mapping_id = role_view(snap,s,slot,p,rule)
                    if mapping_error: row['errors'].append(mapping_error+':'+slot)
                    if mapping_id: row['semantic_assumptions'].append(mapping_id)
                if any(not pb.get(role) or not bm.get(role) for role in contract['required_roles']):
                    vals[slot]='UNKNOWN'; row['gaps'].append('BINDING_UNKNOWN:'+slot); continue
                if any(pb.get(role)!=bm.get(role) for role in contract['required_roles']): row['errors'].append('CROSS_OBJECT_JOIN:'+slot)
                if contract['time_required']:
                    if not p.get('time_scope') or not s['time_scope']:
                        vals[slot]='UNKNOWN'; row['gaps'].append('TIME_UNKNOWN:'+slot); continue
                    if p['time_scope']!=s['time_scope']: row['errors'].append('TIME_SCOPE_MISMATCH:'+slot)
                state=p['state']
                if slot in rule['exception_slots']:
                    # Exception proposition TRUE blocks; never invert missing to FALSE.
                    vals[slot]=state
                else:
                    vals[slot]=state if state in ('UNKNOWN','CONFLICTED') else ('TRUE' if state==contract['expected'] else 'FALSE')
            if not row['errors']:
                ordinary=[v for k,v in vals.items() if k not in rule['exception_slots']]
                exceptions=[vals[k] for k in rule['exception_slots']]
                value=combine(rule['operator'],ordinary,exceptions)
                if any(g in row['gaps'] for g in ('RULE_SEMANTICS_NOT_ACCEPTED','RULE_SCOPE_REVIEW_MISSING_OR_STALE')):value='UNKNOWN'
                if rule['operator']=='OPEN_TEXT':
                    assessment, issue = court_assessment(snap,s,rule)
                    if issue: row['errors'].append(issue)
                    accepted = not any(g in row['gaps'] for g in ('RULE_SEMANTICS_NOT_ACCEPTED','RULE_SCOPE_REVIEW_MISSING_OR_STALE'))
                    if (assessment and accepted and ordinary and all(v=='TRUE' for v in ordinary)
                            and all(v=='FALSE' for v in exceptions) and not row['uncomputed']):
                        value='TRUE'; row['sources'] += assessment['refs']
                        row['semantic_assumptions'].append(assessment['id'])
                        row['verification_basis']='ATTRIBUTED_COURT_ASSESSMENT_NOT_INDEPENDENT_LEGAL_EVALUATION'
                    else:
                        row['gaps'].append('OPEN_TEXT_NOT_IMPLEMENTED')
                        row['uncomputed'].append(sid)
                else: row['verification_basis']='EXPLICIT_CALCULUS_UNDER_REVIEWED_PREMISES'
                row['state']=value
                # A sufficient rule failing does not establish negation of its conclusion.
                # FALSE means antecedents fail, not false legal conclusion.
                if value=='FALSE':
                    row['state']='UNKNOWN';row['gaps'].append('SUFFICIENT_RULE_NOT_APPLICABLE_NO_NEGATIVE_INFERENCE')
                if s['proposed_state']!=row['state']:
                    if row['state'] in ('UNKNOWN','CONFLICTED'):
                        row['gaps'].append('MODEL_CONCLUSION_NOT_ESTABLISHED')
                    else: row['errors'].append('PROPOSED_RESULT_MISMATCH')
        visiting.remove(sid)
        row['sources']=list(dict.fromkeys(row['sources']))
        row['semantic_assumptions']=list(dict.fromkeys(row['semantic_assumptions']))
        row['uncomputed']=list(dict.fromkeys(row['uncomputed']))
        if row['errors']:row['status']='INVALID'
        elif row['state'] in ('UNKNOWN','CONFLICTED'):row['status']='INCOMPLETE_EXECUTION' if row['uncomputed'] else 'INCOMPLETE'
        elif row['semantic_assumptions']:row['status']='CONDITIONAL_RECONSTRUCTION'
        row['formal_legal_status']='NOT_LEGALLY_APPROVED'
        outputs[sid]=row
        return row
    result=[]
    for qid,q in requests.items():
        try:
            row=run(q['step_id'])
            errors=list(row['errors'])
            if q['predicate']!=row.get('predicate'):errors.append('REQUEST_TYPE_UPGRADE')
            if row['state'] not in ('UNKNOWN','CONFLICTED',None) and q['proposed_state']!=row['state']:errors.append('REQUEST_STATE_MISMATCH')
            state=None if errors or row['uncomputed'] else row['state']
            result.append({'id':qid,'text':rules.get(steps[q['step_id']]['rule_ref'],{}).get('conclusion_text'),
                'submitted_text':q['text'],'submitted_text_semantically_checked':False,
                'text_origin':'REVIEWED_RULE_TRANSLATION_NOT_FREE_REQUEST_PROSE','predicate':q['predicate'],
                'draft_status':'INVALID' if errors else row['status'],'answer':state,
                'errors':errors,'gaps':row['gaps'], 'step_id':q['step_id'],
                'model_proposed_state':q['proposed_state'],'semantic_assumptions':row['semantic_assumptions'],
                'uncomputed':row['uncomputed'], 'answer_basis':'NOT_COMPUTED' if row['uncomputed'] else 'CONDITIONAL_RECONSTRUCTION' if row['semantic_assumptions'] else 'EXPLICIT_CALCULUS',
                'formal_status':'APPROVAL_PENDING','source_refs':row['sources']})
        except (ValueError, KeyError, TypeError) as exc:
            visiting.clear()
            result.append({'id':qid,'text':q['text'],'draft_status':'INVALID','answer':None,'errors':[str(exc)],'formal_status':'APPROVAL_PENDING'})
    return {'status':'COMPLETED', 'task':'JUDGMENT_REASONING_RECONSTRUCTION','snapshot_id':snap['snapshot_id'],
        'requests':result,'steps':outputs, 'legal_approval':False, 'checker_version':'REALCASE_LOCAL_V4_SEMANTIC_ADDRESS',
        'interpretation':'Formal dependency checks under model-assisted, explicitly unapproved research premises and rules. No semantic or legal certification.'}

def check_file(certificate, trust_manifest, current=None):
    cert=read_json(certificate); manifest=read_json(trust_manifest); base=Path(trust_manifest).parent
    if current is not None and cert['snapshot_id']!=current: raise ValueError('STALE_CURRENT_SNAPSHOT')
    entry=manifest['snapshots'].get(cert['snapshot_id'])
    if not entry:raise ValueError('UNTRUSTED_SNAPSHOT')
    p=base/entry['path']
    if byte_hash(p)!=entry['sha256']:raise ValueError('SNAPSHOT_BYTES_CHANGED')
    snap=read_json(p)
    # Authenticate source originals as well as normalized snapshot text.
    for doc in snap['documents']:
        if byte_hash(base/doc['path'])!=doc['sha256']:raise ValueError('SOURCE_BYTES_CHANGED')
    return check_payload(cert,snap)
