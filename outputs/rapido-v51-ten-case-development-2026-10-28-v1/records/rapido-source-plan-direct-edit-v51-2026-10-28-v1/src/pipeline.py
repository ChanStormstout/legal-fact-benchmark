"""Two standalone full-report methods; no baseline or reference as model input."""
from common import save,write,digest
from prompts import TRUST,PLAN,WRITE_PLAN,WRITE_DRAFT,LOCATE,EDIT
from local_edits import resolve_plan,locate_findings,apply_local

def execute(client,dossier,method,dest,caps):
    dest.mkdir(parents=True,exist_ok=False);save(dest/'input.json',dossier)
    failures=[];stages=[];sources=dossier['sources']
    def call(stage,prompt,material):
        if client.halt:
            failures.append({'stage':stage,'status':'NOT_RUN_SERVICE_HALTED'});return None
        save(dest/(stage+'-input.json'),{'system':TRUST+'\n'+prompt,'material':material,'cap':caps[stage]})
        try:
            value=client.call(dossier['case_id']+'-'+method+'-'+stage,TRUST+'\n'+prompt,material,caps[stage]);save(dest/(stage+'-raw.json'),value);stages.append({'stage':stage,'status':'MODEL_COMPLETED','output_hash':digest(value)});return value
        except Exception as exc:
            failures.append({'stage':stage,'status':'FAILED','error':type(exc).__name__+':'+str(exc)});return None
    if method=='P':
        plan=call('plan',PLAN,dossier)
        try:resolved=resolve_plan(plan or {},sources)
        except Exception as exc:resolved={'items':[],'address_errors':[{'code':'MALFORMED_PLAN','error':str(exc)}],'semantic_acceptance':None}
        save(dest/'resolved-plan.json',resolved)
        draft=call('draft',WRITE_PLAN,{'originals':dossier,'source_plan':resolved,'plan_failed':plan is None})
    else:draft=call('draft',WRITE_DRAFT,dossier)
    text=draft.get('report') if isinstance(draft,dict) else None
    if not isinstance(text,str) or not text.strip():
        out={'case_id':dossier['case_id'],'method':method,'candidate_available':False,'final_report_available':False,'failures':failures,'status':'NO_USABLE_REPORT','quality':None};save(dest/'outcome.json',out);return out
    write(dest/'candidate-report.txt',text);final=text;audit={'edits':[],'applied':0,'semantic_retention_score':None}
    if method=='E':
        findings=call('locate',LOCATE,{'originals':dossier,'draft':text,'draft_sha256':digest(text)})
        if findings is None:
            findings={'findings':[],'unresolved':['TECHNICAL_DIAGNOSIS_FAILURE_NOT_CASE_UNKNOWN']}
        try:diagnostic=locate_findings(findings,text,sources)
        except Exception as exc:diagnostic=[{'code':'MALFORMED_FINDINGS','error':str(exc)}]
        save(dest/'finding-diagnostics.json',diagnostic)
        proposal=call('edit',EDIT,{'originals':dossier,'draft':text,'draft_sha256':digest(text),'relation_findings':findings,'mechanical_diagnostics':diagnostic})
        if proposal is None:audit={'edits':[],'applied':0,'revision_failed_draft_retained':True,'semantic_endorsement':False}
        else:
            try:final,audit=apply_local(text,proposal,sources)
            except Exception as exc:audit={'edits':[],'applied':0,'invalid_revision_draft_retained':True,'error':str(exc),'semantic_endorsement':False}
    save(dest/'edit-audit.json',audit);write(dest/'final-report.txt',final);save(dest/'stages.json',stages)
    # Store source-ID use as an address diagnostic, never as a quality score.
    import re
    ids=set(re.findall(r'(?<![A-Za-z0-9])[SL][0-9a-f]{12}(?![A-Za-z0-9])',final))
    save(dest/'source-use.json',{'inline_ids':sorted(ids),'unknown_inline_ids':sorted(ids-set(sources)),'CASE_LAW_sources_available':len(sources),'historical_RAG_used':False,'citation_support_not_evaluated':True})
    out={'case_id':dossier['case_id'],'method':method,'candidate_available':True,'final_report_available':True,'full_chain_completed':not failures,'failures':failures,'report_changed':text!=final,'applied_edits':audit.get('applied',0),'semantic_gate':False,'all_semantics_Qwen_proposed':True,'A0_used_as_method_input':False,'quality':None,'post_revision_semantics_independently_checked':False}
    save(dest/'outcome.json',out);return out
